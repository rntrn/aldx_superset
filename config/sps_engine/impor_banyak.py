"""Impor BANYAK tabel sekaligus dari satu koneksi database ke ALDx Engine, dengan CEK KAPASITAS lebih dulu.

Alur (Pusat Kendali › Ekstrak › Impor banyak tabel):
    1. pilih koneksi & skema       -> daftar tabel + perkiraan baris & ukuran dari katalog sumber
                                      (statistik database, tanpa COUNT(*) yang berat; "Hitung pasti" opsional)
    2. centang tabel, Cek kapasitas -> perkiraan kebutuhan di engine dibanding sisa kuota, ruang disk kosong,
                                      dan batas baris per ekstrak  ->  cukup / mendekati / tidak cukup
    3. Impor                        -> tiap tabel didaftarkan jadi dataset lalu dibuat ekstrak "penuh" dan
                                      dikirim ke antrean backgrounder. Ditolak server bila kapasitas tidak cukup.

Perkiraan ukuran di engine (ClickHouse menyimpan per kolom & terkompresi):
    ukuran sumber diketahui -> x RASIO_KOMPRESI;  hanya baris diketahui -> x BYTE_PER_BARIS (sama dengan Batas data).
Selalu disisakan ruang kosong (10% disk, maks. 10 GB) agar engine & sistem tetap sehat.

    GET  /pusat-kendali/api/ekstrak/impor/koneksi
    GET  /pusat-kendali/api/ekstrak/impor/tabel?db=<id>&skema=<nama>
    POST /pusat-kendali/api/ekstrak/impor/cek     {db, skema, tabel: [...], hitung: bool}
    POST /pusat-kendali/api/ekstrak/impor         {db, skema, tabel: [...], jadwal}
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from sps_engine import ekstrak as E
from sps_engine import tabel as T

log = logging.getLogger(__name__)

BYTE_PER_BARIS = 40           # baris terkompresi di ALDx Engine (sama dengan rumus Batas data)
RASIO_KOMPRESI = 0.3          # ukuran tabel sumber -> ukuran di ClickHouse (perkiraan hati-hati)
CADANGAN_DISK = 0.10          # disisakan 10% disk engine ...
CADANGAN_MAKS = 10e9          # ... tapi tidak lebih dari 10 GB (disk besar tidak "habis" oleh cadangan)
AMBANG_MENDEKATI = 0.8        # > 80% dari yang tersedia = "mendekati"
MAKS_TABEL = 200              # per sekali impor
MAKS_HITUNG = 30              # "Hitung pasti" (COUNT(*)) hanya untuk sejumlah tabel ini

# Statistik katalog per jenis database: (nama tabel, perkiraan baris, ukuran byte). :skema diisi skema terpilih.
SQL_PERKIRAAN = {
    "postgresql": "SELECT c.relname AS t, GREATEST(c.reltuples, 0)::bigint AS b, pg_total_relation_size(c.oid) AS z "
                  "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                  "WHERE n.nspname = :skema AND c.relkind IN ('r', 'p', 'm')",
    "mysql": "SELECT TABLE_NAME AS t, TABLE_ROWS AS b, DATA_LENGTH + INDEX_LENGTH AS z "
             "FROM information_schema.TABLES WHERE TABLE_SCHEMA = :skema",
    "mssql": "SELECT t.name AS t, SUM(p.rows) AS b, NULL AS z FROM sys.tables t "
             "JOIN sys.schemas s ON s.schema_id = t.schema_id JOIN sys.partitions p ON p.object_id = t.object_id "
             "WHERE s.name = :skema AND p.index_id IN (0, 1) GROUP BY t.name",
    "oracle": "SELECT table_name AS t, num_rows AS b, NULL AS z FROM all_tables WHERE owner = :skema",
    "clickhouse": "SELECT name AS t, total_rows AS b, total_bytes AS z FROM system.tables WHERE database = :skema",
    "clickhousedb": "SELECT name AS t, total_rows AS b, total_bytes AS z FROM system.tables WHERE database = :skema",
}
SQL_PERKIRAAN["mariadb"] = SQL_PERKIRAAN["mysql"]
SQL_PERKIRAAN["redshift"] = SQL_PERKIRAAN["postgresql"]


class GalatImpor(ValueError):
    pass


def _database(db_id: int):
    from superset import db
    from superset.models.core import Database
    d = db.session.get(Database, int(db_id or 0))
    if d is None:
        raise GalatImpor("Koneksi tidak ditemukan.")
    if E.adalah_engine(d):
        raise GalatImpor("Tabel ALDx Engine sudah ada di engine; pilih koneksi database sumber.")
    return d


def koneksi() -> list[dict]:
    from superset import db
    from superset.models.core import Database
    return [{"id": d.id, "nama": d.database_name, "jenis": d.backend}
            for d in db.session.query(Database).order_by(Database.database_name) if not E.adalah_engine(d)]


def _skema_bawaan(d) -> str | None:
    try:
        with d.get_sqla_engine() as eng:
            return inspect(eng).default_schema_name
    except Exception:  # noqa: BLE001
        return None


def _perkiraan(d, skema: str | None) -> dict[str, tuple[int | None, int | None]]:
    sql = SQL_PERKIRAAN.get(d.backend)
    if not sql or not skema:
        return {}
    try:
        with d.get_sqla_engine() as eng, eng.connect() as c:
            hasil = c.execute(text(sql), {"skema": skema.upper() if d.backend == "oracle" else skema}).fetchall()
        return {str(r[0]).lower(): (int(r[1]) if r[1] is not None else None, int(r[2]) if r[2] is not None else None)
                for r in hasil}
    except Exception as exc:  # noqa: BLE001 - statistik tidak wajib; tanpa itu perkiraan "tidak diketahui"
        log.info("ALDx impor: statistik katalog %s tidak terbaca (%s)", d.backend, exc)
        return {}


def daftar_tabel(db_id: int, skema: str | None) -> dict:
    d = _database(db_id)
    skema = (skema or "").strip() or _skema_bawaan(d)
    try:
        with d.get_sqla_engine() as eng:
            ins = inspect(eng)
            nama = sorted(ins.get_table_names(schema=skema))
            semua_skema = sorted(ins.get_schema_names())
    except Exception as exc:  # noqa: BLE001
        raise GalatImpor(f"Tabel tidak terbaca dari koneksi ini: {str(exc).splitlines()[0][:200]}") from exc
    perk = _perkiraan(d, skema)
    return {"skema": skema, "semua_skema": semua_skema, "statistik": bool(perk),
            "tabel": [{"nama": n, "baris": perk.get(n.lower(), (None, None))[0],
                       "byte": perk.get(n.lower(), (None, None))[1]} for n in nama]}


def _hitung_pasti(d, skema: str | None, nama: list[str]) -> dict[str, int]:
    hasil = {}
    with d.get_sqla_engine() as eng, eng.connect() as c:
        q = eng.dialect.identifier_preparer.quote
        for n in nama[:MAKS_HITUNG]:
            sumber = f"{q(skema)}.{q(n)}" if skema else q(n)
            try:
                hasil[n.lower()] = int(c.execute(text(f"SELECT COUNT(*) FROM {sumber}")).scalar() or 0)
            except Exception:  # noqa: BLE001
                log.info("ALDx impor: COUNT(*) %s gagal", sumber)
    return hasil


def _perlu_byte(baris: int | None, byte: int | None) -> int | None:
    if byte:
        return int(byte * RASIO_KOMPRESI)
    if baris is not None:
        return int(baris * BYTE_PER_BARIS)
    return None


def cek(db_id: int, skema: str | None, tabel: list[str], hitung: bool = False) -> dict:
    """Perkiraan kebutuhan penyimpanan vs kapasitas ALDx Engine untuk tabel terpilih."""
    from sps_server import batas, penyimpanan
    d = _database(db_id)
    tabel = [str(t) for t in tabel or []][:MAKS_TABEL]
    if not tabel:
        raise GalatImpor("Centang minimal satu tabel.")
    skema = (skema or "").strip() or _skema_bawaan(d)
    perk = _perkiraan(d, skema)
    pasti = _hitung_pasti(d, skema, [t for t in tabel if hitung or perk.get(t.lower(), (None,))[0] is None]) \
        if hitung else {}
    atur = penyimpanan.nilai_semua()
    kuota_gb, baris_maks = batas.berlaku(atur, "ekstrak.total_gb"), batas.berlaku(atur, "ekstrak.baris_maks")
    disk = batas._engine_disk()
    if disk["bebas"] is None:
        raise GalatImpor("ALDx Engine tidak terjangkau: kapasitas tidak bisa dicek. Nyalakan container engine dulu.")
    sisa_kuota = (kuota_gb * 1e9 - disk["terpakai"]) if kuota_gb else None
    sisa_disk = disk["bebas"] - min(disk["total"] * CADANGAN_DISK, CADANGAN_MAKS)
    tersedia = int(max(0, min(x for x in (sisa_kuota, sisa_disk) if x is not None)))

    baris_tabel, total, tak_diketahui = [], 0, 0
    for t in tabel:
        b, z = perk.get(t.lower(), (None, None))
        if t.lower() in pasti:
            b = pasti[t.lower()]
        perlu = _perlu_byte(b, z)
        catatan = ""
        if baris_maks and b and b > baris_maks:
            catatan = f"melebihi batas {baris_maks:,} baris per ekstrak".replace(",", ".")
        if perlu is None:
            tak_diketahui += 1
            catatan = catatan or "ukuran tidak diketahui (klik Hitung pasti)"
        else:
            total += perlu
        baris_tabel.append({"nama": t, "baris": b, "byte_sumber": z, "perlu_byte": perlu, "catatan": catatan})

    lebih_baris = [x["nama"] for x in baris_tabel if x["catatan"].startswith("melebihi")]
    if total > tersedia or lebih_baris:
        vonis = "tidak_cukup"
    elif total > tersedia * AMBANG_MENDEKATI or tak_diketahui:
        vonis = "mendekati"
    else:
        vonis = "cukup"
    return {"vonis": vonis, "perlu_byte": total, "tersedia_byte": tersedia, "tak_diketahui": tak_diketahui,
            "lebih_baris": lebih_baris, "kuota_gb": kuota_gb, "disk_bebas": disk["bebas"],
            "disk_total": disk["total"], "terpakai": disk["terpakai"], "tabel": baris_tabel,
            "metode": f"ukuran sumber x {RASIO_KOMPRESI} atau baris x {BYTE_PER_BARIS} byte; disisakan "
                      f"{int(CADANGAN_DISK * 100)}% disk (maks. {int(CADANGAN_MAKS / 1e9)} GB) kosong"}


def _dataset_untuk(d, skema: str | None, nama: str):
    """Dataset fisik untuk tabel sumber (dibuat bila belum ada)."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    t = db.session.query(SqlaTable).filter_by(database_id=d.id, schema=skema, table_name=nama).one_or_none()
    if t is None:
        t = SqlaTable(table_name=nama, database=d, schema=skema)
        db.session.add(t)
        db.session.flush()
        t.fetch_metadata()
        db.session.commit()
    return t


