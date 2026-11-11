"""Halaman galat ALDx bergaya "Poster Tebasan": 403 (tidak berhak) dan 404 (tidak ditemukan).

    from sps_tolak import halaman_tolak
    return halaman_tolak("Pusat Kendali hanya untuk Admin.")

404 untuk browser dipasang lewat daftarkan(app) (FLASK_APP_MUTATOR) menggantikan halaman bawaan Superset
yang berbahasa Inggris & tanpa identitas. Permintaan API / JSON tetap menerima JSON.
Warna mengikuti /identitas/tema.css (Pusat Kendali > Identitas & Tema).
"""

from __future__ import annotations

from html import escape

_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{judul}</title><link rel="icon" href="/identitas/berkas/favicon"><link rel="stylesheet" href="/identitas/tema.css">
<style>
*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}
body{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:48px clamp(24px,7vw,96px);color:#fff;
  font-family:var(--sps-font,'Plus Jakarta Sans','Segoe UI',Arial,sans-serif);position:relative;overflow:hidden;
  background:linear-gradient(155deg,var(--sps-utama-gelap,#121214),var(--sps-utama,#18181B) 55%,var(--sps-utama-terang,#4A4A4F) 140%)}}
.logo{{position:absolute;top:32px;left:clamp(24px,7vw,96px);height:36px}}
.kode{{font-size:clamp(120px,24vw,320px);font-weight:800;line-height:.8;letter-spacing:-.06em;margin:0;position:relative;
  display:inline-block;color:transparent;-webkit-text-stroke:2px rgba(255,255,255,.85)}}
.kode::after{{content:"";position:absolute;left:-6%;right:-10%;top:52%;height:.06em;background:var(--sps-aksen,#E11D74);
  transform:rotate(-14deg);box-shadow:0 0 30px var(--sps-aksen,#E11D74)}}
h1{{font-size:clamp(24px,3vw,38px);margin:40px 0 10px;letter-spacing:-.02em}}
p{{max-width:560px;color:rgba(255,255,255,.72);line-height:1.6;margin:0 0 30px;font-size:16px}}
.aksi{{display:flex;gap:12px;flex-wrap:wrap}}
a{{display:inline-flex;align-items:center;gap:10px;text-decoration:none;font-weight:700;padding:13px 20px;
  border-radius:var(--sps-sudut,8px);border:1.5px solid rgba(255,255,255,.4);color:#fff}}
a.utama{{background:var(--sps-aksen,#E11D74);border-color:var(--sps-aksen,#E11D74);color:var(--sps-teks-aksen,#fff)}}
a:hover,a:focus-visible{{outline:none;border-color:#fff}}
</style></head><body>
<img class="logo" src="/identitas/berkas/logo_putih" alt="">
<p class="kode" aria-hidden="true">{kode}</p>
<h1>{judul}</h1><p>{pesan}</p>
<div class="aksi"><a class="utama" href="/app/" target="_top">Kembali ke Beranda <span aria-hidden="true">→</span></a>
<a href="javascript:history.back()">Halaman sebelumnya</a></div>
</body></html>"""


def halaman_galat(kode: int, judul: str, pesan: str):
    teks = _HTML.format(kode=kode, judul=escape(judul), pesan=escape(pesan))
    return teks, kode, {"Content-Type": "text/html; charset=utf-8"}


def halaman_tolak(pesan: str, kode: int = 403):
    return halaman_galat(kode, "Halaman ini tidak tersedia untuk akun Anda", pesan)


def daftarkan(app) -> None:
    """404 bermerek untuk browser. Handler per kode didahulukan Flask di atas handler HTTPException Superset."""
    from flask import jsonify, request

    def tidak_ditemukan(galat):
        mau_html = "text/html" in request.accept_mimetypes and not request.path.startswith("/api/")
        if mau_html and not request.is_json and not app.config.get("DEBUG"):
            return halaman_galat(404, "Halaman tidak ditemukan",
                                 "Alamat ini tidak ada atau sudah dipindah. Kembali ke Beranda, atau tekan Ctrl + K "
                                 "untuk mencari dashboard, chart, dan dataset.")
        return jsonify(errors=[{"message": str(galat), "error_type": "GENERIC_BACKEND_ERROR", "level": "error"}]), 404

    app.register_error_handler(404, tidak_ditemukan)
