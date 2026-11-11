# ALDx — Advanced Learning & Data eXperience

Platform dashboard & BI **siap pakai untuk perusahaan/instansi mana pun**, berbasis Apache Superset.
Semua komponen berjalan di **Docker**: web, backgrounder, metadata (PostgreSQL), **ALDx Engine**
(ClickHouse), cache (Redis), dan gateway. Nama, logo, dan warna bisa diganti kapan saja (white-label).

## Memasang (pengguna biasa)

> **Baca [CARA-PASANG.md](CARA-PASANG.md)** — satu halaman, tanpa istilah teknis. Versi PDF: [docs/pdf/cara-pasang.pdf](docs/pdf/cara-pasang.pdf).

1. **Tim TI, sekali:** pasang Docker Desktop, masukkan akun pengguna ke grup `docker-users`.
2. **Unduh `ALDx-Setup.exe`**: [Releases › ALDx terbaru](../../releases/latest) (atau dari tim TI).
3. **Klik dua kali `ALDx-Setup.exe`** › Lanjut › Lanjut › **Pasang** › Selesai › isi **akun Superadmin** › **Pasang** › **Buka aplikasi**.

Tanpa internet: **`ALDx-Setup-Offline.exe`** + semua `.bin` ([Releases › ALDx offline](../../releases/tag/offline)), satu folder.
Tanpa Setup.exe: Download ZIP › Extract All › klik dua kali `PASANG.cmd` (wizard yang sama).
Menghapus: Settings › Apps › ALDx › Uninstall (container ikut terhapus; data hanya bila dipilih, dicadangkan dulu).

---

## Ringkasan teknis

