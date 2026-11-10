<#
.SYNOPSIS
    Uji beban: N pengguna maya membuka dashboard bersamaan; hasilnya median & p95 waktu muat chart.

.DESCRIPTION
    Membuktikan angka sizing (docs\15-sizing.md) di server Anda sendiri. Jalankan DI LUAR JAM KERJA:
    uji ini sengaja membebani server. Password akun diketik (tidak tampil, tidak disimpan).
    Kesimpulan CUKUP bila p95 < 5 detik dan gagal < 1%. Kode keluar 2 = KURANG.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\uji-beban.ps1 -Akun admin@perusahaan.co.id
    powershell -ExecutionPolicy Bypass -File scripts\uji-beban.ps1 -Akun admin@perusahaan.co.id -Pengguna 100 -Detik 300 -Dashboard penjualan
    powershell -ExecutionPolicy Bypass -File scripts\uji-beban.ps1 -Akun admin@perusahaan.co.id -TanpaCache
#>
param([Parameter(Mandatory)][string]$Akun, [int]$Pengguna = 50, [int]$Detik = 120,
      [string]$Dashboard = "latihan", [switch]$TanpaCache)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$aman = Read-Host "Password $Akun" -AsSecureString
$env:SPS_BEBAN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($aman))
# Langsung ke proses web (bukan lewat gateway): semua pengguna maya berasal dari satu alamat IP, dan batas
# permintaan per IP di gateway akan memotongnya. Yang diukur = kapasitas web, database, cache & engine.
$env:SPS_BEBAN_ALAMAT = "http://superset:8088"
$argumen = @("--akun", $Akun, "--pengguna", $Pengguna, "--detik", $Detik, "--dashboard", $Dashboard)
if ($TanpaCache) { $argumen += "--tanpa-cache" }
try {
    docker compose exec -T -e SPS_BEBAN_PASSWORD -e SPS_BEBAN_ALAMAT superset python /app/pythonpath/sps_beban.py @argumen
    $kode = $LASTEXITCODE
} finally {
    Remove-Item Env:SPS_BEBAN_PASSWORD -ErrorAction SilentlyContinue
}
exit $kode
