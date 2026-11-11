"""Data latihan FIKTIF "Penerbangan" dalam bentuk Excel (atau CSV) untuk mencoba & memamerkan ALDx.

Enam tabel yang saling terhubung, seperti sistem reservasi maskapai sungguhan:

    maskapai     kd_maskapai (PK)  maskapai rekaan, jenis layanan
    bandara      kd_iata (PK)      bandara Indonesia (kode IATA, provinsi ISO, lintang/bujur -> peta)
    penerbangan  no_penerbangan    rute tetap: maskapai, asal -> tujuan, jarak, pesawat, kapasitas
    jadwal       id_jadwal         satu keberangkatan pada satu tanggal + status (tepat waktu/terlambat/batal)
    penumpang    id_penumpang      orang FIKTIF: usia, domisili, keanggotaan
    tiket        no_tiket          fakta penjualan: jadwal, penumpang, kelas, saluran, harga, status

    maskapai 1-N penerbangan N-1 bandara (asal & tujuan)
    penerbangan 1-N jadwal 1-N tiket N-1 penumpang

Pola yang sengaja ditanam (bahan latihan analisis):
    - tren naik tiap tahun, lonjakan mudik Lebaran, libur sekolah Juli, dan akhir tahun
    - keterlambatan lebih sering di musim hujan (Des-Feb)
    - INSIDEN: semua penerbangan dari/ke DPS (Bali) batal pada 12-13 November 2024 (abu vulkanik)
    - harga naik bila tiket dibeli mendekati hari terbang

Benih acak tetap: ukuran yang sama selalu menghasilkan isi yang sama, jadi bahan ajar bisa menyebut
angka pasti. Semua nama orang & maskapai rekaan; kode/nama bandara memakai data publik.

Pakai (di komputer mana pun yang punya Python + numpy, pandas, openpyxl):
    python sps_latihan_penerbangan.py --ukuran sedang --keluar contoh-penerbangan-sedang.xlsx
    python sps_latihan_penerbangan.py --tiket 3000000 --format csv --keluar penerbangan-3jt
Di server ALDx (tanpa Python di Windows):  scripts\\data-penerbangan.ps1
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

BENIH = 2026
AWAL, AKHIR = "2023-01-01", "2025-12-31"
MAKS_BARIS_LEMBAR = 1_000_000          # batas Excel 1.048.576; dibulatkan agar mudah dihitung
PENULIS_BERKAS = "ALDx"

# ukuran -> jumlah tiket, jadwal, penumpang. Ukuran "kecil" = sampel (tingkat isian kursi rendah).
UKURAN = {
    "kecil": (1_000, 300, 600),
    "sedang": (150_000, 1_100, 40_000),
    "besar": (1_000_000, 7_000, 250_000),
}

# ---------------------------------------------------------------------------------------------
# 1. Data induk (tetap)
# ---------------------------------------------------------------------------------------------
MASKAPAI = [  # kode, nama rekaan, jenis, tahun berdiri, faktor harga, % kelas bisnis
    ("NA", "Nusa Air", "Layanan penuh", 1998, 1.35, 0.12),
    ("RJ", "Rajawali Jet", "Layanan penuh", 2005, 1.25, 0.10),
    ("KA", "Kenari Airlines", "Layanan menengah", 2011, 1.05, 0.05),
    ("SW", "Samudra Wings", "Layanan menengah", 2014, 1.00, 0.04),
    ("CK", "Cakrawala Air", "Berbiaya hemat", 2009, 0.80, 0.0),
    ("TB", "Terbang Bersama", "Berbiaya hemat", 2016, 0.75, 0.0),
    ("PL", "Pelangi Air", "Berbiaya hemat", 2019, 0.72, 0.0),
    ("AR", "Arunika Regional", "Regional", 2012, 1.10, 0.0),
]

BANDARA = [  # IATA, nama, kota, provinsi ISO, pulau, lintang, bujur, bobot keramaian
    ("CGK", "Soekarno-Hatta", "Tangerang", "ID-BT", "Jawa", -6.1256, 106.6559, 10.0),
    ("HLP", "Halim Perdanakusuma", "Jakarta", "ID-JK", "Jawa", -6.2666, 106.8910, 2.5),
    ("SUB", "Juanda", "Surabaya", "ID-JI", "Jawa", -7.3798, 112.7868, 5.0),
    ("DPS", "I Gusti Ngurah Rai", "Denpasar", "ID-BA", "Bali & Nusa Tenggara", -8.7482, 115.1675, 6.0),
    ("KNO", "Kualanamu", "Deli Serdang", "ID-SU", "Sumatra", 3.6422, 98.8853, 4.0),
    ("UPG", "Sultan Hasanuddin", "Makassar", "ID-SN", "Sulawesi", -5.0617, 119.5540, 4.0),
    ("YIA", "Yogyakarta International", "Kulon Progo", "ID-YO", "Jawa", -7.9006, 110.0573, 3.0),
    ("BPN", "Sultan Aji Muhammad Sulaiman", "Balikpapan", "ID-KI", "Kalimantan", -1.2683, 116.8945, 3.0),
    ("KJT", "Kertajati", "Majalengka", "ID-JB", "Jawa", -6.6486, 108.1669, 1.0),
    ("SRG", "Jenderal Ahmad Yani", "Semarang", "ID-JT", "Jawa", -6.9727, 110.3750, 2.2),
    ("SOC", "Adi Soemarmo", "Surakarta", "ID-JT", "Jawa", -7.5161, 110.7569, 1.2),
    ("PLM", "Sultan Mahmud Badaruddin II", "Palembang", "ID-SS", "Sumatra", -2.8983, 104.6999, 2.0),
    ("PDG", "Minangkabau", "Padang", "ID-SB", "Sumatra", -0.7869, 100.2800, 1.8),
    ("PKU", "Sultan Syarif Kasim II", "Pekanbaru", "ID-RI", "Sumatra", 0.4608, 101.4445, 1.8),
    ("BTH", "Hang Nadim", "Batam", "ID-KR", "Sumatra", 1.1210, 104.1190, 2.0),
    ("BTJ", "Sultan Iskandar Muda", "Banda Aceh", "ID-AC", "Sumatra", 5.5229, 95.4206, 1.0),
    ("TKG", "Radin Inten II", "Bandar Lampung", "ID-LA", "Sumatra", -5.2406, 105.1758, 1.0),
    ("PNK", "Supadio", "Pontianak", "ID-KB", "Kalimantan", -0.1507, 109.4039, 1.5),
    ("BDJ", "Syamsudin Noor", "Banjarmasin", "ID-KS", "Kalimantan", -3.4424, 114.7625, 1.6),
    ("MDC", "Sam Ratulangi", "Manado", "ID-SA", "Sulawesi", 1.5493, 124.9260, 1.5),
    ("LOP", "Zainuddin Abdul Madjid", "Lombok Tengah", "ID-NB", "Bali & Nusa Tenggara", -8.7573, 116.2767, 1.6),
    ("KOE", "El Tari", "Kupang", "ID-NT", "Bali & Nusa Tenggara", -10.1716, 123.6711, 1.0),
    ("LBJ", "Komodo", "Labuan Bajo", "ID-NT", "Bali & Nusa Tenggara", -8.4866, 119.8890, 0.8),
    ("AMQ", "Pattimura", "Ambon", "ID-MA", "Maluku", -3.7103, 128.0890, 0.9),
    ("DJJ", "Sentani", "Jayapura", "ID-PA", "Papua", -2.5769, 140.5164, 1.0),
    ("SOQ", "Domine Eduard Osok", "Sorong", "ID-PB", "Papua", -0.8945, 131.2870, 0.6),
]

# Rute dua arah: (asal, tujuan, [maskapai yang melayani]). Nomor penerbangan dibuat otomatis.
RUTE = [
    ("CGK", "DPS", ["NA", "RJ", "CK", "TB", "PL"]), ("CGK", "SUB", ["NA", "RJ", "KA", "CK", "TB"]),
    ("CGK", "KNO", ["NA", "RJ", "CK", "SW"]), ("CGK", "UPG", ["NA", "CK", "KA"]),
    ("CGK", "YIA", ["NA", "CK", "TB"]), ("CGK", "BPN", ["NA", "CK", "SW"]),
    ("CGK", "PLM", ["NA", "CK"]), ("CGK", "PDG", ["NA", "CK"]), ("CGK", "PKU", ["NA", "TB"]),
    ("CGK", "BTH", ["CK", "PL"]), ("CGK", "BTJ", ["NA"]), ("CGK", "TKG", ["AR"]),
    ("CGK", "PNK", ["NA", "SW"]), ("CGK", "BDJ", ["NA", "CK"]), ("CGK", "MDC", ["NA", "KA"]),
    ("CGK", "LOP", ["NA", "CK"]), ("CGK", "DJJ", ["NA"]), ("CGK", "SRG", ["NA", "CK"]),
    ("HLP", "SUB", ["KA", "PL"]), ("HLP", "DPS", ["KA"]), ("HLP", "YIA", ["KA"]),
    ("SUB", "DPS", ["CK", "AR"]), ("SUB", "UPG", ["CK", "KA"]), ("SUB", "BPN", ["CK", "SW"]),
    ("SUB", "BDJ", ["CK", "AR"]), ("SUB", "LOP", ["AR"]), ("SUB", "KNO", ["RJ"]),
    ("DPS", "LOP", ["AR"]), ("DPS", "LBJ", ["AR", "NA"]), ("DPS", "KOE", ["AR"]),
    ("DPS", "UPG", ["CK"]), ("UPG", "MDC", ["AR"]), ("UPG", "AMQ", ["AR", "NA"]),
    ("UPG", "DJJ", ["NA", "CK"]), ("UPG", "SOQ", ["AR"]), ("UPG", "BPN", ["AR"]),
    ("KNO", "BTH", ["AR"]), ("KNO", "BTJ", ["AR"]), ("KNO", "PKU", ["AR"]),
    ("KJT", "DPS", ["CK"]), ("SOC", "BPN", ["SW"]), ("YIA", "BPN", ["CK"]),
]

PESAWAT = {  # tipe -> kapasitas kursi; maskapai regional memakai turboprop
    "Boeing 737-800": 189, "Airbus A320neo": 180, "Airbus A330-300": 360, "ATR 72-600": 72,
}

NAMA_DEPAN = ["Adi", "Agus", "Ahmad", "Andi", "Ani", "Arif", "Ayu", "Bayu", "Budi", "Citra", "Dedi", "Dewi",
              "Dian", "Dimas", "Eka", "Fajar", "Fitri", "Gita", "Hadi", "Hana", "Indah", "Intan", "Joko",
              "Kartika", "Lestari", "Maya", "Nanda", "Nur", "Putri", "Rahmat", "Rani", "Rizki", "Sari",
              "Siti", "Taufik", "Tika", "Umar", "Wahyu", "Wulan", "Yanti", "Yoga", "Yusuf"]
NAMA_BELAKANG = ["Pratama", "Saputra", "Wijaya", "Hidayat", "Santoso", "Lubis", "Siregar", "Nasution",
                 "Purnomo", "Kurniawan", "Halim", "Setiawan", "Rahayu", "Utami", "Gunawan", "Simanjuntak",
                 "Tanjung", "Harahap", "Wibowo", "Susanto", "Pangaribuan", "Manurung", "Sembiring", "Hasibuan"]

LEBARAN = ["2023-04-22", "2024-04-10", "2025-03-31"]          # Idul Fitri; ±7 hari = musim mudik
INSIDEN = ("DPS", ["2024-11-12", "2024-11-13"])               # semua jadwal dari/ke DPS batal
SALURAN = {"Aplikasi seluler": 0.46, "Situs web": 0.24, "Agen perjalanan daring": 0.20, "Loket bandara": 0.10}


def buat_maskapai() -> pd.DataFrame:
    kolom = ["kd_maskapai", "nm_maskapai", "jenis_layanan", "tahun_berdiri"]
    return pd.DataFrame([m[:4] for m in MASKAPAI], columns=kolom)


def buat_bandara() -> pd.DataFrame:
    kolom = ["kd_iata", "nm_bandara", "kota", "provinsi", "pulau", "lintang", "bujur"]
    return pd.DataFrame([b[:7] for b in BANDARA], columns=kolom)


def _jarak_km(a: str, b: str) -> int:
    """Jarak lingkaran besar (haversine) antar dua bandara, dibulatkan ke km."""
    posisi = {b[0]: (b[5], b[6]) for b in BANDARA}
    (la1, lo1), (la2, lo2) = (np.radians(posisi[a]), np.radians(posisi[b]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(h)))


def buat_penerbangan(acak: np.random.Generator) -> pd.DataFrame:
    """Satu baris = satu nomor penerbangan (rute satu arah, jam berangkat tetap)."""
    jenis = {m[0]: m[2] for m in MASKAPAI}
    nomor = {m[0]: 100 for m in MASKAPAI}
    baris = []
    for asal, tujuan, daftar in RUTE:
        for kd in daftar:
            jarak = _jarak_km(asal, tujuan)
            if jenis[kd] == "Regional" and jarak < 900:
                pesawat = "ATR 72-600"
            elif jarak > 2500 and jenis[kd] == "Layanan penuh":
                pesawat = "Airbus A330-300"
            else:
                pesawat = "Boeing 737-800" if acak.random() < 0.55 else "Airbus A320neo"
            durasi = int(round((jarak / (500 if pesawat == "ATR 72-600" else 780) * 60 + 25) / 5) * 5)
            for a, t in ((asal, tujuan), (tujuan, asal)):
                nomor[kd] += 1 + int(acak.integers(0, 3))
                jam = f"{int(acak.integers(5, 21)):02d}:{int(acak.choice([0, 15, 30, 45])):02d}"
                baris.append((f"{kd}{nomor[kd]}", kd, a, t, jarak, durasi, pesawat, PESAWAT[pesawat], jam))
    kolom = ["no_penerbangan", "kd_maskapai", "asal", "tujuan", "jarak_km", "durasi_menit",
             "tipe_pesawat", "kapasitas", "jam_berangkat"]
    return pd.DataFrame(baris, columns=kolom)


# ---------------------------------------------------------------------------------------------
# 2. Data transaksi (bergantung ukuran)
# ---------------------------------------------------------------------------------------------
def _bobot_tanggal(tanggal: pd.DatetimeIndex) -> np.ndarray:
    """Permintaan relatif per tanggal: tren + mudik + libur + pola mingguan."""
    tahun_ke = (tanggal - tanggal[0]).days / 365.25
    bobot = 1 + 0.15 * tahun_ke
    for hari_raya in pd.to_datetime(LEBARAN):
        bobot *= np.where(abs((tanggal - hari_raya).days) <= 7, 1.9, 1.0)
    akhir_tahun = ((tanggal.month == 12) & (tanggal.day >= 18)) | ((tanggal.month == 1) & (tanggal.day <= 3))
    bobot *= np.where(akhir_tahun, 1.5, 1.0) * np.where(tanggal.month == 7, 1.3, 1.0)
    bobot *= np.select([tanggal.dayofweek.isin([4, 6]), tanggal.dayofweek.isin([1, 2])], [1.15, 0.9], 1.0)
    return np.asarray(bobot)


def buat_jadwal(acak: np.random.Generator, penerbangan: pd.DataFrame, jumlah: int) -> pd.DataFrame:
    """Pilih pasangan (nomor penerbangan, tanggal) tanpa duplikat, lalu tentukan status."""
    tanggal = pd.date_range(AWAL, AKHIR, freq="D")
    ramai = {b[0]: b[7] for b in BANDARA}
    bobot_rute = (penerbangan["asal"].map(ramai) + penerbangan["tujuan"].map(ramai)).to_numpy()
    bobot = np.outer(bobot_rute, _bobot_tanggal(tanggal)).ravel()
    jumlah = min(jumlah, bobot.size)

    # Ukuran sedang ke atas: semua jadwal DPS pada tanggal insiden pasti ada, agar anomalinya terlihat.
    kd_insiden, tgl_insiden = INSIDEN
    wajib = np.array([], dtype=int)
    if jumlah >= 1_000:
        rute_dps = np.flatnonzero((penerbangan["asal"] == kd_insiden) | (penerbangan["tujuan"] == kd_insiden))
        hari = np.flatnonzero(tanggal.strftime("%Y-%m-%d").isin(tgl_insiden))
        wajib = (rute_dps[:, None] * tanggal.size + hari).ravel()
        bobot[wajib] = 0
    sisa = acak.choice(bobot.size, size=jumlah - wajib.size, replace=False, p=bobot / bobot.sum())
    i_rute, i_tgl = np.divmod(np.sort(np.concatenate([wajib, sisa])), tanggal.size)

    jd = penerbangan.iloc[i_rute][["no_penerbangan", "asal", "tujuan", "jam_berangkat", "durasi_menit"]]
    jd = jd.reset_index(drop=True)
    jd.insert(1, "tanggal", tanggal[i_tgl].date)

    hujan = pd.DatetimeIndex(tanggal[i_tgl]).month.isin([12, 1, 2])
    peluang_telat = np.where(hujan, 0.27, 0.15)
    undian = acak.random(jumlah)
    status = np.select([undian < 0.015, undian < 0.015 + peluang_telat], ["Batal", "Terlambat"], "Tepat waktu")
    kena =((jd["asal"] == kd_insiden) | (jd["tujuan"] == kd_insiden)) & \
        pd.Series(tanggal[i_tgl].strftime("%Y-%m-%d")).isin(tgl_insiden)
    status[kena.to_numpy()] = "Batal"
    telat = np.where(status == "Terlambat", np.round(15 + acak.exponential(40, jumlah)), 0).astype(int)

    berangkat = pd.to_timedelta(jd["jam_berangkat"] + ":00")
    tiba = (berangkat + pd.to_timedelta(jd["durasi_menit"] + telat, unit="min"))
    jd["jam_tiba"] = [f"{int(s // 3600) % 24:02d}:{int(s % 3600 // 60):02d}" for s in tiba.dt.total_seconds()]
    jd["status"] = status
    jd["menit_terlambat"] = telat
    jd.insert(0, "id_jadwal", [f"J{i:06d}" for i in range(1, jumlah + 1)])
    return jd.drop(columns=["asal", "tujuan", "durasi_menit"])


def buat_penumpang(acak: np.random.Generator, jumlah: int) -> pd.DataFrame:
    kota = [b[2] for b in BANDARA]
    bobot_kota = np.array([b[7] for b in BANDARA])
    usia = ["< 18", "18-24", "25-34", "35-44", "45-54", "55+"]
    return pd.DataFrame({
        "id_penumpang": [f"P{i:07d}" for i in range(1, jumlah + 1)],
        "nm_penumpang": [f"{d} {b}" for d, b in zip(acak.choice(NAMA_DEPAN, jumlah), acak.choice(NAMA_BELAKANG, jumlah))],
        "jenis_kelamin": acak.choice(["L", "P"], jumlah),
        "kelompok_usia": acak.choice(usia, jumlah, p=[0.08, 0.17, 0.30, 0.22, 0.14, 0.09]),
        "kota_domisili": acak.choice(kota, jumlah, p=bobot_kota / bobot_kota.sum()),
        "keanggotaan": acak.choice(["Reguler", "Silver", "Gold"], jumlah, p=[0.78, 0.16, 0.06]),
    })


def _bagi_tiket(acak: np.random.Generator, kapasitas: np.ndarray, aktif: np.ndarray, jumlah: int) -> np.ndarray:
    """Jumlah tiket per jadwal: acak proporsional kapasitas, tidak pernah melebihi kursi."""
    bobot = kapasitas * acak.uniform(0.6, 1.0, kapasitas.size) * aktif
    isi = acak.multinomial(jumlah, bobot / bobot.sum())
    while (lebih := np.maximum(isi - kapasitas, 0)).sum():
        isi -= lebih
        sisa = (kapasitas - isi) * aktif
        isi += acak.multinomial(lebih.sum(), sisa / sisa.sum())
    return isi


def buat_tiket(acak: np.random.Generator, jadwal: pd.DataFrame, penerbangan: pd.DataFrame,
               jumlah_penumpang: int, jumlah: int) -> pd.DataFrame:
    rute = penerbangan.set_index("no_penerbangan")
    jd = jadwal.join(rute[["kd_maskapai", "jarak_km", "kapasitas"]], on="no_penerbangan")
    kapasitas = jd["kapasitas"].to_numpy()
    if jumlah > kapasitas.sum():
        raise ValueError(f"Kursi tidak cukup: {jumlah:,} tiket > {kapasitas.sum():,} kursi. Tambah jadwal.")
    per_jadwal = _bagi_tiket(acak, kapasitas, np.ones(len(jd)), jumlah)
    i = np.repeat(np.arange(len(jd)), per_jadwal)

    harga_ = {m[0]: m[4] for m in MASKAPAI}
    bisnis_ = {m[0]: m[5] for m in MASKAPAI}
    kd = jd["kd_maskapai"].to_numpy()[i]
    tgl_terbang = pd.to_datetime(jd["tanggal"]).to_numpy()[i]
    hari_sebelum = np.minimum(acak.gamma(1.6, 13, jumlah).astype(int), 120)
    bisnis = acak.random(jumlah) < pd.Series(kd).map(bisnis_).to_numpy()
    musim = _bobot_tanggal(pd.DatetimeIndex(tgl_terbang)) ** 0.6
    mendadak = 1 + 0.6 * np.exp(-hari_sebelum / 7)
    harga = (350_000 + 1_050 * jd["jarak_km"].to_numpy()[i]) * pd.Series(kd).map(harga_).to_numpy()
    harga = harga * musim * mendadak * np.where(bisnis, 2.8, 1.0) * acak.normal(1, 0.07, jumlah)
    batal = jd["status"].to_numpy()[i] == "Batal"
    undian = acak.random(jumlah)

    # distribusi miring (Pareto): sebagian kecil penumpang membeli banyak tiket
    id_p = np.minimum((acak.pareto(1.2, jumlah) * jumlah_penumpang / 12).astype(int), jumlah_penumpang - 1)
    return pd.DataFrame({
        "no_tiket": [f"TK{n:09d}" for n in range(1, jumlah + 1)],
        "id_jadwal": jd["id_jadwal"].to_numpy()[i],
        "id_penumpang": [f"P{n + 1:07d}" for n in acak.permutation(jumlah_penumpang)[id_p]],
        "kelas": np.where(bisnis, "Bisnis", "Ekonomi"),
        "saluran": acak.choice(list(SALURAN), jumlah, p=list(SALURAN.values())),
        "tgl_beli": (tgl_terbang - hari_sebelum.astype("timedelta64[D]")).astype("datetime64[D]").astype(object),
        "hari_sebelum_terbang": hari_sebelum,
        "harga": (np.round(harga / 1_000) * 1_000).astype(np.int64),
        "bagasi_kg": acak.choice([0, 7, 15, 20, 30], jumlah, p=[0.18, 0.22, 0.30, 0.22, 0.08]),
        "status": np.select([batal, undian < 0.04, undian < 0.07], ["Refund", "Refund", "No-show"], "Terbang"),
    })


def buat_semua(tiket: int, jadwal: int, penumpang: int) -> dict[str, pd.DataFrame]:
    acak = np.random.default_rng(BENIH)
    penerbangan = buat_penerbangan(acak)
    tb_jadwal = buat_jadwal(acak, penerbangan, jadwal)
    tb_penumpang = buat_penumpang(acak, penumpang)
    return {
        "maskapai": buat_maskapai(),
        "bandara": buat_bandara(),
        "penerbangan": penerbangan,
        "jadwal": tb_jadwal,
        "penumpang": tb_penumpang,
        "tiket": buat_tiket(acak, tb_jadwal, penerbangan, penumpang, tiket),
    }


# ---------------------------------------------------------------------------------------------
# 3. Menulis berkas
# ---------------------------------------------------------------------------------------------
def _potong(nama: str, df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Tabel > 1 juta baris dipecah: tiket_1, tiket_2, ... (batas baris per lembar Excel)."""
    if len(df) <= MAKS_BARIS_LEMBAR:
        return [(nama, df)]
    bagian = range(0, len(df), MAKS_BARIS_LEMBAR)
    return [(f"{nama}_{k}", df.iloc[a:a + MAKS_BARIS_LEMBAR]) for k, a in enumerate(bagian, 1)]


