"""ALDx Kueri Visual — menyusun kueri SQL tanpa mengetik (/kueri/).

Alur untuk pengguna:
    1. pilih database & skema  -> hanya tabel skema itu yang tampil
    2. klik dua kali tabel      -> langsung jadi kueri & dijalankan
    3. klik dua kali tabel lain -> digabung (JOIN) otomatis lewat foreign key / kolom bernama sama
    4. centang kolom, ringkas (jumlah, rata-rata, ...), filter, urutkan
    5. Jalankan / Buka di SQL Lab / Simpan jadi dataset -> lanjut ke Studio Visual

Keamanan: halaman ini hanya HTML + JavaScript. Semua daftar tabel, kolom, dan eksekusi kueri
memakai API resmi Superset (/api/v1/database, /api/v1/sqllab/execute, /api/v1/dataset), jadi
izin database, SQL Lab, dan aturan RLS sama persis dengan SQL Lab.

Struktur:
    tampilan.py         halaman /kueri/ (cek login & izin SQL Lab)
    halaman.html        tata letak
    static/kueri.js     penyusun kueri (tabel, gabung otomatis, kolom, filter, SQL)
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: halaman /kueri/ (menu disusun di sps_menu)."""
    from sps_kueri import tampilan
    app.register_blueprint(tampilan.bp)
