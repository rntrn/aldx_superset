"""Hak akses data berbasis profil pengguna (row level security dinamis). OPSIONAL.

Tanpa profil (bawaan): hak akses data diatur per ROLE lewat Settings > Row Level Security.
Dengan profil: setiap pengguna yang login diambil profilnya dari database perusahaan
(mis. tabel karyawan), lalu baris data dibatasi otomatis sesuai profil itu.

Alur:
    1. LOGIN  : sinkron_profil(username) menjalankan query `profil.sql` di config/akses.yaml
                pada koneksi `profil.database`, lalu menyimpan hasilnya (tabel sps_profil_pengguna).
    2. ATURAN : profil dicocokkan ke `aturan` di akses.yaml -> lingkup + peran.
    3. QUERY  : setiap dataset punya aturan RLS berisi {{ sps_akses(...) }}.
                Fungsi itu mengubah lingkup user yang sedang login menjadi kondisi SQL,
                mis. KD_CABANG IN ('C01').

Prinsip keamanan (gagal = tertutup):
    - Admin Superset             -> 1 = 1 (semua data)
    - Profil tidak ada           -> 1 = 0 (tidak ada data)
    - Tidak ada aturan cocok     -> 1 = 0
    - Data tidak punya kolom yang diwajibkan lingkup user -> 1 = 0
    - Nilai profil kosong        -> 1 = 0
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, select, text

log = logging.getLogger(__name__)

ATURAN_PATH = Path(__file__).with_name("akses.yaml")
SEMUA = "semua"
TIDAK_ADA_DATA = "1 = 0"
SEMUA_DATA = "1 = 1"
BATAS_DETIK_PROFIL = float(os.environ.get("AKSES_TIMEOUT", "8"))  # agar login tidak menggantung
_NAMA_KOLOM = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$#]{0,127}$")
_HANYA_BACA = re.compile(r"^\s*(select|with)\b", re.I)

# Profil disimpan sebagai JSON: atributnya bebas (sesuai kolom hasil query di akses.yaml).
_metadata = MetaData()
PROFIL_TABLE = Table(
    "sps_profil_pengguna", _metadata,
    Column("username", String(128), primary_key=True),
    Column("profil", Text),
    Column("diperbarui", DateTime),
)


# --- Aturan --------------------------------------------------------------------
@dataclass(frozen=True)
class Keputusan:
    """Hasil pencocokan profil ke aturan."""
    aturan: str
    lingkup: Any = None                       # "semua" | list[str] | dict[str, list[str]]
    peran: list[str] = field(default_factory=list)


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _cocok(kapan: dict, profil: dict) -> bool:
    for atribut, harapan in (kapan or {}).items():
        pilihan = harapan if isinstance(harapan, list) else [harapan]
        if _norm(profil.get(atribut)) not in {_norm(p) for p in pilihan}:
            return False
    return True


def muat_aturan() -> dict:
    with ATURAN_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def awalan_peran(aturan: dict | None = None) -> str:
    """Role berawalan ini dikelola otomatis saat login (dicabut lalu diberikan ulang sesuai aturan)."""
    aturan = aturan if aturan is not None else muat_aturan()
    return os.environ.get("AKSES_AWALAN_PERAN") or str(aturan.get("awalan_peran") or "Akses ")


def putuskan(profil: dict | None, aturan: dict | None = None) -> Keputusan:
    """Cari lingkup & peran untuk satu profil. Tanpa profil = tanpa akses."""
    if not profil:
        return Keputusan("tanpa profil")
    aturan = aturan if aturan is not None else muat_aturan()
    khusus = (aturan.get("pengecualian") or {}).get(str(profil.get("username")))
    if khusus:
        return Keputusan("pengecualian", khusus.get("lingkup"), list(khusus.get("peran") or []))
    for a in aturan.get("aturan") or []:
        if _cocok(a.get("kapan"), profil):
            return Keputusan(a.get("nama", "?"), a.get("lingkup"), list(a.get("peran") or []))
    return Keputusan("tidak ada aturan cocok")


def kondisi_sql(keputusan: Keputusan, profil: dict | None, kolom: dict[str, str]) -> str:
    """Ubah lingkup menjadi kondisi SQL untuk satu dataset.

    kolom: atribut -> nama kolom di dataset, mis. {"cabang": "KD_CABANG"}.
    """
    lingkup = keputusan.lingkup
    if lingkup == SEMUA:
        return SEMUA_DATA
    if not lingkup:
        return TIDAK_ADA_DATA

    nilai: dict[str, list[str]] = (
        {a: [(profil or {}).get(a)] for a in lingkup} if isinstance(lingkup, list)
        else {a: (v if isinstance(v, list) else [v]) for a, v in lingkup.items()}
    )
    bagian = []
    for atribut, daftar in nilai.items():
        nama_kolom = kolom.get(atribut)
        daftar = [str(v).strip() for v in daftar if str(v or "").strip()]
        if not nama_kolom or not _NAMA_KOLOM.match(nama_kolom) or not daftar:
            return TIDAK_ADA_DATA          # data tidak punya kolom wajib / nilai kosong
        literal = ", ".join("'" + v.replace("'", "''") + "'" for v in daftar)
        bagian.append(f"{nama_kolom} IN ({literal})")
    return " AND ".join(bagian)


# --- Profil (database) ---------------------------------------------------------
def sumber_profil(aturan: dict | None = None) -> tuple[str, str]:
    """(nama koneksi, query) profil. Kosong = profil tidak dipakai."""
    aturan = aturan if aturan is not None else muat_aturan()
    p = aturan.get("profil") or {}
    return (os.environ.get("AKSES_DATABASE") or str(p.get("database") or "")).strip(), str(p.get("sql") or "").strip()


def _db():
    from superset import db
    return db


def _pastikan_tabel() -> None:
    PROFIL_TABLE.create(bind=_db().engine, checkfirst=True)


def baca_profil(username: str) -> dict | None:
    _pastikan_tabel()
    row = _db().session.execute(
        select(PROFIL_TABLE.c.profil).where(PROFIL_TABLE.c.username == username)).first()
    return json.loads(row[0]) if row and row[0] else None


def sinkron_profil(username: str) -> dict | None:
    """Ambil profil terbaru dari database sumber lalu simpan. Gagal -> pakai profil lama."""
    from superset.models.core import Database

    nama_db, sql = sumber_profil()
    if not nama_db or not sql:                     # profil tidak dipakai: hak akses per role
        return baca_profil(username)
    if not _HANYA_BACA.match(sql) or ":username" not in sql:
        log.error("Hak akses: profil.sql harus SELECT dengan parameter :username; profil %s tidak diperbarui", username)
        return baca_profil(username)
    database = _db().session.query(Database).filter_by(database_name=nama_db).one_or_none()
    if database is None:
        log.error("Hak akses: koneksi '%s' tidak ada; profil %s tidak diperbarui", nama_db, username)
        return baca_profil(username)
    try:
        with database.get_sqla_engine() as engine:
            row = _query_dengan_batas_waktu(engine, sql, username)
    except Exception:  # noqa: BLE001 - sumber mati/lambat tidak boleh menggagalkan login
        log.exception("Hak akses: gagal membaca profil %s; pakai profil lama", username)
        return baca_profil(username)

    if row is None:
        log.warning("Hak akses: %s tidak ditemukan di sumber profil", username)
        return None
    profil = {str(k).lower(): (str(v).strip() if v is not None else None) for k, v in row.items()}
    profil["username"] = username
    _simpan(username, profil)
    return profil


def _query_profil(engine, sql: str, username: str):
    with engine.connect() as conn:
        return conn.execute(text(sql), {"username": username}).mappings().first()


def _query_dengan_batas_waktu(engine, sql: str, username: str):
    """Jalankan query profil maksimal BATAS_DETIK_PROFIL detik (TimeoutError bila lewat)."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(_query_profil, engine, sql, username).result(timeout=BATAS_DETIK_PROFIL)
    finally:
        pool.shutdown(wait=False)


