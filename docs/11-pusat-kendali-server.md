# 11 · Pusat Kendali Server

Halaman khusus Admin untuk mengatur & memantau kemampuan server. Tab bertanda ★ **khusus Superadmin**
([24](24-superadmin-dan-batas-data.md)):
**http://localhost:8088/pusat-kendali/** (menu **Settings → Manage → Pusat Kendali Server**).

| Tab | Isi |
|---|---|
| **Status** | Pengguna aktif, waktu muat chart, cache hit, antrean, **cadangan terakhir & uji pulih**, CPU/RAM tiap proses, chart terlambat |
| **Topologi** | Proses apa jalan di node mana + rekomendasi auto-tuning |
| **Pengaturan** ★ | pengaturan proses, CPU/RAM, cache, batas baris, timeout, gateway, fitur |
| **Batas data** ★ | ukuran & baris maksimal upload, impor berkas, ekstrak, kuota ALDx Engine; rekomendasi otomatis; `0` = tanpa batas |
| **Ekstrak** | Ekstrak ALDx Engine: buat, jadwal, segarkan, pakai di chart, riwayat ([13](13-sps-engine-ekstrak.md)) |
| **Asisten AI** | model aktif (**Uji** waktu jawab, **Jadikan bawaan**), model lokal terdeteksi otomatis + cara memasang, key cloud gratis & berbayar (diuji lalu disimpan terenkripsi) ([28](28-sambungkan-asisten-ai.md)) |
| **Hak akses** ★ | Matriks role × kemampuan (lihat, unduh, buat chart, SQL Lab, upload, …) + peringatan pengguna non-Admin yang bisa melihat semua data |
| **Riwayat** | **Akun terkunci** (buka kunci), **jejak audit** (login, unduh data, ekspor/impor, pengguna & hak akses, koneksi, berkas, moderasi; filter, cari, unduh CSV), riwayat pengaturan sebelum → sesudah |

---

## 1. Arsitektur

```
                     Pengguna (browser)  http://server:8088
                                 │
                       ┌─────────▼─────────┐
                       │  gateway (nginx)  │  bagi beban · failover · batas upload · timeout
                       └───┬───────────┬───┘
                 ┌─────────▼──┐     ┌──▼──────────────┐
  NODE UTAMA     │ superset   │     │ superset (web)  │   NODE TAMBAHAN (opsional)
                 │ (web)      │     │ superset-worker │
                 │ superset-  │     └──┬──────────────┘
                 │  worker    │        │
                 │ superset-  │        │   semua node memakai:
                 │  beat      │◄───────┤   • metadb node utama (metadata + pengaturan pusat)
                 │ redis      │◄───────┤   • Redis node utama (cache + antrean)
                 │ metadb     │        │   • ALDx Engine node utama (ekstrak, upload, ramalan)
                 │ engine     │◄───────┘
                 └────────────┘
```

| Container | Fungsi |
|---|---|
| `gateway` | Pintu masuk, pembagi beban antar-node web |
| `superset` | Web Gunicorn: dashboard, chart, API, SQL Lab langsung |
| `superset-worker` | Celery: satu kelompok proses per antrean (sqllab, grafik, cache, laporan) |
| `superset-beat` | Penjadwal: laporan, pemanasan cache, pembersihan log |
| `redis` | Cache hasil query, status filter, antrean tugas |
| `metadb` | PostgreSQL: metadata & pengaturan pusat |
| `engine` | ClickHouse ALDx Engine: ekstrak, upload, ramalan ([13](13-sps-engine-ekstrak.md)) |

Antrean backgrounder: **sqllab**, **grafik**, **cache**, **laporan**, **ekstrak** (penyegaran ekstrak & ramalan harian).

**Pengaturan pusat**: disimpan di metadb `sps_superset` (tabel `sps_server_atur`), bukan di file,
jadi semua node membaca nilai yang sama. Riwayat di `sps_server_riwayat`, detak node di `sps_node`.

## 2. Struktur berkas

