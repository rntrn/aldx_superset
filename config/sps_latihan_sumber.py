"""Database SUMBER contoh + role RLS contoh, agar semua latihan di bahan ajar bisa dicoba di instalasi baru.

Tanpa ini, latihan Hubungkan data, Ekstrak (penuh/inkremental), Impor banyak tabel, pilih skema, dan uji RLS
butuh database kantor sungguhan. Dimuat scripts\\data-latihan.ps1 (sps_latihan.siapkan), jadi ikut installer.

1. Database PostgreSQL `aldx_contoh` di server metadb (terpisah dari metadata ALDx), dibuat dengan generate_series:
       toko.cabang (6)   toko.produk (500)   toko.pelanggan (20.000)   toko.transaksi (200.000, 2023-2025)
       toko.retur (5.000)   toko.stok (3.000)   sdm.pegawai (300)   sdm.absensi (60.000)
   Kode cabang & kategori sama dengan latihan_penjualan, sehingga filter global & drill-through ikut cocok.
2. Koneksi Superset "Contoh sumber (PostgreSQL)" memakai akun HANYA-BACA `aldx_contoh_baca`
   (sandi acak, dibuat ulang tiap kali dimuat; tidak punya hak apa pun atas database metadata).
3. Dataset `contoh_transaksi` & `contoh_pelanggan` (siap dipilih di Ekstrak; Gamma/Alpha boleh membaca).
4. Role "Latihan Cabang Bandung" & "Latihan Cabang Jakarta" + aturan RLS kd_cabang pada dataset latihan.
   Akun uji TIDAK dibuat otomatis (akun bersandi bawaan = lubang keamanan). Buat bila perlu:
       scripts\\data-latihan.ps1 -AkunUji      -> latihan.bandung & latihan.jakarta, sandi acak dicetak sekali.
5. tambah_transaksi(n): baris baru bertanggal hari ini untuk latihan ekstrak INKREMENTAL
       scripts\\data-latihan.ps1 -TambahTransaksi 500

Semua data REKAAN. Dihapus bersama volume metadb (hapus total); bisa dibuat ulang kapan saja.
"""

from __future__ import annotations

import contextlib
import logging
import os
import secrets

log = logging.getLogger(__name__)

NAMA_DB, AKUN_BACA = "aldx_contoh", "aldx_contoh_baca"
NAMA_KONEKSI = "Contoh sumber (PostgreSQL)"
DATASET = {"contoh_transaksi": ("toko", "transaksi"), "contoh_pelanggan": ("toko", "pelanggan")}
ROLE_CABANG = {"Latihan Cabang Bandung": "C02", "Latihan Cabang Jakarta": "C01"}
DATASET_RLS = ("latihan_penjualan", "latihan_lokasi_pelanggan", "latihan_cabang")
AKUN_UJI = {"latihan.bandung": "Latihan Cabang Bandung", "latihan.jakarta": "Latihan Cabang Jakarta"}

CABANG = [("C01", "Cabang Jakarta", "ID-JK"), ("C02", "Cabang Bandung", "ID-JB"), ("C03", "Cabang Surabaya", "ID-JI"),
          ("C04", "Cabang Medan", "ID-SU"), ("C05", "Cabang Makassar", "ID-SN"), ("C06", "Cabang Balikpapan", "ID-KI")]
KATEGORI = ["Elektronik", "Makanan & Minuman", "Fesyen", "Rumah Tangga", "Kesehatan & Kecantikan"]

