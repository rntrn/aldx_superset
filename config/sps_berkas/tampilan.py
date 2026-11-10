"""Halaman Berkas ALDx (/berkas/): ekspor & impor .ald / .aldx.

    GET  /berkas/                halaman (semua pengguna yang boleh membuka dashboard)
    POST /berkas/api/ekspor      {jenis, ids, format, data, sandi, catatan}     -> unduhan berkas, atau
                                 202 {tugas} bila .aldx berisi data dikerjakan backgrounder (sps_berkas/tugas.py)
    GET  /berkas/api/tugas       ekspor latar milik pengguna (24 jam)
    GET  /berkas/api/tugas/<id>/unduh                                           -> unduhan berkas
    POST /berkas/api/periksa     multipart: berkas, sandi                        -> isi + saran koneksi
    POST /berkas/api/impor       multipart: berkas, sandi, peta (JSON), mode, data -> objek yang dibuat

Izin dicek di paket.py: ekspor butuh "can export" (Dashboard/Chart/Dataset), impor butuh "can write".
Berkas yang diunggah hanya dibaca di memori, tidak disimpan di server.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, Response, current_app, g, jsonify, redirect, render_template_string, request

from sps_berkas import paket, tugas
from sps_berkas.sandi import GalatBerkas

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
MENU = "Berkas ALDx"
bp = Blueprint("sps_berkas", __name__, url_prefix="/berkas",
               static_folder=str(FOLDER / "static"), static_url_path="/static")


def _maks_mb() -> int:
    """Batas unggah berkas (P2): yang terkecil dari "berkas.ukuran_mb" dan batas impor berkas; 0 = tanpa batas."""
    from sps_server import batas, penyimpanan
    atur = penyimpanan.nilai_semua()
    batasan = [b for b in (int(atur.get("berkas.ukuran_mb") or 0), batas.berlaku(atur, "impor.ukuran_mb") or 0) if b]
    return min(batasan) if batasan else 0


@bp.before_request
def _wajib_login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        if request.path.startswith("/berkas/api/"):
            return jsonify(error="Silakan login"), 401
        return redirect(f"/login/?next={request.path}")
    return None


@bp.errorhandler(GalatBerkas)
def _galat(exc):
    return jsonify(error=str(exc)), 400


@bp.route("/")
def beranda():
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "halaman.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), maks_mb=_maks_mb(),
                                  app_name=current_app.config.get("APP_NAME", "ALDx"))


def _unggahan() -> tuple[bytes, str | None]:
    f = request.files.get("berkas")
    if f is None:
        raise GalatBerkas("Pilih berkas .ald / .aldx.")
    maks = _maks_mb()
    # Baca paling banyak batas + 1 byte: berkas raksasa ditolak tanpa memenuhi RAM.
    data = f.read(maks * 1024 * 1024 + 1) if maks else f.read()
    if maks and len(data) > maks * 1024 * 1024:
        raise GalatBerkas(f"Berkas lebih dari {maks} MB (Pusat Kendali › Pengaturan › Batas data: "
                          "Berkas .ald/.aldx: ukuran maksimal).")
    return data, (request.form.get("sandi") or None)


@bp.route("/api/ekspor", methods=["POST"])
def api_ekspor():
    d = request.get_json(silent=True) or {}
    try:
        ids = [int(i) for i in d.get("ids") or []]
    except (TypeError, ValueError):
        raise GalatBerkas("Pilihan objek tidak valid.") from None
    permintaan = {"jenis": str(d.get("jenis", "")), "ids": ids, "format_": str(d.get("format", "ald")),
                  "dengan_data": bool(d.get("data")), "kata_sandi": d.get("sandi") or None,
                  "catatan": str(d.get("catatan") or "")}
    # .aldx berisi data bisa lama: kerjakan di backgrounder bila ada (P1), selain itu langsung.
    if permintaan["dengan_data"] and permintaan["format_"] == "aldx" and tugas.ada_worker():
        paket.periksa_ekspor(**permintaan)                    # galat izin/pengaturan langsung terlihat
        return jsonify(tugas=tugas.antrekan(g.user.username, permintaan)), 202
    nama, isi, _ = paket.ekspor(**permintaan)
    return _unduhan(nama, isi)


def _unduhan(nama: str, isi: bytes) -> Response:
    return Response(isi, mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nama}"', "X-Nama-Berkas": nama})


@bp.route("/api/tugas")
def api_tugas():
    """Ekspor latar milik pengguna ini (24 jam terakhir)."""
    return jsonify(tugas.daftar(g.user.username))


@bp.route("/api/tugas/<tugas_id>/unduh")
def api_unduh_tugas(tugas_id: str):
    hasil = tugas.ambil_isi(tugas_id, g.user.username)
    if hasil is None:
        return jsonify(error="Berkas tidak ditemukan, belum siap, atau sudah kedaluwarsa (24 jam)."), 404
    return _unduhan(*hasil)


@bp.route("/api/periksa", methods=["POST"])
def api_periksa():
    data, sandi = _unggahan()
    try:
        return jsonify(paket.periksa(data, sandi))
    except GalatBerkas as exc:
        perlu = "sandi" in str(exc).lower() and paket.sandi.kepala(data).get("enkripsi") == "sandi"
        return jsonify(error=str(exc), perlu_sandi=perlu), 400


@bp.route("/api/impor", methods=["POST"])
def api_impor():
    data, sandi = _unggahan()
    try:
        peta = json.loads(request.form.get("peta") or "{}")
    except ValueError:
        raise GalatBerkas("Pilihan koneksi tujuan tidak valid.") from None
    return jsonify(paket.impor(data, sandi, peta, request.form.get("mode", "salinan"),
                               request.form.get("data", "1") == "1"))
