"""Jejak data (lineage): dari mana sebuah dataset berasal dan dipakai di mana.

    sumber (database · skema · tabel)  ->  dataset  ->  chart  ->  dashboard

Kegunaan: sebelum mengubah/menghapus dataset atau kolom, lihat dulu chart & dashboard mana yang terdampak
(padanan "Lineage / Impact analysis" Tableau & Power BI).

    GET /jejak-data/                    halaman (wajib login)
    GET /jejak-data/api/daftar?q=       dataset yang boleh diakses pengguna + jumlah chart
    GET /jejak-data/api/jejak/<id>      sumber, chart, dan dashboard untuk satu dataset

Hanya membaca. Pengguna hanya melihat dataset, chart, dan dashboard yang memang boleh ia buka;
objek lain dihitung sebagai "tersembunyi" tanpa menampilkan namanya.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template_string, request

FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_jejak", __name__, url_prefix="/jejak-data")
MAKS_DAFTAR = 300


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return (jsonify(error="Silakan login"), 401) if "/api/" in request.path else redirect(f"/login/?next={request.path}")
    return None


@bp.route("/")
def halaman():
    html = (FOLDER / "sps_jejak.html").read_text(encoding="utf-8")
    return render_template_string(html, app_name=current_app.config.get("APP_NAME", "ALDx"))


def _waktu(v) -> str:
    return v.isoformat(sep=" ", timespec="minutes") if v else ""


def tabel_sumber(sql: str) -> list[str]:
    """Nama tabel yang dibaca sebuah dataset virtual (SQL). Kosong bila SQL tidak terbaca (mis. memakai Jinja)."""
    import sqlglot
    from sqlglot import exp
    try:
        pohon = sqlglot.parse_one(sql)
    except Exception:  # noqa: BLE001 - SQL apa pun dari pengguna; gagal baca = tanpa daftar tabel
        return []
    cte = {c.alias_or_name for c in pohon.find_all(exp.CTE)}
    nama = {".".join(p for p in (t.db, t.name) if p) for t in pohon.find_all(exp.Table) if t.name not in cte}
    return sorted(n for n in nama if n)


def daftar(kata: str = "") -> list[dict]:
    from sqlalchemy import func
    from superset import db
    from superset.models.slice import Slice

    from sps_ai import alat
    jumlah = dict(db.session.query(Slice.datasource_id, func.count(Slice.id))
                  .filter(Slice.datasource_type == "table").group_by(Slice.datasource_id).all())
    return [{**d, "chart": jumlah.get(d["id"], 0)} for d in alat.daftar_dataset(kata, MAKS_DAFTAR)]


def jejak(dataset_id: int) -> dict:
    from superset import db, security_manager as sm
    from superset.models.slice import Slice

    from sps_ai import alat
    t = alat._dataset(dataset_id)                              # menolak bila pengguna tidak boleh mengakses
    virtual = bool(t.sql)
    sumber = {"database": t.database.database_name, "skema": t.schema or "", "virtual": virtual,
              "tabel": tabel_sumber(t.sql) if virtual else [t.table_name]}
    charts, dashboards, tersembunyi = [], {}, 0
    for c in db.session.query(Slice).filter_by(datasource_id=t.id, datasource_type="table").order_by(Slice.slice_name):
        if not sm.can_access_chart(c):
            tersembunyi += 1
            continue
        milik = []
        for d in c.dashboards:
            if not sm.can_access_dashboard(d):
                continue
            milik.append(d.id)
            dashboards.setdefault(d.id, {"id": d.id, "judul": d.dashboard_title, "url": f"/superset/dashboard/{d.slug or d.id}/",
                                         "terbit": bool(d.published), "diubah": _waktu(d.changed_on), "chart": 0})
            dashboards[d.id]["chart"] += 1
        charts.append({"id": c.id, "judul": c.slice_name, "jenis": c.viz_type, "url": f"/explore/?slice_id={c.id}",
                       "diubah": _waktu(c.changed_on), "dashboard": milik})
    return {"dataset": {"id": t.id, "nama": t.table_name, "keterangan": t.description or "", "kolom": len(t.columns),
                        "metrik": len(t.metrics), "diubah": _waktu(t.changed_on),
                        "pemilik": sorted(f"{o.first_name or ''} {o.last_name or ''}".strip() or o.username for o in t.owners),
                        "url": f"/explore/?datasource_type=table&datasource_id={t.id}"},
            "sumber": sumber, "chart": charts,
            "dashboard": sorted(dashboards.values(), key=lambda d: d["judul"].lower()), "tersembunyi": tersembunyi}


@bp.route("/api/daftar")
def api_daftar():
    return jsonify(dataset=daftar(request.args.get("q", "")))


@bp.route("/api/jejak/<int:dataset_id>")
def api_jejak(dataset_id: int):
    from sps_ai import alat
    try:
        return jsonify(jejak(dataset_id))
    except (alat.IzinDitolak, alat.InputSalah) as e:
        return jsonify(error=str(e)), 404


def daftarkan(app) -> None:
    app.register_blueprint(bp)
