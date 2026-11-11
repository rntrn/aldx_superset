"""Alamat /identitas/... dan penerapan identitas ke Superset saat berjalan.

Publik (dipakai halaman login juga):
    GET  /identitas/tema.css               variabel warna, hiasan, animasi
    GET  /identitas/berkas/<nama>          logo | logo_putih | favicon | spinner
Khusus Admin (tab Identitas & Tema di Pusat Kendali):
    GET  /identitas/api                    isian, nilai, preset
    POST /identitas/api                    {"perubahan": {...}}
    POST /identitas/api/preset             {"nama": "djp"}
    POST /identitas/api/berkas/<nama>      unggah logo/favicon (form-data "berkas")
"""

from __future__ import annotations

import logging
import time

from flask import Blueprint, Response, current_app, g, jsonify, redirect, request

from sps_identitas import penyimpanan, skema, tema
from sps_identitas import config_dari

log = logging.getLogger(__name__)
bp = Blueprint("sps_identitas", __name__, url_prefix="/identitas")
DETIK_CEK_ULANG = 10
_status = {"cek": 0.0}


# --- Nilai identitas saat ini (dipakai modul lain) -------------------------------------------------
def nilai() -> dict:
    return current_app.config.get("SPS_IDENTITAS") or skema.bawaan()


def versi() -> str:
    return current_app.config.get("SPS_IDENTITAS_VERSI", "0")


def terapkan(app, paksa: bool = False) -> None:
    """Baca ulang identitas bila versinya berubah, lalu perbarui konfigurasi Superset."""
    v = penyimpanan.versi()
    if not paksa and v == app.config.get("SPS_IDENTITAS_VERSI"):
        return
    app.config.update(config_dari(penyimpanan.baca(), v, app.config["SPS_TOKEN_DASAR"]))
    # Data bootstrap Superset (berisi tema) disimpan sementara 60 detik: kosongkan agar langsung berlaku.
    try:
        from superset.extensions import cache_manager
        from superset.views.base import cached_common_bootstrap_data
        cache_manager.cache.delete_memoized(cached_common_bootstrap_data)
    except Exception:  # noqa: BLE001
        log.debug("ALDx identitas: cache bootstrap tidak dikosongkan", exc_info=True)
    log.info("ALDx identitas: diperbarui (versi %s)", v)


# --- Publik -------------------------------------------------------------------------------------
def _tembolok(resp: Response) -> Response:
    """?v=<versi> cocok -> boleh disimpan browser lama; selain itu selalu periksa ulang."""
    resp.headers["Cache-Control"] = ("public, max-age=604800" if request.args.get("v") == versi()
                                     else "no-cache")
    return resp


@bp.route("/tema.css")
def tema_css():
    return _tembolok(Response(tema.css(nilai(), versi()), mimetype="text/css"))


def _statis_ada(nama_berkas: str) -> bool:
    """True bila berkas ada di folder branding/ (di-mount ke folder static Superset).

    Logo merek pihak lain (mis. instansi) tidak disertakan di repo; bila preset menunjuk
    berkas yang tidak ada, logo dibuat otomatis alih-alih gambar rusak.
    """
    from pathlib import Path
    relatif = tema.STATIS.removeprefix("/static/")
    # folder static aplikasi + jalur mount di docker-compose.yml (./branding -> /app/superset/static/...)
    akar = {current_app.static_folder, "/app/superset/static"} - {None}
    return any((Path(a) / relatif / nama_berkas).is_file() for a in akar)


@bp.route("/berkas/<nama>")
def berkas(nama: str):
    n = nilai()
    if nama == "spinner":
        return _tembolok(Response(tema.svg_spinner(n), mimetype="image/svg+xml"))
    if nama not in skema.BERKAS:
        return Response("tidak ada", status=404)
    sumber = n.get(nama, "")
    if sumber == "unggah" and (isi := penyimpanan.ambil_berkas(nama)):
        return _tembolok(Response(isi[1], mimetype=isi[0]))
    if sumber.startswith("statis:") and _statis_ada(sumber[7:]):
        return redirect(f"{tema.STATIS}/{sumber[7:]}")
    svg =tema.svg_favicon(n) if nama == "favicon" else tema.svg_logo(n, putih=nama == "logo_putih")
    return _tembolok(Response(svg, mimetype="image/svg+xml"))


