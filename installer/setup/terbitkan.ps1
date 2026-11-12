<#
.SYNOPSIS
    Satu perintah setelah setiap perbaikan: bangun installer online & offline, lalu terbitkan ke GitHub Releases.

.DESCRIPTION
    1. Pemeriksaan  : semua perubahan sudah di-commit DAN di-push (installer = commit yang tercatat di git).
    2. Bangun       : buat-installer.ps1 -Offline (online, pembersih total, offline) + pemeriksaan isi + Defender.
    3. Terbitkan    : rilis "terbaru" (ALDx-Setup.exe, ALDx-HapusTotal.exe) & "offline" (ALDx-Setup-Offline.exe,
                      -1.bin, ALDx-HapusTotal.exe) di SETIAP repo -Repo (bawaan: aldx_superset & superset-ald); berkas lama diganti; ukuran di GitHub
                      DICOCOKKAN dengan berkas lokal (diulang 3x bila terpotong / koneksi putus).
    4. Catatan rilis: versi & commit ditulis ulang di kedua rilis.

    Butuh: Inno Setup 6, Docker Desktop menyala, GitHub CLI yang sudah login (gh auth login).

.EXAMPLE
    pwsh -File installer\setup\terbitkan.ps1                 # image Docker offline dipakai ulang bila ada
    pwsh -File installer\setup\terbitkan.ps1 -ImageBaru      # simpan ulang image (setelah ganti versi komponen)
#>
# Kedua repo punya halaman Releases yang dipakai pengguna (README masing-masing menautkannya): selalu terbitkan ke keduanya.
param([string[]]$Repo = @("rntrn/aldx_superset", "rntrn/superset-ald"), [switch]$ImageBaru, [switch]$LewatiPemeriksaanGit)

$ErrorActionPreference = "Stop"
$SETUP = $PSScriptRoot
$AKAR = Split-Path (Split-Path $SETUP -Parent) -Parent
$OUT = "$SETUP\Output"
Set-Location $AKAR
function Langkah([string]$t) { Write-Host "`n==> $t" -ForegroundColor Cyan }

