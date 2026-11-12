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
# Kata kunci pengenal sebagai potongan nama utuh (dipisah _): ID_Tiket, kd_cabang, provinsi_kode, NIK, uuid.
POLA_PENGENAL = re.compile(r"(^|_)(id|kd|kode|no|nomor|nik|nip|npwp|key|uuid|sku)(_|$)", re.I)
POLA_PENGENAL_CAMEL = re.compile(r"^(id|kode)[A-Z]|[a-z0-9](Id|ID|Kode|Key)$")


def kolom_pengenal(nama: str) -> bool:
    """Kolom kode/ID: angka tapi bukan untuk dijumlah -> selalu Dimensi.

    Awalan alias tabel dari Kueri Visual (mis. "t1.ID_Penerbangan") dibuang dulu; dulu awalan itu membuat
    ID_Penerbangan terbaca sebagai Ukuran."""
    dasar = str(nama).rsplit(".", 1)[-1]
    return bool(POLA_ID.search(dasar) or POLA_PENGENAL.search(dasar) or POLA_PENGENAL_CAMEL.search(dasar))
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
    spec: dict = field(default_factory=dict)       # rak Studio (kolom, baris, warna, ukuran) untuk jenis ini


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
        elif kolom_pengenal(kolom) and unik / n > 0.5:
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


# --- Spesifikasi Studio: satu bentuk untuk semua jenis chart (dipakai Studio, Auto Dashboard, Asisten AI) ---------
def _uk(kolom: str, agg: str = "SUM") -> dict:
    return {"field": kolom, "peran": "ukuran", "agg": agg}


def _dm(kolom: str) -> dict:
    return {"field": kolom, "peran": "dimensi"}


def spec_dari(tanda: str, ukuran: list[dict], dims: list[str], mendatar: bool = False) -> dict:
    """Rak Studio untuk satu jenis chart. ke_superset membaca dimensi & ukuran berurutan, jadi cukup menaruh
    dimensi pertama di Kolom (atau Baris bila mendatar / pivot) dan dimensi kedua sebagai Warna untuk seri."""
    d = [_dm(x) for x in dims]
    if tanda == "tabel_pivot":
        return {"kolom": d[1:], "baris": d[:1] + ukuran, "warna": None, "ukuran": None}
    if tanda in ("batang", "garis", "area", "batang_100") and len(d) > 1:
        utama = {"kolom": ukuran, "baris": d[:1]} if mendatar else {"kolom": d[:1], "baris": ukuran}
        return {**utama, "warna": d[1], "ukuran": None}
    if mendatar and tanda == "batang":
        return {"kolom": ukuran, "baris": d, "warna": None, "ukuran": None}
    return {"kolom": d, "baris": ukuran, "warna": None, "ukuran": None}


def jenis_cocok(nd: int, nu: int, geo_titik: bool = False) -> list[str]:
    """Semua jenis chart yang menerima jumlah dimensi & ukuran ini (aturan Tampilkan Saya)."""
    from sps_studio.aturan import ATURAN_TANDA
    return [k for k, a in ATURAN_TANDA.items() if a["dim"][0] <= nd <= a["dim"][1] and a["ukuran"][0] <= nu <= a["ukuran"][1]
            and (a.get("geo") != "titik" or geo_titik) and not a.get("waktu")]


def _saran(tanda: str, judul: str, skor: float, alasan: str, ukuran: list[dict], dims: list[str],
           pratinjau: list[dict] | None = None, mendatar: bool = False, geo_titik: bool = False) -> Saran:
    spec = spec_dari(tanda, ukuran, dims, mendatar)
    metrik = [f"{u['agg']}({u['field']})" for u in ukuran]
    alternatif = [j for j in jenis_cocok(len(dims), len(ukuran), geo_titik) if j != tanda]
    return Saran(f"{tanda}-{'-'.join(dims)}-{'-'.join(u['field'] for u in ukuran)}", judul, tanda, alternatif,
                 metrik, list(dims), round(skor, 3), alasan, pratinjau or [], spec)


