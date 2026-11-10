<#
.SYNOPSIS
    Menghapus ALDx SEPENUHNYA dari komputer ini (uninstall total bersih), setelah mencadangkan data.

.DESCRIPTION
    Berbeda dengan Settings > Apps > ALDx > Uninstall (data bisa dipertahankan untuk pasang ulang), skrip ini
    tidak menyisakan apa pun dari ALDx:

      1. Cadangan        metadata + ALDx Engine + .env disalin ke folder DI LUAR instalasi
                         (bawaan: Dokumen\ALDx-cadangan-<waktu>). Gagal -> berhenti, tidak ada yang dihapus.
      2. Docker          container, volume data (sps_metadb_pg, sps_engine, ...), jaringan, dan image ALDx.
      3. Windows         tugas terjadwal cadangan, sertifikat HTTPS ALDx yang dipercayai (Trusted Root
                         pengguna ini), pintasan Desktop & menu Start, entri di Settings > Apps.
      4. Folder          folder instalasi ini dihapus setelah skrip selesai.

    Yang TIDAK disentuh: Docker Desktop, Ollama/LM Studio, project Docker lain, dan cache build Docker
    (hapus manual bila perlu: docker builder prune; ini juga menghapus cache project lain).

    Kode keluar: 0 berhasil · 1 dibatalkan · 2 Docker Desktop tidak menyala · 3 cadangan gagal (tidak ada yang dihapus)

.PARAMETER SimpanCadangan  Folder tujuan cadangan (bawaan: Dokumen\ALDx-cadangan-<waktu>).
.PARAMETER TanpaCadangan   Lewati cadangan (data hilang permanen).
.PARAMETER Ya              Tanpa pertanyaan konfirmasi (untuk otomatisasi).
.PARAMETER SimpanFolder    Jangan hapus folder instalasi (mis. untuk memasang ulang dari folder yang sama).
.PARAMETER Simulasi        Hanya tampilkan apa saja yang AKAN dihapus; tidak ada yang diubah.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\hapus-total.ps1
    powershell -ExecutionPolicy Bypass -File scripts\hapus-total.ps1 -SimpanCadangan D:\Arsip\ALDx
#>
param([string]$SimpanCadangan = "", [switch]$TanpaCadangan, [switch]$Ya, [switch]$SimpanFolder, [switch]$Simulasi)

$ErrorActionPreference = "Continue"
$AKAR = Split-Path $PSScriptRoot -Parent
Set-Location $AKAR
. "$PSScriptRoot\_umum.ps1"
$Host.UI.RawUI.WindowTitle = "Menghapus total ALDx"
$APP_ID = "{6D3C2A61-4E0B-4C5E-9B7A-1A1D0C000001}_is1"         # AppId installer (installer\setup\aldx-setup.iss)

function Langkah([string]$teks) { Write-Host "`n==> $teks" -ForegroundColor Cyan }
function Keluar([int]$kode, [string]$pesan, [string]$warna = "Green") {
    Write-Host "`n$pesan" -ForegroundColor $warna
    if (-not $Ya) { Read-Host "Tekan Enter untuk menutup" | Out-Null }
    exit $kode
}

# --- Simulasi: daftar jejak ALDx di komputer ini, tanpa mengubah apa pun ---------------------------------
if ($Simulasi) {
    Write-Host "SIMULASI hapus total ALDx (tidak ada yang dihapus)" -ForegroundColor Cyan
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nContainer :"; docker ps -a --filter "name=^sps_" --format "  {{.Names}}  ({{.Status}})"
        Write-Host "Volume    :"; docker volume ls -q | Where-Object { $_ -match '^(sps_|aldx)' } | ForEach-Object { "  $_" }
        Write-Host "Image     :"; docker compose --profile pindah config --images 2>$null | Sort-Object -Unique | ForEach-Object { "  $_" }
    } else { Write-Host "Docker Desktop tidak menyala: bagian Docker tidak bisa diperiksa." -ForegroundColor Yellow }
    Write-Host "Tugas     :"; Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like "ALDx*" } | ForEach-Object { "  $($_.TaskName)" }
    $toko = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser"); $toko.Open("ReadOnly")
    Write-Host "Sertifikat:"; $toko.Certificates | Where-Object { $_.Subject -match '(^|, )O=ALDx(,|$)' } | ForEach-Object { "  $($_.Subject)" }; $toko.Close()
    Write-Host "Pintasan  :"; @((Join-Path ([Environment]::GetFolderPath("Programs")) "ALDx"), (Join-Path ([Environment]::GetFolderPath("Desktop")) "ALDx.lnk")) |
        Where-Object { Test-Path $_ } | ForEach-Object { "  $_" }
    Write-Host "Entri Apps:"; @("HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$APP_ID", "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$APP_ID") |
        Where-Object { Test-Path $_ } | ForEach-Object { "  $_" }
    Write-Host "Folder    :`n  $AKAR$(if ($SimpanFolder) { ' (dipertahankan)' })"
    exit 0
}

