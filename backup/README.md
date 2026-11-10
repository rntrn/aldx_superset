# backup/

Berkas cadangan. Folder ini terpasang di container `metadb` sebagai `/backup`, dan
subfolder `engine\` di container `engine` sebagai `/backups`.

| Berkas | Dibuat oleh |
|---|---|
| `metadb-YYYYMMDD-HHMM.dump` | `scripts\cadangkan.ps1`: metadata PostgreSQL (14 terakhir disimpan) |
| `xampp-*.sql`, `metadb-*.sql` | versi lama (MySQL/MariaDB); hanya untuk `scripts\pindah-metadata.ps1 -DariBerkas` |
| `engine\engine-YYYYMMDD-HHMM.zip` | `scripts\cadangkan.ps1 -Engine`: isi ALDx Engine (5 terakhir) |

Pemulihan: `scripts\cadangkan.ps1 -Pulihkan backup\metadb-....dump` atau `-PulihkanEngine backup\engine\engine-....zip`.

Berisi data rahasia (user, koneksi, dashboard, data). Jangan dibagikan; isinya tidak ikut git.
Salin berkala ke penyimpanan lain (disk/NAS kantor) agar aman bila server rusak.
