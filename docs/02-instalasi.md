# 02 · Instalasi

## Cara termudah: `PASANG.cmd`

Jalankan **`ALDx-Setup.exe`** (Releases › ALDx terbaru), atau klik dua kali **`PASANG.cmd`** di folder proyek (mis. `D:\superset`), lalu ikuti wizard (Next-Next).
Yang wajib hanya **email & password Superadmin**. Panduan untuk pengguna awam: [CARA-PASANG.md](../CARA-PASANG.md);
rinci & gambar: [18-installer.md](18-installer.md).

## Prasyarat

| Kebutuhan | Cara cek |
|---|---|
| Docker Desktop (WSL2 backend) menyala | `docker --version` dan `docker compose version` di PowerShell |
| Resources Docker ≥ 4 CPU / 8 GB (uji coba: 2 / 4 GB) | Docker Desktop → Settings → Resources ([15-sizing.md](15-sizing.md)) |
| Disk bebas ≥ 40 GB | File Explorer |
| Port 8088, 5433, 8124, 6379 bebas | installer memeriksa otomatis |

**Tidak perlu XAMPP atau database lain.** Metadata (PostgreSQL) dan ALDx Engine (ClickHouse) ikut terpasang
di Docker. Instalasi lama (metadata di MySQL XAMPP atau MariaDB) dipindah otomatis oleh installer
(atau `scripts\pindah-metadata.ps1`); XAMPP harus menyala selama pemindahan.

## Cara manual (tanpa wizard)

```powershell
cd D:\superset
Copy-Item .env.example .env       # buka .env: isi ADMIN_PASSWORD (LDAP opsional)
powershell -ExecutionPolicy Bypass -File scripts\init.ps1             # password container, image, database, admin
powershell -ExecutionPolicy Bypass -File scripts\start.ps1            # nyalakan semua
powershell -ExecutionPolicy Bypass -File scripts\build-dashboards.ps1 # menu, izin, dashboard, ALDx Engine
powershell -ExecutionPolicy Bypass -File scripts\data-latihan.ps1     # data latihan (pelatihan & uji)
powershell -ExecutionPolicy Bypass -File scripts\uji.ps1              # uji otomatis
```

Yang dilakukan `init.ps1` (± 10–30 menit pertama kali):

1. Membuat `SUPERSET_SECRET_KEY` dan password acak untuk Redis, metadb, engine (bila masih placeholder)
2. Membangun image Superset (image resmi + driver)
3. Menyalakan `metadb`, `engine`, `redis` dan menunggu sehat
4. Membuat tabel metadata, akun admin, role & permission
5. Menghitung jatah CPU/RAM container (auto-tuning)

Setelah selesai, hapus `ADMIN_PASSWORD` dari `.env` (installer melakukannya otomatis).

## Cek berhasil

- [ ] `scripts\uji.ps1` → semua **LULUS**
- [ ] Halaman login tampil di `http://localhost:8088`
- [ ] `scripts\test-ldap.ps1` menampilkan BERHASIL (bila LDAP dipakai)
- [ ] Bisa login dengan akun admin (dan akun LDAP bila dipakai)
- [ ] Dashboard **Latihan: Dashboard Penjualan (fiktif)** tampil

Langkah berikutnya: atur nama & logo di **Pusat Kendali → Identitas & Tema** ([09](09-identitas-tema.md)),
lalu hubungkan sumber data di **Data → Hubungkan data** ([06](06-sumber-data.md)).

Jika gagal → [04-troubleshooting.md](04-troubleshooting.md).
