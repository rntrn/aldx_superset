"""Panduan ALDx di dalam aplikasi (/panduan/): dokumentasi Markdown di docs/ ditampilkan sebagai situs.

Tanpa internet dan tanpa hosting terpisah: berkas docs/ di-mount read-only ke container
(docker-compose.yml: ./docs -> /app/docs, CARA-PASANG.md -> /app/docs-akar).
Siapa pun yang sudah login boleh membaca. Perubahan Markdown langsung terlihat (tanpa restart).

    tampilan.py   halaman, gambar, PDF, pencarian
    halaman.html  kerangka: sidebar per peran, cari, isi, daftar isi halaman
"""


def daftarkan(app) -> None:
    from sps_panduan import tampilan
    app.register_blueprint(tampilan.bp)
