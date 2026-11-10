"""Auto Chart & Auto Dashboard: mempelajari dataset lalu menyarankan chart.

Cara kerja (tanpa container tambahan):
    1. SAMPEL   ambil s.d. 5.000 baris lewat jalankan_query (RLS tetap berlaku).
    2. PROFIL   kenali peran kolom: ukuran (angka), dimensi (kategori),
                waktu (tahun/bulan/tanggal), atau diabaikan (ID, konstan).
    3. KANDIDAT bentuk calon chart dari kombinasi kolom.
    4. SKOR     nilai "menarik"-nya dengan statistik & machine learning ringan:
                  - tren       : regresi linear (kemiringan, R²)
                  - konsentrasi: indeks Herfindahl & porsi 3 teratas
                  - pencilan   : z-score per kategori
                  - korelasi   : Pearson antar-ukuran
                  - segmentasi : k-means (numpy) pada profil kategori
    5. Pengguna memilih saran mana yang dibuat, jenisnya, dan judulnya.

Semua angka saran dihitung dari SAMPEL; chart yang dibuat memakai data penuh.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from sps_ai import alat

SAMPEL_MAKS = 5000
POLA_WAKTU = re.compile(r"(tahun|thn|bulan|bln|tgl|tanggal|date|periode|masa|year|month|minggu|week)", re.I)
POLA_ID = re.compile(r"(^id$|_id$|npwp|nip|nik|nomor|no_|kode_?unik)", re.I)
MAKS_KATEGORI = 60


@dataclass
class Saran:
    id: str
    judul: str
    jenis: str
    alternatif: list[str]
    metrik: list[str]
    kelompok: list[str]
    skor: float
    alasan: str
    pratinjau: list[dict] = field(default_factory=list)


# --- 1-2. Sampel & profil -------------------------------------------------------
def _sampel(dataset_id: int) -> pd.DataFrame:
    hasil = alat.jalankan_query(dataset_id, batas=SAMPEL_MAKS)
    return pd.DataFrame(hasil["baris"], columns=hasil["kolom"])


def profil_kolom(df: pd.DataFrame) -> dict[str, list[str]]:
    """Kelompokkan kolom: ukuran, dimensi, waktu."""
    peran: dict[str, list[str]] = {"ukuran": [], "dimensi": [], "waktu": [], "abaikan": []}
    n = max(len(df), 1)
    for kolom in df.columns:
        s = df[kolom].dropna()
        unik = s.nunique()
        angka = pd.to_numeric(s, errors="coerce")
        rasio_angka = angka.notna().mean() if len(s) else 0
        if unik <= 1:
            peran["abaikan"].append(kolom)                     # konstan (mis. kolom periode)
        elif POLA_WAKTU.search(kolom) or pd.api.types.is_datetime64_any_dtype(s):
            peran["waktu"].append(kolom)
        elif POLA_ID.search(kolom) and unik / n > 0.5:
            peran["abaikan"].append(kolom)                     # pengenal unik (NPWP, NIP, ...)
        elif rasio_angka > 0.95 and not kolom.lower().startswith(("kd_", "kode")) \
                and (unik > 12 or (angka % 1 != 0).any()):
            peran["ukuran"].append(kolom)
        elif 2 <= unik <= MAKS_KATEGORI:
            peran["dimensi"].append(kolom)
        else:
            peran["abaikan"].append(kolom)
    return peran


# --- 3-4. Kandidat & skor -----------------------------------------------------------
def _pratinjau(g: pd.Series, n: int = 8) -> list[dict]:
    return [{"kategori": str(k), "nilai": float(v)} for k, v in g.head(n).items()]


def _skor_kategori(g: pd.Series) -> tuple[float, str]:
    total = g.abs().sum()
    if total == 0 or len(g) < 2:
        return 0.0, ""
    porsi = (g.abs() / total).sort_values(ascending=False)
    hhi = float((porsi ** 2).sum())
    top3 = float(porsi.head(3).sum())
    cv = float(g.std() / abs(g.mean())) if g.mean() else 0.0
    z = (g - g.mean()) / (g.std() or 1)
    pencilan = [str(k) for k, v in z.items() if abs(v) > 2.5]
    skor = 0.35 * min(cv, 2) / 2 + 0.45 * (top3 if len(g) > 3 else hhi) + 0.2 * bool(pencilan)
    alasan = f"{len(g)} kategori; 3 teratas menyumbang {top3:.0%}"
    if pencilan:
        alasan += f"; menonjol: {', '.join(pencilan[:3])}"
    return round(skor, 3), alasan


def _skor_tren(g: pd.Series) -> tuple[float, str]:
    if len(g) < 3:
        return 0.0, ""
    x = np.arange(len(g), dtype=float)
    y = g.to_numpy(dtype=float)
    miring, potong = np.polyfit(x, y, 1)
    prediksi = miring * x + potong
    ss_tot = float(((y - y.mean()) ** 2).sum()) or 1.0
    r2 = max(0.0, 1 - float(((y - prediksi) ** 2).sum()) / ss_tot)
    persen = miring / abs(y.mean()) if y.mean() else 0.0
    arah = "naik" if miring > 0 else "turun"
    skor = 0.5 * r2 + 0.5 * min(abs(persen) * 5, 1)
    return round(skor, 3), f"tren {arah} ±{abs(persen):.1%} per periode (R²={r2:.2f})"


def _kmeans(x: np.ndarray, k: int = 3, putaran: int = 30, seed: int = 7) -> np.ndarray:
    """K-means sederhana (numpy) - cukup untuk puluhan kategori."""
    rng = np.random.default_rng(seed)
    pusat = x[rng.choice(len(x), size=k, replace=False)]
    for _ in range(putaran):
        label = np.argmin(((x[:, None, :] - pusat[None, :, :]) ** 2).sum(-1), axis=1)
        baru = np.array([x[label == i].mean(0) if (label == i).any() else pusat[i] for i in range(k)])
        if np.allclose(baru, pusat):
            break
        pusat = baru
    return label


def kandidat(df: pd.DataFrame, peran: dict, fokus: str = "", dimensi: list[str] | None = None) -> tuple[list[Saran], list[str]]:
    """Bentuk & beri skor calon chart. Kembalikan (saran, wawasan teks)."""
    ukuran = peran["ukuran"]
    dims = [d for d in peran["dimensi"] if not dimensi or d in dimensi]
    if fokus:
        ukuran = [fokus] + [u for u in ukuran if u != fokus]
    saran: list[Saran] = []
    wawasan: list[str] = []
    num = df[ukuran].apply(pd.to_numeric, errors="coerce") if ukuran else pd.DataFrame()

    for u in ukuran[:4]:
        saran.append(Saran(f"angka-{u}", f"Total {u}", "angka", ["tabel"], [f"SUM({u})"], [],
                           0.35 + (0.1 if u == fokus else 0), "ringkasan utama",
                           [{"kategori": "Total", "nilai": float(num[u].sum())}]))
        sidik_sudah = set()
        for d in dims:
            g = num[u].groupby(df[d].astype(str)).sum().sort_values(ascending=False)
            # Kolom yang isinya setara (mis. kd_cabang & nm_cabang) menghasilkan chart sama: cukup sekali.
            sidik = tuple(round(float(v), 2) for v in g.values)
            if sidik in sidik_sudah:
                continue
            sidik_sudah.add(sidik)
            skor, alasan = _skor_kategori(g)
            jenis = "pie" if len(g) <= 6 and (g >= 0).all() else "batang"
            saran.append(Saran(f"{jenis}-{u}-{d}", f"{u} per {d}", jenis,
                               [j for j in ("batang", "pie", "tabel") if j != jenis],
                               [f"SUM({u})"], [d], skor + (0.1 if u == fokus else 0), alasan, _pratinjau(g)))
        for w in peran["waktu"]:
            g = num[u].groupby(df[w].astype(str)).sum().sort_index()
            skor, alasan = _skor_tren(g)
            if alasan:
                saran.append(Saran(f"garis-{u}-{w}", f"Tren {u} per {w}", "garis", ["batang", "tabel"],
                                   [f"SUM({u})"], [w], skor + 0.05, alasan, _pratinjau(g, 12)))

    if len(dims) >= 2 and ukuran:
        d1, d2, u = dims[0], dims[1], ukuran[0]
        saran.append(Saran(f"tabel-{u}-{d1}-{d2}", f"{u} per {d1} & {d2}", "tabel", ["batang"],
                           [f"SUM({u})"], [d1, d2], 0.3, "rincian dua dimensi"))

    # Korelasi antar-ukuran
    if len(ukuran) >= 2:
        r = num.corr()
        for i, a in enumerate(ukuran):
            for b in ukuran[i + 1:]:
                if abs(r.loc[a, b]) >= 0.7:
                    wawasan.append(f"{a} dan {b} berkorelasi {'positif' if r.loc[a, b] > 0 else 'negatif'} kuat (r={r.loc[a, b]:.2f}).")

    # Segmentasi k-means: kelompokkan kategori berdasarkan profil beberapa ukuran
    if len(ukuran) >= 2 and dims:
        d = dims[0]
        prof = num[ukuran[:4]].groupby(df[d].astype(str)).sum()
        if len(prof) >= 6:
            z = ((prof - prof.mean()) / prof.std().replace(0, 1)).to_numpy()
            label = _kmeans(z, k=3)
            for i in range(3):
                anggota = list(prof.index[label == i])
                if anggota:
                    wawasan.append(f"Segmen {i + 1} {d} (k-means): {', '.join(anggota[:6])}"
                                   f"{' …' if len(anggota) > 6 else ''}")
            saran.append(Saran(f"segmen-{d}", f"Profil {d} ({len(ukuran[:4])} ukuran)", "tabel", ["batang"],
                               [f"SUM({u})" for u in ukuran[:4]], [d], 0.4,
                               "dasar segmentasi k-means (lihat wawasan)"))

    saran.sort(key=lambda s: s.skor, reverse=True)
    return saran, wawasan


# --- API untuk tampilan ---------------------------------------------------------------
def sarankan(dataset_id: int, fokus: str = "", dimensi: list[str] | None = None, jumlah: int = 8) -> dict:
    df = _sampel(dataset_id)
    if df.empty:
        return {"saran": [], "wawasan": [], "profil": {},
                "catatan": "Tidak ada data yang boleh Anda lihat di dataset ini."}
    peran = profil_kolom(df)
    if fokus and fokus not in peran["ukuran"]:
        fokus = ""
    saran, wawasan = kandidat(df, peran, fokus, dimensi)
    return {"saran": [asdict(s) for s in saran[:max(1, min(jumlah, 20))]], "wawasan": wawasan,
            "profil": peran, "jumlah_sampel": len(df)}


def buat_dari_saran(dataset_id: int, pilihan: list[dict], judul_dashboard: str = "") -> dict:
    """pilihan: [{jenis, judul, metrik, kelompok}] -> chart (+ dashboard bila diberi judul)."""
    charts = [alat.buat_chart(dataset_id, p["jenis"], p.get("judul", ""), p["metrik"], p.get("kelompok"))
              for p in pilihan]
    hasil: dict = {"chart": charts}
    tersimpan = [c["id"] for c in charts if c.get("disimpan")]
    if judul_dashboard and tersimpan:
        hasil["dashboard"] = alat.buat_dashboard(judul_dashboard, tersimpan,
                                                 "Dibuat otomatis oleh Auto Dashboard (Asisten AI).")
    return hasil
