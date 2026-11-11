"""Role Superadmin: satu tingkat di atas Admin.

    Superadmin  = Admin + pengaturan vital (Pengaturan server, Batas data, Hak akses, peran AI /hw-engineer)
    Admin       = kelola pengguna, koneksi, ekstrak, identitas & tema, lihat status & riwayat

Cara kerja:
    - Role "Superadmin" adalah PENANDA; izin Superset tetap datang dari role Admin yang juga dimiliki
      pengguna itu. siapkan() memastikan setiap Superadmin juga Admin.
    - Akun ADMIN_USERNAME (.env, akun admin instalasi) dan semua username di SPS_SUPERADMIN_USERS
      (.env, pisah koma; mis. username jaringan LDAP) otomatis menjadi Superadmin: saat build-dashboards / upgrade
      dan setiap kali orang itu login (pastikan()).
    - Pengaman terkunci: bila TIDAK ADA satu pun pengguna aktif ber-role Superadmin, semua Admin
      diperlakukan sebagai Superadmin, sehingga pengaturan vital tidak pernah hilang aksesnya.
    - Admin biasa tidak bisa memberi / mencabut / mengubah role Superadmin atau akun Superadmin
      (lihat pasang(): penjaga API keamanan /api/v1/security/...).
"""

from __future__ import annotations

import logging
import os
import re
from functools import wraps

log = logging.getLogger(__name__)

ROLE = "Superadmin"
API_KEAMANAN = re.compile(r"^/api/v1/security/(users|roles|groups)(?:/(\d+))?(?:/(\w+))?/?$")


def _role_superadmin():
    from superset import security_manager as sm
    return sm.find_role(ROLE)


def _semua_role(user) -> list:
    """Role langsung + role dari grup (FAB groups)."""
    roles = list(getattr(user, "roles", []) or [])
    for grup in getattr(user, "groups", []) or []:
        roles += list(getattr(grup, "roles", []) or [])
    return roles


def _ada_superadmin_aktif(role) -> bool:
    from superset import db, security_manager as sm
    return db.session.query(sm.user_model).filter(
        sm.user_model.roles.contains(role), sm.user_model.active.is_(True)).first() is not None


def adalah(user=None) -> bool:
    """True bila user (bawaan: user yang login) Superadmin."""
    from flask_login import current_user
    from superset import security_manager as sm
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    nama = {r.name for r in _semua_role(user)}
    if ROLE in nama:
        return True
    if sm.auth_role_admin not in nama:
        return False
    role = _role_superadmin()
    return role is None or not _ada_superadmin_aktif(role)          # pengaman terkunci


def khusus(halaman: bool = False):
    """Dekorator view Flask: hanya Superadmin (403 untuk yang lain)."""
    def dekor(fungsi):
        @wraps(fungsi)
        def bungkus(*args, **kwargs):
            from flask import jsonify
            if not adalah():
                pesan = "Pengaturan ini khusus Superadmin."
                if halaman:
                    from sps_tolak import halaman_tolak
                    return halaman_tolak(pesan + " Hubungi Superadmin bila Anda membutuhkannya.")
                return jsonify(error=pesan), 403
            return fungsi(*args, **kwargs)
        return bungkus
    return dekor


# --- Penjaga: Admin biasa tidak boleh menyentuh Superadmin ------------------------------------------
def _tolak_bila_menyentuh(role_id: int) -> str | None:
    from flask import request
    from superset import db, security_manager as sm
    m = API_KEAMANAN.match(request.path)
    if not m:
        return None
    jenis, pk = m.group(1), m.group(2)
    body = request.get_json(silent=True) or {}
    if role_id in [int(x) for x in (body.get("roles") or []) if str(x).isdigit()]:
        return "Hanya Superadmin yang boleh memberi role Superadmin."
    if not pk:
        return None
    pk = int(pk)
    if jenis == "roles" and pk == role_id:
        return "Role Superadmin hanya bisa diubah oleh Superadmin."
    if jenis == "users":
        target = db.session.get(sm.user_model, pk)
        if target is not None and ROLE in {r.name for r in _semua_role(target)}:
            return "Akun Superadmin hanya bisa diubah oleh Superadmin."
    if jenis == "groups":
        grup = db.session.get(sm.group_model, pk) if getattr(sm, "group_model", None) else None
        if grup is not None and any(r.id == role_id for r in grup.roles):
            return "Grup berisi role Superadmin hanya bisa diubah oleh Superadmin."
    return None


def pasang(app) -> None:
    """FLASK_APP_MUTATOR: penjaga API keamanan."""
    from flask import jsonify, request

    @app.before_request
    def _jaga_superadmin():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE") or not request.path.startswith("/api/v1/security/"):
            return None
        try:
            role = _role_superadmin()
            if role is None or adalah():
                return None
            pesan = _tolak_bila_menyentuh(role.id)
        except Exception:  # noqa: BLE001 - penjaga gagal = tolak (aman), bukan izinkan
            log.exception("ALDx superadmin: penjaga gagal")
            pesan = "Pemeriksaan hak Superadmin gagal; coba lagi."
        if pesan:
            log.warning("ALDx superadmin: ditolak %s %s", request.method, request.path)
            return jsonify(message=pesan), 403
        return None


def daftar_otomatis() -> list[str]:
    """Username yang otomatis Superadmin: ADMIN_USERNAME + SPS_SUPERADMIN_USERS."""
    nama = [os.environ.get("ADMIN_USERNAME", "admin")]
    nama += [x.strip() for x in os.environ.get("SPS_SUPERADMIN_USERS", "").split(",") if x.strip()]
    return list(dict.fromkeys(nama))


def pastikan(user) -> bool:
    """Beri role Admin + Superadmin bila username ada di daftar_otomatis(). True bila ada perubahan."""
    from superset import security_manager as sm
    if user is None or user.username not in daftar_otomatis():
        return False
    berubah = False
    if user.last_name == "SPS":                # nama lama akun admin instalasi ("Admin SPS") -> "Admin ALDx"
        user.last_name, berubah = "ALDx", True
    for role in (sm.find_role(sm.auth_role_admin), sm.add_role(ROLE)):
        if role is not None and role not in user.roles:
            user.roles.append(role)
            berubah = True
    return berubah


def siapkan() -> list[str]:
    """build-dashboards: buat role, jadikan daftar_otomatis() Superadmin, pastikan Superadmin juga Admin."""
    from superset import db, security_manager as sm
    role = sm.add_role(ROLE)
    admin = sm.find_role(sm.auth_role_admin)
    hasil = [f"role '{ROLE}'"]
    for nama in daftar_otomatis():
        if pastikan(sm.find_user(username=nama)):
            hasil.append(f"'{nama}' menjadi {ROLE}")
    for u in db.session.query(sm.user_model).filter(sm.user_model.roles.contains(role)):
        if admin is not None and admin not in u.roles:
            u.roles.append(admin)
    db.session.commit()
    return hasil