| Komponen | Nilai |
|---|---|
| Lokasi proyek | `D:\superset` (boleh folder lain tanpa spasi) |
| Pasang | klik dua kali **`PASANG.cmd`** (wizard Next-Next) — panduan awam: [CARA-PASANG.md](CARA-PASANG.md) |
| Alamat web | http://localhost:8088 |
| Versi | Superset 6.1.0 · PostgreSQL 17 · ClickHouse 25.8 · Redis 7.4 · nginx 1.28 (atur di `.env`) |
| Metadata | container `metadb` (PostgreSQL), database `sps_superset` |
| ALDx Engine | container `engine`, database `sps_engine`: ekstrak, impor berkas, upload, ramalan |
| Sumber data | **Hubungkan data**: PostgreSQL, MySQL, SQL Server, Oracle, ClickHouse, Snowflake, BigQuery, Redshift, Databricks, Trino, Athena, SAP HANA (driver opsional), Vertica, Druid + berkas Access/Excel/CSV |
| Login | akun lokal ber-email (Superadmin wajib, pengguna lain diisi di installer) + LDAP / Active Directory **opsional** untuk NIP; halaman login beranimasi |
| HTTPS | opsional (centang di installer): sertifikat dibuat otomatis, `http://` dialihkan; sertifikat kantor bisa dipakai. Lihat [docs/11 §9b](docs/11-pusat-kendali-server.md#https) |
| Identitas & tema | bawaan **Tinta & Sakura** (hitam → abu → putih, semburat pink); nama, perusahaan, logo, warna, huruf, hiasan, animasi: Pusat Kendali, tanpa restart |
| Hak akses data | RLS per role (semua perusahaan) atau otomatis dari profil pengguna (profil DJP) |
| Menu | sidebar mengikuti alur BI: **Data › Kueri › Visual › Dashboard & Story › Asisten › Kelola**, angka 1–5 = urutan membuat laporan |
| Cangkang aplikasi | `/app/`: Beranda (**Siapkan ALDx** untuk admin, cari, 5 langkah bangun laporan, lanjutkan), sidebar urut alur kerja, `Ctrl + K`, tombol `?` cara pakai, bahasa ID/EN/日本語, tampilan ponsel. Lihat [docs/22](docs/22-cangkang-aplikasi.md) |
| Kueri Visual | `/kueri/`: klik dua kali tabel = kueri jadi, tabel kedua digabung otomatis, simpan jadi dataset |
| Studio Visual | `/studio/`: seret-lepas, 23 jenis chart, peta, ramalan, dashboard, persiapan data |
| Pusat Kendali | `/pusat-kendali/`: proses, cache, batas, identitas, hubungkan data, ekstrak, hak akses, multi-node |
| Asisten AI | **panel di setiap halaman** (`Ctrl + I`) dengan peran ahli `/analis` `/panduan` `/data-engineer` `/ahli-ui-ux` `/hw-engineer`; usulan perubahan baru berlaku setelah ditekan **Terapkan**. AI **paham isi aplikasi & halaman yang dibuka** (dataset, chart, dashboard beserta angkanya). **Sambungkan AI** di panel: model lokal (Ollama, LM Studio, Jan, llama.cpp) terdeteksi otomatis, key cloud gratis/berbayar diisi Admin tanpa restart ([docs/28](docs/28-sambungkan-asisten-ai.md)). Halaman `/asisten/`: auto chart/dashboard, story. Lihat [docs/23](docs/23-asisten-ai-peran-ahli.md) |
| Ekspor | tombol **Ekspor** di setiap tabel & grafik halaman ALDx: gambar PNG, PDF, Excel, CSV, TXT, salin |
| Keamanan & audit | akun terkunci otomatis setelah salah password berulang; **jejak audit** (login, unduh data, ekspor/impor, hak akses) di Pusat Kendali › Riwayat + CSV; role bawaan berhak minimum; peringatan akun non-Admin yang melihat semua data |
| Superadmin & batas data | role **Superadmin** di atas Admin untuk pengaturan vital; **Batas data** (ukuran/baris upload, impor, ekstrak, kuota engine) dengan rekomendasi otomatis atau tanpa batas. Lihat [docs/24](docs/24-superadmin-dan-batas-data.md) |
| Berkas .ald / .aldx | simpan & bagikan dashboard/chart/dataset sebagai berkas. Selalu **terenkripsi** (kunci server atau kata sandi), tanpa password koneksi; `.aldx` bisa membawa salinan data sesuai hak akses pembuat |
| Dashboard lanjutan | riwayat versi & pulihkan, tata letak ponsel, langganan laporan email, lencana Resmi, **Lihat sebagai…** (uji hak akses). Lihat [docs/26](docs/26-langganan-versi-ponsel-lihat-sebagai.md) |
| Filter global & ulasan | satu filter (pilihan, rentang angka, rentang waktu) berlaku di **semua dashboard & Story**, tersimpan per akun; **komentar & rating** dengan balasan, @sebut, pemberitahuan & moderasi Superadmin. Lihat [docs/25](docs/25-berkas-filter-global-ulasan.md) |
| Dokumentasi | **Panduan di dalam aplikasi** (menu *Panduan*, `/panduan/`: pencarian, daftar isi, mode gelap, tanpa internet) dari Markdown di `docs\` + **PDF** di `docs\pdf\` |
| Mutu | `scripts\uji.ps1` di server; daftar periksa audit keamanan [docs/27](docs/27-daftar-periksa-audit-keamanan.md) |

**Mulai membaca:** [`docs/00-mulai-di-sini.md`](docs/00-mulai-di-sini.md) (peta dokumentasi per peran).

---

## Untuk tim TI / pengembang

Bagian di bawah ini teknis. Pengguna biasa cukup bagian *Memasang* di atas.

```text
git clone https://github.com/rntrn/superset-ald.git D:\superset   # akhir baris otomatis benar (.gitattributes)
D:\superset\PASANG.cmd                                             # atau klik dua kali
powershell -ExecutionPolicy Bypass -File scripts\uji.ps1           # setelah terpasang: semua LULUS
```

Instalasi lama (metadata di XAMPP atau MariaDB) dipindah otomatis ke PostgreSQL oleh `PASANG.cmd`.
Urutan menyala & penanganan gangguan: [`docs/19-runbook-faq-admin.md`](docs/19-runbook-faq-admin.md).
Rinci installer: [`docs/18-installer.md`](docs/18-installer.md).

---

## Struktur folder

```
D:\superset
├── PASANG.cmd              # Installer wizard (Next-Next) -> installer\pasang.ps1
├── .env.example            # Template konfigurasi (installer membuat .env)
├── .env                    # Konfigurasi + password (RAHASIA, jangan dibagikan/di-commit)
├── docker-compose.yml      # Node utama: gateway, web, backgrounder, penjadwal, metadb, engine, redis
├── docker-compose.node.yml # Node tambahan (scale-out): web + backgrounder
├── LICENSE, NOTICE         # Lisensi Apache 2.0 + pemberitahuan hak cipta
├── THIRD-PARTY-LICENSES.md # Lisensi semua komponen pihak ketiga
├── installer/              # Kode wizard + log instalasi
├── server/                 # gateway.conf (otomatis), engine/ & metadb/ (konfigurasi & skrip perawatan)
├── backup/                 # Cadangan metadb (*.dump) & engine (engine\*.zip)
├── branding/               # Font lokal + logo ALDx (logo lain diunggah lewat Pusat Kendali)
├── certs/                  # (opsional) sertifikat CA kantor untuk model AI via API
├── docker/
│   ├── Dockerfile          # Image resmi + driver semua jenis database (offline)
│   ├── oracle/             # Oracle Instant Client (mode thick, opsional)
│   └── wheels/             # Paket offline (.whl) + paket.txt
├── config/
│   ├── superset_config.py  # Konfigurasi utama Superset (membaca .env)
│   ├── sps_security.py     # Login: LDAP + akun lokal, buat user otomatis, kunci cache aman
│   ├── sps_ldap.py         # Koneksi ke LDAP / Active Directory (ldap3), opsional
│   ├── sps_identitas/      # Identitas & tema, halaman login beranimasi
│   ├── sps_koneksi/        # Wizard Hubungkan data (database, data warehouse, Access/Excel/CSV)
│   ├── akses.yaml          # Aturan hak akses dari profil pengguna (profil DJP, opsional)
│   ├── sps_akses.py        # Profil pengguna + fungsi RLS sps_akses(), sps_sidik()
│   ├── sps_connections.py  # Koneksi dari .env (profil DJP, opsional)
│   ├── sps_pindah_meta.py  # Pindah metadata versi lama (MySQL/MariaDB) -> PostgreSQL
│   ├── sps_jinja.py        # Fungsi SQL template: sps_periode()
│   ├── sps_dashboard_builder.py, sps_dash_*.py  # Dashboard as code (contoh profil DJP)
│   ├── sps_build_dashboards.py # Menyiapkan dashboard, menu, izin, ALDx Engine
│   ├── sps_latihan.py      # DATA LATIHAN fiktif (penjualan ritel) + dashboard latihan
│   ├── sps_latihan_penerbangan.py # DATA LATIHAN fiktif penerbangan (Excel/CSV, 6 tabel, s.d. jutaan baris)
│   ├── sps_uji.py          # UJI OTOMATIS (scripts\uji.ps1)
│   ├── ai.yaml + sps_ai/   # Asisten AI
│   ├── sps_server/         # Pusat Kendali Server: pengaturan, auto-tuning, monitor, multi-node, HTTPS (tls.py)
│   ├── sps_engine/         # ALDx Engine: ekstrak, upload, tugas terjadwal
│   ├── sps_studio/         # Studio Visual: lembar kerja, 23 chart, peta, ramalan, dashboard, persiapan data
│   ├── sps_app/            # Cangkang aplikasi /app/: Beranda, navigasi, bahasa, bantuan, panel AI, ekspor
│   ├── sps_superadmin.py   # Role Superadmin di atas Admin + penjaganya
│   ├── sps_kueri/          # Kueri Visual: susun kueri & gabung tabel tanpa SQL
│   ├── sps_berkas/         # Berkas .ald/.aldx terenkripsi: ekspor & impor dashboard/chart/dataset (+ data)
│   ├── sps_filter_global.py # Filter global: satu filter untuk semua dashboard & Story
│   ├── sps_ulasan/         # Komentar & rating + moderasi Superadmin
│   ├── sps_dialek.py, sps_skema.py # Penyesuaian Oracle & chart berat; skema terpilih per koneksi
│   ├── sps_menu.py         # Susunan menu alur BI (izin menu; tampilan menu ada di sps_app)
│   └── sps_pengguna.py     # Membuat akun lokal dari tabel pengguna installer
├── scripts/
│   ├── init.ps1            # Instalasi (dipanggil installer)
│   ├── start.ps1 / stop.ps1 / logs.ps1
│   ├── uji.ps1             # Uji otomatis semua komponen
│   ├── cadangkan.ps1       # Cadangan & pemulihan metadb (+ engine)
│   ├── versi.ps1           # Versi tiap komponen
│   ├── data-latihan.ps1    # Muat data latihan fiktif
│   ├── data-penerbangan.ps1 # Buat Excel/CSV latihan penerbangan ukuran besar
│   ├── bersihkan-profil-djp.ps1 # Hapus dashboard & dataset profil DJP yang tidak dipakai
│   ├── pindah-metadata.ps1 # Pindah metadata versi lama (XAMPP/MariaDB) ke PostgreSQL
│   ├── add-connections.ps1 # Daftarkan koneksi dari .env (profil DJP)
│   ├── build-dashboards.ps1 # Dashboard, menu, izin, ALDx Engine
│   ├── terapkan-server.ps1 # Terapkan pengaturan Pusat Kendali yang butuh restart
│   ├── percayai-sertifikat.ps1 # Percayai sertifikat HTTPS server di komputer pengguna
│   ├── buka-kunci.ps1      # Darurat: buka kunci akun yang terkunci karena salah password
│   ├── jadwal-cadangan.ps1 # Jadwal cadangan harian + uji pulih mingguan (Task Scheduler)
│   ├── uji-beban.ps1       # Uji beban: N pengguna maya membuka dashboard bersamaan
│   ├── gabung-node.ps1     # Jadikan komputer lain node tambahan
│   ├── test-ldap.ps1, diagnose.ps1, cleanup.ps1
│   └── _umum.ps1           # Fungsi bersama (jangan dijalankan langsung)
├── sql/                    # HANYA untuk instalasi lama berbasis XAMPP (lihat sql/README.md)
└── docs/
    ├── 00-mulai-di-sini.md # Peta dokumentasi per peran
    ├── 01..19-*.md         # Dokumentasi teknis (arsitektur s.d. runbook admin)
    ├── tutorial/           # Tutorial bergambar per level (Pengguna, Analis, Admin data, Admin server)
    ├── bahan-ajar/         # Modul pelatihan: rencana sesi, latihan, kuis, kunci jawaban
    ├── pengujian/          # Skenario UAT (md + lembar Excel) & panduan pengujian
    ├── pdf/                # Versi PDF semua dokumen, tutorial, bahan ajar & presentasi
    └── gambar/             # Gambar dokumentasi
```

## Aturan dasar

1. **Koneksi, versi & rahasia ada di `.env`**; kemampuan server (proses, cache, batas, timeout, upload,
   ekstrak) diatur dari **Pusat Kendali Server**. File lain tidak perlu diubah sehari-hari.
2. **`SUPERSET_SECRET_KEY` jangan diganti** setelah instalasi: password koneksi yang tersimpan tidak akan terbaca.
3. **Cadangkan sebelum mengubah apa pun**: `scripts\cadangkan.ps1 -Engine`.
4. **Uji setelah mengubah apa pun**: `scripts\uji.ps1`.
5. Prefix **`sps_`** dipakai untuk database, tabel, dan modul tambahan proyek ini.

## Lisensi

ALDx dilisensikan dengan [Apache License 2.0](LICENSE): bebas dipakai, diubah, dan dibagikan ulang, asalkan
[`LICENSE`](LICENSE) dan [`NOTICE`](NOTICE) ikut disertakan. Komponen pihak ketiga beserta lisensinya, dan
komponen yang harus diunduh sendiri (Oracle Instant Client, driver SAP HANA, logo instansi):
[THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md).
