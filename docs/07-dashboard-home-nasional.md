# 07 · Dashboard sebagai Kode (contoh: Home Nasional, profil DJP)

> **Khusus profil DJP, opsional.** Dashboard ini hanya dibangun bila `SPS_PROFIL_DJP=1` di `.env` **dan**
> koneksi *Oracle DMP (GENAPP)* ada; instalasi lain otomatis melewatinya. Sudah terlanjur dibuat dan tidak
> dipakai? `scripts\bersihkan-profil-djp.ps1` menghapus dashboard Beranda & Home Nasional beserta chart dan
> dataset `home_nasional__*` / `beranda__*` (tambah `-Koneksi` untuk juga menghapus koneksi sumber DJP). Dokumen ini tetap berguna sebagai **contoh membuat dashboard
> dari kode** (`config\sps_dash_*.py` → `scripts\build-dashboards.ps1`) untuk perusahaan mana pun.

Padanan halaman **/Home** engineN di Superset, dibangun otomatis dari kode.
Alamat: http://localhost:8088/superset/dashboard/home-nasional/

## Isi dashboard

| Bagian | Chart | Asal query engineN (`Mpemby.php`) |
|---|---|---|
| KPI | Target, Penerimaan s.d. Bulan, Capaian, Growth, Penerimaan Tahun Lalu | `getRenpen`, `getPen`, `getPenl` |
| Komposisi | Per Jenis Pajak (7 teratas), Sektor Dominan (10 teratas) | `getPiePen`, `getSektdom` |
| Customer Perspective | Payment Compliance Nasional & WP Pusat | `paycompNas`, `paycompPus` |
| | Strength of Figure | `sofNas` |
| | Grafik WP Terdaftar (11 tahun) | `grafWPTerdaftar` |
| | WP Terdaftar, PPM, PKM, SBP | `getWPterdaftar`, `getPPMPKM` |
| | Breakdown Penerimaan WPS/WPK | `getWpsk`, `getBreakdownPen` |
| | Dashboard WP (Aktif/NE/DE/Badan/OP/IP/Lama/Baru) | `Wpbyrlpr` |
| Follow the Money | Nasional & WP Pusat (coverage, collection, growth) | `getKat` |

Sumber data: koneksi **Oracle DMP (GENAPP)** (= grup `default` engineN).

**Filter** (panel kiri): **Tahun** (otomatis tahun terbaru) dan **s.d. Bulan**.
Bulan kosong = bulan berjalan, sama seperti engineN.

## Cara kerja

```
sps_dash_home.py            definisi: SQL dataset, chart, tata letak, filter
      │
sps_dashboard_builder.py    ubah definisi → format impor Superset → simpan
      │                     (UUID tetap, jadi build ulang = perbarui)
sps_build_dashboards.py     daftar dashboard yang dibangun
      │
scripts\build-dashboards.ps1
```

Filter dashboard dibaca di SQL lewat fungsi `sps_periode()` (`sps_jinja.py`):

```sql
{% set p = sps_periode(filter_values('tahun', remove_filter=True),
                       filter_values('bulan', remove_filter=True)) %}
SELECT ... WHERE TAHUN = '{{ p.tahun }}' AND BULAN <= '{{ p.bulan }}'
```

`sps_periode` hanya menerima angka (tahun 4 digit, bulan 1–12), jadi nilai
filter tidak bisa dipakai menyisipkan SQL. Hasilnya: `tahun`, `tahun_lalu`,
`bulan`, dan `kolom_pdb` (kolom PDB kumulatif per triwulan untuk Follow the Money).

## Langkah

1. Pastikan koneksi Oracle DMP sudah terdaftar: `scripts\add-connections.ps1`
2. Bangun dashboard:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build-dashboards.ps1
   ```
3. Buka dashboard, pilih Tahun & Bulan.

## Mengubah / menambah

| Ingin | Ubah di `config\sps_dash_home.py` |
|---|---|
| Ubah query | `sql` pada `Dataset` terkait |
| Tambah rumus (rasio, growth) | `metrics` pada `Dataset` → `Metric(nama, ekspresi SQL, label, format)` |
| Tambah chart | fungsi `big_number` / `pie` / `bar` / `table` di `CHARTS` |
| Atur tata letak | `ROWS` (lebar total satu baris maks. 12) |

Lalu jalankan lagi `scripts\build-dashboards.ps1`. Tidak perlu restart.

Dashboard lain (mis. Kanwil): buat `sps_dash_kanwil.py` dengan pola yang sama,
lalu tambahkan ke `DASHBOARDS` di `sps_build_dashboards.py`.

> ⚠️ Perubahan lewat UI pada dashboard/chart buatan builder **tertimpa** saat
> build dijalankan lagi. Untuk eksperimen di UI, pakai **Save as** (salinan).

## Perbedaan dengan engineN

- Tampilan memakai chart standar Superset (bukan ECharts kustom engineN).
- Bagian interaktif khusus engineN (Peta Sektor, Corong Kepatuhan, kuadran
  Coverage vs Collection, tautan ke halaman rinci) belum dipindahkan.
- Hak akses: engineN membatasi /Home untuk KPDJP. Di Superset, atur lewat
  **Dashboard → Edit properties → Roles** (fitur `DASHBOARD_RBAC` sudah aktif).
- Query diuji pembentukannya (SQL Oracle valid untuk ke-19 chart), tetapi belum
  dijalankan ke server Oracle sungguhan. Bila ada chart error, buka chart →
  **View query** untuk melihat SQL-nya.
