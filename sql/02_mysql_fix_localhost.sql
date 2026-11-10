-- =============================================================================
--  Perbaikan: "Access denied for user 'superset'@'localhost'"
--  Jalankan di phpMyAdmin (tab SQL) sebagai root.
--
--  Koneksi dari Docker kadang tercatat MySQL sebagai 'localhost' / '127.0.0.1',
--  bukan '%'. Skrip ini menyamakan user superset di ketiga host itu
--  (password 'superset', hak akses HANYA ke database sps_superset).
--
--  Hasil terakhir menampilkan daftar user. Bila ada baris dengan User KOSONG
--  (user anonim) di host localhost, itu juga bisa menyebabkan "Access denied";
--  lihat docs/04-troubleshooting.md sebelum menghapusnya.
-- =============================================================================
CREATE USER IF NOT EXISTS 'superset'@'localhost' IDENTIFIED BY 'superset';
CREATE USER IF NOT EXISTS 'superset'@'127.0.0.1' IDENTIFIED BY 'superset';
ALTER USER 'superset'@'localhost' IDENTIFIED BY 'superset';
ALTER USER 'superset'@'127.0.0.1' IDENTIFIED BY 'superset';
ALTER USER 'superset'@'%' IDENTIFIED BY 'superset';
GRANT ALL PRIVILEGES ON sps_superset.* TO 'superset'@'localhost';
GRANT ALL PRIVILEGES ON sps_superset.* TO 'superset'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sps_superset.* TO 'superset'@'%';
FLUSH PRIVILEGES;
SELECT User, Host FROM mysql.user WHERE User IN ('', 'superset') ORDER BY User, Host;