@bp.route("/tab.js")
def tab_js():
    """Skrip tab Identitas & Tema (dimuat halaman Pusat Kendali)."""
    from pathlib import Path
    return Response((Path(__file__).with_name("tab.js")).read_text(encoding="utf-8"), mimetype="text/javascript")


# --- Admin ---------------------------------------------------------------------------------------
def _admin(fungsi):
    from sps_server.tampilan import _khusus_admin
    return _khusus_admin()(fungsi)


def _jawaban():
    terapkan(current_app._get_current_object(), paksa=True)
    return jsonify(nilai=nilai(), versi=versi())


def _preset_tampil() -> dict:
    """Preset "djp" hanya untuk instalasi DJP (SPS_PRESET=djp atau SPS_PROFIL_DJP=1), bukan perusahaan lain (U20)."""
    import os
    djp = os.environ.get("SPS_PRESET") == "djp" or os.environ.get("SPS_PROFIL_DJP") == "1"
    return {k: v for k, v in skema.PRESET.items() if k != "djp" or djp}


@bp.route("/api")
@_admin
def api_baca():
    return jsonify(grup=list(skema.GRUP.items()), isian=[i.publik for i in skema.ISIAN],
                   preset=[{"nama": k, "label": v["label"], "utama": v["warna_utama"], "aksen": v["warna_aksen"]}
                           for k, v in _preset_tampil().items()],
                   nilai=nilai(), versi=versi())


@bp.route("/api", methods=["POST"])
@_admin
def api_simpan():
    perubahan = (request.get_json(silent=True) or {}).get("perubahan") or {}
    penyimpanan.simpan(perubahan, g.user.username)
    return _jawaban()


@bp.route("/api/preset", methods=["POST"])
@_admin
def api_preset():
    nama = str((request.get_json(silent=True) or {}).get("nama", ""))
    if nama not in _preset_tampil():
        return jsonify(error="Preset tidak dikenal."), 400
    penyimpanan.simpan(skema.nilai_preset(nama), g.user.username)
    return _jawaban()


@bp.route("/api/berkas/<nama>", methods=["POST"])
@_admin
def api_unggah(nama: str):
    f = request.files.get("berkas")
    if not f:
        raise ValueError("Pilih berkas gambar dulu")
    penyimpanan.simpan_berkas(nama, f.mimetype, f.read(skema.BATAS_BERKAS + 1), g.user.username)
    return _jawaban()


# --- Pemasangan -----------------------------------------------------------------------------------
_TAUTAN = '<link id="sps-tema" rel="stylesheet" href="/identitas/tema.css?v={v}">'


def daftarkan(app) -> None:
    app.config["SPS_TOKEN_DASAR"] = app.config["THEME_DEFAULT"]["token"]
    app.register_blueprint(bp)

    @app.before_request
    def _segarkan_identitas():
        if time.monotonic() - _status["cek"] < DETIK_CEK_ULANG:
            return
        _status["cek"] = time.monotonic()
        try:
            terapkan(app)
        except Exception:  # noqa: BLE001 - jangan ganggu permintaan pengguna
            log.exception("ALDx identitas: gagal memuat ulang")

    @app.after_request
    def _sisipkan_css(resp: Response) -> Response:
        """Setiap halaman HTML mendapat tema.css (warna, garis aksen beranimasi, chart muncul halus)."""
        if (resp.mimetype != "text/html" or resp.status_code != 200 or resp.direct_passthrough
                or resp.is_streamed or request.path.startswith("/identitas/")):
            return resp
        html = resp.get_data(as_text=True)
        if 'id="sps-tema"' in html or "</head>" not in html:
            return resp
        resp.set_data(html.replace("</head>", _TAUTAN.format(v=app.config.get("SPS_IDENTITAS_VERSI", "0"))
                                   + "</head>", 1))
        return resp
