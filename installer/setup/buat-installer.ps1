<#
.SYNOPSIS
    Membangun ALDx-Setup.exe (online) dan/atau ALDx-Setup-Offline.exe (+ .bin) di komputer ini,
    tanpa bergantung pada GitHub Actions.

.DESCRIPTION
    Online  : installer kecil; image Docker diunduh saat pemasangan.
    Offline : (-Offline) + semua image Docker ALDx (dari Docker di komputer ini, versi sesuai .env.example)
              + Docker Desktop Installer resmi. Pemasangan tanpa internet.
    Isi installer = kode terbaru di folder ini, tanpa log & perkakas pengembang (lihat Excludes di aldx-setup.iss).
    Versi = VERSI di config\sps_versi_aplikasi.py. Di GitHub Actions (.github\workflows\rilis.yml) skrip ini
    yang dipakai: -PakaiImageAda memakai offline\aldx-images.tar.gz buatan job Linux.
    Setiap hasil dipindai Windows Defender; bila terdeteksi, skrip berhenti dengan galat.

    Butuh: Inno Setup 6 (winget install JRSoftware.InnoSetup), Docker Desktop menyala (untuk -Offline).
    Hasil : installer\setup\Output\  (+ salinan ke -Salin bila diisi)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File installer\setup\buat-installer.ps1
    powershell -ExecutionPolicy Bypass -File installer\setup\buat-installer.ps1 -Offline -Salin D:\ALDX-cadangan\installer
    powershell -ExecutionPolicy Bypass -File installer\setup\buat-installer.ps1 -Offline -PakaiImageAda   # image tidak disimpan ulang
#>
param([switch]$Offline, [switch]$HanyaOffline, [switch]$PakaiImageAda, [string]$Salin = "")

$ErrorActionPreference = "Stop"
$SETUP = $PSScriptRoot
$AKAR = Split-Path (Split-Path $SETUP -Parent) -Parent
Set-Location $AKAR

function Langkah([string]$t) { Write-Host "`n==> $t" -ForegroundColor Cyan }

# --- Alat --------------------------------------------------------------------------------------------
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 belum terpasang. Jalankan: winget install JRSoftware.InnoSetup" }
$versi = (Select-String -Path config\sps_versi_aplikasi.py -Pattern '^VERSI\s*=\s*"(\d{4}\.\d{2}\.\d{2})"' | Select-Object -First 1).Matches[0].Groups[1].Value
$commit = (git rev-parse --short HEAD 2>$null)
Write-Host "ALDx $versi ($commit) · Inno Setup: $iscc"

function Pindai([string]$berkas) {
    # Windows Defender: pindai berkas hasil. Kode 0 = bersih, 2 = ancaman ditemukan.
    $mp = @("$env:ProgramFiles\Windows Defender\MpCmdRun.exe") + @(Get-ChildItem "$env:ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe" -ErrorAction SilentlyContinue |
           Sort-Object FullName -Descending | ForEach-Object FullName) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $mp -or $env:GITHUB_ACTIONS) { Write-Host "    (Windows Defender tidak tersedia di mesin ini, pemindaian dilewati)" -ForegroundColor Yellow; return }
    & $mp -Scan -ScanType 3 -File $berkas -DisableRemediation | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "    Defender: BERSIH  $(Split-Path $berkas -Leaf)" -ForegroundColor Green }
    else { throw "Windows Defender menandai $berkas (kode $LASTEXITCODE). Installer TIDAK boleh dibagikan." }
}

# Isi installer: berkas yang WAJIB ada (fitur AI, panduan, hapus bersih) dan yang TIDAK BOLEH ikut.
$WAJIB = @("config\ai.yaml", "config\sps_ai\wawasan.py", "config\sps_ai\kunci_api.py", "config\sps_ai\tab.js",
           "config\sps_app\static\ai.js", "config\sps_panduan\tampilan.py", "scripts\hapus-total.ps1",
           "scripts\hapus-aldx.ps1", "docs\28-sambungkan-asisten-ai.md", "docs\pdf\cara-pasang.pdf", "installer\pasang.ps1",
           "config\sps_versi_aplikasi.py", "config\sps_latihan_wilayah.py", "config\sps_studio\definisi.py",
           "config\sps_studio\static\huruf\huruf.css", "config\sps_app\static\telusur.js", "docs\31-catatan-versi.md")
$TERLARANG = '(^|\\)(CHANGELOG\.md|bersih\.kecuali|buat-installer\.ps1|terbitkan\.ps1|laporan-qa\.(md|pdf)|unins\d+\.(exe|dat)|\.env|[^\\]+\.(log|dump|sql\.gz))$|' +
             '(^|\\)(\.github|tests|\.git|node_modules|\.vitepress)\\'

