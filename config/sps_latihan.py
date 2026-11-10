"""Data latihan FIKTIF untuk pelatihan, bahan ajar & pengujian (docs/tutorial, docs/pengujian).

Contoh netral: penjualan perusahaan ritel rekaan "PT Contoh Sejahtera". Membuat 3 dataset
di ALDx Engine (bisa dipakai siapa pun, tanpa data asli):

    latihan_penjualan          periode (bulan), kd_cabang, nm_cabang, provinsi, kategori, saluran,
                               jumlah_transaksi, total  -> pola musiman + tren + satu lonjakan
                                                           (untuk latihan ramalan & anomali)
    latihan_lokasi_pelanggan   id & nama pelanggan FIKTIF, lat, lon, provinsi, kd_cabang, saluran,
                               belanja                  -> latihan peta titik/kepadatan/provinsi
    latihan_cabang             kd_cabang, nm_cabang, kota, pulau, kepala_cabang (FIKTIF)
                                                        -> tabel induk untuk latihan gabung (Kueri Visual)

Juga membuat "Latihan: Dashboard Penjualan (fiktif)" (8 chart + 2 filter) untuk Level 1.

Angka dibuat dari bilangan acak dengan benih tetap: hasil selalu sama, jadi bahan ajar &
skenario uji bisa menyebut angka pasti. Semua role yang bisa login (Gamma ke atas) boleh membaca.

Jalankan:  scripts\\data-latihan.ps1   (atau  python sps_latihan.py  di dalam container superset)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

AWAL = "2023-01-01"
BULAN = 36
BENIH = 2026
CABANG = [  # kode, nama, provinsi (ISO), lintang, bujur, skala
    ("C01", "Cabang Jakarta", "ID-JK", -6.20, 106.82, 3.0),
    ("C02", "Cabang Bandung", "ID-JB", -6.91, 107.61, 1.6),
    ("C03", "Cabang Surabaya", "ID-JI", -7.25, 112.75, 1.8),
    ("C04", "Cabang Medan", "ID-SU", 3.59, 98.67, 0.9),
    ("C05", "Cabang Makassar", "ID-SN", -5.14, 119.42, 0.6),
    ("C06", "Cabang Balikpapan", "ID-KI", -1.24, 116.85, 0.8),
]
KATEGORI = {"Elektronik": 1.5, "Makanan & Minuman": 1.3, "Fesyen": 1.0, "Rumah Tangga": 0.7,
            "Kesehatan & Kecantikan": 0.4}
SALURAN = {"Online": 1.4, "Toko": 1.2, "Grosir": 0.9, "Reseller": 0.6}
LONJAKAN = ("C01", "2025-03", "Elektronik")        # untuk latihan anomali (nilai x4)


def buat_penjualan() -> pd.DataFrame:
    acak = np.random.default_rng(BENIH)
    periode = pd.date_range(AWAL, periods=BULAN, freq="MS")
    baris = []
    for kd, nm, prov, _, _, skala in CABANG:
        for i, p in enumerate(periode):
            musim = 1 + 0.18 * math.sin(2 * math.pi * (i - 2) / 12) + (0.25 if p.month == 12 else 0)
            tren = 1 + 0.012 * i
            for kategori, fk in KATEGORI.items():
                for saluran, fs in SALURAN.items():
                    nilai = 85e6 * skala * fk * fs * musim * tren * acak.normal(1, 0.06)
                    if (kd, p.strftime("%Y-%m"), kategori) == LONJAKAN:
                        nilai *= 4
                    baris.append({"periode": p.date(), "kd_cabang": kd, "nm_cabang": nm, "provinsi": prov,
                                  "kategori": kategori, "saluran": saluran,
                                  "jumlah_transaksi": int(120 * skala * fs * acak.uniform(0.8, 1.2)),
                                  "total": round(nilai, 2)})
    return pd.DataFrame(baris)


def buat_lokasi() -> pd.DataFrame:
    acak = np.random.default_rng(BENIH + 1)
    baris = []
    for n in range(1500):
        kd, _, prov, lat, lon, skala = CABANG[acak.choice(len(CABANG), p=_bobot())]
        baris.append({"id_pelanggan": f"PLG-{n + 1:05d}", "nama_pelanggan": f"Pelanggan Contoh {n + 1:04d}",
                      "lat": round(lat + acak.normal(0, 0.35), 5), "lon": round(lon + acak.normal(0, 0.35), 5),
                      "provinsi": prov, "kd_cabang": kd, "saluran": list(SALURAN)[acak.integers(len(SALURAN))],
                      "belanja": round(float(acak.lognormal(16, 1.1)), 2)})
    return pd.DataFrame(baris)


PULAU = {"C01": "Jawa", "C02": "Jawa", "C03": "Jawa", "C04": "Sumatra", "C05": "Sulawesi", "C06": "Kalimantan"}
KEPALA = {"C01": "Andi Contoh", "C02": "Budi Contoh", "C03": "Citra Contoh", "C04": "Dewi Contoh",
          "C05": "Eko Contoh", "C06": "Fajar Contoh"}


def buat_cabang() -> pd.DataFrame:
    """Tabel induk cabang (kunci kd_cabang) untuk latihan gabung tabel."""
    return pd.DataFrame([{"kd_cabang": kd, "nm_cabang": nm, "kota": nm.replace("Cabang ", ""), "provinsi": prov,
                          "pulau": PULAU[kd], "kepala_cabang": KEPALA[kd]} for kd, nm, prov, *_ in CABANG])


def _bobot() -> list[float]:
    s = [k[5] for k in CABANG]
    return [x / sum(s) for x in s]


# --- Tulis & daftarkan -------------------------------------------------------------------------
def _tulis_engine(nama: str, df: pd.DataFrame, urut: list[str]) -> None:
    from sps_engine import klien as K, tabel as T
    k, db = K.klien(), K.nama_db()
    k.perintah(f"CREATE DATABASE IF NOT EXISTS {db}")
    T.isi_penuh(k, db, nama, [df], urut)


def _daftarkan(nama: str, database, schema: str | None, deskripsi: str):
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable, SqlMetric

    t = db.session.query(SqlaTable).filter_by(table_name=nama, database_id=database.id).one_or_none()
    if t is None:
        t = SqlaTable(table_name=nama, database=database, schema=schema)
        db.session.add(t)
    t.description = deskripsi
    db.session.flush()
    t.fetch_metadata()
    for c in t.columns:
        if c.column_name == "periode":
            c.is_dttm = True
    if "total" in {c.column_name for c in t.columns} and not t.metrics:
        t.metrics.append(SqlMetric(metric_name="penjualan", expression="SUM(total)", verbose_name="Penjualan",
                                   d3format="SMART_NUMBER"))
    pv = sm.add_permission_view_menu("datasource_access", t.get_perm())
    for role in ("Gamma", "Alpha"):
        r = sm.find_role(role)
        if r and pv not in r.permissions:
            sm.add_permission_role(r, pv)
    db.session.commit()
    return t


JUDUL_DASHBOARD = "Latihan: Dashboard Penjualan (fiktif)"
SLUG = "latihan"


def _lembar_latihan(ip: int, il: int) -> list[tuple[str, int, dict]]:
    """(judul, lebar, spesifikasi lembar Studio) chart dashboard latihan."""
    D = lambda f: {"field": f, "peran": "dimensi"}                       # noqa: E731
    U = lambda f, agg="SUM": {"field": f, "peran": "ukuran", "agg": agg}  # noqa: E731
    return [
        ("Total penjualan", 4, {"dataset_id": ip, "tanda": "angka", "baris": [U("total")]}),
        ("Jumlah transaksi", 4, {"dataset_id": ip, "tanda": "angka", "baris": [U("jumlah_transaksi")]}),
        ("Komposisi kategori", 4, {"dataset_id": ip, "tanda": "pie", "kolom": [D("kategori")], "baris": [U("total")]}),
        ("Penjualan per bulan", 8, {"dataset_id": ip, "tanda": "garis", "kolom": [D("periode")], "baris": [U("total")]}),
        ("Kategori & saluran", 4, {"dataset_id": ip, "tanda": "treemap",
                                   "kolom": [D("kategori"), D("saluran")], "baris": [U("total")]}),
        ("Penjualan per cabang", 6, {"dataset_id": ip, "tanda": "batang", "baris": [D("nm_cabang")],
                                     "kolom": [U("total")], "warna": D("kategori"), "urut": "turun"}),
        ("Belanja per provinsi", 6, {"dataset_id": il, "tanda": "peta_wilayah", "kolom": [D("provinsi")],
                                     "baris": [U("belanja")]}),
        ("Sebaran lokasi pelanggan", 12, {"dataset_id": il, "tanda": "peta_titik", "kolom": [D("lon")],
                                          "baris": [D("lat")], "warna": D("saluran")}),
    ]


def buat_dashboard(ip: int, il: int, pemilik: str = "admin") -> str:
    """Chart & dashboard latihan (diperbarui bila sudah ada). Dijalankan sebagai admin."""
    from superset import db, security_manager as sm
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from superset.utils.core import override_user
    from sps_studio import dasbor, lembar

    with override_user(sm.find_user(username=pemilik)):
        baris, sekarang = [], []
        for judul, lebar, spec in _lembar_latihan(ip, il):
            judul = f"Latihan - {judul}"
            lama = db.session.query(Slice).filter_by(slice_name=judul).first()
            t, lb = lembar.dari_dict({**spec, "judul": judul})
            hasil = lembar.simpan(t, lb, lama.id if lama else None)
            sekarang.append({"chart_id": hasil["id"], "lebar": lebar})
            if sum(x["lebar"] for x in sekarang) >= 12:
                baris.append(sekarang)
                sekarang = []
        if sekarang:
            baris.append(sekarang)
        lama = (db.session.query(Dashboard).filter_by(slug=SLUG).first()
                or db.session.query(Dashboard).filter_by(dashboard_title=JUDUL_DASHBOARD).first())
        hasil = dasbor.simpan({"judul": JUDUL_DASHBOARD, "baris": baris,
                               "keterangan": "Data FIKTIF untuk pelatihan. Coba filter Cabang & Kategori di kiri.",
                               "filter": [{"nama": "Cabang", "dataset_id": ip, "kolom": "nm_cabang", "jenis": "pilihan"},
                                          {"nama": "Kategori", "dataset_id": ip, "kolom": "kategori",
                                           "jenis": "pilihan"}]},
                              lama.id if lama else None)
        d = db.session.query(Dashboard).get(hasil["id"])
        d.published, d.slug, d.dashboard_title = True, SLUG, JUDUL_DASHBOARD
        db.session.commit()
    return f"dashboard '{JUDUL_DASHBOARD}' -> /superset/dashboard/{SLUG}/"


# Data latihan versi lama (tema pajak). Dihapus otomatis saat data latihan baru dimuat.
LAMA = ("latihan_penerimaan", "latihan_lokasi_wp")


def _hapus_versi_lama() -> list[str]:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.slice import Slice

    hasil = []
    for t in db.session.query(SqlaTable).filter(SqlaTable.table_name.in_(LAMA)).all():
        chart = db.session.query(Slice).filter_by(datasource_type="table", datasource_id=t.id).all()
        for c in chart:
            db.session.delete(c)
        db.session.delete(t)
        hasil.append(f"versi lama dihapus: {t.table_name} (+{len(chart)} chart)")
    db.session.commit()
    try:
        from sps_engine import klien as K
        for nama in LAMA:
            K.klien().perintah(f"DROP TABLE IF EXISTS {K.nama_db()}.{nama}")
    except Exception:  # noqa: BLE001 - engine mati / mode uji: tabel lama dibiarkan
        pass
    return hasil


def siapkan(database=None) -> list[str]:
    """Muat data latihan. database=None -> ALDx Engine; lainnya (uji) -> tulis lewat pandas.to_sql."""
    data = {"latihan_penjualan": (buat_penjualan(), ["kd_cabang", "periode"],
                                  "DATA FIKTIF untuk pelatihan: penjualan bulanan per cabang, kategori, saluran."),
            "latihan_lokasi_pelanggan": (buat_lokasi(), ["kd_cabang"],
                                         "DATA FIKTIF untuk pelatihan peta: lokasi & belanja pelanggan rekaan."),
            "latihan_cabang": (buat_cabang(), ["kd_cabang"],
                               "DATA FIKTIF: daftar cabang (tabel induk untuk latihan gabung di Kueri Visual).")}
    hasil = _hapus_versi_lama()
    if database is None:
        from sps_engine.ekstrak import database_engine
        from sps_engine import klien as K
        database, schema = database_engine(), K.nama_db()
        for nama, (df, urut, _) in data.items():
            _tulis_engine(nama, df, urut)
    else:
        schema = None
        with database.get_sqla_engine() as eng:
            for nama, (df, _, _) in data.items():
                df.to_sql(nama, eng, if_exists="replace", index=False)
    ids = {}
    for nama, (df, _, ket) in data.items():
        t = _daftarkan(nama, database, schema, ket)
        ids[nama] = t.id
        hasil.append(f"{nama}: {len(df):,} baris (dataset {t.id})".replace(",", "."))
    import os
    hasil.append(buat_dashboard(ids["latihan_penjualan"], ids["latihan_lokasi_pelanggan"],
                                os.environ.get("ADMIN_USERNAME", "admin")))
    return hasil


if __name__ == "__main__":
    from superset.app import create_app
    with create_app().app_context():
        for h in siapkan():
            print("OK ", h)
