"""Filter global: satu pilihan filter (mis. Cabang = Cabang Bandung, Tahun = 2025) berlaku di SEMUA dashboard
dan di setiap halaman Story.

Cara kerja:
    1. Pengguna mengisi filter global di bilah atas aplikasi (tombol corong). Disimpan PER AKUN di server
       (tabel sps_filter_global), jadi ikut ke komputer/ponsel lain; browser menyimpan salinan untuk kecepatan.
    2. Saat dashboard dibuka, bingkai.js meminta /filter-global/api/terapkan untuk dashboard itu.
    3. Server mencocokkan NAMA KOLOM filter global dengan filter native dashboard (Filter pilihan / select),
       lalu membuat parameter URL `native_filters` resmi Superset. Dashboard dimuat ulang dengan filter itu.
    4. Kolom yang tidak punya filter native di dashboard itu dilewati (ditampilkan "tidak berlaku").
    5. Dashboard di daftar `kecuali` pengguna tidak diberi filter global sama sekali.

Aman: ini hanya mengisi nilai filter. Hak akses & RLS tetap berlaku; pengguna tidak bisa melihat lebih banyak data.

    GET  /filter-global/api/kolom      kolom yang bisa dipakai (dari filter native dashboard yang boleh dilihat)
    GET  /filter-global/api/nilai      ?kolom=x&cari=teks -> {nilai: [...]} daftar nilai untuk dipilih (RLS berlaku)
    GET  /filter-global/api/terapkan   ?dashboard=id|slug&filter={"kolom": [nilai, ...]}&kecuali=["id|slug", ...]
                                       -> {native_filters, berlaku, tidak_berlaku, dikecualikan, dashboard_id}
    GET  /filter-global/api/sasaran    ?asal=id|slug&filter={...} -> dashboard LAIN yang bisa menerima filter itu
                                       (Telusuri ke dashboard lain / drill-through, sps_app/static/telusur.js)
    GET  /filter-global/api/milik      filter global tersimpan milik pengguna ini
    POST /filter-global/api/milik      {aktif, filter, kecuali} simpan untuk akun ini
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
MAKS_KECUALI = 100
MAKS_SASARAN = 30
MAKS_SUMBER = 5               # dataset yang dibaca untuk daftar nilai satu kolom


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
    if _dikecualikan(dash, request.args.get("kecuali")):
        return jsonify(native_filters=None, berlaku=[], tidak_berlaku=[], dikecualikan=True, dashboard_id=dash.id)
    rison, berlaku, tidak = native_filters(dash, pilihan if isinstance(pilihan, dict) else {})
    return jsonify(native_filters=rison, berlaku=berlaku, tidak_berlaku=tidak, dikecualikan=False, dashboard_id=dash.id)


@bp.route("/api/sasaran")
def api_sasaran():
    """Dashboard lain (yang boleh dibuka pengguna) dengan filter di kolom yang sama -> tujuan drill-through."""
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    try:
        pilihan = json.loads(request.args.get("filter") or "{}")
    except ValueError:
        return jsonify(error="Filter tidak valid"), 400
    if not isinstance(pilihan, dict) or not pilihan:
        return jsonify(sasaran=[])
    asal = _dashboard(request.args.get("asal", ""))
    hasil = []
    for d in db.session.query(Dashboard).order_by(Dashboard.dashboard_title):
        if (asal is not None and d.id == asal.id) or not (sm.is_admin() or sm.can_access_dashboard(d)):
            continue
        rison, berlaku, _ = native_filters(d, pilihan)
        if rison:
            hasil.append({"id": d.id, "judul": d.dashboard_title, "url": f"/superset/dashboard/{d.slug or d.id}/",
                          "berlaku": berlaku, "native_filters": rison})
    hasil.sort(key=lambda x: -len(x["berlaku"]))
    return jsonify(sasaran=hasil[:MAKS_SASARAN])


def _dikecualikan(dash, teks: str | None) -> bool:
    """`kecuali` = JSON daftar id/slug dashboard yang tidak diberi filter global."""
    try:
        daftar = json.loads(teks or "[]")
    except ValueError:
        return False
    kunci = {str(dash.id), str(dash.slug or "")} - {""}
    return any(str(k) in kunci for k in (daftar if isinstance(daftar, list) else [])[:MAKS_KECUALI])


def _sumber_kolom(kolom: str) -> list[tuple[int, str]]:
    """(dataset_id, nama kolom asli) dari filter pilihan di dashboard yang boleh dilihat, untuk kolom ini."""
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    hasil: list[tuple[int, str]] = []
    for d in db.session.query(Dashboard):
        if not (sm.is_admin() or sm.can_access_dashboard(d)):
            continue
        for f in _filter_native(d):
            t = f["targets"][0]
            pasangan = (t.get("datasetId"), (t.get("column") or {}).get("name"))
            if f.get("filterType") == "filter_select" and _kolom(f) == kolom and all(pasangan) and pasangan not in hasil:
                hasil.append(pasangan)
    return hasil[:MAKS_SUMBER]


@bp.route("/api/nilai")
def api_nilai():
    """Daftar nilai kolom pilihan untuk isian filter global. RLS dataset tetap berlaku (values_for_column)."""
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable
    kolom = str(request.args.get("kolom", "")).lower()
    cari = str(request.args.get("cari", "")).strip().lower()[:80]
    nilai: set = set()
    for dataset_id, asli in _sumber_kolom(kolom):
        t = db.session.get(SqlaTable, dataset_id)
        if t is None or not (sm.is_admin() or sm.can_access_datasource(t)):
            continue
        try:
            nilai.update(v for v in t.values_for_column(asli, limit=5000) if v is not None)
        except Exception:                                    # pylint: disable=broad-except
            log.warning("Nilai filter global gagal dibaca: dataset %s kolom %s", dataset_id, asli, exc_info=True)
    cocok = sorted((v for v in nilai if not cari or cari in str(v).lower()), key=lambda v: str(v).lower())
    return jsonify(nilai=cocok[:MAKS_NILAI], lebih=len(cocok) > MAKS_NILAI)


def _bersihkan_filter(filter_) -> dict:
    """Filter dari browser -> bentuk aman untuk disimpan: {kolom: [nilai] | {min, max} | "rentang waktu"}."""
    bersih = {}
    for k, nilai in list((filter_ if isinstance(filter_, dict) else {}).items())[:30]:
        if isinstance(nilai, dict):
            bersih[str(k)[:120]] = {b: _angka(nilai.get(b)) for b in ("min", "max")}
        elif isinstance(nilai, str):
            bersih[str(k)[:120]] = nilai[:80]
        else:
            bersih[str(k)[:120]] = [v for v in (nilai if isinstance(nilai, list) else [nilai])][:MAKS_NILAI]
    return bersih


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
    bersih = _bersihkan_filter(d.get("filter"))
    kecuali = [str(k)[:120] for k in (d.get("kecuali") if isinstance(d.get("kecuali"), list) else [])][:MAKS_KECUALI]
    isi = json.dumps({"aktif": bool(d.get("aktif", True)), "filter": bersih, "kecuali": kecuali}, ensure_ascii=False)
    t, meta = _tabel()
    meta.create_all(bind=_engine(), checkfirst=True)
    with _engine().begin() as c:
        c.execute(delete(t).where(t.c.pengguna == g.user.username))
        c.execute(insert(t).values(pengguna=g.user.username, isi=isi, diubah=datetime.now()))
    return jsonify(ok=True)


# --- Tampilan tersimpan (bookmark, padanan Power BI) ------------------------------------------------
# Keadaan filter sebuah dashboard disimpan dengan nama, per akun. Membuka tampilan = membuka dashboard yang sama
# dengan filter itu terpasang (parameter URL native_filters), jadi hak akses & RLS tetap berlaku seperti biasa.
MAKS_TAMPILAN = 20          # per akun per dashboard


def _tabel_tampilan():
    from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text
    meta = MetaData()
    return Table("sps_tampilan", meta, Column("id", Integer, primary_key=True, autoincrement=True),
                 Column("pengguna", String(128), index=True), Column("dashboard_id", Integer, index=True),
                 Column("nama", String(80)), Column("isi", Text), Column("dibuat", DateTime)), meta


def daftar_tampilan(dash, pengguna: str) -> list[dict]:
    from sqlalchemy import select
    t, meta = _tabel_tampilan()
    meta.create_all(bind=_engine(), checkfirst=True)
    with _engine().connect() as c:
        rows = c.execute(select(t.c.id, t.c.nama, t.c.isi).where(t.c.pengguna == pengguna, t.c.dashboard_id == dash.id)
                         .order_by(t.c.nama)).fetchall()
    hasil = []
    for r in rows:
        filter_ = json.loads(r.isi or "{}")
        rison, berlaku, _ = native_filters(dash, filter_)
        hasil.append({"id": r.id, "nama": r.nama, "filter": filter_, "berlaku": berlaku, "native_filters": rison})
    return hasil


def simpan_tampilan(dash, pengguna: str, nama: str, filter_) -> None:
    from datetime import datetime

    from sqlalchemy import delete, func, insert, select
    nama, bersih = " ".join(str(nama or "").split())[:80], _bersihkan_filter(filter_)
    if not nama:
        raise ValueError("Beri nama tampilan dulu.")
    if not bersih:
        raise ValueError("Belum ada filter aktif untuk disimpan.")
    t, meta = _tabel_tampilan()
    meta.create_all(bind=_engine(), checkfirst=True)
    milik = (t.c.pengguna == pengguna) & (t.c.dashboard_id == dash.id)
    with _engine().begin() as c:
        c.execute(delete(t).where(milik & (t.c.nama == nama)))               # nama sama = timpa
        if c.execute(select(func.count()).select_from(t).where(milik)).scalar() >= MAKS_TAMPILAN:
            raise ValueError(f"Maksimal {MAKS_TAMPILAN} tampilan per dashboard. Hapus yang tidak dipakai.")
        c.execute(insert(t).values(pengguna=pengguna, dashboard_id=dash.id, nama=nama,
                                   isi=json.dumps(bersih, ensure_ascii=False), dibuat=datetime.now()))


def hapus_tampilan(pengguna: str, tampilan_id: int) -> None:
    from sqlalchemy import delete
    t, meta = _tabel_tampilan()
    meta.create_all(bind=_engine(), checkfirst=True)
    with _engine().begin() as c:                                             # hanya milik sendiri
        c.execute(delete(t).where(t.c.id == int(tampilan_id), t.c.pengguna == pengguna))


@bp.route("/api/tampilan")
def api_tampilan():
    from flask import g
    dash = _dashboard(request.args.get("dashboard", ""))
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan atau tidak boleh Anda akses"), 404
    return jsonify(tampilan=daftar_tampilan(dash, g.user.username), url=f"/superset/dashboard/{dash.slug or dash.id}/")


@bp.route("/api/tampilan", methods=["POST"])
def api_simpan_tampilan():
    from flask import g
    d = request.get_json(silent=True) or {}
    dash = _dashboard(d.get("dashboard", ""))
    if dash is None:
        return jsonify(error="Dashboard tidak ditemukan atau tidak boleh Anda akses"), 404
    try:
        simpan_tampilan(dash, g.user.username, d.get("nama"), d.get("filter"))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(tampilan=daftar_tampilan(dash, g.user.username))


@bp.route("/api/tampilan/hapus", methods=["POST"])
def api_hapus_tampilan():
    from flask import g
    d = request.get_json(silent=True) or {}
    hapus_tampilan(g.user.username, int(d.get("id") or 0))
    return jsonify(ok=True)


def daftarkan(app) -> None:
    app.register_blueprint(bp)
