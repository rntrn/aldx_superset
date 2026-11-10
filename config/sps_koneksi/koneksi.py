"""Uji & simpan koneksi database (dipakai wizard "Hubungkan data").

Koneksi disimpan sebagai Database Superset biasa: password terenkripsi oleh Superset,
muncul di menu Data > Database, dan bisa dipakai SQL Lab / dataset / Studio.
Koneksi baru selalu HANYA-BACA (allow_dml=False) & tanpa upload: sumber kantor aman.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy import create_engine, inspect, text

from sps_koneksi import katalog

BATAS_DETIK = 15
MAKS_SKEMA = 5000                         # Oracle besar bisa punya ratusan skema (satu per pengguna)


def _uri_dan_extra(jenis: katalog.Jenis, n: dict[str, Any]) -> tuple[str, dict, dict]:
    katalog.periksa(jenis, n)
    if not jenis.driver_ada():
        raise ValueError(f"Driver {jenis.nama} belum terpasang di image. Lihat docker/wheels/README.md")
    uri = jenis.uri(n)
    _cegah_berkas_lokal(uri)
    return uri, jenis.extra(n), jenis.rahasia_extra(n)


def uji(jenis_id: str, n: dict[str, Any]) -> dict:
    """Coba sambung, ambil versi & daftar schema. Tidak menyimpan apa pun."""
    if jenis_id not in katalog.PETA:
        raise ValueError("Jenis database tidak dikenal")
    jenis = katalog.PETA[jenis_id]
    uri, extra, rahasia = _uri_dan_extra(jenis, n)
    _cegah_internal(uri)
    argumen = {}
    if rahasia.get("credentials_info"):
        argumen["credentials_info"] = rahasia["credentials_info"]
    mulai = time.monotonic()
    e = create_engine(uri, pool_pre_ping=False, **argumen, **_batas_waktu(uri))
    try:
        with e.connect() as c:
            c.execute(text(_sql_uji(e.dialect.name)))
            versi = ".".join(map(str, e.dialect.server_version_info or ())) or "-"
            try:
                ins = inspect(c)
                skema, skema_login = sorted(ins.get_schema_names())[:MAKS_SKEMA], ins.default_schema_name
            except Exception:  # noqa: BLE001 - beberapa driver tidak mendukung daftar schema
                skema, skema_login = [], None
    finally:
        e.dispose()
    return {"ok": True, "versi": versi, "dialek": e.dialect.name, "skema": skema, "skema_login": skema_login,
            "ms": round((time.monotonic() - mulai) * 1000)}


def daftar_skema(database) -> dict:
    """Semua skema koneksi tersimpan + skema yang dipilih (sps_skema)."""
    import sps_skema
    with database.get_inspector() as ins:
        semua = sorted(ins.get_schema_names())[:MAKS_SKEMA]
        login = ins.default_schema_name
    return {"semua": semua, "pilih": sps_skema.pilihan(database), "skema_login": login}


def simpan(jenis_id: str, n: dict[str, Any], nama: str, skema: list[str] | None = None) -> dict:
    """Uji dulu, lalu simpan sebagai Database Superset (nama unik). skema = skema yang ditampilkan (kosong = semua)."""
    from superset import db
    from superset.models.core import Database

    nama = (nama or "").strip()
    if not nama or len(nama) > 120:
        raise ValueError("Nama koneksi wajib diisi (maks 120 karakter)")
    if db.session.query(Database).filter_by(database_name=nama).first():
        raise ValueError(f"Nama koneksi '{nama}' sudah dipakai. Pilih nama lain.")
    hasil = uji(jenis_id, n)
    jenis = katalog.PETA[jenis_id]
    uri, extra, rahasia = _uri_dan_extra(jenis, n)
    d = Database(database_name=nama, expose_in_sqllab=True, allow_dml=False, allow_file_upload=False,
                 allow_run_async=False, extra=json.dumps({"metadata_params": {}, "engine_params": extra,
                                                          "schemas_allowed_for_file_upload": []}))
    if rahasia:
        d.encrypted_extra = json.dumps(rahasia)
    d.set_sqlalchemy_uri(uri)                 # password dipisah & dienkripsi oleh Superset
    db.session.add(d)
    db.session.commit()
    if skema:
        import sps_skema
        sps_skema.simpan(d, skema)
    return {**hasil, "id": d.id, "nama": d.database_name}


# --- Pembantu ---------------------------------------------------------------------------------
def pesan_galat(exc: Exception) -> str:
    """Pesan driver yang ringkas & aman ditampilkan (password di URI disamarkan)."""
    asal = getattr(exc, "orig", None) or exc
    teks = str(asal).split("(Background on this error")[0].strip() or type(asal).__name__
    teks = re.sub(r"(://[^:/@\s]+):[^@\s]+@", r"\1:***@", teks)
    baris = [b.strip() for b in teks.splitlines() if b.strip()]
    return " ".join(baris[:3])[:400]


def _sql_uji(dialek: str) -> str:
    return {"oracle": "SELECT 1 FROM DUAL", "hana": "SELECT 1 FROM DUMMY"}.get(dialek, "SELECT 1")


def _batas_waktu(uri: str) -> dict:
    """Agar tombol Uji tidak menggantung lama bila server tidak terjangkau."""
    awal = uri.split("://", 1)[0]
    if awal.startswith(("postgresql", "redshift")):
        return {"connect_args": {"connect_timeout": BATAS_DETIK}}
    if awal.startswith("mysql"):
        return {"connect_args": {"connect_timeout": BATAS_DETIK}}
    if awal.startswith("mssql"):
        return {"connect_args": {"login_timeout": BATAS_DETIK, "timeout": BATAS_DETIK}}
    if awal.startswith("clickhouse"):
        return {"connect_args": {"connect_timeout": BATAS_DETIK}}
    return {}


def _cegah_berkas_lokal(uri: str) -> None:
    """SQLite/DuckDB = berkas di server; diimpor lewat jalur Berkas, bukan dihubungkan (aturan Superset)."""
    from flask import current_app
    if not current_app.config.get("PREVENT_UNSAFE_DB_CONNECTIONS", True):
        return
    if uri.split(":", 1)[0].split("+", 1)[0].lower() in {"sqlite", "duckdb", "shillelagh"}:
        raise ValueError("Berkas SQLite/DuckDB diimpor lewat pilihan 'Berkas', bukan dihubungkan langsung.")


def _cegah_internal(uri: str) -> None:
    """Metadata Superset tidak boleh dijadikan sumber data (berisi user & password terenkripsi)."""
    from sps_server import lingkungan
    from sqlalchemy.engine import make_url
    try:
        u, m = make_url(uri), make_url(lingkungan.uri_metadata())
    except Exception:  # noqa: BLE001
        return
    if u.host and u.host == m.host and (u.database or "") == (m.database or "") and u.get_backend_name() == m.get_backend_name():
        raise ValueError("Database metadata Superset tidak boleh dihubungkan sebagai sumber data.")
