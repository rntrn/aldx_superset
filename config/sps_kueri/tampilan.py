"""Halaman Kueri Visual (/kueri/). Boleh dibuka siapa pun yang boleh memakai SQL Lab.

    GET /kueri/                       halaman
    GET /kueri/api/dialek/<db_id>     cara mengutip nama tabel/kolom & skema bawaan koneksi itu
    GET /kueri/api/virtual/<db_id>    dataset VIRTUAL (berbasis SQL) di koneksi & skema itu, dipakai sebagai subkueri
    POST /kueri/api/fisik              {dataset_id, jadwal} dataset virtual -> tabel fisik di ALDx Engine (ekstrak; Admin)
    GET /kueri/api/fisik/<ekstrak_id>  status penyalinan
    GET /kueri/api/simpanan           kueri visual tersimpan milik pengguna (F6)
    POST /kueri/api/simpanan          {nama, isi} simpan / timpa kueri dengan nama itu
    DELETE /kueri/api/simpanan/<id>   hapus

Kueri tersimpan menyimpan SUSUNAN visual (tabel, gabung, kolom, filter, urutan) di tabel sps_kueri_simpan.
Saat dibuka, kueri dijalankan sebagai pengguna yang membuka: hak akses & RLS tetap berlaku.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template_string, request

FOLDER = Path(__file__).resolve().parent
MENU = "Kueri Visual"
bp = Blueprint("sps_kueri", __name__, url_prefix="/kueri",
               static_folder=str(FOLDER / "static"), static_url_path="/static")


def boleh_sql_lab() -> bool:
    from superset import security_manager as sm
    return sm.is_admin() or sm.can_access("menu_access", "SQL Editor")


@bp.route("/")
def beranda():
    from flask_login import current_user
    from flask_wtf.csrf import generate_csrf
    if not current_user.is_authenticated:
        return redirect(f"/login/?next={request.path}")
    if not boleh_sql_lab():
        from sps_tolak import halaman_tolak
        return halaman_tolak("Kueri Visual memerlukan izin SQL Lab. Hubungi admin (Pusat Kendali > Hak akses).")
    html = (FOLDER / "halaman.html").read_text(encoding="utf-8")
    from superset import security_manager as sm
    return render_template_string(html, csrf=generate_csrf(), admin=sm.is_admin(),
                                  app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/dialek/<int:db_id>")
def api_dialek(db_id: int):
    """Aturan nama per database. Oracle/Snowflake/DB2 menyimpan nama tanpa kutip dalam HURUF BESAR, sedangkan
    Superset menampilkannya huruf kecil: nama seperti itu harus ditulis TANPA kutip (atau dikutip huruf besar)."""
    from flask_login import current_user
    from superset import db
    from superset.models.core import Database
    if not current_user.is_authenticated or not boleh_sql_lab():
        return jsonify(error="Butuh izin SQL Lab"), 403
    d = db.session.get(Database, db_id)
    if d is None:
        return jsonify(error="Koneksi tidak ditemukan"), 404
    dialek = d.get_dialect()
    siap = dialek.identifier_preparer
    import sps_skema
    return jsonify(dialek=dialek.name, kutip_awal=siap.initial_quote, kutip_akhir=siap.final_quote,
                   normalisasi=bool(getattr(dialek, "requires_name_normalize", False)),
                   kata_khusus=sorted(w.lower() for w in siap.reserved_words),
                   skema=sps_skema.pilihan(d), skema_bawaan=sps_skema.bawaan(d))


# --- Dataset virtual sebagai "tabel" ------------------------------------------------------------------
@bp.route("/api/virtual/<int:db_id>")
def api_virtual(db_id: int):
    """Dataset virtual yang boleh diakses di koneksi ini (skema sama, atau tanpa skema).

    Dataset virtual hanyalah SQL tersimpan, jadi tidak ada di daftar tabel database. Kueri Visual memakainya
    sebagai subkueri: FROM (<sql dataset>) t1. Template Jinja di SQL-nya dirender lebih dulu.
    """
    from flask_login import current_user
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable
    if not current_user.is_authenticated or not boleh_sql_lab():
        return jsonify(error="Butuh izin SQL Lab"), 403
    skema = request.args.get("skema") or None
    hasil = []
    q = db.session.query(SqlaTable).filter(SqlaTable.database_id == db_id, SqlaTable.sql.isnot(None))
    for t in q.order_by(SqlaTable.table_name):
        if not (t.sql or "").strip() or (skema and t.schema and t.schema != skema):
            continue
        if not sm.can_access_datasource(t):
            continue
        sql = t.sql.strip().rstrip(";").strip()
        if "{{" in sql or "{%" in sql:
            try:
                from superset.jinja_context import get_template_processor
                sql = get_template_processor(database=t.database, table=t).process_template(sql).strip().rstrip(";")
            except Exception:  # noqa: BLE001 - template butuh konteks dashboard/filter: lewati
                continue
        hasil.append({"id": t.id, "nama": t.table_name, "sql": sql,
                      "kolom": [{"name": c.column_name, "type": str(c.type or "")}
                                for c in t.columns if c.is_active is not False]})
    return jsonify(hasil)


# --- Simpan jadi dataset FISIK ------------------------------------------------------------------------
def _admin():
    from flask_login import current_user
    from superset import security_manager as sm
    if not current_user.is_authenticated or not sm.is_admin():
        return jsonify(error="Dataset fisik dibuat lewat ekstrak ALDx Engine, khusus Admin. "
                             "Simpan sebagai Virtual, atau minta Admin."), 403
    return None


@bp.route("/api/fisik", methods=["POST"])
def api_fisik():
    """Dataset virtual (baru disimpan) -> ekstrak penuh ke ALDx Engine = tabel fisik + dataset ekstrak__<nama>.

    Memakai mesin ekstrak (Pusat Kendali > Ekstrak): penyalinan per potongan di backgrounder, batas data,
    RLS & akses ikut disalin, dan bisa disegarkan terjadwal.
    """
    from flask import g
    from flask_login import current_user
    from sps_engine import ekstrak as E
    from sps_engine.tampilan import kirim_penyegaran
    if (tolak := _admin()) is not None:
        return tolak
    d = request.get_json(silent=True) or {}
    jadwal = d.get("jadwal") if isinstance(d.get("jadwal"), dict) else {"jenis": "manual"}
    try:
        t = E._dataset(int(d.get("dataset_id") or 0))
        e = E.buat(t.id, t.table_name, "penuh", None, jadwal, current_user.username)
        kirim = kirim_penyegaran(e["id"], f"kueri-visual:{current_user.username}", True)
    except (E.GalatEkstrak, ValueError) as exc:
        return jsonify(error=str(exc)), 400
    g.user = current_user
    return jsonify(ekstrak=E.ambil(e["id"]), kirim=kirim)


@bp.route("/api/fisik/<int:ekstrak_id>")
def api_fisik_status(ekstrak_id: int):
    from sps_engine import ekstrak as E
    if (tolak := _admin()) is not None:
        return tolak
    e = E.ambil(ekstrak_id)
    return jsonify({k: e.get(k) for k in ("id", "nama", "tabel", "status", "pesan", "baris_total", "dataset_id")})


# --- Kueri visual tersimpan (F6) -------------------------------------------------------------------
def _tabel():
    from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text
    meta = MetaData()
    t = Table("sps_kueri_simpan", meta, Column("id", Integer, primary_key=True, autoincrement=True),
              Column("pemilik", String(128), index=True), Column("nama", String(150)), Column("isi", Text),
              Column("diubah", DateTime))
    from sps_server import penyimpanan
    meta.create_all(bind=penyimpanan.engine(), checkfirst=True)
    return t, penyimpanan.engine()


def _izin():
    from flask_login import current_user
    if not current_user.is_authenticated or not boleh_sql_lab():
        return jsonify(error="Butuh izin SQL Lab"), 403
    return None


@bp.route("/api/simpanan")
def api_simpanan():
    import json
    from flask import g
    from sqlalchemy import select
    tolak = _izin()
    if tolak:
        return tolak
    t, e = _tabel()
    with e.connect() as c:
        rows = c.execute(select(t).where(t.c.pemilik == g.user.username).order_by(t.c.diubah.desc())).mappings().all()
    return jsonify([{"id": r["id"], "nama": r["nama"], "isi": json.loads(r["isi"]),
                     "diubah": f"{r['diubah']:%Y-%m-%d %H:%M}"} for r in rows])


@bp.route("/api/simpanan", methods=["POST"])
def api_simpan():
    import json
    from datetime import datetime

    from flask import g
    from sqlalchemy import insert, select, update
    tolak = _izin()
    if tolak:
        return tolak
    d = request.get_json(silent=True) or {}
    nama = str(d.get("nama") or "").strip()[:150]
    isi = d.get("isi")
    if not nama or not isinstance(isi, dict):
        return jsonify(error="Isi nama kueri."), 400
    teks = json.dumps(isi, ensure_ascii=False)
    if len(teks) > 2_000_000:
        return jsonify(error="Kueri terlalu besar untuk disimpan."), 400
    t, e = _tabel()
    with e.begin() as c:
        ada = c.execute(select(t.c.id).where(t.c.pemilik == g.user.username, t.c.nama == nama)).first()
        if ada:
            c.execute(update(t).where(t.c.id == ada.id).values(isi=teks, diubah=datetime.now()))
        else:
            c.execute(insert(t).values(pemilik=g.user.username, nama=nama, isi=teks, diubah=datetime.now()))
    return jsonify(ok=True, ditimpa=bool(ada))


@bp.route("/api/simpanan/<int:kid>", methods=["DELETE"])
def api_hapus_simpanan(kid: int):
    from flask import g
    from sqlalchemy import delete
    tolak = _izin()
    if tolak:
        return tolak
    t, e = _tabel()
    with e.begin() as c:
        n = c.execute(delete(t).where(t.c.id == kid, t.c.pemilik == g.user.username)).rowcount
    return (jsonify(ok=True), 200) if n else (jsonify(error="Tidak ditemukan"), 404)
