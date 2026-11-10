<#
.SYNOPSIS
    Menghapus dashboard profil DJP (Beranda & Home Nasional) beserta chart & dataset-nya.

.DESCRIPTION
    Untuk instalasi yang tidak memakai profil DJP: daftar dataset jadi bersih (tinggal data latihan
    dan dataset buatan Anda sendiri). Menjalankan config\sps_bersihkan.py di dalam container.
    Dataset latihan, dataset buatan pengguna, dan ALDx Engine tidak disentuh.

    -Koneksi  juga menghapus koneksi sumber DJP (Oracle DMP/IKU/Dashboard, ClickHouse DMP_OLAP) yang
              tidak dipakai dataset lain, dan mengosongkan isian DJP di .env agar tidak dibuat lagi.

    Setelah ini build-dashboards / PASANG.cmd tidak membangun dashboard DJP lagi
    (kecuali SPS_PROFIL_DJP=1 di .env). Sebaiknya cadangkan dulu: scripts\cadangkan.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\bersihkan-profil-djp.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\bersihkan-profil-djp.ps1 -Koneksi
#>
param([switch]$Koneksi)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

$argumen = @("/app/pythonpath/sps_bersihkan.py")
if ($Koneksi) { $argumen += "--koneksi" }

# Log INFO Superset ditulis ke stderr; di PowerShell 5.1 + "Stop" itu dianggap galat.
$ErrorActionPreference = "Continue"
docker compose exec -T superset python @argumen 2>&1 | Where-Object { "$_" -match "^(OK|--)" } | ForEach-Object { Write-Host "$_" }
$kode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($kode -ne 0) { throw "Gagal membersihkan (kode $kode). Cek: scripts\logs.ps1" }

if ($Koneksi) {
    foreach ($k in @("ORACLE_DMP_HOST", "ORACLE_DMP_PASSWORD", "ORACLE_IKU_HOST", "ORACLE_IKU_PASSWORD",
                     "ORACLE_DASHBD_HOST", "ORACLE_DASHBD_PASSWORD", "ORACLE_TABLEAU_HOST", "ORACLE_TABLEAU_PASSWORD", "CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD", "AKSES_DATABASE")) {
        if (Get-EnvValue $k) { Set-EnvValue $k "" }
    }
    Write-Host "OK  isian sumber DJP di .env dikosongkan"
}
Set-EnvValue "SPS_PROFIL_DJP" ""
Write-Host "`nSelesai. Muat ulang browser (Ctrl+F5)." -ForegroundColor Green
if ($Koneksi) { Write-Host "Isian .env berubah: jalankan  docker compose up -d  agar berlaku." -ForegroundColor Yellow }

exit 0
