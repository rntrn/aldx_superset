# 07 · Dashboard sebagai Kode

Untuk pengembang. Dashboard bisa dibuat lewat UI (Studio Visual, Superset) **atau** ditulis sebagai kode Python,
sehingga bisa disimpan di git, ditinjau, dan dibangun ulang sama persis di server mana pun.

## Cara kerja

```
sps_dash_<nama>.py          definisi: SQL dataset, metrik, chart, tata letak, filter, hak akses
      │
sps_dashboard_builder.py    ubah definisi → format impor Superset → simpan
      │                     (UUID tetap dari nama, jadi build ulang = perbarui, bukan duplikat)
sps_build_dashboards.py     daftar DASHBOARDS yang dibangun
      │
scripts\build-dashboards.ps1
```

Dashboard yang koneksi sumbernya belum ada otomatis dilewati.

## Contoh: dashboard dari data latihan

Buat `config\sps_dash_contoh.py`:

```python
from sps_dashboard_builder import Chart, Dashboard, Dataset, Metric, SelectFilter

PENJUALAN = Dataset(
    key="penjualan",
    sql="SELECT periode, nm_cabang, kategori, total FROM latihan_penjualan",
    columns=["periode", "nm_cabang", "kategori", "total"],
    metrics=[Metric("total_penjualan", "SUM(total)", "Total penjualan", ",.0f")],
    akses=None,                     # data contoh: tanpa pembatasan baris (lihat "Hak akses" di bawah)
)

CONTOH = Dashboard(
    key="contoh", title="Contoh Dashboard Kode", slug="contoh-kode",
    database_name="ALDx Engine (ClickHouse)",
    datasets=[PENJUALAN],
    charts=[
        Chart("total", "Total penjualan", "big_number_total", "penjualan",
              {"metric": "total_penjualan"}, width=4),
        Chart("per_kategori", "Penjualan per kategori", "echarts_timeseries_bar", "penjualan",
              {"x_axis": "kategori", "metrics": ["total_penjualan"]}, width=8),
    ],
    rows=[["total", "per_kategori"]],
    filters=[SelectFilter("cabang", "Cabang", "penjualan", "nm_cabang")],
)
```

Daftarkan di `config\sps_build_dashboards.py`:

```python
from sps_dash_contoh import CONTOH
DASHBOARDS: list = [CONTOH]
```

Lalu:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-dashboards.ps1
```

`params` pada `Chart` mengikuti *form data* Superset untuk `viz_type` tersebut. Cara termudah mendapatkannya: buat chart
di UI, lalu salin parameternya dari **… → Edit chart properties / Export**.

## Hak akses

Setiap `Dataset` mendapat aturan RLS otomatis dari `akses`:

| `akses` | Artinya |
|---|---|
| `{}` (bawaan) | data menyeluruh: hanya pengguna berlingkup `semua` yang melihat |
| `{"cabang": "KD_CABANG"}` | baris dibatasi sesuai atribut profil pengguna ([08](08-hak-akses-data.md), `config\akses.yaml`) |
| `None` | data referensi, tanpa pembatasan |

Tanpa profil pengguna (bawaan), batasi baris lewat **Settings → Row Level Security** per role.

## Mengubah / menambah

| Ingin | Ubah di `sps_dash_<nama>.py` |
|---|---|
| Ubah query | `sql` pada `Dataset` |
| Tambah rumus (rasio, pertumbuhan) | `metrics` → `Metric(nama, ekspresi SQL, label, format d3)` |
| Tambah chart | satu `Chart(...)` di `charts` |
| Atur tata letak | `rows` (lebar total satu baris maks. 12); `Markdown(...)` untuk teks/judul |
| Filter | `filters` → `SelectFilter(...)` |

Filter periode bisa dibaca di SQL lewat `sps_periode()` (`config\sps_jinja.py`), yang hanya menerima angka
(tahun 4 digit, bulan 1–12) sehingga nilai filter tidak bisa dipakai menyisipkan SQL. Hasilnya: `tahun`, `tahun_lalu`,
`bulan` (dua digit), dan `triwulan` (1–4):

```sql
{% set p = sps_periode(filter_values('tahun', remove_filter=True), filter_values('bulan', remove_filter=True)) %}
SELECT ... WHERE TAHUN = '{{ p.tahun }}' AND BULAN <= '{{ p.bulan }}'
```

> ⚠️ Perubahan lewat UI pada dashboard/chart buatan builder **tertimpa** saat build dijalankan lagi.
> Untuk eksperimen di UI, pakai **Save as** (salinan).