def tulis_excel(data: dict[str, pd.DataFrame], keluar: Path) -> None:
    """Mode write-only openpyxl: hemat memori untuk jutaan baris."""
    from openpyxl import Workbook

    buku = Workbook(write_only=True)
    buku.properties.creator = buku.properties.lastModifiedBy = PENULIS_BERKAS
    buku.properties.title = "Data latihan Penerbangan (fiktif)"
    buku.properties.created = buku.properties.modified = dt.datetime(2026, 1, 1)
    for nama, df in data.items():
        for nama_lembar, bagian in _potong(nama, df):
            lembar = buku.create_sheet(nama_lembar)
            lembar.freeze_panes = "A2"
            lembar.append(list(bagian.columns))
            for baris in bagian.itertuples(index=False, name=None):
                lembar.append([v.item() if isinstance(v, np.generic) else v for v in baris])
    buku.save(keluar)


def tulis_csv(data: dict[str, pd.DataFrame], keluar: Path) -> None:
    """Satu folder berisi satu CSV per tabel (tanpa batas baris)."""
    keluar.mkdir(parents=True, exist_ok=True)
    for nama, df in data.items():
        df.to_csv(keluar / f"{nama}.csv", index=False)


# ---------------------------------------------------------------------------------------------
# 4. Angka kunci (untuk kunci jawaban bahan ajar)
# ---------------------------------------------------------------------------------------------
def _id(teks: str) -> str:
    """Format angka gaya Indonesia: 1,234.5 -> 1.234,5"""
    return teks.replace(",", "X").replace(".", ",").replace("X", ".")