function Periksa-Isi([string]$manifest) {
    # Kolom ke-2 = berkas sumber (…\installer\setup\..\..\<jalur>); baris pertama = judul kolom.
    $isi = Get-Content $manifest | Select-Object -Skip 1 | ForEach-Object { ($_ -split "`t")[1] } | Where-Object { $_ } |
           ForEach-Object { ($_ -replace '^.*?\\\.\.\\\.\.\\', '').Trim() }
    $hilang = $WAJIB | Where-Object { $w = $_; -not ($isi | Where-Object { $_ -like "*$w" }) }
    $bocor = $isi | Where-Object { $_ -match $TERLARANG }
    if ($hilang) { throw "Installer TIDAK memuat berkas wajib: $($hilang -join ', ')" }
    if ($bocor) { throw "Installer memuat berkas terlarang: $(($bocor | Select-Object -First 5) -join ', ')" }
    Write-Host "    Isi: $($isi.Count) berkas · semua berkas wajib ada · tanpa log pengembangan/rahasia" -ForegroundColor Green
}

function Iscc([string[]]$argumen) {
    # Antivirus kadang mengunci exe yang sedang ditulis ("EndUpdateResource failed (110)") dan meninggalkan
    # potongan kecil. Coba ulang sampai 3 kali; potongan gagal dihapus agar tidak terunggah.
    for ($i = 1; $i -le 3; $i++) {
        & $iscc /Q @argumen
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "    Inno Setup gagal (kode $LASTEXITCODE), percobaan $i/3; menunggu antivirus selesai memindai..." -ForegroundColor Yellow
        Start-Sleep -Seconds (10 * $i)
    }
    throw "Inno Setup gagal 3 kali. Tambahkan folder $SETUP\Output ke pengecualian antivirus, lalu ulangi."
}

function Bangun([string[]]$argumen, [string]$pola) {
    Remove-Item "$SETUP\Output\isi-installer.txt" -ErrorAction SilentlyContinue
    Iscc (@("/DVersi=$versi", "/DManifest") + $argumen + @("$SETUP\aldx-setup.iss"))
    $kecil = Get-ChildItem "$SETUP\Output\$pola" -Filter *.exe | Where-Object { $pola -notlike "*Offline*" -and $_.Length -lt 50MB }
    if ($kecil) { Remove-Item $kecil.FullName -Force; throw "Hasil $($kecil.Name) terlalu kecil ($([math]::Round($kecil.Length/1KB)) KB): pembuatan terpotong." }
    Periksa-Isi "$SETUP\Output\isi-installer.txt"
    Remove-Item "$SETUP\Output\isi-installer.txt" -ErrorAction SilentlyContinue
    Get-ChildItem "$SETUP\Output\$pola" | ForEach-Object {
        Write-Host ("    {0,-36} {1,10:N1} MB" -f $_.Name, ($_.Length / 1MB))
        Pindai $_.FullName
    }
}

New-Item -ItemType Directory -Force "$SETUP\Output" | Out-Null
# Kode yang dibekukan ke installer -> tampil di halaman login & Beranda (config\versi.json, tidak di-commit).
[IO.File]::WriteAllText("$AKAR\config\versi.json", ('{"commit": "' + $commit + '", "tanggal": "' + (Get-Date -Format "yyyy-MM-dd") + '"}'), (New-Object Text.UTF8Encoding $false))

# --- Online --------------------------------------------------------------------------------------------
if (-not $HanyaOffline) {
    Langkah "Membangun ALDx-Setup.exe (online)"
    Remove-Item "$SETUP\Output\ALDx-Setup.exe" -ErrorAction SilentlyContinue
    Bangun @() "ALDx-Setup.exe"

    Langkah "Membangun ALDx-HapusTotal.exe (pembersih total, satu berkas)"
    Remove-Item "$SETUP\Output\ALDx-HapusTotal.exe", "$SETUP\Output\isi-hapus-total.txt" -ErrorAction SilentlyContinue
    Iscc @("/DVersi=$versi", "/DManifest", "$SETUP\aldx-hapus-total.iss")
    if ((Get-Item "$SETUP\Output\ALDx-HapusTotal.exe").Length -lt 1MB) { throw "ALDx-HapusTotal.exe terpotong." }
    $isiHapus = Get-Content "$SETUP\Output\isi-hapus-total.txt" | Select-Object -Skip 1 | ForEach-Object { Split-Path (($_ -split "`t")[1]) -Leaf }
    if (@($isiHapus) -join "," -ne "hapus-total.ps1,_umum.ps1") { throw "Isi ALDx-HapusTotal.exe tidak sesuai: $($isiHapus -join ', ')" }
    Remove-Item "$SETUP\Output\isi-hapus-total.txt"
    $h = Get-Item "$SETUP\Output\ALDx-HapusTotal.exe"
    Write-Host ("    Isi: hapus-total.ps1 + _umum.ps1 saja" ) -ForegroundColor Green
    Write-Host ("    {0,-36} {1,10:N1} MB" -f $h.Name, ($h.Length / 1MB))
    Pindai $h.FullName
}