```
config/sps_server/
├── skema.py        DAFTAR SEMUA PENGATURAN (tambah pengaturan baru di sini)
├── tuning.py       AUTO-TUNING: rumus CPU/RAM -> jatah container & jumlah proses
├── konfig.py       pengaturan -> konfigurasi Superset (cache, Celery, batas, upload)
├── jalankan.py     peluncur proses tiap container + detak (heartbeat)
├── penyimpanan.py  tabel pengaturan, riwayat, node
├── gateway.py      pembuat server/gateway.conf
├── terapkan.py     dipanggil terapkan-server.ps1
├── izin.py         matriks hak akses + izin upload ke ALDx Engine
├── monitor.py      data tab Status
├── tampilan.py     halaman & API /pusat-kendali/
└── halaman.html    tampilan
server/gateway.conf          dibuat otomatis (jangan diedit)
docker-compose.yml           node utama
docker-compose.node.yml      node tambahan
scripts/terapkan-server.ps1  terapkan perubahan "Perlu diterapkan"
scripts/gabung-node.ps1      jadikan komputer lain node tambahan
```

## 3. Memasang (dari versi sebelumnya)

Jalankan **`PASANG.cmd`** ([18-installer.md](18-installer.md)): container baru (metadb, engine, redis,
worker, beat, gateway) dinyalakan, metadata lama (XAMPP/MariaDB) dipindah ke PostgreSQL, jatah CPU/RAM dihitung, izin menu dibuat.

Lalu buka `http://localhost:8088/pusat-kendali/`. Alamat Superset untuk pengguna **tidak berubah**
(port 8088 kini dilayani gateway). Akses web langsung tanpa gateway: `http://localhost:8089` (diagnosa).

> Docker Desktop: sediakan minimal **6 GB RAM** (Settings → Resources). Tab Status memberi
> peringatan bila jatah RAM terlalu kecil.

## 4. "Langsung berlaku" vs "Perlu diterapkan"

| Lencana | Artinya | Contoh |
|---|---|---|
| **Langsung berlaku** | Semua node membaca ulang dalam ≤ 10 detik, tanpa restart | batas baris, timeout chart, cache, upload |
| **Perlu diterapkan** | Jumlah proses / jatah CPU-RAM / komponen yang dibuat saat start | proses web, backgrounder, Redis, rate limit |

Pengaturan "Perlu diterapkan" yang sudah disimpan muncul di pita kuning **"N perubahan menunggu
diterapkan"**. Terapkan dengan `scripts\terapkan-server.ps1`
(container dinyalakan ulang ±1 menit).

Catatan: tampilan SQL Lab di browser bisa menampilkan batas lama hingga 60 detik (cache tampilan
Superset); batas sebenarnya di server sudah berlaku.

## 5. Daftar pengaturan

Nilai **auto** dihitung tiap node dari perangkat kerasnya (bagian 6). Validasi silang: timeout
chart & SQL Lab harus lebih kecil dari timeout permintaan web; fitur async butuh minimal 1 backgrounder.

**Proses (topologi)**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `web.worker` | Proses web | auto proses | diterapkan |
| `web.thread` | Thread per proses web | auto thread | diterapkan |
| `web.timeout_detik` | Timeout permintaan web | 330 detik | diterapkan |
| `web.daur_ulang` | Daur ulang proses web setiap | 1000 permintaan | diterapkan |
| `antrean.sqllab` | Backgrounder: SQL Lab | auto proses | diterapkan |
| `antrean.grafik` | Backgrounder: chart async | auto proses | diterapkan |
| `antrean.cache` | Backgrounder: pemanasan cache | 1 proses | diterapkan |
| `antrean.laporan` | Backgrounder: laporan & alert | 1 proses | diterapkan |
| `antrean.ekstrak` | Backgrounder: penyegaran ekstrak | 1 proses | diterapkan |

**Jatah CPU & RAM per container**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `sumber.cadangan_persen` | Cadangan RAM untuk sistem | 15 % | diterapkan |
| `sumber.web_cpu` | CPU container web | auto inti | diterapkan |
| `sumber.web_ram_mb` | RAM container web | auto MB | diterapkan |
| `sumber.worker_cpu` | CPU container backgrounder | auto inti | diterapkan |
| `sumber.worker_ram_mb` | RAM container backgrounder | auto MB | diterapkan |
| `sumber.redis_ram_mb` | RAM cache server (Redis) | auto MB | diterapkan |
| `sumber.engine_ram_mb` | RAM ALDx Engine (ClickHouse) | auto MB (25%, 1–16 GB) | diterapkan |
| `sumber.metadb_ram_mb` | RAM database katalog (PostgreSQL) | auto MB (512–1024) | diterapkan |

