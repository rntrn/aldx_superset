"""Daftar periksa "Siapkan ALDx" di Beranda (khusus Admin): langkah sesudah instalasi.

GET /app/api/persiapan -> {langkah: [{id, selesai, ...}], selesai, total}
Setiap pemeriksaan berdiri sendiri: bila satu gagal dibaca, langkah itu dianggap belum selesai.
"""

from __future__ import annotations

import logging

from flask import jsonify

log = logging.getLogger(__name__)


def _aman(fungsi) -> bool:
    try:
        return bool(fungsi())
    except Exception:  # noqa: BLE001
        log.debug("ALDx persiapan: pemeriksaan gagal", exc_info=True)
        return False


def _ada_ai() -> bool:
    from sps_ai import pengaturan
    return bool(pengaturan.muat().model)


def _ada_data() -> bool:
    """Ada dataset selain data latihan bawaan."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    return db.session.query(SqlaTable.id).filter(~SqlaTable.table_name.like("latihan%")).limit(1).count() > 0


def _ada_pengguna() -> bool:
    from superset import security_manager as sm
    return sm.get_session.query(sm.user_model).count() > 1


def _ada_identitas() -> bool:
    from sps_identitas import penyimpanan
    return penyimpanan.ada_isian()


def _ada_cadangan() -> bool:
    from sps_server import monitor
    c = monitor.cadangan().get("cadangan") or {}
    return bool(c.get("waktu")) and c.get("umur_jam", 999) < 72


def api_persiapan():
    from superset import security_manager as sm
    if not sm.is_admin():
        return jsonify(langkah=[], selesai=0, total=0)
    langkah = [
        {"id": "ai", "selesai": _aman(_ada_ai)},
        {"id": "data", "selesai": _aman(_ada_data)},
        {"id": "pengguna", "selesai": _aman(_ada_pengguna)},
        {"id": "identitas", "selesai": _aman(_ada_identitas)},
        {"id": "cadangan", "selesai": _aman(_ada_cadangan)},
    ]
    return jsonify(langkah=langkah, selesai=sum(x["selesai"] for x in langkah), total=len(langkah))
