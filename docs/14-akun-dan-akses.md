# 14 · Akun & Cara Akses Setiap Komponen

Dokumen ini mencatat **semua akun** yang dipakai ALDx dan **cara masuk** ke setiap komponen
Docker. Password **tidak ditulis di sini**; dokumen ini hanya menunjukkan di mana password disimpan.

> **Aturan emas:** semua password ada di berkas `D:\superset\.env`. Berkas itu rahasia:
> jangan dikirim lewat chat/email, jangan di-commit ke git, dan cadangkan di tempat aman.

---

## 1. Peta komponen

```
                       Komputer server (Windows + Docker Desktop)
 Browser pengguna      ┌──────────────────────────────────────────────────────────────┐
 http://server:8088 ──►│ gateway (nginx)  ─► superset (web)    ─► metadb  (PostgreSQL)│
                       │                    superset-worker ──► engine  (ClickHouse) │
                       │                    superset-beat   ──► redis   (cache)      │
                       └──────────────────────────────┬───────────────────────────────┘
                                                      ▼
                       sumber data perusahaan (Hubungkan data) · LDAP/AD kantor (opsional)
```

| Container | Nama Docker | Fungsi | Peran |
|---|---|---|---|
| `gateway` | `sps_gateway` | pintu masuk web, pembagi beban | Gateway |
| `superset` | `sps_superset` | web aplikasi | tampilan & API |
| `superset-worker` | `sps_superset_worker` | backgrounder (query async, ekstrak, laporan) | Backgrounder |
| `superset-beat` | `sps_superset_beat` | penjadwal tugas | Backgrounder scheduler |
| `metadb` | `sps_metadb` | metadata: user, chart, dashboard, pengaturan | Repository |
| `engine` | `sps_engine` | ALDx Engine: ekstrak, upload, ramalan | mesin data analitik |
| `redis` | `sps_redis` | cache & antrean | Cache Server |

---

## 2. Daftar akun

| Akun | Dipakai untuk | Username | Password disimpan di | Siapa memegang |
|---|---|---|---|---|
| **Admin aplikasi** | login darurat & pengelolaan Superset | **email Superadmin** dari installer (`ADMIN_USERNAME` di `.env`; instalasi lama `admin`) | **tidak disimpan**; diisi saat instalasi (lihat 4.1 bila lupa) | Admin server |
| **Pengguna – akun lokal** | login harian (tanpa LDAP) | dibuat Admin di Settings → List Users | metadb (terenkripsi) | masing-masing pengguna |
| **Pengguna – LDAP** (opsional) | login harian | username jaringan kantor | Active Directory kantor | masing-masing pengguna |
| **metadb** (PostgreSQL) | Superset membaca/menulis metadata; perawatan | `.env` → `METADB_USER` (`superset`, pemilik database) | `.env` → `METADB_PASSWORD` | sistem / Admin server |
| **engine** | Superset & admin ke ALDx Engine | `.env` → `ENGINE_USER` (`sps`) | `.env` → `ENGINE_PASSWORD` | sistem / Admin data |
| **redis** | cache & antrean | (tanpa username) | `.env` → `REDIS_PASSWORD` | sistem |
| **Sumber data** (wizard Hubungkan data) | membaca data perusahaan | diisi di wizard | metadb, **terenkripsi** dengan `SUPERSET_SECRET_KEY` | DBA pemilik sumber |
| **Sumber data profil DJP** (opsional) | Oracle DMP/IKU/Dashboard, ClickHouse DMP_OLAP | `.env` → `ORACLE_*_USER`, `CLICKHOUSE_USER` | `.env` → `ORACLE_*_PASSWORD`, `CLICKHOUSE_PASSWORD` | pemilik sumber data |
| **Model AI cloud** | Asisten AI (opsional) | – | `.env` → `AI_*_API_KEY` | Admin server |
| **SECRET_KEY** | mengenkripsi password koneksi di metadb | – | `.env` → `SUPERSET_SECRET_KEY` | **jangan diganti** |

Password `REDIS_PASSWORD`, `METADB_PASSWORD`, `ENGINE_PASSWORD`, dan
`SUPERSET_SECRET_KEY` dibuat **acak otomatis** oleh installer (`PASANG.cmd`).

### Peran (role) di aplikasi

