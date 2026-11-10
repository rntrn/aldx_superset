"""Hak akses data berbasis profil pegawai DJP (row level security dinamis).

Alur:
    1. LOGIN  : sinkron_profil(username) mengambil profil dari Oracle
                (PEGAWAI + DIM_KANTOR, sama dengan engineN Mauth::cekuser)
                dan menyimpannya di tabel sps_akses_profil (database metadata).
    2. ATURAN : profil dicocokkan ke config/akses.yaml -> lingkup + peran.
    3. QUERY  : setiap dataset punya aturan RLS berisi {{ sps_akses(...) }}.
                Fungsi itu mengubah lingkup user yang sedang login menjadi
                kondisi SQL, mis. KD_KANWIL = '090' AND KD_KPP = '091'.

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
from sqlalchemy import Column, DateTime, MetaData, String, Table, select, text

log = logging.getLogger(__name__)

ATURAN_PATH = Path(__file__).with_name("akses.yaml")
SEMUA = "semua"
TIDAK_ADA_DATA = "1 = 0"
SEMUA_DATA = "1 = 1"
ATRIBUT = ("nip", "nip18", "nama", "kd_kantor", "kd_kpp", "kd_kanwil", "tp_kantor",
           "kd_unor", "kd_jabatan", "kd_jabatan_fung", "jabatan")
BATAS_DETIK_ORACLE = float(os.environ.get("AKSES_TIMEOUT", "8"))  # agar login tidak menggantung
_NAMA_KOLOM = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$#]{0,127}$")

# Query profil: sama dengan engineN app/Models/Mauth.php::cekuser (LEFT JOIN).
PROFIL_SQL = text("""
SELECT P.NIP9, P.NIP18, P.NAMA, P.KD_KANTOR, P.KPPADM, P.NAMA_JABATAN,
       P.KD_JAB_STRUKTURAL, P.KD_JAB_FUNGSIONAL, P.KD_UNIT_ORGANISASI,
       K.TP_KANTOR, K.KD_KANWIL
FROM PEGAWAI P LEFT JOIN DIM_KANTOR K ON P.KD_KANTOR = K.KD_KANTOR
WHERE P.NIP9 = :nip
""")
_KOLOM_ORACLE = {"nip": "NIP9", "nip18": "NIP18", "nama": "NAMA", "kd_kantor": "KD_KANTOR",
                 "kd_kpp": "KPPADM", "jabatan": "NAMA_JABATAN", "kd_jabatan": "KD_JAB_STRUKTURAL",
                 "kd_jabatan_fung": "KD_JAB_FUNGSIONAL", "kd_unor": "KD_UNIT_ORGANISASI",
                 "tp_kantor": "TP_KANTOR", "kd_kanwil": "KD_KANWIL"}

# Tabel profil di database metadata (MySQL sps_superset), prefix sps_.
_metadata = MetaData()
PROFIL_TABLE = Table(
    "sps_akses_profil", _metadata,
    Column("username", String(64), primary_key=True),
    *[Column(a, String(255)) for a in ATRIBUT],
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


def putuskan(profil: dict | None, aturan: dict | None = None) -> Keputusan:
    """Cari lingkup & peran untuk satu profil. Tanpa profil = tanpa akses."""
    if not profil:
        return Keputusan("tanpa profil")
    aturan = aturan if aturan is not None else muat_aturan()
    khusus = (aturan.get("pengecualian") or {}).get(str(profil.get("nip")))
    if khusus:
        return Keputusan("pengecualian", khusus.get("lingkup"), list(khusus.get("peran") or []))
    for a in aturan.get("aturan") or []:
        if _cocok(a.get("kapan"), profil):
            return Keputusan(a.get("nama", "?"), a.get("lingkup"), list(a.get("peran") or []))
    return Keputusan("tidak ada aturan cocok")


def kondisi_sql(keputusan: Keputusan, profil: dict | None, kolom: dict[str, str]) -> str:
    """Ubah lingkup menjadi kondisi SQL untuk satu dataset.

    kolom: atribut -> nama kolom di dataset, mis. {"kd_kanwil": "KD_KANWIL"}.
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
def _db():
    from superset import db
    return db


