# 19 · Runbook & FAQ Admin Server

Pegangan admin saat **menyalakan, mematikan, memeriksa, dan memulihkan** ALDx.
Ditulis berurutan seperti prosedur: ikuti dari atas, jangan lompat.
Versi kelas (latihan, simulasi gangguan, kuis): [bahan-ajar/modul-runbook-admin.md](bahan-ajar/modul-runbook-admin.md).
Kartu ringkas untuk ditempel: [§7](#7-kartu-perintah-ringkas).

> Semua perintah dijalankan di **PowerShell** dari folder `D:\superset`
> (`cd D:\superset`). Bila muncul *running scripts is disabled*, lihat [FAQ 1](#6-faq-admin).

---

## 1. Susunan komponen & urutan menyala

Komponen menyala **berlapis**. Lapisan atas hanya sehat bila lapisan di bawahnya sehat.

| Lapis | Komponen | Container | Fungsi | Sehat bila |
|---|---|---|---|---|
| 0 | Windows, **Docker Desktop**, jaringan/VPN; *(opsional)* **Ollama / LM Studio** untuk Asisten AI | – | tempat semua berjalan; jalur ke AD & sumber data | Docker Desktop **Running** |
| 1 | **metadb** (PostgreSQL) | `sps_metadb` | user, dashboard, koneksi, pengaturan | `healthy` |
| 1 | **engine** (ClickHouse) | `sps_engine` | ekstrak, impor berkas, ramalan | `healthy` |
| 1 | **redis** | `sps_redis` | cache & antrean tugas | `healthy` |
| 2 | **superset** (web) | `sps_superset` | halaman web & API | `healthy` (±1–2 menit) |
| 3 | **superset-worker**, **superset-beat** | `sps_superset_worker`, `sps_superset_beat` | tugas latar: ekstrak, laporan, jadwal | `running` |
| 4 | **gateway** (nginx) | `sps_gateway` | pintu masuk `http://server:8088` | `running` |

Docker menjaga urutan ini sendiri (`depends_on: service_healthy`), jadi **satu perintah**
`scripts\start.ps1` sudah cukup. Urutan di tabel dipakai saat **mencari penyebab**:
periksa dari lapis 0 ke atas, berhenti pada lapis pertama yang tidak sehat.

```
Browser ──► gateway ──► superset ──┬──► metadb   (wajib)
                          ▲        ├──► redis    (wajib)
          worker/beat ────┘        └──► engine   (wajib)
                                         sumber data kantor (Oracle, SQL Server, ...) lewat jaringan
```

---

## 2. Prosedur standar (SOP)

### 2.1 Menyalakan (pagi / setelah server restart)

| # | Langkah | Perintah / tindakan | Hasil yang benar |
|---|---|---|---|
| 1 | Nyalakan Docker Desktop | buka aplikasi, tunggu ikon paus berhenti bergerak | status **Engine running** |
| 2 | (Bila pakai LDAP / sumber kantor) sambungkan VPN | – | `Test-NetConnection 10.x.x.x -Port 389` = True |
| 3 | Nyalakan semua container | `powershell -ExecutionPolicy Bypass -File scripts\start.ps1` | "Superset berjalan. Buka http://localhost:8088" |
| 4 | Tunggu sehat | `docker compose ps` (ulang tiap 30 detik) | semua `running`, kolom kesehatan `healthy` |
| 5 | Uji otomatis | `powershell -ExecutionPolicy Bypass -File scripts\uji.ps1` | `N/N lulus` |
| 6 | Buka web | `http://localhost:8088` → login | dashboard tampil |

Container memakai `restart: unless-stopped`: setelah Windows restart, container **ikut menyala
sendiri** begitu Docker Desktop menyala, kecuali sebelumnya dimatikan dengan `stop.ps1`.
Langkah 3 tetap aman dijalankan (tidak mengubah apa pun bila sudah menyala).

### 2.2 Mematikan (pemeliharaan / sebelum mematikan server)

| # | Langkah | Perintah |
|---|---|---|
| 1 | Umumkan ke pengguna (±10 menit sebelumnya) | – |
| 2 | Cadangkan | `powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1` |
| 3 | Matikan semua container | `powershell -ExecutionPolicy Bypass -File scripts\stop.ps1` |
| 4 | (Opsional) tutup Docker Desktop | klik kanan ikon paus → Quit |

Urutan mati dibalik otomatis oleh Docker (gateway & web dulu, database terakhir).
Data **tidak hilang** saat dimatikan: tersimpan di volume `sps_metadb` dan `sps_engine`.

### 2.3 Restart satu komponen

| Kebutuhan | Perintah |
|---|---|
| Web lambat / error aneh | `docker compose restart superset` |
| Tugas latar macet (ekstrak tidak jalan) | `docker compose restart superset-worker superset-beat` |
| Cache bermasalah | `docker compose restart redis` |
| Engine bermasalah | `docker compose restart engine` lalu `docker compose restart superset-worker` |
| metadb bermasalah | `docker compose restart metadb` lalu `docker compose restart superset superset-worker superset-beat` |

Aturan: **setelah me-restart lapis bawah, restart juga lapis di atasnya** (koneksi lama terputus).

### 2.4 Setelah mengubah sesuatu

| Yang diubah | Yang harus dijalankan |
|---|---|
| Pengaturan di **Pusat Kendali** (batas, cache, identitas, tema) | tidak ada; berlaku otomatis (beberapa butuh "Terapkan", ditandai di layar) |
| Isi **`.env`** | `scripts\start.ps1` (container dibuat ulang dengan nilai baru) |
| Berkas di **`config\`** (`.py`, `.yaml`) | `docker compose restart superset superset-worker superset-beat` |
| Driver baru di **`docker\wheels\`** | `docker compose build` lalu `scripts\start.ps1` |
| Versi baru aplikasi disalin ke `D:\superset` | `PASANG.cmd` (aman diulang; data tetap) lalu `scripts\uji.ps1` |
| Versi komponen di `.env` (`*_VERSI`) | ikuti [16-upgrade-downgrade.md](16-upgrade-downgrade.md) |

### 2.5 Cadangan & pemulihan

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1            # metadata (harian)
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Engine    # + isi ALDx Engine (mingguan)
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Pulihkan backup\metadb-YYYYMMDD-HHMM.dump
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -PulihkanEngine backup\engine\engine-YYYYMMDD-HHMM.zip
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -UjiPulih   # bukti cadangan terbaru bisa dipulihkan
powershell -ExecutionPolicy Bypass -File scripts\jadwal-cadangan.ps1       # jadwal harian + uji pulih mingguan
```
Status cadangan & uji pulih terakhir: Pusat Kendali › Status, kartu **Cadangan terakhir**.
Simpan juga salinan **`.env`** di tempat aman (tanpa `SUPERSET_SECRET_KEY` yang sama, password
koneksi yang tersimpan tidak bisa dibuka). Jadwal otomatis: [tutorial Level 4 §8](tutorial/level-4-admin-server.md#8-cadangan--pemulihan).

---

## 3. Cek kesehatan 5 menit (harian)

| # | Periksa | Perintah | Normal |
|---|---|---|---|
| 1 | Status container | `docker compose ps` | 7 container `running`, database `healthy` |
| 2 | Uji otomatis | `scripts\uji.ps1` | `lulus` semua |
| 3 | Pemakaian | Pusat Kendali → **Status** | CPU/RAM di bawah garis merah, antrean ≈ 0 |
| 4 | Ekstrak | Pusat Kendali → **Ekstrak** | tidak ada status **Gagal** |
| 5 | Disk | Docker Desktop → Settings → Resources | sisa disk > 20% |
| 6 | Cadangan | isi folder `backup\` | ada berkas `metadb-*.dump` hari ini |

---

## 4. Mencari penyebab gangguan (pohon keputusan)

Selalu mulai dari **lapis bawah**. Laporan lengkap sekali jalan:
`powershell -ExecutionPolicy Bypass -File scripts\diagnose.ps1` → `diagnosa.txt`.

### 4.1 Web tidak bisa dibuka

1. Docker Desktop **Running**? Tidak → nyalakan, tunggu, ulangi.
2. `docker compose ps` → ada container tidak muncul / `exited`?
   → `scripts\start.ps1`, lalu `docker compose logs --tail 50 <nama>` untuk yang mati.
3. `metadb`/`engine`/`redis` = `unhealthy`/`restarting`? (Sejak 2026.11.10 `superset_worker` & `superset_beat`
   diperiksa dari proses celery-nya; versi lama selalu tampil `unhealthy` walau bekerja normal.)
   → lihat log komponen itu; penyebab tersering **RAM/disk habis** → naikkan di Docker Desktop.
4. `superset` = `starting` lebih dari 3 menit / `restarting`?
   → `docker compose logs --tail 80 superset`, cari baris `Error`. Cocokkan dengan [04-troubleshooting.md](04-troubleshooting.md).
5. Semua sehat tetapi browser menolak?
   → port bentrok (`port is already allocated`) atau firewall Windows. Coba `http://localhost:8089` (jalur langsung tanpa gateway).

### 4.2 Bisa buka web tapi tidak bisa login

1. Akun lokal `admin` bisa? Bisa → masalah di **LDAP** (lanjut 2). Tidak → reset password admin ([FAQ 6](#6-faq-admin)).
2. `scripts\test-ldap.ps1` → baca pesannya (server tak terjangkau / user tidak ditemukan).
3. VPN tersambung? Bila Windows bisa menjangkau AD tetapi container tidak: restart Docker Desktop **setelah** VPN tersambung.

### 4.3 Dashboard lambat / chart error

1. Chart error menyebut koneksi sumber (*timed out*, *DPY-*, *Login failed*) → sumber data/VPN, bukan ALDx.
2. Semua chart lambat → Pusat Kendali → Status: CPU/RAM penuh? antrean menumpuk?
   → naikkan batas di Pusat Kendali → Pengaturan, atau tambah node ([11](11-pusat-kendali-server.md)).
3. Dataset besar dari sumber lambat → buat **ekstrak** ke ALDx Engine ([13](13-sps-engine-ekstrak.md)).
4. Tidak tahu chart mana yang lambat → **Kelola › Kesehatan kueri**: chart & dashboard diurutkan menurut p95,
   lengkap dengan saran perbaikan ([26 §7d](26-langganan-versi-ponsel-lihat-sebagai.md)).

### 4.4 Ekstrak / impor gagal

1. Data → Ekstrak ke ALDx Engine → **Riwayat**: baca pesan galat.
2. "ALDx Engine mati" → `docker compose restart engine superset-worker`.
3. Tidak pernah berjalan sesuai jadwal → `superset-beat` mati → `docker compose restart superset-beat`.

### 4.5 Hubungkan data gagal

| Pesan di wizard | Arti | Tindakan |
|---|---|---|
| *timed out* / *could not connect* / *Unable to connect* | server tidak terjangkau dari Docker | cek alamat & port, VPN, firewall server database |
| *authentication failed* / *Login failed* / *Access denied* | user/password salah atau tidak berhak | minta akun hanya-baca ke DBA |
| *Driver ... belum terpasang* | paket Python belum ada di image | tambah `.whl` di `docker\wheels\` ([README](../docker/wheels/README.md)) |
| *database ... does not exist* | nama database / service salah | cek ejaan, huruf besar-kecil |

---

## 5. Perintah penting (rujukan)

| Tujuan | Perintah |
|---|---|
| Nyalakan / matikan | `scripts\start.ps1` / `scripts\stop.ps1` |
| Status | `docker compose ps` |
| Log satu komponen | `docker compose logs --tail 100 superset` (ganti `superset` dengan nama lain) |
| Log terus berjalan | `scripts\logs.ps1` (berhenti: Ctrl+C) |
| Uji otomatis | `scripts\uji.ps1` (rinci: `-Rinci`) |
| Diagnosa lengkap | `scripts\diagnose.ps1` → `diagnosa.txt` |
| Versi semua komponen | `scripts\versi.ps1` |
| Memastikan installer asli & utuh | `Get-FileHash ALDx-Setup.exe` = baris di `ALDx-SHA256.txt` rilis `v<VERSI>` ([29](29-versi-pembaruan-hapus-total.md#versi-yang-bisa-dicocokkan-dengan-rilis-github)) |
| Masuk ke dalam container | `docker compose exec superset bash` (keluar: `exit`) |
| Query metadb langsung | `docker compose exec metadb psql -U superset -d sps_superset` (keluar: `\q`) |
| Query engine langsung | `docker compose exec engine clickhouse-client` (keluar: `exit`) |
| Bersihkan sisa image | `scripts\cleanup.ps1` |
| Bangun ulang dashboard bawaan & menu | `scripts\build-dashboards.ps1` |
| Terbitkan installer online/offline/HapusTotal (pengembang) | `.\scripts\sinkron-laptop.ps1 -Terbitkan` (Inno Setup & GitHub CLI dipasang otomatis; galat "GitHub CLI belum login" = jalankan lagi, browser login terbuka) |
| Muat ulang data latihan | `scripts\data-latihan.ps1` (± 20 detik; `-Skala 4` = ± 9,3 juta baris data harian untuk demo kecepatan) |

Semua skrip dijalankan dengan `powershell -ExecutionPolicy Bypass -File scripts\<nama>.ps1`.

---

## 6. FAQ admin

**1. Muncul "running scripts is disabled on this system".**
Kebijakan PowerShell Windows. Pakai `powershell -ExecutionPolicy Bypass -File ...` (tidak
mengubah setelan komputer), atau sekali saja untuk akun Anda:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Berkas hasil unduhan juga perlu
dibuka blokirnya: `Get-ChildItem D:\superset -Recurse -File | Unblock-File`.

**2. Urutan menyalakan yang benar?**
Docker Desktop → (VPN) → `scripts\start.ps1`. Urutan antar-container diatur Docker sendiri ([§1](#1-susunan-komponen--urutan-menyala)).

**3. Server mati listrik. Apa yang harus dilakukan?**
Nyalakan server dan Docker Desktop, tunggu 2 menit, lalu `docker compose ps` dan `scripts\uji.ps1`.
PostgreSQL & ClickHouse memulihkan diri otomatis. Bila metadb tidak mau sehat: pulihkan cadangan terakhir ([§2.5](#25-cadangan--pemulihan)).

**4. Apakah `stop.ps1` menghapus data?**
Tidak. Yang menghapus data hanya `docker volume rm ...` (lihat [04 § Mulai ulang dari nol](04-troubleshooting.md#mulai-ulang-dari-nol)).

**5. Sudah ubah `.env`, kok tidak berubah?**
`.env` dibaca saat container dibuat. Jalankan `scripts\start.ps1` (bukan hanya `restart`).

**6. Lupa password admin.**
`docker compose exec superset superset fab reset-password --username admin --password PASSWORD_BARU`

**7. Web hanya bisa dibuka dari server, tidak dari komputer lain.**
Buka port `SUPERSET_PORT` (bawaan 8088) di Windows Firewall:
`New-NetFirewallRule -DisplayName "ALDx" -Direction Inbound -Protocol TCP -LocalPort 8088 -Action Allow` (PowerShell sebagai Administrator).

**8. Disk penuh.**
`scripts\cleanup.ps1` (sisa image), hapus cadangan lama di `backup\` setelah disalin ke tempat lain,
lalu Data → Ekstrak ke ALDx Engine: hapus ekstrak yang tidak dipakai.

**9. Bagaimana tahu siapa mengubah pengaturan?**
Pusat Kendali → **Riwayat** (pengaturan, identitas) dan Superset → Settings → **Action Log** (aktivitas pengguna).

**10. Bolehkah mematikan XAMPP setelah pindah ke PostgreSQL?**
Ya, setelah `scripts\uji.ps1` lulus. Metadata sudah di container `metadb`; data XAMPP tidak dihapus (cadangan).

**11. Bagaimana memperbarui ke versi aplikasi baru?**
Cadangkan → salin berkas versi baru ke `D:\superset` (`.env` & `backup\` jangan ditimpa) → `PASANG.cmd` → `scripts\uji.ps1`.

**12. Mengganti logo, nama, warna?**
Pusat Kendali → **Identitas & Tema**. Tanpa restart. Logo perusahaan diunggah di tab yang sama.

**12a. Kartu SAP HANA abu-abu di Hubungkan data?**
Driver SAP (`hdbcli`) tidak disertakan karena lisensinya. Unduh `hdbcli-*.whl`, taruh di `docker\wheels\`, jalankan
`scripts\init.ps1` ([06 §4](06-sumber-data.md#4-menambah-jenis-database-baru-pengembang)). Fitur lain tidak terpengaruh.

**13. Menambah sumber data baru?**
Pusat Kendali → **Hubungkan data** (database, data warehouse, atau berkas Access/Excel/CSV). Lihat [06-sumber-data.md](06-sumber-data.md).

**14. Pengguna mengeluh tidak melihat data.**
Hak akses baris (RLS): cek role pengguna di Settings → List Users, aturan di Settings → Row Level Security,
dan panduan [08-hak-akses-data.md](08-hak-akses-data.md).

**15. Docker Desktop meminta update. Aman?**
Ya, tetapi lakukan di luar jam kerja: cadangkan → `stop.ps1` → update → `start.ps1` → `uji.ps1`.

**16. Asisten AI tidak bisa menjawab / model tidak terhubung?**
Buka panel Asisten AI (`Ctrl + I`) › ikon **sambung**: layar itu menunjukkan aplikasi lokal mana yang menyala,
model yang terdeteksi, dan key cloud yang terisi. Langkah & tabel masalah: [28-sambungkan-asisten-ai.md](28-sambungkan-asisten-ai.md).
Model lokal (Ollama / LM Studio) dipasang sendiri di Windows, bukan di Docker.

**16b. Komputer lain tampil beda / fitur baru tidak ada?**
Setup.exe berisi versi saat dibangun; `git pull` selalu terbaru. Samakan versinya:
[29 §1](29-versi-pembaruan-hapus-total.md). Menghapus tanpa sisa: [29 §3](29-versi-pembaruan-hapus-total.md).

**16c. Pengguna tidak melihat menu / tombol Asisten AI?**
Akun hanya ber-role *Pengguna* (tanpa Gamma) atau *Superadmin* (tanpa Admin). Sejak 2026.11.10 role pendamping
dilengkapi otomatis dan **disimpan** saat akun dimuat; minta pengguna memuat ulang halaman. `scripts\uji.ps1` memeriksa
semua akun (*Role pendamping lengkap & tersimpan*). Pengguna tetap hanya melihat dataset yang izinnya diberikan
ke role Gamma/Pengguna.

**17. Apa yang harus dicadangkan di luar server?**
Folder `backup\` dan berkas `.env`. Keduanya berisi rahasia: simpan di lokasi terbatas.

**18. Bagaimana memakai HTTPS? Browser menulis "tidak aman".**
Centang **Pakai HTTPS** di installer (atau `.env` `SPS_HTTPS=1`) lalu `scripts\terapkan-server.ps1`. Sertifikat dibuat
otomatis. Peringatan browser hilang setelah `scripts\percayai-sertifikat.ps1` dijalankan di komputer pengguna, atau
pakai sertifikat kantor di `server\tls\` ([11 §9b](11-pusat-kendali-server.md#https)).

**20. Siapa mengunduh data / mengubah hak akses minggu lalu?**
Pusat Kendali › **Riwayat** › *Jejak audit*: pilih kelompok & periode, cari nama, **Unduh CSV** untuk pemeriksa.
Disimpan 365 hari (Pengaturan › `keamanan.audit_simpan_hari`).

**21. Superadmin satu-satunya terkunci karena salah password.**
Tunggu 15 menit, atau di server: `scripts\buka-kunci.ps1 -Akun <email>`.

**19. LDAP mati / belum ada. Bisa login?**
Bisa. Superadmin & akun ber-email selalu akun lokal. LDAP hanya untuk login dengan akun jaringan kantor dan boleh diaktifkan nanti ([05](05-login-ldap.md)).

---

## 7. Kartu perintah ringkas

Cetak halaman ini (atau versi PDF di `docs\pdf\`) dan tempel di dekat server.

```
ALDx — KARTU ADMIN                              (cd D:\superset)
──────────────────────────────────────────────────────────────────
NYALAKAN     1 Docker Desktop  2 VPN  3 scripts\start.ps1  4 scripts\uji.ps1
MATIKAN      scripts\cadangkan.ps1  →  scripts\stop.ps1
STATUS       docker compose ps         (semua running/healthy)
LOG          docker compose logs --tail 100 <superset|metadb|engine|redis|gateway>
RESTART      docker compose restart <nama>     (lapis bawah → restart lapis atas juga)
DIAGNOSA     scripts\diagnose.ps1  →  diagnosa.txt
CADANGAN     scripts\cadangkan.ps1 [-Engine]   jadwal: scripts\jadwal-cadangan.ps1
UJI PULIH    scripts\cadangkan.ps1 -UjiPulih   (tidak mengubah data)
UJI BEBAN    scripts\uji-beban.ps1 -Akun <email> -Pengguna 50   (di luar jam kerja)
PULIHKAN     scripts\cadangkan.ps1 -Pulihkan backup\metadb-....dump
UPDATE APP   cadangkan → salin versi baru → PASANG.cmd → uji.ps1
RESET ADMIN  docker compose exec superset superset fab reset-password --username admin --password BARU
Skrip .ps1:  powershell -ExecutionPolicy Bypass -File scripts\<nama>.ps1
Urutan cek:  Docker → metadb/engine/redis → superset → worker/beat → gateway
```
