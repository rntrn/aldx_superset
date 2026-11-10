<#
.SYNOPSIS
    Mencadangkan / memulihkan metadata (metadb) dan, bila diminta, ALDx Engine.

.DESCRIPTION
    metadb  : user, role, koneksi, dataset, chart, dashboard, pengaturan Pusat Kendali,
              daftar ekstrak -> backup\metadb-<waktu>.dump (PostgreSQL, 14 terakhir disimpan)
    engine  : (-Engine) isi ALDx Engine: ekstrak, upload Excel/CSV, ramalan, data latihan
              -> backup\engine\engine-<waktu>.zip (5 terakhir disimpan)
              Ekstrak bisa dibuat ulang dari sumber, tetapi data UPLOAD hanya ada di engine.

    Jadwal harian + uji pulih mingguan otomatis: scripts\jadwal-cadangan.ps1. WAJIB juga sebelum upgrade.

    -UjiPulih  membuktikan cadangan bisa dipulihkan: dipulihkan ke database SEMENTARA (aplikasi tidak disentuh),
               isi pentingnya dihitung, lalu dihapus. Tanpa nama berkas = cadangan terbaru.
    -Salin     salin cadangan ke lokasi kedua (mis. \\server-arsip\aldx), agar selamat bila disk server rusak.
    -Simpan    jumlah cadangan metadb yang disimpan (bawaan 14; engine 5).
    Hasil setiap jalan dicatat di backup\cadangan.log dan server\status\cadangan.json (tampil di Pusat Kendali).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1            # metadb saja
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Engine    # metadb + engine
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Pulihkan backup\metadb-20260101-0200.dump
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -PulihkanEngine backup\engine\engine-20260101-0200.zip
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -UjiPulih                  # uji cadangan terbaru
    powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Engine -Salin \\arsip\aldx  # + salinan kedua
#>
param([switch]$Engine, [string]$Pulihkan, [string]$PulihkanEngine, [switch]$UjiPulih, [string]$Berkas,
      [string]$Salin, [int]$Simpan = 14)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force "backup\engine" | Out-Null

function Catat([string]$aksi, [string]$hasil, [string]$rincian) {
    # Log teks + status terakhir (dibaca Pusat Kendali > Status).
    $baris = "{0}  {1,-10} {2,-6} {3}" -f (Get-Date -Format "yyyy-MM-dd HH:mm"), $aksi, $hasil, $rincian
    Add-Content -Path "backup\cadangan.log" -Value $baris -Encoding UTF8
    New-Item -ItemType Directory -Force "server\status" | Out-Null
    $berkasStatus = "server\status\cadangan.json"
    $status = @{}
    if (Test-Path $berkasStatus) {
        (Get-Content $berkasStatus -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $status[$_.Name] = $_.Value }
    }
    $status[$aksi] = @{ waktu = (Get-Date -Format "yyyy-MM-dd HH:mm"); hasil = $hasil; rincian = $rincian }
    $status | ConvertTo-Json -Depth 4 | Set-Content -Path $berkasStatus -Encoding UTF8
}

function Konfirmasi([string]$pesan) {
    $jawab = Read-Host "$pesan Ketik YA untuk lanjut"
    if ($jawab -ne "YA") { Write-Host "Dibatalkan."; exit 0 }
}

# --- Uji pemulihan (tidak mengubah apa pun) ----------------------------------------------
if ($UjiPulih) {
    $pilih = if ($Berkas) { Get-Item "backup\$(Split-Path $Berkas -Leaf)" } else {
        Get-ChildItem "backup\metadb-*.dump" | Sort-Object Name -Descending | Select-Object -First 1 }
    if (-not $pilih) { Catat "uji-pulih" "GAGAL" "belum ada cadangan"; throw "Belum ada cadangan di backup\." }
    $env:BERKAS = $pilih.Name
    docker compose exec -T -e BERKAS metadb sh /sps/sps.sh ujipulih
    if ($LASTEXITCODE -ne 0) { Catat "uji-pulih" "GAGAL" $pilih.Name; throw "Uji pulih $($pilih.Name) GAGAL." }
    $mesin = Get-ChildItem "backup\engine\engine-*.zip" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($mesin -and -not $Berkas) {
        $env:BERKAS = $mesin.Name
        docker compose exec -T -e BERKAS engine sh /sps/sps.sh ujipulih
        if ($LASTEXITCODE -ne 0) { Catat "uji-pulih" "GAGAL" $mesin.Name; throw "Uji pulih $($mesin.Name) GAGAL." }
    }
    Catat "uji-pulih" "OK" ($pilih.Name + $(if ($mesin -and -not $Berkas) { " + " + $mesin.Name } else { "" }))
    Write-Host "Uji pulih berhasil: cadangan bisa dipulihkan." -ForegroundColor Green
    exit 0
}

