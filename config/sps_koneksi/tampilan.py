"""API wizard "Hubungkan data" (tab di Pusat Kendali) — khusus Admin.

    GET  /hubungkan/tab.js                 skrip tab (dimuat sps_server/halaman.html)
    GET  /hubungkan/api/katalog            jenis database + status driver + jenis berkas
    GET  /hubungkan/api/koneksi            koneksi yang sudah tersimpan (+ skema terpilih)
    GET  /hubungkan/api/koneksi/<id>/skema semua skema + yang dipilih
    POST /hubungkan/api/koneksi/<id>/skema {skema: [...]}  -> hanya skema ini yang tampil di menu lain
    POST /hubungkan/api/uji                {jenis, isian}            -> versi, schema, waktu
    POST /hubungkan/api/simpan             {jenis, isian, nama, skema} -> Database Superset baru
    POST /hubungkan/api/berkas             form-data "berkas"        -> token + pratinjau tabel
    POST /hubungkan/api/berkas/<token>     {tabel: [...], awalan}    -> dataset di ALDx Engine

Berkas unggahan disimpan sementara di folder tmp dan dihapus setelah diimpor
atau setelah 2 jam (mana yang lebih dulu).
"""

from __future__ import annotations

import logging
import secrets
import shutil
import tempfile
import time
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request

from sps_koneksi import impor, katalog, koneksi
from sps_server.tampilan import _khusus_admin

log = logging.getLogger(__name__)
bp = Blueprint("sps_koneksi", __name__, url_prefix="/hubungkan")

FOLDER = Path(tempfile.gettempdir()) / "sps_hubungkan"
UMUR_DETIK = 2 * 3600


def _maks_mb() -> int:
    """Batas ukuran berkas impor yang berlaku (0 = tanpa batas). Diatur di Pusat Kendali › Batas data."""
    from sps_server import batas, penyimpanan
    return batas.berlaku(penyimpanan.nilai_semua(), "impor.ukuran_mb") or 0


def _data() -> dict:
    return request.get_json(silent=True) or {}


# --- Database -------------------------------------------------------------------------------------
@bp.route("/tab.js")
def tab_js():
    return Response(Path(__file__).with_name("tab.js").read_text(encoding="utf-8"), mimetype="text/javascript")


@bp.route("/api/katalog")
@_khusus_admin()
def api_katalog():
    return jsonify(kelompok=katalog.KELOMPOK, jenis=[j.publik for j in katalog.KATALOG],
                   berkas=katalog.BERKAS, maks_mb=_maks_mb())


@bp.route("/api/koneksi")
@_khusus_admin()
def api_koneksi():
    from superset import db
    from superset.models.core import Database
    import sps_skema
    return jsonify([{"id": d.id, "nama": d.database_name, "dialek": d.backend, "dml": d.allow_dml,
                     "skema": sps_skema.pilihan(d)}
                    for d in db.session.query(Database).order_by(Database.database_name)])


def _database(db_id: int):
    from superset import db
    from superset.models.core import Database
    d = db.session.get(Database, db_id)
    if d is None:
        raise ValueError("Koneksi tidak ditemukan")
    return d


@bp.route("/api/koneksi/<int:db_id>/skema", methods=["GET", "POST"])
@_khusus_admin()
def api_skema(db_id: int):
    import sps_skema
    d = _database(db_id)
    if request.method == "POST":
        pilih = sps_skema.simpan(d, [str(s) for s in _data().get("skema") or []])
        log.info("ALDx hubungkan: skema koneksi '%s' = %s oleh %s", d.database_name, pilih or "semua", g.user.username)
        return jsonify(pilih=pilih)
    try:
        return jsonify(koneksi.daftar_skema(d))
    except Exception as exc:  # noqa: BLE001 - database tidak terjangkau
        return jsonify(error=koneksi.pesan_galat(exc)), 400


@bp.route("/api/uji", methods=["POST"])
@_khusus_admin()
def api_uji():
    d = _data()
    try:
        return jsonify(koneksi.uji(d.get("jenis", ""), d.get("isian") or {}))
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - pesan driver diteruskan apa adanya (tanpa password)
        return jsonify(ok=False, error=koneksi.pesan_galat(exc)), 400


@bp.route("/api/simpan", methods=["POST"])
@_khusus_admin()
def api_simpan():
    d = _data()
    try:
        hasil = koneksi.simpan(d.get("jenis", ""), d.get("isian") or {}, d.get("nama", ""), d.get("skema") or [])
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        from superset import db
        db.session.rollback()
        return jsonify(ok=False, error=koneksi.pesan_galat(exc)), 400
    log.info("ALDx hubungkan: koneksi '%s' dibuat oleh %s", hasil["nama"], g.user.username)
    return jsonify(hasil)


# --- Berkas -------------------------------------------------------------------------------------
def _bersihkan_lama() -> None:
    if not FOLDER.exists():
        return
    batas = time.time() - UMUR_DETIK
    for f in FOLDER.iterdir():
        if f.stat().st_mtime < batas:
            shutil.rmtree(f, ignore_errors=True)


def _berkas_token(token: str) -> Path:
    if not token.isalnum():
        raise ValueError("Token berkas tidak sah")
    folder = FOLDER / token
    isi = list(folder.iterdir()) if folder.is_dir() else []
    if not isi:
        raise ValueError("Berkas sudah kedaluwarsa. Unggah ulang.")
    return isi[0]


@bp.route("/api/berkas", methods=["POST"])
@_khusus_admin()
def api_berkas():
    f = request.files.get("berkas")
    if not f or not f.filename:
        raise ValueError("Pilih berkas dulu")
    akhiran = Path(f.filename).suffix.lower()
    if akhiran not in impor.PEMBACA:
        raise ValueError(f"Jenis berkas {akhiran or '(tanpa akhiran)'} belum didukung")
    _bersihkan_lama()
    token = secrets.token_hex(12)
    folder = FOLDER / token
    folder.mkdir(parents=True)
    path = folder / f"{_awalan_saran(f.filename) or 'berkas'}{akhiran}"   # nama aman (tanpa / .. dll.)
    f.save(path)
    try:
        from sps_server import batas, penyimpanan
        batas.periksa_ukuran(path.stat().st_size, penyimpanan.nilai_semua(), "impor.ukuran_mb", "Berkas")
    except ValueError:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    try:
        tabel = impor.pratinjau(path)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return jsonify(token=token, nama=f.filename, jenis=katalog.BERKAS.get(akhiran, akhiran), tabel=tabel,
                   awalan=_awalan_saran(f.filename))


@bp.route("/api/berkas/<token>", methods=["POST"])
@_khusus_admin()
def api_impor(token: str):
    d = _data()
    path = _berkas_token(token)
    pilihan = [str(t) for t in d.get("tabel") or []]
    if not pilihan:
        raise ValueError("Pilih minimal satu tabel")
    hasil = impor.impor(path, pilihan, str(d.get("awalan", "")).strip(), g.user, str(d.get("nama_asli") or path.name)[:200])
    shutil.rmtree(path.parent, ignore_errors=True)
    log.info("ALDx hubungkan: %d tabel diimpor oleh %s", len(hasil), g.user.username)
    return jsonify(hasil=hasil)


def _awalan_saran(nama: str) -> str:
    from sps_engine.tabel import nama_aman
    return nama_aman(Path(nama).stem).lower()[:30]
