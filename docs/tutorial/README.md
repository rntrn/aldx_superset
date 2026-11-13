# Tutorial ALDx per Level

Tutorial ini ditulis untuk pengguna **tanpa latar belakang IT**. Setiap langkah disertai gambar;
angka di dalam lingkaran emas pada gambar menunjukkan urutan bagian yang dibahas.

| Level | Untuk siapa | Bisa apa setelah selesai | Waktu belajar |
|---|---|---|---|
| [Level 1 · Pengguna](level-1-pengguna.md) | semua pengguna | login, membaca & menyaring dashboard, telusuri, tampilan tersimpan, PowerPoint, bertanya ke Asisten AI | 1 jam |
| [Level 2 · Analis](level-2-analis.md) | pembuat laporan di unit kerja | chart & dashboard dengan seret-lepas, peta, ramalan, template, tab, Auto chart, laporan & peringatan email | 3 jam |
| [Level 3 · Admin data](level-3-admin-data.md) | pengelola data di unit/divisi | sumber data, dataset, ekstrak, hak akses data, jejak data, pindai & gabung dataset lewat AI | 3 jam |
| [Level 4 · Admin server](level-4-admin-server.md) | tim TI pengelola server | memasang, memantau, kapasitas, cadangan, upgrade, SSO, sematan, kesehatan kueri, pengaturan AI | 4 jam |

Setiap level mengandaikan level sebelumnya sudah dikuasai.

**Tidak yakin menu mana untuk siapa?** Lihat [peta menu per level](../33-peta-menu-per-level.md): semua menu, fungsinya, dan bagian tutorial yang membahasnya.

**Bahan untuk pengajar** (rencana sesi, latihan, kuis, kunci jawaban): [../bahan-ajar/](../bahan-ajar/README.md) ·
**alur pelatihan** (kalender, penilaian, tindak lanjut): [../bahan-ajar/alur-pelatihan.md](../bahan-ajar/alur-pelatihan.md)

## Data latihan

Semua tutorial memakai **data fiktif** yang aman dipakai siapa saja:

| Dataset | Isi |
|---|---|
| `latihan_penjualan` | penjualan bulanan perusahaan ritel rekaan *PT Contoh Sejahtera*, Jan 2023 – Des 2025: 6 cabang, 5 kategori produk, 4 saluran penjualan |
| `latihan_lokasi_pelanggan` | 1.500 pelanggan rekaan dengan koordinat & provinsi |
| `latihan_penjualan_harian` | **± 2,3 juta baris** penjualan harian 2021–2025, 138 outlet di 17 provinsi; hierarki bawaan *Wilayah*, *Kalender*, *Produk*; pola Lebaran & anomali untuk ramalan |
| Dashboard **Latihan: Wilayah & Prediksi (fiktif)** | alamat `/superset/dashboard/latihan-wilayah/` |
| Dashboard **Latihan: Dashboard Penjualan (fiktif)** | alamat `/superset/dashboard/latihan/` |

Admin memuatnya dengan `scripts\data-latihan.ps1`. Angkanya selalu sama, sehingga hasil latihan
bisa dicocokkan dengan kunci jawaban.

## Kamus singkat

| Istilah | Arti sederhana |
|---|---|
| **Dashboard** | satu halaman berisi beberapa grafik tentang satu topik |
| **Chart / grafik** | satu gambar data (batang, garis, peta, …) |
| **Dataset** | tabel data yang menjadi bahan chart |
| **Dimensi** | kolom untuk mengelompokkan: cabang, kategori, bulan (biasanya teks/tanggal) |
| **Ukuran** | kolom angka yang dijumlah/dirata-rata: total penjualan, jumlah transaksi |
| **Filter** | menyaring agar hanya sebagian data yang tampil |
| **Agregasi** | cara meringkas angka: Jumlah (SUM), Rata-rata (AVG), Hitung (COUNT), … |
| **Ekstrak** | salinan data di server ALDx (ALDx Engine) agar dashboard cepat |
| **Hak akses data (RLS)** | aturan otomatis: pengguna hanya melihat data yang menjadi bagiannya (mis. cabangnya) |
| **Ramalan** | perkiraan nilai bulan-bulan berikutnya berdasarkan pola masa lalu |
| **Koneksi** | jalur ke satu sumber data (database kantor, data warehouse, atau berkas yang diimpor) |

### Membaca singkatan angka

| Di halaman Superset (dashboard, Explore) | Di Studio Visual | Arti |
|---|---|---|
| `k` | `rb` | ribu |
| `M` | `jt` | juta |
| `B` | `M` | **miliar** |
| `T` | `T` | triliun |

Contoh: `667B` di dashboard = `667,4 M` di Studio = **Rp667,4 miliar**. Arahkan kursor ke angka
untuk melihat nilai lengkapnya.