def _simpan(username: str, profil: dict) -> None:
    _pastikan_tabel()
    session = _db().session
    session.execute(PROFIL_TABLE.delete().where(PROFIL_TABLE.c.username == username))
    session.execute(PROFIL_TABLE.insert().values(username=username, profil=json.dumps(profil, ensure_ascii=False),
                                                 diperbarui=datetime.now()))
    session.commit()


# --- Fungsi template SQL (dipanggil dari RLS / dataset) ------------------------
def _user_sekarang():
    from flask import g
    return getattr(g, "user", None)


def _konteks() -> tuple[Keputusan, dict | None]:
    """Profil + keputusan user yang sedang login (di-cache per request)."""
    from flask import g
    from superset import security_manager

    user = _user_sekarang()
    username = getattr(user, "username", None)
    cache = getattr(g, "_sps_akses", None)
    if cache and cache[0] == username:      # cache hanya untuk user yang SAMA
        return cache[1]

    if user is None or not getattr(user, "is_authenticated", False):
        hasil = (Keputusan("tidak login"), None)
    elif security_manager.is_admin():
        hasil = (Keputusan("admin superset", SEMUA), None)
    else:
        profil = baca_profil(user.username)
        hasil = (putuskan(profil), profil)
    g._sps_akses = (username, hasil)
    return hasil