# --- Pemulihan --------------------------------------------------------------------------
if ($Pulihkan) {
    $env:BERKAS = Split-Path $Pulihkan -Leaf
    if (-not (Test-Path "backup\$env:BERKAS")) { throw "Berkas backup\$env:BERKAS tidak ada." }
    if ((Select-String -Path "backup\$env:BERKAS" -Pattern "MariaDB dump|MySQL dump" -SimpleMatch -List -Quiet)) {
        throw "Berkas ini cadangan MariaDB versi lama. Pulihkan lewat: scripts\pindah-metadata.ps1 -DariBerkas $Pulihkan"
    }
    Konfirmasi "Semua metadata sekarang akan DIGANTI isi $env:BERKAS."
    docker compose stop superset superset-worker superset-beat
    docker compose exec -T -e BERKAS metadb sh /sps/sps.sh pulihkan
    if ($LASTEXITCODE -ne 0) { throw "Pemulihan metadb gagal." }
    docker compose up -d
    Write-Host "Metadata dipulihkan dari backup\$env:BERKAS." -ForegroundColor Green
    exit 0
}
if ($PulihkanEngine) {
    $env:BERKAS = Split-Path $PulihkanEngine -Leaf
    if (-not (Test-Path "backup\engine\$env:BERKAS")) { throw "Berkas backup\engine\$env:BERKAS tidak ada." }
    Konfirmasi "Seluruh isi ALDx Engine akan DIGANTI isi $env:BERKAS."
    docker compose exec -T -e BERKAS engine sh /sps/sps.sh pulihkan
    if ($LASTEXITCODE -ne 0) { throw "Pemulihan engine gagal." }
    Write-Host "ALDx Engine dipulihkan dari backup\engine\$env:BERKAS." -ForegroundColor Green
    exit 0
}

# --- Pencadangan ------------------------------------------------------------------------
$waktu = Get-Date -Format 'yyyyMMdd-HHmm'
$env:BERKAS = "metadb-$waktu.dump"
docker compose exec -T -e BERKAS metadb sh /sps/sps.sh cadangkan
if ($LASTEXITCODE -ne 0) { Catat "cadangan" "GAGAL" "metadb"; throw "Pencadangan metadb gagal. Cek: docker compose ps metadb" }
Get-ChildItem "backup\metadb-*.dump" | Sort-Object Name -Descending | Select-Object -Skip $Simpan | Remove-Item
$dibuat = @("backup\$env:BERKAS")
Write-Host "Cadangan metadata: backup\$env:BERKAS" -ForegroundColor Green

if ($Engine) {
    $env:BERKAS = "engine-$waktu.zip"
    docker compose exec -T -e BERKAS engine sh /sps/sps.sh cadangkan
    if ($LASTEXITCODE -ne 0) { Catat "cadangan" "GAGAL" "engine"; throw "Pencadangan engine gagal. Cek: docker compose logs engine" }
    Get-ChildItem "backup\engine\engine-*.zip" | Sort-Object Name -Descending | Select-Object -Skip 5 | Remove-Item
    Write-Host "Cadangan engine  : backup\engine\$env:BERKAS" -ForegroundColor Green
    $dibuat += "backup\engine\$env:BERKAS"
}

if ($Salin) {
    # Salinan kedua di luar server (folder jaringan / disk lain). Gagal menyalin tidak membatalkan cadangan.
    try {
        New-Item -ItemType Directory -Force $Salin | Out-Null
        foreach ($b in $dibuat) { Copy-Item -Path $b -Destination $Salin -Recurse -Force }
        Write-Host "Disalin ke       : $Salin" -ForegroundColor Green
    } catch {
        Catat "salin" "GAGAL" "$Salin ($($_.Exception.Message))"
        Write-Host "Peringatan: gagal menyalin ke $Salin ($($_.Exception.Message))" -ForegroundColor Yellow
    }
}
Catat "cadangan" "OK" (($dibuat | ForEach-Object { Split-Path $_ -Leaf }) -join " + ")
