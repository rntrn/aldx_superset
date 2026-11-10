"""Halaman login beranimasi (GET /login/), memakai identitas & warna dari Pusat Kendali.

Hanya TAMPILAN yang diganti: formulir tetap dikirim ke POST /login/ milik Superset
(LDAP / akun lokal, batas percobaan, CSRF), jadi keamanan login tidak berubah.
    /login/?klasik=1   halaman login bawaan Superset (cadangan bila ada masalah tampilan)
"""

from __future__ import annotations

from pathlib import Path

from flask import get_flashed_messages, redirect, render_template_string, request

from sps_identitas import tema

HTML = Path(__file__).with_name("login.html")
PESAN = {  # pesan bawaan Flask-AppBuilder -> bahasa Indonesia
    "Invalid login. Please try again.": "Nama pengguna atau password salah. Coba lagi.",
    "Too many login attempts. Please try again later.": "Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi.",
}


def daftarkan(app) -> None:
    @app.before_request
    def _halaman_login():
        if request.method != "GET" or request.path.rstrip("/") != "/login" or request.args.get("klasik"):
            return None
        from flask_login import current_user
        from flask_wtf.csrf import generate_csrf
        if current_user.is_authenticated:
            return redirect(app.config["SPS_IDENTITAS"]["halaman_depan"])
        n = app.config["SPS_IDENTITAS"]
        pesan = [PESAN.get(m, m) for _, m in get_flashed_messages(with_categories=True)]
        if any(m.startswith("Akun dikunci") for m in pesan):   # pesan kunci sudah menjelaskan; buang pesan umum
            pesan = list(dict.fromkeys(m for m in pesan if m.startswith("Akun dikunci")))
        lanjut = request.args.get("next", "")
        return render_template_string(
            HTML.read_text(encoding="utf-8"), n=n, p=tema.palet(n), v=app.config["SPS_IDENTITAS_VERSI"],
            kaki=tema.teks_kaki(n), pesan=pesan, csrf=generate_csrf(),
            aksi="/login/" + (f"?next={_aman(lanjut)}" if lanjut else ""))


def _aman(url: str) -> str:
    """Hanya alamat di dalam aplikasi yang boleh dijadikan tujuan setelah login."""
    from urllib.parse import quote
    return quote(url, safe="/?=&") if url.startswith("/") and not url.startswith("//") else ""
