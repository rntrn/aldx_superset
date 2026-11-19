# 34 · Analisis: editor ganda (buat vs edit) & Asisten AI yang lemah mengubah aplikasi

> Status (2026-11-20): §1, Fase 0 (AI lokal), Fase 1 (ALDx Rencana) dan bagian navigasi Fase 3 (Studio satu pintu chart,
> C1–C5) dan Fase 2 (round-trip dashboard D1–D4) sudah diterapkan di versi 2026.11.20. Fase 4 juga sudah (hapus dataset sengaja tidak disediakan). Belum: D5.

---

## 0. Akar masalah dalam satu kalimat

ALDx punya **dua editor untuk objek yang sama** (Studio Visual vs editor bawaan Superset), dan keduanya
**tidak bisa saling membaca hasil yang lain secara utuh**. Asisten AI hanya punya alat **membuat** dan
**membaca**, tidak punya alat **mengubah / menghapus**, jadi permintaan seperti "tambahkan filter di dashboard
tes1 yang berlaku di semua chart" memang tidak bisa dikerjakan, sekuat apa pun modelnya.

---

## 1. Sudah diperbaiki (penyebab error 400 di panel AI)

Dari log `sps_superset` 15-11-2026 06:07–06:12:

| Gejala | Penyebab | Perbaikan |
|---|---|---|
| `Model 'qwen3.5-9b-…' mengembalikan error (400)` | Isi jawaban LM Studio: `{"error":"terminated"}`. LM Studio **memutus** permintaan saat model dibongkar/diganti. Pemicunya: (a) ringkasan dashboard 4 berjalan bersamaan dengan chat, (b) pengalihan otomatis ke model **lain di LM Studio yang sama** (`deepseek-v4.1-…`) membuat LM Studio membongkar qwen → semua permintaan qwen yang berjalan diputus. | `llm.py`: `terminated` dan `Failed to load model` sekarang dikenali sebagai galat sementara dengan pesan yang jelas (dicoba ulang / dialihkan). `agen.cadangan()`: model di server lokal yang sama ditaruh paling akhir sebagai cadangan. |
| `gemma-4-e4b tidak tersedia` lalu gagal | LM Studio gagal memuat model (`Failed to load model`, biasanya RAM/VRAM kurang). | Pesan khusus "server lokal gagal memuat model". |
| `ALDx AI: gagal mencatat audit` (berulang) | `sps_ai_log.model` = `VARCHAR(64)`, sedangkan id model lokal terdeteksi otomatis `lokal:LM Studio:qwen3.5-9b-the-defiant-…` lebih panjang → `StringDataRightTruncation`. **Audit AI hilang diam-diam.** | `agen._catat()`: `model` & `username` dipotong 64 huruf. |

Berlaku setelah `docker compose up -d` (stack sedang mati).

Masih disarankan (belum dikerjakan): kunci antre per server lokal (satu permintaan sekaligus ke LM Studio
dengan *parallel = 1*), dan ringkasan otomatis dashboard ditunda bila chat sedang berjalan.

---

## 2. Chart: "Studio Visual" vs "Chart editor" (Explore)

| # | Temuan | Lokasi | Dampak |
|---|---|---|---|
| C1 | Chart yang **tidak** dibuat di Studio ditolak Studio: *"Chart ini tidak dibuat di Studio; buka lewat Explore."* | `sps_studio/lembar.py` `buka()` (±baris 701) | Chart dari Superset, impor .ald, atau AI (jenis dasar) hanya bisa diedit di Explore → dua editor. |
| C2 | **Spesifikasi basi.** Studio menyimpan spec di `params.sps_studio`. Saat chart diubah di Explore, `params` berubah tetapi `sps_studio` tetap versi lama. | `lembar.ke_superset()` | Buka lagi di Studio = tampil versi lama; **Simpan di Studio menimpa perubahan dari Explore tanpa peringatan.** |
| C3 | Daftar chart & tombol edit selalu menuju `/explore/`. Studio hanya terjangkau lewat kartu petunjuk yang bisa ditutup permanen. | `sps_app/static/app.js` (NAV `chart`, palet perintah), `bingkai.js` PETUNJUK | Pengguna tidak tahu chart itu "milik" Studio. |
| C4 | AI `buat_chart`: jenis `angka/tabel/pie/batang/garis` → `alat.buat_chart` (tanpa spec Studio); jenis lain → pembangun Studio. **Jenis Studio + filter** (`treemap` dengan filter) dibelokkan ke `alat.buat_chart` yang hanya kenal 5 jenis → galat *"Jenis chart tidak dikenal"*. | `sps_ai/agen.py` `_jalankan_alat` cabang `buat_chart` | Chart AI kadang bisa dibuka di Studio, kadang tidak; chart Studio berfilter dari AI selalu gagal. |
| C5 | Dua pembangun params berbeda (`alat.params_chart` vs `lembar.ke_superset`) untuk jenis yang sama → tampilan, warna, batas baris berbeda antara chart AI dan chart Studio. | `alat.py`, `lembar.py` | Inkonsistensi visual. |

