"""Template dashboard: pilih dataset -> ALDx membuat lembar kerja & susunan dashboard siap pakai.

Alur (padanan "Quick create" Power BI / "Dashboard Starter" Tableau):
    1. petakan(dataset)  : pilih kolom waktu, kategori (2-50 nilai), wilayah, dan ukuran secara otomatis
    2. rancang(...)      : susun daftar lembar kerja menurut template (lihat TEMPLAT)
    3. buat(...)         : simpan lembar kerja sebagai chart, kembalikan susunan untuk kanvas "Susun dashboard"
Dashboard TIDAK langsung disimpan: pengguna melihat hasilnya di kanvas, mengubah bila perlu, lalu Simpan.

Menambah template baru: tambah satu entri di TEMPLAT + satu fungsi _susun_<kunci>() yang mengembalikan
daftar baris berisi (spesifikasi lembar, lebar). Spesifikasi memakai bentuk yang sama dengan lembar.dari_dict().
"""

from __future__ import annotations

from sps_ai import alat
from sps_ai.auto import kolom_pengenal
from sps_studio import bidang, lembar

TEMPLAT = {
    "ringkasan": {"label": "Ringkasan eksekutif",
                  "ket": "Angka utama, tren dengan ramalan, peringkat, dan komposisi dalam satu layar."},
    "tren": {"label": "Tren & ramalan",
             "ket": "Fokus waktu: tren tiap ukuran, ramalan 6 periode, akumulasi berjalan, dan tabel rincian."},
    "perbandingan": {"label": "Perbandingan kategori",
                     "ket": "Fokus kategori/wilayah: peringkat, porsi (% dari total), peta, dan tabel berskala warna."},
}
MAKS_UKURAN = 4            # kotak angka di baris pertama
MAKS_CALON = 8             # kolom teks yang diperiksa jumlah nilainya (hemat query)


def _dim(nama: str) -> dict:
    return {"field": nama, "peran": "dimensi"}


def _uk(b: dict) -> dict:
    return {"field": b["field"], "peran": "ukuran", "agg": b.get("agg", "SUM"), "metrik": bool(b.get("metrik"))}


def petakan(dataset_id: int, utama: str = "") -> dict:
    """Peran kolom untuk template: {"waktu", "kategori": [...], "wilayah", "ukuran": [...]}.
    utama = nama ukuran pilihan pengguna; ditaruh pertama (dipakai tren, peringkat, komposisi)."""
    t = alat._dataset(dataset_id)
    b = bidang.daftar(dataset_id)
    waktu = next((d["field"] for d in b["dimensi"] if d.get("dttm")), None) or \
        next((d["field"] for d in b["dimensi"] if d.get("waktu")), None)
    wilayah = next((d["field"] for d in b["dimensi"] if d.get("geo") == "wilayah"), None)
    kategori = []
    calon = [d["field"] for d in b["dimensi"] if d["jenis"] == "teks" and not kolom_pengenal(d["field"])]
    for nama in calon[:MAKS_CALON]:
        n = len(lembar.nilai_unik(t, nama, 51))
        if 2 <= n <= 50:
            kategori.append((n, nama))
    semua = [u for u in b["ukuran"] if u["field"] != lembar.BARIS]
    semua.sort(key=lambda u: (u["field"] != utama, bool(u.get("metrik")) and u["field"].lower() == "count"))
    ukuran = semua[:MAKS_UKURAN] or [u for u in b["ukuran"] if u["field"] == lembar.BARIS]
    return {"nama": b["nama"], "waktu": waktu, "wilayah": wilayah,
            "kategori": [nama for _, nama in sorted(kategori)],          # paling sedikit nilainya dulu
            "ukuran": [_uk(u) for u in ukuran]}


def _label(u: dict) -> str:
    return "Jumlah baris" if u["field"] == lembar.BARIS else u["field"].replace("_", " ").capitalize()


def _angka(p: dict) -> list[tuple[dict, int]]:
    lebar = {1: 12, 2: 6, 3: 4}.get(len(p["ukuran"]), 3)
    return [({"tanda": "angka", "judul": _label(u), "baris": [u]}, lebar) for u in p["ukuran"]]


def _susun_ringkasan(p: dict) -> list[list[tuple[dict, int]]]:
    u, kat = p["ukuran"][0], p["kategori"]
    baris = [_angka(p)]
    tengah = []
    if p["waktu"]:
        tengah.append(({"tanda": "garis", "judul": f"Tren {_label(u)} + ramalan", "kolom": [_dim(p["waktu"])],
                        "baris": [u], "analitik": {"ramalan": 6}}, 6 if kat else 12))
    if kat:
        tengah.append(({"tanda": "pie", "judul": f"Komposisi per {kat[0]}", "kolom": [_dim(kat[0])], "baris": [u]},
                       6))
    baris.append(tengah)
    bawah = []
    if len(kat) > 1 or (kat and not p["waktu"]):
        k = kat[-1]
        bawah.append(({"tanda": "batang", "judul": f"10 teratas per {k}", "baris": [_dim(k)], "kolom": [u],
                       "urut": "turun", "batas": 10}, 6))
    if p["wilayah"]:
        bawah.append(({"tanda": "peta_wilayah", "judul": f"{_label(u)} per provinsi", "kolom": [_dim(p["wilayah"])],
                       "baris": [u]}, 6))
    elif len(kat) > 1:
        bawah.append(({"tanda": "treemap", "judul": f"{kat[0]} › {kat[1]}", "kolom": [_dim(kat[0]), _dim(kat[1])],
                       "baris": [u]}, 6))
    baris.append(bawah)
    return baris