def ribu(x: float) -> str:
    return _id(f"{int(x):,}")


def rp(x: float) -> str:
    if x >= 1e12:
        return _id(f"Rp{x / 1e12:,.2f} triliun")
    return _id(f"Rp{x / 1e9:,.2f} miliar") if x >= 1e9 else _id(f"Rp{x / 1e6:,.1f} juta")


def persen(x: float) -> str:
    return _id(f"{x:.1%}")


def angka_kunci(data: dict[str, pd.DataFrame]) -> list[tuple[str, str]]:
    t, j, p = data["tiket"], data["jadwal"], data["penerbangan"]

    gabung = t.merge(j[["id_jadwal", "no_penerbangan", "tanggal"]], on="id_jadwal") \
              .merge(p[["no_penerbangan", "kd_maskapai", "asal", "tujuan"]], on="no_penerbangan")
    laku = gabung[gabung["status"] != "Refund"]
    tahun = pd.to_datetime(laku["tanggal"]).dt.year
    per_tahun = laku.groupby(tahun)["harga"].sum()
    per_maskapai = laku.groupby("kd_maskapai")["harga"].sum().sort_values()
    nm_maskapai = dict(zip(data["maskapai"]["kd_maskapai"], data["maskapai"]["nm_maskapai"]))
    rute = (laku["asal"] + " → " + laku["tujuan"]).value_counts()
    bulan = laku.groupby(pd.to_datetime(laku["tanggal"]).dt.to_period("M"))["harga"].sum()
    jd_rute = j.merge(p[["no_penerbangan", "asal", "tujuan", "kapasitas"]], on="no_penerbangan")
    kd_insiden, tgl_insiden = INSIDEN
    insiden = (jd_rute["asal"].eq(kd_insiden) | jd_rute["tujuan"].eq(kd_insiden)) \
        & jd_rute["tanggal"].astype(str).isin(tgl_insiden)
    isi = len(t) / jd_rute["kapasitas"].sum()
    berangkat = jd_rute["asal"].value_counts()
    return [
        ("Jumlah baris: maskapai / bandara / penerbangan", f"{len(data['maskapai'])} / {len(data['bandara'])} / {len(p)}"),
        ("Jumlah baris: jadwal / penumpang / tiket", f"{ribu(len(j))} / {ribu(len(data['penumpang']))} / {ribu(len(t))}"),
        ("Pendapatan (harga tiket berstatus Terbang + No-show)", rp(laku["harga"].sum())),
        ("Pendapatan per tahun " + " / ".join(map(str, per_tahun.index)), " / ".join(rp(v) for v in per_tahun)),
        ("Maskapai pendapatan terbesar", f"{nm_maskapai[per_maskapai.index[-1]]}, {rp(per_maskapai.iloc[-1])}"),
        ("Rute tiket terlaku", f"{rute.index[0]}, {ribu(int(rute.iloc[0]))} tiket"),
        ("Bandara keberangkatan tersibuk (jumlah jadwal)", f"{berangkat.index[0]}, {ribu(int(berangkat.iloc[0]))} jadwal"),
        ("Bulan pendapatan tertinggi", f"{bulan.idxmax()}, {rp(bulan.max())}"),
        ("Jadwal terlambat / batal", f"{persen((j['status'] == 'Terlambat').mean())} / {ribu(int((j['status'] == 'Batal').sum()))} jadwal"),
        ("Rata-rata keterlambatan (jadwal terlambat)", f"{j.loc[j['status'] == 'Terlambat', 'menit_terlambat'].mean():.0f} menit"),
        ("Jadwal batal karena insiden DPS 12–13 Nov 2024", f"{int(insiden.sum())} jadwal"),
        ("Tingkat isian kursi rata-rata", persen(isi)),
        ("Tiket Refund / No-show", f"{ribu(int((t['status'] == 'Refund').sum()))} / {ribu(int((t['status'] == 'No-show').sum()))}"),
        ("Jadwal yang benar-benar terbang", ribu(int((j["status"] != "Batal").sum()))),
    ]


