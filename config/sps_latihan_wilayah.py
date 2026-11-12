"""Data latihan FIKTIF berskala besar: penjualan HARIAN per outlet (hierarki wilayah, kalender, produk).

Untuk latihan hierarki (telusur bertingkat), analitik prediktif (ramalan, tren, rata-rata bergerak, anomali),
peta, dan uji kecepatan pada jutaan baris. Dimuat otomatis oleh installer (scripts\\data-latihan.ps1 ->
sps_latihan.siapkan) ke ALDx Engine.

    latihan_outlet            138 outlet rekaan: kd_outlet, nm_outlet, pulau, provinsi (kode ISO), nama_provinsi,
                              kab_kota, kecamatan, kelurahan, lat, lon, tipe_gerai, tanggal_buka
    latihan_penjualan_harian  2021-01-01 s.d. 2025-12-31 x outlet x 10 subkategori (±2,3 juta baris; x SKALA)

Hierarki bawaan (Studio > panel Hierarki):
    Wilayah   pulau > nama_provinsi > kab_kota > kecamatan > kelurahan > nm_outlet
    Kalender  tahun > kuartal > bulan > tanggal
    Produk    kategori > subkategori

Pola yang sengaja ditanam (kunci jawaban bahan ajar):
    tren naik ±11%/tahun; pola mingguan (Sabtu tertinggi); musiman tahunan; 14 hari sebelum Lebaran x1,9 dan
    libur Lebaran x0,55 (tanggal Idulfitri asli 2021-2025); 15-31 Desember x1,35; 11.11 & 12.12 promo;
    gajian (tgl 25-2) x1,08; 2021 semester 1 x0,8 dan PPKM Juli-Agustus 2021 x0,55; sebagian outlet buka belakangan.
    Anomali: banjir Jakarta Timur 27 Jan-2 Feb 2025 (x0,15), gangguan sistem Sulawesi Selatan 5 Okt 2023 (x0,1),
    promo 17 Agustus 2024 satu outlet Badung (x6).

Nama provinsi & kab/kota & kecamatan asli; kelurahan, outlet, dan semua angka REKAAN (benih tetap: hasil selalu sama).
Tabel fakta dibangkitkan langsung di ClickHouse (INSERT ... SELECT dari numbers()), jadi jutaan baris tanpa
membebani RAM. SKALA (env SPS_LATIHAN_SKALA, 1-10) = jumlah outlet per kelurahan -> baris x SKALA.
"""

from __future__ import annotations

import hashlib
import os

import pandas as pd

AWAL, HARI = "2021-01-01", 1826                       # s.d. 2025-12-31
TABEL_OUTLET, TABEL_FAKTA = "latihan_outlet", "latihan_penjualan_harian"
LEBARAN = ("2021-05-13", "2022-05-02", "2023-04-22", "2024-04-10", "2025-03-31")   # Idulfitri

