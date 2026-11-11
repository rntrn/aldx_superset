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

Ramalan (Holt-Winters, pita 80/95%), garis tren (R²), dan tanda anomali untuk Garis/Area/Batang
dengan satu dimensi berurutan. Penjelasan: [17 bagian 4](17-katalog-chart-peta-prediksi.md#4-analitik-prediktif).

### Hierarki dimensi (telusur bertingkat)

Beberapa kolom bertingkat dipakai seperti **satu kolom**, mis. *Wilayah* = provinsi › kabupaten › kecamatan › kelurahan.

| Langkah | Cara |
|---|---|
| Buat | Panel Data → **Hierarki → ＋**, beri nama, centang kolom **berurutan dari yang paling umum** (2–8 level). Atau menu pil → *Buat hierarki dari kolom ini…* |
| Pakai | Seret/dobel klik hierarki ke rak. Tampil di level teratas (teragregasi). |
| Masuk ke satu nilai | **Klik** batang/titik/wilayah di chart → level berikutnya, difilter ke nilai itu (jalur tampil di pil, mis. `ID-JK › kategori`). |
| Turun / naik level | Tombol **▸** (level berikutnya, semua nilai) dan **◂** (kembali satu level) di pil. |
| Hapus | Tombol 🗑 di daftar Hierarki. |

- Disimpan **per dataset di server** (tabel `sps_hierarki`), dipakai semua orang yang boleh membuka dataset itu.
  Membuat/menghapus butuh izin membuat chart (Alpha/Admin).
- Chart yang disimpan memakai **level yang sedang tampil** (beserta filter jalurnya).
- API: `GET/POST /studio/api/hierarki/<dataset_id>`, `POST /studio/api/hierarki/<dataset_id>/hapus`
  (modul `config/sps_studio/hierarki.py`).

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

1. Tab **Susun dashboard** → seret lembar kerja dari kiri ke kanvas.
2. Ke **baris yang ada** = berdampingan; ke kotak **"baris baru"** = baris baru.
3. Atur lebar tiap kotak (¼ ⅓ ½ ⅔ Penuh; total satu baris ≤ penuh). Seret kotak untuk memindah.
4. Isi judul & keterangan → **Simpan dashboard**. Buka lagi lewat pilihan "Buka dashboard Studio".

Dashboard tersimpan sebagai *Draft* di Superset (publikasikan dari menu **Dashboard & Story → Daftar dashboard** bila siap).

### Filter dashboard

1. **Tambah filter** → pilih dataset & kolom, nama, jenis:
   **Pilihan nilai** (dropdown, mis. Cabang) atau **Rentang angka** (mis. Penjualan).
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
| Panel Analitik pudar | jenis bukan Garis/Area/Batang, atau > 1 dimensi | sisakan satu dimensi berurutan; kosongkan Warna |
| "butuh minimal 4 titik" | periode terlalu sedikit | perluas filter periode |
| Simpan ramalan: "ALDx Engine tidak bisa dihubungi" | container engine mati | `docker compose up -d engine`, atau simpan tanpa Ramalan |
| Status "dicocokkan lewat nama" di peta provinsi | kolom berisi nama, bukan kode ISO | ubah ke kode ISO (ID-JK) sebelum disimpan |
| Chart terlihat beda di Explore | Superset memakai pengaturan tampilannya sendiri | Rapikan di Explore; buka lagi di Studio memakai spesifikasi Studio |
