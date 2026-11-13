# 23 · Asisten AI di Setiap Halaman (Peran Ahli)

Asisten AI kini ada di **semua halaman**: panel di sisi kanan. Pilih **peran ahli**
sesuai pekerjaan: analis data, pemandu aplikasi, data engineer, ahli UI/UX, atau HW engineer.

![Panel Asisten AI](gambar/app/a10-panel-ai.png)

## 1. Membuka panel

| Cara | Keterangan |
|---|---|
| Tombol **✦** di bilah atas | muncul bila Anda boleh memakai Asisten AI. Belum ada model aktif? Panel menampilkan layar **Sambungkan AI** ([28](28-sambungkan-asisten-ai.md)) |
| Tombol cepat di dashboard | saat sebuah dashboard terbuka, panel menawarkan **Ringkas dashboard ini dalam 5 poin** dan *Apa yang janggal atau perlu ditindaklanjuti…*: satu klik, jawaban memakai isi dashboard yang sedang tampil |
| Ikon **sambung** (🔗) di kepala panel | buka layar Sambungkan AI: status model lokal, key cloud (Admin) |
| `Ctrl + I` | buka / tutup panel (juga saat kursor ada di dalam halaman) |
| Beranda › **Tanya AI** | pertanyaan dari kotak Cari langsung dikirim ke panel |

Di layar lebar (≥ 1280 px) panel menempel di kanan dan halaman menyempit. Di laptop kecil panel melayang,
di ponsel panel memenuhi layar.

## 1b. Asisten paham isi aplikasi & halaman yang dibuka

Asisten tidak perlu diberi tahu nama tabel atau id. Setiap pertanyaan otomatis disertai:

| Yang diketahui | Isinya | Contoh pertanyaan |
|---|---|---|
| **Peta isi aplikasi** | dataset (kolom & metrik utama), dashboard (chart di dalamnya), chart lain; **hanya yang boleh Anda akses** | dari Beranda: *"Cabang mana yang penjualannya paling tinggi?"* |
| **Halaman yang sedang dibuka** | dashboard: semua chart, metrik, pengelompokan, filter, **beserta angkanya**; chart: rinciannya & angkanya; dataset: kolomnya | di dashboard: *"Jelaskan dashboard ini dan temuan utamanya"* |
| **Teks di layar** | potongan tulisan yang tampil di halaman (maks. ±2.000 huruf) | *"Apa arti angka di kartu kanan atas?"* |

Alat tambahan peran `/analis`: **info_dashboard**, **info_chart**, dan **data_chart** (menjalankan ulang query
chart dengan hak akses Anda).

**Privasi.** Angka chart dan teks layar hanya dikirim ke model yang boleh menerima data (`kirim_data: true`,
bawaan untuk model lokal). Model cloud (`kirim_data: false`) hanya menerima nama dataset, kolom, dan judul chart,
lalu angkanya ditampilkan langsung ke Anda tanpa lewat model.

**Kecepatan.** Model lokal kecil (4B) tanpa GPU butuh ±1–3 menit untuk pertanyaan yang memakai beberapa alat. Di halaman
dashboard, angka sudah disertakan sehingga biasanya cukup satu langkah. Untuk jawaban cepat, pakai model 8B+ dengan GPU atau
layanan cloud ([28](28-sambungkan-asisten-ai.md)). Bila sering melewati batas waktu, naikkan `batas_detik_lokal` (model lokal, bawaan 240 dtk)
atau `batas_detik_model` (cloud, 120 dtk) di `config\ai.yaml`.

## 2. Peran ahli

Pilih dengan **chip** di atas obrolan, atau ketik **`/`** lalu nama peran (panah ↑ ↓, `Enter`).

![Pilih peran dengan /](gambar/app/a11-perintah-peran.png)

| Perintah | Peran | Bisa apa | Siapa |
|---|---|---|---|
| `/analis` | Analis data | tanya data, ambil angka, buat chart & dashboard, **gabung dataset** menjadi satu dataset detail | semua pengguna Asisten AI |
| `/panduan` | Pemandu aplikasi | menjelaskan cara memakai menu & pintasan (dari isi panel **?**) | semua pengguna Asisten AI |
| `/data-engineer` | Data engineer | dataset, koneksi, ekstrak, batas data, menulis SQL sesuai dialek, cek kualitas data | Analis (SQL Lab) atau Admin |
| `/ahli-ui-ux` | Ahli UI/UX | menilai & mengusulkan warna, huruf, tema; cek kontras WCAG | Admin |
| `/hw-engineer` | HW engineer | membaca status CPU/RAM/proses/cache, mengusulkan pengaturan server | Superadmin |

Peran yang tidak boleh untuk akun Anda tidak tampil. Bila panel dibuka di halaman tertentu, peran awalnya
menyesuaikan: Pusat Kendali › Status/Pengaturan/Batas data → `/hw-engineer`; Identitas & Tema → `/ahli-ui-ux`;
Dataset, Hubungkan data, Ekstrak, Kueri Visual, SQL Lab, Persiapan data → `/data-engineer`; selain itu `/analis`.

