"""Konfigurasi Superset proyek SPS.

File ini dibaca Superset saat start (lewat SUPERSET_CONFIG_PATH).
Semua nilai rahasia diambil dari environment (.env), bukan ditulis di sini.

Bagian:
    1. Helper   - membaca environment variable dengan pesan error yang jelas
    2. Keamanan - SECRET_KEY
    3. Metadata - koneksi ke PostgreSQL container metadb (database sps_superset)
    4. Login    - LDAP DJP (sps_security.py + sps_ldap.py)
    5. Driver   - Oracle lewat oracledb (pengganti cx_Oracle)
    6. Tampilan - identitas & tema (diatur di Pusat Kendali; sps_identitas/)
    7. Fitur    - feature flag + fungsi template SQL (sps_jinja.py, sps_akses.py)
    8. Umum     - format angka Indonesia
    9. Server   - cache, backgrounder, batas baris, timeout, upload (Pusat Kendali Server,
                  config/sps_server/; nilainya diatur dari halaman /pusat-kendali/)
"""

import logging
import os
import sys

import oracledb

from flask_appbuilder.security.manager import AUTH_DB, AUTH_LDAP
from sqlalchemy.dialects.mysql.base import MySQLDialect

import sps_identitas
import sps_ldap
from sps_akses import sps_akses, sps_profil, sps_sidik
from sps_jinja import sps_periode
from sps_security import SpsSecurityManager
from sps_server import konfig as sps_server_konfig
from sps_server.lingkungan import uri_metadata, wajib
from sps_studio.lembar import RUNTUN, SKEMA_LAMA, SKEMA_RUNTUN, SKEMA_WARNA, WARNA


# --- 1. Helper ---------------------------------------------------------------
require_env = wajib   # ambil environment variable; hentikan start bila kosong (sps_server/lingkungan.py)


# --- 2. Keamanan -------------------------------------------------------------
SECRET_KEY = require_env("SUPERSET_SECRET_KEY")


# --- 3. Metadata database (PostgreSQL, container metadb) ----------------------
# Driver: psycopg2 (dipasang di docker/Dockerfile). Perbandingan pilihan: docs/02.
# URI disusun di sps_server/lingkungan.py (dipakai bersama peluncur node & skrip terapkan).
SQLALCHEMY_DATABASE_URI = uri_metadata()


def _disable_mariadb_sequences() -> None:
    """Paksa MariaDB memakai AUTO_INCREMENT, bukan SEQUENCE.

    Metadata kini PostgreSQL; ini tetap perlu untuk SUMBER DATA MariaDB dan
    untuk membaca metadata lama saat pindah (config/sps_pindah_meta.py).

    SQLAlchemy 1.4 menganggap MariaDB >= 10.3 mendukung SEQUENCE dan mengirim
    `CREATE SEQUENCE ... NO CYCLE`, yang ditolak MariaDB (error 1064).
    Dengan ini MariaDB diperlakukan sama seperti MySQL biasa.
    """
    original_initialize = MySQLDialect.initialize

    def initialize(self, connection):
        original_initialize(self, connection)
        self.supports_sequences = False

    MySQLDialect.initialize = initialize


_disable_mariadb_sequences()


# --- 4. Login: LDAP / Active Directory (opsional) atau akun lokal -------------
# LDAP_SERVERS terisi  -> login LDAP (sps_ldap.py) + akun lokal darurat (AUTH_LOCAL_USERS).
# LDAP_SERVERS kosong  -> semua akun lokal: dibuat Admin di Settings > List Users (dengan password).
# AUTH_LDAP_SERVER wajib ada untuk Flask-AppBuilder, meski koneksi sebenarnya oleh sps_ldap.py.
AUTH_TYPE = AUTH_LDAP if sps_ldap.aktif() else AUTH_DB
AUTH_LDAP_SERVER = (sps_ldap.LdapSettings.from_env().servers or ("ldap://localhost",))[0]
AUTH_USER_REGISTRATION = False  # pendaftaran ditangani sps_security.py
CUSTOM_SECURITY_MANAGER = SpsSecurityManager


# --- 5. Driver Oracle ---------------------------------------------------------
ORACLE_CLIENT_DIR = "/opt/oracle/instantclient"   # diisi docker/oracle/install-instantclient.sh


