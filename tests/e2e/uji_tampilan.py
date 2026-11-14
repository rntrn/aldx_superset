"""Uji tampilan ALDx (end-to-end) dengan Playwright: membuka halaman seperti pengguna dan memeriksa hasilnya.

Menangkap regresi yang tidak terlihat oleh sps_uji.py (uji API/modul), terutama setelah Superset dinaikkan versinya:
menu, Studio, dashboard (termasuk sisipan klik kanan & bilah atas ALDx), Panduan, dan galat JavaScript.

Pakai:
    pip install playwright && python -m playwright install chromium
    ALDX_URL=http://localhost:8088 ALDX_USER=admin ALDX_PASSWORD=... python tests/e2e/uji_tampilan.py
    (opsional) ALDX_CHROMIUM=/jalur/chrome   memakai Chromium yang sudah terpasang

Keluar 0 = semua lulus. Tangkapan layar tiap uji: tests/e2e/hasil/<nama>.png (diunggah CI sebagai artefak).
Menambah uji: tulis fungsi `uji_<nama>(hal)` di bawah; `periksa(syarat, pesan)` menggagalkan uji.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Frame, Page, sync_playwright

URL = os.environ.get("ALDX_URL", "http://localhost:8088").rstrip("/")
PENGGUNA, SANDI = os.environ.get("ALDX_USER", "admin"), os.environ.get("ALDX_PASSWORD", "")
HASIL = Path(__file__).with_name("hasil")
TUNGGU_MS = 30000


class Gagal(AssertionError):
    pass


def periksa(syarat: bool, pesan: str) -> None:
    if not syarat:
        raise Gagal(pesan)


def bingkai(hal: Page, bagian: str) -> Frame:
    """Halaman ALDx tampil di dalam bingkai cangkang (/app/?p=...): cari frame yang alamatnya memuat `bagian`."""
    batas = time.monotonic() + TUNGGU_MS / 1000
    while time.monotonic() < batas:
        for f in hal.frames:
            if bagian in f.url:
                return f
        hal.wait_for_timeout(300)
    raise Gagal(f"bingkai {bagian} tidak terbuka")


# --- Uji -----------------------------------------------------------------------------------------
def uji_login_dan_beranda(hal: Page) -> str:
    hal.goto(f"{URL}/login/")
    kaki = hal.inner_text(".kaki")
    periksa(re.search(r"v\d{4}\.\d{2}\.\d{2}", kaki) is not None, f"versi tidak tampil di kaki login: {kaki!r}")
    hal.fill("#username", PENGGUNA); hal.fill("#password", SANDI); hal.click("#tombol")
    hal.wait_for_url(re.compile(r"/app/"), timeout=TUNGGU_MS)
    hal.wait_for_selector("#versiBeranda a", timeout=TUNGGU_MS)
    href = hal.get_attribute("#versiBeranda a", "href") or ""
    periksa("/releases/tag/v" in href, f"versi Beranda tidak menaut ke rilis: {href}")
    menu = hal.locator(".nav a").count()
    periksa(menu >= 15, f"menu terlalu sedikit: {menu}")
    return f"{menu} menu; versi menaut {href.rsplit('/', 1)[-1]}"


def uji_studio(hal: Page) -> str:
    hal.goto(f"{URL}/studio/")
    f = bingkai(hal, "/studio/")
    f.wait_for_selector("#daftarDimensi, .daftarBidang, #pilihTanda", timeout=TUNGGU_MS)
    f.select_option("#pilihTanda", "tabel")
    f.wait_for_timeout(500)
    periksa(f.is_visible("#barisAmbang"), "baris Ambang tidak tampil untuk Tabel")
    f.select_option("#pilihTanda", "garis")
    f.wait_for_timeout(500)
    periksa(not f.is_visible("#barisAmbang"), "baris Ambang tampil untuk Garis")
    jenis = f.locator("#pilihTanda option").count()
    periksa(jenis >= 20, f"jenis chart di Studio terlalu sedikit: {jenis}")
    return f"{jenis} pilihan jenis; Ambang hanya untuk Angka/Tabel"


def uji_dashboard(hal: Page) -> str:
    hal.goto(f"{URL}/superset/dashboard/latihan-wilayah/")
    f = bingkai(hal, "/superset/dashboard/")
    f.wait_for_selector(".dashboard-component-chart-holder", timeout=TUNGGU_MS)
    f.wait_for_timeout(8000)                                  # chart memuat data
    chart = f.locator(".dashboard-component-chart-holder").count()
    galat = f.locator(".dashboard-component-chart-holder .alert-danger, [data-test='alert-error']").count()
    periksa(chart >= 3, f"chart dashboard terlalu sedikit: {chart}")
    periksa(galat == 0, f"{galat} chart menampilkan galat")
    periksa(hal.locator(".chip-segar").is_visible(), "label kesegaran data tidak tampil")
    periksa(hal.locator("#bukaTelusur").is_visible(), "tombol Telusuri tidak tampil di dashboard")
    return f"{chart} chart tanpa galat; kesegaran & Telusuri tampil"


def uji_panduan(hal: Page) -> str:
    hal.goto(f"{URL}/panduan/32-peta-fitur")
    f = bingkai(hal, "/panduan/")
    teks = f.inner_text("body")
    periksa("Peta Fitur" in teks, "bab 32 tidak tampil")
    periksa(re.search(r"Tableau|Power ?BI|Looker", teks) is None, "panduan masih menyebut merek lain")
    return "bab 32 tampil, bebas merek lain"


def uji_pusat_kendali(hal: Page) -> str:
    hal.goto(f"{URL}/pusat-kendali/")
    f = bingkai(hal, "/pusat-kendali/")
    f.wait_for_load_state("networkidle")
    teks = f.inner_text("body")
    periksa("superset" in teks.lower() or "Status" in teks, "Pusat Kendali kosong")
    return "Pusat Kendali terbuka"


UJI = [uji_login_dan_beranda, uji_studio, uji_dashboard, uji_panduan, uji_pusat_kendali]


def main() -> int:
    if not SANDI:
        print("ALDX_PASSWORD belum diisi.")
        return 2
    HASIL.mkdir(exist_ok=True)
    gagal = 0
    with sync_playwright() as pw:
        exe = os.environ.get("ALDX_CHROMIUM")
        peramban = pw.chromium.launch(**({"executable_path": exe} if exe else {}))
        hal = peramban.new_page(viewport={"width": 1440, "height": 900})
        galat_js: list[str] = []
        hal.on("pageerror", lambda e: galat_js.append(str(e)))
        for fungsi in UJI:
            nama, galat_js[:] = fungsi.__name__.removeprefix("uji_"), []
            mulai = time.monotonic()
            try:
                ket = fungsi(hal)
                periksa(not galat_js, f"galat JavaScript: {galat_js[:2]}")
                print(f"  LULUS  {nama:<22} {ket} ({time.monotonic() - mulai:.1f} dtk)")
            except Exception as exc:  # noqa: BLE001 - semua jenis kegagalan dilaporkan, uji lain tetap jalan
                gagal += 1
                print(f"  GAGAL  {nama:<22} {exc}")
            hal.screenshot(path=str(HASIL / f"{nama}.png"))
        peramban.close()
    print(f"{len(UJI) - gagal}/{len(UJI)} uji tampilan lulus")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