SQL_ISI = f"""
SELECT setseed(0.2026);
DROP SCHEMA IF EXISTS toko CASCADE; DROP SCHEMA IF EXISTS sdm CASCADE;
CREATE SCHEMA toko; CREATE SCHEMA sdm;
CREATE TABLE toko.cabang (kd_cabang text PRIMARY KEY, nm_cabang text, provinsi text);
INSERT INTO toko.cabang VALUES {", ".join(f"('{k}', '{n}', '{p}')" for k, n, p in CABANG)};
CREATE TABLE toko.produk AS
  SELECT g AS id_produk, 'Produk ' || lpad(g::text, 3, '0') AS nm_produk,
         (ARRAY[{", ".join(f"'{k}'" for k in KATEGORI)}])[1 + g % 5] AS kategori,
         (5000 + floor(random() * 995) * 1000)::bigint AS harga
  FROM generate_series(1, 500) g;
CREATE TABLE toko.pelanggan AS
  SELECT g AS id_pelanggan, 'Pelanggan ' || g AS nm_pelanggan, 'C0' || (1 + g % 6) AS kd_cabang,
         (ARRAY['Reguler', 'Silver', 'Gold'])[1 + (g % 10) / 4] AS keanggotaan,
         date '2020-01-01' + (g % 1800) AS tgl_daftar
  FROM generate_series(1, 20000) g;
CREATE TABLE toko.transaksi AS
  SELECT g AS id_transaksi, date '2023-01-01' + ((g * 1096) / 200000) AS tanggal,
         'C0' || (1 + floor(random() * 6)::int) AS kd_cabang, 1 + floor(random() * 20000)::int AS id_pelanggan,
         1 + floor(random() * 500)::int AS id_produk, 1 + floor(random() * 5)::int AS jumlah,
         (ARRAY['Online', 'Toko', 'Grosir', 'Reseller'])[1 + floor(random() * 4)::int] AS saluran
  FROM generate_series(1, 200000) g;
ALTER TABLE toko.transaksi ADD COLUMN total bigint;
UPDATE toko.transaksi t SET total = t.jumlah * p.harga FROM toko.produk p WHERE p.id_produk = t.id_produk;
ALTER TABLE toko.transaksi ADD PRIMARY KEY (id_transaksi);
CREATE TABLE toko.retur AS
  SELECT g AS id_retur, 1 + floor(random() * 200000)::int AS id_transaksi,
         (ARRAY['Rusak', 'Salah kirim', 'Berubah pikiran'])[1 + g % 3] AS alasan,
         date '2023-01-10' + (g % 1080) AS tgl_retur
  FROM generate_series(1, 5000) g;
CREATE TABLE toko.stok AS
  SELECT c.kd_cabang, p.id_produk, floor(random() * 200)::int AS stok
  FROM toko.cabang c CROSS JOIN toko.produk p;
CREATE TABLE sdm.pegawai AS
  SELECT g AS id_pegawai, 'Pegawai ' || g AS nm_pegawai, 'C0' || (1 + g % 6) AS kd_cabang,
         (ARRAY['Kasir', 'Gudang', 'Penjualan', 'Admin'])[1 + g % 4] AS jabatan,
         date '2015-01-01' + (g * 11) AS tgl_masuk
  FROM generate_series(1, 300) g;
CREATE TABLE sdm.absensi AS
  SELECT row_number() OVER () AS id_absensi, p.id_pegawai, date '2025-06-01' + d AS tanggal,
         (ARRAY['Hadir', 'Hadir', 'Hadir', 'Hadir', 'Izin', 'Sakit'])[1 + floor(random() * 6)::int] AS status
  FROM sdm.pegawai p CROSS JOIN generate_series(0, 199) d;
ANALYZE;
GRANT USAGE ON SCHEMA toko, sdm TO {AKUN_BACA};
GRANT SELECT ON ALL TABLES IN SCHEMA toko, sdm TO {AKUN_BACA};
"""


def _metadb() -> dict | None:
    """Alamat server metadb. None bila metadata bukan PostgreSQL bawaan (instalasi lama) -> dilewati."""
    if (os.environ.get("METADB_JENIS") or "postgresql").lower() not in ("postgresql", "postgres"):
        return None
    if not os.environ.get("METADB_PASSWORD"):
        return None
    return {"host": os.environ.get("METADB_HOST", "metadb"), "port": int(os.environ.get("METADB_PORT", "5432")),
            "user": os.environ.get("METADB_USER", "superset"), "password": os.environ["METADB_PASSWORD"]}


