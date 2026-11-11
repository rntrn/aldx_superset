# 09 · Identitas & Tema (white-label)

Nama aplikasi, nama perusahaan, logo, ikon tab, warna, huruf, motif hiasan, dan animasi
**bisa diganti kapan saja tanpa restart**. Berlaku untuk semua halaman: login, dashboard,
Studio Visual, Asisten AI, Pusat Kendali.

| Cara | Kapan |
|---|---|
| **Pusat Kendali → Identitas & Tema** | sehari-hari (disarankan) |
| Halaman **Identitas** di `PASANG.cmd` | saat instalasi pertama |
| `.env` (`SPS_PRESET`, `SPS_NAMA_APLIKASI`, …) | isi awal otomatis (lihat §5) |

---

## 1. Mengubah lewat Pusat Kendali

![Identitas & Tema](gambar/tutorial/l4-08-identitas.png)

1. Login sebagai Admin → **Settings → Pusat Kendali Server** → tab **Identitas & Tema**.
2. **(1) Preset cepat**: satu klik mengganti warna & motif (lihat §3). Preset langsung tersimpan.
3. **(2)** Ubah isian; baris yang diubah ditandai kuning. **(3) Pratinjau** di kanan ikut berubah.
4. **Simpan**. Pengguna lain melihat perubahan dalam ±1 menit (cukup muat ulang halaman).

Setiap perubahan tercatat di tab **Riwayat** (siapa, kapan, nilai lama/baru).

## 2. Daftar isian

| Kelompok | Isian | Keterangan |
|---|---|---|
| Nama & teks | Nama aplikasi | judul tab browser, navbar, login (maks 40 huruf) |
| | Nama perusahaan / instansi | login, kaki halaman, Asisten AI. Boleh kosong: login & kaki halaman memakai nama aplikasi |
| | Slogan, Sapaan login, Teks kaki | teks di halaman login; `{tahun}` & `{perusahaan}` diganti otomatis |
| | Halaman pertama setelah login | bawaan `/app/` (Beranda); bisa juga `/superset/dashboard/latihan/`. Bila dashboard tujuannya belum ada (mis. `beranda` profil DJP sebelum koneksi Oracle DMP dibuat), pengguna diarahkan ke daftar dashboard |
| Warna | Warna utama | navbar, tombol, header |
| | Warna aksen | garis hiasan, sorotan, tab aktif |
| | Warna latar halaman | latar belakang |
| Tampilan & animasi | Huruf | Plus Jakarta Sans, Sistem (Segoe UI), Klasik (Georgia) — disimpan lokal, tanpa internet |
| | Sudut | lembut, tegas, bulat |
| | Motif hiasan | gelombang, titik, garis, polos |
| | Animasi halus | latar login bergerak, garis aksen mengalir, chart muncul perlahan |
| Logo & ikon | Logo (latar terang), Logo (latar gelap), Ikon tab | unggah PNG/SVG/JPG/WebP maks 1 MB; **kosong = dibuat otomatis** dari nama & warna |

Warna teks di atas warna utama (hitam/putih) dipilih otomatis agar tetap terbaca.
Animasi **otomatis mati** bagi pengguna yang mengaktifkan *Kurangi gerakan / Show animations: off*
di Windows (aturan aksesibilitas `prefers-reduced-motion`).

## 3. Preset

| Preset | Warna utama / aksen | Motif |
|---|---|---|
| `netral` | biru `#1F4E79` / jingga `#F2A900` | gelombang — juga **mengembalikan semua isian ke bawaan** |
| `hijau` | `#0F6E56` / `#F4B400` | titik |
| `marun` | `#7A1F2B` / `#E0A100` | garis |
| `ungu` | `#4B2E83` / `#19B5A5` | gelombang |
| `grafit` | `#263238` / `#26A69A` | titik |
| `djp` | navy `#1F2F5F` / emas `#F2B705` | gelombang; nama, logo & halaman depan DJP |

Preset selain `netral` dan `djp` hanya mengganti warna & motif; nama dan logo Anda tetap.

Logo resmi DJP **tidak disertakan** di repo (merek milik instansi). Preset `djp` mencari `logo-djp.png`,
`logo-djp-putih.png`, dan `favicon-djp-32.png` di folder `branding\`; bila tidak ada, logo dibuat otomatis
dari nama & warna. Instalasi DJP cukup menyalin berkas logo resmi ke `branding\` (diabaikan git) atau
mengunggahnya di tab ini.
Menambah preset: satu entri di `PRESET` dalam `config\sps_identitas\skema.py`.

## 4. Halaman login beranimasi

Halaman `/login/` memakai identitas di atas: panggung warna yang bergerak perlahan, motif hiasan,
dan contoh grafik "hidup". Keamanan tidak berubah: formulir tetap dikirim ke Superset (LDAP / akun
lokal, CSRF, batas percobaan). Pesan galat berbahasa Indonesia.

Bila tampilan bermasalah (mis. browser sangat lama), buka **`/login/?klasik=1`** untuk halaman login bawaan Superset.

## 5. Isi awal dari `.env` (instalasi)

Dibaca **sekali** oleh `scripts\build-dashboards.ps1` bila database belum punya identitas, atau bila
`SPS_IDENTITAS_TERAPKAN=1` (diisi installer saat halaman Identitas diubah).

| Variabel | Contoh |
|---|---|
| `SPS_PRESET` | `netral`, `hijau`, `marun`, `ungu`, `grafit`, `djp` |
| `SPS_NAMA_APLIKASI` | `Analitik Penjualan` |
| `SPS_NAMA_PERUSAHAAN` | `PT Contoh Sejahtera` |
| `SPS_LOGO` | nama berkas di folder `branding\`, mis. `logo-kustom.png` |
| `SPS_HALAMAN_DEPAN` | `/superset/dashboard/latihan/` |

Setelah terpasang, ubah lewat Pusat Kendali (nilai `.env` tidak menimpa lagi).

## 6. Cara kerja (untuk pengembang)

```
Pusat Kendali ─► /identitas/api ─► tabel sps_identitas (+ sps_identitas_berkas) di metadb
                                      │  versi berubah
setiap node, tiap ±10 detik  ◄────────┘
   └─► APP_NAME, APP_ICON, FAVICONS, THEME_DEFAULT (token warna & huruf Superset)
   └─► /identitas/tema.css  (variabel CSS, hiasan, animasi) disisipkan ke semua halaman
   └─► /identitas/berkas/<logo|logo_putih|favicon|spinner>
```
Modul: `config\sps_identitas\` (urutan baca di docstring `__init__.py`).

## 7. Masalah umum

| Gejala | Solusi |
|---|---|
| Logo/warna belum berubah | tunggu 1 menit lalu Ctrl+F5 |
| Unggah logo ditolak | maks 1 MB, format PNG/SVG/JPG/WebP/ICO |
| Halaman login polos tanpa animasi | Windows "kurangi gerakan" aktif, atau isian *Animasi halus* dimatikan |
| Tampilan login rusak | pakai `/login/?klasik=1`, laporkan ke admin |
| Ingin kembali ke awal | preset **Netral** |
