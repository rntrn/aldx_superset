"""Security manager Superset proyek ALDx: login LDAP / Active Directory (opsional) + akun lokal.

Superset memanggil `auth_user_ldap()` setiap ada yang login (AUTH_TYPE = AUTH_LDAP).
Fungsi bawaannya butuh paket python-ldap (harus dikompilasi, tidak bisa
dipasang offline), jadi di sini diganti memakai sps_ldap (ldap3).

Alur login:
    username ada di AUTH_LOCAL_USERS  -> cek password di database Superset
    selain itu                        -> cek ke Active Directory (sps_ldap)
        - pertama kali login: user dibuat otomatis dengan role LDAP_DEFAULT_ROLE
        - username di LDAP_ADMIN_USERS: dipastikan punya role Admin
        - username di SPS_SUPERADMIN_USERS: dipastikan punya role Admin + Superadmin
        - bila profil diaktifkan di akses.yaml: profil pengguna diambil dari database perusahaan
          -> role sesuai aturan (lihat sps_akses.py; hak akses DATA diterapkan lewat RLS)

Penguncian akun (sps_kunci): salah password berulang -> akun dikunci sementara, lokal maupun LDAP.
Hak minimum: menu admin ALDx & Superset tidak pernah diberikan ke role bawaan Gamma/Alpha oleh
`superset init` (ADMIN_ONLY_VIEW_MENUS, ALPHA_ONLY_VIEW_MENUS, SPS_ADMIN_ONLY_PMVS di bawah).
"""

from __future__ import annotations

import logging
import os

from superset.security import SupersetSecurityManager

import sps_akses
import sps_kunci
import sps_ldap

log = logging.getLogger(__name__)

NAME_MAX_LENGTH = 64  # batas kolom first_name/last_name di tabel ab_user
# Role dasar yang dimiliki semua pengguna login LDAP. Diatur SPS_ROLE_PENGGUNA di .env.
ROLE_PENGGUNA = os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna"


def _env_list(name: str, default: str = "") -> set[str]:
    """Baca variabel .env berisi daftar dipisah koma menjadi set."""
    return {item.strip() for item in os.environ.get(name, default).split(",") if item.strip()}


def _tolak_terkunci(username: str) -> bool:
    """True (dan beri pesan di halaman login) bila akun sedang dikunci."""
    sampai = sps_kunci.terkunci_sampai(username)
    if sampai is None:
        return False
    from flask import flash
    flash(sps_kunci.pesan(sampai), "warning")
    log.info("ALDx login %s: DITOLAK (akun dikunci sampai %s)", username, sampai)
    return True


