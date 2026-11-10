"""Filter global: satu pilihan filter (mis. Cabang = Cabang Bandung, Tahun = 2025) berlaku di SEMUA dashboard
dan di setiap halaman Story.

Cara kerja:
    1. Pengguna mengisi filter global di bilah atas aplikasi (tombol corong). Disimpan PER AKUN di server
       (tabel sps_filter_global), jadi ikut ke komputer/ponsel lain; browser menyimpan salinan untuk kecepatan.
    2. Saat dashboard dibuka, bingkai.js meminta /filter-global/api/terapkan untuk dashboard itu.
    3. Server mencocokkan NAMA KOLOM filter global dengan filter native dashboard (Filter pilihan / select),
       lalu membuat parameter URL `native_filters` resmi Superset. Dashboard dimuat ulang dengan filter itu.
    4. Kolom yang tidak punya filter native di dashboard itu dilewati (ditampilkan "tidak berlaku").

Aman: ini hanya mengisi nilai filter. Hak akses & RLS tetap berlaku; pengguna tidak bisa melihat lebih banyak data.

    GET  /filter-global/api/kolom      kolom yang bisa dipakai (dari filter native dashboard yang boleh dilihat)
    GET  /filter-global/api/terapkan   ?dashboard=id|slug&filter={"kolom": [nilai, ...]} -> {native_filters, berlaku, tidak_berlaku}
    GET  /filter-global/api/milik      filter global tersimpan milik pengguna ini
    POST /filter-global/api/milik      {aktif, filter} simpan untuk akun ini
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request

log = logging.getLogger(__name__)
bp = Blueprint("sps_filter_global", __name__, url_prefix="/filter-global")
JENIS_DIDUKUNG = {"filter_select", "filter_range", "filter_time"}
WAKTU = "__waktu__"            # kunci khusus: rentang waktu (filter_time), mis. "Last month" atau "2025-01-01 : 2025-12-31"
MAKS_NILAI = 200


def _filter_native(dashboard) -> list[dict]:
    try:
        meta = json.loads(dashboard.json_metadata or "{}")
    except ValueError:
        return []
    return [f for f in meta.get("native_filter_configuration") or []
            if f.get("type") == "NATIVE_FILTER" and f.get("filterType") in JENIS_DIDUKUNG and f.get("targets")]


def _kolom(f: dict) -> str:
    if f.get("filterType") == "filter_time":
        return WAKTU
    return str((f["targets"][0].get("column") or {}).get("name") or "").lower()


def _angka(v):
    try:
        f = float(str(v).replace(",", "."))
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


def _sesuaikan_tipe(dataset_id, kolom: str, nilai: list) -> list:
    """Nilai diketik sebagai teks; untuk kolom angka (mis. tahun) ubah ke angka agar cocok dengan data."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.utils.core import GenericDataType
    t = db.session.get(SqlaTable, dataset_id) if dataset_id else None
    c = next((c for c in (t.columns if t else []) if c.column_name == kolom), None)
    if c is None or c.type_generic != GenericDataType.NUMERIC:
        return nilai
    hasil = []
    for v in nilai:
        try:
            f = float(str(v).replace(",", "."))
            hasil.append(int(f) if f.is_integer() else f)
        except ValueError:
            hasil.append(v)
    return hasil


def native_filters(dashboard, pilihan: dict) -> tuple[str | None, list[str], list[str]]:
    """Bangun nilai parameter URL `native_filters` (rison) -> (rison | None, kolom berlaku, kolom tidak berlaku).

    pilihan per kunci:
        kolom pilihan  -> [nilai, ...]                    (filter_select, operator IN)
        kolom angka    -> {"min": a, "max": b}             (filter_range, salah satu boleh kosong)
        "__waktu__"    -> "Last month" | "2025-01-01 : 2025-12-31"   (filter_time)
    """
    import prison
    bersih: dict = {}
    for k, n in (pilihan or {}).items():
        k = str(k).lower()
        if k == WAKTU:
            if isinstance(n, str) and n.strip():
                bersih[k] = n.strip()[:80]
        elif isinstance(n, dict):
            rentang = {b: _angka(n.get(b)) for b in ("min", "max")}
            if any(v is not None for v in rentang.values()):
                bersih[k] = rentang
        else:
            daftar = [v for v in (n if isinstance(n, list) else [n]) if v not in (None, "")][:MAKS_NILAI]
            if daftar:
                bersih[k] = daftar
    hasil, berlaku = {}, set()
    for f in _filter_native(dashboard):
        kolom, jenis = _kolom(f), f.get("filterType")
        if kolom not in bersih:
            continue
        v = bersih[kolom]
        if jenis == "filter_time" and isinstance(v, str):
            hasil[f["id"]] = {"id": f["id"], "extraFormData": {"time_range": v},
                              "filterState": {"value": v}, "ownState": {}}
        elif jenis == "filter_range" and isinstance(v, dict):
            asli = f["targets"][0]["column"]["name"]
            syarat = ([{"col": asli, "op": ">=", "val": v["min"]}] if v["min"] is not None else []) + \
                     ([{"col": asli, "op": "<=", "val": v["max"]}] if v["max"] is not None else [])
            hasil[f["id"]] = {"id": f["id"], "extraFormData": {"filters": syarat},
                              "filterState": {"value": [v["min"], v["max"]]}, "ownState": {}}
        elif jenis == "filter_select" and isinstance(v, list):
            asli = f["targets"][0]["column"]["name"]
            nilai = _sesuaikan_tipe(f["targets"][0].get("datasetId"), asli, v)
            hasil[f["id"]] = {"id": f["id"],
                              "extraFormData": {"filters": [{"col": asli, "op": "IN", "val": nilai}]},
                              "filterState": {"value": nilai, "label": ", ".join(map(str, nilai))}, "ownState": {}}
        else:
            continue
        berlaku.add(kolom)
    tidak = sorted(set(bersih) - berlaku)
    return (prison.dumps(hasil) if hasil else None), sorted(berlaku), tidak