@contextlib.contextmanager
def _sambung(m: dict, database: str):
    import psycopg2
    c = psycopg2.connect(dbname=database, connect_timeout=10, **m)
    c.autocommit = True                       # CREATE DATABASE tidak boleh di dalam transaksi
    try:
        yield c
    finally:
        c.close()


def buat_database() -> tuple[dict, str]:
    """(Ulang) isi database contoh & akun hanya-baca. Kembalikan (alamat, sandi akun baca)."""
    m = _metadb()
    if m is None:
        raise RuntimeError("metadata bukan PostgreSQL bawaan")
    sandi = secrets.token_urlsafe(24)
    with _sambung(m, "postgres") as c, c.cursor() as k:
        k.execute("SELECT 1 FROM pg_database WHERE datname = %s", (NAMA_DB,))
        if not k.fetchone():
            k.execute(f"CREATE DATABASE {NAMA_DB}")
        k.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (AKUN_BACA,))
        perintah = "ALTER" if k.fetchone() else "CREATE"
        k.execute(f"{perintah} ROLE {AKUN_BACA} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %s", (sandi,))
    with _sambung(m, NAMA_DB) as c, c.cursor() as k:
        k.execute(SQL_ISI)
    return m, sandi


def tambah_transaksi(n: int = 500) -> int:
    """Baris baru bertanggal hari ini (id melanjutkan yang terakhir): bahan latihan ekstrak inkremental."""
    m = _metadb()
    if m is None:
        raise RuntimeError("metadata bukan PostgreSQL bawaan")
    n = max(1, min(int(n), 100000))
    with _sambung(m, NAMA_DB) as c, c.cursor() as k:
        k.execute("""
            INSERT INTO toko.transaksi (id_transaksi, tanggal, kd_cabang, id_pelanggan, id_produk, jumlah, saluran, total)
            SELECT s.awal + x.g, current_date, x.kd_cabang, x.id_pelanggan, x.id_produk, x.jumlah, x.saluran, x.jumlah * p.harga
            FROM (SELECT coalesce(max(id_transaksi), 0) AS awal FROM toko.transaksi) s
            CROSS JOIN (SELECT g, 'C0' || (1 + floor(random() * 6)::int) AS kd_cabang,
                               1 + floor(random() * 20000)::int AS id_pelanggan, 1 + floor(random() * 500)::int AS id_produk,
                               1 + floor(random() * 5)::int AS jumlah,
                               (ARRAY['Online', 'Toko', 'Grosir', 'Reseller'])[1 + floor(random() * 4)::int] AS saluran
                        FROM generate_series(1, %s) g) x
            JOIN toko.produk p ON p.id_produk = x.id_produk""", (n,))
        k.execute("SELECT count(*) FROM toko.transaksi")
        return int(k.fetchone()[0])


def _koneksi(m: dict, sandi: str):
    from superset import db
    from superset.models.core import Database
    d = db.session.query(Database).filter_by(database_name=NAMA_KONEKSI).one_or_none()
    if d is None:
        d = Database(database_name=NAMA_KONEKSI, expose_in_sqllab=True, allow_dml=False)
        db.session.add(d)
    d.set_sqlalchemy_uri(f"postgresql+psycopg2://{AKUN_BACA}:{sandi}@{m['host']}:{m['port']}/{NAMA_DB}")
    db.session.commit()
    return d


