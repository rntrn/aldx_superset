<#
.SYNOPSIS
    Darurat: buka kunci akun yang terkunci karena salah password berulang.

.DESCRIPTION
    Biasanya cukup lewat Pusat Kendali › Riwayat › Akun terkunci (Admin), atau tunggu kuncinya habis
    (bawaan 15 menit). Skrip ini untuk keadaan darurat, mis. satu-satunya Superadmin terkunci.
    Tanpa -Akun: hanya menampilkan daftar akun yang sedang terkunci.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\buka-kunci.ps1
    powershell -ExecutionPolicy Bypass -File scripts\buka-kunci.ps1 -Akun admin@perusahaan.co.id
#>
param([string]$Akun = "")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($Akun) { docker compose exec -T superset python /app/pythonpath/sps_kunci.py $Akun }
else { docker compose exec -T superset python /app/pythonpath/sps_kunci.py }
exit $LASTEXITCODE
