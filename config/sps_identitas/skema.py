"""Daftar isian identitas & tema, beserta preset siap pakai.

Semua tampilan (Superset, halaman login, Pusat Kendali, Studio, Asisten AI) membaca
nilai dari sini lewat sps_identitas.muat(). Menambah isian baru = tambah satu baris ISIAN.

Nilai isian berkas (logo, logo_putih, favicon):
    ""               -> dibuat otomatis (SVG dari nama & warna)
    "unggah"         -> berkas yang diunggah admin (tabel sps_identitas_berkas)
    "statis:<nama>"  -> berkas di folder branding/ (mis. statis:logo-kustom.png);
                        bila berkasnya tidak ada, logo dibuat otomatis
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

WARNA = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class Isian:
    kunci: str
    label: str
    grup: str
    jenis: str              # teks | warna | pilihan | ya_tidak | berkas | jalur
    bawaan: Any
    bantu: str = ""
    opsi: tuple = field(default_factory=tuple)
    maks: int = 120

    @property
    def publik(self) -> dict:
        return {"kunci": self.kunci, "label": self.label, "grup": self.grup, "jenis": self.jenis,
                "bawaan": self.bawaan, "bantu": self.bantu, "opsi": list(self.opsi)}


GRUP = {"nama": "Nama & teks", "warna": "Warna", "tampilan": "Tampilan & animasi", "berkas": "Logo & ikon"}
FONT = {"Plus Jakarta Sans": "'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif",
        "Sistem (Segoe UI)": "'Segoe UI', Roboto, Arial, sans-serif",
        "Klasik (Georgia)": "Georgia, 'Times New Roman', serif"}
SUDUT = {"lembut": 8, "tegas": 2, "bulat": 14}
HIASAN = ("tinta", "gelombang", "titik", "garis", "polos")

ISIAN: tuple[Isian, ...] = (
    Isian("nama_aplikasi", "Nama aplikasi", "nama", "teks", "ALDx",
          "Tampil di judul tab, navbar & halaman login.", maks=40),
    Isian("nama_perusahaan", "Nama perusahaan / instansi", "nama", "teks", "", maks=80),
    Isian("slogan", "Slogan", "nama", "teks", "Satu tempat untuk semua data", "Baris kecil di halaman login.", maks=80),
    Isian("teks_login", "Sapaan halaman login", "nama", "teks", "Masuk dengan email atau akun kantor Anda.", maks=120),
    Isian("teks_kaki", "Teks kaki halaman login", "nama", "teks", "© {tahun} {perusahaan}",
          "{tahun} dan {perusahaan} diganti otomatis.", maks=120),
    Isian("halaman_depan", "Halaman pertama setelah login", "nama", "jalur", "/app/",
          "/app/ = Beranda. Bisa juga alamat dashboard, mis. /superset/dashboard/latihan/", maks=200),
    # Bawaan "Tinta & Sakura": hitam tinta -> abu -> putih, semburat pink. Kontras: putih di atas utama 17,7:1,
    # putih di atas aksen 4,5:1 (WCAG AA). Gradasi abu dibuat otomatis dari warna utama (tema.palet).
    Isian("warna_utama", "Warna utama", "warna", "warna", "#18181B", "Tombol utama, menu aktif, judul."),
    Isian("warna_aksen", "Warna aksen", "warna", "warna", "#E11D74", "Sorotan, fokus, langkah berikutnya."),
    Isian("warna_latar", "Warna latar halaman", "warna", "warna", "#F4F4F5"),
    Isian("font", "Huruf", "tampilan", "pilihan", "Plus Jakarta Sans", opsi=tuple(FONT)),
    Isian("sudut", "Sudut kotak & tombol", "tampilan", "pilihan", "lembut", opsi=tuple(SUDUT)),
    Isian("hiasan", "Motif hiasan", "tampilan", "pilihan", "tinta",
          "Motif di halaman login & header halaman ALDx.", opsi=HIASAN),
    Isian("animasi", "Animasi halus", "tampilan", "ya_tidak", True,
          "Latar login bergerak pelan, chart & kartu muncul lembut. "
          "Otomatis mati bagi pengguna yang memilih 'kurangi gerakan' di Windows."),
    Isian("logo", "Logo (latar terang)", "berkas", "berkas", "", "PNG/SVG/JPG, maks 1 MB. Kosong = dibuat otomatis."),
    Isian("logo_putih", "Logo (latar gelap)", "berkas", "berkas", "", "Versi putih untuk header & login."),
    Isian("favicon", "Ikon tab browser", "berkas", "berkas", "", "Persegi, mis. 64×64 PNG atau SVG."),
)
PETA = {i.kunci: i for i in ISIAN}
BERKAS = tuple(i.kunci for i in ISIAN if i.jenis == "berkas")
BATAS_BERKAS = 1024 * 1024
MIME_BOLEH = {"image/png", "image/svg+xml", "image/jpeg", "image/webp", "image/x-icon",
              "image/vnd.microsoft.icon", "image/gif"}


def bawaan() -> dict[str, Any]:
    return {i.kunci: i.bawaan for i in ISIAN}


# --- Preset --------------------------------------------------------------------------------
# Hanya kunci yang disebut yang berubah; nama perusahaan dll. tetap milik admin
# kecuali preset menyebutnya (preset DJP mengisi identitas DJP lengkap).
PRESET: dict[str, dict[str, Any]] = {
    # "netral" = kembali ke SEMUA nilai bawaan (nama, teks, warna, logo otomatis).
    "netral": {"label": "Tinta & Sakura / bawaan (hitam, abu, putih + pink)", **{i.kunci: i.bawaan for i in ISIAN}},
    "navy": {"label": "Navy & biru (klasik)", "warna_utama": "#1E2A44", "warna_aksen": "#4F7CF7",
             "warna_latar": "#F5F6F8", "hiasan": "polos"},
    "hijau": {"label": "Hijau segar", "warna_utama": "#0F6E56", "warna_aksen": "#F4B400",
              "warna_latar": "#F3F7F5", "hiasan": "titik"},
    "marun": {"label": "Merah marun", "warna_utama": "#7A1F2B", "warna_aksen": "#E0A100",
              "warna_latar": "#F8F4F4", "hiasan": "garis"},
    "ungu": {"label": "Ungu modern", "warna_utama": "#4B2E83", "warna_aksen": "#19B5A5",
             "warna_latar": "#F5F4FA", "hiasan": "gelombang"},
    "grafit": {"label": "Grafit & toska", "warna_utama": "#263238", "warna_aksen": "#26A69A",
               "warna_latar": "#F3F5F6", "hiasan": "titik"},
    "djp": {"label": "Direktorat Jenderal Pajak", "nama_aplikasi": "DJP Analytics",
            "nama_perusahaan": "Direktorat Jenderal Pajak", "slogan": "Data penerimaan untuk keputusan",
            "halaman_depan": "/superset/dashboard/beranda/",
            "warna_utama": "#1F2F5F", "warna_aksen": "#F2B705", "warna_latar": "#F4F6F9", "hiasan": "gelombang",
            "logo": "statis:logo-aldx.svg", "logo_putih": "statis:logo-aldx-putih.svg",
            "favicon": "statis:favicon-aldx.svg"},
}


# Teks lama yang dibersihkan otomatis saat build-dashboards (kembali ke teks bawaan).
TEKS_LOGIN_USANG = ("Masuk dengan akun intranet DJP (sama seperti engineN).",)
NAMA_APLIKASI_USANG = ("SPS Analytics",)                   # nama lama -> nama bawaan baru (ALDx)


def nilai_preset(nama: str) -> dict[str, Any]:
    if nama not in PRESET:
        raise ValueError(f"Preset '{nama}' tidak dikenal. Pilihan: {', '.join(PRESET)}")
    return {k: v for k, v in PRESET[nama].items() if k != "label"}


# --- Validasi --------------------------------------------------------------------------------
def periksa(kunci: str, nilai: Any) -> Any:
    """Kembalikan nilai yang sudah dibersihkan, atau ValueError dengan pesan untuk admin."""
    if kunci not in PETA:
        raise ValueError(f"Isian '{kunci}' tidak dikenal")
    i = PETA[kunci]
    if i.jenis == "ya_tidak":
        return bool(nilai)
    nilai = str(nilai if nilai is not None else "").strip()
    if i.jenis == "warna":
        if not WARNA.match(nilai):
            raise ValueError(f"{i.label}: tulis kode warna seperti #1F4E79")
        return nilai.upper()
    if i.jenis == "pilihan" and nilai not in i.opsi:
        raise ValueError(f"{i.label}: pilih salah satu dari {', '.join(i.opsi)}")
    if i.jenis == "jalur" and not (nilai.startswith("/") and not nilai.startswith("//")):
        raise ValueError(f"{i.label}: harus alamat di dalam aplikasi, diawali '/'")
    if i.jenis == "berkas" and nilai not in ("", "unggah") and not re.match(r"^statis:[\w.-]+$", nilai):
        raise ValueError(f"{i.label}: nilai berkas tidak sah")
    if i.jenis == "teks" and not nilai:
        raise ValueError(f"{i.label} tidak boleh kosong")
    if len(nilai) > i.maks:
        raise ValueError(f"{i.label}: maksimal {i.maks} karakter")
    return nilai