| Role | Isi | Diberikan ke |
|---|---|---|
| `Superadmin` | Admin + pengaturan vital (Pengaturan, Batas data, Hak akses, `/hw-engineer`) | akun `ADMIN_USERNAME` & `SPS_SUPERADMIN_USERS` otomatis; lainnya oleh Superadmin ([24](24-superadmin-dan-batas-data.md)) |
| `Admin` | semua, termasuk Pusat Kendali (tanpa pengaturan vital) | akun admin lokal & `LDAP_ADMIN_USERS` |
| `Alpha` | membuat chart/dataset dari tabel mana pun (bisa melewati RLS) | perorangan, hati-hati |
| `Gamma` | melihat dashboard yang diizinkan | **bawaan pengguna baru** (`LDAP_DEFAULT_ROLE`) |
| `Pengguna` (`SPS_ROLE_PENGGUNA`) | menu Studio Visual & Asisten AI, membaca dataset (tetap dibatasi RLS) | semua pengguna |
| `sql_lab` | SQL Lab & **Kueri Visual** | pengguna berperan **Analis** (installer) |

Peran di tabel pengguna installer: **Pengguna** = Gamma + Pengguna · **Analis** = Gamma + Pengguna + sql_lab · **Admin** = Admin · **Superadmin** = Admin + Superadmin.
| role buatan Anda (mis. `Cabang Jakarta`) | kelompok untuk aturan RLS | Settings → List Roles; kemampuan di Pusat Kendali → Hak akses |
| `DJP Pegawai`, `DJP Kanwil`, … | role profil DJP (otomatis dari `akses.yaml`) | hanya instalasi DJP |

---

## 3. Cara masuk ke setiap komponen

Semua perintah dijalankan di **PowerShell** dari folder `D:\superset`.

### 3.1 Aplikasi web (semua pengguna)

| Halaman | Alamat |
|---|---|
| Aplikasi | `http://<nama-server>:8088` |
| Studio Visual | `http://<nama-server>:8088/studio/` |
| Pusat Kendali (Admin) | `http://<nama-server>:8088/pusat-kendali/` |
| Asisten AI | `http://<nama-server>:8088/asisten/` |
| Langsung ke web tanpa gateway (diagnosa, hanya dari server) | `http://localhost:8089` |

### 3.2 Melihat status & log semua container

```powershell
docker compose ps                      # status & kesehatan (healthy/unhealthy)
powershell -File scripts\logs.ps1      # log Superset
docker compose logs --tail 100 engine  # log satu container (ganti nama: metadb, redis, gateway, ...)
powershell -File scripts\versi.ps1     # versi setiap komponen
powershell -File scripts\diagnose.ps1  # kumpulkan info masalah ke diagnosa.txt
```

### 3.3 metadb (PostgreSQL) – metadata

**Lewat terminal di dalam container** (tanpa password, hanya dari server):
```powershell
docker compose exec metadb psql -U superset -d sps_superset
# contoh: \dt   (daftar tabel)   select username, active from ab_user;   \q (keluar)
```

**Lewat aplikasi database** (DBeaver / pgAdmin / HeidiSQL) di komputer server:

| Isian | Nilai |
|---|---|
| Host | `127.0.0.1` |
| Port | `5433` (`METADB_PORT_HOST`) |
| User | `superset` (`METADB_USER`) |
| Password | `METADB_PASSWORD` di `.env` |
| Database | `sps_superset` |

> Jangan mengubah tabel metadata langsung kecuali diminta panduan; gunakan menu aplikasi.
> Sebelum perubahan apa pun: `scripts\cadangkan.ps1`.

### 3.4 engine (ClickHouse) – ALDx Engine

**SQL di browser** (bawaan ClickHouse) dari komputer server: `http://localhost:8124/play`
→ isi user `sps` dan password `ENGINE_PASSWORD`.

**Lewat terminal:**
```powershell
docker compose exec engine clickhouse-client --user sps --password
# contoh: SHOW TABLES FROM sps_engine;  SELECT count() FROM sps_engine.latihan_penjualan;
```

**DBeaver**: driver ClickHouse, host `127.0.0.1`, port `8124`, database `sps_engine`.

Dari aplikasi Superset: koneksi **ALDx Engine (ClickHouse)** di SQL Lab (sesuai izin).

### 3.5 redis – cache & antrean

```powershell
docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning info memory'
docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 0 llen ekstrak'   # antrean menunggu
```
Isi Redis aman dikosongkan (hanya cache): `scripts\stop.ps1` lalu `scripts\start.ps1`.

### 3.6 superset / worker / beat – aplikasi

```powershell
docker compose exec superset bash                  # masuk ke container web
docker compose exec superset superset fab list-users
docker compose exec superset-worker celery -A superset.tasks.celery_app:app inspect active   # tugas berjalan
```

### 3.7 gateway (nginx)

Tidak punya akun. Konfigurasi `server\gateway.conf` dibuat ulang oleh `scripts\terapkan-server.ps1`.
```powershell
docker compose exec gateway nginx -t              # cek konfigurasi
```

---

## 4. Tugas akun yang sering ditanyakan