# provinsi ISO, nama provinsi, pulau, kab/kota, lat, lon, skala pasar, kecamatan (nama asli)
WILAYAH = [
    ("ID-JK", "DKI Jakarta", "Jawa", "Jakarta Selatan", -6.26, 106.81, 3.6, ["Kebayoran Baru", "Tebet", "Setiabudi", "Cilandak"]),
    ("ID-JK", "DKI Jakarta", "Jawa", "Jakarta Barat", -6.17, 106.76, 3.2, ["Grogol Petamburan", "Kebon Jeruk", "Cengkareng"]),
    ("ID-JK", "DKI Jakarta", "Jawa", "Jakarta Timur", -6.23, 106.90, 3.0, ["Cakung", "Duren Sawit", "Jatinegara"]),
    ("ID-JB", "Jawa Barat", "Jawa", "Kota Bandung", -6.91, 107.61, 2.8, ["Coblong", "Sukajadi", "Lengkong"]),
    ("ID-JB", "Jawa Barat", "Jawa", "Kota Bekasi", -6.24, 106.99, 2.4, ["Bekasi Barat", "Bekasi Selatan"]),
    ("ID-JB", "Jawa Barat", "Jawa", "Kabupaten Bogor", -6.48, 106.83, 2.0, ["Cibinong", "Ciawi"]),
    ("ID-BT", "Banten", "Jawa", "Kota Tangerang", -6.18, 106.63, 2.3, ["Cipondoh", "Karawaci"]),
    ("ID-BT", "Banten", "Jawa", "Kota Tangerang Selatan", -6.29, 106.71, 2.5, ["Serpong", "Pondok Aren"]),
    ("ID-JT", "Jawa Tengah", "Jawa", "Kota Semarang", -6.99, 110.42, 2.3, ["Semarang Tengah", "Banyumanik", "Tembalang"]),
    ("ID-JT", "Jawa Tengah", "Jawa", "Kota Surakarta", -7.57, 110.82, 1.8, ["Laweyan", "Banjarsari"]),
    ("ID-JT", "Jawa Tengah", "Jawa", "Kabupaten Banyumas", -7.43, 109.24, 1.4, ["Purwokerto Utara", "Sokaraja"]),
    ("ID-YO", "DI Yogyakarta", "Jawa", "Kota Yogyakarta", -7.80, 110.37, 1.9, ["Gondokusuman", "Umbulharjo"]),
    ("ID-YO", "DI Yogyakarta", "Jawa", "Kabupaten Sleman", -7.72, 110.36, 1.7, ["Depok", "Mlati"]),
    ("ID-JI", "Jawa Timur", "Jawa", "Kota Surabaya", -7.26, 112.75, 3.0, ["Gubeng", "Tegalsari", "Wonokromo"]),
    ("ID-JI", "Jawa Timur", "Jawa", "Kota Malang", -7.98, 112.63, 2.0, ["Klojen", "Lowokwaru"]),
    ("ID-JI", "Jawa Timur", "Jawa", "Kabupaten Sidoarjo", -7.45, 112.72, 1.9, ["Sidoarjo", "Waru"]),
    ("ID-SU", "Sumatera Utara", "Sumatra", "Kota Medan", 3.59, 98.67, 2.6, ["Medan Baru", "Medan Petisah", "Medan Kota"]),
    ("ID-SU", "Sumatera Utara", "Sumatra", "Kabupaten Deli Serdang", 3.53, 98.87, 1.5, ["Lubuk Pakam", "Percut Sei Tuan"]),
    ("ID-SB", "Sumatera Barat", "Sumatra", "Kota Padang", -0.95, 100.35, 1.6, ["Padang Barat", "Kuranji"]),
    ("ID-SS", "Sumatera Selatan", "Sumatra", "Kota Palembang", -2.98, 104.76, 2.0, ["Ilir Barat I", "Ilir Timur I"]),
    ("ID-RI", "Riau", "Sumatra", "Kota Pekanbaru", 0.51, 101.45, 1.8, ["Sukajadi", "Tampan"]),
    ("ID-BA", "Bali", "Bali & Nusa Tenggara", "Kota Denpasar", -8.65, 115.22, 2.1, ["Denpasar Selatan", "Denpasar Barat"]),
    ("ID-BA", "Bali", "Bali & Nusa Tenggara", "Kabupaten Badung", -8.58, 115.18, 2.2, ["Kuta", "Kuta Utara"]),
    ("ID-KS", "Kalimantan Selatan", "Kalimantan", "Kota Banjarmasin", -3.32, 114.59, 1.5, ["Banjarmasin Tengah", "Banjarmasin Utara"]),
    ("ID-KI", "Kalimantan Timur", "Kalimantan", "Kota Balikpapan", -1.24, 116.85, 1.8, ["Balikpapan Kota", "Balikpapan Selatan"]),
    ("ID-KI", "Kalimantan Timur", "Kalimantan", "Kota Samarinda", -0.50, 117.15, 1.6, ["Samarinda Ulu", "Sungai Kunjang"]),
    ("ID-KB", "Kalimantan Barat", "Kalimantan", "Kota Pontianak", -0.03, 109.33, 1.4, ["Pontianak Kota", "Pontianak Selatan"]),
    ("ID-SN", "Sulawesi Selatan", "Sulawesi", "Kota Makassar", -5.15, 119.43, 2.2, ["Panakkukang", "Rappocini", "Tamalanrea"]),
    ("ID-SA", "Sulawesi Utara", "Sulawesi", "Kota Manado", 1.47, 124.84, 1.4, ["Wenang", "Malalayang"]),
    ("ID-PA", "Papua", "Papua & Maluku", "Kota Jayapura", -2.53, 140.72, 1.1, ["Jayapura Utara", "Abepura"]),
]
# kategori, subkategori, bobot penjualan, harga rata-rata (Rp), margin
PRODUK = [
    ("Elektronik", "Ponsel", 1.30, 3_500_000, 0.08), ("Elektronik", "Aksesori", 0.60, 150_000, 0.30),
    ("Makanan & Minuman", "Makanan Ringan", 0.90, 15_000, 0.22), ("Makanan & Minuman", "Minuman", 0.80, 12_000, 0.25),
    ("Fesyen", "Pakaian", 0.80, 180_000, 0.35), ("Fesyen", "Sepatu", 0.50, 450_000, 0.30),
    ("Rumah Tangga", "Perabot", 0.50, 650_000, 0.25), ("Rumah Tangga", "Kebersihan", 0.60, 35_000, 0.20),
    ("Kesehatan & Kecantikan", "Perawatan Kulit", 0.60, 95_000, 0.40),
    ("Kesehatan & Kecantikan", "Obat & Vitamin", 0.50, 60_000, 0.28),
]
HIERARKI = {"Wilayah": ["pulau", "nama_provinsi", "kab_kota", "kecamatan", "kelurahan", "nm_outlet"],
            "Kalender": ["tahun", "kuartal", "bulan", "tanggal"],
            "Produk": ["kategori", "subkategori"]}
