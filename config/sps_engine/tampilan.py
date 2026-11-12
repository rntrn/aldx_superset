"""API ekstrak untuk tab "Ekstrak" di Pusat Kendali (/pusat-kendali/api/ekstrak/...) — khusus Admin.

    GET  /api/ekstrak                daftar ekstrak + status engine
    GET  /api/ekstrak/sumber         dataset yang bisa diekstrak (+ kolomnya)
    POST /api/ekstrak                buat  {dataset_id, nama, mode, kolom_inkremental, jadwal}
    POST /api/ekstrak/<id>/segarkan  {penuh: bool}  -> dikirim ke antrean "ekstrak"
    POST /api/ekstrak/<id>/jadwal    {jadwal}
    POST /api/ekstrak/<id>/pindah    chart sumber -> ekstrak   (chart memakai ekstrak)
    POST /api/ekstrak/<id>/kembali   chart ekstrak -> sumber
    POST /api/ekstrak/<id>/hapus
    GET  /api/ekstrak/<id>/riwayat
    GET  /api/ekstrak/impor/koneksi | /impor/tabel   POST /impor/cek | /impor   impor banyak tabel (impor_banyak.py)
"""

from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request

from sps_engine import ekstrak as E, impor_banyak as IB, klien as K
from sps_server.tampilan import _khusus_admin

log = logging.getLogger(__name__)
bp = Blueprint("sps_engine", __name__, url_prefix="/pusat-kendali/api/ekstrak")


def _data() -> dict:
    return request.get_json(silent=True) or {}


def status_engine() -> dict:
    """Ringkasan ALDx Engine untuk tab Status/Ekstrak (tidak pernah melempar galat)."""
    try:
        k = K.klien()
        df = k.kueri_df("SELECT version() AS versi, (SELECT sum(bytes_on_disk) FROM system.parts "
                        f"WHERE active AND database = '{K.nama_db()}') AS ukuran, "
                        "(SELECT count() FROM system.tables WHERE database = "
                        f"'{K.nama_db()}') AS tabel")
        r = df.iloc[0]
        return {"aktif": True, "versi": str(r["versi"]), "ukuran_byte": int(r["ukuran"] or 0),
                "tabel": int(r["tabel"])}
    except Exception as exc:  # noqa: BLE001
        return {"aktif": False, "pesan": str(exc).split("\n")[0][:300]}


def kirim_penyegaran(ekstrak_id: int, pemicu: str, penuh: bool) -> str:
    """Ke backgrounder bila ada Redis; tanpa Redis dijalankan langsung (mode uji/satu container)."""
    from sps_server import lingkungan
    if lingkungan.redis().aktif:
        from sps_engine.tugas import segarkan
        segarkan.apply_async(args=[ekstrak_id, pemicu, penuh], queue="ekstrak")
        return "antre"
    E.segarkan(ekstrak_id, pemicu, penuh)
    return "selesai"


@bp.route("")
@_khusus_admin()
def api_daftar():
    return jsonify(engine=status_engine(), ekstrak=E.daftar())


@bp.route("/sumber")
@_khusus_admin()
def api_sumber():
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    hasil = []
    for t in db.session.query(SqlaTable).order_by(SqlaTable.table_name).all():
        if E.adalah_engine(t.database) and not (t.sql or "").strip():
            continue
        hasil.append({"id": t.id, "nama": t.table_name, "database": t.database.database_name,
                      "kolom": [{"nama": c.column_name, "waktu": bool(c.is_dttm)}
                                for c in t.columns if not c.expression],
                      "template": bool(t.sql and E.POLA_JINJA.search(t.sql))})
    return jsonify(hasil)


@bp.route("", methods=["POST"])
@_khusus_admin()
def api_buat():
    d = _data()
    e = E.buat(int(d.get("dataset_id") or 0), str(d.get("nama") or ""), str(d.get("mode") or "penuh"),
               d.get("kolom_inkremental") or None, d.get("jadwal") or {}, g.user.username)
    status = kirim_penyegaran(e["id"], "pertama", True) if d.get("segarkan_sekarang", True) else "baru"
    return jsonify(ekstrak=E.ambil(e["id"]), kirim=status)


@bp.route("/impor/koneksi")
@_khusus_admin()
def api_impor_koneksi():
    return jsonify(IB.koneksi())


@bp.route("/impor/tabel")
@_khusus_admin()
def api_impor_tabel():
    return jsonify(IB.daftar_tabel(int(request.args.get("db") or 0), request.args.get("skema")))


@bp.route("/impor/cek", methods=["POST"])
@_khusus_admin()
def api_impor_cek():
    d = _data()
    return jsonify(IB.cek(int(d.get("db") or 0), d.get("skema"), d.get("tabel") or [], bool(d.get("hitung"))))


@bp.route("/impor", methods=["POST"])
@_khusus_admin()
def api_impor():
    d = _data()
    return jsonify(IB.impor(int(d.get("db") or 0), d.get("skema"), d.get("tabel") or [], d.get("jadwal") or {},
                            g.user.username, lambda i: kirim_penyegaran(i, "pertama", True)))


@bp.route("/<int:ekstrak_id>/segarkan", methods=["POST"])
@_khusus_admin()
def api_segarkan(ekstrak_id: int):
    if E.ambil(ekstrak_id)["status"] == "berjalan":
        raise E.GalatEkstrak("Penyegaran sedang berjalan.")
    status = kirim_penyegaran(ekstrak_id, f"manual:{g.user.username}", bool(_data().get("penuh")))
    return jsonify(ekstrak=E.ambil(ekstrak_id), kirim=status)


@bp.route("/<int:ekstrak_id>/jadwal", methods=["POST"])
@_khusus_admin()
def api_jadwal(ekstrak_id: int):
    return jsonify(ekstrak=E.ubah_jadwal(ekstrak_id, _data().get("jadwal") or {}))


@bp.route("/<int:ekstrak_id>/pindah", methods=["POST"])
@_khusus_admin()
def api_pindah(ekstrak_id: int):
    return jsonify(E.pindahkan_chart(ekstrak_id))


@bp.route("/<int:ekstrak_id>/kembali", methods=["POST"])
@_khusus_admin()
def api_kembali(ekstrak_id: int):
    return jsonify(E.kembalikan_chart(ekstrak_id))


@bp.route("/<int:ekstrak_id>/hapus", methods=["POST"])
@_khusus_admin()
def api_hapus(ekstrak_id: int):
    E.hapus(ekstrak_id)
    return jsonify(ok=True)


@bp.route("/<int:ekstrak_id>/riwayat")
@_khusus_admin()
def api_riwayat(ekstrak_id: int):
    return jsonify(E.riwayat(ekstrak_id))
