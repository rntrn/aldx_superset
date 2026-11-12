# 31 · Catatan Versi

Daftar perubahan per rilis, terbaru di atas. Setiap rilis punya bagian **Perlu dilakukan setelah memperbarui** untuk
ketiga cara memasang ([29 §1](29-versi-pembaruan-hapus-total.md)).

> **Untuk pengembang:** setiap kali menambah fitur, tambahkan baris di rilis teratas (atau buat rilis baru), lalu
> jalankan `installer\setup\terbitkan.ps1` agar `ALDx-Setup.exe`, `ALDx-Setup-Offline.exe` dan `ALDx-HapusTotal.exe`
> di Releases ikut berisi versi ini.

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

### Perbaikan

| Masalah | Penyebab & perbaikan |
|---|---|
| **Ramalan / tren / anomali tidak bisa dipakai** pada data ALDx Engine (mis. `latihan_penjualan`) | Superset 6.1 tidak mengenali kolom ClickHouse `Float32/Float64` (termasuk di dalam `Nullable(...)`) sebagai angka. Kolom seperti `total` masuk **Dimensi**, tidak bisa dijumlah, dan panel Analitik mati. Sekarang dikenali sebagai angka (`config/sps_dialek.py` §5), juga di Explore |
| Label sumbu tanggal panjang ("Sat, 01 Mar 2025 00:00:00 GMT") | Kolom `Date/Date32` kini dikirim sebagai `2025-03-01` (`config/sps_ai/alat.py`) |

### Perlu dilakukan setelah memperbarui

| Cara memasang | Langkah |
|---|---|
| **git** (`git pull`) | `git pull` → `docker compose up -d` (atau klik dua kali `PASANG.cmd`) → `scripts\uji.ps1` harus **62/62 LULUS** → browser `Ctrl + F5` |
| **ALDx-Setup.exe** (online) | pastikan tanggal exe di Releases **setelah** rilis ini → jalankan di atas instalasi lama (folder sama; data & `.env` dipertahankan) → `Ctrl + F5` |
| **ALDx-Setup-Offline.exe** + `.bin` | sama dengan online; semua fitur baru jalan **tanpa internet** (huruf, peta, ECharts, gambar tersimpan lokal) |

Tidak ada langkah manual lain:
- Tabel baru `sps_hierarki` (hierarki) dan `sps_gambar` (gambar dashboard) dibuat otomatis di metadb.
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