## 3. Dashboard: "Susun dashboard" (Studio) vs edit dashboard Superset

| # | Temuan | Lokasi | Dampak |
|---|---|---|---|
| D1 | Studio hanya mendaftar dashboard bertanda `sps_studio: true`. Dashboard dari AI (`alat.buat_dashboard`), Superset, atau impor tidak bisa dibuka di Studio. | `sps_studio/dasbor.py` `daftar()` | "Dashboard" dan "edit dashboard" terasa dua aplikasi. |
| D2 | `buka()` hanya membaca `ROW → CHART` dan markdown milik Studio. **Hilang saat dibuka di Studio**: komponen `COLUMN`, `HEADER`, markdown buatan Superset, tab bertingkat, baris di luar `TABS` bila ada tab, tinggi hasil resize di Superset (bukan 26/38/52/70/90). | `dasbor.buka()` | **Simpan dari Studio menghapus semua itu tanpa peringatan** (position_json ditulis ulang total). |
| D3 | Filter native buatan Superset tidak tampil di Studio (hanya awalan `NATIVE_FILTER-sps`). Dipertahankan, tetapi `chartsInScope`-nya tidak diperbarui → **chart yang ditambah di Studio tidak ikut terfilter** oleh filter lama. | `dasbor.simpan()` | Persis keluhan "filter tidak berlaku di semua chart". |
| D4 | Simpan Studio memaksa `color_scheme` dan `cross_filters_enabled`, menimpa pengaturan yang dibuat di editor Superset. | `dasbor.simpan()` `meta` | Warna/perilaku berubah sendiri setelah disimpan di Studio. |
| D5 | Filter global (`sps_filter_global.py`) hanya berlaku pada kolom yang **sudah punya filter native** di dashboard itu; tidak ada jalur (UI ringkas maupun AI) untuk menambahkannya dari halaman dashboard. | `sps_filter_global.native_filters()` | Filter global terlihat "tidak berfungsi" di dashboard tanpa filter native. |

## 4. Asisten AI: kenapa "bingung harus ngapain"

| # | Temuan | Dampak |
|---|---|---|
| A1 | Alat analis (13) hanya `cari/info/ambil/buat`. **Tidak ada**: ubah chart, hapus, tambah/ubah filter dashboard, ubah tata letak, ubah/hapus dataset, kelola story. | Permintaan edit tidak mungkin berhasil. Model kecil lalu mengarang jawaban atau membuat objek baru. |
| A2 | Instruksi sistem + katalog isi aplikasi + 13 skema alat panjang → model 7–9B kehabisan "perhatian"; sering salah id/argumen (sudah ditambal `rapikan_argumen`). | Kualitas turun tajam pada model lokal. |
| A3 | Satu putaran = model harus merencanakan **dan** mengisi argumen teknis (id, nama kolom persis, jenis viz). | Beban terlalu besar untuk model kecil. |

---

## 5. Rancangan: "ALDx Rencana" — perantara yang dipahami AI dan aplikasi

Ide pengguna: semua perubahan lewat berkas `.ald/.aldx` yang diekstrak, diolah, disimpan, lalu dihapus.
Catatan penting: **`.ald/.aldx` sudah ada** (`config/sps_berkas`) sebagai paket ekspor terenkripsi berisi YAML
ekspor resmi Superset. Memakainya langsung sebagai bahan yang *ditulis* AI **tidak disarankan**:
YAML Superset (position_json, params, native filter) besar dan rapuh — model 9B hampir pasti merusaknya.

Yang dipertahankan dari ide itu (dan memang tepat): **satu bahasa perantara + konfirmasi + simpan otomatis
+ salinan sementara yang dibuang per sesi.** Bentuknya dibuat tiga lapis:

```
Prompt pengguna
   │
   ▼  (1) Penerjemah niat  ── pola umum dikenali TANPA LLM (regex/kamus):
   │        "tambah filter X di dashboard Y", "ganti chart Z jadi batang", "hapus chart", "ganti judul"
   │      ── sisanya: LLM hanya mengisi SLOT kecil, bukan JSON teknis
   ▼
ALDx Rencana  (daftar operasi semantik, kecil, tervalidasi skema)
   [{"op":"tambah_filter","dashboard":"tes1","kolom":"cabang","jenis":"pilihan","semua_chart":true},
    {"op":"ubah_chart","chart":"Penjualan per cabang","jenis":"batang"}]
   │
   ▼  (2) Resolver  ── nama → id (fuzzy, dari katalog yang boleh diakses), kolom → kolom sah per dataset,
   │                 hak akses dicek, konflik dicari.  Galat → pertanyaan balik yang spesifik ke pengguna.
   ▼
Pratinjau perubahan (diff yang bisa dibaca manusia)  →  tombol "Simpan perubahan" / "Batal"
   │
   ▼  (3) Kompiler deterministik  ── memakai kode yang SUDAH ADA: dasbor.filter_native(), lembar.ke_superset(),
   │                                 dasbor.posisi(), perintah Superset Update/Delete*Command
   ▼
Simpan ke metadb  +  snapshot "sebelum" (.ald sementara, per sesi) untuk tombol "Urungkan"
                     → dihapus otomatis saat sesi chat berakhir / 24 jam; bisa diunduh bila diizinkan
```

