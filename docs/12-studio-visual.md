# 12 · Studio Visual

Pembuatan chart, dashboard, dan persiapan data dengan **drag & drop**, di dalam Superset: **http://localhost:8088/studio/** (menu **Studio Visual**).

| Tab | Isi |
|---|---|
| **Lembar kerja** | Panel Data (Dimensi/Ukuran), rak Kolom/Baris/Filter, kartu Marks (Warna, Ukuran, Label), "Tampilkan saya", saran dari data |
| **Susun dashboard** | Seret lembar kerja ke kanvas, atur lebar ¼ ⅓ ½ ⅔ penuh, filter dashboard, klik-filter antar-chart |
| **Persiapan data** | Alur langkah termasuk **gabung (join)**, profil kolom, aksi cepat, simpan sebagai dataset baru |

Hasilnya **chart, dashboard, dan dataset Superset biasa**: bisa dibuka di Explore, diedit di editor
dashboard Superset, dipakai Asisten AI & Story. Chart buatan Studio bisa dibuka lagi di Studio
(spesifikasinya disimpan di `params.sps_studio`).

Pilihan dataset berisi dataset **fisik dan virtual** yang boleh Anda akses. Dataset yang baru dibuat (mis. dari
Kueri Visual atau SQL Lab) muncul otomatis saat Anda kembali ke Studio, tanpa memuat ulang halaman.

Tautan langsung: `/studio/?dataset=<id>` membuka lembar kerja dengan dataset itu; `/studio/?tab=prep&dataset=<id>`
membuka Persiapan data (dipakai tombol lanjutan Kueri Visual dan menu **Data → Persiapan data**).

---

## 1. Lembar kerja

```
┌ Panel Data ┐┌ Filter ┐┌ Kolom: [nm_cabang]          ┐┌ Tampilkan saya ┐
│ Dimensi    ││ Marks  ││ Baris: [SUM(total)]         ││ ▣ ▣ ▣          │
│  Abc kd_.. ││ Warna  ││ ┌──────── kanvas ────────┐  ││ ▣ ▣ ▣          │
│ Ukuran     ││ Ukuran ││ │   grafik (ECharts)     │  ││ Saran dari data│
│  #  total  ││ Label  ││ └────────────────────────┘  ││ Tersimpan      │
└────────────┘└────────┘└─────────────────────────────┘└────────────────┘
```

| Aksi | Cara |
|---|---|
| Menambah kolom | Seret dari panel Data ke rak; atau **klik dua kali** (dimensi → Kolom, ukuran → Baris) |
| Ganti agregasi | Klik pil ukuran → Jumlah / Rata-rata / Hitung / Hitung unik / Min / Maks |
| Filter | Seret kolom ke rak **Filter** → centang nilai (dimensi) atau isi min/maks (ukuran) |
| Warna / bertumpuk | Seret dimensi ke **Warna** → batang/area bertumpuk per nilai |
| Membuang | Seret pil kembali ke panel Data, atau klik × |
| Batang mendatar | Tombol **Tukar** (isi rak Kolom ⇄ Baris) |
| Lihat angka | **Lihat data** (tabel di bawah grafik) |
| Simpan | **Simpan** (perbarui) / **Simpan baru** → chart Superset |

### Panel Data: Dimensi vs Ukuran

Kolom dibagi otomatis (`config/sps_studio/bidang.py`):
**Ukuran** = kolom angka yang bukan kode/ID/waktu, metrik tersimpan dataset, dan "Jumlah baris".
**Dimensi** = teks, tanggal/periode (`tahun`, `bulan`), kode (`kd_*`, `npwp`, `nip`).

### Tampilkan saya (Show Me)

Jenis yang bisa dipakai menyala; **bingkai emas = rekomendasi**. Aturan kebutuhan ada di satu tempat:
`ATURAN_TANDA` di `config/sps_studio/lembar.py` (dipakai server & browser).

