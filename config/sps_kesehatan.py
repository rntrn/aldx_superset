"""Kesehatan kueri: chart & dashboard mana yang lambat, kueri apa yang gagal, dan apa yang perlu dilakukan.

Sumber data (tanpa tabel baru):
    logs (Superset)   setiap kueri chart tercatat sebagai ChartDataRestApi.data + durasi (ms), chart, dashboard
    query (SQL Lab)   kueri SQL Lab berstatus gagal
    sps_ekstrak       penyegaran ekstrak yang gagal (ALDx Engine)

    GET /kesehatan-kueri/                 halaman (khusus Admin)
    GET /kesehatan-kueri/api/ringkas?hari=7

Saran otomatis per chart lambat: ekstrak ke ALDx Engine (bila datasetnya masih membaca sumber langsung),
kurangi batas baris, atau aktifkan cache. Hanya membaca.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template_string, request

FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_kesehatan", __name__, url_prefix="/kesehatan-kueri")
LAMBAT_MS = 5000              # kueri chart di atas ini dianggap lambat
MIN_JALAN = 3                 # chart dengan lebih sedikit kueri tidak diperingkat (p95 tidak bermakna)
MAKS_LOG = 200_000            # batas baris log yang dibaca per permintaan
TERATAS = 15


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
        return halaman_tolak("Kesehatan kueri khusus Admin.")
    return None


@bp.route("/")
def halaman():
    html = (FOLDER / "sps_kesehatan.html").read_text(encoding="utf-8")
    return render_template_string(html, app_name=current_app.config.get("APP_NAME", "ALDx"), lambat=LAMBAT_MS // 1000)


def persentil(nilai: list[float], p: float) -> float:
    """Persentil p (0-100) dengan interpolasi linear; 0 bila kosong."""
    if not nilai:
        return 0.0
    urut = sorted(nilai)
    k = (len(urut) - 1) * p / 100
    bawah = int(k)
    atas = min(bawah + 1, len(urut) - 1)
    return urut[bawah] + (urut[atas] - urut[bawah]) * (k - bawah)


def _ringkas_durasi(d: list[float]) -> dict:
    return {"jalan": len(d), "rata": sum(d) / len(d) if d else 0, "p50": persentil(d, 50), "p95": persentil(d, 95),
            "maks": max(d) if d else 0, "lambat": sum(1 for v in d if v >= LAMBAT_MS)}


def saran(chart_ringkas: dict, di_engine: bool, cache_detik: int | None) -> list[str]:
    hasil = []
    if chart_ringkas["p95"] >= LAMBAT_MS and not di_engine:
        hasil.append("Ekstrak datasetnya ke ALDx Engine (Data › Ekstrak): kueri dibaca dari mesin kolom, bukan sumber langsung.")
    if chart_ringkas["p95"] >= LAMBAT_MS and di_engine:
        hasil.append("Kurangi jumlah baris/kolom chart, atau ringkas dataset di Persiapan data.")
    if chart_ringkas["jalan"] >= 20 and chart_ringkas["p95"] >= LAMBAT_MS / 2 and not cache_detik:
        hasil.append("Sering dibuka: atur cache dataset (Edit dataset › Cache timeout) agar hasil dipakai ulang.")
    return hasil


def ringkas(hari: int = 7, sekarang: datetime | None = None) -> dict:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.core import Log
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.models.sql_lab import Query

    from sps_engine import ekstrak
    sejak = (sekarang or datetime.now()) - timedelta(days=hari)
    log = (db.session.query(Log.slice_id, Log.dashboard_id, Log.duration_ms)
           .filter(Log.action == "ChartDataRestApi.data", Log.dttm >= sejak, Log.duration_ms.isnot(None))
           .order_by(Log.id.desc()).limit(MAKS_LOG).all())
    semua = [float(r.duration_ms) for r in log]
    per_chart: dict[int, list[float]] = {}
    per_dash: dict[int, list[float]] = {}
    for r in log:
        if r.slice_id:
            per_chart.setdefault(r.slice_id, []).append(float(r.duration_ms))
        if r.dashboard_id:
            per_dash.setdefault(r.dashboard_id, []).append(float(r.duration_ms))

    chart = {c.id: c for c in db.session.query(Slice).filter(Slice.id.in_(list(per_chart) or [0]))}
    ds_id = {c.datasource_id for c in chart.values()}
    dataset = {t.id: t for t in db.session.query(SqlaTable).filter(SqlaTable.id.in_(list(ds_id) or [0]))}
    charts = []
    for cid, d in per_chart.items():
        c = chart.get(cid)
        if c is None or len(d) < MIN_JALAN:
            continue
        t = dataset.get(c.datasource_id)
        r = _ringkas_durasi(d)
        charts.append({"id": cid, "judul": c.slice_name, "jenis": c.viz_type, "url": f"/explore/?slice_id={cid}",
                       "dataset": t.table_name if t else "", "dataset_id": t.id if t else None,
                       "engine": bool(t and ekstrak.adalah_engine(t.database)), **r,
                       "saran": saran(r, bool(t and ekstrak.adalah_engine(t.database)), t.cache_timeout if t else None)})
    charts.sort(key=lambda x: -x["p95"])

    judul_dash = dict(db.session.query(Dashboard.id, Dashboard.dashboard_title).filter(Dashboard.id.in_(list(per_dash) or [0])))
    dash = [{"id": i, "judul": judul_dash.get(i, f"#{i}"), "url": f"/superset/dashboard/{i}/", **_ringkas_durasi(d)}
            for i, d in per_dash.items() if i in judul_dash]
    dash.sort(key=lambda x: -x["p95"])

    gagal = [{"waktu": q.start_time and datetime.fromtimestamp(float(q.start_time) / 1000).isoformat(sep=" ", timespec="minutes"),
              "database": q.database.database_name if q.database else "", "pesan": (q.error_message or "")[:300],
              "sql": (q.sql or "")[:300]}
             for q in db.session.query(Query).filter(Query.status == "failed", Query.changed_on >= sejak)
             .order_by(Query.changed_on.desc()).limit(20)]
    ekstrak_gagal = [{"nama": e["nama"], "pesan": (e.get("pesan") or "")[:300], "selesai": e.get("selesai") or ""}
                     for e in ekstrak.daftar() if e.get("status") == "gagal"]
    return {"hari": hari, "ambang_lambat_ms": LAMBAT_MS, "total": _ringkas_durasi(semua),
            "chart": charts[:TERATAS], "dashboard": dash[:TERATAS], "sql_gagal": gagal, "ekstrak_gagal": ekstrak_gagal}


@bp.route("/api/ringkas")
def api_ringkas():
    hari = max(1, min(int(request.args.get("hari") or 7), 90))
    return jsonify(ringkas(hari))


def daftarkan(app) -> None:
    app.register_blueprint(bp)
