"""Sematkan (embed) dashboard ALDx ke web / aplikasi lain, dengan filter dari URL dan RLS per penonton.

Cara pakai (rinci: docs/30-sematkan-dashboard.md):
    1. Admin: Dashboard & Story > Sematkan -> nyalakan dashboard yang boleh disematkan.
    2. .env:  SPS_SEMATKAN_DOMAIN=https://portal.kantor.local   (asal halaman yang boleh menampilkan; pisah koma)
              SPS_SEMATKAN_KUNCI=<rahasia panjang>              (dipakai SERVER aplikasi induk untuk meminta token)
    3. Server aplikasi induk meminta token tamu (berumur pendek):
           POST /sematkan/api/token   header  X-ALDx-Kunci: <kunci>
           {"dashboard": "<id|slug|uuid>", "rls": ["kd_cabang = 'C01'"], "pengguna": "budi"}
    4. Halaman induk:  <iframe src="https://aldx/sematkan/d/<uuid>?token=<token>&f.cabang=Bandung&f.tahun=2025">

Keamanan:
    - Tanpa token yang sah tidak ada data. Token ditandatangani server, hanya berlaku untuk dashboard itu,
      dan membawa aturan RLS-nya; penonton tidak perlu (dan tidak mendapat) akun ALDx.
    - Kunci hanya untuk server ke server; jangan pernah ditaruh di halaman web / JavaScript browser.
    - Filter URL (f.<kolom>=nilai) hanya MEMPERSEMPIT data, memakai pencocok filter global (sps_filter_global).
    - Hanya asal di SPS_SEMATKAN_DOMAIN yang boleh menampilkan (CSP frame-ancestors), dan hanya untuk
      halaman /sematkan/d/ & /embedded/; halaman ALDx lain tetap tidak bisa dibingkai situs lain.

    GET  /sematkan/                 halaman admin: daftar dashboard, saklar, contoh kode
    GET  /sematkan/api/daftar       (Admin) dashboard + status sematan
    POST /sematkan/api/atur         (Admin) {"dashboard": id, "aktif": true|false}
    POST /sematkan/api/token        (kunci) token tamu
    GET  /sematkan/d/<kunci>        halaman bingkai untuk <iframe> (publik; data tetap butuh token)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from pathlib import Path

from flask import Blueprint, Response, jsonify, render_template_string, request

log = logging.getLogger(__name__)
bp = Blueprint("sps_sematkan", __name__, url_prefix="/sematkan")
JALUR_BINGKAI = ("/sematkan/d/", "/embedded/")
_ASAL = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d{1,5})?$")
_KLAUSA_TERLARANG = re.compile(r";|--|/\*|\*/")
MAKS_RLS = 20


# --- Pengaturan (.env) ---------------------------------------------------------------------------
def domain_boleh() -> list[str]:
    """Asal (skema://host[:port]) yang boleh menampilkan dashboard dalam <iframe>."""
    mentah = (os.environ.get("SPS_SEMATKAN_DOMAIN") or "").split(",")
    return [d.strip().rstrip("/") for d in mentah if _ASAL.match(d.strip().rstrip("/"))]


def _kunci_server() -> str:
    return (os.environ.get("SPS_SEMATKAN_KUNCI") or "").strip()


def rahasia_token(secret_key: str) -> str:
    """Rahasia penandatangan token tamu: turunan SUPERSET_SECRET_KEY (bukan nilai bawaan Superset)."""
    return hashlib.sha256(f"aldx-sematkan:{secret_key}".encode()).hexdigest()


def umur_token_detik() -> int:
    try:
        menit = int(os.environ.get("SPS_SEMATKAN_MENIT") or 15)
    except ValueError:
        menit = 15
    return max(1, min(menit, 24 * 60)) * 60


# --- Header bingkai: hanya untuk halaman sematan -------------------------------------------------
class IzinBingkai:
    """WSGI: di halaman sematan, izinkan <iframe> dari SPS_SEMATKAN_DOMAIN (halaman lain tidak diubah)."""

    def __init__(self, wsgi):
        self.wsgi = wsgi

    def __call__(self, environ, start_response):
        if not (environ.get("PATH_INFO") or "").startswith(JALUR_BINGKAI):
            return self.wsgi(environ, start_response)
        leluhur = "frame-ancestors " + " ".join(["'self'", *domain_boleh()])

        def mulai(status, headers, exc_info=None):
            baru = []
            for nama, nilai in headers:
                rendah = nama.lower()
                if rendah == "x-frame-options":
                    continue
                if rendah == "content-security-policy":
                    bagian = [b.strip() for b in nilai.split(";") if b.strip() and not b.strip().startswith("frame-ancestors")]
                    nilai = "; ".join([*bagian, leluhur])
                baru.append((nama, nilai))
            if not any(n.lower() == "content-security-policy" for n, _ in baru):
                baru.append(("Content-Security-Policy", leluhur))
            return start_response(status, baru, exc_info)

        return self.wsgi(environ, mulai)


# --- Dashboard & sematan -------------------------------------------------------------------------
def _cari(kunci: str):
    """Dashboard dari id, slug, atau uuid sematan. -> (dashboard, embedded | None)"""
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.embedded_dashboard import EmbeddedDashboard

    kunci = str(kunci or "").strip()
    if re.fullmatch(r"[0-9a-fA-F-]{36}", kunci):
        e = db.session.query(EmbeddedDashboard).filter_by(uuid=kunci).one_or_none()
        if e is not None:
            return db.session.get(Dashboard, e.dashboard_id), e
    q = db.session.query(Dashboard)
    dash = q.filter_by(id=int(kunci)).one_or_none() if kunci.isdigit() else q.filter_by(slug=kunci).one_or_none()
    return dash, (dash.embedded[0] if dash is not None and dash.embedded else None)


def _filter_url(args) -> dict:
    """f.<kolom>=a,b | f.<kolom>.min= / .max= | f.waktu=Last month  ->  pilihan untuk sps_filter_global."""
    from sps_filter_global import WAKTU
    pilihan: dict = {}
    for nama in args:
        if not nama.startswith("f.") or len(nama) < 3:
            continue
        kolom, _, batas = nama[2:].lower().partition(".")
        nilai = args.get(nama, "")
        if kolom == "waktu":
            pilihan[WAKTU] = nilai
        elif batas in ("min", "max"):
            pilihan.setdefault(kolom, {})[batas] = nilai
        elif not batas:
            pilihan[kolom] = [v.strip() for v in ",".join(args.getlist(nama)).split(",") if v.strip()]
    return pilihan


# --- Halaman bingkai (publik) --------------------------------------------------------------------
_BINGKAI = """<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ judul }}</title><link rel="stylesheet" href="/identitas/tema.css">
<style>html,body{height:100%;margin:0;background:var(--sps-latar,#F4F4F5);font-family:var(--sps-font,sans-serif)}
iframe{border:0;width:100%;height:100%;display:block}
#pesan{position:fixed;inset:0;display:grid;place-items:center;text-align:center;color:#52525B;font-size:14px;padding:24px}
[hidden]{display:none!important}</style></head>
<body><div id="pesan">Menunggu izin dari aplikasi induk…</div><iframe id="dasbor" title="{{ judul }}" hidden></iframe>
<script nonce="{{ csp_nonce() }}">
(function () {
  var bingkai = document.getElementById("dasbor"), pesan = document.getElementById("pesan");
  var token = new URLSearchParams(location.search).get("token"), port = null;
  function kirim() { if (port && token) port.postMessage({switchboardAction: "emit", method: "guestToken", args: {guestToken: token}}); }
  // Aplikasi induk boleh mengirim / memperbarui token: iframe.contentWindow.postMessage({aldxToken: "..."}, "*")
  window.addEventListener("message", function (e) {
    if (e.source === window.parent && e.data && typeof e.data.aldxToken === "string") { token = e.data.aldxToken; mulai(); kirim(); }
  });
  function mulai() {
    if (!token || bingkai.src) return;
    bingkai.addEventListener("load", function () {
      var kanal = new MessageChannel(); port = kanal.port1; port.start();
      bingkai.contentWindow.postMessage({type: "__embedded_comms__", handshake: "port transfer"}, location.origin, [kanal.port2]);
      kirim(); pesan.hidden = true; bingkai.hidden = false;
    });
    bingkai.src = {{ alamat|tojson }};
  }
  mulai();
})();
</script></body></html>"""


@bp.route("/d/<kunci>")
def bingkai(kunci: str):
    from sps_tolak import halaman_galat
    dash, sematan = _cari(kunci)
    if dash is None or sematan is None:
        return halaman_galat(404, "Dashboard tidak tersedia untuk disematkan",
                             "Minta Admin ALDx menyalakan dashboard ini di menu Dashboard & Story › Sematkan.")
    from sps_filter_global import native_filters
    rison, _, _ = native_filters(dash, _filter_url(request.args))
    ui = 0 if request.args.get("judul") == "1" else 1                       # 1 = sembunyikan judul dashboard
    alamat = f"/embedded/{sematan.uuid}?uiConfig={ui}"
    if rison:
        from urllib.parse import quote
        alamat += "&native_filters=" + quote(rison, safe="")
    return render_template_string(_BINGKAI, judul=dash.dashboard_title, alamat=alamat)


# --- Token tamu (server ke server) ---------------------------------------------------------------
@bp.route("/api/token", methods=["POST"])
def api_token():
    kunci = _kunci_server()
    if not kunci:
        return jsonify(error="Sematan belum diaktifkan: isi SPS_SEMATKAN_KUNCI di .env"), 503
    if not hmac.compare_digest(request.headers.get("X-ALDx-Kunci", ""), kunci):
        return jsonify(error="Kunci salah"), 401
    isi = request.get_json(silent=True) or {}
    dash, sematan = _cari(isi.get("dashboard"))
    if dash is None or sematan is None:
        return jsonify(error="Dashboard tidak ditemukan atau belum dinyalakan untuk disematkan"), 404
    aturan = []
    for r in (isi.get("rls") or [])[:MAKS_RLS]:
        klausa = (r.get("clause") if isinstance(r, dict) else r) or ""
        if not isinstance(klausa, str) or not klausa.strip() or _KLAUSA_TERLARANG.search(klausa):
            return jsonify(error="Aturan rls tidak sah (teks syarat SQL tanpa ; atau komentar)"), 400
        satu = {"clause": klausa.strip()}
        if isinstance(r, dict) and str(r.get("dataset", "")).isdigit():
            satu["dataset"] = int(r["dataset"])
        aturan.append(satu)
    nama = str(isi.get("pengguna") or "tamu")[:64]
    from superset import security_manager
    token = security_manager.create_guest_access_token(
        {"username": f"sematan:{nama}", "first_name": nama, "last_name": "(sematan)"},
        [{"type": "dashboard", "id": str(sematan.uuid)}], aturan)
    log.info("ALDx sematkan: token untuk dashboard %s, pengguna %s, %d aturan rls", dash.id, nama, len(aturan))
    return jsonify(token=token.decode() if isinstance(token, bytes) else token, berlaku_detik=umur_token_detik(),
                   alamat=f"/sematkan/d/{sematan.uuid}")


# --- Admin ---------------------------------------------------------------------------------------
def _admin(halaman: bool = False):
    from sps_server.tampilan import _khusus_admin
    return _khusus_admin(halaman)


@bp.route("/api/daftar")
def api_daftar():
    @_admin()
    def inti():
        from superset import db
        from superset.models.dashboard import Dashboard
        baris = [{"id": d.id, "judul": d.dashboard_title, "slug": d.slug, "terbit": bool(d.published),
                  "uuid": str(d.embedded[0].uuid) if d.embedded else None}
                 for d in db.session.query(Dashboard).order_by(Dashboard.dashboard_title).all()]
        return jsonify(dashboard=baris, domain=domain_boleh(), kunci_terisi=bool(_kunci_server()),
                       menit=umur_token_detik() // 60)
    return inti()


@bp.route("/api/atur", methods=["POST"])
def api_atur():
    @_admin()
    def inti():
        from superset import db
        from superset.daos.dashboard import EmbeddedDashboardDAO
        from superset.models.dashboard import Dashboard
        isi = request.get_json(silent=True) or {}
        dash = db.session.get(Dashboard, int(isi.get("dashboard") or 0))
        if dash is None:
            return jsonify(error="Dashboard tidak ditemukan"), 404
        if isi.get("aktif"):
            EmbeddedDashboardDAO.upsert(dash, [])       # domain dijaga CSP (SPS_SEMATKAN_DOMAIN), bukan referrer
        else:
            for e in list(dash.embedded):
                db.session.delete(e)
        db.session.commit()
        db.session.refresh(dash)
        return jsonify(uuid=str(dash.embedded[0].uuid) if dash.embedded else None)
    return inti()


@bp.route("/")
def halaman():
    @_admin(True)
    def inti():
        from flask import current_app
        html = Path(__file__).with_name("sps_sematkan.html").read_text(encoding="utf-8")
        return render_template_string(html, app_name=current_app.config.get("APP_NAME", "ALDx"))
    return inti()


def siapkan() -> list[str]:
    """build-dashboards: role penonton sematan = izin baca role Gamma (yang sudah dipangkas hak minimumnya).
    Akses dataset tidak diberikan ke role: token tamu hanya membuka dashboard yang disebut di token."""
    from flask import current_app
    from superset import db, security_manager as sm
    nama = current_app.config.get("GUEST_ROLE_NAME") or "Penonton Sematan"
    role, gamma = sm.add_role(nama), sm.find_role("Gamma")
    if gamma is None:
        return [f"role '{nama}': Gamma tidak ada, izin tidak disalin"]
    baca = [pv for pv in gamma.permissions if pv.permission.name.startswith("can_")
            and pv.permission.name not in ("can_write", "can_this_form_post", "can_this_form_get")]
    role.permissions = baca
    db.session.commit()
    return [f"role '{nama}': {len(baca)} izin baca (sematan)"]


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: halaman & API /sematkan/ + izin bingkai khusus halaman sematan."""
    app.register_blueprint(bp)
    app.wsgi_app = IzinBingkai(app.wsgi_app)
    try:      # dipanggil server aplikasi induk dengan kunci (bukan browser yang sedang login): tanpa token CSRF
        from superset.extensions import csrf
        csrf.exempt(app.view_functions["sps_sematkan.api_token"])
    except Exception:  # noqa: BLE001
        log.warning("ALDx sematkan: gagal mengecualikan CSRF untuk /sematkan/api/token", exc_info=True)
