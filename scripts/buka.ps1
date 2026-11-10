<#
.SYNOPSIS
    Membuka ALDx di browser (dipakai pintasan "ALDx" di Desktop & menu Start).

.DESCRIPTION
    Alamat dibaca dari .env (port & HTTPS), jadi pintasan tetap benar walau port diganti.
    Bila Docker Desktop belum menyala, dinyalakan dulu lalu ditunggu (maks. 3 menit).
#>

$ErrorActionPreference = "SilentlyContinue"
$AKAR = Split-Path $PSScriptRoot -Parent
Set-Location $AKAR
. "$AKAR\scripts\_umum.ps1"
Add-Type -AssemblyName System.Windows.Forms

if (-not (Test-Path ".env")) {
    [void][System.Windows.Forms.MessageBox]::Show("ALDx belum dipasang. Jalankan 'Pasang / ubah pengaturan ALDx' dulu.", "ALDx", "OK", "Information")
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $exe) { Start-Process $exe }
    $batas = (Get-Date).AddMinutes(3)
    do { Start-Sleep -Seconds 5; docker info *> $null } while ($LASTEXITCODE -ne 0 -and (Get-Date) -lt $batas)
    if ($LASTEXITCODE -ne 0) {
        [void][System.Windows.Forms.MessageBox]::Show("Docker Desktop belum menyala. Buka Docker Desktop, tunggu ikon paus diam, lalu coba lagi.", "ALDx", "OK", "Warning")
        exit 1
    }
    docker compose up -d *> $null       # container ALDx menyala lagi setelah Docker hidup
}

Start-Process (Get-AlamatWeb)
