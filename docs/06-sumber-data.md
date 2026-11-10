# 06 · Sumber Data: Database, Data Warehouse & Berkas

Cara termudah: **Data → Hubungkan data** (wizard 4 langkah, khusus Admin).
Tutorial bergambar: [tutorial Level 3 §1](tutorial/level-3-admin-data.md#1-menghubungkan-sumber-data-wizard-hubungkan-data).

```
1 Pilih sumber ─► 2 Isi detail ─► 3 Uji koneksi ─► 4 Simpan
   database / data warehouse ──► koneksi Superset (hanya-baca, password terenkripsi)
   berkas Access/Excel/CSV   ──► disalin ke ALDx Engine ──► dataset siap dibuat chart
```

## 1. Jenis sumber yang didukung

| Kelompok | Jenis | Isian utama | Catatan |
|---|---|---|---|
| Database | PostgreSQL | alamat, port 5432, database, user, password, SSL | juga Supabase, Neon, Amazon RDS/Aurora |
| | MySQL / MariaDB | alamat, port 3306, database, user, password | juga XAMPP, Amazon RDS MySQL, TiDB |
| | SQL Server / Azure SQL / Synapse | alamat, port 1433, database, user, password | login SQL Server (bukan Windows authentication) |
| | Oracle | alamat, port 1521, **service name**, user, password | Oracle 11g butuh Instant Client (`docker\oracle\`) |
| | ClickHouse | alamat, port HTTP 8123/8443, database, user, password | |
| Data warehouse | Snowflake | account identifier, user, password, database, schema, warehouse, role | |
| | Google BigQuery | project ID, kunci service account (JSON) | kunci disimpan terenkripsi |
| | Amazon Redshift | alamat, port 5439, database, user, password | |
| | Databricks SQL | server hostname, HTTP path, access token, catalog, schema | |
| | Trino / Starburst / Presto | alamat, port, user, catalog, schema, HTTPS | |
| | Amazon Athena | region, S3 staging dir, access key, secret key, database | |
| | SAP HANA | alamat, port 30015, tenant, user, password | |
| | Vertica | alamat, port 5433, database, user, password | |
| | Apache Druid | alamat, port 8082, HTTPS | |
| Lainnya | URI SQLAlchemy | `dialek+driver://user:pass@host:port/db` | untuk admin berpengalaman |
| **Berkas** (diimpor) | Microsoft Access `.mdb` `.accdb` | unggah berkas → pilih tabel | kolom foto/lampiran (OLE) dilewati |
| | Excel `.xlsx` `.xls`, CSV `.csv` `.txt` `.tsv` | tiap lembar = satu tabel | pemisah CSV dikenali otomatis (`,` `;` tab `|`) |
| | SQLite, DuckDB, Parquet | semua tabel dibaca | |

Batas ukuran & jumlah baris berkas diatur Superadmin di **Pusat Kendali › Batas data** (bawaan `auto` = dihitung
dari RAM server; `0` = tanpa batas). Lihat [24-superadmin-dan-batas-data.md](24-superadmin-dan-batas-data.md).

## 2. Aturan keamanan

- Koneksi dari wizard selalu **hanya-baca** (`allow_dml = false`) dan **tidak** menerima upload.
  Minta akun database **hanya-baca** ke DBA.
- Password dipisah dari alamat dan **dienkripsi** dengan `SUPERSET_SECRET_KEY`.
- Pesan galat menyamarkan password; berkas unggahan dihapus setelah diimpor (atau setelah 2 jam).
- Metadata aplikasi sendiri dan berkas lokal di server (SQLite/DuckDB lewat URI) **ditolak** sebagai sumber.
- Hak akses baris (RLS) tetap berlaku untuk semua dataset dari koneksi mana pun ([08](08-hak-akses-data.md)).

## 2a. Skema yang ditampilkan

Database besar (mis. Oracle DJP) berisi ratusan skema milik pengguna lain. Setelah **Uji koneksi** berhasil,
centang skema yang berisi data Anda (mis. `genapp`), lalu **Simpan**. Skema lain disembunyikan di
**Dataset**, **SQL Lab**, **Kueri Visual**, dan **Studio**; skema pertama dipilih otomatis di Kueri Visual.

- Koneksi lama: **Koneksi tersimpan → Atur skema** (cari, centang, *Simpan skema*). Berlaku langsung.
- Tidak ada yang dicentang = semua skema tampil.
- Ini hanya menyaring **daftar**; hak akses data tetap diatur RLS ([08](08-hak-akses-data.md)).

## 3. Setelah tersambung

| Ingin | Cara |
|---|---|
| Mencoba query | SQL Lab (tautan muncul setelah simpan) |
| Membuat dataset | menu **Datasets → + Dataset** pilih koneksi, schema, tabel |
| Membuat chart | Studio Visual → pilih dataset |
| Mempercepat sumber lambat | **Ekstrak** ke ALDx Engine ([13](13-sps-engine-ekstrak.md)) |
| Mengubah alamat/password / menghapus koneksi | Hubungkan data → Koneksi tersimpan → *pengaturan koneksi lanjutan* |
| Memilih skema yang tampil | Hubungkan data → Koneksi tersimpan → **Atur skema** |

## 4. Menambah jenis database baru (pengembang)

1. Tambah driver `.whl` di `docker\wheels\` + nama paketnya di `docker\wheels\paket.txt`
   ([README](../docker/wheels/README.md)), lalu `docker compose build` dan `scripts\start.ps1`.
2. Tambah satu `Jenis(...)` di `config\sps_koneksi\katalog.py`: isian formulir + templat URI.
3. `scripts\uji.ps1` memeriksa semua driver di katalog terpasang.

## 5. Koneksi dari `.env` (profil DJP, opsional)

Untuk instalasi DJP, empat koneksi standar dibuat otomatis dari `.env` oleh
`scripts\add-connections.ps1` (`config\sps_connections.py`). Koneksi dengan password kosong dilewati.

| Nama di Superset | Jenis | Variabel `.env` |
|---|---|---|
| Oracle DMP (GENAPP) | Oracle | `ORACLE_DMP_*` (juga sumber profil pegawai: `AKSES_DATABASE`) |
| Oracle Dashboard (IKU) | Oracle | `ORACLE_IKU_*` |
| Oracle Dashboard (DASHBD) | Oracle | `ORACLE_DASHBD_*` (versi lama: `ORACLE_TABLEAU_*`, dipindah otomatis) |
| ClickHouse DMP_OLAP | ClickHouse | `CLICKHOUSE_*` |

Alamat bawaan DJP diisi otomatis oleh installer bila password sumber DJP diisi.

## 6. Masalah umum

| Pesan | Arti | Tindakan |
|---|---|---|
| *timed out* / *could not connect* / *Unable to connect* | server tidak terjangkau dari Docker | cek alamat & port, VPN, firewall server database |
| *authentication failed* / *Login failed* / *Access denied* | user/password salah atau tidak berhak | periksa ke DBA |
| *Driver … belum terpasang* | paket Python belum ada di image | §4 langkah 1 |
| *database … does not exist* | nama database / service salah | cek ejaan, huruf besar-kecil |
| Oracle `DPY-3010` | Oracle di bawah 12.1 | pasang Instant Client ([04](04-troubleshooting.md)) |
| Oracle `ORA-00933 SQL command not properly ended` (versi lama aplikasi) | batas baris `FETCH FIRST` tidak dikenal Oracle 11g | sudah diperbaiki: batas memakai `ROWNUM` (`config/sps_dialek.py`). Restart `superset` & `superset-worker` |
| Daftar skema terlalu banyak / tabel *tidak ada* | skema yang dipilih bukan tempat tabel | §2a: **Atur skema** |
| Impor: *tidak berisi tabel* | berkas kosong / terlindung password | buka di aplikasinya, simpan ulang tanpa password |
