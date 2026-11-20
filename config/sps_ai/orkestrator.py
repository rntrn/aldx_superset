"""Orchestrator Asisten AI: dari setiap pertanyaan, pilih peran ahli (agent) yang paling tepat menjawabnya.

Dipakai saat panel AI dalam mode **Otomatis** (bawaan). Tanpa model AI: cepat, tidak membebani model lokal, dan
hasilnya bisa dijelaskan ("otomatis: menyebut 'dataset', 'join'"). Urutan pertimbangan:

    1. Perintah ubah yang dikenali penerjemah niat (niat.py)  -> /analis (dataset: ukuran/dimensi/label -> /data-engineer)
    2. Lanjutan singkat ("ya", "lanjut", "ok", "yang kedua")   -> peran jawaban sebelumnya
    3. Skor kata kunci tiap bidang (+ halaman yang sedang dibuka sebagai petunjuk ringan)
       "bagaimana cara ..." / "di mana menu ..."               -> /panduan (walau menyebut chart/dashboard)
       chart, grafik, berapa, tren, bandingkan, dashboard       -> /analis
       dataset, tabel, kolom, join, SQL, koneksi, ekstrak      -> /data-engineer
       warna, tema, huruf, kontras, logo, tampilan             -> /ahli-ui-ux
       CPU, RAM, memori, server, worker, cache, timeout        -> /hw-engineer
    4. Tidak ada petunjuk -> peran sebelumnya, atau /analis

Hanya peran yang BOLEH dipakai pengguna itu (peran.tersedia) yang bisa terpilih. Memilih chip peran atau mengetik
/peran di panel tetap memaksa peran tertentu (orchestrator tidak dipakai).

    pilih(pertanyaan, boleh_ids, konteks=None, terakhir=None) -> (peran_id, alasan)
"""

from __future__ import annotations

import re

URUTAN = ("analis", "data-engineer", "panduan", "ahli-ui-ux", "hw-engineer")   # pemenang bila skor seri

# (pola, bobot) per peran. Pola dicocokkan pada huruf kecil; \b agar 'ram' tidak cocok di 'program'.
KATA: dict[str, list[tuple[str, int]]] = {
    "panduan": [
        (r"\bbagaimana (?:cara|caranya)\b|\bgimana (?:cara|caranya)\b|\bcara (?:membuat|memakai|menggunakan|mengganti|menambah|"
         r"menghapus|mengatur|mengubah|install|memasang|ekspor|impor|login|bikin)\b", 4),
        (r"\bdi ?mana (?:menu|tombol|letak|tempat)\b|\bmenu apa\b|\bletak (?:menu|tombol)\b", 4),
        (r"\b(?:apa itu|apa bedanya|bedanya|perbedaan antara|fungsi (?:menu|tombol|fitur))\b", 3),
        (r"\b(?:pintasan|shortcut|tutorial|panduan|langkah-langkah|langkahnya|petunjuk|tips memakai)\b", 3),
        (r"\b(?:fitur|menu|tombol)\b", 1),
    ],
    "analis": [
        (r"\b(?:chart|charts|grafik|diagram|visual\w*|plot)\b", 3),
        (r"\b(?:dashboard|dasbor)\b", 2),
        (r"\b(?:berapa|total|jumlah|rata-rata|rerata|tertinggi|terendah|terbesar|terkecil|teratas|terbawah|persentase|"
         r"proporsi|naik|turun|tren|trend|pertumbuhan|bandingkan|perbandingan|per (?:bulan|tahun|cabang|wilayah|kategori))\b", 2),
        (r"\b(?:analisis|analisa|insight|wawasan|menonjol|menarik|janggal|anomali|ringkas\w*|kesimpulan|prediksi|ramalan)\b", 2),
        (r"\b(?:penjualan|pendapatan|omzet|laba|biaya|transaksi|pelanggan|target)\b", 1),
        (r"\b(?:filter|story)\b", 1),
    ],
    "data-engineer": [
        (r"\b(?:sql|query|kueri|select|join|left join|inner join|cte|subquery|indeks|index)\b", 3),
        (r"\b(?:dataset|tabel|table|kolom|column|skema|schema|tipe data|primary key|kunci)\b", 2),
        (r"\b(?:koneksi|database|basis data|ekstrak|extract|etl|sumber data|impor data|sinkron\w*|clickhouse|postgres\w*|"
         r"oracle|mysql|sql server|engine)\b", 3),
        (r"\b(?:gabung\w*|denormal\w*|duplikat|null|kosong|kualitas data|bersihkan data|validasi data|baris ganda)\b", 2),
        (r"\b(?:ukuran terdefinisi|dimensi terdefinisi|kolom hitung|metrik tersimpan|label kolom|rls|hak akses data|batas data)\b", 2),
    ],
    "ahli-ui-ux": [
        (r"\b(?:warna|color|tema|theme|palet|palette|huruf|font|tipografi|kontras|contrast|logo|ikon|icon)\b", 3),
        (r"\b(?:tampilan|desain|design|ui|ux|aksesibilitas|accessibility|wcag|mode gelap|dark mode|identitas|branding)\b", 2),
    ],
    "hw-engineer": [
        (r"\b(?:cpu|ram|memori|memory|disk|penyimpanan|storage|gpu|prosesor|core)\b", 3),
        (r"\b(?:server|container|docker|worker|gunicorn|celery|redis|proses|beban|load|kapasitas|skala|scaling|node)\b", 2),
        (r"\b(?:cache|timeout|waktu tunggu|lambat|lemot|hang|macet|error 50\d|restart|pengaturan server)\b", 2),
    ],
}
_POLA = {p: [(re.compile(pola, re.I), bobot) for pola, bobot in daftar] for p, daftar in KATA.items()}

