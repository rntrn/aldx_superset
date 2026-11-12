<#
.SYNOPSIS
    Memuat data latihan FIKTIF ke ALDx Engine (untuk pelatihan, bahan ajar & pengujian).

.DESCRIPTION
    Membuat (config\sps_latihan.py & config\sps_latihan_wilayah.py):
      latihan_penjualan, latihan_lokasi_pelanggan, latihan_cabang   data bulanan kecil (dashboard "latihan")
      latihan_outlet, latihan_penjualan_harian                      +-2,3 juta baris harian 2021-2025 dengan
                                                                     hierarki Wilayah/Kalender/Produk
                                                                     (dashboard "latihan-wilayah")
    Dijalankan otomatis oleh installer. Aman diulang: isi tabel diganti dengan data yang sama persis.
    Syarat: Superset menyala (scripts\start.ps1).

.PARAMETER Skala
    1-10: jumlah outlet per kelurahan untuk data harian. 1 = +-2,3 juta baris (bawaan), 4 = +-9,3 juta,
    10 = +-23 juta baris (butuh RAM & disk engine lebih besar; untuk demo kecepatan).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\data-latihan.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\data-latihan.ps1 -Skala 4
#>
param([ValidateRange(1, 10)][int]$Skala = 1)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose exec -T -e "SPS_LATIHAN_SKALA=$Skala" superset python /app/pythonpath/sps_latihan.py
if ($LASTEXITCODE -ne 0) { throw "Gagal memuat data latihan. Cek: scripts\logs.ps1" }
Write-Host "`nSelesai. Dataset latihan siap di Studio Visual, termasuk latihan_penjualan_harian (skala $Skala)." -ForegroundColor Green

exit 0
