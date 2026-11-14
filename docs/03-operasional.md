# 03 · Operasional

Urutan menyala, SOP, dan FAQ gangguan ada di [19-runbook-faq-admin.md](19-runbook-faq-admin.md).

## Perintah harian

| Tujuan | Perintah (dari `D:\superset`) |
|---|---|
| Nyalakan | `powershell -ExecutionPolicy Bypass -File scripts\start.ps1` |
| Matikan | `powershell -ExecutionPolicy Bypass -File scripts\stop.ps1` |
| Lihat log | `powershell -ExecutionPolicy Bypass -File scripts\logs.ps1` |
| Status | `docker compose ps` |
| Uji otomatis | `powershell -ExecutionPolicy Bypass -File scripts\uji.ps1` |
| Cadangkan | `powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 [-Engine]` |
| Versi komponen | `powershell -ExecutionPolicy Bypass -File scripts\versi.ps1` |
| Uji lengkap dari nol di Linux/WSL kosong (sama dengan CI) | `bash scripts/uji-ci.sh` |
| Uji tampilan terhadap ALDx yang jalan | `ALDX_PASSWORD=... python tests/e2e/uji_tampilan.py` ([pengujian §1b](pengujian/README.md#1b-uji-tampilan-otomatis-ci)) |
| Pratinjau catatan rilis satu versi (dipakai GitHub Actions untuk rilis `v<VERSI>`) | `pwsh -File scripts\catatan-rilis.ps1 -Versi 2026.11.14` |
| Bersihkan storage Docker | `powershell -ExecutionPolicy Bypass -File scripts\cleanup.ps1` |

Container memakai `restart: unless-stopped`: ikut menyala otomatis saat Docker Desktop menyala, kecuali Anda mematikannya dengan `stop.ps1`.

## Log ada di mana?

| Log | Isi | Cara melihat |
|---|---|---|
| Log Superset (server) | Error, login (`ALDx login ... BERHASIL/GAGAL`), hak akses (`ALDx akses ...`) | `scripts\logs.ps1`, atau Docker Desktop → Containers → `sps_superset` → Logs |
| Laporan diagnosa | Status, user, jaringan AD, 400 baris log | `scripts\diagnose.ps1` → `D:\superset\diagnosa.txt` |
| Action Log (aktivitas user) | Siapa membuka dashboard/chart apa, kapan | Superset → **Settings → Action Log** (khusus Admin) |
| Profil hak akses (opsional) | Profil pengguna terakhir saat login | tabel `sps_profil_pengguna` di metadb ([14](14-akun-dan-akses.md)) |
| Log komponen lain | metadb, engine, redis, gateway | `docker compose logs --tail 100 <nama>` |

Log server ikut terhapus bila container dibuat ulang. Untuk jejak jangka panjang
pakai **Action Log** (tersimpan di database).

## Membersihkan storage Docker

Lihat ukuran di Docker Desktop → **Images**. Yang perlu ada hanya:

| Image | Kegunaan |
|---|---|
| `sps-superset:6.1.0` | Dipakai container (wajib) |
| `apache/superset:6.1.0` | Bahan build (simpan, agar build tidak mengunduh ulang ±870 MB) |
| `postgres`, `clickhouse/clickhouse-server`, `redis`, `nginx` | metadb, engine, cache, gateway (wajib) |
| `mariadb` | hanya dipakai sekali saat memindah metadata versi lama; boleh dihapus setelahnya |

Image `<none>` adalah sisa build lama. Hapus otomatis dengan `scripts\cleanup.ps1`
(tidak menyentuh dashboard/data). Ukuran di Docker Desktop terlihat besar karena
lapisan dihitung per image, padahal sebagian besar dipakai bersama.

## Mengelola pengguna

Tanpa LDAP: Admin membuat akun di **Settings → List Users → +**. Dengan LDAP: pengguna cukup login
dengan akun jaringan kantor; user Superset dibuat otomatis. Ubah role seseorang di **Settings → List Users**.
Rincian: [`05-login-ldap.md`](05-login-ldap.md).

## Menambah sumber data

1. **Data → Hubungkan data**: pilih jenis database/data warehouse atau unggah berkas
   Access/Excel/CSV, uji, simpan ([06](06-sumber-data.md)).
2. Database di komputer Windows yang sama (bukan container) dijangkau dengan alamat `host.docker.internal`.

## Menambah driver database

Image resmi Superset tidak membawa driver database. Proyek ini membangun image sendiri lewat
`docker\Dockerfile` dengan driver 16 jenis database + impor Access/Excel. Jaringan kantor memblokir pypi.org
dari Docker, jadi driver dipasang **offline**: unduh `.whl` via browser ke `docker\wheels\`, tambahkan nama
paketnya di `docker\wheels\paket.txt` (panduan: `docker\wheels\README.md`), lalu `docker compose build` dan `scripts\start.ps1`.

## Upgrade versi

Lihat [16-upgrade-downgrade.md](16-upgrade-downgrade.md) (Superset, PostgreSQL, ClickHouse, Redis, nginx).

## Cadangan

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1           # metadata
powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Engine   # + ALDx Engine
```
Berkas di `backup\` (lihat `backup\README.md`). Simpan juga **`.env`**: tanpa `SUPERSET_SECRET_KEY`
yang sama, password koneksi yang tersimpan tidak bisa dibuka. Jadwal otomatis: [tutorial Level 4 §8](tutorial/level-4-admin-server.md#8-cadangan--pemulihan).