### 4.1 Lupa password admin aplikasi
```powershell
docker compose exec superset superset fab reset-password --username <email-superadmin> --password <PasswordBaru>
```
Atau jalankan ulang `PASANG.cmd` lalu isi password baru (data tidak berubah).

### 4.2 Menjadikan pengguna Admin
Akun lokal: **Settings → List Users** → edit → tambah role `Admin`.
LDAP: isi username di `.env` → `LDAP_ADMIN_USERS=user1,user2` (Admin) atau `SPS_SUPERADMIN_USERS=user1` (Admin + Superadmin),
lalu `scripts\start.ps1` (`docker compose up -d`); berlaku saat login berikutnya (keluar lalu login lagi).

### 4.3 Mengganti password sumber data
**Settings → Database Connections** → edit koneksi → isi password baru → **Test connection** → **Finish**.
Profil DJP (koneksi dari `.env`): ubah `ORACLE_*_PASSWORD` / `CLICKHOUSE_PASSWORD` → `scripts\add-connections.ps1`.

### 4.4 Mengganti password container (metadb, engine, redis)
Password ini dipakai saat volume pertama kali dibuat. Menggantinya perlu dua langkah:

| Komponen | Langkah |
|---|---|
| redis | ubah `REDIS_PASSWORD` di `.env` → `docker compose up -d` (Redis tidak menyimpan data) |
| engine | `docker compose exec engine clickhouse-client --user sps --password -q "ALTER USER sps IDENTIFIED BY '<baru>'"` → ubah `ENGINE_PASSWORD` di `.env` → `docker compose up -d` |
| metadb | `docker compose exec metadb psql -U superset -d sps_superset -c "ALTER USER superset PASSWORD '<baru>'"` → ubah `METADB_PASSWORD` di `.env` → `scripts\start.ps1` |

Hindari tanda `$ " ' \` # spasi` di password (merusak `.env`).

### 4.5 Akun terkunci (salah password berulang)
Setelah **5 kali** salah password berturut-turut, akun dikunci **15 menit** (akun email maupun NIP LDAP); selama itu
password benar pun ditolak dan halaman login menampilkan jam kunci berakhir. Atur di Pusat Kendali › Pengaturan ›
Gateway & keamanan (`keamanan.login_maks_gagal`, `keamanan.login_kunci_menit`; 0 = tidak dikunci).

| Cara membuka | Siapa |
|---|---|
| Tunggu sampai waktu kunci habis | pengguna |
| Pusat Kendali › **Riwayat** › *Akun terkunci* › **Buka kunci** | Admin (akun Superadmin hanya oleh Superadmin) |
| `powershell -ExecutionPolicy Bypass -File scripts\buka-kunci.ps1 -Akun <email/NIP>` | admin server (darurat, mis. Superadmin satu-satunya terkunci) |

Semua login (berhasil, gagal, dikunci, dibuka) tercatat di **jejak audit** (Pusat Kendali › Riwayat).

### 4.5b Menguji apa yang dilihat seorang pengguna
Kelola › **Lihat sebagai…**: pilih pengguna & dashboard; setiap chart dijalankan sebagai pengguna itu beserta aturan
hak akses datanya ([26 §4](26-langganan-versi-ponsel-lihat-sebagai.md)). Tidak perlu password pengguna.

### 4.6 Memindahkan ke server lain
Salin folder `D:\superset` **termasuk `.env`** dan cadangan `backup\metadb-*.dump`, jalankan
`PASANG.cmd`, lalu `scripts\cadangkan.ps1 -Pulihkan backup\metadb-....dump`. Ekstrak dibuat ulang
dengan tombol **Segarkan** (isinya disalin lagi dari sumber).

---

## 5. Port yang dipakai

| Port | Komponen | Terbuka untuk | Diatur di |
|---|---|---|---|
| 8088 | gateway (web) | jaringan kantor | `SUPERSET_PORT` |
| 8089 | web langsung | hanya server | `NODE_WEB_PORT` |
| 5433 | metadb | hanya server (multi-node: node tambahan) | `METADB_PORT_HOST`, `CLUSTER_BIND` |
| 8124 | engine HTTP | hanya server (multi-node: node tambahan) | `ENGINE_PORT_HOST`, `CLUSTER_BIND` |
| 6379 | redis | hanya server (multi-node: node tambahan) | `CLUSTER_BIND` |

`CLUSTER_BIND=127.0.0.1` (bawaan) = port 5433/8124/6379 hanya bisa diakses dari server itu sendiri.
Mode multi-node (`0.0.0.0`): buka firewall **hanya untuk IP node tambahan** ([11-pusat-kendali-server.md](11-pusat-kendali-server.md)).