def _pastikan_tabel() -> None:
    PROFIL_TABLE.create(bind=_db().engine, checkfirst=True)


def baca_profil(username: str) -> dict | None:
    _pastikan_tabel()
    row = _db().session.execute(
        select(PROFIL_TABLE).where(PROFIL_TABLE.c.username == username)).mappings().first()
    return dict(row) if row else None


def sinkron_profil(username: str) -> dict | None:
    """Ambil profil terbaru dari Oracle lalu simpan. Gagal -> pakai profil lama."""
    from superset.models.core import Database

    nama_db = os.environ.get("AKSES_DATABASE", "Oracle DMP (GENAPP)")
    if not nama_db:                     # profil DJP tidak dipakai (perusahaan lain)
        return baca_profil(username)
    database = _db().session.query(Database).filter_by(database_name=nama_db).one_or_none()
    if database is None:
        log.error("Hak akses: koneksi '%s' tidak ada; profil %s tidak diperbarui", nama_db, username)
        return baca_profil(username)
    try:
        with database.get_sqla_engine() as engine:
            row = _query_dengan_batas_waktu(engine, username)
    except Exception:  # noqa: BLE001 - Oracle mati/lambat tidak boleh menggagalkan login
        log.exception("Hak akses: gagal membaca profil %s dari Oracle; pakai profil lama", username)
        return baca_profil(username)

    if row is None:
        log.warning("Hak akses: NIP %s tidak ada di PEGAWAI", username)
        return None
    upper = {k.upper(): v for k, v in row.items()}
    profil = {a: (str(upper.get(c)).strip() if upper.get(c) is not None else None)
              for a, c in _KOLOM_ORACLE.items()}
    _simpan(username, profil)
    return profil


def _query_profil(engine, username: str):
    with engine.connect() as conn:
        return conn.execute(PROFIL_SQL, {"nip": username}).mappings().first()


def _query_dengan_batas_waktu(engine, username: str):
    """Jalankan query profil maksimal BATAS_DETIK_ORACLE detik (TimeoutError bila lewat)."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(_query_profil, engine, username).result(timeout=BATAS_DETIK_ORACLE)
    finally:
        pool.shutdown(wait=False)


def _simpan(username: str, profil: dict) -> None:
    _pastikan_tabel()
    session = _db().session
    data = {**profil, "username": username, "diperbarui": datetime.now()}
    session.execute(PROFIL_TABLE.delete().where(PROFIL_TABLE.c.username == username))
    session.execute(PROFIL_TABLE.insert().values(**data))
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

    Contoh di RLS: {{ sps_akses(kd_kanwil='KD_KANWIL', kd_kpp='KD_KPP', nip='NIP_AR') }}
    Tanpa argumen = data nasional: hanya user berlingkup 'semua' yang melihat.
    """
    keputusan, profil = _konteks()
    return kondisi_sql(keputusan, profil, kolom)


def sidik_akses() -> str:
    """Sidik jari LINGKUP data user saat ini, untuk kunci cache chart.

    Superset menyusun kunci cache dari teks RLS mentah ("{{ sps_akses(...) }}")
    yang SAMA untuk semua user -> tanpa sidik ini cache bisa membocorkan data
    antar-pegawai. Pegawai dengan lingkup sama (mis. Kanwil 090) berbagi cache.
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
        # Tanpa profil (perusahaan tanpa profil DJP): data dibatasi aturan RLS per ROLE,
        # jadi lingkup = himpunan role. Pengguna dengan role sama berbagi cache & ramalan.
        user = _user_sekarang()
        nilai = {"peran": sorted(r.name for r in getattr(user, "roles", None) or [])}
    return hashlib.sha256(json.dumps(nilai, sort_keys=True).encode()).hexdigest()[:16]


def sps_sidik() -> str:
    """Untuk RLS dataset ramalan: {{ sps_sidik() }} = sidik lingkup user yang login."""
    return sidik_akses()


def sps_profil(atribut: str = "") -> Any:
    """Nilai profil user yang sedang login, mis. {{ sps_profil('kd_kanwil') }}."""
    _, profil = _konteks()
    profil = profil or {}
    return profil.get(atribut, "") if atribut else profil
