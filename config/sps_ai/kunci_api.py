"""Key API model cloud yang diisi lewat aplikasi (panel Asisten AI › Sambungkan AI).

Disimpan TERENKRIPSI di database metadata (tabel sps_ai_kunci), kunci enkripsi diturunkan dari
SUPERSET_SECRET_KEY, sehingga semua node membaca key yang sama dan tidak perlu restart.
Key di .env (AI_*_API_KEY) tetap berlaku dan didahulukan.

Browser tidak pernah menerima key: hanya status "terisi" dan 4 karakter terakhirnya.
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, delete, insert, select

log = logging.getLogger(__name__)

_meta = MetaData()
KUNCI = Table("sps_ai_kunci", _meta,
              Column("nama", String(64), primary_key=True),       # nama variabel, mis. AI_GEMINI_API_KEY
              Column("nilai", Text),                              # terenkripsi (Fernet)
              Column("diubah", DateTime), Column("oleh", String(128)))

UMUR_DETIK = 15
BAWAAN = "_MODEL_BAWAAN"          # bukan key: id model yang dipilih Admin sebagai bawaan
_tembolok: tuple[float, dict[str, str]] | None = None
_kunci = threading.Lock()


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


def _fernet() -> Fernet:
    import os
    rahasia = os.environ.get("SUPERSET_SECRET_KEY") or ""
    if not rahasia:
        from flask import current_app
        rahasia = current_app.config["SECRET_KEY"]
    kunci = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"aldx-ai-kunci", info=b"api-key").derive(rahasia.encode())
    return Fernet(base64.urlsafe_b64encode(kunci))


def pastikan_tabel() -> None:
    _meta.create_all(bind=_engine(), checkfirst=True)


def semua() -> dict[str, str]:
    """{nama variabel: key} yang tersimpan di aplikasi. Galat database -> {} (asisten tetap jalan)."""
    global _tembolok
    with _kunci:
        if _tembolok and time.monotonic() - _tembolok[0] < UMUR_DETIK:
            return _tembolok[1]
    hasil: dict[str, str] = {}
    try:
        pastikan_tabel()
        f = _fernet()
        with _engine().connect() as c:
            for r in c.execute(select(KUNCI.c.nama, KUNCI.c.nilai)):
                try:
                    hasil[r.nama] = f.decrypt(r.nilai.encode()).decode()
                except InvalidToken:
                    log.warning("ALDx AI: key %s tidak bisa dibuka (SECRET_KEY berubah?) - isi ulang", r.nama)
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx AI: key tersimpan tidak terbaca (%s)", exc)
    with _kunci:
        _tembolok = (time.monotonic(), hasil)
    return hasil


def simpan(nama: str, nilai: str, oleh: str) -> None:
    """Simpan (atau hapus bila nilai kosong) satu key."""
    global _tembolok
    nilai = (nilai or "").strip()
    pastikan_tabel()
    with _engine().begin() as c:
        c.execute(delete(KUNCI).where(KUNCI.c.nama == nama))
        if nilai:
            c.execute(insert(KUNCI).values(nama=nama, nilai=_fernet().encrypt(nilai.encode()).decode(),
                                           diubah=datetime.now(), oleh=oleh[:128]))
    with _kunci:
        _tembolok = None


def samar(nilai: str) -> str:
    """Tampilan aman: ••••abcd."""
    return f"••••{nilai[-4:]}" if len(nilai) >= 8 else "••••"
