<#
.SYNOPSIS
    Mendaftarkan koneksi Oracle & ClickHouse ke Superset dari isi .env.

.DESCRIPTION
    Membaca variabel ORACLE_DMP_*, ORACLE_IKU_*, ORACLE_DASHBD_*, CLICKHOUSE_*
    di .env (lihat config/sps_connections.py). Koneksi berpassword kosong dilewati.
    Aman dijalankan berulang; jalankan lagi setiap kali .env diubah.
    Superset harus sedang menyala (scripts\start.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\add-connections.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose up -d --force-recreate   # muat ulang .env ke container
docker compose exec -T superset python /app/pythonpath/sps_connections.py
if ($LASTEXITCODE -ne 0) { throw "Gagal mendaftarkan koneksi. Cek: scripts\logs.ps1" }

Write-Host "`nSelesai. Cek di Superset: Settings -> Database Connections." -ForegroundColor Green

exit 0
