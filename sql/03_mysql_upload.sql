-- =============================================================================
--  Database tujuan upload Excel/CSV pengguna: sps_upload
--  Jalankan SEKALI di phpMyAdmin (tab SQL) sebagai root.
--  Terpisah dari sps_superset (metadata) dan dari data sumber (Oracle/ClickHouse).
-- =============================================================================
CREATE DATABASE IF NOT EXISTS sps_upload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- User superset (dibuat di 01/02) boleh membuat & mengisi tabel hasil upload.
GRANT ALL PRIVILEGES ON sps_upload.* TO 'superset'@'localhost';
GRANT ALL PRIVILEGES ON sps_upload.* TO 'superset'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sps_upload.* TO 'superset'@'%';
FLUSH PRIVILEGES;
