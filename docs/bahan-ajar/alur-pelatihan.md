# Alur Pelatihan ALDx

Panduan **menyelenggarakan pelatihan dari awal sampai tindak lanjut**: siapa belajar apa, kapan, bagaimana dinilai,
dan menu mana yang tercakup di sesi mana. Isi tiap sesi ada di modul per level (lihat [ringkasan](README.md)).

## 1. Gambaran alur

```text
 Persiapan (H-3)  →  Level 1  →  Level 2  →  Level 3  →  Level 4  →  Tindak lanjut (30 / 60 / 90 hari)
  data latihan,       semua       pembuat      pengelola    tim TI        klinik tanya-jawab,
  akun, uji           pengguna    laporan      data                       laporan penggunaan
```

| Level | Peserta | Durasi | Kelas | Prasyarat | Hasil akhir (bukti) |
|---|---|---|---|---|---|
| 1 · Pengguna | semua pengguna | 90 menit (+15 modul tambahan) | 30 | akun login | kuis ≥ 70% + daftar periksa L1 |
| 2 · Analis | pembuat laporan | 2 × 120 menit | 20 | lulus L1 | dashboard *Latihan – [nama]* + kuis ≥ 70% |
| 3 · Admin data | pengelola data | 2 × 120 menit | 12 | lulus L2 | dataset gabungan + aturan RLS teruji |
| 4 · Admin server | tim TI | 2 × 150 menit | 8 | lulus L1, paham L3 (RLS) | cadangan-pulih berhasil + uji 100% lulus |
| Runbook | petugas jaga | 150 menit | 8 | L4 | simulasi gangguan selesai tepat waktu |

## 2. Kalender contoh

**Program reguler (2 minggu)**

