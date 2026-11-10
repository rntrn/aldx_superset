<#
.SYNOPSIS
    Uji otomatis: semua container sehat + fungsi utama berjalan (config\sps_uji.py).

.DESCRIPTION
    Dipakai setelah instalasi, upgrade, atau perubahan pengaturan.
    Tidak mengubah data pengguna. Butuh data latihan (scripts\data-latihan.ps1).
    Kode keluar 1 bila ada yang GAGAL. Rincian galat: tambahkan -Rinci.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\uji.ps1
#>
param([switch]$Rinci)

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Status container" -ForegroundColor Cyan
docker compose ps --format "table {{.Service}}\t{{.State}}\t{{.Health}}"
$tidakSehat = docker compose ps --format "{{.Service}} {{.Health}}" | Where-Object { $_ -match "unhealthy|starting" }
if ($tidakSehat) { Write-Host "Belum sehat: $tidakSehat (tunggu 1-2 menit lalu ulangi)" -ForegroundColor Yellow }

Write-Host "`n==> Uji fungsi" -ForegroundColor Cyan
$env:SPS_UJI_RINCI = if ($Rinci) { "1" } else { "" }
docker compose exec -T -e SPS_UJI_RINCI superset python /app/pythonpath/sps_uji.py
$kode = $LASTEXITCODE
if ($kode -eq 0) { Write-Host "`nSemua uji LULUS." -ForegroundColor Green }
else { Write-Host "`nAda uji GAGAL. Lihat baris GAGAL di atas; rincian: scripts\uji.ps1 -Rinci" -ForegroundColor Red }
exit $kode
