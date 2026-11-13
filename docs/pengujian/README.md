# Bahan Pengujian ALDx

Tiga lapis pengujian, dari yang otomatis sampai uji oleh pengguna.

| Lapis | Apa | Siapa | Kapan | Berkas |
|---|---|---|---|---|
| 1. **Uji otomatis** | 81 pemeriksaan: container, koneksi, backgrounder, 23 chart, ramalan (termasuk tipe angka ClickHouse), engine, halaman & menu, keamanan & Superadmin, batas data, ekspor, peran AI, hierarki dimensi, objek dashboard, Tampilkan saya & analitik lengkap, preset tema, kolom ID, data latihan harian, impor banyak tabel, versi aplikasi, ukuran & dimensi terdefinisi, kalkulasi cepat, template dashboard, data pendukung latihan, berkas .ald/.aldx, filter global & ulasan, driver Hubungkan data, HTTPS gateway, penguncian akun & audit, hak minimum, ketahanan (ekspor latar & cadangan) | admin server | setiap instalasi, upgrade, perubahan pengaturan | `scripts\uji.ps1` → `config/sps_uji.py` |
| 2. **Uji asap** | 12 skenario manual inti (± 20 menit) | admin server | setelah lapis 1 | skenario bertanda *asap* |
| 3. **UAT** | 168 skenario per level & area | perwakilan pengguna tiap level | sebelum dipakai pengguna, dan setelah upgrade mayor | [skenario-uji.md](skenario-uji.md), [lembar-uji.xlsx](lembar-uji.xlsx) |

Laporan QA terakhir (installer sampai seluruh menu, UI/UX, keamanan): [laporan-qa.md](laporan-qa.md) (PDF: `docs\pdf\laporan-qa.pdf`).

## 1. Uji otomatis

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uji.ps1          # ringkas
powershell -ExecutionPolicy Bypass -File scripts\uji.ps1 -Rinci   # + detail galat
```

Contoh hasil:
```
[Komponen]
  LULUS  metadb (PostgreSQL) terhubung              postgresql 17.x
  LULUS  ALDx Engine (ClickHouse) terhubung          versi 25.8.x
  LULUS  Redis terhubung                            redis:6379
  LULUS  Backgrounder menjawab & melayani antrean   4 worker, antrean ['cache', 'ekstrak', 'laporan', 'sqllab']
[Studio]
  LULUS  chart Batang                               24 baris -> echarts_timeseries_bar
  ...
81/81 lulus
```

Uji ini **tidak mengubah data pengguna** (tabel sementara `uji__otomatis` dibuat lalu dihapus) dan
butuh data latihan (`scripts\data-latihan.ps1`).

## 2. UAT: cara menyelenggarakan

1. **Siapkan**: server uji (atau produksi sebelum diumumkan), data latihan, akun penguji per level:
   minimal 2 akun di role cabang berbeda (untuk uji hak akses H01–H02, E07), satu database uji
   dengan akun hanya-baca (F12–F13, H09), dan berkas `bahan-ajar/berkas/contoh-target-toko.xlsx` (F14).
2. **Bagikan** `lembar-uji.xlsx` (satu salinan per penguji, atau satu bersama).
3. Penguji mengerjakan skenario sesuai levelnya, mengisi kolom kuning: **Hasil**, **Catatan**, **Penguji**, **Tanggal**.
4. Sheet **Ringkasan** menghitung otomatis: jumlah lulus/gagal per area, % lulus, dan
   **Prioritas Tinggi gagal**.
5. **Kriteria siap pakai**: *Prioritas Tinggi gagal = 0*. Skenario Sedang/Rendah yang gagal dicatat
   sebagai perbaikan berikutnya.
6. Kumpulkan catatan **Gagal** + tangkapan layar → kirim ke pengembang bersama `diagnosa.txt`.

| Level penguji | Area yang diuji |
|---|---|
| 1 Pengguna | B, C, H01–H02 |
| 2 Analis | D, E, H07 |
| 3 Admin data | F, H03, H09 |
| 4 Admin server | A, G, H04–H06, H08, I |

## 3. Uji hak akses (paling penting)

Data perusahaan rahasia: kegagalan RLS adalah gangguan **kritis**. Selalu uji dengan **dua akun nyata
berbeda lingkup**, bukan hanya akun admin (admin melihat semua).

| Uji | Cara singkat |
|---|---|
| Dashboard | H01: dua akun beda cabang, dashboard sama, total berbeda sesuai cabang |
| Cache | H02: buka bergantian dalam 1 menit; angka tidak tertukar |
| Ekstrak | F06: setelah *Pakai di chart*, pembatasan tetap sama |
| Persiapan data | F02 dengan sumber ber-RLS: dataset hasil tetap terbatas |
| Ramalan | E07: ramalan pengguna A tidak terlihat pengguna B beda lingkup |
| Asisten AI | H07: jawaban hanya berisi cabang penanya |
| Koneksi | H09: koneksi dari wizard menolak UPDATE/INSERT/DELETE |

## 4. Mengubah skenario

Skenario ditulis sekali di `skenario.py` (daftar `SKENARIO`). Setelah mengubah:
```powershell
python docs\pengujian\skenario.py      # membuat ulang skenario-uji.md & lembar-uji.xlsx
```

## 5. Pengujian yang dilakukan pengembang

Selain uji di atas, setiap rilis diuji pengembang di lingkungan uji:
- uji backend (test client Flask): 59 kasus termasuk 23 jenis chart, ramalan & RLS-nya, ekstrak (penuh, inkremental, pindah/kembali, hapus terlindungi), upload engine;
- uji wizard Hubungkan data: 32 kasus (katalog, uji & simpan PostgreSQL dengan password berkarakter khusus, pesan galat tanpa password, penolakan sumber lokal, impor CSV/Excel/SQLite/Access .mdb & .accdb, token sekali pakai, non-admin ditolak);
- uji login mode akun lokal (tanpa LDAP) dan mode LDAP;
- uji browser (Playwright): Studio, peta, ramalan, tab Ekstrak, tanpa galat JavaScript;
- **render di Superset asli**: setiap jenis chart yang disimpan Studio dibuka di Explore dan
  dipastikan tampil tanpa galat (31/31);
- akurasi anomali: 40 deret acak × 2 skenario → 80/80 lonjakan tertangkap, 0 salah tandai.
