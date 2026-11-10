"""ALDx Engine — database analitik internal (ClickHouse di container "engine"), padanan
mesin analitik internal untuk ekstrak & upload.

Dipakai untuk:
    - EKSTRAK: salinan dataset Oracle/ClickHouse DMP/MySQL yang disegarkan terjadwal
    - UPLOAD Excel/CSV dari menu Superset
    - hasil PREDIKSI (forecast) yang disimpan sebagai dataset

Struktur modul (baca berurutan):
    klien.py     koneksi ke engine (clickhouse-connect; chDB untuk pengujian)
    tabel.py     tebak tipe kolom, buat tabel MergeTree, isi penuh (tukar atomik) / tambahan
    ekstrak.py   daftar ekstrak, jadwal, penyegaran, dataset + RLS, pindahkan chart
    tugas.py     tugas backgrounder (antrean "ekstrak") + penjadwal tiap 5 menit
    upload.py    izinkan upload Excel/CSV ke engine (HANYA ke engine)
    tampilan.py  API tab "Ekstrak" di Pusat Kendali
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: API ekstrak + upload ke engine."""
    import logging

    from sps_engine import tampilan, upload
    app.register_blueprint(tampilan.bp)
    try:
        upload.pasang()
    except Exception:  # noqa: BLE001 - upload gagal dipasang tidak boleh mematikan Superset
        logging.getLogger(__name__).exception("ALDx engine: gagal memasang upload")


def siapkan() -> list[str]:
    """build-dashboards: koneksi Superset ke engine + tabel metadata ekstrak."""
    from sps_engine import ekstrak, klien
    hasil = [f"koneksi '{ekstrak.database_engine().database_name}'"]
    ekstrak.daftar()                                  # membuat tabel sps_ekstrak bila belum ada
    try:
        klien.klien().perintah(f"CREATE DATABASE IF NOT EXISTS {klien.nama_db()}")
        hasil.append(f"database engine '{klien.nama_db()}' siap")
    except Exception as exc:  # noqa: BLE001
        hasil.append(f"engine belum bisa dihubungi ({str(exc).splitlines()[0][:120]})")
    return hasil