Kenapa ini membuat AI lemah jadi cukup kuat:

1. **Model hanya memilih operasi dari menu kecil** (±15 `op`) dan mengisi nama dalam bahasa manusia.
   Tidak ada id, tidak ada JSON Superset. Satu alat saja: `rencanakan(operasi[])`.
2. **Sebagian besar prompt harian tidak butuh LLM sama sekali** — penerjemah niat menangkapnya duluan
   (lebih cepat, tidak bergantung model, tidak bisa "error 400").
3. **Validasi & penyelesaian nama di server**, bukan di model. Ambigu → AI bertanya balik
   ("Ada 2 dashboard bernama tes1…").
4. **Aman**: tidak ada yang tersimpan sebelum pengguna menekan Simpan; setiap rencana bisa diurungkan;
   semua lewat izin pengguna (RLS/ownership) dan tercatat di jejak audit.

Daftar operasi awal (cukup untuk hampir semua permintaan aplikasi):

| Objek | Operasi |
|---|---|
| Dashboard | `buat`, `ganti_judul`, `tambah_chart`, `buang_chart`, `atur_lebar`, `tambah_tab`, `tambah_filter`, `ubah_filter`, `hapus_filter`, `hapus` |
| Chart | `buat`, `ubah_jenis`, `ubah_metrik`, `ubah_kelompok`, `tambah_filter`, `ganti_judul`, `duplikat`, `hapus` |
| Dataset | `daftarkan_tabel`, `gabung`, `tambah_kolom_hitung`, `tambah_metrik`, `ganti_nama_kolom`, `hapus` |
| Story | `buat`, `tambah_langkah`, `urutkan`, `tulis_narasi`, `hapus` |

---

## 6. Rancangan: satu editor ("Studio Visual" sebagai editor utama)

1. **Satu model kanonik = objek Superset**, spec Studio hanya turunan. Simpan sidik `sps_studio_sidik`
   (hash params saat disimpan Studio). Saat dibuka, sidik ≠ hash params sekarang → spec dibangun ulang
   dari params (pemetaan balik viz → lembar untuk jenis yang didukung), atau Studio memberi peringatan
   *"diubah di editor lanjutan"* dan tidak menimpa diam-diam. (C2)
2. **Studio bisa membuka semua chart**: jenis yang punya pemetaan balik → lembar kerja; sisanya dibuka di
   tab **"Mode lanjutan"** di dalam Studio (Explore tersemat), jadi pengguna tetap di satu menu. (C1)
3. **Semua tombol "Edit"** (daftar chart, menu chart di dashboard, palet perintah) diarahkan ke
   `/studio/?chart=<id>`. Explore tetap ada hanya sebagai "Mode lanjutan". (C3)
4. **AI memakai pembangun Studio untuk semua jenis** (hapus cabang `alat.buat_chart` untuk chart baru). (C4, C5)
5. **Dashboard round-trip tanpa kehilangan**: `buka()` membawa komponen yang tidak dikenali Studio sebagai
   "kotak terkunci" (passthrough) dan `simpan()` menulisnya kembali apa adanya; tinggi bebas dipertahankan;
   `color_scheme`/`cross_filters_enabled` hanya ditulis bila diubah di Studio. (D2, D4)
6. **Filter**: semua filter native tampil & bisa diedit di Studio; `chartsInScope` dihitung ulang tiap simpan
   untuk semua filter berlingkup ROOT. (D3) Tombol "Tambah filter untuk semua chart" di halaman dashboard
   memakai operasi rencana `tambah_filter`. (D5)
7. Studio mendaftar **semua** dashboard yang boleh diedit pengguna, bukan hanya `sps_studio`. (D1)

---

## 7. Urutan pengerjaan yang disarankan

| Fase | Isi | Hasil yang terasa |
|---|---|---|
| 1 | Operasi rencana **dashboard filter** + **ubah chart** + pratinjau/simpan/urungkan di panel AI; penerjemah niat untuk pola itu | Prompt "buatkan filter yang berlaku di semua chart" langsung jalan, bahkan dengan model 7B |
| 2 | Perbaiki round-trip dashboard Studio (D1–D4) | Edit di Studio tidak lagi menghapus isi dari editor lain |
| 3 | Studio sebagai editor tunggal chart (C1–C5) | Satu menu untuk buat & edit |
| 4 | Sisa operasi (dataset, story, hapus) + snapshot .ald sementara yang bisa diunduh | AI menangani hampir semua prompt pengelolaan aplikasi |
