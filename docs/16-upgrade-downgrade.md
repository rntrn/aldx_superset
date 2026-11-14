# 16 · Upgrade & Downgrade Komponen

Setiap komponen di Docker punya **versi yang ditulis di `.env`**. Mengganti versi = mengubah satu
baris, lalu menjalankan beberapa perintah. Dokumen ini menjelaskan langkahnya per komponen.

## 1. Daftar versi

| Komponen | Variabel `.env` | Bawaan | Image Docker | Jenis rilis |
|---|---|---|---|---|
| Superset | `SUPERSET_VERSION` | `6.1.0` | `apache/superset` (+ driver, `docker/Dockerfile`) | mengikuti rilis Apache Superset |
| PostgreSQL (metadb) | `METADB_VERSI` | `17` | `postgres:<versi>-alpine` | versi utama didukung 5 tahun; rilis kecil (17.x) tiap 3 bulan |
| ClickHouse (engine) | `ENGINE_VERSI` | `25.8` | `clickhouse/clickhouse-server` | LTS (dukungan 1 tahun) |
| Redis | `REDIS_VERSI` | `7.4` | `redis:<versi>-alpine` | stabil |
| nginx (gateway) | `GATEWAY_VERSI` | `1.28` | `nginx:<versi>-alpine` | stabil |
| Driver Python | `docker/wheels/*.whl` | lihat folder | – | – |