def _dashboard(kunci):
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    q = db.session.query(Dashboard)
    d = q.get(int(kunci)) if str(kunci).isdigit() else q.filter_by(slug=str(kunci)).one_or_none()
    if d is None or not (sm.is_admin() or sm.can_access_dashboard(d)):
        return None
    return d


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return jsonify(error="Silakan login"), 401
    return None


@bp.route("/api/kolom")
def api_kolom():
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    kolom: dict[str, dict] = {}
    for d in db.session.query(Dashboard):
        if not (sm.is_admin() or sm.can_access_dashboard(d)):
            continue
        for f in _filter_native(d):
            jenis = {"filter_select": "pilihan", "filter_range": "rentang", "filter_time": "waktu"}[f["filterType"]]
            label = "Rentang waktu" if jenis == "waktu" else (f.get("name") or _kolom(f))
            k = kolom.setdefault(_kolom(f), {"kolom": _kolom(f), "label": label, "jenis": jenis, "dashboard": 0})
            k["dashboard"] += 1
    return jsonify(kolom=sorted(kolom.values(), key=lambda k: (-k["dashboard"], k["kolom"])))


@bp.route("/api/terapkan")
def api_terapkan():
    """GET (hanya membaca): ?dashboard=<id|slug>&filter=<JSON {kolom: [nilai]}>."""
    dash = _dashboard(request.args.get("dashboard", ""))
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan atau tidak boleh Anda akses"), 404
    try:
        pilihan = json.loads(request.args.get("filter") or "{}")
    except ValueError:
        return jsonify(error="Filter tidak valid"), 400
    rison, berlaku, tidak = native_filters(dash, pilihan if isinstance(pilihan, dict) else {})
    return jsonify(native_filters=rison, berlaku=berlaku, tidak_berlaku=tidak)


# --- Simpanan per akun (U24) --------------------------------------------------------------------
def _tabel():
    from sqlalchemy import Column, DateTime, MetaData, String, Table, Text
    meta = MetaData()
    return Table("sps_filter_global", meta, Column("pengguna", String(128), primary_key=True),
                 Column("isi", Text), Column("diubah", DateTime)), meta


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


@bp.route("/api/milik")
def api_milik():
    from flask import g
    from sqlalchemy import select
    t, meta = _tabel()
    meta.create_all(bind=_engine(), checkfirst=True)
    with _engine().connect() as c:
        r = c.execute(select(t.c.isi).where(t.c.pengguna == g.user.username)).first()
    return jsonify(json.loads(r.isi) if r and r.isi else None)


@bp.route("/api/milik", methods=["POST"])
def api_simpan_milik():
    from datetime import datetime

    from flask import g
    from sqlalchemy import delete, insert
    d = request.get_json(silent=True) or {}
    filter_ = d.get("filter") if isinstance(d.get("filter"), dict) else {}
    bersih = {}
    for k, nilai in list(filter_.items())[:30]:
        if isinstance(nilai, dict):
            bersih[str(k)[:120]] = {b: _angka(nilai.get(b)) for b in ("min", "max")}
        elif isinstance(nilai, str):
            bersih[str(k)[:120]] = nilai[:80]
        else:
            bersih[str(k)[:120]] = [v for v in (nilai if isinstance(nilai, list) else [nilai])][:MAKS_NILAI]
    isi = json.dumps({"aktif": bool(d.get("aktif", True)), "filter": bersih}, ensure_ascii=False)
    t, meta = _tabel()
    meta.create_all(bind=_engine(), checkfirst=True)
    with _engine().begin() as c:
        c.execute(delete(t).where(t.c.pengguna == g.user.username))
        c.execute(insert(t).values(pengguna=g.user.username, isi=isi, diubah=datetime.now()))
    return jsonify(ok=True)


def daftarkan(app) -> None:
    app.register_blueprint(bp)
