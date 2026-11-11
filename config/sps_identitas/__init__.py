"""ALDx Identitas — nama aplikasi, perusahaan, logo, favicon, warna, huruf, hiasan & animasi.

Diatur di Pusat Kendali > Identitas & Tema (atau installer), berlaku TANPA restart:
setiap node memeriksa versi identitas tiap ±10 detik lalu memperbarui tema Superset.

Struktur modul (baca berurutan):
    skema.py        daftar isian, nilai bawaan, preset (netral, navy, hijau, ...), validasi
    penyimpanan.py  tabel sps_identitas & sps_identitas_berkas di database metadata
    tema.py         identitas -> token tema Superset, CSS bersama, logo/favicon/spinner SVG
    tampilan.py     /identitas/... (CSS, berkas, API admin) + penyisipan CSS ke semua halaman
    login.html      halaman login beranimasi (lihat sps_identitas/login.py)
"""

from __future__ import annotations

import os
from typing import Any


def tema_awal(token_dasar: dict[str, Any]) -> dict[str, Any]:
    """Dipanggil superset_config saat start: identitas dari database -> nilai config awal."""
    from sps_identitas import penyimpanan
    nilai = penyimpanan.baca()
    try:
        versi = penyimpanan.versi()
    except Exception:  # noqa: BLE001 - database belum siap (instalasi pertama)
        versi = "0"
    return config_dari(nilai, versi, token_dasar)


def config_dari(nilai: dict[str, Any], versi: str, token_dasar: dict[str, Any]) -> dict[str, Any]:
    """Nilai identitas -> kunci konfigurasi Superset yang bergantung padanya."""
    from sps_identitas import tema
    return {
        "APP_NAME": nilai["nama_aplikasi"],
        "APP_ICON": tema.url_berkas("logo", nilai, versi),
        "FAVICONS": [{"href": tema.url_berkas("favicon", nilai, versi), "sizes": "64x64"}],
        "LOGO_TARGET_PATH": nilai["halaman_depan"],
        "THEME_DEFAULT": {"token": tema.token_superset(nilai, versi, token_dasar), "algorithm": "default"},
        # Mode gelap (U25): token identitas yang sama tanpa warna latar terang; dipilih per pengguna di menu akun.
        "THEME_DARK": {"token": tema.token_gelap(tema.token_superset(nilai, versi, token_dasar)), "algorithm": "dark"},
        "SPS_IDENTITAS": nilai,
        "SPS_IDENTITAS_VERSI": versi,
    }


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: halaman /identitas, penyegaran tema, penyisipan CSS, halaman login."""
    from sps_identitas import login, tampilan
    tampilan.daftarkan(app)
    login.daftarkan(app)


def siapkan() -> list[str]:
    """build-dashboards: tabel + isi awal dari .env (instalasi baru / installer).

    Isi awal dipakai bila database belum punya identitas, atau SPS_IDENTITAS_TERAPKAN=1
    (diisi installer ketika admin mengubah halaman Identitas).
      SPS_PRESET           netral (Tinta & Sakura) | navy | hijau | marun | ungu | grafit
      SPS_NAMA_APLIKASI, SPS_NAMA_PERUSAHAAN, SPS_HALAMAN_DEPAN
      SPS_LOGO             nama berkas di folder branding/ (mis. logo-kustom.png)
    """
    from sps_identitas import penyimpanan, skema
    penyimpanan.pastikan_tabel()
    lama = penyimpanan.baca()
    if lama.get("teks_login") in skema.TEKS_LOGIN_USANG:            # bersihkan teks lama
        penyimpanan.simpan({"teks_login": skema.PETA["teks_login"].bawaan}, "sistem")
    if lama.get("nama_aplikasi") in skema.NAMA_APLIKASI_USANG:      # SPS Analytics -> ALDx
        penyimpanan.simpan({"nama_aplikasi": skema.PETA["nama_aplikasi"].bawaan}, "sistem")
    paksa = os.environ.get("SPS_IDENTITAS_TERAPKAN") == "1"
    if penyimpanan.ada_isian() and not paksa:
        return ["identitas: sudah ada (diubah lewat Pusat Kendali > Identitas & Tema)"]

    preset = os.environ.get("SPS_PRESET") or "netral"
    if preset not in skema.PRESET:                                     # preset yang sudah tidak ada
        preset = "netral"
    isi = skema.nilai_preset(preset)
    for kunci, env in (("nama_aplikasi", "SPS_NAMA_APLIKASI"), ("nama_perusahaan", "SPS_NAMA_PERUSAHAAN"),
                       ("halaman_depan", "SPS_HALAMAN_DEPAN")):
        if os.environ.get(env):
            isi[kunci] = os.environ[env]
    if not os.environ.get("SPS_HALAMAN_DEPAN") and os.environ.get("HALAMAN_DEPAN"):
        isi["halaman_depan"] = os.environ["HALAMAN_DEPAN"]
    if os.environ.get("SPS_LOGO"):
        isi["logo"] = isi["logo_putih"] = f"statis:{os.environ['SPS_LOGO']}"
    berubah = penyimpanan.simpan(isi, "installer")
    return [f"identitas: preset '{preset}', {len(berubah)} isian diterapkan"]
