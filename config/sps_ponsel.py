"""Tata letak ponsel per dashboard (F7).

Di layar ≤ 760 px dashboard ditampilkan satu kolom. Pemilik dashboard (atau Admin) bisa mengatur URUTAN chart dan
menyembunyikan chart yang tidak cocok di ponsel (mis. tabel lebar), tanpa mengubah tata letak layar lebar.

Disimpan di tabel sendiri (sps_tata_ponsel), bukan json_metadata, agar tidak hilang saat dashboard disimpan dari
Superset. Diterapkan oleh bingkai.js (cangkang ALDx) hanya di layar sempit.

    GET  /ponsel-dashboard/?id=<id>        halaman pengaturan (pemilik & Admin)
    GET  /ponsel-dashboard/api/<id|slug>   {urutan: [chart_id], sembunyi: [chart_id], chart: [...]}  (semua penonton)
    POST /ponsel-dashboard/api/<id>        {urutan, sembunyi}                                       (pemilik & Admin)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template_string, request
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, delete, insert, select

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_ponsel", __name__, url_prefix="/ponsel-dashboard")
_meta = MetaData()
TATA = Table("sps_tata_ponsel", _meta, Column("dashboard_id", Integer, primary_key=True),
             Column("isi", Text), Column("oleh", String(128)), Column("diubah", DateTime))


def _engine():
    from sps_server import penyimpanan
    e = penyimpanan.engine()
    _meta.create_all(bind=e, checkfirst=True)
    return e


def _dashboard(kunci: str):
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    q = db.session.query(Dashboard)
    d = q.get(int(kunci)) if str(kunci).isdigit() else q.filter_by(slug=str(kunci)).one_or_none()
    if d is None or not (sm.is_admin() or sm.can_access_dashboard(d)):
        return None
    return d


def _boleh_ubah(dash) -> bool:
    from superset import security_manager as sm
    return sm.is_admin() or g.user in dash.owners


def _urutan_layar_lebar(dash) -> list[int]:
    """Urutan chart di tata letak layar lebar (atas ke bawah, kiri ke kanan)."""
    try:
        pos = json.loads(dash.position_json or "{}")
    except ValueError:
        pos = {}
    hasil: list[int] = []

    def jalan(kunci: str) -> None:
        node = pos.get(kunci) or {}
        if node.get("type") == "CHART":
            cid = (node.get("meta") or {}).get("chartId")
            if cid and cid not in hasil:
                hasil.append(cid)
        for anak in node.get("children") or []:
            jalan(anak)
    jalan("ROOT_ID")
    for s in dash.slices:                                  # chart yang tidak ada di tata letak: di akhir
        if s.id not in hasil:
            hasil.append(s.id)
    return hasil


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return (jsonify(error="Silakan login"), 401) if "/api/" in request.path else redirect(f"/login/?next={request.full_path}")
    return None


@bp.route("/")
def halaman():
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "sps_ponsel.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/<kunci>")
def api_baca(kunci: str):
    dash = _dashboard(kunci)
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan atau tidak boleh Anda buka."), 404
    with _engine().connect() as c:
        r = c.execute(select(TATA.c.isi).where(TATA.c.dashboard_id == dash.id)).first()
    isi = json.loads(r.isi) if r else {}
    nama = {s.id: s.slice_name for s in dash.slices}
    urutan = [i for i in isi.get("urutan", []) if i in nama] + [i for i in _urutan_layar_lebar(dash)
                                                               if i not in isi.get("urutan", []) and i in nama]
    return jsonify(id=dash.id, judul=dash.dashboard_title, diatur=bool(r), boleh_ubah=_boleh_ubah(dash),
                   urutan=urutan, sembunyi=[i for i in isi.get("sembunyi", []) if i in nama],
                   chart=[{"id": i, "nama": nama[i]} for i in urutan])


@bp.route("/api/<int:dash_id>", methods=["POST"])
def api_simpan(dash_id: int):
    dash = _dashboard(str(dash_id))
    if dash is None or not _boleh_ubah(dash):
        return jsonify(error="Hanya pemilik dashboard atau Admin yang boleh mengatur tata letak ponsel."), 403
    d = request.get_json(silent=True) or {}
    ada = {s.id for s in dash.slices}
    bersih = lambda daftar: [int(i) for i in (daftar or []) if str(i).isdigit() and int(i) in ada]  # noqa: E731
    isi = json.dumps({"urutan": bersih(d.get("urutan")), "sembunyi": bersih(d.get("sembunyi"))})
    with _engine().begin() as c:
        c.execute(delete(TATA).where(TATA.c.dashboard_id == dash_id))
        if not d.get("hapus"):
            c.execute(insert(TATA).values(dashboard_id=dash_id, isi=isi, oleh=g.user.username, diubah=datetime.now()))
    return jsonify(ok=True)


def daftarkan(app) -> None:
    app.register_blueprint(bp)
