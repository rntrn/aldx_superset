<#
.SYNOPSIS
    Menampilkan log secara live (Ctrl+C untuk keluar). Pakai ini pertama kali saat ada error.

.PARAMETER Layanan
    superset (web, bawaan) | superset-worker (backgrounder) | superset-beat (penjadwal)
    | redis (cache) | gateway | semua

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\logs.ps1
    powershell -ExecutionPolicy Bypass -File scripts\logs.ps1 -Layanan superset-worker
#>
param([string]$Layanan = "superset")

Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Layanan -eq "semua") {
    docker compose logs -f --tail 100
} else {
    docker compose logs -f --tail 200 $Layanan
}