def _susun_tren(p: dict) -> list[list[tuple[dict, int]]]:
    if not p["waktu"]:
        raise alat.InputSalah("Template Tren & ramalan butuh kolom tanggal di dataset. Pilih template lain.")
    w, u = _dim(p["waktu"]), p["ukuran"][0]
    baris = [_angka(p),
             [({"tanda": "garis", "judul": f"Tren {_label(u)} + ramalan & garis tren", "kolom": [w], "baris": [u],
                "analitik": {"ramalan": 6, "tren": True}}, 12)],
             [({"tanda": "area", "judul": f"{_label(u)} kumulatif", "kolom": [w], "baris": [u],
                "kalkulasi": "kumulatif"}, 6)]]
    if len(p["ukuran"]) > 1:
        baris[-1].append(({"tanda": "garis", "judul": "Perbandingan ukuran", "kolom": [w],
                           "baris": p["ukuran"][:3]}, 6))
    elif p["kategori"]:
        baris[-1].append(({"tanda": "batang_100", "judul": f"Porsi per {p['kategori'][0]}", "kolom": [w],
                           "baris": [u], "warna": _dim(p["kategori"][0])}, 6))
    baris.append([({"tanda": "tabel", "judul": "Rincian per periode", "baris": [w], "kolom": p["ukuran"],
                    "skala_warna": True, "batas": 200}, 12)])
    return baris


def _susun_perbandingan(p: dict) -> list[list[tuple[dict, int]]]:
    if not p["kategori"]:
        raise alat.InputSalah("Template Perbandingan butuh kolom kategori (teks dengan 2-50 nilai). Pilih template lain.")
    u, kat = p["ukuran"][0], p["kategori"]
    k = kat[-1]
    baris = [_angka(p),
             [({"tanda": "batang", "judul": f"Peringkat {k}", "baris": [_dim(k)], "kolom": [u], "urut": "turun",
                "batas": 15, "label": True}, 6),
              ({"tanda": "batang", "judul": f"Porsi {kat[0]} (% dari total)", "kolom": [_dim(kat[0])], "baris": [u],
                "kalkulasi": "persen_total", "label": True}, 6)]]
    bawah = []
    if p["wilayah"]:
        bawah.append(({"tanda": "peta_wilayah", "judul": f"{_label(u)} per provinsi", "kolom": [_dim(p["wilayah"])],
                       "baris": [u]}, 6))
    if len(kat) > 1:
        bawah.append(({"tanda": "peta_panas", "judul": f"{kat[0]} × {kat[1]}", "kolom": [_dim(kat[0])],
                       "baris": [_dim(kat[1]), u]}, 6))
    baris.append(bawah)
    baris.append([({"tanda": "tabel", "judul": f"Rincian per {k}", "baris": [_dim(k)], "kolom": p["ukuran"],
                    "skala_warna": True, "urut": "turun", "batas": 200}, 12)])
    return baris


SUSUN = {"ringkasan": _susun_ringkasan, "tren": _susun_tren, "perbandingan": _susun_perbandingan}


def rancang(dataset_id: int, kunci: str, utama: str = "") -> tuple[dict, list[list[tuple[dict, int]]]]:
    """(peta kolom, baris berisi (spesifikasi lembar, lebar)). Tidak menyimpan apa pun."""
    if kunci not in TEMPLAT:
        raise alat.InputSalah(f"Template '{kunci}' tidak dikenal.")
    p = petakan(dataset_id, utama)
    if not p["ukuran"]:
        raise alat.InputSalah("Dataset ini belum punya kolom angka untuk dijadikan ukuran.")
    baris = [[({**spec, "dataset_id": dataset_id}, lebar) for spec, lebar in isi] for isi in SUSUN[kunci](p) if isi]
    return p, baris


def buat(dataset_id: int, kunci: str, utama: str = "") -> dict:
    """Simpan lembar kerja template lalu kembalikan susunan untuk kanvas (bentuk sama dengan dasbor.buka)."""
    from superset import security_manager

    if not security_manager.can_access("can_write", "Chart"):
        raise alat.IzinDitolak("Anda belum punya izin menyimpan chart, jadi template tidak bisa dibuat.")
    p, rancangan = rancang(dataset_id, kunci, utama)
    baris, dilewati = [], []
    for isi in rancangan:
        kotak = []
        for spec, lebar in isi:
            try:                                   # satu chart gagal (mis. data kosong) tidak menggagalkan template
                t, l = lembar.dari_dict(spec)
                lembar.periksa_tanda(l)
                h = lembar.simpan(t, l)
                kotak.append({"chart_id": h["id"], "lebar": lebar, "judul": h["judul"]})
            except alat.InputSalah as e:
                dilewati.append(f"{spec['judul']}: {e}")
        if kotak:
            baris.append(kotak)
    if not baris:
        raise alat.InputSalah("Tidak ada chart yang bisa dibuat dari dataset ini. " + "; ".join(dilewati[:2]))
    judul = {"jenis": "teks", "lebar": 12, "tinggi": 10, "teks": f"{TEMPLAT[kunci]['label']}: {p['nama']}",
             "huruf": "bawaan", "ukuran": 26, "tebal": True, "miring": False, "warna": "#111827", "latar": "",
             "rata": "left", "tegak": "center"}
    filter_ = [{"nama": k.replace("_", " ").capitalize(), "dataset_id": dataset_id, "kolom": k, "jenis": "pilihan"}
               for k in p["kategori"][:3]]
    if p["waktu"]:
        filter_.append({"nama": "Rentang waktu", "dataset_id": dataset_id, "kolom": p["waktu"], "jenis": "waktu"})
    return {"judul": f"{TEMPLAT[kunci]['label']} {p['nama']}", "baris": [[judul], *baris], "filter": filter_,
            "dilewati": dilewati}
