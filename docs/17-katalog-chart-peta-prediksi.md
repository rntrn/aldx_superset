# 17 · Katalog Chart, Peta & Analitik Prediktif

Studio Visual punya **23 jenis chart** dalam 6 kelompok. Setiap jenis tersimpan sebagai chart
Superset asli: bisa dibuka di Explore, dipasang di dashboard, dan memakai hak akses data (RLS).

Cara memilih: seret kolom ke rak, lalu lihat panel **Tampilkan saya**. Tombol berbingkai emas
adalah rekomendasi; tombol pudar berarti kolom yang dipilih belum cukup (arahkan kursor ke tombol
untuk melihat kebutuhannya).

> Semua contoh gambar memakai **data latihan fiktif** (`latihan_penjualan`, `latihan_lokasi_pelanggan`).

---

## 1. Ringkasan

| Kelompok | Jenis | Butuh (dimensi · ukuran) | Chart Superset | Pakai untuk |
|---|---|---|---|---|
| Angka | Angka besar | 0 · 1 | Big Number | satu angka utama (KPI) |
| | Angka + tren | 1 tanggal · 1 | Big Number with Trendline | KPI + garis kecil perkembangannya |
| | Gauge | 0 · 1 | Gauge | capaian terhadap skala |
| Tabel | Tabel | 0–9 · 0–9 | Table | daftar rinci, angka persis |
| | Tabel pivot | 2–4 · 1–4 | Pivot Table | silang baris × kolom + total |
| | Peta panas | 2 · 1 | Heatmap | pola dua kategori (mis. bulan × kategori produk) |
| Perbandingan | Batang | 1–2 · 1–5 | Bar Chart | membandingkan kategori |
| | Batang 100% | 2 · 1 | Bar Chart (Expand) | komposisi per kategori dalam persen |
| | Garis | 1–2 · 1–5 | Line Chart | perkembangan waktu |
| | Area | 1–2 · 1–3 | Area Chart | perkembangan + komposisi |
| | Waterfall | 1 · 1 | Waterfall | kontribusi tiap bagian ke total |
| | Radar | 1 · 3–8 | Radar | profil beberapa ukuran sekaligus |
| Komposisi | Pie | 1 · 1 | Pie (donut) | bagian dari keseluruhan (≤ 7 bagian) |
| | Treemap | 1–2 · 1 | Treemap | komposisi bertingkat, banyak bagian |
| | Sunburst | 2–3 · 1 | Sunburst | komposisi bertingkat melingkar |
| | Corong | 1 · 1 | Funnel | tahapan yang menyusut |
| | Awan kata | 1 · 1 | Word Cloud | menonjolkan nama dengan nilai besar |
| Sebaran | Sebar | 1 · 2–3 | Bubble | hubungan dua ukuran |
| | Box plot | 2 · 1 | Box Plot | sebaran nilai, pencilan |
| | Sankey | 2 · 1 | Sankey | aliran dari kategori A ke B |
| Peta | Peta provinsi | 1 (kode provinsi) · 1 | Country Map (Indonesia) | nilai per provinsi |
| | Peta titik | lintang + bujur (+1 warna) · 0–1 | deck.gl Scatterplot | lokasi WP, kantor, POI |
| | Peta kepadatan | lintang + bujur · 0–1 | deck.gl Hexagon | konsentrasi titik |

---

## 2. Galeri

| | | |
|---|---|---|
| **Angka besar**<br>![](gambar/katalog/angka.png) | **Angka + tren**<br>![](gambar/katalog/angka_tren.png) | **Gauge**<br>![](gambar/katalog/gauge.png) |
| **Tabel**<br>![](gambar/katalog/tabel.png) | **Tabel pivot**<br>![](gambar/katalog/tabel_pivot.png) | **Peta panas**<br>![](gambar/katalog/peta_panas.png) |
| **Batang**<br>![](gambar/katalog/batang.png) | **Batang 100%**<br>![](gambar/katalog/batang_100.png) | **Garis**<br>![](gambar/katalog/garis.png) |
| **Area**<br>![](gambar/katalog/area.png) | **Waterfall**<br>![](gambar/katalog/waterfall.png) | **Radar**<br>![](gambar/katalog/radar.png) |
| **Pie**<br>![](gambar/katalog/pie.png) | **Treemap**<br>![](gambar/katalog/treemap.png) | **Sunburst**<br>![](gambar/katalog/sunburst.png) |
| **Corong**<br>![](gambar/katalog/funnel.png) | **Awan kata**<br>![](gambar/katalog/awan_kata.png) | **Sebar**<br>![](gambar/katalog/sebar.png) |
| **Box plot**<br>![](gambar/katalog/box_plot.png) | **Sankey**<br>![](gambar/katalog/sankey.png) | **Peta provinsi**<br>![](gambar/katalog/peta_wilayah.png) |
| **Peta titik**<br>![](gambar/katalog/peta_titik.png) | **Peta kepadatan**<br>![](gambar/katalog/peta_kepadatan.png) | |

---

## 3. Peta

### 3.1 Kolom geografis dikenali dari namanya

Di panel Data, kolom ini bertanda **Geo**.

| Peran | Nama kolom yang dikenali (huruf besar/kecil sama saja) |
|---|---|
| Lintang | `lat`, `latitude`, `lintang`, `..._lat`, `lat_...` |
| Bujur | `lon`, `lng`, `long`, `longitude`, `bujur`, `..._lon` |
| Provinsi | `prov`, `provinsi`, `propinsi`, `kd_prov`, `kode_prov`, `iso_prov` |