def main() -> None:
    p = argparse.ArgumentParser(description="Buat data latihan Penerbangan (fiktif) ke Excel/CSV.")
    p.add_argument("--ukuran", choices=UKURAN, default="sedang", help="preset jumlah baris (bawaan: sedang)")
    p.add_argument("--tiket", type=int, help="jumlah tiket sendiri, mis. 3000000 (menimpa --ukuran)")
    p.add_argument("--format", choices=["xlsx", "csv"], default="xlsx")
    p.add_argument("--keluar", type=Path, help="nama berkas .xlsx atau folder CSV")
    a = p.parse_args()

    tiket, jadwal, penumpang = UKURAN[a.ukuran]
    if a.tiket:
        tiket, jadwal, penumpang = a.tiket, math.ceil(a.tiket / 140), max(a.tiket // 4, 100)
    keluar = a.keluar or Path(f"contoh-penerbangan-{a.ukuran if not a.tiket else tiket}" + (".xlsx" if a.format == "xlsx" else ""))

    mulai = time.time()
    data = buat_semua(tiket, jadwal, penumpang)
    print(f"Data dibuat dalam {time.time() - mulai:.0f} detik. Menulis {keluar} ...", flush=True)
    (tulis_excel if a.format == "xlsx" else tulis_csv)(data, keluar)
    print(f"Selesai dalam {time.time() - mulai:.0f} detik.\n\n| Pertanyaan | Jawaban |\n|---|---|")
    for tanya, jawab in angka_kunci(data):
        print(f"| {tanya} | {jawab} |")


if __name__ == "__main__":
    main()
