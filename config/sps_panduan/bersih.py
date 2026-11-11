"""Aturan versi jualan (bersih): baris khusus pengembang tidak tampil bagi pengguna.

Penanda: tulis `<!-- khusus-pengembang -->` di baris Markdown yang hanya untuk tim pengembang
(mis. tautan ke CHANGELOG atau laporan QA, yang tidak ikut versi jualan). Baris itu dibuang di:

    - panduan di dalam aplikasi (/panduan/, sps_panduan/tampilan.py)
    - PDF (docs/pdf/buat_pdf.py)
    - folder bersih (scripts/buat-bersih.ps1, aturan yang sama ditulis ulang di PowerShell)

Di Markdown mentah & situs VitePress pengembang baris tetap terlihat (komentar HTML tidak dirender).
Daftar jejak terlarang ada di `bersih.terlarang`, diperiksa tests/test_bersih.py.
"""

PENANDA = "<!-- khusus-pengembang -->"


def tanpa_khusus_pengembang(teks: str) -> str:
    """Buang setiap baris yang memuat PENANDA; baris lain (termasuk akhir barisnya) tidak berubah."""
    return "".join(b for b in teks.splitlines(keepends=True) if PENANDA not in b)