# --- 0. Konfirmasi ----------------------------------------------------------------------------------
if (-not $SimpanCadangan) {
    $SimpanCadangan = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "ALDx-cadangan-$(Get-Date -Format 'yyyyMMdd-HHmm')"
}
Write-Host "HAPUS TOTAL ALDx" -ForegroundColor Red
Write-Host "Folder instalasi : $AKAR$(if ($SimpanFolder) { ' (dipertahankan)' })"
Write-Host "Cadangan ke      : $(if ($TanpaCadangan) { 'TIDAK ADA - data hilang permanen' } else { $SimpanCadangan })"
Write-Host "Dihapus          : container, data, image, tugas terjadwal, sertifikat, pintasan, entri Apps$(if (-not $SimpanFolder) { ', folder' })"
if (-not $Ya) {
    $jawab = Read-Host "`nKetik HAPUS untuk melanjutkan"
    if ($jawab -cne "HAPUS") { Keluar 1 "Dibatalkan. Tidak ada yang dihapus." "Yellow" }
}

docker info *> $null
$dockerHidup = $LASTEXITCODE -eq 0
$adaContainer = $dockerHidup -and (docker ps -a --filter "name=^sps_" --format "{{.Names}}")
if (-not $dockerHidup) { Keluar 2 "Docker Desktop tidak menyala. Nyalakan dulu agar data bisa dicadangkan & dihapus." "Yellow" }

# --- 1. Cadangan --------------------------------------------------------------------------------------
if (-not $TanpaCadangan) {
    Langkah "Mencadangkan data ke $SimpanCadangan"
    New-Item -ItemType Directory -Force $SimpanCadangan | Out-Null
    if ($adaContainer) {
        docker compose up -d metadb engine *> $null
        Wait-Container @("metadb", "engine") 120
        & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\cadangkan.ps1" -Engine -Salin $SimpanCadangan
        if ($LASTEXITCODE -ne 0) { Keluar 3 "Cadangan GAGAL: demi keamanan TIDAK ada yang dihapus." "Red" }
    }
    if (Test-Path ".env") { Copy-Item ".env" (Join-Path $SimpanCadangan "env-RAHASIA.env") }
    if (Test-Path "backup") { Copy-Item "backup\*" $SimpanCadangan -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host "OK  cadangan: $SimpanCadangan" -ForegroundColor Green
}

# --- 2. Docker ----------------------------------------------------------------------------------------
Langkah "Menghapus container, volume data, jaringan & image ALDx"
docker compose --profile pindah down --volumes --remove-orphans --rmi all 2>&1 | Out-Host
# Sisa dengan awalan sps_ (mis. dari folder instalasi lain / versi lama)
docker ps -aq --filter "name=^sps_" | ForEach-Object { docker rm -f $_ *> $null }
docker volume ls -q | Where-Object { $_ -match '^(sps_|aldx)' } | ForEach-Object { docker volume rm -f $_ *> $null }
docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match '^sps-superset' } | ForEach-Object { docker rmi -f $_ *> $null }
Write-Host "OK  Docker bersih dari ALDx" -ForegroundColor Green

# --- 3. Windows ---------------------------------------------------------------------------------------
Langkah "Menghapus tugas terjadwal, sertifikat, pintasan & entri Apps"
foreach ($tugas in @("ALDx Cadangan Harian", "ALDx Uji Pulih Mingguan")) {
    Unregister-ScheduledTask -TaskName $tugas -Confirm:$false -ErrorAction SilentlyContinue
}
try {
    $toko = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $toko.Open("ReadWrite")
    $sert = @($toko.Certificates | Where-Object { $_.Subject -match '(^|, )O=ALDx(,|$)' })
    foreach ($s in $sert) { $toko.Remove($s) }                # Windows bisa meminta konfirmasi: pilih Yes
    $toko.Close()
    Write-Host "OK  sertifikat ALDx dihapus: $($sert.Count)"
} catch { Write-Host "Sertifikat tidak bisa dihapus: $($_.Exception.Message)" -ForegroundColor Yellow }
$pintasan = @(
    (Join-Path ([Environment]::GetFolderPath("Programs")) "ALDx"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "ALDx.lnk"),
    (Join-Path ([Environment]::GetFolderPath("CommonDesktopDirectory")) "ALDx.lnk")
)
$pintasan | Where-Object { Test-Path $_ } | ForEach-Object { Remove-Item $_ -Recurse -Force -ErrorAction SilentlyContinue }
foreach ($kunci in @("HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$APP_ID",
                     "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$APP_ID",
                     "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$APP_ID")) {
    if (Test-Path $kunci) { Remove-Item $kunci -Recurse -Force -ErrorAction SilentlyContinue }
}
Write-Host "OK  Windows bersih dari ALDx" -ForegroundColor Green

# --- 4. Folder instalasi --------------------------------------------------------------------------------
if ($SimpanFolder) { Keluar 0 "Selesai. Folder $AKAR dipertahankan.$(if (-not $TanpaCadangan) { " Cadangan: $SimpanCadangan" })" }
Langkah "Menghapus folder $AKAR"
Set-Location $env:TEMP
# Skrip ini berjalan dari dalam folder itu: hapus setelah jendela ini tertutup.
Start-Process cmd.exe -ArgumentList "/c timeout /t 3 /nobreak >nul & rmdir /s /q `"$AKAR`"" -WindowStyle Hidden
Keluar 0 "ALDx sudah dihapus total.$(if (-not $TanpaCadangan) { " Cadangan (simpan baik-baik; berisi rahasia): $SimpanCadangan" })"