def _use_oracledb_as_cx_oracle() -> None:
    """Pakai oracledb sebagai cx_Oracle, dalam mode thick bila Instant Client ada.

    SQLAlchemy 1.4 (dipakai Superset 6.1) hanya mengenal driver cx_Oracle.
    oracledb adalah penerus resminya dengan API yang sama, jadi cukup
    "didaftarkan" dengan nama cx_Oracle. URI tetap: oracle://user:pass@host:port/?service_name=X

    Mode:
    - thick : bila Instant Client terpasang di ORACLE_CLIENT_DIR. Wajib untuk
              server Oracle < 12.1 (tanpa ini muncul error DPY-3010).
    - thin  : tanpa Instant Client. Hanya untuk Oracle 12.1 ke atas.
    """
    if os.path.isdir(ORACLE_CLIENT_DIR):
        try:
            oracledb.init_oracle_client()  # library ditemukan lewat ldconfig
        except oracledb.Error as exc:
            logging.getLogger(__name__).error("Oracle thick mode gagal, tetap thin: %s", exc)
    oracledb.version = "8.3.0"  # versi minimal yang diterima SQLAlchemy 1.4
    sys.modules["cx_Oracle"] = oracledb


_use_oracledb_as_cx_oracle()


# --- 6. Tampilan: identitas & tema ---------------------------------------------
# Nama aplikasi, perusahaan, logo, favicon, warna, huruf, hiasan & animasi DIATUR dari
# Pusat Kendali > Identitas & Tema (disimpan di database, berlaku tanpa restart).
# Di sini hanya token DASAR Superset 6.1; token identitas ditambahkan oleh sps_identitas.
# THEME_DEFAULT MENGGANTIKAN tema bawaan seluruhnya, jadi semua token bawaan ikut ditulis.
_TOKENS = {
    "brandLogoMargin": "14px 0",
    "brandLogoHeight": "28px",
    "brandSpinnerSvg": None,
    "colorWarning": "#F2B705",
    "colorError": "#e04355",
    "colorSuccess": "#5ac189",
    "colorInfo": "#66bcfe",
    # Font Plus Jakarta Sans (gratis, OFL) disimpan lokal di branding/fonts/ -> tanpa internet.
    "fontUrls": ["/static/assets/images/sps/fonts/fonts.css"],
    "fontFamilyCode": "'IBM Plex Mono', 'Courier New', monospace",
    "transitionTiming": 0.3,
    "brandIconMaxWidth": 37,
    "fontSizeXS": "8",
    "fontSizeXXL": "28",
    "fontWeightNormal": "400",
    "fontWeightLight": "300",
    "fontWeightStrong": "600",
    "fontWeightBold": "700",
    "colorEditorSelection": "#fff5cf",
}
# APP_NAME, APP_ICON, FAVICONS, LOGO_TARGET_PATH, THEME_DEFAULT, SPS_IDENTITAS (lihat sps_identitas).
globals().update(sps_identitas.tema_awal(_TOKENS))
# Mode gelap (THEME_DARK) diisi sps_identitas; pilihannya di menu akun cangkang (Terang / Gelap / Ikuti sistem).

# Bahasa halaman bawaan Superset (hanya bahasa yang punya terjemahan Superset). Bahasa Indonesia
# untuk cangkang & halaman ALDx ada di config/sps_app/static/bahasa/ (pilih lewat menu Bahasa di sidebar).
LANGUAGES = {"en": {"flag": "us", "name": "English"}, "ja": {"flag": "jp", "name": "日本語"}}

# Markdown dashboard boleh memakai style/class (untuk banner DJP).
HTML_SANITIZATION_SCHEMA_EXTENSIONS = {"attributes": {"*": ["style", "className"]}}


