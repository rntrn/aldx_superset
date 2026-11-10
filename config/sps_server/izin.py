"""Hak akses tingkat KEMAMPUAN (apa yang boleh dilakukan) per role.

Hak akses DATA (baris mana yang terlihat) tetap diatur config/akses.yaml (RLS).

Kemampuan = kumpulan permission Superset yang selalu diberikan bersama.
Role bawaan Superset (Admin, Alpha, Gamma, sql_lab, Public) hanya ditampilkan:
isinya dikembalikan ke semula setiap `superset init`, jadi ubahlah role DJP
atau role buatan sendiri.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime

from sps_server import penyimpanan

log = logging.getLogger(__name__)

ROLE_BAWAAN = {"Admin", "Alpha", "Gamma", "sql_lab", "Public"}


@dataclass(frozen=True)
class Kemampuan:
    id: str
    label: str
    istilah: str
    izin: tuple[tuple[str, str], ...]
    catatan: str = ""
    diatur_di: str = ""          # bila diisi: kolom hanya-baca, diatur di tempat lain


KEMAMPUAN = [
    Kemampuan("lihat", "Lihat dashboard", "", (("can_read", "Dashboard"),)),
    Kemampuan("unduh", "Unduh data chart", "",
              (("can_csv", "Superset"), ("can_export", "Chart"))),
    Kemampuan("chart", "Buat & simpan chart", "", (("can_write", "Chart"),)),
    Kemampuan("dashboard", "Buat & ubah dashboard", "", (("can_write", "Dashboard"),)),
    Kemampuan("ekspor", "Ekspor/impor dashboard", "", (("can_export", "Dashboard"),)),
    Kemampuan("dataset", "Kelola dataset", "", (("can_write", "Dataset"),),
              "Dataset baru TIDAK otomatis punya filter hak akses; berikan dengan hati-hati."),
    Kemampuan("sqllab", "SQL Lab", "",
              (("menu_access", "SQL Lab"), ("menu_access", "SQL Editor"), ("can_sqllab", "Superset"),
               ("can_execute_sql_query", "SQLLab"), ("can_read", "SQLLab"), ("can_get_results", "SQLLab"),
               ("can_format_sql", "SQLLab"), ("can_export_csv", "SQLLab"),
               ("can_sqllab_history", "Superset")),
              "Butuh juga akses database; RLS hanya berlaku pada tabel yang terdaftar sebagai dataset."),
    Kemampuan("ai", "Asisten AI", "", (("menu_access", "Asisten AI"),),
              diatur_di="config/ai.yaml (peran_boleh)"),
    Kemampuan("upload", "Upload Excel/CSV", "", (("can_upload", "Database"),),
              diatur_di="Pengaturan → Upload Excel / CSV"),
]
PETA = {k.id: k for k in KEMAMPUAN}


def _sm():
    from superset import security_manager
    return security_manager


def _punya(role, izin: tuple[tuple[str, str], ...]) -> bool:
    milik = {(p.permission.name, p.view_menu.name) for p in role.permissions}
    return all(i in milik for i in izin)


IZIN_SEMUA_DATA = {("all_datasource_access", "all_datasource_access"), ("all_database_access", "all_database_access")}


def peringatan_akses() -> list[dict]:
    """K10: pengguna aktif BUKAN Admin yang bisa melihat SEMUA data (role Alpha atau izin all_*_access).

    Akun seperti ini melewati batas hak akses per sumber data; RLS tetap berlaku. Di produksi daftar ini
    sebaiknya kosong.
    """
    from superset import db
    from flask_appbuilder.security.sqla.models import User
    hasil = []
    for u in db.session.query(User).filter(User.active.is_(True)):
        nama_role = {r.name for r in u.roles}
        if "Admin" in nama_role:
            continue
        sebab = sorted({r.name for r in u.roles if r.name == "Alpha" or any(
            (pv.permission.name, pv.view_menu.name) in IZIN_SEMUA_DATA for pv in r.permissions)})
        if sebab:
            hasil.append({"username": u.username, "nama": f"{u.first_name or ''} {u.last_name or ''}".strip(),
                          "role": sebab})
    return hasil


def matriks() -> dict:
    sm = _sm()
    roles = sorted(sm.get_all_roles(), key=lambda r: (r.name not in ROLE_BAWAAN, r.name))
    return {
        "peringatan": peringatan_akses(),
        "kemampuan": [{"id": k.id, "label": k.label, "istilah": k.istilah, "catatan": k.catatan,
                       "diatur_di": k.diatur_di} for k in KEMAMPUAN],
        "role": [{"nama": r.name, "bawaan": r.name in ROLE_BAWAAN, "jumlah_user": len(r.user or []),
                  # Superadmin selalu dipasang bersama Admin, jadi kemampuannya = Admin.
                  "punya": {k.id: (r.name in ("Admin", "Superadmin") or _punya(r, k.izin)) for k in KEMAMPUAN}}
                 for r in roles],
    }


def _ubah_izin(role, izin: tuple[tuple[str, str], ...], aktif: bool) -> None:
    sm = _sm()
    for perm, view in izin:
        pv = sm.add_permission_view_menu(perm, view)          # buat bila belum ada
        if aktif and pv not in role.permissions:
            sm.add_permission_role(role, pv)
        elif not aktif and pv in role.permissions:
            sm.del_permission_role(role, pv)


def ubah(nama_role: str, kemampuan_id: str, aktif: bool, oleh: str) -> None:
    k = PETA.get(kemampuan_id)
    if k is None:
        raise ValueError(f"Kemampuan '{kemampuan_id}' tidak dikenal.")
    if k.diatur_di:
        raise ValueError(f"'{k.label}' diatur di {k.diatur_di}.")
    if nama_role in ROLE_BAWAAN:
        raise ValueError(f"Role bawaan '{nama_role}' dikembalikan otomatis oleh superset init; "
                         "ubah role DJP atau buat role baru.")
    role = _sm().find_role(nama_role)
    if role is None:
        raise ValueError(f"Role '{nama_role}' tidak ada.")
    sebelum = _punya(role, k.izin)
    _ubah_izin(role, k.izin, aktif)
    _catat(oleh, f"izin:{nama_role}:{k.id}", sebelum, aktif)


def _catat(oleh: str, kunci: str, lama, baru) -> None:
    with penyimpanan.engine().begin() as c:
        c.execute(penyimpanan.RIWAYAT.insert().values(
            waktu=datetime.now(), oleh=oleh, kunci=kunci, lama=json.dumps(lama), baru=json.dumps(baru)))


# --- Upload Excel/CSV -----------------------------------------------------------------------
def siapkan_upload(atur: dict) -> str:
    """Koneksi ALDx Engine boleh menerima upload & izin upload sesuai pengaturan. Kembalikan ringkasan."""
    from superset import db
    from sps_engine import klien as K
    from sps_engine.ekstrak import database_engine

    database = database_engine()
    database.allow_file_upload = bool(atur["upload.aktif"])
    extra = json.loads(database.extra or "{}")
    extra["schemas_allowed_for_file_upload"] = [K.nama_db()]
    database.extra = json.dumps(extra)
    db.session.commit()

    sm = _sm()
    boleh = set(atur["upload.peran"]) if atur["upload.aktif"] else set()
    izin = (("can_upload", "Database"), ("database_access", database.perm))
    for role in sm.get_all_roles():
        if role.name in ROLE_BAWAAN:
            continue
        _ubah_izin(role, izin, role.name in boleh)
    db.session.commit()
    return f"database '{database.database_name}', role upload: {sorted(boleh) or '-'}"


def terapkan_sqllab_async(aktif: bool) -> int:
    """Nyalakan/matikan eksekusi async SQL Lab di semua koneksi. Kembalikan jumlah koneksi."""
    from superset import db
    from superset.models.core import Database

    semua = db.session.query(Database).all()
    for d in semua:
        d.allow_run_async = aktif
    db.session.commit()
    return len(semua)
