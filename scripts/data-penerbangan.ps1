<#
.SYNOPSIS
    Membuat data latihan FIKTIF "Penerbangan" (Excel/CSV) berukuran besar untuk mencoba & memamerkan ALDx.

.DESCRIPTION
    Enam tabel saling terhubung: maskapai, bandara, penerbangan, jadwal, penumpang, tiket
    (generator: config\sps_latihan_penerbangan.py). Dijalankan DI DALAM container superset,
    jadi tidak perlu Python di Windows. Hasil disalin ke docs\bahan-ajar\berkas\.

    Ukuran kecil & sedang sudah tersedia di folder itu. Skrip ini terutama untuk ukuran besar
    (1 juta tiket, sekitar 3 menit) atau jumlah tiket sendiri (-Tiket). Lebih dari 1 juta tiket:
    Excel dipecah menjadi lembar tiket_1, tiket_2, ...; -Format csv tidak punya batas baris.
    Rincian & kamus data: docs\bahan-ajar\berkas\README.md
    Syarat: Superset menyala (scripts\start.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\data-penerbangan.ps1                          # besar (1 juta tiket)
    powershell -ExecutionPolicy Bypass -File scripts\data-penerbangan.ps1 -Ukuran sedang
    powershell -ExecutionPolicy Bypass -File scripts\data-penerbangan.ps1 -Tiket 3000000 -Format csv
#>
param([ValidateSet("kecil", "sedang", "besar")][string]$Ukuran = "besar",
      [int]$Tiket = 0,
      [ValidateSet("xlsx", "csv")][string]$Format = "xlsx")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$nama = if ($Tiket -gt 0) { "contoh-penerbangan-$Tiket" } else { "contoh-penerbangan-$Ukuran" }
if ($Format -eq "xlsx") { $nama += ".xlsx" }
$sementara = "/tmp/$nama"
$tujuan = "docs\bahan-ajar\berkas\$nama"

$argumen = @("python", "/app/pythonpath/sps_latihan_penerbangan.py", "--format", $Format, "--keluar", $sementara)
$argumen += if ($Tiket -gt 0) { @("--tiket", $Tiket) } else { @("--ukuran", $Ukuran) }

Write-Host "Membuat $nama (bisa beberapa menit untuk jutaan baris) ..." -ForegroundColor Cyan
docker compose exec -T superset @argumen
if ($LASTEXITCODE -ne 0) { throw "Gagal membuat data. Cek: scripts\logs.ps1" }

if (Test-Path $tujuan) { Remove-Item -Recurse -Force $tujuan }
docker compose cp "superset:$sementara" $tujuan
if ($LASTEXITCODE -ne 0) { throw "Gagal menyalin hasil dari container." }
docker compose exec -T superset rm -rf $sementara | Out-Null

Write-Host "`nSelesai: $tujuan" -ForegroundColor Green
Write-Host "Impor lewat Pusat Kendali > Hubungkan data > Berkas (bukan Upload bawaan: batasnya 200.000 baris)."

exit 0
