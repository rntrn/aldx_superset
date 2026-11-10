"""Komentar & rating dashboard/chart, dimoderasi Superadmin.

Untuk pengguna: buka dashboard atau chart di aplikasi, tekan tombol komentar di bilah atas
(atau tombol pada kartu dashboard). Beri 1-5 bintang dan/atau komentar.
Untuk Superadmin: Kelola › Moderasi ulasan (/ulasan/moderasi/) -> Tampilkan / Tolak (dengan alasan).

Pengaturan: Pusat Kendali › Pengaturan › "Komentar perlu disetujui Superadmin" (bawaan: ya).
Ulasan Superadmin sendiri langsung tampil.

Struktur:
    model.py        tabel sps_ulasan (dibuat otomatis) & kueri
    tampilan.py     API & halaman moderasi
    moderasi.html   halaman moderasi
    Panel ulasan di cangkang: config/sps_app/static/ulasan.js
"""


def daftarkan(app) -> None:
    from sps_ulasan import tampilan
    app.register_blueprint(tampilan.bp)
