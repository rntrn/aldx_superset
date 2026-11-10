<#
.SYNOPSIS
    Menyiapkan menu, izin, ALDx Engine, identitas, & dashboard bawaan di Superset.

.DESCRIPTION
    Menjalankan config/sps_build_dashboards.py di dalam container.
    Aman dijalankan berulang: objek yang sama diperbarui, bukan diduplikasi.
    Syarat: Superset menyala (scripts\start.ps1). Dashboard profil DJP hanya dibuat bila
    koneksi sumber DJP ada (scripts\add-connections.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build-dashboards.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

docker compose exec -T superset python /app/pythonpath/sps_build_dashboards.py
if ($LASTEXITCODE -ne 0) { throw "Gagal membangun dashboard. Cek pesan di atas / scripts\logs.ps1" }

Write-Host "`nSelesai. Buka $(Get-AlamatWeb)/app/" -ForegroundColor Green

exit 0
