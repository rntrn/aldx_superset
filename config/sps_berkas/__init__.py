"""Berkas ALDx: .ald (workbook, tanpa data) & .aldx (paket, bisa membawa data).

Untuk pengguna (menu Dashboard & Story › Berkas ALDx, halaman /berkas/):
    Ekspor  pilih dashboard / chart / dataset -> pilih .ald atau .aldx (+ data) -> kunci server atau kata sandi
    Impor   pilih berkas -> lihat isi -> pilih koneksi tujuan -> Impor -> buka hasilnya

Keamanan:
    - Isi selalu dienkripsi AES-256-GCM & ditandatangani (sandi.py). Diubah sedikit saja = ditolak.
    - Berkas TIDAK PERNAH membawa alamat server, nama user, atau password koneksi.
    - Data di .aldx diambil sebagai pembuat (RLS berlaku): hanya baris yang boleh ia lihat.
    - Impor hanya ke koneksi yang boleh diakses penerima; data .aldx masuk ke ALDx Engine.

Struktur:
    sandi.py        format biner, enkripsi, tanda tangan
    paket.py        ekspor/periksa/impor (memakai perintah ekspor-impor resmi Superset)
    tampilan.py     halaman & API /berkas/
    halaman.html, static/berkas.js   antarmuka
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: halaman /berkas/ (menu disusun di sps_menu)."""
    from sps_berkas import tampilan
    app.register_blueprint(tampilan.bp)