def _dataset(d, nama: str, skema: str, tabel: str):
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable
    t = db.session.query(SqlaTable).filter_by(database_id=d.id, schema=skema, table_name=tabel).one_or_none()
    if t is None:
        t = SqlaTable(table_name=tabel, schema=skema, database=d)
        db.session.add(t)
    t.description = f"DATA FIKTIF dari database sumber contoh ({skema}.{tabel}); untuk latihan Ekstrak & Hubungkan data."
    db.session.flush()
    t.fetch_metadata()
    for c in t.columns:
        if c.column_name in ("tanggal", "tgl_daftar"):
            c.is_dttm = True
    pv = sm.add_permission_view_menu("datasource_access", t.get_perm())
    for role in ("Gamma", "Alpha"):
        r = sm.find_role(role)
        if r and pv not in r.permissions:
            sm.add_permission_role(r, pv)
    db.session.commit()
    return t


def siapkan_rls() -> list[str]:
    """Role per cabang + aturan RLS kd_cabang pada dataset latihan (tanpa akun)."""
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import RowLevelSecurityFilter, SqlaTable
    from superset.utils.core import RowLevelSecurityFilterType
    tabel = db.session.query(SqlaTable).filter(SqlaTable.table_name.in_(DATASET_RLS)).all()
    if not tabel:
        return ["RLS contoh dilewati: dataset latihan belum ada"]
    for nama_role, kode in ROLE_CABANG.items():
        role = sm.add_role(nama_role)
        nama = f"Latihan: hanya {nama_role.replace('Latihan ', '')}"
        rls = db.session.query(RowLevelSecurityFilter).filter_by(name=nama).one_or_none() or RowLevelSecurityFilter(name=nama)
        rls.filter_type, rls.clause = RowLevelSecurityFilterType.REGULAR, f"kd_cabang = '{kode}'"
        rls.description = "Contoh untuk latihan RLS (bahan ajar Level 3). Aman dihapus."
        rls.tables, rls.roles = tabel, [role]
        db.session.add(rls)
    db.session.commit()
    return [f"role & RLS contoh: {', '.join(ROLE_CABANG)} (kd_cabang) pada {len(tabel)} dataset latihan"]


def buat_akun_uji() -> list[str]:
    """Akun uji per cabang dengan sandi ACAK (dicetak sekali). Hanya atas permintaan (-AkunUji)."""
    from superset import db, security_manager as sm
    dasar = [r for r in (sm.find_role(os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna"), sm.find_role("Gamma")) if r]
    hasil = []
    for username, nama_role in AKUN_UJI.items():
        sandi = secrets.token_urlsafe(9)
        peran = dasar + [sm.add_role(nama_role)]
        u = sm.find_user(username=username)
        if u is None:
            u = sm.add_user(username, "Latihan", nama_role.replace("Latihan Cabang ", ""), f"{username}@latihan.invalid",
                            peran, password=sandi)
        else:
            u.roles, u.active = peran, True
            sm.reset_password(u.id, sandi)
        db.session.commit()
        hasil.append(f"akun uji {username}  sandi: {sandi}  (role {nama_role})")
    hasil.append("CATAT sandi di atas: tidak disimpan di mana pun. Hapus akun ini setelah latihan (Kelola > Pengguna).")
    return hasil


def siapkan() -> list[str]:
    """Database sumber contoh + koneksi + dataset + role RLS. Gagal = dilewati dengan catatan (latihan lain tetap jalan)."""
    hasil = []
    try:
        m, sandi = buat_database()
        d = _koneksi(m, sandi)
        for nama, (skema, tabel) in DATASET.items():
            _dataset(d, nama, skema, tabel)
        hasil.append(f"database sumber contoh '{NAMA_KONEKSI}': skema toko (6 tabel) & sdm (2 tabel), "
                     "200.000 transaksi, akun hanya-baca")
    except Exception as exc:  # noqa: BLE001 - sumber contoh bersifat tambahan
        from superset import db
        db.session.rollback()
        log.warning("ALDx latihan: database sumber contoh dilewati (%s)", exc)
        hasil.append(f"database sumber contoh dilewati: {str(exc).splitlines()[0][:120]}")
    hasil += siapkan_rls()
    return hasil