def _peran_geo(df: pd.DataFrame, peran: dict) -> dict:
    """Pisahkan kolom lintang/bujur (bukan ukuran) & kolom provinsi; tambah ke peran."""
    from sps_studio.lembar import peran_geo
    geo = {"lintang": None, "bujur": None, "wilayah": None}
    for kolom in df.columns:
        jenis = peran_geo(str(kolom))
        if jenis and geo[jenis] is None:
            geo[jenis] = kolom
    for k in ("lintang", "bujur"):
        if geo[k] in peran["ukuran"]:
            peran["ukuran"].remove(geo[k])
    return geo


def kandidat(df: pd.DataFrame, peran: dict, fokus: str = "", dimensi: list[str] | None = None) -> tuple[list[Saran], list[str]]:
    """Bentuk & beri skor calon chart dari SEMUA jenis yang cocok dengan bentuk data. Kembalikan (saran, wawasan)."""
    geo = _peran_geo(df, peran)
    ukuran = peran["ukuran"]
    dims = [d for d in peran["dimensi"] if not dimensi or d in dimensi]
    if fokus:
        ukuran = [fokus] + [u for u in ukuran if u != fokus]
    saran: list[Saran] = []
    wawasan: list[str] = []
    num = df[ukuran].apply(pd.to_numeric, errors="coerce") if ukuran else pd.DataFrame()
    unik = {d: df[d].nunique() for d in dims}
    bonus = lambda u: 0.1 if u == fokus else 0.0  # noqa: E731

    for u in ukuran[:3]:
        U = [_uk(u)]
        total = float(num[u].sum())
        saran.append(_saran("angka", f"Total {u}", 0.34 + bonus(u), "ringkasan utama", U, [],
                            [{"kategori": "Total", "nilai": total}]))
        saran.append(_saran("gauge", f"Capaian {u}", 0.12, "satu angka dalam skala (isi target di Superset)", U, []))
        sidik_sudah = set()
        for d in dims:
            g = num[u].groupby(df[d].astype(str)).sum().sort_values(ascending=False)
            sidik = tuple(round(float(v), 2) for v in g.values)       # kd_x & nm_x setara: cukup sekali
            if sidik in sidik_sudah:
                continue
            sidik_sudah.add(sidik)
            skor, alasan = _skor_kategori(g)
            n, positif = len(g), bool((g >= 0).all())
            prat = _pratinjau(g)
            saran.append(_saran("batang", f"{u} per {d}", skor + bonus(u), alasan, U, [d], prat, mendatar=n > 8))
            if 2 <= n <= 6 and positif:
                saran.append(_saran("pie", f"Porsi {u} per {d}", skor - 0.04, f"komposisi {n} bagian", U, [d], prat))
            if 3 <= n <= 8 and positif:
                saran.append(_saran("funnel", f"Corong {u} per {d}", skor - 0.12, "urutan dari terbesar", U, [d], prat))
            if n >= 6 and positif:
                saran.append(_saran("treemap", f"Peta pohon {u} per {d}", skor - 0.06,
                                    f"{n} kategori dalam satu bidang", U, [d], prat))
            if n >= 15 and df[d].dtype == object:
                saran.append(_saran("awan_kata", f"Awan kata {d}", 0.16, f"{n} istilah, ukuran = {u}", U, [d], prat))
            if d == geo["wilayah"]:
                saran.append(_saran("peta_wilayah", f"Peta {u} per provinsi", 0.5 + bonus(u),
                                    "kolom provinsi dikenali: sebaran wilayah", U, [d], prat))
        for w in peran["waktu"]:
            g = num[u].groupby(df[w].astype(str)).sum().sort_index()
            skor, alasan = _skor_tren(g)
            if not alasan:
                continue
            prat = _pratinjau(g, 12)
            saran.append(_saran("garis", f"Tren {u} per {w}", skor + 0.05 + bonus(u), alasan, U, [w], prat))
            saran.append(_saran("area", f"Volume {u} per {w}", skor - 0.04, alasan, U, [w], prat))
            if len(g) <= 24:
                saran.append(_saran("waterfall", f"Perubahan {u} per {w}", skor * 0.6, "naik-turun antar periode",
                                    U, [w], prat))
            for d in dims[:2]:
                if unik[d] <= 10:
                    saran.append(_saran("garis", f"Tren {u} per {w} menurut {d}", skor + 0.02, f"{alasan}; dirinci {d}",
                                        U, [w, d], prat))
                    saran.append(_saran("peta_panas", f"Pola {u}: {w} × {d}", 0.3, "pola musiman per kategori",
                                        U, [w, d]))

    # Dua dimensi kategori
    pasangan = [(a, b) for i, a in enumerate(dims) for b in dims[i + 1:] if unik[a] <= 15 and unik[b] <= 12][:3]
    if ukuran:
        u, U = ukuran[0], [_uk(ukuran[0])]
        for d1, d2 in pasangan:
            n_sel = max(unik[d1] * unik[d2], 1)
            saran += [
                _saran("batang", f"{u} per {d1} & {d2}", 0.32, "perbandingan bertumpuk", U, [d1, d2]),
                _saran("batang_100", f"Komposisi {d2} di tiap {d1}", 0.28, "porsi relatif per kategori", U, [d1, d2]),
                _saran("peta_panas", f"{u}: {d1} × {d2}", 0.29, "pola silang dua kategori", U, [d1, d2]),
                _saran("tabel_pivot", f"Pivot {u}: {d1} × {d2}", 0.27, "rincian silang + total", U, [d1, d2]),
                _saran("sunburst", f"Hierarki {d1} → {d2}", 0.25, "komposisi bertingkat", U, [d1, d2]),
                _saran("sankey", f"Alur {d1} → {d2}", 0.22, "aliran nilai antar kategori", U, [d1, d2]),
            ]
            if len(df) / n_sel >= 3:
                saran.append(_saran("box_plot", f"Sebaran {u} per {d1}", 0.2, f"variasi {u} di dalam tiap {d1}", U, [d1, d2]))

    # Beberapa ukuran: korelasi (sebar) & profil (radar)
    if len(ukuran) >= 2 and dims:
        r = num.corr()
        a, b = ukuran[0], ukuran[1]
        kuat = abs(float(r.loc[a, b])) if not np.isnan(r.loc[a, b]) else 0.0
        U3 = [_uk(x) for x in ukuran[:3]]
        saran.append(_saran("sebar", f"{a} vs {b} per {dims[0]}", 0.22 + 0.4 * kuat,
                            f"korelasi r={float(r.loc[a, b]):.2f}", U3, [dims[0]]))
        for i, x in enumerate(ukuran):
            for y in ukuran[i + 1:]:
                if abs(r.loc[x, y]) >= 0.7:
                    wawasan.append(f"{x} dan {y} berkorelasi {'positif' if r.loc[x, y] > 0 else 'negatif'} kuat (r={r.loc[x, y]:.2f}).")
        d_radar = next((d for d in dims if 3 <= unik[d] <= 10), None)
        if len(ukuran) >= 3 and d_radar:
            saran.append(_saran("radar", f"Profil {d_radar} ({min(len(ukuran), 6)} ukuran)", 0.24,
                                "membandingkan beberapa ukuran sekaligus", [_uk(x) for x in ukuran[:6]], [d_radar]))

    # Peta titik dari lintang/bujur
    if geo["lintang"] and geo["bujur"]:
        U = [_uk(ukuran[0])] if ukuran else []
        saran.append(_saran("peta_titik", "Sebaran lokasi", 0.5, "kolom lintang & bujur dikenali", U,
                            [geo["lintang"], geo["bujur"]], geo_titik=True))
        saran.append(_saran("peta_kepadatan", "Kepadatan lokasi", 0.36, "konsentrasi titik per area", U,
                            [geo["lintang"], geo["bujur"]], geo_titik=True))

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
            saran.append(_saran("tabel", f"Profil {d} ({len(ukuran[:4])} ukuran)", 0.3,
                                "dasar segmentasi k-means (lihat wawasan)", [_uk(x) for x in ukuran[:4]], [d]))

    if dims and ukuran:
        saran.append(_saran("tabel", f"Rincian {ukuran[0]} per {', '.join(dims[:3])}", 0.15, "tabel rinci",
                            [_uk(ukuran[0])], dims[:3]))
    return _ragamkan(saran), wawasan


