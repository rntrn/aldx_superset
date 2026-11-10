"""Riwayat versi dashboard (F8): setiap perubahan dashboard menyimpan versi SEBELUMNYA; bisa dipulihkan.

Yang dicatat: judul, tata letak (position_json), pengaturan (json_metadata: filter, warna, dll.), CSS, dan daftar chart.
Isi chart & dataset TIDAK ikut (punya riwayatnya sendiri di Superset).

Kapan versi dibuat:
    sebelum PUT /api/v1/dashboard/<id>            simpan tata letak / properti (tombol Simpan di dashboard)
    sebelum PUT /api/v1/dashboard/<id>/filters    ubah filter native
    sebelum PUT /api/v1/dashboard/<id>/colors     ubah warna
    sebelum memulihkan versi lain                 (pemulihan bisa dibatalkan dengan memulihkan versi ini)
Versi yang isinya sama dengan versi terakhir tidak disimpan ulang. Disimpan SIMPAN_VERSI terakhir per dashboard.

    GET  /versi-dashboard/?id=<id>                     halaman riwayat (pemilik & Admin)
    GET  /versi-dashboard/api/<id>                     daftar versi
    POST /versi-dashboard/api/<id>/pulihkan/<versi>    pulihkan (pemilik dashboard / Admin)

Tabel sps_versi_dashboard (metadata): id, dashboard_id, waktu, oleh, isi (JSON).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template_string, request
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, delete, insert, select

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
SIMPAN_VERSI = 50
bp = Blueprint("sps_versi", __name__, url_prefix="/versi-dashboard")
_meta = MetaData()
VERSI = Table("sps_versi_dashboard", _meta,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("dashboard_id", Integer, index=True), Column("waktu", DateTime),
              Column("oleh", String(128)), Column("isi", Text))
_UBAH = re.compile(r"^/api/v1/dashboard/(\d+)(/filters|/colors)?/?$")


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


def pastikan_tabel() -> None:
    _meta.create_all(bind=_engine(), checkfirst=True)


def potret(dash) -> dict:
    return {"judul": dash.dashboard_title, "position_json": dash.position_json, "json_metadata": dash.json_metadata,
            "css": dash.css, "chart": sorted(s.id for s in dash.slices)}


def simpan_versi(dash_id: int, isi: dict, oleh: str) -> bool:
    """Simpan satu versi (bila berbeda dari versi terakhir). Kembalikan True bila tersimpan."""
    teks = json.dumps(isi, ensure_ascii=False, sort_keys=True)
    with _engine().begin() as c:
        akhir = c.execute(select(VERSI.c.isi).where(VERSI.c.dashboard_id == dash_id)
                          .order_by(VERSI.c.id.desc()).limit(1)).first()
        if akhir and akhir.isi == teks:
            return False
        c.execute(insert(VERSI).values(dashboard_id=dash_id, waktu=datetime.now(), oleh=oleh, isi=teks))
        lama = [r.id for r in c.execute(select(VERSI.c.id).where(VERSI.c.dashboard_id == dash_id)
                                        .order_by(VERSI.c.id.desc()).offset(SIMPAN_VERSI))]
        if lama:
            c.execute(delete(VERSI).where(VERSI.c.id.in_(lama)))
    return True


# --- Pencatatan otomatis: potret sebelum perubahan, simpan bila perubahan berhasil -----------------
def _sebelum():
    m = _UBAH.match(request.path) if request.method == "PUT" else None
    if not m:
        return
    try:
        from superset import db
        from superset.models.dashboard import Dashboard
        dash = db.session.get(Dashboard, int(m.group(1)))
        if dash is not None:
            g.sps_versi = (dash.id, potret(dash))
    except Exception as exc:  # noqa: BLE001 - pencatatan tidak boleh menggagalkan penyimpanan
        log.warning("ALDx versi: potret gagal (%s)", exc)


def _sesudah(resp):
    data = g.pop("sps_versi", None)
    if data and resp.status_code < 400:
        try:
            simpan_versi(data[0], data[1], getattr(getattr(g, "user", None), "username", "?"))
        except Exception as exc:  # noqa: BLE001
            log.warning("ALDx versi: gagal menyimpan versi (%s)", exc)
    return resp


# --- Halaman & API ---------------------------------------------------------------------------------
def _dashboard(dash_id: int, ubah: bool = False):
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    dash = db.session.get(Dashboard, dash_id)
    if dash is None or not (sm.is_admin() or sm.can_access_dashboard(dash)):
        return None, "Dashboard tidak ditemukan atau tidak boleh Anda buka."
    if ubah and not (sm.is_admin() or g.user in dash.owners):
        return None, "Hanya pemilik dashboard atau Admin yang boleh memulihkan versi."
    return dash, ""


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return (jsonify(error="Silakan login"), 401) if "/api/" in request.path else redirect(f"/login/?next={request.full_path}")
    return None


@bp.route("/")
def halaman():
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "sps_versi.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/<int:dash_id>")
def api_daftar(dash_id: int):
    dash, galat = _dashboard(dash_id)
    if dash is None:
        return jsonify(error=galat), 404
    pastikan_tabel()
    with _engine().connect() as c:
        rows = c.execute(select(VERSI).where(VERSI.c.dashboard_id == dash_id).order_by(VERSI.c.id.desc())).mappings().all()
    from superset import security_manager as sm
    versi = []
    for r in rows:
        isi = json.loads(r["isi"])
        versi.append({"id": r["id"], "waktu": f"{r['waktu']:%Y-%m-%d %H:%M}", "oleh": r["oleh"],
                      "judul": isi.get("judul"), "jumlah_chart": len(isi.get("chart") or [])})
    return jsonify(judul=dash.dashboard_title, boleh_pulihkan=sm.is_admin() or g.user in dash.owners,
                   sekarang={"jumlah_chart": len(dash.slices)}, versi=versi)


@bp.route("/api/<int:dash_id>/pulihkan/<int:versi_id>", methods=["POST"])
def api_pulihkan(dash_id: int, versi_id: int):
    from superset import db
    from superset.models.slice import Slice
    dash, galat = _dashboard(dash_id, ubah=True)
    if dash is None:
        return jsonify(error=galat), 403
    with _engine().connect() as c:
        r = c.execute(select(VERSI.c.isi).where(VERSI.c.id == versi_id, VERSI.c.dashboard_id == dash_id)).first()
    if r is None:
        return jsonify(error="Versi tidak ditemukan."), 404
    isi = json.loads(r.isi)
    simpan_versi(dash.id, potret(dash), g.user.username)          # keadaan sekarang tetap bisa dikembalikan
    dash.dashboard_title = isi["judul"]
    dash.position_json = isi["position_json"]
    dash.json_metadata = isi["json_metadata"]
    dash.css = isi["css"]
    ada = db.session.query(Slice).filter(Slice.id.in_(isi.get("chart") or [0])).all()
    dash.slices = ada
    db.session.commit()
    import sps_audit
    sps_audit.catat("objek", "Pulihkan versi dashboard", dash.dashboard_title, {"versi": versi_id})
    hilang = len(isi.get("chart") or []) - len(ada)
    return jsonify(ok=True, chart_hilang=hilang)


def daftarkan(app) -> None:
    app.register_blueprint(bp)
    app.before_request(_sebelum)
    app.after_request(_sesudah)
    with app.app_context():
        try:
            pastikan_tabel()
        except Exception as exc:  # noqa: BLE001 - database belum siap: dibuat saat dipakai
            log.warning("ALDx versi: tabel belum dibuat (%s)", exc)
