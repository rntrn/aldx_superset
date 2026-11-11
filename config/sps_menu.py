"""Susunan menu navbar mengikuti alur membuat laporan BI.

    Data        Hubungkan data · Dataset · Persiapan data · Ekstrak
    Kueri       Kueri Visual · SQL Lab · Kueri tersimpan
    Analisis    Studio Visual · Daftar chart · Asisten AI
    Dashboard   Daftar dashboard · Story · Berkas .ald / .aldx
    (Settings, di kanan: Keamanan & Kelola: Pusat Kendali Server, Koneksi database, Riwayat kueri)
Satu fungsi = satu item menu: menu yang mirip dipindah ke Settings (KE_PENGATURAN).

Cara kerja:
    - Superset & modul SPS menambah menu seperti biasa (add_link/add_view).
    - Pada permintaan pertama, `susun()` memindahkan item itu ke kategori di atas (sekali per proses).
      Tidak bisa saat start karena FLASK_APP_MUTATOR berjalan SEBELUM Superset menambah menunya.
    - Item tambahan (mis. "Persiapan data") tidak punya izin sendiri: izinnya mengikuti menu dasar
      di IZIN_DASAR. `perluas_izin()` dipanggil dari SpsSecurityManager.get_user_menu_access.
    - Kategori tampil bila minimal satu isinya boleh dibuka.

Nama kategori sengaja BUKAN "Data"/"Security"/"Manage": nama itu dipindah Superset ke menu Pengaturan.
"""

from __future__ import annotations

import logging
import threading

log = logging.getLogger(__name__)

# (nama kategori, label, [(nama item, label, href | None = item Superset yang sudah ada)])
SUSUNAN = [
    ("SPS Data", "Data", [
        ("Hubungkan data", "Hubungkan data", "/pusat-kendali/?tab=hubungkan"),
        ("Datasets", "Dataset", None),
        ("Persiapan data", "Persiapan data", "/studio/?tab=prep"),
        ("Ekstrak data", "Ekstrak ke ALDx Engine", "/pusat-kendali/?tab=ekstrak"),
    ]),
    ("SPS Kueri", "Kueri", [
        ("Kueri Visual", "Kueri Visual (tanpa SQL)", "/kueri/"),
        ("SQL Editor", "SQL Lab", None),
        ("Saved Queries", "Kueri tersimpan", None),
    ]),
    ("SPS Analisis", "Analisis & Visual", [
        ("Studio Visual", "Studio Visual", None),
        ("Charts", "Daftar chart", None),
        ("Asisten AI", "Asisten AI", None),
    ]),
    ("SPS Dashboard", "Dashboard & Story", [
        ("Dashboards", "Daftar dashboard", None),
        ("Story", "Story (rangkuman dashboard)", "/asisten/?tab=story"),
        ("Berkas ALDx", "Berkas .ald / .aldx", "/berkas/"),
        ("Sematkan", "Sematkan ke web lain", "/sematkan/"),
    ]),
]

# Menu Superset yang fungsinya sudah tercakup menu lain -> dipindah ke Settings > Manage (untuk admin):
#   Koneksi database  (sudah ada di Data > Hubungkan data, daftar "Koneksi tersimpan")
#   Riwayat kueri     (sudah ada di SQL Lab, panel "Query history")
KE_PENGATURAN = [("Databases", "Koneksi database (lanjutan)"), ("Query Search", "Riwayat kueri")]

# Item tambahan -> menu yang izinnya dipakai
KHUSUS_ADMIN = {"Hubungkan data", "Ekstrak data", "Sematkan"}      # halamannya memang hanya untuk Admin
IZIN_DASAR = {
    "Hubungkan data": "Pusat Kendali Server",
    "Ekstrak data": "Pusat Kendali Server",
    "Persiapan data": "Studio Visual",
    "Kueri Visual": "SQL Editor",
    "Story": "Asisten AI",
    "Berkas ALDx": "Dashboards",
    "Sematkan": "Pusat Kendali Server",
}
KATEGORI = {k: [n for n, _, _ in isi] for k, _, isi in SUSUNAN}

_kunci = threading.Lock()
_sudah = {"ok": False}


def _lepas(menu: list, nama: str):
    """Cari item bernama `nama` di pohon menu, lepaskan dari induknya, kembalikan item itu."""
    for i, item in enumerate(menu):
        if item.name == nama:
            return menu.pop(i)
        if item.childs:
            hasil = _lepas(item.childs, nama)
            if hasil is not None:
                return hasil
    return None


def susun(appbuilder) -> None:
    """Pindahkan item menu ke susunan alur BI. Aman dipanggil berkali-kali (hanya sekali bekerja)."""
    if _sudah["ok"]:
        return
    with _kunci:
        if _sudah["ok"]:
            return
        from flask_appbuilder.menu import MenuItem
        menu = appbuilder.menu.menu
        kategori_baru = []
        for nama_kat, label_kat, isi in SUSUNAN:
            anak = []
            for nama, label, href in isi:
                item = _lepas(menu, nama)
                if item is None and href is None:
                    continue                               # menu Superset itu tidak ada di versi ini
                if item is None:
                    item = MenuItem(name=nama, href=href, label=label)
                item.label = label
                anak.append(item)
            if anak:
                kategori_baru.append(MenuItem(name=nama_kat, label=label_kat, childs=anak))
        kelola = next((m for m in menu if m.name == "Manage"), None)
        for nama, label in KE_PENGATURAN:
            item = _lepas(menu, nama)
            if item is not None and kelola is not None:
                item.label = label
                kelola.childs.append(item)
        # Buang kategori lama yang kini kosong (mis. "SQL Lab", "Data")
        menu[:] = [m for m in menu if m.childs or m.href or m.baseview or m.name == "-"]
        # Sisipkan setelah "Home" (bila ada), sebelum kategori lain
        posisi = next((i + 1 for i, m in enumerate(menu) if m.name == "Home"), 0)
        menu[posisi:posisi] = kategori_baru
        _sudah["ok"] = True
        log.info("SPS menu: disusun ulang (%s)", ", ".join(k.label for k in kategori_baru))


def perluas_izin(boleh: set[str], admin: bool) -> set[str]:
    """Tambahkan item tambahan & kategori SPS ke himpunan menu yang boleh dibuka pengguna."""
    boleh = set(boleh)
    boleh |= {item for item, dasar in IZIN_DASAR.items()
              if dasar in boleh and (admin or item not in KHUSUS_ADMIN)}
    boleh |= {kat for kat, isi in KATEGORI.items() if boleh.intersection(isi)}
    return boleh


def nama_izin_dasar() -> set[str]:
    return set(IZIN_DASAR.values())


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: susun menu pada permintaan pertama (setelah Superset selesai menambah menu)."""
    @app.before_request
    def _susun_menu():
        if not _sudah["ok"]:
            try:
                from superset.extensions import appbuilder
                susun(appbuilder)
            except Exception:  # noqa: BLE001 - menu gagal disusun tidak boleh mematikan halaman
                _sudah["ok"] = True
                log.exception("SPS menu: gagal menyusun ulang, memakai menu bawaan")
