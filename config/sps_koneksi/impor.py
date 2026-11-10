"""Impor BERKAS (Access, Excel, CSV, SQLite, DuckDB, Parquet) ke ALDx Engine.

Berkas tidak bisa "dihubungkan" seperti server database, jadi isinya disalin ke
ALDx Engine lalu didaftarkan sebagai dataset Superset (siap dibuat chart).

Alur:
    1. baca_tabel(path)     -> {nama_tabel: fungsi pembaca potongan DataFrame}
    2. pratinjau(path)      -> daftar tabel + kolom + 5 baris contoh (untuk wizard)
    3. impor(path, pilihan) -> salin tabel terpilih ke engine & buat dataset
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Callable, Iterator

import pandas as pd

log = logging.getLogger(__name__)
POTONGAN = 50_000
Pembaca = Callable[[], Iterator[pd.DataFrame]]


# --- Pembaca per jenis berkas ---------------------------------------------------------------
def _csv(path: Path) -> dict[str, Pembaca]:
    def baca():
        with open(path, "rb") as f:
            awal = f.read(4096).decode("utf-8", "replace")
        pemisah = max([",", ";", "\t", "|"], key=awal.count)
        return pd.read_csv(path, sep=pemisah, chunksize=POTONGAN, encoding_errors="replace", low_memory=False)
    return {path.stem: baca}


def _excel(path: Path) -> dict[str, Pembaca]:
    mesin = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    lembar = pd.ExcelFile(path, engine=mesin).sheet_names
    return {s: (lambda s=s: iter([pd.read_excel(path, sheet_name=s, engine=mesin)])) for s in lembar}


def _access(path: Path) -> dict[str, Pembaca]:
    from access_parser import AccessParser
    logging.getLogger("access_parser").setLevel(logging.CRITICAL)   # pustaka ini sangat "cerewet"
    db = AccessParser(str(path))
    nama = [t for t in db.catalog if not t.startswith(("MSys", "~"))]

    def baca(t):
        isi = db.parse_table(t)                   # {kolom: [nilai...]}
        return iter([pd.DataFrame({k: list(v) for k, v in isi.items()})])
    return {t: (lambda t=t: baca(t)) for t in nama}


def _sqlite(path: Path) -> dict[str, Pembaca]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as c:
        nama = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') "
                                        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    def baca(t):
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            yield from pd.read_sql(f'SELECT * FROM "{t}"', c, chunksize=POTONGAN)
        finally:
            c.close()
    return {t: (lambda t=t: baca(t)) for t in nama}


def _duckdb(path: Path) -> dict[str, Pembaca]:
    import duckdb
    with duckdb.connect(str(path), read_only=True) as c:
        nama = [r[0] for r in c.execute("SELECT table_name FROM information_schema.tables "
                                        "WHERE table_schema = 'main' ORDER BY 1").fetchall()]

    def baca(t):
        with duckdb.connect(str(path), read_only=True) as c:
            yield c.execute(f'SELECT * FROM "{t}"').df()
    return {t: (lambda t=t: baca(t)) for t in nama}


def _parquet(path: Path) -> dict[str, Pembaca]:
    return {path.stem: lambda: iter([pd.read_parquet(path)])}


PEMBACA = {".csv": _csv, ".txt": _csv, ".tsv": _csv, ".xlsx": _excel, ".xlsm": _excel, ".xls": _excel,
           ".mdb": _access, ".accdb": _access, ".sqlite": _sqlite, ".db": _sqlite, ".sqlite3": _sqlite,
           ".duckdb": _duckdb, ".parquet": _parquet}


def _tanpa_biner(df: pd.DataFrame) -> pd.DataFrame:
    """Kolom biner (foto/OLE di Access, BLOB di SQLite) tidak bisa dianalisis: dilewati."""
    biner = [k for k in df.columns if df[k].dtype == object
             and df[k].map(lambda v: isinstance(v, (bytes, bytearray, memoryview))).any()]
    if biner:
        log.info("ALDx impor: kolom biner dilewati: %s", ", ".join(map(str, biner)))
    return df.drop(columns=biner)


def _bersih(baca: Pembaca) -> Pembaca:
    return lambda: (_tanpa_biner(df) for df in baca())


def baca_tabel(path: Path) -> dict[str, Pembaca]:
    akhiran = path.suffix.lower()
    if akhiran not in PEMBACA:
        raise ValueError(f"Jenis berkas {akhiran} belum didukung. Didukung: {', '.join(sorted(PEMBACA))}")
    try:
        tabel = PEMBACA[akhiran](path)
    except ImportError as exc:
        raise ValueError(f"Driver untuk {akhiran} belum terpasang ({exc.name}). Lihat docker/wheels/README.md") from exc
    if not tabel:
        raise ValueError("Berkas tidak berisi tabel.")
    return {nama: _bersih(baca) for nama, baca in tabel.items()}


def pratinjau(path: Path) -> list[dict]:
    hasil = []
    for nama, baca in baca_tabel(path).items():
        try:
            df = next(iter(baca()), pd.DataFrame()).head(5)
            hasil.append({"nama": nama, "kolom": [str(k) for k in df.columns],
                          "contoh": df.astype(str).values.tolist()})
        except Exception as exc:  # noqa: BLE001 - satu tabel rusak tidak menggagalkan yang lain
            hasil.append({"nama": nama, "kolom": [], "contoh": [], "galat": str(exc)})
    return hasil


# --- Impor ke ALDx Engine -----------------------------------------------------------------------
def impor(path: Path, pilihan: list[str], awalan: str, pemilik, nama_asli: str = "") -> list[dict]:
    """Salin tabel terpilih ke ALDx Engine & buat dataset. Tabel dengan nama sama diganti isinya."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable, TableColumn

    from sps_engine import klien as K, tabel as T
    from sps_engine.ekstrak import _tipe_superset, database_engine
    from sps_server import batas, penyimpanan

    atur = penyimpanan.nilai_semua()
    batas.periksa_kuota_engine(atur)
    maks_baris = batas.berlaku(atur, "impor.baris_maks")

    tabel = baca_tabel(path)
    tidak_ada = [p for p in pilihan if p not in tabel]
    if tidak_ada:
        raise ValueError(f"Tabel tidak ditemukan di berkas: {', '.join(tidak_ada)}")
    k, nama_db, eng = K.klien(), K.nama_db(), database_engine()
    hasil = []
    for p in pilihan:
        dasar = T.nama_aman(p).lower()
        nama = dasar if not awalan or T.nama_aman(awalan).lower() == dasar else T.nama_aman(f"{awalan}_{p}").lower()
        potongan = batas.batasi_baris((df.rename(columns=lambda c: T.nama_aman(c)) for df in tabel[p]()),
                                      maks_baris, f"Tabel '{p}'")
        baris, tipe = T.isi_penuh(k, nama_db, nama, potongan, [])
        ds = db.session.query(SqlaTable).filter_by(database_id=eng.id, schema=nama_db, table_name=nama).one_or_none()
        if ds is None:
            ds = SqlaTable(table_name=nama, schema=nama_db, database=eng, owners=[pemilik] if pemilik else [],
                           description=f"Impor dari berkas {nama_asli or path.name} (tabel '{p}').")
            db.session.add(ds)
        ada = {c.column_name for c in ds.columns}
        for kolom, tch in tipe.items():
            if kolom not in ada:
                jenis, waktu = _tipe_superset(tch)
                ds.columns.append(TableColumn(column_name=kolom, type=jenis, is_dttm=waktu,
                                              groupby=True, filterable=True))
        db.session.commit()
        hasil.append({"tabel": p, "dataset": nama, "dataset_id": ds.id, "baris": baris})
        log.info("ALDx impor berkas %s: %s -> %s (%d baris)", nama_asli or path.name, p, nama, baris)
    return hasil