**23 jenis** dalam 6 kelompok (Angka, Tabel, Perbandingan, Komposisi, Sebaran, Peta). Daftar lengkap,
kebutuhan, dan galeri: [17-katalog-chart-peta-prediksi.md](17-katalog-chart-peta-prediksi.md).

Urutan rekomendasi (yang pertama cocok dipakai):

| Kondisi | Rekomendasi |
|---|---|
| hanya ukuran: 1 / lebih | Angka besar / Tabel |
| ada kolom lintang **dan** bujur | Peta titik |
| 1 dimensi provinsi + 1 ukuran | Peta provinsi |
| ukuran di Kolom **dan** Baris, 1 dimensi | Sebar |
| dimensi di Kolom **dan** Baris, ukuran di Warna | Peta panas |
| ≥ 3 dimensi di Kolom & Baris | Tabel pivot |
| ada dimensi waktu | Garis |
| 1–2 dimensi kategori | Batang |
| lainnya | Tabel pivot / Tabel |

### Panel Analitik

Ramalan (Holt-Winters, pita 80/95%), garis tren (R²), tanda anomali, **rata-rata bergerak**, **garis rata-rata**,
**garis median**, **garis target**, dan **tertinggi & terendah** untuk Garis/Area/Batang dengan satu dimensi berurutan.
Panel pudar? Klik **Siapkan agar analitik aktif**: kolom tanggal dipilih, dimensi lain dilepas, ukuran ke Baris,
jenis menjadi Garis. Penjelasan: [17 bagian 4](17-katalog-chart-peta-prediksi.md#4-analitik-prediktif).

### Hierarki dimensi (telusur bertingkat)

Beberapa kolom bertingkat dipakai seperti **satu kolom**, mis. *Wilayah* = provinsi › kabupaten › kecamatan › kelurahan.

| Langkah | Cara |
|---|---|
| Buat (seret-tumpuk) | **Seret satu dimensi ke atas dimensi lain** di panel Data (mis. `kecamatan` ke atas `kab_kota`): dialog *Hierarki baru* terbuka dengan urutan terisi, tinggal beri **nama** (= nama kolom baru). Seret dimensi ke atas **hierarki** = tambah level paling rinci |
| Buat (dialog) | Panel Data → **Hierarki → ＋**, beri nama, centang kolom **berurutan dari yang paling umum** (2–8 level). Atau menu pil → *Buat hierarki dari kolom ini…* |
| Pakai | Seret/dobel klik hierarki ke rak. Tampil di level teratas (teragregasi). |
| Masuk ke satu nilai | **Klik** batang/titik/wilayah di chart → level berikutnya, difilter ke nilai itu (jalur tampil di pil, mis. `ID-JK › kategori`). |
| Turun / naik level | Tombol **▸** (level berikutnya, semua nilai) dan **◂** (kembali satu level) di pil. |
| Hapus | Tombol 🗑 di daftar Hierarki. |

- Disimpan **per dataset di server** (tabel `sps_hierarki`), dipakai semua orang yang boleh membuka dataset itu.
  Membuat/menghapus butuh izin membuat chart (Alpha/Admin).
- Chart yang disimpan memakai **level yang sedang tampil** (beserta filter jalurnya).
- API: `GET/POST /studio/api/hierarki/<dataset_id>`, `POST /studio/api/hierarki/<dataset_id>/hapus`
  (modul `config/sps_studio/hierarki.py`).

Data latihan `latihan_penjualan_harian` sudah membawa hierarki **Wilayah** (pulau › provinsi › kab/kota › kecamatan ›
kelurahan › outlet), **Kalender** (tahun › kuartal › bulan › tanggal), dan **Produk** (kategori › subkategori).

### Ukuran & dimensi terdefinisi (seperti *New measure / New column* Power BI)

Panel Data › **+ Ukuran** atau **+ Dimensi** (butuh izin mengubah dataset: Alpha/Admin).

| | Ukuran | Dimensi |
|---|---|---|
| Rumus | **agregat**: `SUM(laba) / SUM(penjualan)`, `COUNT(DISTINCT id_pelanggan)`, `SUM(CASE WHEN … THEN … END)` | **per baris**: `CASE WHEN total >= 1000000 THEN 'Besar' ELSE 'Kecil' END`, `harga * jumlah` |
| Dihitung | ulang di setiap pengelompokan → rasio tetap benar per cabang, per bulan, dan total | sekali per baris, lalu dipakai di rak, filter, hierarki |
| Disimpan sebagai | metrik dataset (dengan format: angka, ribuan, desimal, persen, mata uang) | kolom hitung dataset |

1. Isi **Nama** (huruf/angka/garis bawah), tulis **Rumus**; klik nama kolom untuk menyisipkan, atau pilih **Contoh rumus**.
2. **Uji rumus**: rumus dijalankan ke sumber dan contoh hasilnya tampil. Rumus salah menampilkan sebabnya.
3. **Simpan** → muncul di panel bertanda **ƒ**; seret ke rak. Klik kanan: **Ubah rumus…** / **Hapus definisi**.

Aturan pengaman: tanpa subquery, perintah SQL, komentar, tabel lain, atau kolom yang tidak ada; ukuran wajib beragregat,
dimensi tidak boleh; rumus selalu diuji sebelum disimpan; hanya definisi buatan Studio yang bisa diubah/dihapus di sini
(kolom asli aman); definisi yang masih dipakai chart tidak bisa dihapus atau diganti namanya. Definisi tersimpan di
**dataset**, jadi langsung tersedia di semua chart, Explore, dan untuk semua pengguna dataset itu, dengan RLS yang sama.
Kode: `config/sps_studio/definisi.py`.

### N teratas (Top N)

Kotak **N teratas** di bilah alat: isi angka (mis. 10) → hanya N baris teratas menurut urutan yang tampil; dengan
**Urutkan** naik = N terbawah. Kosongkan = semua. Ikut tersimpan ke chart.

### Kalkulasi cepat: % dari total, kumulatif & YoY

Pilihan **Hitung** di panel Marks (aktif untuk Garis/Area/Batang dengan **satu dimensi**, syarat yang sama dengan Analitik):

| Pilihan | Hasil | Contoh |
|---|---|---|
| Nilai asli | angka apa adanya | penjualan per bulan |
| **% dari total** | tiap batang/titik = porsinya terhadap jumlah semua (total 100%) | porsi tiap saluran |
| **Kumulatif (berjalan)** | nilai dijumlah terus dari kiri ke kanan; pada tanggal urut waktu, pada kategori urut terbesar (kurva Pareto) | penjualan sejak awal tahun |
| **% vs tahun lalu (YoY)** | perubahan % terhadap tanggal yang sama setahun sebelumnya; kosong bila tahun lalu tidak ada datanya. Hanya aktif bila dimensinya **kolom tanggal** | pertumbuhan Januari 2024 vs Januari 2023 |

Dihitung di server setelah kueri (bukan fungsi jendela SQL), jadi hasilnya sama di semua database sumber.
Saat disimpan memakai fitur bawaan chart Superset (*Contribution* / *Rolling cumsum* / *Time comparison 1 year ago*)
sehingga chart di dashboard sama dengan pratinjau. Chart YoY tersimpan memakai rentang waktu 30 tahun terakhir
(syarat Superset) dan serinya bernama *1 year ago*. Kode: `_kalkulasi()` di `config/sps_studio/lembar.py`.

### Skala warna tabel

Jenis **Tabel** → centang **Skala warna sel**: latar sel ukuran makin pekat untuk nilai makin besar (per kolom),
sehingga nilai tinggi/rendah langsung terlihat tanpa membaca angka. Ikut tersimpan (format bersyarat Superset).

### Kelompokkan nilai (Group)

Klik kanan sebuah **dimensi teks** → **Kelompokkan nilai…** → beri nama kelompok (mis. *Jawa*, *Luar Jawa*), pilih
kelompok untuk tiap nilai, tentukan nilai lain (*tetap* atau *gabung jadi "Lainnya"*) → **Buat dimensi**.
Hasilnya dimensi terdefinisi biasa (`CASE WHEN … END`), jadi bisa diubah lewat **Ubah rumus…** dan dipakai semua
chart. Butuh izin mengubah dataset; maksimal 4 kelompok dan 300 nilai (lebih dari itu pakai **+ Dimensi**).

### Tampilkan saya dengan banyak kolom

Jenis grafik bisa dipilih selama **kebutuhan minimalnya** terpenuhi. Kolom yang melebihi kapasitas jenis itu
**tidak dipakai**: pilnya tampil pudar dicoret dan status menulis *Tidak dipakai Pie: …* (seperti Tableau).
Urutan pemakaian: jenis berbasis waktu mendahulukan kolom tanggal, peta titik mendahulukan lintang/bujur, peta
provinsi mendahulukan kolom wilayah, jenis komposisi (Pie, Treemap, Corong) mendahulukan kategori; selebihnya
urutan rak (Kolom, Baris, Warna). Chart yang disimpan memakai kolom yang sama dengan pratinjau.

### Saran dari data

Memakai mesin Auto Chart (`sps_ai/auto.py`: tren R², konsentrasi, korelasi, k-means). Hingga 16 saran dari
berbagai jenis chart (batang, garis, treemap, peta panas, pivot, sankey, sebar, peta, …), masing-masing dengan
label jenisnya. Klik saran → rak Kolom, Baris, Warna, dan jenis chart terisi otomatis. Daftar lengkap jenis menurut
bentuk data: [10 §5](10-asisten-ai.md).

### Warna

Palet kategori 8 warna *Tinta & Sakura* (`WARNA` di `lembar.py`): pink `#E11D74` sebagai warna pertama, lalu indigo,
toska, ungu, emas, anggur, biru baja, zaitun. Lolos validator buta warna (terang & gelap: pisah ΔE 14, kontras ≥ 3:1)
dan didaftarkan ke Superset sebagai skema **"ALDx"**; peta panas memakai **"ALDx Pink"** (satu hue terang→gelap).
Dashboard versi sebelumnya ikut berganti: id skema lama tetap terdaftar, dan warna kategori dari palet lama dipetakan
ke palet baru saat `build-dashboards` / tugas malam (`sps_warna.py`); warna pilihan sendiri tidak diubah.
Warna dibagi menurut urutan kemunculan, sama seperti Superset, jadi pratinjau = hasil di dashboard.

## 2. Susun dashboard

0. **Mulai cepat: Dari template…** → pilih dataset, **ukuran utama**, dan template; ALDx memilih kolom tanggal,
   kategori (teks dengan 2–50 nilai), dan provinsi secara otomatis, membuat lembar kerjanya, lalu mengisi kanvas
   beserta filter. Periksa/ubah, lalu **Simpan dashboard**.

   | Template | Isi |
   |---|---|
   | Ringkasan eksekutif | angka utama, tren + ramalan, komposisi, 10 teratas, peta provinsi |
   | Tren & ramalan | angka utama, tren + ramalan + garis tren, kumulatif, perbandingan ukuran, tabel berskala warna |
   | Perbandingan kategori | angka utama, peringkat, % dari total, peta, peta panas, tabel berskala warna |

   Lembar kerja template tersimpan sebagai chart biasa (bisa dibuka & diubah di tab Lembar kerja). Template yang
   butuh kolom tanggal/kategori memberi pesan jelas bila dataset tidak memilikinya. Kode: `config/sps_studio/templat.py`
   (menambah template = satu entri `TEMPLAT` + satu fungsi `_susun_…`).
1. Tab **Susun dashboard** → seret lembar kerja dari kiri ke kanvas.
2. Ke **baris yang ada** = berdampingan; ke kotak **"baris baru"** = baris baru.
3. Atur lebar tiap kotak (¼ ⅓ ½ ⅔ Penuh; total satu baris ≤ penuh). Seret kotak untuk memindah.
4. Isi judul & keterangan → **Simpan dashboard**. Buka lagi lewat pilihan "Buka dashboard Studio".

Dashboard tersimpan sebagai *Draft* di Superset (publikasikan dari menu **Dashboard & Story → Daftar dashboard** bila siap).

### Objek desain: teks, gambar, garis

Panel kiri bagian **Objek** (padanan *Objects* di Tableau / Power BI). Seret ke kanvas, atau klik untuk menambah di
baris paling bawah. Kotak teks & gambar punya tombol **Atur**.

| Objek | Yang bisa diatur |
|---|---|
| **Teks** | isi (Enter = baris baru), **huruf** (10 pilihan + bawaan), ukuran 10–96 px, tebal, miring, warna teks, latar (atau tanpa latar), rata kiri/tengah/kanan, posisi tegak, tinggi kotak |
| **Gambar** | unggah PNG/JPEG/WebP/GIF (maks. 3 MB), teks alternatif, rata, *Utuh* atau *Penuhi kotak*, tinggi kotak |
| **Garis** | garis pemisah selebar dashboard; seret untuk memindah |

Pilihan huruf (berkas tersimpan lokal, jalan tanpa internet): Inter, Plus Jakarta Sans, Montserrat, Poppins,
Space Grotesk, Oswald, Playfair Display, Lora, Roboto Slab, JetBrains Mono.

Catatan:
- Objek tampil tanpa kartu putih, menyatu dengan latar dashboard; warna latar teks diatur objek itu sendiri.
- Gambar disimpan di server (tabel `sps_gambar`, ikut cadangan metadb). Alamatnya `/studio/gambar/<id>` terbuka tanpa
  login agar tampil juga di dashboard sematan; id = sidik isi berkas, tidak bisa ditebak. Jangan unggah gambar rahasia.
- SVG tidak diterima (bisa berisi skrip). Format dicek dari isi berkas, bukan dari namanya.
- Huruf dipasang lewat CSS dashboard (bagian bertanda `ALDX-HURUF`); CSS yang Anda tulis sendiri di Superset tetap utuh.

### Filter dashboard

1. **Tambah filter** → pilih dataset & kolom, nama, jenis:
   **Pilihan nilai** (dropdown, mis. Cabang), **Rentang angka** (mis. Tahun, Penjualan), atau
   **Rentang waktu** (30 hari terakhir, tanggal tertentu; berlaku untuk chart yang datasetnya punya kolom waktu).
2. **Pilih** pada chip filter menyaring pratinjau kotak di Studio (hanya untuk mencoba).
3. Saat disimpan, filter menjadi **bilah filter Superset** (panel kiri dashboard).

| Perilaku | Penjelasan |
|---|---|
| Cakupan | Berlaku untuk semua chart yang datanya punya kolom bernama sama (cara kerja Superset) |
| Klik-filter | Klik batang/irisan pada chart → chart lain ikut tersaring (cross filter, selalu aktif) |
| Filter buatan Superset | Filter yang ditambah lewat editor Superset **dipertahankan** saat Studio menyimpan ulang |
| Hak akses | Filter hanya menyempitkan; data tetap dibatasi hak akses pengguna |

## 3. Persiapan data

| Langkah | Contoh |
|---|---|
| Pilih kolom | buang kolom yang tidak perlu |
| Ganti nama | `total` → `penjualan` |
| Ubah tipe | teks / angka / tanggal |
| Bersihkan | hapus spasi tepi, HURUF BESAR, huruf kecil, isi nilai kosong |
| Filter baris | `saluran != 'Reseller'`, `tahun >= 2024`, `IN (…)` |
| Kolom hitung | `total / NULLIF(jumlah_transaksi, 0)` |
| Agregasi | jumlah per `kd_cabang, bulan` |
| **Gabung data** | `penjualan` ⟕ `cabang_ref` pada `kd_cabang` → tambah `nm_cabang` |

### Gabung data (join)

- **Cara gabung**: *Semua baris kiri* (left join) atau *Hanya yang cocok di kedua sisi* (inner join).
- **Kolom kunci**: pasangan kolom kiri = kanan (otomatis diusulkan bila namanya sama); boleh lebih dari satu.
- **Kolom diambil**: kolom dataset kanan yang ditambahkan; nama yang bentrok diberi akhiran `_2`.
- Hanya dataset di **database yang sama** (mis. sesama Oracle DMP) yang bisa digabung.

**Aksi cepat**: klik nilai di kartu profil → "Hanya nilai ini" / "Kecualikan";
tombol **Aksi** di kartu → ganti nama, buang, ubah tipe, bersihkan, saring.

SQL disusun SQLAlchemy sesuai dialek database asal (Oracle, ClickHouse, MySQL); lihat dengan **Lihat SQL**.

### Keamanan persiapan data

| Lapisan | Perilaku |
|---|---|
| Pratinjau | Data asal **sudah** dibatasi hak akses Anda (RLS) |
| Dataset baru | Mewarisi aturan `{{ sps_akses(...) }}` dataset asal; nama kolom hak akses ikut diganti bila Anda ganti nama |
| Kolom hak akses | Wajib tetap ada & tidak diubah (tipe/bersihkan). Bila dibuang/diagregasi hilang → **ditolak** |
| Rumus kolom hitung | Diperiksa `sqlglot`: tanpa subquery, perintah SQL, komentar, atau kolom/tabel lain |
| Akses dataset | Hanya role yang boleh memakai **semua** dataset asal (kiri & yang digabung) yang mendapat akses dataset baru |
| Gabung: hak akses | Dataset baru memakai hak akses **kedua sisi** (`… AND …`). Kolom hak akses kanan yang menjadi kunci gabung cukup diwakili kolom kiri (nilainya sama). Left join: baris tanpa pasangan tetap tampil, kolom kanannya kosong |
| Izin | Menyimpan butuh kemampuan **Kelola dataset** (Pusat Kendali → Hak akses) |

## 4. Izin

| Tindakan | Butuh |
|---|---|
| Membuka Studio, melihat pratinjau | Login (data tetap dibatasi hak akses) |
| Menyimpan lembar kerja | Kemampuan "Buat & simpan chart" |
| Menyimpan dashboard | "Buat & ubah dashboard" |
| Menyimpan dataset dari persiapan data | "Kelola dataset" |
| Memperbarui chart/dashboard | Pemilik atau Admin |

Menu **Studio Visual** diberikan ke Admin & role dasar pengguna (`SPS_ROLE_PENGGUNA`) oleh `scripts\build-dashboards.ps1`.

## 5. Struktur berkas

```
config/sps_studio/
├── lembar.py     spesifikasi lembar kerja, ATURAN_TANDA (23 jenis), query, -> chart Superset, WARNA
├── prediksi.py   ramalan Holt/Holt-Winters, tren, anomali (numpy)
├── ramalan.py    simpan ramalan ke ALDx Engine + RLS lingkup pembuat + penyegaran harian
├── bidang.py     panel Data: Dimensi & Ukuran
├── dasbor.py     penyusun dashboard -> position_json Superset
├── objek.py      objek desain dashboard (teks, gambar, garis), daftar HURUF, tabel sps_gambar
├── hierarki.py   hierarki dimensi per dataset (tabel sps_hierarki)
├── definisi.py   ukuran & dimensi terdefinisi (rumus -> metrik / kolom hitung dataset)
├── templat.py    template dashboard (petakan kolom -> lembar kerja -> susunan kanvas)
├── prep.py       persiapan data -> dataset virtual + warisan RLS
├── tampilan.py   halaman & API /studio/
├── halaman.html  tata letak & gaya
└── static/
    ├── umum.js     API, format angka, menu, dialog, tab
    ├── grafik.js   perender 23 jenis grafik, peta & analitik (ECharts)
    ├── indonesia.geojson  batas provinsi (lokal, tanpa internet)
    ├── lembar.js   lembar kerja (drag & drop, Tampilkan saya)
    ├── dasbor.js   penyusun dashboard
    ├── prep.js     persiapan data
    ├── huruf/      10 huruf woff2 (OFL/Apache-2.0) + huruf.css + LISENSI-*.txt
    └── echarts.min.js  ECharts 5.6.1 (Apache-2.0), disimpan lokal: tidak butuh internet
```

## 6. Masalah umum

| Gejala | Penyebab | Solusi |
|---|---|---|
| Menu Studio Visual tidak ada | Izin belum dibuat | `scripts\build-dashboards.ps1`, login ulang |
| Jenis grafik abu-abu di "Tampilkan saya" | Jumlah dimensi/ukuran tidak cocok | Arahkan kursor ke jenis itu untuk melihat kebutuhannya |
| "Simpan" memberi tautan Explore | Belum punya izin simpan chart | Pusat Kendali → Hak akses |
| "Kolom hak akses … harus tetap ada" | Kolom wilayah/cabang dibuang atau diubah di persiapan data | Pertahankan kolom tsb. tanpa diubah (boleh disembunyikan di chart) |
| "ada di database lain; gabung hanya bisa…" | Dataset kanan di koneksi berbeda | Gabung hanya sesama database; untuk lintas database minta Admin membuat view |
| Filter dashboard tidak menyaring sebuah chart | Dataset chart itu tidak punya kolom bernama sama | Samakan nama kolom (persiapan data → Ganti nama) |
| "Rumus tidak boleh …" | Rumus berisi subquery/perintah SQL | Gunakan ekspresi sederhana atas kolom yang ada |
| Saran dari data lama muncul | Sumber data lambat | Tunggu; jawaban lama otomatis diabaikan |
| "Ukuran harus memakai fungsi agregat" | rumus ukuran tanpa SUM/AVG/COUNT | bungkus dengan agregat, atau buat sebagai **Dimensi** bila memang per baris |
| "Rumus ditolak database: …" | fungsi tidak dikenal database sumber | pakai fungsi SQL database itu (mis. `ifNull` di ALDx Engine, `NVL` di Oracle) |
| Panel Analitik pudar | jenis bukan Garis/Area/Batang, atau > 1 dimensi | sisakan satu dimensi berurutan; kosongkan Warna |
| Kolom `ID_…` / `t1.ID_…` / `kode_…` ada di **Ukuran** | versi lama: awalan alias tabel hasil Kueri Visual (`t1.`) membuat ID tidak dikenali | perbarui ALDx; ID/kode kini selalu Dimensi |
| Kolom angka (mis. `total`) ada di **Dimensi**, tidak bisa dijumlah / diramal | versi lama: kolom desimal ClickHouse (`Float64`) tidak dikenali sebagai angka | perbarui ALDx ([31](31-catatan-versi.md)); bila sumber lain, set tipe kolom ke angka di Dataset › Edit › Kolom |
| Huruf objek teks tidak berubah di dashboard | CSS dashboard dihapus manual di Superset | buka dashboard di Studio › Simpan lagi (bagian `ALDX-HURUF` dibuat ulang) |
| Gambar objek: "Format gambar harus PNG, JPEG, WebP, atau GIF" | berkas SVG / format lain | ekspor ulang logo sebagai PNG |
| "butuh minimal 4 titik" | periode terlalu sedikit | perluas filter periode |
| Simpan ramalan: "ALDx Engine tidak bisa dihubungi" | container engine mati | `docker compose up -d engine`, atau simpan tanpa Ramalan |
| Status "dicocokkan lewat nama" di peta provinsi | kolom berisi nama, bukan kode ISO | ubah ke kode ISO (ID-JK) sebelum disimpan |
| Chart terlihat beda di Explore | Superset memakai pengaturan tampilannya sendiri | Rapikan di Explore; buka lagi di Studio memakai spesifikasi Studio |