# --- Offline -------------------------------------------------------------------------------------------
if ($Offline -or $HanyaOffline) {
    Langkah "Menyiapkan image Docker (versi .env.example)"
    $sudahAda = $PakaiImageAda -and (Test-Path "offline\aldx-images.tar.gz")     # mis. dibuat job Linux di GitHub Actions
    if (-not $sudahAda) { docker info *> $null; if ($LASTEXITCODE -ne 0) { throw "Docker Desktop tidak menyala." } }
    $v = @{}; Get-Content .env.example | Where-Object { $_ -match '^(\w+)=(.*)$' } | ForEach-Object { $v[$Matches[1]] = $Matches[2].Trim() }
    $img = @("sps-superset:$($v.SUPERSET_VERSION)", "redis:$($v.REDIS_VERSI)-alpine", "postgres:$($v.METADB_VERSI)-alpine",
             "clickhouse/clickhouse-server:$($v.ENGINE_VERSI)", "nginx:$($v.GATEWAY_VERSI)-alpine")
    foreach ($i in $(if ($sudahAda) { @() } else { $img })) {
        docker image inspect $i *> $null
        if ($LASTEXITCODE -eq 0) { Write-Host "    ada   $i"; continue }
        if ($i -like "sps-superset:*") { docker build docker --build-arg "SUPERSET_VERSION=$($v.SUPERSET_VERSION)" -t $i }
        else { docker pull -q $i }
        if ($LASTEXITCODE -ne 0) { throw "Image $i tidak bisa disiapkan." }
    }
    New-Item -ItemType Directory -Force offline | Out-Null
    $tar = "offline\aldx-images.tar"
  if ($PakaiImageAda -and (Test-Path "offline\aldx-images.tar.gz")) {
    Write-Host "    memakai offline\aldx-images.tar.gz yang sudah ada (-PakaiImageAda)"
  } else {
    Write-Host "    menyimpan image (beberapa menit)..."
    docker save -o $tar @img
    if ($LASTEXITCODE -ne 0) { throw "docker save gagal." }
    Write-Host "    memadatkan (gzip)..."
    $masuk = [IO.File]::OpenRead((Resolve-Path $tar)); $keluar = [IO.File]::Create("$AKAR\offline\aldx-images.tar.gz")
    $gz = New-Object IO.Compression.GZipStream($keluar, [IO.Compression.CompressionLevel]::Fastest)
    try { $masuk.CopyTo($gz) } finally { $gz.Dispose(); $keluar.Dispose(); $masuk.Dispose() }
    Remove-Item $tar
  }
    "$versi-$commit" | Set-Content offline\versi.txt -Encoding ASCII
    if (-not (Test-Path offline\DockerDesktopInstaller.exe)) {
        Write-Host "    mengunduh Docker Desktop Installer resmi (desktop.docker.com)..."
        Invoke-WebRequest "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -OutFile offline\DockerDesktopInstaller.exe
    }
    $tt = Get-AuthenticodeSignature offline\DockerDesktopInstaller.exe
    if ($tt.Status -ne "Valid" -or $tt.SignerCertificate.Subject -notmatch "Docker") {
        throw "Tanda tangan Docker Desktop Installer tidak valid ($($tt.Status)). Hapus offline\DockerDesktopInstaller.exe lalu ulangi."
    }
    Write-Host "    Docker Desktop Installer: tanda tangan Docker Inc. valid" -ForegroundColor Green

    Langkah "Membangun ALDx-Setup-Offline.exe (+ .bin)"
    Remove-Item "$SETUP\Output\ALDx-Setup-Offline*" -ErrorAction SilentlyContinue
    Bangun @("/DOffline") "ALDx-Setup-Offline*"
}

# --- Salinan --------------------------------------------------------------------------------------------
if ($Salin) {
    Langkah "Menyalin ke $Salin"
    New-Item -ItemType Directory -Force $Salin | Out-Null
    Copy-Item "$SETUP\Output\*" $Salin -Force
}
Write-Host "`nSelesai. Hasil: $SETUP\Output$(if ($Salin) { " dan $Salin" })" -ForegroundColor Green