class SpsSecurityManager(SupersetSecurityManager):
    """SupersetSecurityManager + login LDAP berbasis ldap3 + penguncian akun + hak minimum."""

    # Menu & izin yang hanya untuk Admin (tidak diberikan ke Gamma/Alpha oleh `superset init`).
    ADMIN_ONLY_VIEW_MENUS = SupersetSecurityManager.ADMIN_ONLY_VIEW_MENUS | {
        "Pusat Kendali Server", "Action Log", "Plugins", "DynamicPlugin", "Themes", "RowLevelSecurity",
    }
    # Koneksi database: untuk Alpha (analis) ke atas, bukan pengguna biasa.
    ALPHA_ONLY_VIEW_MENUS = SupersetSecurityManager.ALPHA_ONLY_VIEW_MENUS | {"Databases"}
    SPS_ADMIN_ONLY_PMVS = {("can_write", "Theme"), ("can_export", "Theme")}

    # Role pendamping wajib (sama dengan peta peran installer, sps_pengguna.PERAN):
    #   Superadmin            -> + Admin  (Superadmin = Admin + pengaturan vital)
    #   role dasar (Pengguna) -> + Gamma  (izin dasar Superset: menu, dashboard, chart)
    # Akun yang dibuat lewat Kelola > Pengguna kadang hanya diberi satu role: tanpa pendamping, API menu
    # menolak (403) sehingga sidebar kosong & tombol Asisten AI hilang. Dilengkapi otomatis saat dimuat
    # (pemeriksaan himpunan nama role di memori; database hanya ditulis bila memang ada yang kurang).
    def load_user(self, user_id):
        user = super().load_user(user_id)
        if user is not None:
            try:
                self.lengkapi_role(user)
            except Exception:  # noqa: BLE001 - tidak boleh menggagalkan login
                from superset import db
                db.session.rollback()
                log.exception("ALDx: gagal melengkapi role %s", getattr(user, "username", user_id))
        return user

    def lengkapi_role(self, user) -> list[str]:
        """Tambahkan role pendamping yang wajib. Kembalikan nama role yang ditambahkan."""
        nama = {r.name for r in user.roles}
        tambah = []
        if "Superadmin" in nama and self.auth_role_admin not in nama:
            tambah.append(self.auth_role_admin)
        if ROLE_PENGGUNA in nama and not nama & {"Gamma", "Alpha", self.auth_role_admin, *tambah}:
            tambah.append("Gamma")
        role = [r for r in (self.find_role(n) for n in tambah) if r is not None]
        if role:
            from superset import db
            user.roles.extend(role)
            db.session.commit()                    # FAB versi ini tidak punya self.get_session
            log.warning("ALDx: role %s dilengkapi dengan %s", user.username, [r.name for r in role])
        return [r.name for r in role]

    def _is_admin_only(self, pvm) -> bool:
        if (pvm.permission.name, pvm.view_menu.name) in self.SPS_ADMIN_ONLY_PMVS:
            return True
        return super()._is_admin_only(pvm)

    def auth_user_db(self, username, password):
        """Login akun lokal (email). Dipanggil langsung oleh Superset (tanpa LDAP) atau dari auth_user_ldap."""
        username = (username or "").strip()
        if not username or not password or _tolak_terkunci(username):
            return None
        user = super().auth_user_db(username, password)
        if user:
            sps_kunci.berhasil(username)
        else:
            sampai = sps_kunci.gagal(username, "lokal")
            if sampai:
                from flask import flash
                flash(sps_kunci.pesan(sampai), "warning")
        return user

    def auth_user_ldap(self, username, password):
        username = (username or "").strip()
        if not username or not password:
            return None

        # Akun lokal: login berupa email (dibuat installer / Kelola > Pengguna) atau tercantum di AUTH_LOCAL_USERS.
        # Username jaringan (tanpa "@") selalu diperiksa ke LDAP. Jadi Superadmin tetap bisa masuk walau LDAP mati.
        if "@" in username or username in _env_list("AUTH_LOCAL_USERS", "admin"):
            user = self.auth_user_db(username, password)
            log.info("ALDx login lokal %s: %s", username, "BERHASIL" if user else "GAGAL")
            if user:
                self._ensure_admin_role(user)
            return user

        if _tolak_terkunci(username):
            return None
        user = self.find_user(username=username)
        if user and not user.is_active:
            log.info("ALDx login LDAP %s: GAGAL (user dinonaktifkan)", username)
            return None

        ldap_user = sps_ldap.authenticate(username, password)
        if ldap_user is None:
            log.info("ALDx login LDAP %s: GAGAL (ditolak AD / tidak terhubung)", username)
            if user:
                self.update_user_auth_stat(user, success=False)
            sampai = sps_kunci.gagal(username, "LDAP")
            if sampai:
                from flask import flash
                flash(sps_kunci.pesan(sampai), "warning")
            return None

        user = user or self._register_ldap_user(ldap_user)
        if user is None:
            return None

        self._ensure_admin_role(user)
        self._sync_akses(user)
        self.update_user_auth_stat(user, success=True)
        sps_kunci.berhasil(username)
        log.info("ALDx login LDAP %s: BERHASIL", username)
        return user

    def get_user_menu_access(self, menu_names=None):
        """Menu yang boleh dibuka + item & kategori susunan SPS (lihat sps_menu.py)."""
        import sps_menu
        nama = None if menu_names is None else list({*menu_names, *sps_menu.nama_izin_dasar()})
        return sps_menu.perluas_izin(super().get_user_menu_access(nama), admin=self.is_admin())

    def get_schemas_accessible_by_user(self, database, catalog, schemas, hierarchical=True):
        """Hanya skema yang dipilih untuk koneksi itu (Hubungkan data › Atur skema; lihat sps_skema.py)."""
        import sps_skema
        hasil = super().get_schemas_accessible_by_user(database, catalog, schemas, hierarchical)
        return sps_skema.batasi(database, set(hasil))

    def get_rls_cache_key(self, datasource) -> list[str]:
        """Tambahkan sidik lingkup akses user ke kunci cache (cegah bocor antar-pegawai).

        Kunci bawaan memakai teks RLS mentah yang sama untuk semua user. Aturan yang memakai
        current_username() (data impor .aldx) diberi nama pengguna agar cache tidak dibagi.
        """
        kunci = super().get_rls_cache_key(datasource)
        sql = getattr(datasource, "sql", "") or ""
        if any("sps_" in k for k in kunci) or "sps_akses" in sql or "sps_profil" in sql:
            kunci.append("sps-akses:" + sps_akses.sidik_akses())
        if any("current_username" in k for k in kunci):      # aturan per pengguna (mis. data impor .aldx)
            from flask import g
            kunci.append("pengguna:" + str(getattr(getattr(g, "user", None), "username", "")))
        return kunci

    def _register_ldap_user(self, ldap_user: sps_ldap.LdapUser):
        """Buat user Superset untuk pegawai yang baru pertama kali login."""
        role_name = os.environ.get("LDAP_DEFAULT_ROLE", "Gamma")
        role = self.find_role(role_name)
        if role is None:
            log.error("Role '%s' (LDAP_DEFAULT_ROLE) tidak ada di Superset", role_name)
            return None

        first_name, _, last_name = ldap_user.display_name.partition(" ")
        user = self.add_user(
            username=ldap_user.username,
            first_name=first_name[:NAME_MAX_LENGTH],
            last_name=(last_name or "-")[:NAME_MAX_LENGTH],
            email=ldap_user.email or f"{ldap_user.username}@email.notfound",
            role=role,
        )
        if user:
            log.info("User LDAP baru terdaftar: %s (nomor pegawai %s)", ldap_user.username, ldap_user.nomor_pegawai or "-")
        else:
            log.error("Gagal mendaftarkan user LDAP %s (email bentrok?)", ldap_user.username)
        return user

    def _ensure_admin_role(self, user) -> None:
        """Beri role Admin bila username di LDAP_ADMIN_USERS; Admin + Superadmin bila di SPS_SUPERADMIN_USERS."""
        import sps_superadmin
        if sps_superadmin.pastikan(user):
            self.update_user(user)
            log.info("ALDx login %s: dipastikan Admin + Superadmin (SPS_SUPERADMIN_USERS)", user.username)
            return
        if user.username not in _env_list("LDAP_ADMIN_USERS"):
            return
        admin_role = self.find_role(self.auth_role_admin)
        if admin_role and admin_role not in user.roles:
            user.roles.append(admin_role)
            self.update_user(user)

    def _sync_akses(self, user) -> None:
        """Perbarui profil & role; bila gagal, login TETAP jalan (data tetap dibatasi RLS)."""
        try:
            self._sync_akses_inti(user)
        except Exception:  # noqa: BLE001
            log.exception("ALDx akses %s: GAGAL sinkron hak akses, role tidak diubah", user.username)
            self.session.rollback()

    def _sync_akses_inti(self, user) -> None:
        profil = sps_akses.sinkron_profil(user.username)
        keputusan = sps_akses.putuskan(profil)
        nama_role = {ROLE_PENGGUNA, *keputusan.peran}
        awalan = sps_akses.awalan_peran()

        user.roles = [r for r in user.roles if not r.name.startswith(awalan)]
        user.roles += [self.add_role(nama) for nama in sorted(nama_role)]
        self.update_user(user)
        log.info("ALDx akses %s: aturan '%s', lingkup %s, role %s",
                 user.username, keputusan.aturan, keputusan.lingkup, sorted(nama_role))


def rapikan_role_bawaan() -> list[str]:
    """Cabut izin khusus Admin dari Gamma dan izin khusus Alpha dari Gamma (instalasi yang sudah ada).

    `superset init` sudah memakai aturan di SpsSecurityManager; fungsi ini untuk instalasi lama yang hanya
    menjalankan build-dashboards. Dipanggil sps_build_dashboards. Kembalikan ringkasan.
    """
    from superset import db, security_manager as sm
    hasil = []
    for nama, tolak in (("Gamma", lambda pv: sm._is_admin_only(pv) or sm._is_alpha_only(pv)),
                        ("Alpha", sm._is_admin_only)):
        role = sm.find_role(nama)
        if role is None:
            continue
        cabut = [pv for pv in role.permissions if tolak(pv)]
        for pv in cabut:
            role.permissions.remove(pv)
        hasil.append(f"role {nama}: {len(cabut)} izin khusus admin/analis dicabut")
    db.session.commit()
    return hasil
