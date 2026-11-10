<#
.SYNOPSIS
    Memindahkan metadata versi lama (MySQL XAMPP atau MariaDB) ke PostgreSQL (container metadb).

.DESCRIPTION
    Dijalankan otomatis oleh PASANG.cmd bila terdeteksi data lama. Sumber hanya DIBACA,
    jadi aman diulang bila gagal di tengah jalan.

    Sumber yang dikenali (lihat Get-SumberMetaLama di _umum.ps1):
      xampp   : versi pertama, metadata di MySQL XAMPP Windows (MYSQL_HOST=host.docker.internal)
      mariadb : versi sebelumnya, metadata di container MariaDB (volume Docker "sps_metadb")
      berkas  : cadangan MariaDB lama (backup\*.sql), lewat parameter -DariBerkas

    Langkah:
      1. Siapkan .env (password PostgreSQL), matikan Superset
      2. Bangun image, nyalakan sumber lama (XAMPP dicek / container metadb-lama)
      3. Kosongkan PostgreSQL, salin seluruh metadata (config/sps_pindah_meta.py)
      4. superset db upgrade & init
      5. Pindahkan tabel upload lama (database sps_upload) ke ALDx Engine
      6. Tandai METADB_JENIS=postgres, matikan container lama

    Volume lama "sps_metadb" TIDAK dihapus (cadangan). Hapus manual setelah yakin:
      docker volume rm sps_metadb

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\pindah-metadata.ps1
    powershell -ExecutionPolicy Bypass -File scripts\pindah-metadata.ps1 -DariBerkas backup\metadb-20260101-0200.sql
#>
param([string]$DariBerkas)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

function Invoke-Step([string]$Title, [scriptblock]$Action) {
    Write-Host "`n==> $Title" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gagal pada langkah: $Title" }
}

# --- 0. Apa yang dipindah? -------------------------------------------------------------------
$sumber = if ($DariBerkas) { "berkas" } else { Get-SumberMetaLama }
if (-not $sumber) {
    Write-Host "Metadata sudah di PostgreSQL. Tidak ada yang dipindah." -ForegroundColor Green
    exit 0
}
if ($sumber -eq "mariadb") {
    docker volume inspect sps_metadb *> $null
    if ($LASTEXITCODE -ne 0) {
        Set-EnvValue "METADB_JENIS" "postgres"
        Write-Host "Volume MariaDB lama (sps_metadb) tidak ada. Tidak ada yang dipindah." -ForegroundColor Green
        exit 0
    }
}
Write-Host "Sumber metadata lama: $sumber" -ForegroundColor Yellow

# --- 1. .env & matikan Superset ----------------------------------------------------------------
Initialize-ServerEnv
Set-EnvValue "METADB_HOST" "metadb"     # versi lama: METADB_PORT berarti port host (3307)
Set-EnvValue "METADB_PORT" "5432"
New-Item -ItemType Directory -Force "backup" | Out-Null
docker compose stop superset superset-worker superset-beat gateway

# --- 2. Image & sumber lama --------------------------------------------------------------------
Invoke-Step "Membangun image Superset (driver PostgreSQL)" { docker compose build }

switch ($sumber) {
    "xampp" {
        $hostLama = "host.docker.internal"
        $portLama = Get-EnvValue "MYSQL_PORT"; if (-not $portLama) { $portLama = "3306" }
        if (-not (Test-NetConnection localhost -Port $portLama -WarningAction SilentlyContinue).TcpTestSucceeded) {
            throw "MySQL XAMPP (port $portLama) belum menyala. Buka XAMPP Control Panel -> MySQL -> Start, lalu ulangi."
        }
    }
    default {
        $hostLama = "metadb-lama"; $portLama = "3306"
        Invoke-Step "Menyalakan MariaDB lama (hanya dibaca)" {
            docker compose --profile pindah up -d --wait --wait-timeout 180 metadb-lama
        }
        if ($sumber -eq "berkas") {
            $env:BERKAS = Split-Path $DariBerkas -Leaf
            if (-not (Test-Path "backup\$env:BERKAS")) { throw "Berkas backup\$env:BERKAS tidak ada (taruh di folder backup)." }
            Invoke-Step "Memuat cadangan $env:BERKAS ke MariaDB lama" {
                docker compose --profile pindah exec -T -e BERKAS metadb-lama sh /sps/lama.sh impor
            }
        }
    }
}

# --- 3. Salin ke PostgreSQL ----------------------------------------------------------------------
Invoke-Step "Menyalakan PostgreSQL, engine & Redis" { Wait-Container @("metadb", "engine", "redis") }
Invoke-Step "Mengosongkan PostgreSQL" { docker compose exec -T metadb sh /sps/sps.sh kosongkan }
Invoke-Step "Menyalin metadata ($sumber -> PostgreSQL)" {
    docker compose run --rm -e MYSQL_HOST=$hostLama -e MYSQL_PORT=$portLama superset `
        python /app/pythonpath/sps_pindah_meta.py salin
}

# --- 4. Struktur terbaru -------------------------------------------------------------------------
Invoke-Step "Memperbarui struktur metadata" { docker compose run --rm superset superset db upgrade }
Invoke-Step "Menyiapkan role & permission" { docker compose run --rm superset superset init }

# --- 5. Upload lama -> ALDx Engine ----------------------------------------------------------------
Invoke-Step "Memindahkan data upload lama ke ALDx Engine" {
    docker compose run --rm -e MYSQL_HOST=$hostLama -e MYSQL_PORT=$portLama superset `
        python /app/pythonpath/sps_pindah_meta.py upload
}

# --- 6. Selesai ----------------------------------------------------------------------------------
Set-EnvValue "METADB_JENIS" "postgres"
if ($sumber -ne "xampp") { docker compose --profile pindah rm -sf metadb-lama | Out-Null }

Write-Host "`nSelesai. Metadata kini di PostgreSQL (container metadb)." -ForegroundColor Green
if ($sumber -eq "xampp") { Write-Host "XAMPP tidak diubah; boleh dimatikan." }
else { Write-Host "Volume lama 'sps_metadb' disimpan sebagai cadangan. Hapus bila sudah yakin: docker volume rm sps_metadb" }
Write-Host "Lanjutkan: scripts\start.ps1, lalu buat cadangan baru: scripts\cadangkan.ps1"

exit 0