| Hari | Kegiatan | Peserta |
|---|---|---|
| H-3 | persiapan: data latihan, akun, uji ([README](README.md#persiapan-umum-h-3)) | admin server + pengajar |
| Minggu 1 · Sen | **Level 1** + modul tambahan | semua |
| Minggu 1 · Rab | **Level 2** sesi 1 (Studio, chart, peta) | analis |
| Minggu 1 · Kam | **Level 2** sesi 2 (ramalan, dashboard, Kueri Visual, laporan terjadwal) | analis |
| Minggu 2 · Sen | **Level 3** sesi 1 (hubungkan data, dataset, persiapan data) | admin data |
| Minggu 2 · Rab | **Level 3** sesi 2 (RLS, ekstrak, Asisten AI untuk data) | admin data |
| Minggu 2 · Kam | **Level 4** sesi 1 (pasang, pantau, pengaturan, keamanan) | tim TI |
| Minggu 2 · Jum | **Level 4** sesi 2 (cadangan, upgrade, gangguan) + runbook | tim TI |
| H+30 | klinik tanya-jawab 60 menit | semua |

**Intensif 1 hari per peran** (bila waktu terbatas)

| Peran | Susunan |
|---|---|
| Pengguna | L1 (90 menit) + modul tambahan (15 menit) |
| Analis | L1 ringkas (30 menit, hanya §6e) → L2 sesi 1 dan 2 berurutan dengan istirahat 30 menit |
| Admin data | L2 §12 (Kueri Visual) + L3 sesi 1 dan 2 |
| Tim TI | L4 sesi 1 dan 2 + runbook |

## 3. Persiapan lingkungan

| Siapa | Apa | Bukti siap |
|---|---|---|
| Admin server | `scripts\data-latihan.ps1` (data latihan lengkap), `scripts\uji.ps1` | semua uji LULUS |
| Admin server | akun peserta per peran (Pengguna / Analis / Admin) + akun uji cabang `-AkunUji` untuk latihan RLS | tiap peserta bisa login |
| Admin server | **Email (SMTP)** bila Langganan laporan & Peringatan data akan dipraktikkan; tanpa SMTP hanya tercatat di log | email uji diterima |
| Admin server | model AI aktif (lokal atau cloud gratis) agar sesi Asisten AI berjalan; siapkan **dua model** untuk demo model cadangan | panel ✦ menjawab |
| Pengajar | coba semua latihan dengan akun peserta; cetak [peta menu](../33-peta-menu-per-level.md) | kunci jawaban cocok |
| Panitia | semua komputer peserta bisa membuka alamat aplikasi; proyektor; jaringan/VPN | tes buka halaman login |

## 4. Menu × sesi: memastikan tidak ada yang terlewat

| Menu / alat | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| Beranda, Cari `Ctrl + K`, Panduan, bahasa & mode gelap | ● | | | |
| Daftar dashboard, filter, klik-filter, unduh | ● | | | |
| Filter global, komentar & rating, ekspor tabel | ● | | | |
| Telusuri, tampilan tersimpan, kesegaran data, PowerPoint | ● (modul tambahan) | | | |
| Asisten AI (panel ✦) | ● tanya | | ● pindai tabel, gabung | ● model, cadangan, batas |
| Studio Visual, jenis chart, peta | | ● | | |
| Ramalan, kalkulasi cepat, simulasi, jelaskan perubahan | | ● | | |
| Susun dashboard (template, tab, tinggi) | | ● | | |
| Kueri Visual, Kueri tersimpan | | ● | | |
| Auto chart & dashboard | | ● | | |
| Daftar chart, Jejak data | | ● | ● | |
| Langganan laporan, Peringatan data | | ● | | ● (siapkan email) |
| Berkas .ald / .aldx | | ● | | |
| Hubungkan data, Dataset, SQL Lab | | | ● | |
| Persiapan data, Ekstrak, impor banyak tabel | | | ● | |
| Hak akses data (RLS), Lihat sebagai, Pengguna, Role | | | ● | ● |
| Riwayat kueri | | | ● | |
| Pusat Kendali (status, pengaturan, batas data) | | | | ● |
| Kesehatan kueri, Jejak audit, Moderasi ulasan | | | | ● |
| Sematkan ke web lain | | | | ● |
| Login SSO, keamanan, cadangan, upgrade | | | | ● |

## 5. Penilaian

| Tahap | Alat | Kapan |
|---|---|---|
| **Pra-uji** | 5 pertanyaan (lihat bawah), tanpa nilai: untuk menyesuaikan kecepatan | awal sesi pertama |
| **Latihan** | latihan modul + kunci jawaban | dalam sesi |
| **Kuis** | kuis modul (pilihan ganda, ada kunci) | akhir sesi |
| **Praktik terukur** | satu tugas akhir per level (tabel di bawah) | akhir level |
| **Daftar periksa kompetensi** | dicentang pengajar bersama peserta | akhir level |

**Pra-uji (L1):** (1) Apa beda dashboard dan chart? (2) Bagaimana menyaring satu cabang? (3) `25B` berarti? (4) Kenapa dua
rekan melihat angka berbeda? (5) Pernah memakai Excel pivot? (jawaban jujur menentukan kecepatan L2).

| Level | Tugas akhir | Kriteria lulus |
|---|---|---|
| 1 | di dashboard latihan: saring Kategori = Elektronik, telusuri ke dashboard lain, simpan sebagai tampilan | angka benar + tampilan tersimpan |
| 2 | dashboard 4 chart (satu ramalan) + filter + satu tab tambahan + judul | semua chart tampil, filter bekerja |
| 3 | dataset gabungan (≥ 2 sumber) dengan RLS per role, diuji di *Lihat sebagai…* | akun cabang A tidak melihat cabang B |
| 4 | cadangan → hapus objek → pulihkan; ubah satu pengaturan dan telusuri di Riwayat/jejak audit | objek kembali, jejak ditemukan |

**Lulus** = kuis ≥ 70% **dan** tugas akhir memenuhi kriteria **dan** daftar periksa kompetensi terisi. Yang belum lulus
mengulang bagian yang kurang (bukan seluruh level).

**Sertifikat internal (contoh isi):** nama · level · tanggal · versi ALDx (lihat kaki halaman login) · nama pengajar.

## 6. Tindak lanjut

| Waktu | Kegiatan | Tujuan |
|---|---|---|
| H+7 | pesan ke peserta: 3 tips pemakaian + tautan [peta menu](../33-peta-menu-per-level.md) | menjaga kebiasaan |
| H+30 | **klinik tanya-jawab** 60 menit; peserta membawa laporan nyata | mengatasi kendala nyata |
| H+60 | Admin: tinjau **Kesehatan kueri** dan **Jejak audit**; bina pengguna aktif | kinerja & keamanan |
| H+90 | evaluasi: berapa dashboard dibuat, siapa aktif, apa yang menghambat | rencana pelatihan lanjutan |

## 7. Masalah umum di kelas

| Gejala | Penyebab | Solusi cepat |
|---|---|---|
| peserta tidak melihat menu tertentu | role belum diberi izin | cek Kelola › Pengguna / Role; menu tampil sesuai izin |
| angka peserta beda dengan kunci | aturan RLS atau filter global aktif | hapus filter global (corong), cek **Lihat sebagai…** |
| Asisten AI lambat / galat 503 | model lokal kecil atau penyedia gratis sibuk | pakai model cadangan; atau jalankan demo AI di akun pengajar |
| Langganan laporan tidak terkirim | SMTP belum diisi | tunjukkan di log (mode uji); isi SMTP sebelum sesi |
| layar tidak muat di proyektor | resolusi tinggi | `Ctrl` + `+`/`−`; sidebar dilipat (tombol panah) |
| peserta tertinggal | beda kecepatan | bagi tugas berjenjang: wajib (latihan 1–4) dan tantangan (sisanya) |

## 8. Bahan pendukung

| Bahan | Lokasi |
|---|---|
| Modul per level (rencana sesi, latihan, kunci, kuis) | [README](README.md) |
| Tutorial bergambar untuk peserta | [../tutorial/](../tutorial/README.md) |
| Peta menu per level | [../33-peta-menu-per-level.md](../33-peta-menu-per-level.md) |
| Data latihan & angka kunci | [README § Data latihan](README.md#data-latihan) |
| Skenario uji (UAT) | [../pengujian/](../pengujian/README.md) |
| Semua dokumen dalam PDF siap cetak | [../pdf/](../pdf/README.md) |