def _ragamkan(saran: list[Saran], per_jenis: int = 2) -> list[Saran]:
    """Urutkan menurut skor, tetapi tiap jenis maksimal `per_jenis` di depan, agar usulan beragam."""
    saran.sort(key=lambda s: s.skor, reverse=True)
    hitung: dict[str, int] = {}
    depan, belakang = [], []
    for s in saran:
        hitung[s.jenis] = hitung.get(s.jenis, 0) + 1
        (depan if hitung[s.jenis] <= per_jenis else belakang).append(s)
    return depan + belakang


# --- API untuk tampilan ---------------------------------------------------------------
def sarankan(dataset_id: int, fokus: str = "", dimensi: list[str] | None = None, jumlah: int = 12) -> dict:
    from sps_studio.aturan import ATURAN_TANDA
    df = _sampel(dataset_id)
    if df.empty:
        return {"saran": [], "wawasan": [], "profil": {},
                "catatan": "Tidak ada data yang boleh Anda lihat di dataset ini."}
    peran = profil_kolom(df)
    if fokus and fokus not in peran["ukuran"]:
        fokus = ""
    saran, wawasan = kandidat(df, peran, fokus, dimensi)
    return {"saran": [asdict(s) for s in saran[:max(1, min(jumlah, 40))]], "wawasan": wawasan,
            "profil": peran, "jumlah_sampel": len(df), "jumlah_jenis": len({s.jenis for s in saran}),
            "label_jenis": {k: a["label"] for k, a in ATURAN_TANDA.items()}}


