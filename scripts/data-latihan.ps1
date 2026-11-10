<#
.SYNOPSIS
    Memuat data latihan FIKTIF ke ALDx Engine (untuk pelatihan, bahan ajar & pengujian).

.DESCRIPTION
    Membuat dataset latihan_penjualan & latihan_lokasi_pelanggan (config\sps_latihan.py).
    Aman diulang: isi tabel diganti dengan data yang sama persis.
    Syarat: Superset menyala (scripts\start.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\data-latihan.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose exec -T superset python /app/pythonpath/sps_latihan.py
if ($LASTEXITCODE -ne 0) { throw "Gagal memuat data latihan. Cek: scripts\logs.ps1" }
Write-Host "`nSelesai. Dataset latihan_penjualan & latihan_lokasi_pelanggan siap di Studio Visual." -ForegroundColor Green

exit 0