def sps_akses(**kolom: str) -> str:
    """Kondisi SQL hak akses user yang sedang login.

    Contoh di RLS: {{ sps_akses(wilayah='KD_WILAYAH', cabang='KD_CABANG') }}
    Tanpa argumen = data menyeluruh: hanya user berlingkup 'semua' yang melihat.
    """
    keputusan, profil = _konteks()
    return kondisi_sql(keputusan, profil, kolom)


def sidik_akses() -> str:
    """Sidik jari LINGKUP data user saat ini, untuk kunci cache chart.

    Superset menyusun kunci cache dari teks RLS mentah ("{{ sps_akses(...) }}")
    yang SAMA untuk semua user -> tanpa sidik ini cache bisa membocorkan data
    antar-pengguna. Pengguna dengan lingkup sama (mis. cabang C01) berbagi cache.
    Tanpa profil: sidik dari daftar role (aturan RLS per role).
    """
    keputusan, profil = _konteks()
    lingkup = keputusan.lingkup
    if lingkup == SEMUA:
        nilai: Any = SEMUA
    elif isinstance(lingkup, list):
        nilai = {a: _norm((profil or {}).get(a)) for a in sorted(lingkup)}
    elif isinstance(lingkup, dict):
        nilai = {a: sorted(map(_norm, v if isinstance(v, list) else [v])) for a, v in sorted(lingkup.items())}
    else:
        # Tanpa profil: data dibatasi aturan RLS per ROLE, jadi lingkup = himpunan role.
        # Pengguna dengan role sama berbagi cache & ramalan.
        user = _user_sekarang()
        nilai = {"peran": sorted(r.name for r in getattr(user, "roles", None) or [])}
    return hashlib.sha256(json.dumps(nilai, sort_keys=True).encode()).hexdigest()[:16]


def sps_sidik() -> str:
    """Untuk RLS dataset ramalan: {{ sps_sidik() }} = sidik lingkup user yang login."""
    return sidik_akses()


def sps_profil(atribut: str = "") -> Any:
    """Nilai profil user yang sedang login, mis. {{ sps_profil('cabang') }}."""
    _, profil = _konteks()
    profil = profil or {}
    return profil.get(atribut, "") if atribut else profil
