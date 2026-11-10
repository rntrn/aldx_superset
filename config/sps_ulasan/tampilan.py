"""API & halaman komentar dan rating.

    GET    /ulasan/api/<jenis>/<id>           ringkasan rating + daftar ulasan yang boleh dilihat
    POST   /ulasan/api/<jenis>/<id>           {teks, nilai} tulis ulasan (menunggu moderasi bila aktif)
    DELETE /ulasan/api/item/<ulasan_id>       hapus ulasan sendiri (Superadmin: ulasan siapa pun)
    GET    /ulasan/moderasi/                  halaman moderasi (Superadmin)
    GET    /ulasan/api/moderasi?status=...    antrean
    POST   /ulasan/api/moderasi/<ulasan_id>   {status: tampil|ditolak, alasan}

<jenis> = dashboard (id atau slug) | chart (id). Hanya yang boleh membuka objek itu yang bisa membaca/menulis.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template_string, request

import sps_audit
import sps_superadmin
from sps_ulasan import model

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_ulasan", __name__, url_prefix="/ulasan")
BATAS_PER_MENIT = 5          # komentar per pengguna per menit (cegah spam yang membanjiri moderasi)


def _moderasi_aktif() -> bool:
    from sps_server import penyimpanan
    return bool(penyimpanan.nilai_semua().get("ulasan.moderasi", True))


def _objek(jenis: str, kunci: str):
    """Kembalikan id objek bila ada & boleh diakses pengguna; None bila tidak."""
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    if jenis == "dashboard":
        q = db.session.query(Dashboard)
        o = q.get(int(kunci)) if kunci.isdigit() else q.filter_by(slug=kunci).one_or_none()
        boleh = o is not None and (sm.is_admin() or sm.can_access_dashboard(o))
    elif jenis == "chart" and kunci.isdigit():
        o = db.session.get(Slice, int(kunci))
        boleh = o is not None and (sm.is_admin() or sm.can_access_chart(o))
    else:
        return None
    return o.id if boleh else None


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return (jsonify(error="Silakan login"), 401) if "/api/" in request.path else redirect(f"/login/?next={request.path}")
    return None


@bp.route("/api/<jenis>/<kunci>", methods=["GET", "POST"])
def api_objek(jenis: str, kunci: str):
    objek_id = _objek(jenis, kunci)
    if objek_id is None:
        return jsonify(error="Tidak ditemukan atau tidak boleh Anda akses"), 404
    superadmin = sps_superadmin.adalah()
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        teks = str(d.get("teks") or "").strip()[:model.MAKS_TEKS]
        nilai = d.get("nilai")
        nilai = int(nilai) if str(nilai or "").isdigit() and 1 <= int(nilai) <= 5 else None
        if not teks and nilai is None:
            return jsonify(error="Tulis komentar atau beri bintang"), 400
        if model.jumlah_baru(g.user.username) >= BATAS_PER_MENIT:
            return jsonify(error="Terlalu banyak komentar dalam satu menit. Coba lagi sebentar."), 429
        nama = " ".join(x for x in (g.user.first_name, g.user.last_name) if x) or g.user.username
        induk = d.get("induk_id")
        induk = int(induk) if str(induk or "").isdigit() else None
        if induk:
            asal = model.ambil(induk)
            if asal is None or asal["jenis"] != jenis or asal["objek_id"] != objek_id or asal.get("induk_id"):
                return jsonify(error="Komentar yang dibalas tidak ditemukan"), 400
        u = model.tambah(jenis, objek_id, g.user.username, nama, teks, nilai, _moderasi_aktif() and not superadmin, induk)
        log.info("ALDx ulasan: %s menulis ulasan %s/%s (%s)", g.user.username, jenis, objek_id, u["status"])
        return jsonify(ulasan=u), 201
    return jsonify(**model.ringkasan(jenis, objek_id), saya=g.user.username, superadmin=superadmin,
                   moderasi=_moderasi_aktif(), ulasan=model.daftar(jenis, objek_id, g.user.username, superadmin))


@bp.route("/api/item/<int:ulasan_id>", methods=["DELETE"])
def api_hapus(ulasan_id: int):
    u = model.ambil(ulasan_id)
    if u is None:
        return jsonify(error="Tidak ditemukan"), 404
    if u["pengguna"] != g.user.username and not sps_superadmin.adalah():
        return jsonify(error="Hanya penulis atau Superadmin yang boleh menghapus"), 403
    model.hapus(ulasan_id)
    log.info("ALDx ulasan: %s menghapus ulasan %s", g.user.username, ulasan_id)
    if u["pengguna"] != g.user.username:
        sps_audit.catat("ulasan", "Hapus komentar orang lain", u["pengguna"], {"id": ulasan_id})
    return jsonify(ok=True)


@bp.route("/moderasi/")
@sps_superadmin.khusus(halaman=True)
def halaman_moderasi():
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "moderasi.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/moderasi")
@sps_superadmin.khusus()
def api_antrean():
    status = request.args.get("status", "menunggu")
    if status not in model.STATUS:
        return jsonify(error="Status tidak dikenal"), 400
    return jsonify(ulasan=_dengan_judul(model.antrean(status)), menunggu=model.jumlah_menunggu())


def _dengan_judul(daftar: list[dict]) -> list[dict]:
    """Tambahkan judul dashboard/chart agar moderator tidak hanya melihat '#id'."""
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    ids = {j: {u["objek_id"] for u in daftar if u["jenis"] == j} for j in ("dashboard", "chart")}
    judul = {("dashboard", i): t for i, t in db.session.query(Dashboard.id, Dashboard.dashboard_title)
             .filter(Dashboard.id.in_(ids["dashboard"] or [0]))}
    judul.update({("chart", i): t for i, t in db.session.query(Slice.id, Slice.slice_name)
                  .filter(Slice.id.in_(ids["chart"] or [0]))})
    return [{**u, "judul": judul.get((u["jenis"], u["objek_id"]), f"{u['jenis']} #{u['objek_id']} (dihapus)")}
            for u in daftar]


@bp.route("/api/moderasi/massal", methods=["POST"])
@sps_superadmin.khusus()
def api_moderasi_massal():
    """{ids: [...], status: tampil|ditolak, alasan} untuk banyak ulasan sekaligus."""
    d = request.get_json(silent=True) or {}
    status = d.get("status")
    if status not in ("tampil", "ditolak"):
        return jsonify(error="Status harus tampil atau ditolak"), 400
    try:
        ids = [int(i) for i in d.get("ids") or []][:500]
    except (TypeError, ValueError):
        return jsonify(error="Pilihan tidak valid"), 400
    alasan = str(d.get("alasan") or "")
    hasil = [u for u in (model.moderasi(i, status, g.user.username, alasan) for i in ids) if u]
    sps_audit.catat("ulasan", ("Tampilkan" if status == "tampil" else "Tolak") + f" {len(hasil)} komentar sekaligus",
                    "", {"ids": [u["id"] for u in hasil], "alasan": alasan or None})
    return jsonify(jumlah=len(hasil), menunggu=model.jumlah_menunggu())


@bp.route("/api/notifikasi")
def api_notifikasi():
    """Pemberitahuan @sebut & balasan untuk pengguna ini."""
    return jsonify(model.notifikasi(g.user.username))


@bp.route("/api/notifikasi/baca", methods=["POST"])
def api_notifikasi_baca():
    model.tandai_dibaca(g.user.username)
    return jsonify(ok=True)


@bp.route("/api/pengguna")
def api_cari_pengguna():
    """Saran @sebut: username & nama pengguna aktif yang cocok (maks. 8)."""
    from superset import db
    from flask_appbuilder.security.sqla.models import User
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify([])
    pola = f"%{q}%"
    hasil = (db.session.query(User.username, User.first_name, User.last_name)
             .filter(User.active.is_(True))
             .filter(User.username.ilike(pola) | User.first_name.ilike(pola) | User.last_name.ilike(pola)).limit(8))
    return jsonify([{"username": u, "nama": f"{a or ''} {b or ''}".strip()} for u, a, b in hasil])


@bp.route("/api/menunggu")
def api_menunggu():
    """Jumlah menunggu moderasi untuk lencana di cangkang (0 bila bukan Superadmin)."""
    return jsonify(menunggu=model.jumlah_menunggu() if sps_superadmin.adalah() else 0)


@bp.route("/api/moderasi/<int:ulasan_id>", methods=["POST"])
@sps_superadmin.khusus()
def api_moderasi(ulasan_id: int):
    d = request.get_json(silent=True) or {}
    status = d.get("status")
    if status not in ("tampil", "ditolak"):
        return jsonify(error="Status harus tampil atau ditolak"), 400
    u = model.moderasi(ulasan_id, status, g.user.username, str(d.get("alasan") or ""))
    if u is None:
        return jsonify(error="Tidak ditemukan"), 404
    log.info("ALDx ulasan: %s memoderasi ulasan %s -> %s", g.user.username, ulasan_id, status)
    sps_audit.catat("ulasan", "Tampilkan komentar" if status == "tampil" else "Tolak komentar",
                    f"{u['jenis']} #{u['objek_id']} oleh {u['pengguna']}",
                    {"id": ulasan_id, "alasan": d.get("alasan") or None})
    return jsonify(ulasan=u)
