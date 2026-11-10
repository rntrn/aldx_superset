"""Tabel di ALDx Engine: tebak tipe, buat tabel, isi penuh (tukar atomik) & isi tambahan.

Tipe ClickHouse dipilih dari data (potongan pertama):
    bilangan bulat   -> Nullable(Int64)
    pecahan/Decimal  -> Nullable(Float64)
    tanggal-waktu    -> Nullable(DateTime64(3))
    tanggal          -> Nullable(Date32)
    teks berulang    -> LowCardinality(Nullable(String))   (mis. kode kanwil: hemat & cepat)
    teks lain        -> Nullable(String)
Urutan penyimpanan (ORDER BY) = kolom hak akses (mis. KD_KANWIL), agar filter per pegawai cepat.
"""

from __future__ import annotations

import datetime as dt
import decimal
import re
from typing import Iterable

import pandas as pd

NAMA_SAH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,120}$")
BATAS_LOW_CARDINALITY = 10_000


def nama_aman(n: str) -> str:
    n = re.sub(r"[^A-Za-z0-9_]", "_", str(n).strip())
    n = n if re.match(r"^[A-Za-z_]", n) else f"k_{n}"
    return n[:120]


def kutip(n: str) -> str:
    return "`" + str(n).replace("`", "") + "`"


def _contoh(s: pd.Series):
    isi = s.dropna()
    return isi.iloc[0] if len(isi) else None


def tipe_kolom(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "Nullable(UInt8)"
    if pd.api.types.is_integer_dtype(s):
        return "Nullable(Int64)"
    if pd.api.types.is_float_dtype(s):
        return "Nullable(Float64)"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "Nullable(DateTime64(3))"
    contoh = _contoh(s)
    if isinstance(contoh, bool):
        return "Nullable(UInt8)"
    if isinstance(contoh, (int,)) and s.dropna().map(lambda v: isinstance(v, int)).all():
        return "Nullable(Int64)"
    if isinstance(contoh, (float, decimal.Decimal, int)):
        return "Nullable(Float64)"
    if isinstance(contoh, (dt.datetime, pd.Timestamp)):
        return "Nullable(DateTime64(3))"
    if isinstance(contoh, dt.date):
        return "Nullable(Date32)"
    isi = s.dropna()
    if len(isi) and isi.nunique() <= min(BATAS_LOW_CARDINALITY, max(1, len(isi) // 2)):
        return "LowCardinality(Nullable(String))"
    return "Nullable(String)"


def tebak_tipe(df: pd.DataFrame) -> dict[str, str]:
    return {k: tipe_kolom(df[k]) for k in df.columns}


def sesuaikan(df: pd.DataFrame, tipe: dict[str, str]) -> pd.DataFrame:
    """Ubah nilai tiap potongan agar cocok dengan tipe tabel."""
    hasil = pd.DataFrame(index=df.index)
    for k, t in tipe.items():
        s = df[k] if k in df else pd.Series([None] * len(df), index=df.index)
        if "Int64" in t or "UInt8" in t:
            hasil[k] = pd.to_numeric(s, errors="coerce").astype("Int64")
        elif "Float64" in t:
            hasil[k] = pd.to_numeric(s.map(lambda v: float(v) if isinstance(v, decimal.Decimal) else v),
                                     errors="coerce").astype("float64")
        elif "DateTime64" in t:
            hasil[k] = pd.to_datetime(s, errors="coerce")
        elif "Date32" in t:
            hasil[k] = pd.to_datetime(s, errors="coerce").dt.date
        else:
            hasil[k] = s.map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    return hasil


def ddl(tabel: str, tipe: dict[str, str], urut: list[str]) -> str:
    kolom = ",\n  ".join(f"{kutip(k)} {t}" for k, t in tipe.items())
    kunci = ", ".join(kutip(k) for k in urut if k in tipe) or "tuple()"
    return (f"CREATE TABLE {tabel} (\n  {kolom}\n) ENGINE = MergeTree ORDER BY ({kunci})\n"
            "SETTINGS allow_nullable_key = 1")


def isi_penuh(klien, db: str, tabel: str, potongan: Iterable[pd.DataFrame], urut: list[str]) -> tuple[int, dict]:
    """Muat ke tabel sementara lalu TUKAR atomik, sehingga dashboard tak pernah melihat data setengah jadi."""
    target, sementara = f"{db}.{kutip(tabel)}", f"{db}.{kutip(tabel + '__baru')}"
    klien.perintah(f"DROP TABLE IF EXISTS {sementara}")
    tipe, baris = None, 0
    try:
        for df in potongan:
            if tipe is None:
                tipe = tebak_tipe(df)
                klien.perintah(ddl(sementara, tipe, urut))
            if len(df):
                klien.sisip_df(sementara.replace("`", ""), sesuaikan(df, tipe))
                baris += len(df)
    except Exception:
        klien.perintah(f"DROP TABLE IF EXISTS {sementara}")       # gagal/melebihi batas: data lama tetap utuh
        raise
    if tipe is None:
        raise ValueError("Sumber tidak mengembalikan kolom apa pun.")
    if ada(klien, db, tabel):
        klien.perintah(f"EXCHANGE TABLES {target} AND {sementara}")
        klien.perintah(f"DROP TABLE {sementara}")
    else:
        klien.perintah(f"RENAME TABLE {sementara} TO {target}")
    return baris, tipe


def isi_tambah(klien, db: str, tabel: str, potongan: Iterable[pd.DataFrame], tipe: dict[str, str]) -> int:
    """Tambah baris lewat tabel sementara lalu satu INSERT ... SELECT: bila gagal/melebihi batas di tengah jalan,
    tabel tujuan tidak berubah sama sekali (tidak ada baris setengah masuk)."""
    target, sementara = f"{db}.{kutip(tabel)}", f"{db}.{kutip(tabel + '__tambah')}"
    klien.perintah(f"DROP TABLE IF EXISTS {sementara}")
    klien.perintah(f"CREATE TABLE {sementara} AS {target}")
    baris = 0
    try:
        for df in potongan:
            if len(df):
                klien.sisip_df(sementara.replace("`", ""), sesuaikan(df, tipe))
                baris += len(df)
        if baris:
            klien.perintah(f"INSERT INTO {target} SELECT * FROM {sementara}")
    finally:
        klien.perintah(f"DROP TABLE IF EXISTS {sementara}")
    return baris


def ada(klien, db: str, tabel: str) -> bool:
    df = klien.kueri_df(f"SELECT count() AS n FROM system.tables WHERE database = '{db}' AND name = '{tabel}'")
    return int(df["n"].iloc[0]) > 0


def tipe_tabel(klien, db: str, tabel: str) -> dict[str, str]:
    df = klien.kueri_df(f"SELECT name, type FROM system.columns WHERE database = '{db}' AND table = '{tabel}' "
                        "ORDER BY position")
    return dict(zip(df["name"], df["type"]))


def statistik(klien, db: str, tabel: str) -> dict:
    df = klien.kueri_df(f"SELECT sum(rows) AS baris, sum(bytes_on_disk) AS ukuran FROM system.parts "
                        f"WHERE database = '{db}' AND table = '{tabel}' AND active")
    return {"baris": int(df["baris"].iloc[0] or 0), "ukuran_byte": int(df["ukuran"].iloc[0] or 0)}


def hapus(klien, db: str, tabel: str) -> None:
    klien.perintah(f"DROP TABLE IF EXISTS {db}.{kutip(tabel)}")
