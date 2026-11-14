"""Jejak data (lineage): dari mana sebuah dataset berasal dan dipakai di mana.

    sumber (database · skema · tabel)  ->  dataset  ->  chart  ->  dashboard

Kegunaan: sebelum mengubah/menghapus dataset atau kolom, lihat dulu chart & dashboard mana yang terdampak
(asal-usul data & analisis dampak perubahan).

    GET /jejak-data/                    halaman (wajib login)
    GET /jejak-data/api/daftar?q=       dataset yang boleh diakses pengguna + jumlah chart
    GET /jejak-data/api/jejak/<id>      sumber, chart, dan dashboard untuk satu dataset
    GET /jejak-data/api/segar?dashboard=<id|slug>   kesegaran data sebuah dashboard (label di bilah atas)

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


def _tabel_ditulis() -> dict[str, tuple[str, int]]:
    """{nama tabel: (waktu terakhir ditulis, usia dalam detik)} untuk semua tabel ALDx Engine.
    Usia dihitung engine sendiri agar beda zona waktu antar-container tidak menggeser hasil. {} bila engine tidak menjawab."""
    from sps_engine import klien as K
    try:
        df = K.klien().kueri_df("SELECT table AS tabel, toString(max(modification_time)) AS waktu, "
                                "dateDiff('second', max(modification_time), now()) AS usia FROM system.parts "
                                f"WHERE active AND database = '{K.nama_db()}' GROUP BY table")
    except Exception:  # noqa: BLE001 - label kesegaran tidak boleh menggagalkan halaman
        return {}
    return {n: (w, max(int(u), 0)) for n, w, u in zip(df["tabel"], df["waktu"], df["usia"])}


def kesegaran(dash, sekarang=None) -> dict:
    """Seberapa baru data sebuah dashboard.

    Dataset hasil Ekstrak (ALDx Engine) -> waktu penyegaran terakhir & jadwal berikutnya.
    Tabel engine lain (impor berkas, data latihan, ramalan) -> waktu tabel terakhir ditulis (dari engine).
    Dataset lain membaca database sumber secara langsung -> selalu terbaru ("langsung").
    usia_detik = usia data yang PALING LAMA (itulah batas kesegaran dashboard); None bila semuanya langsung.
    """
    from datetime import datetime

    from superset import security_manager as sm

    from sps_engine import ekstrak
    sekarang = sekarang or datetime.now()
    per_dataset = {e["dataset_id"]: e for e in ekstrak.daftar()}
    usia_dari = lambda teks: max(int((sekarang - datetime.fromisoformat(teks)).total_seconds()), 0)  # noqa: E731
    ditulis = None                                              # diisi saat pertama dibutuhkan (satu kueri ke engine)
    rincian, lihat = [], set()
    for c in dash.slices:
        t = c.datasource
        if t is None or t.id in lihat or not sm.can_access_datasource(t):
            continue
        lihat.add(t.id)
        e = per_dataset.get(t.id)
        if e and e.get("selesai"):
            rincian.append({"dataset": t.table_name, "jenis": "ekstrak", "selesai": e["selesai"],
                            "usia_detik": usia_dari(e["selesai"]), "status": e.get("status") or "",
                            "berikutnya": e.get("berikutnya") or ""})
        elif ekstrak.adalah_engine(t.database):
            ditulis = _tabel_ditulis() if ditulis is None else ditulis
            waktu = ditulis.get(t.table_name)
            rincian.append({"dataset": t.table_name, "jenis": "engine", **(
                {"selesai": waktu[0], "usia_detik": waktu[1]} if waktu else {})})
        else:
            rincian.append({"dataset": t.table_name, "jenis": "langsung"})
    usia = [r["usia_detik"] for r in rincian if "usia_detik" in r]
    return {"usia_detik": max(usia) if usia else None, "gagal": any(r.get("status") == "gagal" for r in rincian),
            "rincian": sorted(rincian, key=lambda r: -r.get("usia_detik", -1))}


@bp.route("/api/segar")
def api_segar():
    from sps_filter_global import _dashboard
    dash = _dashboard(request.args.get("dashboard", ""))
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan atau tidak boleh Anda akses"), 404
    return jsonify(kesegaran(dash))


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
