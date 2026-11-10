<#
.SYNOPSIS
    Menerapkan pengaturan Pusat Kendali Server yang bertanda "Perlu diterapkan".

.DESCRIPTION
      1. Pastikan REDIS_PASSWORD & NODE_NAMA ada di .env
      2. Hitung jatah CPU/RAM tiap container dari perangkat komputer ini
         (auto-tuning) + tulis server\gateway.conf (daftar node web)
      3. Tulis hasilnya ke blok "SERVER" di .env
      4. Nyalakan ulang container yang berubah (docker compose up -d)
      5. Muat ulang gateway (node utama)

    Container dinyalakan ulang +/- 1 menit; pengguna yang sedang membuka
    dashboard cukup memuat ulang halaman.

.PARAMETER Tambahan
    Jalankan di node TAMBAHAN (memakai docker-compose.node.yml).

.PARAMETER JanganNyalakan
    Hanya hitung & tulis .env, tanpa menyalakan container (dipakai init.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\terapkan-server.ps1
#>
param([switch]$Tambahan, [switch]$JanganNyalakan)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

$compose = if ($Tambahan) { @("-f", "docker-compose.node.yml") } else { @() }
$peran = if ($Tambahan) { "tambahan" } else { "utama" }

Initialize-ServerEnv

Write-Host "`n==> Menghitung jatah sumber daya node ini ($peran)" -ForegroundColor Cyan
$errFile = New-TemporaryFile
# Windows PowerShell 5.1 menganggap teks stderr program sebagai error bila dialihkan;
# sementara pakai "Continue" agar ringkasan (stderr) tidak menghentikan skrip.
$ErrorActionPreference = "Continue"
$hasil = docker compose @compose run --rm --no-deps -T superset python -m sps_server.terapkan $peran 2> $errFile
$kode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content $errFile | Where-Object { $_ -notmatch "^\s*$|Container .* (Creating|Created|Starting|Started)" } | ForEach-Object { Write-Host "    $_" }
Remove-Item $errFile
if ($kode -ne 0) { throw "Gagal menghitung pengaturan. Cek pesan di atas (MySQL menyala?)." }

$baris = @($hasil | Where-Object { $_ -match "^[A-Z_]+=" })
$blok = "# >>> SERVER (dikelola scripts\terapkan-server.ps1 - jangan diedit manual)`r`n" + ($baris -join "`r`n") + "`r`n# <<< SERVER"
$text = Get-Content ".env" -Raw
$pola = "(?s)# >>> SERVER.*?# <<< SERVER"
if ($text -match $pola) {
    $text = [regex]::Replace($text, $pola, [System.Text.RegularExpressions.MatchEvaluator]{ $blok })
} else {
    $text = $text.TrimEnd() + "`r`n`r`n" + $blok + "`r`n"
}
Set-Content ".env" $text -NoNewline
Write-Host "    Blok SERVER di .env diperbarui ($($baris.Count) nilai)." -ForegroundColor Green

if ($JanganNyalakan) { exit 0 }

Write-Host "`n==> Menyalakan ulang container yang berubah" -ForegroundColor Cyan
docker compose @compose up -d
if ($LASTEXITCODE -ne 0) { throw "Container gagal dinyalakan. Cek: scripts\logs.ps1" }

if (-not $Tambahan) {
    Write-Host "`n==> Memuat ulang gateway" -ForegroundColor Cyan
    docker compose exec -T gateway nginx -t
    if ($LASTEXITCODE -ne 0) { throw "server\gateway.conf tidak valid. Cek pesan di atas." }
    docker compose exec -T gateway nginx -s reload
}

Write-Host "`nSelesai. Pantau di $(Get-AlamatWeb)/pusat-kendali/ (tab Status)." -ForegroundColor Green