**Cache server**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `cache.data_detik` | Lama hasil query disimpan | 3600 detik | langsung |
| `cache.filter_detik` | Lama status filter & explore disimpan | 86400 detik | diterapkan |
| `cache.pemanasan_aktif` | Pemanasan cache terjadwal | tidak  | diterapkan |
| `cache.pemanasan_jam` | Jam pemanasan cache | 6 jam | diterapkan |
| `cache.pemanasan_jumlah` | Jumlah dashboard dipanaskan | 10 dashboard | diterapkan |

**Batas baris**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `batas.baris_chart` | Baris maksimal per chart | 5000 baris | langsung |
| `batas.baris_sql` | Baris maksimal hasil SQL Lab | 100000 baris | langsung |
| `batas.baris_tampil_sql` | Baris ditampilkan di SQL Lab | 10000 baris | langsung |
| `batas.baris_chart_berat` | Baris maksimal chart berat (Tree, Graph, Sankey, Sunburst, Treemap, Word cloud, peta titik) | 1000 baris | langsung |
| `batas.baris_sampel` | Baris contoh data (View data) | 1000 baris | langsung |
| `batas.baris_filter` | Nilai maksimal di daftar filter | 10000 nilai | langsung |

**Timeout & sesi**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `timeout.chart_detik` | Timeout chart & dashboard | 60 detik | langsung |
| `timeout.sqllab_detik` | Timeout SQL Lab | 300 detik | langsung |
| `timeout.sqllab_async_detik` | Timeout SQL Lab async | 21600 detik | diterapkan |
| `timeout.sesi_menit` | Lama sesi login | 480 menit | langsung |

**Batas data: upload, impor berkas, ekstrak** (tab **Batas data**, khusus Superadmin; `0` = tanpa batas, `auto` = dari RAM/disk, lihat [24](24-superadmin-dan-batas-data.md))

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `upload.aktif` | Izinkan upload Excel/CSV | ya  | langsung |
| `upload.ukuran_mb` | Upload: ukuran file maksimal | 25 MB | langsung |
| `upload.baris_maks` | Upload: baris maksimal per file | 200000 baris | langsung |
| `upload.jenis` | Jenis file diizinkan | csv, xlsx, xls  | langsung |
| `upload.peran` | Role yang boleh upload | Alpha | langsung |
| `impor.ukuran_mb` | Impor berkas: ukuran maksimal | auto MB | langsung |
| `impor.baris_maks` | Impor berkas: baris maksimal per tabel | auto baris | langsung |
| `ekstrak.baris_maks` | Ekstrak: baris maksimal per ekstrak | auto baris | langsung |
| `ekstrak.total_gb` | Kuota disk ALDx Engine | auto GB | langsung |
| `berkas.snapshot_data` | Berkas .aldx boleh membawa data | ya | langsung |
| `berkas.baris_snapshot` | Berkas .aldx: baris maksimal per dataset | 100000 baris | langsung |
| `berkas.ukuran_mb` | Berkas .ald/.aldx: ukuran maksimal | 100 MB | langsung |
| `berkas.peran_muat_data` | Peran yang boleh memuat data dari berkas .aldx | Admin | langsung |
| `ulasan.moderasi` | Komentar perlu disetujui Superadmin | ya | langsung |

**Gateway & keamanan**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `gateway.permintaan_per_detik` | Batas permintaan per pengguna | 50 per detik | diterapkan |
| `gateway.login_per_menit` | Batas percobaan login | 10 per menit | diterapkan |
| `gateway.log_simpan_hari` | Simpan log aktivitas | 180 hari | diterapkan |
| `keamanan.login_maks_gagal` | Kunci akun setelah salah password | 5 kali (0 = mati) | langsung |
| `keamanan.login_kunci_menit` | Lama akun terkunci | 15 menit | langsung |
| `keamanan.audit_simpan_hari` | Simpan jejak audit | 365 hari | langsung |

**Fitur pemrosesan**

| Kunci | Pengaturan | Bawaan | Berlaku |
|---|---|---|---|
| `fitur.sqllab_async` | SQL Lab async | tidak  | langsung |
| `fitur.chart_async` | Chart async | tidak  | diterapkan |

## 6. Auto-tuning

Dua tahap, dikerjakan di **tiap node** (termasuk node yang baru bergabung):

