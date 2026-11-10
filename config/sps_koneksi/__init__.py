"""ALDx Koneksi — wizard "Hubungkan data" (menu Data > Hubungkan data).

Dua jalur, dipilih admin di langkah pertama wizard:
    SERVER DATABASE / DATA WAREHOUSE  -> isi formulir -> Uji -> Simpan sebagai koneksi Superset
                                          (selalu hanya-baca; password terenkripsi)
    BERKAS (Access, Excel, CSV, ...)  -> unggah -> pilih tabel -> salin ke ALDx Engine + dataset

Struktur modul (baca berurutan):
    katalog.py    daftar jenis database: isian formulir, templat URI, driver
    koneksi.py    uji & simpan koneksi
    impor.py      baca berkas & salin ke ALDx Engine
    tampilan.py   API /hubungkan/... (khusus Admin)
    tab.js        tampilan wizard di Pusat Kendali

Menambah jenis database: tambah satu Jenis(...) di katalog.py + paket driver di
docker/wheels/paket.txt (lihat docker/wheels/README.md).
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: API wizard Hubungkan data."""
    from sps_koneksi import tampilan
    app.register_blueprint(tampilan.bp)
