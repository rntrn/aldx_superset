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
# Server AD dari LDAP_SERVERS di .env (ldap://host[:port] / ldaps://host[:port]). Kosong = LDAP tidak dipakai.
$adServer = @()
$barisLdap = Select-String -Path ".env" -Pattern '^LDAP_SERVERS=(.*)$' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($barisLdap) {
    foreach ($u in ($barisLdap.Matches[0].Groups[1].Value -split ",")) {
        if ($u.Trim() -match '^(ldaps?)://([^:/]+)(?::(\d+))?') {
            $port = if ($Matches[3]) { [int]$Matches[3] } elseif ($Matches[1] -eq "ldaps") { 636 } else { 389 }
            $adServer += ,@($Matches[2], $port)
        }
    }
}

function Write-Section([string]$Title) { "`n===== $Title =====" }

& {
    Write-Section "Waktu"
    Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Write-Section "Status container"
    docker compose ps -a

    Write-Section "Daftar user Superset"
    docker compose exec -T superset superset fab list-users

    Write-Section "Koneksi ke Active Directory dari Windows"
    if (-not $adServer) { "LDAP tidak dipakai (LDAP_SERVERS kosong di .env)" }
    foreach ($s in $adServer) {
        $ok = (Test-NetConnection $s[0] -Port $s[1] -WarningAction SilentlyContinue).TcpTestSucceeded
        "$($s[0]):$($s[1]) : $ok"
    }

    Write-Section "Koneksi ke Active Directory dari dalam container"
    if ($adServer) {
        $daftar = ($adServer | ForEach-Object { "('$($_[0])',$($_[1]))" }) -join ","
        docker compose exec -T superset python -c "import socket;[print(h, p, ':', (lambda s: (s.settimeout(5), s.connect_ex((h,p))==0)[1])(socket.socket())) for h,p in [$daftar]]"
    }

    Write-Section "Pemakaian CPU/RAM container"
    docker stats --no-stream

    foreach ($l in @("superset", "superset-worker", "superset-beat", "redis", "gateway")) {
        Write-Section "Log $l (200 baris terakhir)"
        docker compose logs --no-color --tail 200 $l
    }
} *>&1 | Out-File $report -Encoding utf8

Write-Host "Selesai. Laporan tersimpan di $(Join-Path (Get-Location) $report)" -ForegroundColor Green
