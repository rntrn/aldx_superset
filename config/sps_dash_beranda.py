"""Dashboard "Beranda DJP" - halaman depan untuk semua pegawai.

Tanpa chart (hanya teks/tautan), jadi tidak membaca data apa pun. Halaman
"/" dan "/superset/welcome/" diarahkan ke sini (HALAMAN_DEPAN di
superset_config.py). Isi bisa diubah bebas di MENU di bawah.
"""

from __future__ import annotations

from sps_dashboard_builder import Dashboard, Markdown

NAVY, EMAS = "#1F2F5F", "#F2B705"

# (judul, keterangan, alamat, untuk siapa)
MENU = [
    ("Dashboard Nasional", "Penerimaan, kepatuhan, dan Follow the Money se-Indonesia.",
     "/superset/dashboard/home-nasional/", "Kantor Pusat"),
    ("Daftar Dashboard", "Semua dashboard yang boleh Anda buka.",
     "/dashboard/list/", "Semua pegawai"),
    ("Daftar Chart", "Cari chart tertentu.", "/chart/list/", "Semua pegawai"),
]

HERO = (
    f'<div style="background:linear-gradient(120deg,{NAVY} 0%,#2B4A8F 100%);color:#fff;'
    f'padding:28px 32px;border-radius:12px;border-bottom:6px solid {EMAS}">'
    '<img src="/identitas/berkas/logo_putih" alt="Logo" style="height:46px"/>'
    '<div style="font-size:26px;font-weight:700;margin-top:14px">DJP Analytics</div>'
    '<div style="font-size:14px;opacity:.9;margin-top:4px">'
    'Dashboard analitik Direktorat Jenderal Pajak. Data yang tampil otomatis '
    'disesuaikan dengan unit kerja dan jabatan Anda.</div></div>'
)


def _kartu(judul: str, ket: str, url: str, untuk: str) -> str:
    return (
        f'<a href="{url}" style="text-decoration:none;color:inherit">'
        f'<div style="border:1px solid #D5DCE4;border-left:5px solid {NAVY};border-radius:8px;'
        'padding:14px 16px;margin-bottom:10px;background:#fff">'
        f'<div style="font-size:15px;font-weight:700;color:{NAVY}">{judul} &rarr;</div>'
        f'<div style="font-size:12px;color:#5F6B7A;margin-top:3px">{ket}</div>'
        f'<div style="font-size:11px;color:#8A6D00;margin-top:6px">Untuk: {untuk}</div>'
        '</div></a>'
    )


INFO = (
    f'<div style="background:#FFF8E1;border-left:5px solid {EMAS};border-radius:8px;padding:14px 16px">'
    '<b>Tentang hak akses</b><br/>'
    '<span style="font-size:12px">Kantor Pusat melihat seluruh data; pegawai Kanwil melihat '
    'kanwilnya; pegawai KPP melihat KPP-nya; Account Representative melihat WP yang diampunya. '
    'Bila data yang seharusnya Anda lihat tidak muncul, hubungi admin aplikasi.</span></div>'
)

BERANDA = Dashboard(
    key="beranda",
    title="Beranda DJP",
    slug="beranda",
    database_name="Oracle DMP (GENAPP)",
    datasets=[],
    charts=[],
    rows=[
        Markdown(HERO, height=30),
        Markdown("### Menu\n" + "".join(_kartu(*m) for m in MENU), height=50),
        Markdown(INFO, height=16),
    ],
    roles=["DJP Pegawai", "DJP Pusat"],
)
