<#
.SYNOPSIS
    Menampilkan versi setiap komponen yang terpasang & yang diminta .env.

.DESCRIPTION
    Dipakai sebelum/sesudah upgrade (docs\16-upgrade-downgrade.md).
    Kolom "Diminta" dari .env, kolom "Berjalan" dari container yang menyala.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\versi.ps1
#>

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

function Jalan([string]$layanan, [string]$perintah) {
    $hasil = docker compose exec -T $layanan sh -c $perintah 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $hasil) { return "(mati)" }
    return ($hasil | Select-Object -First 1).Trim()
}

$baris = @(
    [pscustomobject]@{ Komponen = "Superset (web)"; Diminta = Get-EnvValue "SUPERSET_VERSION";
        Berjalan = Jalan "superset" "superset version 2>/dev/null | grep -o '[0-9][0-9.]*' | head -1" }
    [pscustomobject]@{ Komponen = "PostgreSQL (metadb)"; Diminta = Get-EnvValue "METADB_VERSI";
        Berjalan = Jalan "metadb" "postgres --version | grep -o '[0-9][0-9.]*' | head -1" }
    [pscustomobject]@{ Komponen = "ClickHouse (engine)"; Diminta = Get-EnvValue "ENGINE_VERSI";
        Berjalan = Jalan "engine" "clickhouse-server --version | grep -o '[0-9][0-9.]*' | head -1" }
    [pscustomobject]@{ Komponen = "Redis"; Diminta = Get-EnvValue "REDIS_VERSI";
        Berjalan = Jalan "redis" "redis-server --version | grep -o 'v=[0-9.]*' | cut -c3-" }
    [pscustomobject]@{ Komponen = "nginx (gateway)"; Diminta = Get-EnvValue "GATEWAY_VERSI";
        Berjalan = Jalan "gateway" "nginx -v 2>&1 | grep -o '[0-9][0-9.]*'" }
)
$baris | Format-Table -AutoSize
Write-Host "Docker: $(docker version --format '{{.Server.Version}}' 2>$null)"
