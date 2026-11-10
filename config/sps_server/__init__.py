"""ALDx Server — pengelolaan kemampuan server dari satu halaman.

Halaman: http://localhost:8088/pusat-kendali/  (menu Settings → Pusat Kendali Server, khusus Admin)

Struktur modul (baca berurutan):
    lingkungan.py   alamat metadb, ALDx Engine, Redis & identitas node dari .env
    skema.py        DAFTAR SEMUA PENGATURAN (kunci, bawaan, batas)
    penyimpanan.py  simpan pengaturan pusat, riwayat, detak node (tabel sps_server_*, sps_node)
    tuning.py       AUTO-TUNING: CPU/RAM -> jatah container & jumlah proses
    konfig.py       pengaturan -> konfigurasi Superset (cache, backgrounder, batas, upload)
    jalankan.py     peluncur proses tiap container + detak ke Pusat Kendali
    gateway.py      konfigurasi nginx (pembagi beban & failover antar-node)
    terapkan.py     dipanggil scripts\\terapkan-server.ps1 (nilai yang butuh restart)
    izin.py         matriks hak akses kemampuan + izin upload ke ALDx Engine
    monitor.py      data halaman Status
    tampilan.py     halaman & API /pusat-kendali/
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: pengaturan langsung, penjaga upload, halaman & menu."""
    from sps_server.tampilan import daftarkan as _daftarkan
    _daftarkan(app)


def siapkan() -> list[str]:
    """build-dashboards: tabel, izin menu Admin, database upload."""
    from sps_server.tampilan import siapkan as _siapkan
    return _siapkan()
