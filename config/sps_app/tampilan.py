"""Cangkang aplikasi /app/ + pengalihan halaman lama + penyisipan bingkai.js.

    GET /app/                    cangkang (Beranda); /app/?p=/dashboard/list/ membuka halaman di bingkai
    GET /app/static/...          aset cangkang (CSS, JS, kamus bahasa, isi bantuan)
    POST /app/api/ekspor         tabel -> Excel (ekspor.py)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, current_app, redirect, render_template_string, request

import sps_superadmin

FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_app", __name__, url_prefix="/app",
               static_folder=str(FOLDER / "static"), static_url_path="/static")

# Halaman yang selalu ditampilkan di dalam cangkang bila dibuka langsung di tab browser.
HALAMAN_DIBINGKAI = re.compile(
    r"^/(superset/(dashboard|explore|sqllab|welcome)|dashboard/list|chart/list|explore|sqllab|tablemodelview|"
    r"databaseview|savedqueryview|users|roles|list_groups|rowlevelsecurity|actionlog|csstemplatemodelview|"
    r"annotationlayer|theme|superset/tags|studio|kueri|asisten|pusat-kendali|panduan|user_info)(/|$)")
BAHASA = ("id", "en", "ja")


def bahasa_aktif() -> str:
    b = request.cookies.get("sps_bahasa", "")
    if b in BAHASA:
        return b
    terbaik = request.accept_languages.best_match(BAHASA)
    return terbaik or "id"


@bp.route("/")
def cangkang():
    from flask_login import current_user
    from flask_wtf.csrf import generate_csrf
    from superset import security_manager as sm
    if not current_user.is_authenticated:
        return redirect(f"/login/?next={quote(request.full_path)}")
    nilai = current_app.config.get("SPS_IDENTITAS", {})
    pengguna = {"nama": " ".join(x for x in (current_user.first_name, current_user.last_name) if x) or current_user.username,
                "username": current_user.username, "id": current_user.id, "admin": sm.is_admin(),
                "superadmin": sps_superadmin.adalah()}
    html = (FOLDER / "halaman.html").read_text(encoding="utf-8")
    return render_template_string(
        html, csrf=generate_csrf(), app_name=current_app.config.get("APP_NAME", "ALDx"),
        perusahaan=nilai.get("nama_perusahaan", ""), versi=current_app.config.get("SPS_IDENTITAS_VERSI", "0"),
        bahasa=bahasa_aktif(), pengguna=json.dumps(pengguna))


def daftarkan(app) -> None:
    from sps_app import ekspor, persiapan
    bp.add_url_rule("/api/ekspor", "ekspor", ekspor.api_ekspor, methods=["POST"])
    bp.add_url_rule("/api/persiapan", "persiapan", persiapan.api_persiapan)
    app.register_blueprint(bp)
    try:      # hanya mengubah data di layar menjadi berkas (tanpa efek samping): tidak perlu token CSRF
        from superset.extensions import csrf
        csrf.exempt(app.view_functions["sps_app.ekspor"])
    except Exception:  # noqa: BLE001
        pass

    @app.before_request
    def alihkan_ke_app():
        """Halaman Superset/ALDx yang dibuka langsung (bukan di bingkai) -> /app/?p=<alamat>."""
        if (request.method != "GET" or request.headers.get("Sec-Fetch-Dest") != "document"
                or request.args.get("sps_bebas") or not HALAMAN_DIBINGKAI.match(request.path)):
            return None
        from flask_login import current_user
        if not current_user.is_authenticated:
            return None
        tujuan = request.full_path.rstrip("?")
        return redirect("/app/?p=" + quote(tujuan, safe=""))

    @app.after_request
    def sisipkan_bingkai(resp):
        """Setiap halaman HTML mendapat bingkai.js; skrip itu hanya bekerja bila halaman ada di dalam cangkang."""
        if (resp.mimetype != "text/html" or resp.status_code != 200 or resp.direct_passthrough
                or resp.is_streamed or request.path.startswith(("/app", "/login", "/identitas"))):
            return resp
        html = resp.get_data(as_text=True)
        if "</body>" not in html or "bingkai.js" in html:
            return resp
        nonce = getattr(request, "csp_nonce", "")
        versi = current_app.config.get("SPS_IDENTITAS_VERSI", "0")
        skrip = f'<script nonce="{nonce}" src="/app/static/bingkai.js?v={versi}" defer></script>'
        resp.set_data(html.replace("</body>", skrip + "</body>", 1))
        return resp