1. **Saat diterapkan** (`terapkan-server.ps1` → `tuning.alokasi_container`): dari total CPU/RAM Docker
   node → jatah per container.
   RAM tersedia = RAM × (100 − cadangan%) → Redis 10% (256–2048 MB, node utama) → sisanya web 60%,
   backgrounder 40%. CPU: web 60%, backgrounder 50% (batas atas, boleh tumpang tindih).
2. **Saat container start** (`jalankan.py` → `tuning.proses_web/proses_worker`): dari jatah container →
   jumlah proses.
   Proses web = min(2 × CPU + 1, RAM / 700 MB), 1–16; thread = 8 bila RAM/proses ≥ 1,2 GB, selain itu 4.
   Backgrounder total = min(2 × CPU, RAM / 450 MB), 1–24; cache & laporan tetap, sisanya SQL Lab
   (dibagi dua dengan chart async bila aktif).

Contoh hasil (pengaturan bawaan, node utama):

| Docker node | Web (CPU / RAM) | Proses web × thread | Backgrounder (CPU / RAM) | Proses backgrounder | Redis |
|---|---|---|---|---|---|
| 4 CPU / 6 GB | 2 / 2.666 MB | 3 × 4 | 2 / 1.777 MB | sqllab 1, cache 1, laporan 1 | 522 MB |
| 4 CPU / 8 GB | 2 / 3.606 MB | 5 × 4 | 2 / 2.404 MB | sqllab 2, cache 1, laporan 1 | 696 MB |
| 8 CPU / 16 GB | 5 / 7.366 MB | 10 × 4 | 4 / 4.911 MB | sqllab 6, cache 1, laporan 1 | 1.392 MB |
| 16 CPU / 32 GB | 10 / 15.328 MB | 16 × 4 | 8 / 10.219 MB | sqllab 14, cache 1, laporan 1 | 2.048 MB |

Angka yang diisi admin (bukan `auto`) selalu dihormati. Tab **Topologi → Rekomendasi** menunjukkan
hasil auto-tuning bila diterapkan ulang.

## 7. Cache & hak akses data

Superset aslinya menyusun kunci cache dari teks aturan RLS mentah (`{{ sps_akses(...) }}`) yang
**sama untuk semua pengguna**, sehingga cache bisa membocorkan data antar-wilayah. Ini sudah ditutup:
`SpsSecurityManager.get_rls_cache_key` menambahkan **sidik lingkup akses** (`sps_akses.sidik_akses`).
Pengguna dengan lingkup sama berbagi cache; lingkup berbeda tidak pernah. Aturan RLS biasa (per role)
sudah aman sejak awal karena teks aturannya berbeda per role.

## 8. Upload Excel/CSV

- Data masuk ke **ALDx Engine** (koneksi "ALDx Engine (ClickHouse)", database `sps_engine`), terpisah dari sumber data.
  Upload ke koneksi ClickHouse lain ditolak. Berkas Access/Excel banyak lembar: **Hubungkan data → Berkas** ([06](06-sumber-data.md)).
- Dijaga di 3 lapis: gateway (ukuran), Superset (aktif/ukuran/jenis), pembaca file (jumlah baris).
  Ukuran & baris diatur di tab **Batas data** (`0` = tanpa batas).
- Role yang boleh: pengaturan `upload.peran` (Admin selalu boleh). Diterapkan langsung ke permission Superset.
- Cara pakai: menu **+ → Data → Upload CSV/Excel**.

## 9. Menambah node (scale-out)

Di **node utama** (sekali):

1. `.env`: `CLUSTER_BIND=0.0.0.0`, lalu `scripts\terapkan-server.ps1` (metadb, engine & Redis terbuka ke jaringan).
2. Firewall Windows: izinkan masuk port **5433** (metadb), **8124** (engine) & **6379** (Redis) **hanya dari IP node tambahan**.

Di **komputer baru**:

1. Pasang Docker Desktop, salin folder `D:\superset` **beserta `.env`** dari node utama
   (`SUPERSET_SECRET_KEY` dan semua password wajib sama).
2. `powershell -ExecutionPolicy Bypass -File scripts\gabung-node.ps1 -Utama <IP node utama>`
3. Buka firewall masuk port **8088** dari IP node utama.

Kembali di **node utama**: tunggu node muncul di tab Status (±1 menit), lalu
`scripts\terapkan-server.ps1` agar gateway ikut membagi beban ke node baru.