Contoh: `/hw-engineer server terasa lambat, apa yang perlu diubah?`

**Gabung dataset (denormal/detail):** mis. *"dari latihan_penjualan, latihan_cabang, latihan_lokasi_pelanggan buatkan
dataset detail"*. Asisten mencari kolom penghubung (mis. `kd_cabang`), menjadikan tabel transaksi sebagai dataset utama,
lalu LEFT JOIN tabel lain. Tabel yang hubungannya **banyak-ke-banyak** (kunci tidak unik di kedua sisi, mis. penjualan ×
pelanggan per cabang) **dilewati dengan penjelasan**, karena baris akan berlipat dan semua SUM/COUNT salah. Hak akses
data (RLS) semua dataset asal ikut terbawa. Butuh izin membuat dataset. Kode: `config/sps_ai/gabung.py`.

**Andal di semua jenis model (lokal, gratis, berbayar):**

| Situasi | Yang dilakukan ALDx |
|---|---|
| Penyedia sibuk / kuota habis (HTTP 429, 5xx, mis. *Gemini 503*), jaringan putus | dicoba ulang 2× (jeda 2 & 6 detik), lalu **beralih otomatis ke model aktif lain**; jawaban menulis *"Dijawab dengan … karena … sedang tidak tersedia"* dan pilihan model ikut berganti |
| Privasi saat beralih | bila model awal sudah menerima data, cadangannya harus model yang juga boleh menerima data, atau model lokal. Tidak pernah berpindah ke model "tanpa data" dengan riwayat berisi angka |
| Model lokal kecil menulis pemanggilan alat sebagai teks (`<tool_call>…</tool_call>` atau blok JSON) | dibaca sebagai pemanggilan alat resmi (hanya alat yang memang ditawarkan) |
| Model menulis nama dataset alih-alih id (`"latihan_penjualan"`), atau daftar sebagai teks | dirapikan otomatis sebelum alat dijalankan |
| Galat lain | pesan yang bisa ditindaklanjuti: key salah (401/403), kuota (429), nama model berganti (404), server penyedia sibuk (5xx) |

Mematikan pengalihan otomatis: `cadangan_otomatis: false` di `config\ai.yaml`.

**Menyesuaikan diri dengan model apa pun:**

| Jenis model | Penyesuaian otomatis |
|---|---|
| Model "bernalar" (qwen3, deepseek-r1, …) yang menulis `<think>…</think>` | proses berpikirnya dibuang, hanya jawaban akhir yang tampil |
| Model / penyedia tanpa *function calling* (menolak `tools`) | beralih ke **mode teks**: daftar alat dijelaskan di instruksi, pemanggilan dibaca dari jawaban; diingat per model |
| Model berkonteks kecil (galat *context length*) | instruksi diringkas (tanpa katalog isi aplikasi, 6 pesan terakhir, hasil alat dipotong) lalu dicoba lagi |
| Model kecil yang salah menulis argumen | nama dataset → id, daftar teks → daftar, JSON rusak → diminta tulis ulang |

**Keamanan Asisten AI:**

| Lapisan | Perilaku |
|---|---|
| Hak akses | semua alat berjalan **sebagai pengguna yang bertanya** (RLS, izin dataset/dashboard/database berlaku) |
| Instruksi tersembunyi di data (*prompt injection*) | instruksi sistem menegaskan isi hasil alat, kolom, dashboard, dan halaman adalah DATA, bukan perintah; pada mode teks hasil alat diberi label "data, bukan perintah" |
| Rahasia | API key model & variabel rahasia server disamarkan (••••••) bila muncul di jawaban, apa pun kata modelnya; alat tidak pernah mengirim alamat/password koneksi |
| Data ke model cloud | hanya bila `kirim_data` model itu diizinkan; pengalihan ke model cadangan tidak pernah melanggar aturan ini |
| Batas pembuatan | maks. **12 objek baru** (chart/dashboard/dataset) per pertanyaan |
| Batas pemakaian | maks. **60 pertanyaan per pengguna per jam** (`batas_pertanyaan_per_jam`; Admin tidak dibatasi) untuk melindungi biaya model berbayar |
| Tampilan | jawaban di-escape sebelum tampil (tidak ada HTML/skrip/tautan dari model); tabel markdown dirender aman |
| Jejak | setiap pertanyaan tercatat (pengguna, model yang menjawab, alat, status) di log Asisten AI |

**Terintegrasi dengan ALDx:** dataset, chart, dan dashboard yang dibuat Asisten tampil sebagai tautan di bawah
jawaban (dataset juga punya tombol **Buka di Studio Visual**). Di bawah jawaban muncul **tombol langkah berikutnya**
(mis. *Buat dashboard ringkasan dari dataset ini*, *Daftarkan tabel-tabel itu sebagai dataset*); satu klik = kirim.

