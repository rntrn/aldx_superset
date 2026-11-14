<#
.SYNOPSIS
    Instalasi pertama Superset (jalankan SEKALI).

.DESCRIPTION
    1. Membuat .env dari .env.example bila belum ada
    2. Membuat SUPERSET_SECRET_KEY acak bila masih placeholder
    3. Membuat password container (Redis, metadb, engine) bila masih placeholder
    4. Membangun image Superset & menyalakan metadb (PostgreSQL), engine (ClickHouse), Redis
    5. Membuat tabel metadata (superset db upgrade)
    6. Membuat akun admin dari nilai di .env
    7. Menyiapkan role & permission default (superset init)
    8. Menghitung jatah CPU/RAM container dari komputer ini (Pusat Kendali Server)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\init.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)   # pindah ke D:\superset
. "$PSScriptRoot\_umum.ps1"

function Invoke-Step([string]$Title, [scriptblock]$Action) {
    Write-Host "`n==> $Title" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gagal pada langkah: $Title" }
}

# --- 1. File .env ------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "File .env dibuat dari .env.example." -ForegroundColor Green
}

# --- 2. Secret key -----------------------------------------------------------
$envText = Get-Content ".env" -Raw
if ($envText -match "SUPERSET_SECRET_KEY=GANTI_DENGAN_SECRET_KEY") {
    $bytes = New-Object byte[] 42
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $key = [Convert]::ToBase64String($bytes)
    $envText = $envText -replace "SUPERSET_SECRET_KEY=GANTI_DENGAN_SECRET_KEY", "SUPERSET_SECRET_KEY=$key"
    Set-Content ".env" $envText -NoNewline
    Write-Host "SUPERSET_SECRET_KEY dibuat otomatis di .env (jangan diubah setelah ini)." -ForegroundColor Green
}
Assert-SudahPindah
Initialize-ServerEnv   # password Redis/metadb/engine, NODE_NAMA

# --- 3-6. Instalasi ----------------------------------------------------------
if (Import-ImageOffline) {
    Write-Host "Paket offline: image Superset tidak dibangun ulang." -ForegroundColor Green
} else {
    Invoke-Step "Membangun image Superset" { docker compose build }   # --pull: lihat docs\16 (upgrade)
}

Invoke-Step "Menyalakan metadb, engine & Redis" { Wait-Container @("metadb", "engine", "redis") }
Sync-MetadbPassword    # volume lama + .env baru: password disamakan (aman bila sudah sama)

Invoke-Step "Membuat tabel metadata" {
    docker compose run --rm superset superset db upgrade
}

Invoke-Step "Membuat akun admin" {
    docker compose run --rm superset sh /app/pythonpath/sps_buat_admin.sh   # nama/password berspasi tetap utuh
}

Invoke-Step "Menyiapkan role & permission" {
    docker compose run --rm superset superset init
}

Invoke-Step "Menghitung jatah CPU/RAM container (auto-tuning)" {
    & "$PSScriptRoot\terapkan-server.ps1" -JanganNyalakan
}

Write-Host "`nSelesai. Jalankan scripts\start.ps1 untuk menyalakan Superset." -ForegroundColor Green

exit 0
