<#
.SYNOPSIS
    Membersihkan sisa Docker yang tidak terpakai agar storage lega.

.DESCRIPTION
    AMAN: tidak menyentuh data (semua dashboard ada di MySQL sps_superset)
    dan tidak menghapus image yang sedang dipakai.
      1. Container sps_superset diperbarui ke image terbaru (bila ada).
      2. Container yang sudah berhenti dihapus.
      3. Image tanpa nama (<none>) yang tidak dipakai dihapus.
      4. Cache build dihapus.
    Yang DIPERTAHANKAN: sps-superset:6.1.0 (dipakai) dan apache/superset:6.1.0
    (bahan build; bila dihapus, build berikutnya mengunduh ulang ±870 MB).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\cleanup.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "`n==> Sebelum" -ForegroundColor Cyan
docker system df

docker compose up -d                 # pastikan container memakai image terbaru
docker container prune -f            # container berhenti (sisa 'docker compose run')
docker image prune -f                # image <none> yang tidak dipakai
docker builder prune -f              # cache build

Write-Host "`n==> Sesudah" -ForegroundColor Cyan
docker system df
docker image ls