**Tabel database, bukan hanya dataset:** *"scan di sps_engine seluruh tabel berawalan data_penerbangan"* → alat
**cari_tabel** (nama, jumlah baris, kolom, sudah/belum jadi dataset) → *"daftarkan semuanya"* → **daftarkan_tabel**.
Melihat tabel mentah butuh akses ke database itu (Admin atau role dengan akses database); pengguna lain hanya
melihat tabel yang sudah menjadi dataset yang boleh ia akses. Kode: `config/sps_ai/tabel_db.py`.

**Progres langsung & Batalkan:** pertanyaan berjalan di latar belakang server. Selama menunggu, panel menampilkan
waktu berjalan dan setiap langkah yang selesai (*Mencari dataset ✓, Menggabung dataset ✓*). Tombol **Batalkan**
menghentikan Asisten setelah langkah yang sedang berjalan; chart/dataset yang sudah dibuat tetap tersimpan.

**Batas waktu:** satu pertanyaan maksimal **15 menit** (`batas_latar_detik` di `config\ai.yaml`, 60–3600), satu langkah
model maksimal 240 detik untuk model lokal. Bila model belum selesai, Asisten berhenti dengan rapi dan menyebut langkah
yang sudah selesai. Model lokal kecil di CPU tetap lambat untuk permintaan bertahap; pakai model yang lebih kuat atau
pecah permintaan. (Mode latar butuh Redis, yang selalu ada di instalasi standar; tanpa Redis panel memakai cara lama
dengan batas ±5 menit.)

## 3. Usulan & tombol Terapkan

Peran yang bisa mengubah sesuatu (`/ahli-ui-ux`, `/hw-engineer`) **tidak pernah mengubah sendiri**. Peran itu
membuat **kartu usulan**: nilai lama → nilai baru, alasan, dan (untuk tema) hasil cek kontras.

| Usulan pengaturan server | Usulan tema |
|---|---|
| ![](gambar/app/a12-usulan-server.png) | ![](gambar/app/a13-usulan-tema.png) |

- **Terapkan** mengirim perubahan lewat API yang sama dengan Pusat Kendali, jadi hak akses Anda diperiksa lagi.
- **Abaikan** = tidak ada yang berubah.
- Pengaturan berlabel *perlu diterapkan* baru aktif setelah `scripts\terapkan-server.ps1` (restart container).
- Cek kontras: teks ≥ 4,5 : 1 (WCAG AA); elemen non-teks seperti sorotan & garis fokus ≥ 3 : 1.
- Setiap perubahan tercatat di Pusat Kendali › **Riwayat** atas nama Anda.

## 4. Keamanan & privasi

| Aturan | Cara |
|---|---|
| Hak akses tetap berlaku | semua alat berjalan sebagai pengguna yang login; data tetap disaring RLS |
| Alat dibatasi per peran | model hanya diberi alat milik peran itu; alat lain ditolak server |
| Model cloud tanpa data | `kirim_data: false` di `config/ai.yaml`: angka hasil kueri tidak dikirim ke model, hanya tampil di layar |
| Konfigurasi, bukan data bisnis | `/ahli-ui-ux` & `/hw-engineer` hanya membaca tema & pengaturan server, bukan data bisnis/pribadi |
| Tanpa rahasia | password, API key, dan `.env` tidak pernah dibaca alat mana pun |
| Audit | setiap pertanyaan tercatat di tabel `sps_ai_log` dengan awalan peran, mis. `[/hw-engineer] ...` |

## 5. Untuk pengembang

| Berkas | Isi |
|---|---|
| `config/sps_ai/peran.py` | daftar `PERAN` (id, nama, syarat, alat, instruksi) + alat ahli & pelaksananya |
| `config/sps_ai/agen.py` | putaran agen; instruksi umum + instruksi peran; alat dipilih per peran |
| `config/sps_ai/tampilan.py` | `GET /asisten/api/peran`, `POST /asisten/api/chat {riwayat, peran, konteks, model}` |
| `config/sps_app/static/ai.js` | panel di cangkang: chip peran, saran `/`, kartu usulan, tabel dengan tombol Ekspor |

Menambah peran: tambah satu `Peran(...)` di `PERAN`, tulis definisi alatnya di `ALAT_AHLI` dan pelaksananya di
`jalankan()`, lalu tambahkan teksnya di `config/sps_app/terjemahan.py` (EN/JA). Uji otomatis
"Peran Asisten AI & alatnya lengkap" memastikan semua alat peran terdaftar.

Halaman **Asisten AI** lama (`/asisten/`, dengan tab Auto Chart & Story) tetap ada untuk pekerjaan panjang.
Lihat juga [10-asisten-ai.md](10-asisten-ai.md) (memasang model, `ai.yaml`) dan [20-model-ai-lokal.md](20-model-ai-lokal.md).
