# 31 · Catatan Versi

Daftar perubahan per rilis, terbaru di atas. Setiap rilis punya bagian **Perlu dilakukan setelah memperbarui** untuk
ketiga cara memasang ([29 §1](29-versi-pembaruan-hapus-total.md)).

> **Untuk pengembang:** setiap pembaruan aplikasi, naikkan `VERSI` di `config/sps_versi_aplikasi.py` (format `YYYY.MM.DD`,
> rilis kedua di hari yang sama `YYYY.MM.DD.2`; dipakai halaman login, Beranda, dan pengecekan *Pembaruan tersedia*) dan tambahkan
> baris di rilis teratas. Setelah masuk cabang `main`, GitHub Actions membangun dan menerbitkan `ALDx-Setup.exe`,
> `ALDx-Setup-Offline.exe` dan `ALDx-HapusTotal.exe` ke Releases; build ditolak bila kode berubah tetapi `VERSI` tidak ([29 §1](29-versi-pembaruan-hapus-total.md)).

---

## November 2026 · BI lanjutan

### Baru

| Area | Perubahan | Dokumen |
|---|---|---|
| Sematkan | Dashboard tampil di web/aplikasi lain (`<iframe>` + token tamu), **RLS per penonton**, filter dari URL, hanya domain yang diizinkan | [30](30-sematkan-dashboard.md) |
| Tema | Preset **Neon malam** (gelap, pink + cyan), **warna aksen kedua**, kombinasi warna manual, warna teks otomatis paling kontras, palet chart *ALDx Neon* | [09](09-identitas-tema.md) |
| Studio | **Saran chart** mencakup hampir semua jenis (bukan 1–2), masing-masing berlabel jenis | [12](12-studio-visual.md), [10](10-asisten-ai.md) |
| Studio | **Hierarki dimensi** (provinsi › kabupaten › kecamatan › …): klik chart untuk menelusuri, ◂/▸ naik/turun level | [12](12-studio-visual.md#hierarki-dimensi-telusur-bertingkat) |
| Studio | **Objek desain dashboard**: Teks (10 huruf lokal, ukuran, warna, latar, rata), Gambar (unggah), Garis pemisah | [12](12-studio-visual.md#objek-desain-teks-gambar-garis) |
| Filter global | Nilai dipilih dari **daftar yang bisa dicari** (RLS berlaku), **chip filter aktif** di bilah atas, *Kecualikan dashboard ini* | [25](25-berkas-filter-global-ulasan.md) |
| Dashboard | Klik-filter antar-chart, **drill to detail**, **drill by** aktif bawaan | [12](12-studio-visual.md) |
| Studio | **Hierarki seret-tumpuk**: seret satu dimensi ke atas dimensi lain → beri nama (seperti Tableau); seret ke atas hierarki = tambah level | [12](12-studio-visual.md#hierarki-dimensi-telusur-bertingkat) |
| Studio | **Tampilkan saya** tidak lagi mematikan jenis saat kolom berlebih: kolom ekstra tidak dipakai & ditandai pudar (±19 dari 23 jenis aktif dengan 3 dimensi) | [12](12-studio-visual.md#tampilkan-saya-dengan-banyak-kolom) |
| Analitik | Opsi baru: **rata bergerak**, **garis rata-rata**, **median**, **target**, **tertinggi & terendah** (ikut tersimpan ke chart Superset); tombol **Siapkan agar analitik aktif** | [17 §4](17-katalog-chart-peta-prediksi.md#4-analitik-prediktif) |
| Studio | **+ Ukuran / + Dimensi**: definisikan ukuran (rumus agregat) & dimensi (rumus per baris) seperti *measure / column* Power BI, dengan uji rumus | [12](12-studio-visual.md#ukuran--dimensi-terdefinisi-seperti-new-measure--new-column-power-bi) |
| Dashboard | **Telusuri ke dashboard lain** (drill-through): filter & klik-filter aktif dibawa ke dashboard lain | [25 §2b](25-berkas-filter-global-ulasan.md) |
| Studio | **N teratas** (Top N) | [12](12-studio-visual.md#n-teratas-top-n) |
| Studio | **Kalkulasi cepat**: *% dari total* & *Kumulatif* (pilihan **Hitung**), ikut tersimpan ke chart | [12](12-studio-visual.md#kalkulasi-cepat--dari-total--kumulatif) |
| Studio | **Skala warna sel** pada Tabel; **Kelompokkan nilai…** (klik kanan dimensi → kelompok bernama tanpa menulis rumus) | [12](12-studio-visual.md#skala-warna-tabel) |
| Dashboard | **Dari template…**: Ringkasan eksekutif, Tren & ramalan, Perbandingan kategori; kolom dipilih otomatis, kanvas & filter terisi | [12 §2](12-studio-visual.md#2-susun-dashboard) |
| Studio | Kalkulasi cepat **% vs tahun lalu (YoY)**; batang mendatar tersimpan kini terbesar di atas (sama dengan pratinjau) | [12](12-studio-visual.md) |
| Dashboard | **Tampilan tersimpan** (bookmark): simpan keadaan filter dengan nama, buka lagi satu klik | [25 §2c](25-berkas-filter-global-ulasan.md) |
| Dashboard | Menu **Peringatan data**: email bila angka melewati ambang | [26 §1b](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Data | Halaman **Jejak data** (lineage): sumber → dataset → chart → dashboard, untuk melihat dampak sebelum mengubah dataset | [26 §7](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Dashboard | **Label kesegaran data** di bilah atas (*Data: 2 jam lalu* / *Data langsung*), rincian per dataset | [26 §7b](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Studio | **Simulasi what-if**: geser satu ukuran −50%…+100% (hanya pratinjau) | [12](12-studio-visual.md#simulasi-what-if) |
| Asisten AI | Alat **gabung dataset** (denormal/detail): kunci otomatis, banyak-ke-banyak dilewati, RLS ikut. Pertanyaan berhenti rapi sebelum batas server (pesan langkah yang sudah selesai) | [23](23-asisten-ai-peran-ahli.md) |
| Persiapan data | Aturan RLS biasa per role kini ikut disalin saat menggabung/menyimpan dataset (sebelumnya ditolak) | [12](12-studio-visual.md#gabung-data-join) |
| Studio | Penyusun dashboard: **tab** dan **tinggi kotak** per chart | [12 §2](12-studio-visual.md#2-susun-dashboard) |
| Studio | **Tooltip kaya** (porsi dari total, porsi di titik, ▲/▼ vs sebelumnya); **Jelaskan perubahan** (klik kanan periode → penyumbang terbesar per dimensi) | [12](12-studio-visual.md#jelaskan-perubahan) |
| Analitik | Analitik **per Warna** (ramalan/tren per nilai dimensi warna) | [17 §4](17-katalog-chart-peta-prediksi.md#4-analitik-prediktif) |
| Dashboard | **Ekspor ke PowerPoint** (satu chart per slide) | [26 §7c](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Admin | **Kesehatan kueri**: chart/dashboard lambat (p95), kueri gagal, saran perbaikan | [26 §7d](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Login | **Masuk dengan SSO** (OpenID Connect: Microsoft Entra ID, Google, Okta, Keycloak), tambahan di samping login password | [05](05-login-ldap.md#masuk-dengan-sso-openid-connect) |
| Dashboard | **Klik kanan chart → Telusuri ke dashboard lain…** (drill-through satu gerakan) | [25 §2b](25-berkas-filter-global-ulasan.md) |
| Rilis | `VERSI` wajib naik tiap pembaruan (dijaga GitHub Actions); tanggal & judul di halaman Releases selalu build terakhir; versi mendukung nomor urut harian (`2026.11.13.2`) | [29 §1](29-versi-pembaruan-hapus-total.md) |
| Asisten AI | Tombol cepat di dashboard: **Ringkas dashboard ini dalam 5 poin** & *Apa yang janggal…* | [23](23-asisten-ai-peran-ahli.md) |
| Peta jalan | Perbandingan fitur dengan Tableau, Power BI, Looker, Sigma | [32](32-perbandingan-fitur-bi.md) |
| Installer | Installer online, offline & HapusTotal kini **dibangun dan diterbitkan otomatis** oleh GitHub Actions di setiap perubahan `main` | [29 §1](29-versi-pembaruan-hapus-total.md) |
| Versi | Versi terpasang tampil di **halaman login** & **Beranda**, dengan status *Versi terbaru* / *Pembaruan tersedia* (dicek ke GitHub) | [29](29-versi-pembaruan-hapus-total.md) |
| Ekstrak | **Impor banyak tabel sekaligus** dari satu koneksi, dengan **cek kapasitas** (perkiraan ukuran vs sisa kuota & disk engine: Cukup / Mendekati / Tidak cukup) sebelum impor | [13 §2.5](13-sps-engine-ekstrak.md) |
| Data latihan | **Database sumber contoh** (*Contoh sumber (PostgreSQL)*, akun hanya-baca) untuk latihan Hubungkan data, Ekstrak & impor banyak tabel; **role RLS contoh** per cabang (`-AkunUji`); dashboard Wilayah kini punya filter **rentang Tahun** & **Rentang waktu** | [bahan ajar](bahan-ajar/README.md#peta-fitur--data-contoh) |
| Data latihan | **`latihan_penjualan_harian`**: ±2,3 juta baris harian 2021–2025, hierarki Wilayah/Kalender/Produk, pola Lebaran & anomali, dashboard *Latihan: Wilayah & Prediksi*; dimuat otomatis oleh installer (`-Skala` s.d. ±23 juta baris) | [bahan ajar](bahan-ajar/README.md) |

### Perbaikan

| Masalah | Penyebab & perbaikan |
|---|---|
| **Ramalan / tren / anomali tidak bisa dipakai** pada data ALDx Engine (mis. `latihan_penjualan`) | Superset 6.1 tidak mengenali kolom ClickHouse `Float32/Float64` (termasuk di dalam `Nullable(...)`) sebagai angka. Kolom seperti `total` masuk **Dimensi**, tidak bisa dijumlah, dan panel Analitik mati. Sekarang dikenali sebagai angka (`config/sps_dialek.py` §5), juga di Explore |
| Filter **Rentang waktu** dashboard tidak berpengaruh pada chart buatan Studio | chart tidak mencatat kolom waktu dataset; kini dicatat saat chart disimpan (simpan ulang chart lama agar ikut) |
| Label sumbu tanggal panjang ("Sat, 01 Mar 2025 00:00:00 GMT") | Kolom `Date/Date32` kini dikirim sebagai `2025-03-01` (`config/sps_ai/alat.py`) |
| **Pilih preset Tinta & Sakura (pink) tapi warna tetap hijau** | preset ini ikut mengosongkan nama perusahaan sehingga ditolak validasi; kini preset hanya mengubah tampilan, dan tiap preset menetapkan keempat warnanya |
| Kolom `ID_…` (mis. `t1.ID_Penerbangan` hasil gabung Kueri Visual) masuk **Ukuran** | awalan alias tabel `t1.` membuat ID tidak dikenali; pengenal ID/kode kini membuang awalan & mengenali `ID_x`, `x_id`, `idX`, `XId`, `kode_`, `NIK` |

### Perlu dilakukan setelah memperbarui

| Cara memasang | Langkah |
|---|---|
| **git** | `Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1` (folder hasil Setup.exe: tambah `-JadikanGit` sekali; ambil versi baru, terapkan, uji: harus **81/81 LULUS**) → browser `Ctrl + F5` |
| **ALDx-Setup.exe** (online) | pastikan tanggal exe di Releases **setelah** rilis ini → jalankan di atas instalasi lama (folder sama; data & `.env` dipertahankan) → `Ctrl + F5` |
| **ALDx-Setup-Offline.exe** + `.bin` | sama dengan online; semua fitur baru jalan **tanpa internet** (huruf, peta, ECharts, gambar tersimpan lokal) |

Tidak ada langkah manual lain:
- Tabel baru `sps_hierarki` (hierarki) dan `sps_gambar` (gambar dashboard) dibuat otomatis di metadb.
- Data latihan harian & dashboard *Latihan: Wilayah & Prediksi*: dimuat otomatis oleh Setup; instalasi git jalankan
  `scripts\data-latihan.ps1` sekali (± 20 detik).
- Kolom desimal di ALDx Engine otomatis pindah ke **Ukuran** di Studio. Chart lama yang sudah disimpan tidak berubah.
- Role tamu *Penonton Sematan* dibuat otomatis oleh `build-dashboards`.

Opsional, hanya bila memakai fitur **Sematkan**: isi di `.env` lalu `docker compose up -d`:

```ini
SPS_SEMATKAN_DOMAIN=https://portal.kantor.co.id     # domain yang boleh menyematkan, pisah spasi
SPS_SEMATKAN_KUNCI=<string acak panjang>            # kunci server Anda untuk meminta token tamu (RAHASIA)
SPS_SEMATKAN_MENIT=15                               # umur token tamu (menit)
```

### Menghapus versi ini

Tidak ada yang berbeda dari [29 §2–3](29-versi-pembaruan-hapus-total.md):
- **Uninstall biasa** (*hapus data = Tidak*): hierarki, gambar dashboard, dan filter global tetap ada di volume data
  dan kembali saat dipasang ulang.
- **Hapus total / `ALDx-HapusTotal.exe`**: semuanya ikut **dicadangkan** (di dalam cadangan metadb) sebelum dihapus,
  dan kembali saat cadangan dipulihkan.