# Halaman yang sedang dibuka -> petunjuk ringan (bobot kecil; isi pertanyaan tetap yang utama)
HALAMAN = [
    (re.compile(r"^/pusat-kendali/?(\?tab=(status|topologi|pengaturan|batas))?$"), "hw-engineer"),
    (re.compile(r"^/pusat-kendali/\?tab=identitas"), "ahli-ui-ux"),
    (re.compile(r"^/(pusat-kendali/\?tab=(hubungkan|ekstrak)|tablemodelview|databaseview|kueri|sqllab|studio/\?tab=prep)"), "data-engineer"),
    (re.compile(r"^/panduan"), "panduan"),
    (re.compile(r"^/(superset/dashboard|explore|studio)"), "analis"),
]
LANJUTAN = re.compile(r"^\s*(?:ya|iya|yes|y|ok(?:e|ay)?|sip|lanjut\w*|boleh|silakan|setuju|betul|benar|tidak|nggak|gak|no|"
                      r"yang (?:pertama|kedua|ketiga|itu|ini)|nomor \d+|\d+|go|sure|terus|lagi)\W*$", re.I)


def _skor(teks: str) -> dict[str, tuple[int, list[str]]]:
    hasil = {}
    for peran, daftar in _POLA.items():
        nilai, bukti = 0, []
        for pola, bobot in daftar:
            temu = pola.findall(teks)
            if temu:
                nilai += bobot * min(len(temu), 2)
                bukti += [t if isinstance(t, str) else t[0] for t in temu[:2]]
        hasil[peran] = (nilai, bukti)
    return hasil


def pilih(pertanyaan: str, boleh_ids: list[str], konteks: dict | None = None, terakhir: str | None = None) -> tuple[str, str]:
    """(id peran, alasan singkat untuk ditampilkan). boleh_ids = peran yang boleh dipakai pengguna (urut bebas)."""
    boleh = [p for p in URUTAN if p in boleh_ids] + [p for p in boleh_ids if p not in URUTAN]
    cadangan = "analis" if "analis" in boleh else (boleh[0] if boleh else "analis")
    teks = re.sub(r"^/[\w-]+\s*", "", str(pertanyaan or "")).strip()

    # 1. Perintah ubah yang dikenali tanpa model
    from sps_ai import niat
    ops = niat.baca(teks)
    if ops:
        dataset = all(o.get("op") in ("tambah_ukuran", "tambah_dimensi", "ganti_label_kolom") for o in ops)
        tujuan = "data-engineer" if dataset and "data-engineer" in boleh else cadangan
        return tujuan, "perintah ubah dikenali"

    # 2. Lanjutan singkat percakapan
    if terakhir in boleh and (LANJUTAN.match(teks) or len(teks.split()) <= 2):
        return terakhir, "lanjutan percakapan"

    # 3. Kata kunci + halaman
    skor = _skor(teks)
    alamat = str((konteks or {}).get("alamat") or "")
    halaman = next((p for pola, p in HALAMAN if pola.search(alamat)), None)
    total = {p: skor.get(p, (0, []))[0] + (1 if p == halaman else 0) + (1 if p == terakhir else 0) for p in boleh}
    if not total or max(total.values()) == 0:
        terbaik, alasan = (terakhir if terakhir in boleh else cadangan), "tidak ada petunjuk khusus"
    else:
        terbaik = max(boleh, key=lambda p: (total[p], -boleh.index(p)))
        bukti = skor.get(terbaik, (0, []))[1]
        alasan = ("menyebut " + ", ".join(f"'{b}'" for b in dict.fromkeys(x.lower() for x in bukti[:3]))) if bukti \
            else "halaman yang dibuka"
    # Bidang paling cocok tidak boleh dipakai akun ini -> beri tahu lewat alasan, pakai peran terbaik yang boleh
    terlarang = [p for p in KATA if p not in boleh and skor[p][0] > total.get(terbaik, 0)]
    if terlarang:
        alasan = f"/{terlarang[0]} tidak tersedia untuk akun Anda; dijawab /{terbaik}"
    return terbaik, alasan
