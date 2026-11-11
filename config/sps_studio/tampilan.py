"""Halaman & API Studio Visual (/studio/).

Semua pengguna yang login boleh membuka Studio; data yang terlihat tetap dibatasi
hak akses (RLS). Menyimpan chart/dashboard/dataset butuh izin masing-masing
(lihat Pusat Kendali Server → Hak akses).
"""

from __future__ import annotations

import logging
import os
from functools import wraps
from pathlib import Path

from flask import Blueprint, g, jsonify, redirect, render_template_string, request

from sps_ai import alat
from sps_studio import bidang, dasbor, lembar, prep

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
MENU = "Studio Visual"
ROLE_MENU = [os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna"]   # role dasar pengguna (.env)

bp = Blueprint("sps_studio", __name__, url_prefix="/studio",
               static_folder=str(FOLDER / "static"), static_url_path="/static")


def _login(halaman: bool = False):
    def dekor(fungsi):
        @wraps(fungsi)
        def bungkus(*args, **kwargs):
            from flask_login import current_user
            from sps_ai.tampilan import _aman
            if not current_user.is_authenticated:
                return redirect(f"/login/?next={request.path}") if halaman else (jsonify(error="Belum login"), 401)
            g.user = current_user._get_current_object()
            return _aman(fungsi, *args, **kwargs)
        return bungkus
    return dekor


def _data() -> dict:
    return request.get_json(silent=True) or {}


@bp.route("/")
@_login(halaman=True)
def beranda():
    from flask import current_app
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "halaman.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(),
                                  app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/awal")
@_login()
def api_awal():
    from superset import security_manager as sm
    return jsonify(dataset=alat.daftar_dataset(batas=500), aturan=lembar.ATURAN_TANDA, warna=lembar.WARNA,
                   lembar=lembar.daftar(), dashboard=dasbor.daftar(), user=g.user.username,
                   izin={"chart": sm.can_access("can_write", "Chart"),
                         "dashboard": sm.can_access("can_write", "Dashboard"),
                         "dataset": sm.can_access("can_write", "Dataset")})


@bp.route("/api/bidang/<int:dataset_id>")
@_login()
def api_bidang(dataset_id: int):
    return jsonify(bidang.daftar(dataset_id))


@bp.route("/api/nilai/<int:dataset_id>")
@_login()
def api_nilai(dataset_id: int):
    return jsonify(lembar.nilai_unik(alat._dataset(dataset_id), request.args.get("kolom", "")))


@bp.route("/api/saran/<int:dataset_id>")
@_login()
def api_saran(dataset_id: int):
    from sps_ai import auto
    return jsonify(auto.sarankan(dataset_id, "", None, 16))


@bp.route("/api/kueri", methods=["POST"])
@_login()
def api_kueri():
    t, l = lembar.dari_dict(_data())
    lembar.periksa_tanda(l)                     # jumlah dimensi/ukuran & kolom peta sesuai jenis
    return jsonify(lembar.jalankan(t, l))


@bp.route("/api/lembar")
@_login()
def api_daftar_lembar():
    return jsonify(lembar.daftar())


@bp.route("/api/lembar", methods=["POST"])
@_login()
def api_simpan_lembar():
    d = _data()
    t, l = lembar.dari_dict(d.get("spec") or {})
    return jsonify(lembar.simpan(t, l, d.get("chart_id")))


@bp.route("/api/lembar/<int:chart_id>")
@_login()
def api_buka_lembar(chart_id: int):
    return jsonify(lembar.buka(chart_id))


@bp.route("/api/dashboard")
@_login()
def api_daftar_dashboard():
    return jsonify(dasbor.daftar())


@bp.route("/api/dashboard", methods=["POST"])
@_login()
def api_simpan_dashboard():
    d = _data()
    return jsonify(dasbor.simpan(d, d.get("id")))


@bp.route("/api/dashboard/<int:dashboard_id>")
@_login()
def api_buka_dashboard(dashboard_id: int):
    return jsonify(dasbor.buka(dashboard_id))


@bp.route("/api/prep/pratinjau", methods=["POST"])
@_login()
def api_prep_pratinjau():
    d = _data()
    return jsonify(prep.pratinjau(int(d.get("dataset_id") or 0), d.get("langkah") or []))


@bp.route("/api/prep/simpan", methods=["POST"])
@_login()
def api_prep_simpan():
    d = _data()
    return jsonify(prep.simpan(int(d.get("dataset_id") or 0), d.get("langkah") or [], str(d.get("nama", ""))))


# --- Pemasangan --------------------------------------------------------------------------
def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: halaman /studio/ + menu navbar."""
    app.register_blueprint(bp)
    try:
        from superset.extensions import appbuilder
        appbuilder.add_link(MENU, href="/studio/", label=MENU)
    except Exception:  # noqa: BLE001 - menu gagal tidak boleh mematikan Superset
        log.exception("ALDx Studio: gagal menambah menu")


def siapkan() -> str:
    """Izin menu Studio untuk Admin & pegawai (dipanggil build-dashboards)."""
    from superset import db, security_manager as sm
    pv = sm.add_permission_view_menu("menu_access", MENU)
    for nama in ["Admin", *ROLE_MENU]:
        role = sm.add_role(nama)
        if pv not in role.permissions:
            sm.add_permission_role(role, pv)
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    from sps_studio.ramalan import NAMA_RLS, NAMA_RLS_LAMA
    lama = db.session.query(RowLevelSecurityFilter).filter_by(name=NAMA_RLS_LAMA).one_or_none()
    if lama is not None and not db.session.query(RowLevelSecurityFilter).filter_by(name=NAMA_RLS).first():
        lama.name = NAMA_RLS                         # aturan RLS ramalan: nama lama SPS -> ALDx
    db.session.commit()
    return f"izin menu '{MENU}' untuk Admin & {', '.join(ROLE_MENU)}"
