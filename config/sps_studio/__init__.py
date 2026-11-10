"""ALDx Studio — pembuatan chart, dashboard & persiapan data dengan seret-lepas.

Halaman: http://localhost:8088/studio/  (menu navbar "Studio Visual")

Tab:
    Lembar kerja     rak Kolom/Baris/Filter, kartu Marks, "Tampilkan Saya" (drag & drop)
    Dashboard        susun lembar kerja ke kanvas (drag & drop), atur lebar, simpan
    Persiapan data   alur langkah -> dataset baru (hak akses diwariskan)

Struktur modul:
    lembar.py     spesifikasi lembar kerja, aturan Tampilkan Saya, query, -> chart Superset
    bidang.py     panel Data: Dimensi & Ukuran
    dasbor.py     penyusun dashboard -> position_json Superset
    prep.py       persiapan data -> dataset virtual + warisan RLS
    tampilan.py   halaman & API /studio/
    halaman.html  tampilan (markup + gaya)
    static/       studio.js (logika browser), echarts.min.js (pustaka grafik, lokal)
"""


def daftarkan(app) -> None:
    from sps_studio.tampilan import daftarkan as _daftarkan
    _daftarkan(app)


def siapkan() -> str:
    from sps_studio.tampilan import siapkan as _siapkan
    return _siapkan()
