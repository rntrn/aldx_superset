<#
.SYNOPSIS
    Mengumpulkan informasi untuk mencari penyebab masalah, lalu menyimpannya
    ke D:\superset\diagnosa.txt (tanpa password).

.DESCRIPTION
    Isi laporan:
      1. Status container
      2. Daftar user di database Superset
      3. Koneksi ke Active Directory dari Windows dan dari dalam container
      4. Pemakaian CPU/RAM tiap container
      5. Log terakhir semua layanan (web, backgrounder, penjadwal, cache, gateway)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\diagnose.ps1
#>

Set-Location (Split-Path $PSScriptRoot -Parent)
$report = "diagnosa.txt"
$adHosts = @("10.254.28.50", "10.254.28.142")

function Write-Section([string]$Title) { "`n===== $Title =====" }

& {
    Write-Section "Waktu"
    Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Write-Section "Status container"
    docker compose ps -a

    Write-Section "Daftar user Superset"
    docker compose exec -T superset superset fab list-users

    Write-Section "Koneksi ke AD dari Windows (port 389)"
    foreach ($h in $adHosts) {
        $ok = (Test-NetConnection $h -Port 389 -WarningAction SilentlyContinue).TcpTestSucceeded
        "$h : $ok"
    }

    Write-Section "Koneksi ke AD dari dalam container (port 389)"
    docker compose exec -T superset python -c "import socket;[print(h, ':', (lambda s: (s.settimeout(5), s.connect_ex((h,389))==0)[1])(socket.socket())) for h in ['10.254.28.50','10.254.28.142']]"

    Write-Section "Pemakaian CPU/RAM container"
    docker stats --no-stream

    foreach ($l in @("superset", "superset-worker", "superset-beat", "redis", "gateway")) {
        Write-Section "Log $l (200 baris terakhir)"
        docker compose logs --no-color --tail 200 $l
    }
} *>&1 | Out-File $report -Encoding utf8

Write-Host "Selesai. Laporan tersimpan di $(Join-Path (Get-Location) $report)" -ForegroundColor Green