$gh = @((Get-Command gh -ErrorAction SilentlyContinue).Source,
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe",
        "$env:ProgramFiles\GitHub CLI\gh.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $gh) { throw "GitHub CLI belum terpasang: winget install GitHub.cli, lalu gh auth login" }
& $gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw "GitHub CLI belum login. Jalankan: & `"$gh`" auth login" }

# --- 1. Semua perubahan sudah di git ---------------------------------------------------------------------
if (-not $LewatiPemeriksaanGit) {
    Langkah "Memeriksa git"
    if (git status --porcelain) { throw "Ada perubahan yang belum di-commit. Commit & push dulu agar installer = versi di git." }
    git fetch -q origin
    $maju = (git rev-list --count "origin/main..HEAD")
    if ([int]$maju -gt 0) { throw "$maju commit belum di-push ke origin. Jalankan git push dulu." }
}
$commit = git rev-parse --short HEAD
$versi = (Select-String -Path config\sps_versi_aplikasi.py -Pattern '^VERSI\s*=\s*"(\d{4}\.\d{2}\.\d{2})"' | Select-Object -First 1).Matches[0].Groups[1].Value
Write-Host "Versi $versi · commit $commit · repo rilis $($Repo -join ", ")"

# --- 2. Bangun -------------------------------------------------------------------------------------------
Langkah "Membangun installer online, pembersih total, offline"
# Splat HASHTABLE (bukan array): array mengirim "-Offline" sebagai teks posisional sehingga terbaca sebagai -Salin.
$p = @{ Offline = $true; Salin = "D:\ALDX-cadangan\installer" }
if (-not $ImageBaru) { $p.PakaiImageAda = $true }
& "$SETUP\buat-installer.ps1" @p
foreach ($f in "ALDx-Setup.exe", "ALDx-HapusTotal.exe", "ALDx-Setup-Offline.exe", "ALDx-Setup-Offline-1.bin") {
    $b = Get-Item "$OUT\$f" -ErrorAction SilentlyContinue
    if (-not $b -or $b.LastWriteTime -lt (Get-Date).AddMinutes(-30)) { throw "$f tidak ikut dibangun ulang pada run ini." }
}

# --- 3. Terbitkan dengan pencocokan ukuran ------------------------------------------------------------------
$env:GODEBUG = "http2client=0"          # HTTP/1.1: lebih tahan untuk berkas besar
function Ukuran([string]$tag, [string]$nama) {
    $j = & $gh release view $tag -R $R --json assets 2>$null | ConvertFrom-Json
    ($j.assets | Where-Object { $_.name -eq $nama } | Select-Object -First 1).size
}
function Terbitkan([string]$tag, [string]$judul, [string]$catatan, [string[]]$berkas, [bool]$terbaru) {
    Langkah "Rilis '$tag'"
    & $gh release view $tag -R $R *> $null
    if ($LASTEXITCODE -ne 0) {
        & $gh release create $tag -R $R --target main --title $judul --notes $catatan "--latest=$($terbaru.ToString().ToLower())" | Out-Null
    } else {
        & $gh release edit $tag -R $R --title $judul --notes $catatan | Out-Null
    }
    foreach ($b in $berkas) {
        $nama = Split-Path $b -Leaf; $lokal = (Get-Item $b).Length; $ok = $false
        for ($i = 1; $i -le 3 -and -not $ok; $i++) {
            if ($null -ne (Ukuran $tag $nama)) { & $gh release delete-asset $tag $nama -R $R -y 2>&1 | Out-Null }
            & $gh release upload $tag $b -R $R 2>&1 | Out-Null
            $di = Ukuran $tag $nama; $ok = ($di -eq $lokal)
            if (-not $ok) { Write-Host "    $nama percobaan $i : GitHub $di vs lokal $lokal, ulangi..." -ForegroundColor Yellow; Start-Sleep 10 }
        }
        if (-not $ok) { throw "Unggah $nama ke rilis '$tag' gagal 3 kali (ukuran tidak cocok)." }
        Write-Host ("    {0,-28} {1,10:N1} MB  COCOK" -f $nama, ($lokal / 1MB)) -ForegroundColor Green
    }
}

$umum = "Dibangun dari commit $commit. Semua berkas dipindai Windows Defender (bersih) dan isinya diperiksa. " +
        "SmartScreen 'Windows protected your PC': More info > Run anyway.`n`n" +
        "ALDx-HapusTotal.exe = pembersih total satu berkas (cadangan ke Dokumen, lalu container, image, volume, jaringan, " +
        "Kubernetes ALDx, sertifikat, tugas terjadwal, pintasan, entri Apps & folder ALDx dihapus)."
foreach ($R in $Repo) {
Write-Host "`n### Repo $R" -ForegroundColor Cyan
Terbitkan "terbaru" "ALDx terbaru ($versi)" ("ALDx $versi (online)`n`n1. Komputer sudah punya Docker Desktop (menyala).`n" +
    "2. Unduh ALDx-Setup.exe, klik dua kali, Lanjut > Lanjut > Pasang. Pasang di atas versi lama: data & pengaturan tetap.`n" +
    "3. Setelah terpasang: Beranda > kartu 'Siapkan ALDx'; Asisten AI: Ctrl + I > Sambungkan AI.`n`n" +
    "Tanpa internet: rilis 'ALDx offline'.`n`n$umum") @("$OUT\ALDx-Setup.exe", "$OUT\ALDx-HapusTotal.exe") $true
Terbitkan "offline" "ALDx offline ($versi)" ("ALDx $versi (offline) - pasang TANPA internet.`n`n" +
    "1. Unduh ALDx-Setup-Offline.exe dan ALDx-Setup-Offline-1.bin ke SATU folder.`n" +
    "2. Klik dua kali ALDx-Setup-Offline.exe. Semua image Docker ALDx & Docker Desktop Installer resmi sudah di dalamnya.`n`n$umum") `
    @("$OUT\ALDx-Setup-Offline.exe", "$OUT\ALDx-Setup-Offline-1.bin", "$OUT\ALDx-HapusTotal.exe") $false
}

Write-Host "`nSelesai: installer online & offline commit $commit terbit di:" -ForegroundColor Green
$Repo | ForEach-Object { Write-Host "  https://github.com/$_/releases" -ForegroundColor Green }