Node baru **menyetel diri sendiri** (auto-tuning) dari CPU/RAM-nya. Pengaturan pusat, cache, dan
antrean dipakai bersama, jadi chart yang di-cache satu node langsung dipakai node lain.

### Batasan HA (jujur)

Ini **scale-out** (beban dibagi, satu node web mati → gateway mengalihkan ke node lain), belum HA penuh:

| Titik tunggal | Akibat bila mati | Jalan menuju HA penuh |
|---|---|---|
| Komputer node utama (gateway) | Semua akses berhenti | Load balancer kantor (F5/nginx HA) di depan semua node |
| metadb (PostgreSQL) | Semua berhenti | PostgreSQL replikasi streaming (Patroni), atau server PostgreSQL kantor |
| engine (ClickHouse) | Dashboard ekstrak berhenti (live tetap jalan) | ClickHouse replikasi (Keeper) |
| Redis | Cache & antrean hilang (dibangun ulang) | Redis Sentinel |


## 9b. HTTPS (opsional) {#https}

Bawaan: `http://`. HTTPS mengenkripsi koneksi browser ↔ server (password & data tidak bisa disadap di jaringan).

| Langkah | Cara |
|---|---|
| Aktifkan | installer: centang **Atur pengaturan lanjutan** › halaman Identitas › **Pakai HTTPS**, atau `.env`: `SPS_HTTPS=1` + `SPS_HTTPS_NAMA=srv-aldx,10.1.2.3` |
| Terapkan | `scripts\terapkan-server.ps1` → sertifikat dibuat otomatis di `server\tls\` (bila belum ada), gateway pindah ke HTTPS |
| Alamat | `https://localhost:8088` (port sama). `http://` otomatis dialihkan ke `https://` |
| Peringatan browser | wajar untuk sertifikat buatan sendiri. Hilangkan: jalankan `scripts\percayai-sertifikat.ps1 -Alamat https://srv-aldx:8088` di komputer pengguna, atau sebarkan `server\tls\aldx.crt` lewat GPO |
| Sertifikat kantor | salin ke `server\tls\aldx.crt` + `aldx.key`, lalu `scripts\terapkan-server.ps1` |
| Matikan | `SPS_HTTPS=` (kosong) → `scripts\terapkan-server.ps1` |

Kunci `aldx.key` rahasia: jangan dibagikan / di-commit (sudah di `.gitignore`). Kode: `config/sps_server/tls.py`,
`config/sps_server/gateway.py`.

## 10. Masalah umum

| Gejala | Penyebab | Solusi |
|---|---|---|
| Menu Pusat Kendali tidak ada | Izin belum dibuat | `scripts\build-dashboards.ps1`, login ulang |
| Tab Status: "Belum ada detak node" | Container masih versi lama | `scripts\terapkan-server.ps1` |
| `localhost:8088` 502 Bad Gateway | Web belum siap / gateway memakai daftar lama | Tunggu 1–2 menit; `scripts\terapkan-server.ps1` |
| Container berhenti `OOMKilled` | Jatah RAM terlalu kecil | Naikkan RAM Docker Desktop, atau kecilkan `web.worker` |
| "Upload Excel/CSV sedang dinonaktifkan" | `upload.aktif` = tidak | Pengaturan → Upload |
| "File berisi N baris; maksimal …" | Melebihi `upload.baris_maks` | Naikkan batas atau pecah file |
| Antrean menumpuk (tab Status) | Backgrounder kurang | Naikkan `antrean.*` lalu terapkan |
| Node tambahan tidak muncul | metadb/engine/Redis node utama tidak terjangkau | Ulangi `gabung-node.ps1`, cek firewall & `CLUSTER_BIND` |
| Browser: "Koneksi tidak pribadi" / *Not secure* | HTTPS dengan sertifikat buatan sendiri | Klik *Lanjutkan*, atau `scripts\percayai-sertifikat.ps1` (§9b) |
| Sesudah HTTPS aktif tidak bisa login | Cookie lama | Tutup tab, buka `https://…` lagi, Ctrl+F5 |
| "Akun dikunci sementara…" di halaman login | Salah password berulang | Tunggu, atau Admin: tab Riwayat › Buka kunci; darurat `scripts\buka-kunci.ps1` |
| Pengaturan sulit dicari | Banyak isian | Ketik di kotak **Cari pengaturan** di atas tab Pengaturan |
| Log per layanan | — | `scripts\logs.ps1 -Layanan superset-worker` (atau `semua`) |