def impor(db_id: int, skema: str | None, tabel: list[str], jadwal: dict, oleh: str, kirim) -> dict:
    """Daftarkan dataset + buat ekstrak penuh untuk setiap tabel. kirim(ekstrak_id) = antrekan penyegaran."""
    hasil_cek = cek(db_id, skema, tabel)
    if hasil_cek["vonis"] == "tidak_cukup":
        raise GalatImpor("Kapasitas ALDx Engine tidak cukup untuk tabel terpilih. Kurangi tabel, hapus ekstrak lama, "
                         "atau minta Superadmin menaikkan kuota (Pusat Kendali › Batas data).")
    d = _database(db_id)
    skema = (skema or "").strip() or _skema_bawaan(d)
    hasil = []
    for nama in tabel[:MAKS_TABEL]:
        try:
            t = _dataset_untuk(d, skema, nama)
            nama_ekstrak = T.nama_aman(f"{skema}_{nama}" if skema else nama).lower()
            e = E.buat(t.id, nama_ekstrak, "penuh", None, jadwal or {}, oleh)
            hasil.append({"tabel": nama, "ok": True, "ekstrak": e["nama"], "kirim": kirim(e["id"])})
        except Exception as exc:  # noqa: BLE001 - satu tabel gagal tidak menggagalkan yang lain
            from superset import db
            db.session.rollback()
            hasil.append({"tabel": nama, "ok": False, "pesan": str(exc).splitlines()[0][:200]})
    return {"hasil": hasil, "berhasil": sum(1 for x in hasil if x["ok"]), "cek": hasil_cek}
