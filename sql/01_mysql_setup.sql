-- =============================================================================
--  Persiapan MySQL/MariaDB XAMPP untuk metadata Superset.
--  Jalankan SEKALI di phpMyAdmin (tab SQL) sebagai root.
--
--  1. Database sps_superset (prefix "sps_" ada di nama database), utf8mb4
--  2. User superset boleh login dari container Docker ('%' = host mana pun)
--  3. Hak akses user HANYA ke database sps_superset
--  4. Cek hasil: harus tampil 1 database dan baris GRANT untuk sps_superset
--
--  Catatan: komentar sengaja hanya di bagian atas. Komentar di antara perintah
--  membuat phpMyAdmin menampilkan "#1046 No database selected" (tidak berbahaya).
-- =============================================================================
CREATE DATABASE IF NOT EXISTS sps_superset CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'superset'@'%' IDENTIFIED BY 'superset';
GRANT ALL PRIVILEGES ON sps_superset.* TO 'superset'@'%';
FLUSH PRIVILEGES;
SHOW DATABASES LIKE 'sps_superset';
SHOW GRANTS FOR 'superset'@'%';
