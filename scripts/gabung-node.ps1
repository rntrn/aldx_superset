<#
.SYNOPSIS
    Menjadikan komputer INI node tambahan (scale-out) dari node utama.

.DESCRIPTION
    Syarat:
      - Docker Desktop terpasang di komputer ini
      - Folder D:\superset disalin dari node utama, TERMASUK .env
        (SUPERSET_SECRET_KEY & semua password harus sama dengan node utama)
      - Di node utama: CLUSTER_BIND=0.0.0.0, firewall membuka port 5433 (metadb),
        8124 (engine) & 6379 (Redis)
        (lihat docs\11-pusat-kendali-server.md bagian "Menambah node")

    Langkah skrip:
      1. Arahkan metadb, engine & Redis ke node utama, isi nama & alamat node ini di .env
      2. Uji koneksi ke metadb (5433), engine (8124) & Redis (6379) node utama
      3. Bangun image & jalankan web + backgrounder (jumlah proses otomatis
         dari CPU/RAM komputer ini = auto-tuning saat bergabung)

.PARAMETER Utama
    Alamat IP node utama, mis. 10.245.1.20

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\gabung-node.ps1 -Utama 10.245.1.20
#>
param([Parameter(Mandatory = $true)][string]$Utama)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
. "$PSScriptRoot\_umum.ps1"

if (-not (Test-Path ".env")) { throw "File .env belum ada. Salin .env dari node utama ke folder ini." }

# --- 1. .env ---------------------------------------------------------------------
$ipSaya = (Find-NetRoute -RemoteIPAddress $Utama | Where-Object IPAddress | Select-Object -First 1).IPAddress
if (-not $ipSaya) { throw "Tidak menemukan jalur jaringan ke $Utama." }
$portMetadb = Get-EnvValue "METADB_PORT_HOST"; if (-not $portMetadb) { $portMetadb = "5433" }
$portEngine = Get-EnvValue "ENGINE_PORT_HOST"; if (-not $portEngine) { $portEngine = "8124" }
Set-EnvValue "METADB_HOST" $Utama
Set-EnvValue "METADB_PORT" $portMetadb
Set-EnvValue "ENGINE_HOST" $Utama
Set-EnvValue "ENGINE_PORT" $portEngine
Set-EnvValue "REDIS_HOST" $Utama
Set-EnvValue "NODE_NAMA" $env:COMPUTERNAME
Set-EnvValue "NODE_ALAMAT" "${ipSaya}:8088"
Write-Host "Node ini: $env:COMPUTERNAME ($ipSaya) -> node utama $Utama" -ForegroundColor Green

# --- 2. Koneksi ke node utama ------------------------------------------------------------
foreach ($p in @(@{Port = [int]$portMetadb; Nama = "metadb"}, @{Port = [int]$portEngine; Nama = "engine"},
                 @{Port = 6379; Nama = "Redis"})) {
    $ok = (Test-NetConnection $Utama -Port $p.Port -WarningAction SilentlyContinue).TcpTestSucceeded
    if (-not $ok) {
        throw "$($p.Nama) node utama ($Utama`:$($p.Port)) tidak terjangkau. Buka firewall di node utama (docs\11)."
    }
    Write-Host "  $($p.Nama) node utama terjangkau." -ForegroundColor Green
}

# --- 3. Bangun & jalankan --------------------------------------------------------------------
docker compose -f docker-compose.node.yml build
if ($LASTEXITCODE -ne 0) { throw "Gagal membangun image." }
& "$PSScriptRoot\terapkan-server.ps1" -Tambahan

Write-Host "`nNode bergabung. Langkah terakhir di NODE UTAMA:" -ForegroundColor Yellow
Write-Host "  1. Pastikan node ini muncul di Pusat Kendali > Status (+/- 1 menit)"
Write-Host "  2. Jalankan scripts\terapkan-server.ps1 agar gateway ikut membagi beban ke $ipSaya"
Write-Host "  3. Di komputer INI, buka firewall masuk port 8088 untuk IP node utama"