def _arahkan_halaman_depan(app) -> None:
    """'/' dan halaman Welcome bawaan diarahkan ke halaman depan pilihan admin (Identitas & Tema).

    Bila halaman depan berupa dashboard (/superset/dashboard/<slug>/) yang belum ada, mis. "beranda"
    profil DJP yang belum dibangun karena koneksinya belum dibuat, pengguna diarahkan ke daftar
    dashboard, bukan halaman 404.
    """
    import re
    import time

    from urllib.parse import quote

    from flask import redirect, request
    from flask_login import current_user

    cadangan = "/dashboard/list/"
    tembolok = {}                                   # slug -> (waktu periksa, ada?)

    def _dashboard_ada(slug: str) -> bool:
        waktu, ada = tembolok.get(slug, (0.0, False))
        if time.monotonic() - waktu > 60:          # periksa ulang tiap menit
            from superset import db
            from superset.models.dashboard import Dashboard
            ada = db.session.query(Dashboard.id).filter(Dashboard.slug == slug).first() is not None
            tembolok[slug] = (time.monotonic(), ada)
        return ada

    def _tujuan() -> str:
        tujuan = app.config["SPS_IDENTITAS"]["halaman_depan"]
        m = re.fullmatch(r"/superset/dashboard/([\w-]+)/?", tujuan)
        if m and not m.group(1).isdigit() and not _dashboard_ada(m.group(1)):
            return cadangan
        return tujuan

    @app.before_request
    def _halaman_depan():
        if not current_user.is_authenticated:
            return None
        if request.path in ("/", "/superset/welcome/"):
            tujuan = _tujuan()                      # semua halaman tampil di cangkang /app/ (sps_app)
            return redirect("/app/" if tujuan in (cadangan, "/app/") else "/app/?p=" + quote(tujuan, safe=""))
        depan = app.config["SPS_IDENTITAS"]["halaman_depan"]
        if request.path.rstrip("/") == depan.rstrip("/") and _tujuan() != depan:
            return redirect(cadangan)               # tautan logo ke dashboard depan yang belum ada
        return None


def _pasang_tambahan(app) -> None:
    """Dipanggil Superset saat start: identitas, halaman depan, Asisten AI, Pusat Kendali, Engine,
    Hubungkan data, Studio, Kueri Visual, susunan menu alur BI, penjaga Superadmin."""
    sps_identitas.daftarkan(app)
    _arahkan_halaman_depan(app)
    import sps_ai
    import sps_berkas
    import sps_filter_global
    import sps_ulasan
    import sps_app
    import sps_engine
    import sps_koneksi
    import sps_kueri
    import sps_menu
    import sps_server
    import sps_studio
    import sps_dialek
    import sps_superadmin
    import sps_audit
    import sps_versi
    sps_audit.pasang(app)                   # jejak audit + tabel penguncian akun
    sps_versi.daftarkan(app)                # riwayat versi dashboard
    import sps_ponsel
    sps_ponsel.daftarkan(app)               # tata letak ponsel per dashboard
    import sps_lihat_sebagai
    sps_lihat_sebagai.daftarkan(app)        # Lihat sebagai… (uji hak akses, khusus Admin)
    sps_dialek.pasang(app)                  # Oracle ROWNUM & tipe angka, batas chart berat
    sps_superadmin.pasang(app)
    sps_ai.daftarkan(app)
    sps_server.daftarkan(app)
    sps_engine.daftarkan(app)
    sps_koneksi.daftarkan(app)
    sps_studio.daftarkan(app)
    sps_kueri.daftarkan(app)
    sps_berkas.daftarkan(app)
    sps_filter_global.daftarkan(app)
    sps_ulasan.daftarkan(app)
    sps_menu.daftarkan(app)
    sps_app.daftarkan(app)
    import sps_panduan
    sps_panduan.daftarkan(app)              # /panduan/: dokumentasi docs/ di dalam aplikasi


FLASK_APP_MUTATOR = _pasang_tambahan


# --- 7. Feature flags --------------------------------------------------------
FEATURE_FLAGS = {
    "DASHBOARD_RBAC": True,              # akses dashboard diatur per role (DJP Pusat, dst.)
    "TAGGING_SYSTEM": True,              # beri tag pada chart/dashboard
    "ENABLE_TEMPLATE_PROCESSING": True,  # Jinja di SQL & RLS: {{ sps_akses() }}, {{ sps_periode() }}
    "RLS_IN_SQLLAB": True,               # aturan hak akses juga berlaku di SQL Lab
    "ALERT_REPORTS": True,               # Langganan laporan & peringatan (menu Dashboard & Story › Langganan)
}

# --- 7b. Email untuk langganan laporan (opsional, isi di .env) ---------------------------------
# Tanpa SMTP_HOST laporan tetap dijadwalkan tetapi TIDAK dikirim (mode uji: tercatat di log saja).
# Laporan chart berformat CSV / teks langsung jalan. Laporan bergambar (PNG/PDF dashboard) butuh peramban
# di image (lihat docs/26-langganan-versi-ponsel-lihat-sebagai.md).
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or 587)
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "1") == "1"
SMTP_SSL = os.environ.get("SMTP_SSL", "") == "1"
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_MAIL_FROM = os.environ.get("SMTP_MAIL_FROM", "") or SMTP_USER or "aldx@localhost"
EMAIL_NOTIFICATIONS = bool(SMTP_HOST)
ALERT_REPORTS_NOTIFICATION_DRY_RUN = not SMTP_HOST
EMAIL_REPORTS_SUBJECT_PREFIX = os.environ.get("SMTP_AWALAN_SUBJEK", "[ALDx] ")

