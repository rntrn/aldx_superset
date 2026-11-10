"""Halaman "tidak berhak" yang rapi (403), dipakai semua halaman ALDx yang dibuka lewat alamat langsung.

    from sps_tolak import halaman_tolak
    return halaman_tolak("Pusat Kendali hanya untuk Admin.")
"""

from __future__ import annotations

from html import escape

_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tidak berhak</title><link rel="stylesheet" href="/identitas/tema.css">
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--sps-latar,#F5F6F8);
font-family:var(--sps-font,'Plus Jakarta Sans','Segoe UI',Arial,sans-serif);color:#1F2933}}
.k{{background:#fff;border:1px solid #D5DCE4;border-radius:14px;padding:28px 32px;max-width:440px;text-align:center;box-shadow:0 8px 24px rgba(15,23,42,.06)}}
.i{{font-size:36px}}h1{{font-size:18px;margin:8px 0}}p{{color:#5F6B7A;line-height:1.5;margin:0 0 18px}}
a{{display:inline-block;background:var(--sps-utama,#1E2A44);color:#fff;text-decoration:none;border-radius:8px;padding:8px 16px;font-weight:600}}</style>
</head><body><div class="k"><div class="i">🔒</div><h1>Halaman ini tidak tersedia untuk akun Anda</h1><p>{pesan}</p>
<a href="/app/" target="_top">Kembali ke Beranda</a></div></body></html>"""


def halaman_tolak(pesan: str, kode: int = 403):
    return _HTML.format(pesan=escape(pesan)), kode, {"Content-Type": "text/html; charset=utf-8"}