Melihat versi yang **diminta** (.env) dan yang **berjalan**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\versi.ps1
```

Versi `11.4`, `25.8`, dll. = **seri**. `docker compose pull` mengambil perbaikan terbaru dalam seri
yang sama (patch keamanan). Ini aman dan disarankan tiap bulan.

---

## 2. Aturan umum (WAJIB dibaca)

1. **Cadangkan dulu**: `scripts\cadangkan.ps1 -Engine`. Cadangan ini satu-satunya jalan kembali.
2. **Baca catatan rilis** versi tujuan (bagian "breaking changes").
3. **Uji di server uji** dulu bila mungkin (salin folder + `.env` + cadangan → `PASANG.cmd`).
4. **Naikkan satu komponen per waktu**, lalu jalankan uji cepat (bagian 8).
5. Pilih waktu di luar jam kerja; pengguna akan terputus 1–10 menit.
6. Catat di **Pusat Kendali → Riwayat** atau buku log: tanggal, versi lama → baru, siapa.

| Istilah | Arti |
|---|---|
| **Patch** (11.4.5 → 11.4.7) | perbaikan bug/keamanan, aman |
| **Minor/mayor** (11.4 → 11.8, 6.1 → 6.2) | fitur baru, bisa mengubah struktur data |
| **Downgrade** | kembali ke versi lama; untuk database **selalu lewat cadangan** |

---

## 3. Superset

Komponen paling sensitif: modul ALDx (`config/sps_*`) memakai bagian dalam Superset.

### Upgrade (mis. 6.1.0 → 6.2.0)
```powershell
scripts\cadangkan.ps1 -Engine
# ubah .env: SUPERSET_VERSION=6.2.0
docker compose build --pull                              # image baru + driver dari docker/wheels
docker compose run --rm superset superset db upgrade     # struktur metadata versi baru
docker compose run --rm superset superset init
scripts\start.ps1
scripts\build-dashboards.ps1                             # menu, izin, dashboard as code
scripts\uji.ps1                                          # uji otomatis (bagian 8)
```
Bila `uji.ps1` atau halaman Studio / Pusat Kendali / Asisten AI error: lakukan downgrade, lalu
laporkan pesan galat ke pengembang (bagian modul yang perlu disesuaikan).

### Downgrade (kembali ke 6.1.0)
`db upgrade` mengubah struktur metadata; versi lama tidak bisa membacanya. Jadi:
```powershell
scripts\stop.ps1
# ubah .env: SUPERSET_VERSION=6.1.0
docker compose build
docker compose up -d metadb
scripts\cadangkan.ps1 -Pulihkan backup\metadb-<sebelum-upgrade>.dump
scripts\start.ps1
```
Perubahan (chart/dashboard baru) yang dibuat **setelah** cadangan akan hilang.

### Driver Python (semua jenis database, LDAP, impor berkas)
Jaringan kantor memblokir pypi.org dari dalam Docker, jadi driver dipasang dari `docker/wheels/`.
Ganti berkas `.whl` (unduh di komputer yang punya internet, versi `cp310`/`manylinux`), lalu
`docker compose build` dan `scripts\start.ps1`. Lihat `docker/wheels/README.md`.

---

## 4. PostgreSQL (metadb)

### Rilis kecil (mis. 17.5 → 17.6) — otomatis
`METADB_VERSI=17` selalu mengambil rilis 17.x terbaru (perbaikan keamanan; format data sama).
```powershell
scripts\cadangkan.ps1
docker compose pull metadb
scripts\start.ps1
```

### Versi utama (mis. 17 → 18) — lewat cadangan
Berkas data PostgreSQL **tidak bisa** dibuka langsung oleh versi utama lain (naik maupun turun).
Caranya sama untuk upgrade dan downgrade: cadangkan, buat volume baru, pulihkan.
```powershell
scripts\cadangkan.ps1                    # catat nama berkas backup\metadb-....dump
scripts\stop.ps1
docker compose rm -f metadb
docker volume rm sps_metadb_pg           # menghapus data metadb (cadangan harus ada!)
# ubah .env: METADB_VERSI=18   (downgrade: kembali ke 17)
docker compose up -d metadb
scripts\cadangkan.ps1 -Pulihkan backup\metadb-<terakhir>.dump
scripts\start.ps1
scripts\uji.ps1
```
Lakukan dulu di server uji.

### Dari versi lama (metadata di MySQL XAMPP / MariaDB)
Tidak perlu langkah di atas: `PASANG.cmd` mendeteksi dan memindahkan otomatis
(`scripts\pindah-metadata.ps1`, rincian di [18-installer.md](18-installer.md)).

---

## 5. ClickHouse (ALDx Engine)

### Upgrade (mis. 25.8 → 26.3)
```powershell
scripts\cadangkan.ps1 -Engine
# ubah .env: ENGINE_VERSI=26.3
docker compose pull engine
docker compose up -d engine
docker compose exec engine clickhouse-client --user sps --password -q "SELECT version()"
```
Naik dari LTS ke LTS berikutnya umumnya aman. Setelah naik, ClickHouse **menulis format baru**
saat tabel digabung (merge), sehingga downgrade di tempat tidak dijamin.

### Downgrade
```powershell
docker compose stop engine
docker compose rm -f engine
docker volume rm sps_engine
# ubah .env: ENGINE_VERSI=25.8
docker compose up -d engine
scripts\cadangkan.ps1 -PulihkanEngine backup\engine\engine-<sebelum-upgrade>.zip
```
Tanpa cadangan engine: ekstrak bisa diisi ulang lewat **Segarkan → Penuh**, ramalan diperbarui
otomatis pukul 03:00, data latihan lewat `scripts\data-latihan.ps1`. Data **upload** hilang.

---

## 6. Redis & nginx (gateway)

Keduanya **tidak menyimpan data permanen**; naik/turun versi bebas:
```powershell
# ubah .env: REDIS_VERSI=8.0   atau   GATEWAY_VERSI=1.30
docker compose pull redis gateway
docker compose up -d redis gateway
```
Isi cache hilang (chart pertama setelahnya sedikit lebih lambat). Pengguna mungkin perlu login ulang.

---

## 7. Docker Desktop & Windows

- Perbarui Docker Desktop lewat menu **Check for updates** di luar jam kerja.
- Setelah pembaruan, cek **Settings → Resources** (CPU/RAM) tidak kembali ke bawaan, lalu
  `scripts\terapkan-server.ps1`.
- Restart Windows: container menyala sendiri (`restart: unless-stopped`) setelah Docker Desktop
  terbuka. Aktifkan **Start Docker Desktop when you sign in**.

---

## 8. Uji setelah upgrade

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uji.ps1
```
Uji otomatis memeriksa: semua container sehat, koneksi metadb/engine/Redis, backgrounder,
query Studio (23 jenis chart), ekstrak (buat-segarkan-hapus), ramalan, dan izin halaman.
Lalu lakukan uji manual singkat dari [pengujian/skenario-uji.md](pengujian/skenario-uji.md)
(bagian "Uji asap", ±15 menit).

**Upgrade versi Superset (mayor)** wajib lulus **uji tampilan** lebih dulu: ubah `SUPERSET_VERSION` di `.env.example`
pada cabang baru, buka pull request, dan tunggu workflow **uji** (GitHub Actions) hijau. Uji tampilan memeriksa bagian
ALDx yang menempel pada tampilan Superset (bingkai aplikasi, bilah atas dashboard, Telusuri, Studio), yang paling mudah
rusak saat Superset berubah ([pengujian §1b](pengujian/README.md#1b-uji-tampilan-otomatis-ci)).

## 9. Jadwal perawatan yang disarankan

| Kapan | Apa |
|---|---|
| Harian 01:00 | `scripts\cadangkan.ps1` (Task Scheduler) |
| Mingguan | `scripts\cadangkan.ps1 -Engine`; salin folder `backup\` ke NAS |
| Bulanan | `docker compose pull` + `docker compose up -d` (patch dalam seri), `scripts\uji.ps1` |
| Per 6–12 bulan | evaluasi naik versi PostgreSQL/ClickHouse LTS & Superset (di server uji dulu) |
