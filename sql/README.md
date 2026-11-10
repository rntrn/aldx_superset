# sql/ (khusus instalasi lama)

Berkas di sini hanya untuk instalasi **lama** yang menyimpan metadata di MySQL XAMPP.
Instalasi sekarang memakai container `metadb` (MariaDB) dan tidak membutuhkan berkas ini;
pemindahan dari XAMPP dilakukan otomatis oleh `PASANG.cmd` / `scripts\pindah-dari-xampp.ps1`.

| Berkas | Dulu dipakai untuk |
|---|---|
| `01_mysql_setup.sql` | membuat database `sps_superset` + user `superset` di XAMPP |
| `02_mysql_fix_localhost.sql` | perbaikan "Access denied superset@localhost" |
| `03_mysql_upload.sql` | database `sps_upload` untuk upload (kini upload masuk ke ALDx Engine) |