_AWALAN = ["Suka", "Mekar", "Tirta", "Karang", "Sido", "Margo", "Taman", "Sinar", "Bumi", "Cempaka", "Kebon", "Puri"]
_AKHIRAN = ["maju", "sari", "jaya", "mulya", "rejo", "asri", "indah", "makmur", "harja", "raya", "agung", "baru"]
TIPE_GERAI = (("Mal", 1.20), ("Ruko", 0.90), ("Mandiri", 1.00))
BUKA_BELAKANGAN = ("2022-06-01", "2023-03-01", "2024-01-15")


def _angka(teks: str) -> int:
    """Bilangan tetap dari teks (md5): nama kelurahan & sifat outlet selalu sama di setiap pemasangan."""
    return int(hashlib.md5(teks.encode()).hexdigest()[:8], 16)


def skala() -> int:
    try:
        return max(1, min(int(os.environ.get("SPS_LATIHAN_SKALA") or 1), 10))
    except ValueError:
        return 1


def buat_outlet(per_kelurahan: int = 1) -> pd.DataFrame:
    baris, nomor = [], 0
    for iso, prov, pulau, kab, lat, lon, skala_pasar, kecamatan in WILAYAH:
        for kec in kecamatan:
            for j in range(2):                                          # 2 kelurahan rekaan per kecamatan
                h = _angka(f"{kab}/{kec}/{j}")
                kel = f"{_AWALAN[h % len(_AWALAN)]}{_AKHIRAN[(h // 7 + j) % len(_AKHIRAN)]}"
                for k in range(per_kelurahan):
                    nomor += 1
                    g = _angka(f"{kel}/{k}/{nomor}")
                    tipe, f_tipe = TIPE_GERAI[g % 3]
                    buka = BUKA_BELAKANGAN[g % 3] if nomor % 6 == 0 else AWAL
                    baris.append({
                        "kd_outlet": f"OT{nomor:04d}", "nm_outlet": f"Gerai {kel}{'' if per_kelurahan == 1 else f' {k + 1}'}",
                        "pulau": pulau, "provinsi": iso, "nama_provinsi": prov, "kab_kota": kab, "kecamatan": kec,
                        "kelurahan": kel, "lat": round(lat + ((g % 1000) / 1000 - 0.5) * 0.08, 5),
                        "lon": round(lon + (((g // 1000) % 1000) / 1000 - 0.5) * 0.08, 5), "tipe_gerai": tipe,
                        "tanggal_buka": buka, "skala": round(skala_pasar * f_tipe * (0.8 + (g % 400) / 1000), 3)})
    return pd.DataFrame(baris)


def _sql_produk() -> str:
    isi = ", ".join(f"('{k}', '{s}', {b}, {h}, {m})" for k, s, b, h, m in PRODUK)
    return f"SELECT * FROM VALUES('kategori String, subkategori String, bobot Float64, harga Float64, margin Float64', {isi})"


def sql_fakta(db: str, tabel: str) -> str:
    """CREATE TABLE ... AS SELECT: satu baris per tanggal x outlet x subkategori (sejak outlet buka)."""
    lebaran = ", ".join(f"toDate('{t}')" for t in LEBARAN)
    acak = lambda garam: f"(cityHash64(tanggal, kd_outlet, subkategori, '{garam}') % 100000) / 100000.0"  # noqa: E731
    return f"""
CREATE TABLE {db}.`{tabel}` ENGINE = MergeTree ORDER BY (provinsi, kab_kota, kd_outlet, tanggal) AS
SELECT
    tanggal, toUInt16(toYear(tanggal)) AS tahun,
    CAST(concat(toString(toYear(tanggal)), '-Q', toString(toQuarter(tanggal))) AS LowCardinality(String)) AS kuartal,
    CAST(formatDateTime(tanggal, '%Y-%m') AS LowCardinality(String)) AS bulan,
    CAST(['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'][toDayOfWeek(tanggal)] AS LowCardinality(String)) AS hari,
    CAST(pulau AS LowCardinality(String)) AS pulau, CAST(provinsi AS LowCardinality(String)) AS provinsi,
    CAST(nama_provinsi AS LowCardinality(String)) AS nama_provinsi, CAST(kab_kota AS LowCardinality(String)) AS kab_kota,
    CAST(kecamatan AS LowCardinality(String)) AS kecamatan, CAST(kelurahan AS LowCardinality(String)) AS kelurahan,
    CAST(kd_outlet AS LowCardinality(String)) AS kd_outlet, CAST(nm_outlet AS LowCardinality(String)) AS nm_outlet,
    CAST(tipe_gerai AS LowCardinality(String)) AS tipe_gerai, lat, lon,
    CAST(kategori AS LowCardinality(String)) AS kategori, CAST(subkategori AS LowCardinality(String)) AS subkategori,
    toUInt32(round(harapan / harga * (0.8 + 0.4 * u1))) AS unit,
    round(unit * harga * (0.93 + 0.14 * u2)) AS penjualan,
    toUInt32(if(unit = 0, 0, greatest(1, round(unit / (1.1 + 0.8 * u3))))) AS transaksi,
    toUInt32(round(transaksi * (2 + 2 * u4)) + 3) AS pengunjung,
    round(penjualan * margin * (0.85 + 0.3 * u4)) AS laba,
    round(skala * bobot * 4000000 * (1 + 0.13 * hari_ke / 365) * mingguan * tahunan) AS target,
    toUInt8(f_lebaran > 1 OR f_akhir_tahun > 1 OR f_promo > 1) AS promo
FROM (
    SELECT o.*, p.*, toDate('{AWAL}') + toUInt32(d.number) AS tanggal,
        dateDiff('day', toDate('{AWAL}'), tanggal) AS hari_ke,
        [0.88, 0.90, 0.93, 0.97, 1.08, 1.25, 1.18][toDayOfWeek(tanggal)] AS mingguan,
        1 + 0.08 * sin(2 * pi() * (toDayOfYear(tanggal) - 80) / 365) AS tahunan,
        arrayMap(l -> dateDiff('day', tanggal, l), [{lebaran}]) AS ke_lebaran,
        multiIf(arrayExists(x -> x BETWEEN 1 AND 14, ke_lebaran), 1.9,
                arrayExists(x -> x BETWEEN -2 AND 0, ke_lebaran), 0.55, 1.0) AS f_lebaran,
        if(toMonth(tanggal) = 12 AND toDayOfMonth(tanggal) >= 15, 1.35, 1.0) AS f_akhir_tahun,
        if((toMonth(tanggal) = 11 AND toDayOfMonth(tanggal) = 11) OR (toMonth(tanggal) = 12 AND toDayOfMonth(tanggal) = 12),
           if(kategori = 'Elektronik', 1.8, 1.25), 1.0) AS f_promo,
        if(toDayOfMonth(tanggal) >= 25 OR toDayOfMonth(tanggal) <= 2, 1.08, 1.0) AS f_gajian,
        multiIf(tanggal BETWEEN '2021-07-03' AND '2021-08-31', 0.55, tanggal < '2021-07-01', 0.8, 1.0) AS f_pandemi,
        multiIf(kab_kota = 'Jakarta Timur' AND tanggal BETWEEN '2025-01-27' AND '2025-02-02', 0.15,
                provinsi = 'ID-SN' AND tanggal = '2023-10-05', 0.1,
                kd_outlet = (SELECT min(kd_outlet) FROM {db}.`{TABEL_OUTLET}` WHERE kab_kota = 'Kabupaten Badung')
                    AND tanggal = '2024-08-17', 6.0, 1.0) AS f_kejadian,
        skala * bobot * 4000000 * (1 + 0.11 * hari_ke / 365) * mingguan * tahunan
            * f_lebaran * f_akhir_tahun * f_promo * f_gajian * f_pandemi * f_kejadian AS harapan,
        {acak('a')} AS u1, {acak('b')} AS u2, {acak('c')} AS u3, {acak('d')} AS u4
    FROM {db}.`{TABEL_OUTLET}` AS o
    CROSS JOIN (SELECT number FROM numbers({HARI})) AS d
    CROSS JOIN ({_sql_produk()}) AS p
    WHERE tanggal >= toDate(o.tanggal_buka)
)"""


def tulis_engine() -> dict[str, int]:
    """Tulis kedua tabel ke ALDx Engine (tabel fakta ditukar atomik). Kembalikan jumlah baris."""
    from sps_engine import klien as K, tabel as T
    k, db = K.klien(), K.nama_db()
    k.perintah(f"CREATE DATABASE IF NOT EXISTS {db}")
    outlet = buat_outlet(skala())
    T.isi_penuh(k, db, TABEL_OUTLET, [outlet], ["kd_outlet"])
    baru = f"{TABEL_FAKTA}__baru"
    k.perintah(f"DROP TABLE IF EXISTS {db}.`{baru}`")
    try:
        k.perintah(sql_fakta(db, baru))
    except Exception:
        k.perintah(f"DROP TABLE IF EXISTS {db}.`{baru}`")
        raise
    if T.ada(k, db, TABEL_FAKTA):
        k.perintah(f"EXCHANGE TABLES {db}.`{TABEL_FAKTA}` AND {db}.`{baru}`")
        k.perintah(f"DROP TABLE {db}.`{baru}`")
    else:
        k.perintah(f"RENAME TABLE {db}.`{baru}` TO {db}.`{TABEL_FAKTA}`")
    jumlah = int(k.kueri_df(f"SELECT count() AS n FROM {db}.`{TABEL_FAKTA}`")["n"].iloc[0])
    return {TABEL_OUTLET: len(outlet), TABEL_FAKTA: jumlah}


METRIK = (("total_penjualan", "SUM(penjualan)", "Total penjualan", "SMART_NUMBER"),
          ("total_laba", "SUM(laba)", "Total laba", "SMART_NUMBER"),
          ("margin_persen", "SUM(laba) / NULLIF(SUM(penjualan), 0)", "Margin %", ".1%"),
          ("capaian_target", "SUM(penjualan) / NULLIF(SUM(target), 0)", "Capaian target %", ".1%"))


def lengkapi_dataset(t) -> None:
    """Kolom waktu, metrik siap pakai, dan hierarki bawaan untuk dataset fakta."""
    from superset import db
    from superset.connectors.sqla.models import SqlMetric
    from sps_studio import hierarki
    for c in t.columns:
        if c.column_name == "tanggal":
            c.is_dttm = True
    ada = {m.metric_name for m in t.metrics}
    for nama, ekspresi, label, fmt in METRIK:
        if nama not in ada:
            t.metrics.append(SqlMetric(metric_name=nama, expression=ekspresi, verbose_name=label, d3format=fmt))
    db.session.commit()
    for nama, kolom in HIERARKI.items():
        hierarki.pasang_bawaan(t.id, nama, kolom)


JUDUL_DASHBOARD, SLUG = "Latihan: Wilayah & Prediksi (fiktif)", "latihan-wilayah"


def lembar_dashboard(ih: int) -> list[tuple[str, int, dict]]:
    D = lambda f: {"field": f, "peran": "dimensi"}                       # noqa: E731
    U = lambda f, agg="SUM": {"field": f, "peran": "ukuran", "agg": agg}  # noqa: E731
    M = lambda f: {"field": f, "peran": "ukuran", "metrik": True}        # noqa: E731
    return [
        ("Total penjualan", 4, {"dataset_id": ih, "tanda": "angka", "baris": [M("total_penjualan")]}),
        ("Capaian target", 4, {"dataset_id": ih, "tanda": "angka", "baris": [M("capaian_target")]}),
        ("Margin", 4, {"dataset_id": ih, "tanda": "angka", "baris": [M("margin_persen")]}),
        ("Penjualan per bulan & ramalan", 12, {"dataset_id": ih, "tanda": "garis", "kolom": [D("bulan")],
                                               "baris": [U("penjualan")],
                                               "analitik": {"ramalan": 6, "tren": True, "rata_bergerak": 3}}),
        ("Penjualan per provinsi", 6, {"dataset_id": ih, "tanda": "peta_wilayah", "kolom": [D("provinsi")],
                                       "baris": [U("penjualan")]}),
        ("Kategori & subkategori", 6, {"dataset_id": ih, "tanda": "treemap",
                                       "kolom": [D("kategori"), D("subkategori")], "baris": [U("penjualan")]}),
        ("10 kab/kota teratas", 12, {"dataset_id": ih, "tanda": "batang", "baris": [D("kab_kota")],
                                     "kolom": [U("penjualan")], "urut": "turun", "batas": 10}),
    ]


def buat_dashboard(ih: int, pemilik: str = "admin") -> str:
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.utils.core import override_user
    from sps_studio import dasbor, lembar

    with override_user(sm.find_user(username=pemilik)):
        baris, sekarang = [], []
        for judul, lebar, spec in lembar_dashboard(ih):
            judul = f"Latihan Wilayah - {judul}"
            lama = db.session.query(Slice).filter_by(slice_name=judul).first()
            t, lb = lembar.dari_dict({**spec, "judul": judul})
            hasil = lembar.simpan(t, lb, lama.id if lama else None)
            sekarang.append({"chart_id": hasil["id"], "lebar": lebar})
            if sum(x["lebar"] for x in sekarang) >= 12:
                baris.append(sekarang)
                sekarang = []
        if sekarang:
            baris.append(sekarang)
        lama = db.session.query(Dashboard).filter_by(slug=SLUG).first()
        hasil = dasbor.simpan({
            "judul": JUDUL_DASHBOARD, "baris": baris,
            "keterangan": "Data FIKTIF ±2,3 juta baris penjualan harian. Di Studio: hierarki Wilayah, Kalender, Produk.",
            "filter": [{"nama": "Provinsi", "dataset_id": ih, "kolom": "nama_provinsi", "jenis": "pilihan"},
                       {"nama": "Kategori", "dataset_id": ih, "kolom": "kategori", "jenis": "pilihan"}]},
            lama.id if lama else None)
        d = db.session.query(Dashboard).get(hasil["id"])
        d.published, d.slug, d.dashboard_title = True, SLUG, JUDUL_DASHBOARD
        db.session.commit()
    return f"dashboard '{JUDUL_DASHBOARD}' -> /superset/dashboard/{SLUG}/"
