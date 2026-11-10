<#
.SYNOPSIS
    Menghapus container (dan bila diminta, SEMUA data) ALDx. Dipanggil otomatis oleh Uninstall ALDx-Setup.

.DESCRIPTION
    Tanpa -Data : container & image ALDx dihapus. DATA TETAP (volume Docker + .env), jadi bila ALDx dipasang
                  ulang di folder yang sama, semua dashboard & pengguna kembali.
    Dengan -Data: cadangan lengkap dibuat dulu (backup\metadb-*.dump, backup\engine\*.zip, salinan .env),
                  lalu container, image, volume data, .env, sertifikat & log dihapus. Folder backup\ DISIMPAN.
                  Bila cadangan gagal, data TIDAK dihapus (hanya container) - aman.
    -MulaiBaru  : (dipakai installer saat data lama tanpa .env) cadangkan lalu hapus HANYA volume data
                  sps_metadb_pg & sps_engine. .env baru, image & berkas lain tetap.
    Kode keluar : 0 berhasil · 2 Docker Desktop tidak menyala (tidak ada yang dihapus) · 3 cadangan gagal (data disimpan)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\hapus-aldx.ps1          # container saja, data tetap
    powershell -ExecutionPolicy Bypass -File scripts\hapus-aldx.ps1 -Data    # cadangkan lalu hapus semua
#>
param([switch]$Data, [switch]$MulaiBaru, [switch]$TanpaJeda)

$ErrorActionPreference = "Continue"
$AKAR = Split-Path $PSScriptRoot -Parent
Set-Location $AKAR
. "$PSScriptRoot\_umum.ps1"
$Host.UI.RawUI.WindowTitle = "Menghapus ALDx"

function Selesai([int]$kode, [string]$pesan, [string]$warna = "Green") {
    Write-Host "`n$pesan" -ForegroundColor $warna
    if (-not $TanpaJeda) { Write-Host "Jendela ini tertutup sendiri dalam 15 detik."; Start-Sleep -Seconds 15 }
    exit $kode
}

docker info *> $null
if ($LASTEXITCODE -ne 0) { Selesai 2 "Docker Desktop tidak menyala: container & data ALDx TIDAK dihapus." "Yellow" }

$kode = 0
if ($MulaiBaru) {
    Write-Host "==> Mencadangkan data pemasangan sebelumnya" -ForegroundColor Cyan
    Wait-Container @("metadb", "engine") 120
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\cadangkan.ps1" -Engine
    if ($LASTEXITCODE -ne 0) { Write-Host "Cadangan GAGAL: data lama TIDAK dihapus." -ForegroundColor Red; exit 3 }
    docker compose down --remove-orphans
    docker volume rm sps_metadb_pg sps_engine
    if ($LASTEXITCODE -ne 0) { Write-Host "Volume data lama tidak bisa dihapus." -ForegroundColor Red; exit 1 }
    Write-Host "Data lama dicadangkan di $AKAR\backup lalu dihapus. Pemasangan dilanjutkan dari awal." -ForegroundColor Green
    exit 0
}
if ($Data) {
    Write-Host "==> Membuat cadangan sebelum menghapus data" -ForegroundColor Cyan
    Wait-Container @("metadb", "engine") 120
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\cadangkan.ps1" -Engine
    if ($LASTEXITCODE -eq 0) {
        if (Test-Path ".env") { Copy-Item ".env" "backup\env-$(Get-Date -Format 'yyyyMMdd-HHmm').txt" }   # SECRET_KEY untuk pemulihan
    } else {
        Write-Host "Cadangan GAGAL: demi keamanan data TIDAK dihapus, hanya container." -ForegroundColor Red
        $Data = $false; $kode = 3
    }
}

Write-Host "`n==> Menghapus container & image ALDx" -ForegroundColor Cyan
$argumen = @("compose", "--profile", "pindah", "down", "--remove-orphans", "--rmi", "all")
if ($Data) { $argumen += "--volumes" }
& docker @argumen

foreach ($tugas in @("ALDx Cadangan Harian", "ALDx Uji Pulih Mingguan")) {
    Unregister-ScheduledTask -TaskName $tugas -Confirm:$false -ErrorAction SilentlyContinue
}

if ($Data) {
    Write-Host "`n==> Menghapus pengaturan & rahasia" -ForegroundColor Cyan
    Remove-Item ".env", "server\tls\*.key", "server\tls\*.crt", "server\status", "installer\log" `
        -Recurse -Force -ErrorAction SilentlyContinue
    Selesai 0 "ALDx & datanya sudah dihapus. Cadangan tersimpan di: $AKAR\backup"
}
if ($kode -eq 3) { Selesai 3 "Container dihapus. Data tetap tersimpan di Docker (cadangan gagal)." "Yellow" }
Selesai 0 "Container ALDx sudah dihapus. Data tetap tersimpan; pasang ulang ke folder yang sama untuk memakainya lagi."
