"""Jelaskan perubahan: kenapa sebuah titik naik/turun dibanding titik sebelumnya?

Jelaskan kenaikan/penurunan, versi sederhana yang bisa ditelusuri:
    1. ambil nilai ukuran pada dua titik (mis. Maret vs Februari) per nilai tiap dimensi lain di dataset
    2. hitung selisih tiap nilai (mis. Cabang Jakarta +1,2 M, Cabang Medan -0,3 M)
    3. urutkan menurut sumbangan terbesar terhadap perubahan total

Hanya membaca, memakai hak akses pengguna (RLS berlaku) dan filter lembar kerja yang sedang aktif.
Dipakai Studio: klik kanan sebuah titik pada Garis/Area/Batang dengan satu dimensi -> "Jelaskan perubahan ini".
"""

from __future__ import annotations

from sps_ai import alat
from sps_ai.auto import kolom_pengenal
from sps_studio import bidang, lembar

MAKS_DIMENSI = 6           # dimensi yang diperiksa (tiap dimensi = satu kueri)
MAKS_NILAI = 50            # dimensi dengan nilai lebih banyak dilewati (rincian tidak terbaca)
TERATAS = 5                # penyumbang yang ditampilkan per dimensi


def _calon(t, lembar_: lembar.Lembar) -> list[str]:
    """Dimensi teks/wilayah selain sumbu & selain kolom yang sudah difilter, paling sedikit nilainya dulu."""
    dipakai = {p.field for p in lembar_.dimensi} | {f.get("field") for f in lembar_.filter}
    calon = []
    for d in bidang.daftar(t.id)["dimensi"]:
        nama = d["field"]
        if nama in dipakai or d["jenis"] not in ("teks", "geo") or d.get("geo") in ("lintang", "bujur") \
                or kolom_pengenal(nama):
            continue
        n = len(lembar.nilai_unik(t, nama, MAKS_NILAI + 1))
        if 2 <= n <= MAKS_NILAI:
            calon.append((n, nama))
        if len(calon) >= MAKS_DIMENSI:
            break
    return [nama for _, nama in sorted(calon)]


def jelaskan(spec: dict, x, x_sebelum) -> dict:
    t, l = lembar.dari_dict(spec)
    if l.tanda not in lembar.TANDA_ANALITIK or len(l.dimensi) != 1 or not l.ukuran_semua:
        raise alat.InputSalah("Jelaskan perubahan butuh Garis, Area, atau Batang dengan satu dimensi dan satu ukuran.")
    if x is None or x_sebelum is None or x == x_sebelum:
        raise alat.InputSalah("Pilih titik yang punya titik sebelumnya.")
    sumbu, ukuran = l.dimensi[0], l.ukuran_semua[0]
    metrik = lembar._metrik(ukuran)
    saring = lembar._filter(t, l) + alat._filter_bersih(t, [{"kolom": sumbu.field, "op": "IN", "nilai": [x, x_sebelum]}])

    def nilai(baris, titik):
        return sum(float(b.get(ukuran.label) or 0) for b in baris if b.get(sumbu.label) == titik)

    total = alat.jalankan_objek(t, [metrik], [sumbu.field], saring, [], 10)["baris"]
    kini, dulu = nilai(total, x), nilai(total, x_sebelum)
    selisih = kini - dulu
    rincian = []
    for dim in _calon(t, l):
        baris = alat.jalankan_objek(t, [metrik], [sumbu.field, dim], saring, [], 2 * (MAKS_NILAI + 1))["baris"]
        per = {}
        for b in baris:
            v = float(b.get(ukuran.label) or 0)
            a = per.setdefault(b.get(dim), [0.0, 0.0])
            a[0 if b.get(sumbu.label) == x else 1] += v
        butir = [{"nilai": k, "kini": a[0], "dulu": a[1], "selisih": a[0] - a[1],
                  "porsi": (a[0] - a[1]) / selisih * 100 if selisih else None} for k, a in per.items()]
        butir.sort(key=lambda b: -abs(b["selisih"]))
        # Kekuatan penjelas: seberapa terpusat perubahan pada beberapa nilai (penyumbang teratas / total gerak).
        gerak = sum(abs(b["selisih"]) for b in butir) or 1.0
        rincian.append({"dimensi": dim, "teratas": butir[:TERATAS],
                        "pusat": sum(abs(b["selisih"]) for b in butir[:2]) / gerak * 100})
    rincian.sort(key=lambda r: -r["pusat"])
    return {"ukuran": ukuran.label, "sumbu": sumbu.label, "x": x, "x_sebelum": x_sebelum,
            "kini": kini, "dulu": dulu, "selisih": selisih, "persen": selisih / abs(dulu) * 100 if dulu else None,
            "rincian": rincian}