Nama kolom berbeda? Ubah nama lewat **Persiapan data → Ganti nama** atau alias di SQL dataset
(`SELECT KOORDINAT_Y AS lat ...`).

### 3.2 Peta provinsi

- Nilai kolom provinsi harus **kode ISO** agar cocok di chart Superset: `ID-JK` (DKI Jakarta),
  `ID-JB` (Jawa Barat), `ID-JI` (Jawa Timur), `ID-SU` (Sumatera Utara), dst.
- Pratinjau Studio juga mengenali **nama provinsi**, tetapi status lembar akan memperingatkan
  "dicocokkan lewat nama". Ubah ke kode ISO sebelum disimpan.
- Batas provinsi memakai peta bawaan Superset (33 provinsi; provinsi pemekaran setelah 2012 belum
  terpisah). Berkas peta tersimpan **lokal**: tidak butuh internet.

### 3.3 Peta titik & kepadatan

- Seret kolom **bujur** ke Kolom dan **lintang** ke Baris, lalu dimensi lain ke **Warna**
  (mis. saluran) dan ukuran ke **Ukuran** (besar titik).
- Pratinjau Studio memakai garis provinsi lokal. Chart Superset (deck.gl) memakai **ubin peta
  dasar** dari `SPS_PETA_UBIN` di `.env`, bawaannya OpenStreetMap (butuh internet di **browser
  pengguna**).
- Jaringan tanpa internet: pasang server ubin di jaringan kantor, isi
  `SPS_PETA_UBIN=http://10.x.x.x:8080/tile/{z}/{x}/{y}.png`, lalu `scripts\start.ps1`.
  Titik tetap tampil walau ubin tidak termuat.
- Titik dengan koordinat kosong atau di luar rentang (lintang ±90, bujur ±180) dilewati dan dihitung di status lembar.

---

## 4. Analitik prediktif

Panel **Analitik** di bawah Marks.

![Ramalan](gambar/tutorial/l2-07-ramalan.png)

| Pilihan | Hasil | Cara hitung |
|---|---|---|
| **Ramalan _n_ periode** | garis putus-putus + pita keyakinan **80%** (lebih gelap) dan **95%** | Holt (tren) atau **Holt-Winters** (tren + musiman) bila data ≥ 2 musim + 2 titik. Parameter dipilih otomatis dari galat terkecil |
| **Garis tren** | garis titik-titik + **R²** | regresi linear (kuadrat terkecil) |
| **Tandai anomali** | titik merah | buang tren (rata-rata bergerak) & pola musim, tandai sisa > 3,5 simpangan robust (MAD); bertahap, sehingga satu lonjakan tidak membuat bulan yang sama di tahun lain ikut tertandai |

Syarat: jenis **Garis, Area, atau Batang**, tepat **satu dimensi berurutan** (tanggal, `YYYY-MM`,
tahun, atau urutan lain), tanpa dimensi di Warna, minimal **4 periode**.

**Musim dikenali otomatis:** data bulanan → 12, triwulanan → 4, harian → 7.

### Membaca ramalan

- **Pita 80%**: 8 dari 10 kemungkinan nilai sebenarnya jatuh di dalam pita ini.
- Pita makin lebar ke kanan = makin jauh ke depan, makin tidak pasti.
- Ramalan hanya meneruskan pola masa lalu. Perubahan kebijakan, tarif, atau kejadian luar biasa
  **tidak** diketahui model; anggap ramalan sebagai **titik awal diskusi**, bukan target.
- Bulan berjalan yang belum lengkap menarik ramalan ke bawah; filter dulu agar hanya bulan lengkap.

### Ramalan di dashboard

Saat lembar dengan **Ramalan** atau **Garis tren** disimpan:

1. ramalan dihitung **sebagai pengguna yang menyimpan** (RLS berlaku);
2. hasilnya ditulis ke ALDx Engine (tabel `ramalan__xxxx`) dan didaftarkan sebagai dataset;
3. chart Superset menampilkan garis Aktual, Ramalan, batas 80%/95%, dan Tren;
4. **hanya pengguna dengan lingkup akses yang sama** dengan pembuat yang melihat isinya
   (aturan RLS "ALDx ramalan (lingkup pembuat)"; lingkup = profil akses, atau kumpulan role bila tanpa
   profil). Pengguna Cabang Jakarta tidak melihat ramalan yang dibuat pengguna Cabang Bandung, dan sebaliknya;
5. diperbarui otomatis **tiap hari 03:00** (tugas `sps.ramalan.segarkan`).

*Tandai anomali* hanya tampil di Studio Visual (tidak disimpan ke chart Superset).

### Kode

| Berkas | Isi |
|---|---|
| `config/sps_studio/prediksi.py` | Holt / Holt-Winters, interval, tren, anomali, label periode (numpy saja) |
| `config/sps_studio/ramalan.py` | simpan ke engine, dataset + RLS, penyegaran harian |
| `config/sps_studio/lembar.py` | `ATURAN_TANDA` (23 jenis), konversi ke chart Superset |
| `config/sps_studio/static/grafik.js` | perender pratinjau (ECharts, peta GeoJSON lokal) |
| `config/sps_studio/static/indonesia.geojson` | batas provinsi Indonesia |
