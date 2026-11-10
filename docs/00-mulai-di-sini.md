# 00 · Mulai di Sini

Peta dokumentasi **ALDx** (berbasis Apache Superset). Pilih sesuai peran Anda.
Semua dokumen juga tersedia sebagai **PDF** di folder [`pdf/`](pdf/).

## Saya pengguna

| Ingin | Baca |
|---|---|
| **Tampilan baru**: Beranda, sidebar, Cari `Ctrl + K`, Cara pakai `?`, bahasa (ID/EN/JA), ponsel | [22-cangkang-aplikasi.md](22-cangkang-aplikasi.md) |
| **Alur menu** (Data › Kueri › Visual › Dashboard) & **Kueri Visual** tanpa SQL | [21-kueri-visual-dan-alur-menu.md](21-kueri-visual-dan-alur-menu.md) |
| Belajar membaca dashboard | [tutorial/level-1-pengguna.md](tutorial/level-1-pengguna.md) |
| Membuat chart & dashboard sendiri | [tutorial/level-2-analis.md](tutorial/level-2-analis.md) |
| Melihat semua jenis chart, peta, ramalan | [17-katalog-chart-peta-prediksi.md](17-katalog-chart-peta-prediksi.md) |
| **Asisten AI di setiap halaman** (`Ctrl + I`, peran `/analis`, `/panduan`, ...) | [23-asisten-ai-peran-ahli.md](23-asisten-ai-peran-ahli.md) |
| **Menyambungkan Asisten AI** (lokal Ollama/LM Studio, cloud gratis & berbayar) | [28-sambungkan-asisten-ai.md](28-sambungkan-asisten-ai.md) |
| **Ekspor** tabel/grafik ke gambar, PDF, Excel, CSV, TXT | [22-cangkang-aplikasi.md § 7](22-cangkang-aplikasi.md) |
| Halaman Asisten AI (Auto Chart, Story) | [10-asisten-ai.md](10-asisten-ai.md) |
| **Mode gelap**, menu akun, pemberitahuan @sebut | [22-cangkang-aplikasi.md](22-cangkang-aplikasi.md) |
| **Kueri tersimpan**, riwayat versi dashboard, tata letak ponsel | [26-langganan-versi-ponsel-lihat-sebagai.md](26-langganan-versi-ponsel-lihat-sebagai.md) |

## Saya admin data

| Ingin | Baca |
|---|---|
| Tutorial dataset, hak akses, ekstrak, upload | [tutorial/level-3-admin-data.md](tutorial/level-3-admin-data.md) |
| **Menghubungkan database, data warehouse, Access/Excel** | [06-sumber-data.md](06-sumber-data.md) |
| Aturan hak akses data (RLS) | [08-hak-akses-data.md](08-hak-akses-data.md) |
| ALDx Engine & ekstrak | [13-sps-engine-ekstrak.md](13-sps-engine-ekstrak.md) |
| Studio Visual (rinci, termasuk persiapan data) | [12-studio-visual.md](12-studio-visual.md) |
| **Lihat sebagai…** (uji hak akses), langganan laporan, lencana Resmi | [26-langganan-versi-ponsel-lihat-sebagai.md](26-langganan-versi-ponsel-lihat-sebagai.md) |

## Saya admin server

| Ingin | Baca |
|---|---|
| **Memasang** — pengguna awam | [CARA-PASANG.md](../CARA-PASANG.md) (satu halaman) |
| **Memasang** — rinci (PASANG.cmd; akun lokal atau LDAP) | [18-installer.md](18-installer.md), [02-instalasi.md](02-instalasi.md) |
| Memahami susunan sistem | [01-arsitektur.md](01-arsitektur.md) |
| Tutorial pengelolaan server | [tutorial/level-4-admin-server.md](tutorial/level-4-admin-server.md) |
| Akun, password ada di mana, cara masuk tiap container | [14-akun-dan-akses.md](14-akun-dan-akses.md) |
| Menentukan CPU/RAM/disk | [15-sizing.md](15-sizing.md) |
| Upgrade / downgrade komponen | [16-upgrade-downgrade.md](16-upgrade-downgrade.md) |
| **Menyambungkan Asisten AI**: lokal, cloud gratis, cloud berbayar (satu pintu) | [28-sambungkan-asisten-ai.md](28-sambungkan-asisten-ai.md) |
| Rincian model AI lokal (RAM, jaringan kantor, masalah) | [20-model-ai-lokal.md](20-model-ai-lokal.md) |
| Pusat Kendali, auto-tuning, multi-node | [11-pusat-kendali-server.md](11-pusat-kendali-server.md) |
| **Superadmin & Batas data** (ukuran/baris maksimal, rekomendasi, tanpa batas) | [24-superadmin-dan-batas-data.md](24-superadmin-dan-batas-data.md) |
| **Berkas .ald/.aldx** (simpan & bagikan laporan), **filter global**, **komentar & rating** | [25-berkas-filter-global-ulasan.md](25-berkas-filter-global-ulasan.md) |
| Pekerjaan harian, log, cadangan | [03-operasional.md](03-operasional.md) |
| **Cadangan terjadwal & uji pulih**, **uji beban** | [19-runbook-faq-admin.md §2.5](19-runbook-faq-admin.md), [15-sizing.md §4b](15-sizing.md) |
| **Daftar periksa audit keamanan** (sebelum produksi) | [27-daftar-periksa-audit-keamanan.md](27-daftar-periksa-audit-keamanan.md) |
| **Urutan menyala, SOP, FAQ gangguan** | [19-runbook-faq-admin.md](19-runbook-faq-admin.md) |
| Ada masalah (tabel pesan galat) | [04-troubleshooting.md](04-troubleshooting.md) |
| Login LDAP / Active Directory (opsional) | [05-login-ldap.md](05-login-ldap.md) |
| Nama, logo, warna, animasi (white-label) | [09-identitas-tema.md](09-identitas-tema.md) |
| Dashboard sebagai kode (contoh: profil DJP) | [07-dashboard-home-nasional.md](07-dashboard-home-nasional.md) |

## Saya pengajar / penguji

| Ingin | Baca |
|---|---|
| Bahan ajar per level (rencana sesi, latihan, kuis, kunci jawaban) | [bahan-ajar/](bahan-ajar/README.md) |
| Pelatihan admin: runbook & simulasi gangguan | [bahan-ajar/modul-runbook-admin.md](bahan-ajar/modul-runbook-admin.md) |
| Skenario uji (UAT) & lembar isian Excel | [pengujian/](pengujian/README.md) |
| **Laporan QA** (temuan & urutan perbaikan) | [pengujian/laporan-qa.md](pengujian/laporan-qa.md) |

## Profil DJP (opsional)

Aplikasi ini netral untuk perusahaan mana pun. Bagian khusus Direktorat Jenderal Pajak (login
intranet, profil pegawai dari Oracle DMP, Beranda & Home Nasional, preset tema `djp`) aktif hanya bila
diisi di `.env`. Lihat dokumen 05, 07, 08 dan preset `djp` di 09.

## Urutan membaca untuk pengembang

1. [01-arsitektur.md](01-arsitektur.md)
2. `config/superset_config.py` (dibaca dari atas, bernomor per bagian)
3. Docstring di awal setiap `config/sps_*/__init__.py` (urutan modul tertulis di sana)
4. [pengujian/README.md](pengujian/README.md) bagian 5 untuk cara uji
