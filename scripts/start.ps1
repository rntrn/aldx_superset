<#
.SYNOPSIS
    Menyalakan Superset di background, lalu menampilkan alamatnya.

.DESCRIPTION
    Semua komponen (metadb, engine, Redis, Superset, gateway) berjalan di Docker;
    Superset baru dinyalakan setelah metadb & engine sehat.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

. "$PSScriptRoot\_umum.ps1"
Assert-SudahPindah
Initialize-ServerEnv            # versi lama: tambahkan password engine dsb. bila belum ada

docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "Superset gagal dinyalakan. Cek: scripts\logs.ps1" }

Write-Host "`nSuperset berjalan. Buka $(Get-AlamatWeb) (tunggu +/- 1 menit saat pertama start)." -ForegroundColor Green

exit 0
