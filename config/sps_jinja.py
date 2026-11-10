"""Fungsi tambahan untuk template SQL (Jinja) di dataset Superset.

Didaftarkan di superset_config.py lewat JINJA_CONTEXT_ADDONS, lalu dipakai
di SQL dataset seperti ini:

    {% set p = sps_periode(filter_values('tahun', remove_filter=True),
                           filter_values('bulan', remove_filter=True)) %}
    SELECT ... WHERE TAHUN = '{{ p.tahun }}' AND BULAN <= '{{ p.bulan }}'

Nilai filter dari dashboard DIVALIDASI di sini (hanya angka), sehingga
tidak bisa dipakai untuk menyisipkan SQL. Bila filter kosong, dipakai
tahun & bulan berjalan - sama seperti halaman Home engineN.
"""

from __future__ import annotations

from datetime import date


def _first_valid(values, length: int, low: int, high: int) -> int | None:
    """Ambil nilai pertama yang berupa angka sepanjang `length` dan dalam rentang."""
    for value in values or []:
        text = str(value).strip()
        if len(text) <= length and text.isdigit() and low <= int(text) <= high:
            return int(text)
    return None


# Kolom PDB kumulatif per triwulan di tabel REF_BI_GDP (sama dengan Mpemby::getKat).
_KOLOM_PDB_KUMULATIF = ("TWI", "(TWI+TWII)", "(TWI+TWII+TWIII)", "(TWI+TWII+TWIII+TWIV)")


def sps_periode(tahun_values=None, bulan_values=None) -> dict[str, str]:
    """Kembalikan periode laporan yang sudah aman dipakai di SQL.

    Hasil: {"tahun": "2026", "tahun_lalu": "2025", "bulan": "10",
            "kolom_pdb": "(TWI+TWII+TWIII+TWIV)"}
    """
    today = date.today()
    tahun = _first_valid(tahun_values, 4, 2000, 2100) or today.year
    bulan = _first_valid(bulan_values, 2, 1, 12) or today.month
    return {
        "tahun": str(tahun),
        "tahun_lalu": str(tahun - 1),
        "bulan": f"{bulan:02d}",
        "kolom_pdb": _KOLOM_PDB_KUMULATIF[(bulan - 1) // 3],
    }
