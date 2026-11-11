"""Skema terpilih per koneksi: hanya skema ini yang tampil di Dataset, SQL Lab, Kueri Visual, Studio.

Disimpan di extra koneksi:  {"sps_skema": ["genapp", "iku"]}   (kosong / tidak ada = semua skema)
Diatur di Data › Hubungkan data (saat menyimpan koneksi, atau tombol "Atur skema" di Koneksi tersimpan).

Database besar (mis. Oracle perusahaan) punya ratusan skema milik pengguna lain; tanpa pilihan ini daftar skema
memenuhi layar dan pengguna mudah salah memilih (tabel "tidak ditemukan").
"""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)
KUNCI = "sps_skema"


def _extra(database) -> dict:
    try:
        return json.loads(database.extra or "{}")
    except ValueError:
        return {}


def pilihan(database) -> list[str]:
    """Skema yang dipilih admin untuk koneksi ini (kosong = semua)."""
    return [str(s) for s in (_extra(database).get(KUNCI) or []) if str(s).strip()]


def bawaan(database) -> str | None:
    """Skema yang dipilih otomatis: pilihan pertama, atau skema bawaan login koneksi."""
    if p := pilihan(database):
        return p[0]
    try:
        return database.get_default_schema(None)
    except Exception:  # noqa: BLE001 - database tidak terjangkau: biarkan pengguna memilih
        return None


def batasi(database, skema: set[str]) -> set[str]:
    """Saring daftar skema dengan pilihan (huruf besar/kecil tidak dibedakan)."""
    p = {s.lower() for s in pilihan(database)}
    return {s for s in skema if s.lower() in p} if p else skema


def simpan(database, skema: list[str]) -> list[str]:
    """Simpan pilihan skema ke extra koneksi."""
    from superset import db
    extra = _extra(database)
    bersih = sorted({str(s).strip() for s in skema if str(s).strip()})
    if bersih:
        extra[KUNCI] = bersih
    else:
        extra.pop(KUNCI, None)
    database.extra = json.dumps(extra)
    db.session.commit()
    return bersih