def buat_dari_saran(dataset_id: int, pilihan: list[dict], judul_dashboard: str = "") -> dict:
    """pilihan: [{jenis, judul, spec | metrik+kelompok}] -> chart (+ dashboard bila diberi judul).
    Dengan spec, semua jenis chart Studio bisa dibuat (pembangun yang sama dengan Studio Visual)."""
    charts = [buat_satu(dataset_id, p) for p in pilihan]
    hasil: dict = {"chart": charts}
    tersimpan = [c["id"] for c in charts if c.get("disimpan")]
    if judul_dashboard and tersimpan:
        hasil["dashboard"] = alat.buat_dashboard(judul_dashboard, tersimpan,
                                                 "Dibuat otomatis oleh Auto Dashboard (Asisten AI).")
    return hasil


def buat_satu(dataset_id: int, p: dict) -> dict:
    from sps_studio import lembar as L
    jenis, spec = str(p.get("jenis") or ""), p.get("spec")
    if not spec and jenis in alat.JENIS_CHART:
        return alat.buat_chart(dataset_id, jenis, p.get("judul", ""), p["metrik"], p.get("kelompok"))
    if not spec:
        ukuran = [_uk(m[1], m[0]) for m in (re.match(r"^(\w+)\((.+)\)$", x).groups() for x in p.get("metrik") or [])]
        spec = spec_dari(jenis, ukuran, list(p.get("kelompok") or []))
    t, lb = L.dari_dict({"dataset_id": dataset_id, "tanda": jenis, "judul": p.get("judul", ""), **spec})
    h = L.simpan(t, lb)
    return {**h, "judul": h.get("judul") or p.get("judul", ""), "jenis": jenis}