# Fungsi tambahan yang bisa dipanggil di SQL dataset / aturan RLS:
#   sps_periode(...) - tahun & bulan dari filter dashboard   (sps_jinja.py)
#   sps_akses(...)   - kondisi hak akses user yang login      (sps_akses.py)
#   sps_profil(...)  - profil pegawai yang login (nip, kd_kanwil, ...)
#   sps_sidik()      - sidik lingkup akses user (RLS dataset ramalan Studio)
JINJA_CONTEXT_ADDONS = {"sps_periode": sps_periode, "sps_akses": sps_akses, "sps_profil": sps_profil,
                        "sps_sidik": sps_sidik}


# --- 8. Pengaturan umum ------------------------------------------------------
# Format angka gaya Indonesia: 1.234.567,89 dan Rp
D3_FORMAT = {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["Rp ", ""]}
# Nama bulan/hari di sumbu & info sorot chart dalam bahasa Indonesia (format tanggal 31/12/2026, jam 24).
D3_TIME_FORMAT = {
    "dateTime": "%A, %e %B %Y %H:%M:%S", "date": "%d/%m/%Y", "time": "%H:%M:%S", "periods": ["AM", "PM"],
    "days": ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"],
    "shortDays": ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"],
    "months": ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
               "November", "Desember"],
    "shortMonths": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"],
}

# Skema warna kategori (sama dengan pratinjau Studio Visual; config/sps_studio/lembar.py).
# Id lama tetap terdaftar dengan warna baru, agar dashboard versi sebelumnya ikut memakai palet baru.
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {"id": SKEMA_WARNA, "description": "Palet ALDx Tinta & Sakura (aman buta warna)", "label": "ALDx",
     "isDefault": True, "colors": WARNA},
    *({"id": lama, "description": "Palet ALDx (id versi sebelumnya)", "label": "ALDx (lama)", "colors": WARNA}
      for lama, baru in SKEMA_LAMA.items() if baru == SKEMA_WARNA),
]
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [
    {"id": SKEMA_RUNTUN, "description": "Pink terang ke gelap", "label": "ALDx Pink",
     "isDiverging": False, "isDefault": True, "colors": RUNTUN},
    *({"id": lama, "description": "Palet ALDx (id versi sebelumnya)", "label": "ALDx Pink (lama)",
       "isDiverging": False, "colors": RUNTUN} for lama, baru in SKEMA_LAMA.items() if baru == SKEMA_RUNTUN),
]

# Peta (deck.gl: Peta titik & Peta kepadatan). Ubin peta dasar diambil BROWSER pengguna.
# Jaringan tanpa internet: isi SPS_PETA_UBIN dengan server ubin lokal, mis.
#   http://10.245.1.20:8080/tile/{z}/{x}/{y}.png
# Peta provinsi & pratinjau Studio memakai GeoJSON lokal (tidak butuh internet).
# Tanpa telemetri pihak ketiga (pixel scarf.sh) - data perusahaan tetap di dalam.
SCARF_ANALYTICS = False

SPS_PETA_UBIN = os.environ.get("SPS_PETA_UBIN", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
DECKGL_BASE_MAP = [["tile://" + SPS_PETA_UBIN, "Peta dasar"]]
_host_ubin = "/".join(SPS_PETA_UBIN.split("/")[:3])               # skema://host:port
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"],
        "default-src": ["'self'"],
        "img-src": ["'self'", "blob:", "data:", _host_ubin],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'", _host_ubin],
        "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'"],
        "script-src": ["'self'", "'strict-dynamic'"],
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,
    "session_cookie_secure": False,
}


# --- 9. Server: cache, backgrounder, batas, timeout, upload --------------------
# JANGAN mengisi ROW_LIMIT, SQLLAB_TIMEOUT, cache, dsb. di file ini: semuanya
# diatur dari halaman Pusat Kendali Server (/pusat-kendali/) dan disimpan di
# database. Daftar lengkap & nilai bawaan: config/sps_server/skema.py
sps_server_konfig.terapkan_ke_config(globals())
