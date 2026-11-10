"""Analitik prediktif untuk lembar kerja :

    ramalan  : Holt (tren) atau Holt-Winters aditif (tren + musiman) bila data cukup,
               dengan pita keyakinan 80% & 95%
    tren     : garis tren linear (kuadrat terkecil) + R²
    anomali  : titik yang menyimpang jauh dari pola (|z robust| > 3,5 setelah tren & musim dibuang)

Hanya numpy (tanpa statsmodels/prophet), deterministik: hasil sama di pratinjau Studio,
dashboard, dan tabel ramalan yang disimpan (ramalan.py).

Sumbu X boleh berupa tanggal, "2025-01", tahun (2021, 2022, ...), atau urutan lain;
label periode ramalan dibuat menyambung pola sumbu X (label_berikut).
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any

import numpy as np

MIN_TITIK_RAMALAN = 4
MAKS_PERIODE = 36
Z80, Z95 = 1.2816, 1.96
BATAS_ANOMALI = 3.5                     # skor-z termodifikasi (Iglewicz & Hoaglin)
_GRID = (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
POLA_BULAN = re.compile(r"^(\d{4})-(\d{1,2})$")
POLA_TANGGAL = re.compile(r"^\d{4}-\d{2}-\d{2}")


# --- Sumbu X: urutan & label periode berikutnya --------------------------------------------
def _ke_tanggal(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, (int, float)) and v > 1e11:                    # epoch milidetik (Superset)
        return datetime.utcfromtimestamp(v / 1000)
    if isinstance(v, str) and POLA_TANGGAL.match(v):
        try:
            return datetime.fromisoformat(v.replace("Z", "")[:19])
        except ValueError:
            return None
    return None


def kunci_urut(v: Any):
    t = _ke_tanggal(v)
    if t is not None:
        return (0, t.timestamp())
    if isinstance(v, (int, float)):
        return (0, float(v))
    m = POLA_BULAN.match(str(v))
    if m:
        return (0, int(m[1]) * 12 + int(m[2]))
    return (1, str(v))


def _tambah_bulan(t: datetime, n: int) -> datetime:
    b = t.month - 1 + n
    tahun, bulan = t.year + b // 12, b % 12 + 1
    hari = min(t.day, [31, 29 if tahun % 4 == 0 and (tahun % 100 or tahun % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][bulan - 1])
    return t.replace(year=tahun, month=bulan, day=hari)


def _langkah_bulan(ts: list[datetime]) -> int:
    """Selisih bulan yang paling sering antar-titik (0 = bukan data bulanan/tahunan)."""
    if len(ts) < 2 or any(t.day != ts[0].day for t in ts[:3]):
        return 0
    beda = [(b.year - a.year) * 12 + b.month - a.month for a, b in zip(ts, ts[1:])]
    return max(set(beda), key=beda.count) if beda else 0


def label_berikut(xs: list, n: int) -> list:
    """Label n periode setelah xs (xs sudah urut)."""
    if not xs or n <= 0:
        return []
    akhir = xs[-1]
    ts = [_ke_tanggal(x) for x in xs]
    if all(ts):
        lb = _langkah_bulan(ts)
        if lb > 0:
            hasil = [_tambah_bulan(ts[-1], lb * i) for i in range(1, n + 1)]
        else:
            langkah = np.median(np.diff([t.timestamp() for t in ts])) if len(ts) > 1 else 86400
            hasil = [datetime.utcfromtimestamp(ts[-1].timestamp() + langkah * i) for i in range(1, n + 1)]
        bentuk = "%Y-%m-%d" if isinstance(akhir, str) and len(akhir) <= 10 else "%Y-%m-%dT%H:%M:%S"
        if isinstance(akhir, (int, float)):
            return [int(t.timestamp() * 1000) for t in hasil]
        return [t.strftime(bentuk) for t in hasil]
    if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in xs):
        langkah = int(np.median(np.diff(xs))) if len(xs) > 1 else 1
        return [akhir + langkah * i for i in range(1, n + 1)]
    m = POLA_BULAN.match(str(akhir))
    if m and all(POLA_BULAN.match(str(x)) for x in xs):
        dasar = int(m[1]) * 12 + int(m[2]) - 1
        return [f"{(dasar + i) // 12}-{(dasar + i) % 12 + 1:02d}" for i in range(1, n + 1)]
    return [f"+{i}" for i in range(1, n + 1)]


def periode_musim(xs: list) -> int:
    """Panjang musim dari pola sumbu X: bulanan -> 12, triwulan -> 4, harian -> 7, lainnya 0."""
    ts = [_ke_tanggal(x) for x in xs]
    if all(ts) and len(ts) > 2:
        lb = _langkah_bulan(ts)
        if lb == 1:
            return 12
        if lb == 3:
            return 4
        if lb == 0 and abs(np.median(np.diff([t.timestamp() for t in ts])) - 86400) < 3600:
            return 7
        return 0
    if all(POLA_BULAN.match(str(x)) for x in xs):
        return 12
    return 0


# --- Model ---------------------------------------------------------------------------------
def _holt(y: np.ndarray, a: float, b: float):
    """Holt linear. Kembalikan (galat langkah-1, level, tren)."""
    level, tren = y[0], y[1] - y[0]
    galat = np.zeros(len(y))
    for t in range(1, len(y)):
        prediksi = level + tren
        galat[t] = y[t] - prediksi
        level_baru = a * y[t] + (1 - a) * prediksi
        tren = b * (level_baru - level) + (1 - b) * tren
        level = level_baru
    return galat[1:], level, tren


def _holt_winters(y: np.ndarray, m: int, a: float, b: float, g: float):
    """Holt-Winters aditif. Kembalikan (galat langkah-1, level, tren, musim)."""
    level = y[:m].mean()
    tren = (y[m:2 * m].mean() - y[:m].mean()) / m
    musim = list(y[:m] - level)
    galat = []
    for t in range(m, len(y)):
        s = musim[t - m]
        prediksi = level + tren + s
        galat.append(y[t] - prediksi)
        level_baru = a * (y[t] - s) + (1 - a) * (level + tren)
        tren = b * (level_baru - level) + (1 - b) * tren
        musim.append(g * (y[t] - level_baru) + (1 - g) * s)
        level = level_baru
    return np.array(galat), level, tren, musim[-m:]


def ramal(y: list[float], h: int, m: int = 0) -> dict:
    """Ramalan h periode. Parameter penghalus dipilih dari grid (galat kuadrat terkecil)."""
    y = np.asarray(y, dtype=float)
    musiman = m >= 2 and len(y) >= 2 * m + 2
    terbaik = None
    for a in _GRID:
        for b in _GRID[:5]:
            for g in (_GRID[:5] if musiman else (None,)):
                hasil = _holt_winters(y, m, a, b, g) if musiman else _holt(y, a, b)
                sse = float(np.sum(hasil[0] ** 2))
                if terbaik is None or sse < terbaik[0]:
                    terbaik = (sse, (a, b, g), hasil)
    _, (a, b, g), hasil = terbaik
    galat, level, tren = hasil[0], hasil[1], hasil[2]
    sigma = float(np.sqrt(np.sum(galat ** 2) / max(1, len(galat) - 2)))
    titik, lebar = [], []
    for k in range(1, h + 1):
        nilai = level + k * tren + (hasil[3][(k - 1) % m] if musiman else 0.0)
        # Varians ramalan k langkah (Hyndman & Athanasopoulos, model ETS aditif)
        var = 1 + sum((a + j * a * b + (g if musiman and j % m == 0 else 0)) ** 2 for j in range(1, k))
        titik.append(float(nilai))
        lebar.append(sigma * math.sqrt(var))
    cocok = y[len(y) - len(galat):] - galat
    return {"metode": "Holt-Winters (musiman %d)" % m if musiman else "Holt (tren linear)",
            "parameter": {"alpha": a, "beta": b, **({"gamma": g} if musiman else {})},
            "nilai": titik, "lebar": lebar, "sigma": sigma, "cocok": cocok.tolist(),
            "awal_cocok": len(y) - len(galat)}


def tren_linear(y: list[float]) -> dict:
    y = np.asarray(y, dtype=float)
    x = np.arange(len(y), dtype=float)
    kemiringan, intersep = np.polyfit(x, y, 1)
    garis = kemiringan * x + intersep
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum((y - garis) ** 2)) / ss_tot if ss_tot else 1.0
    return {"kemiringan": float(kemiringan), "intersep": float(intersep), "r2": round(r2, 4),
            "nilai": garis.tolist()}


def _tren_bergerak(y: np.ndarray, w: int, fungsi=np.median) -> np.ndarray:
    """Rata-rata/median bergerak jendela penuh; ujung yang jendelanya tak penuh diisi garis
    lurus (agar ujung data tidak salah dianggap menyimpang)."""
    k = w // 2
    tengah = np.arange(k, len(y) - k)
    if len(tengah) < 2:
        return np.full(len(y), np.median(y))
    nilai = np.array([fungsi(y[i - k:i + k + 1]) for i in tengah])
    hasil = np.interp(np.arange(len(y)), tengah, nilai)
    a, b = np.polyfit(tengah, nilai, 1)
    hasil[:k] = a * np.arange(k) + b
    hasil[len(y) - k:] = a * np.arange(len(y) - k, len(y)) + b
    return hasil


def _sisa(y: np.ndarray, m: int) -> np.ndarray:
    """Sisa setelah tren (rata-rata/median bergerak) & pola musiman dibuang."""
    musiman = m >= 2 and len(y) >= 2 * m
    if musiman:        # dekomposisi klasik: rata-rata bergerak satu musim penuh menghapus pola musim
        tren = _tren_bergerak(y, m + (1 - m % 2), np.mean)
    else:
        tren = _tren_bergerak(y, min(5, len(y)) | 1)
    sisa = y - tren
    if musiman:
        # median per posisi musim butuh >= 5 musim; lebih sedikit -> rata-rata (median 3 nilai
        # membuat satu sisa selalu 0 sehingga simpangan dianggap terlalu kecil)
        pusat = np.median if len(y) >= 5 * m else np.mean
        musim = np.array([pusat(sisa[i::m]) for i in range(m)])
        sisa = sisa - np.resize(musim, len(y))
    return sisa


def anomali(y: list[float], m: int = 0) -> list[int]:
    """Indeks titik yang menyimpang (> 3,5 simpangan robust/MAD dari pola tren + musim).

    Bertahap seperti Generalized ESD: titik paling menyimpang ditandai, nilainya diganti nilai
    harapan, lalu pola dihitung ulang. Dengan begitu satu lonjakan besar tidak "menular" ke
    bulan yang sama di tahun lain lewat rata-rata musiman.
    """
    y = np.asarray(y, dtype=float).copy()
    hasil: list[int] = []
    sisa0 = _sisa(y, m)
    mad = float(np.median(np.abs(sisa0 - np.median(sisa0)))) * 1.4826   # skala dari data asli
    if mad == 0:
        return []
    for _ in range(max(1, len(y) // 10)):
        sisa = _sisa(y, m)
        z = (sisa - np.median(sisa)) / mad
        z[hasil] = 0
        i = int(np.argmax(np.abs(z)))
        if abs(z[i]) <= BATAS_ANOMALI:
            break
        hasil.append(i)
        y[i] -= sisa[i] - np.median(sisa)          # ganti dengan nilai harapan
    return sorted(hasil)


# --- Untuk lembar kerja ------------------------------------------------------------------------
def analisis(baris: list[dict], dim: str, ukuran: list[str], opsi: dict) -> dict:
    """Hitung ramalan/tren/anomali tiap ukuran. opsi = {"ramalan": n, "tren": bool, "anomali": bool}."""
    data = sorted((b for b in baris if b.get(dim) is not None), key=lambda b: kunci_urut(b[dim]))
    xs = [b[dim] for b in data]
    h = max(0, min(int(opsi.get("ramalan") or 0), MAKS_PERIODE))
    m = periode_musim(xs)
    hasil = {"x": xs, "x_ramalan": label_berikut(xs, h) if h else [], "seri": {}, "catatan": []}
    for u in ukuran:
        y = [b.get(u) for b in data]
        if any(v is None for v in y):
            y = [v if v is not None else 0.0 for v in y]
        y = [float(v) for v in y]
        s: dict[str, Any] = {}
        if opsi.get("tren") and len(y) >= 2:
            s["tren"] = tren_linear(y)
        if (h or opsi.get("anomali")) and len(y) >= MIN_TITIK_RAMALAN:
            if h:
                r = ramal(y, h, m)
                s["ramalan"] = {
                    "metode": r["metode"], "parameter": r["parameter"], "nilai": r["nilai"],
                    "bawah80": [v - Z80 * w for v, w in zip(r["nilai"], r["lebar"])],
                    "atas80": [v + Z80 * w for v, w in zip(r["nilai"], r["lebar"])],
                    "bawah95": [v - Z95 * w for v, w in zip(r["nilai"], r["lebar"])],
                    "atas95": [v + Z95 * w for v, w in zip(r["nilai"], r["lebar"])]}
            if opsi.get("anomali"):
                s["anomali"] = [{"i": i, "x": xs[i], "nilai": y[i]} for i in anomali(y, m)]
        elif h or opsi.get("anomali"):
            hasil["catatan"].append(f"{u}: butuh minimal {MIN_TITIK_RAMALAN} titik untuk ramalan/anomali.")
        hasil["seri"][u] = s
    return hasil
