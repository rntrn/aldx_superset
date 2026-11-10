"""Lihat sebagai… (F1): Admin melihat data dashboard PERSIS seperti yang dilihat pengguna lain.

Untuk menguji hak akses (RLS) tanpa meminjam password atau login dua akun. Setiap chart di dashboard dijalankan
SEBAGAI pengguna terpilih (izin, akses dashboard, dan aturan hak akses data miliknya), lalu hasilnya ditampilkan
sebagai tabel hanya-baca, berikut aturan RLS yang berlaku. Admin tidak pernah masuk ke sesi pengguna itu.

    GET  /lihat-sebagai/                      halaman (khusus Admin)
    GET  /lihat-sebagai/api/pilihan?q=        pengguna aktif & dashboard
    POST /lihat-sebagai/api/jalankan          {username, dashboard_id} -> hasil per chart

Setiap pemakaian tercatat di jejak audit (kelompok "Pengguna & hak akses").
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template_string, request

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_lihat_sebagai", __name__, url_prefix="/lihat-sebagai")
BARIS_TAMPIL = 50


@bp.before_request
def _khusus_admin():
    from flask_login import current_user
    from superset import security_manager as sm
    if not current_user.is_authenticated:
        return (jsonify(error="Silakan login"), 401) if "/api/" in request.path else redirect(f"/login/?next={request.path}")
    if not sm.is_admin():
        if "/api/" in request.path:
            return jsonify(error="Khusus Admin"), 403
        from sps_tolak import halaman_tolak
        return halaman_tolak("Lihat sebagai… khusus Admin.")
    return None


@bp.route("/")
def halaman():
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "sps_lihat_sebagai.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/pilihan")
def api_pilihan():
    from flask_appbuilder.security.sqla.models import User
    from superset import db
    from superset.models.dashboard import Dashboard
    q = (request.args.get("q") or "").strip()
    pengguna = db.session.query(User).filter(User.active.is_(True))
    if q:
        pola = f"%{q}%"
        pengguna = pengguna.filter(User.username.ilike(pola) | User.first_name.ilike(pola) | User.last_name.ilike(pola))
    return jsonify(
        pengguna=[{"username": u.username, "nama": f"{u.first_name or ''} {u.last_name or ''}".strip(),
                   "role": sorted(r.name for r in u.roles)} for u in pengguna.order_by(User.username).limit(30)],
        dashboard=[{"id": d.id, "judul": d.dashboard_title} for d in
                   db.session.query(Dashboard).order_by(Dashboard.dashboard_title).limit(500)])


KUNCI_KOLOM = ("x_axis", "groupby", "columns", "series", "entity", "groupbyRows", "groupbyColumns", "all_columns")
KUNCI_METRIK = ("metrics", "metric", "metric_2", "percent_metrics", "size", "x", "y")


def _qc_dari_form_data(chart) -> dict:
    """Chart tanpa query_context (mis. dibuat lewat API): susun query sederhana dari params chart."""
    from superset.utils.core import convert_legacy_filters_into_adhoc, split_adhoc_filters_into_base_filters
    fd = json.loads(chart.params or "{}")
    convert_legacy_filters_into_adhoc(fd)
    ds = chart.datasource
    split_adhoc_filters_into_base_filters(fd, ds.database.db_engine_spec.engine if ds else "sqlite")
    kolom, metrik = [], []
    for k in KUNCI_KOLOM:
        v = fd.get(k)
        kolom += [x for x in (v if isinstance(v, list) else [v] if v else []) if x not in kolom]
    for k in KUNCI_METRIK:
        v = fd.get(k)
        metrik += [x for x in (v if isinstance(v, list) else [v] if v else []) if x not in metrik]
    return {"datasource": {"id": chart.datasource_id, "type": chart.datasource_type}, "force": True,
            "queries": [{"columns": kolom, "metrics": metrik, "filters": fd.get("filters") or [],
                         "extras": {"where": fd.get("where") or "", "having": fd.get("having") or ""},
                         "time_range": fd.get("time_range") or "No filter",
                         "row_limit": int(fd.get("row_limit") or 1000), "orderby": []}],
            "form_data": fd, "result_format": "json", "result_type": "full"}


def _jalankan_chart(chart) -> dict:
    """Jalankan query_context chart sebagai g.user (sudah diganti). Kembalikan ringkasan hasil."""
    from superset import security_manager as sm
    from superset.charts.schemas import ChartDataQueryContextSchema
    from superset.commands.chart.data.get_data_command import ChartDataCommand
    from superset.exceptions import SupersetSecurityException

    hasil = {"id": chart.id, "nama": chart.slice_name, "jenis": chart.viz_type}
    try:
        qc_json = json.loads(chart.query_context) if chart.query_context else _qc_dari_form_data(chart)
        qc_json.update(result_format="json", result_type="full", force=True)
        cmd = ChartDataCommand(ChartDataQueryContextSchema().load(qc_json))
        cmd.validate()
        q = (cmd.run().get("queries") or [{}])[0]
    except SupersetSecurityException:
        return {**hasil, "galat": "Pengguna ini TIDAK berhak melihat chart / dataset ini."}
    except Exception as exc:  # noqa: BLE001 - tampilkan galat apa adanya untuk Admin
        return {**hasil, "galat": str(exc)[:300]}
    data = q.get("data") or []
    ds = chart.datasource
    try:
        rls = [{"klausa": f.clause, "grup": f.group_key} for f in sm.get_rls_filters(ds)] if ds else []
    except Exception:  # noqa: BLE001
        rls = []
    return {**hasil, "kolom": q.get("colnames") or (list(data[0].keys()) if data else []),
            "baris": data[:BARIS_TAMPIL], "jumlah_baris": q.get("rowcount", len(data)), "rls": rls,
            "galat": q.get("error")}


@bp.route("/api/jalankan", methods=["POST"])
def api_jalankan():
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    from superset.utils.core import override_user

    import sps_audit
    d = request.get_json(silent=True) or {}
    target = sm.find_user(username=str(d.get("username") or ""))
    dash = db.session.get(Dashboard, int(d.get("dashboard_id") or 0))
    if target is None or not target.is_active:
        return jsonify(error="Pengguna tidak ditemukan atau tidak aktif."), 404
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan."), 404
    admin = g.user
    sps_audit.catat("keamanan", "Lihat sebagai", f"{target.username} · {dash.dashboard_title}")
    with override_user(target, force=True):
        boleh = sm.is_admin() or sm.can_access_dashboard(dash)
        chart = [_jalankan_chart(c) for c in dash.slices] if boleh else []
    g.user = admin
    db.session.rollback()                      # pastikan tidak ada perubahan yang terbawa dari sesi tiruan
    return jsonify(pengguna={"username": target.username, "nama": f"{target.first_name or ''} {target.last_name or ''}".strip(),
                             "role": sorted(r.name for r in target.roles)},
                   dashboard=dash.dashboard_title, boleh_buka=boleh, chart=chart)


def daftarkan(app) -> None:
    app.register_blueprint(bp)
