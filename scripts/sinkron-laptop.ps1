<#
.SYNOPSIS
    Menyamakan ALDx di laptop/server dengan versi terbaru di GitHub, menguji, lalu (opsional) menerbitkan installer.

.DESCRIPTION
    Satu perintah untuk semua langkah setelah ada perubahan di GitHub:

      1. Pemeriksaan awal  : folder repo, git, Docker Desktop menyala, tidak ada perubahan lokal yang belum di-commit.
      2. Ambil versi baru  : git fetch + checkout cabang (bawaan main) + pull (fast-forward saja, riwayat tidak ditulis ulang).
      3. Terapkan          : docker compose up -d, restart web & backgrounder (konfigurasi di config\ dibaca ulang),
                             build-dashboards (menu, izin, role baru seperti "Penonton Sematan").
      4. Uji               : scripts\uji.ps1, semua harus LULUS.
      5. -KomitInstaller   : commit & push folder installer\setup dan .github\workflows bila belum ada di repo.
      6. -Terbitkan        : bangun & unggah installer online, offline, HapusTotal (installer\setup\terbitkan.ps1).
                             Inno Setup & GitHub CLI dipasang otomatis bila belum; login GitHub dibuka di browser.

    Data, akun, dan .env TIDAK diubah. Bila satu langkah gagal, skrip berhenti dan menjelaskan apa yang harus dilakukan.
    Catatan lengkap tersimpan di installer\log\sinkron-<waktu>.log.

.PARAMETER Cabang
    Cabang git yang dipakai. Bawaan "main". Isi nama cabang PR untuk mencoba perubahan sebelum di-merge.

.PARAMETER KomitInstaller
    Commit & push installer\setup dan .github\workflows (berkas hasil build di installer\setup\Output tidak ikut).

.PARAMETER Terbitkan
    Jalankan installer\setup\terbitkan.ps1 setelah uji lulus.

.PARAMETER JadikanGit
    Untuk folder yang dipasang dengan ALDx-Setup.exe (belum ada .git): jadikan folder git yang mengikuti GitHub.
    Berkas program diganti versi GitHub; .env, cadangan, log, dan data Docker TIDAK disentuh (.env disalin dulu
    ke installer\log). Cukup sekali; berikutnya skrip berjalan tanpa pilihan ini.

.PARAMETER TanpaUji
    Lewati scripts\uji.ps1 (tidak disarankan; -Terbitkan tidak bisa dipakai bersama ini).

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1
    Ambil versi terbaru main, terapkan, uji (dijalankan di jendela PowerShell yang sedang terbuka).

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1 -KomitInstaller -Terbitkan
    Sekaligus simpan skrip installer ke repo dan terbitkan installer baru ke GitHub Releases.

.EXAMPLE
    Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1 -JadikanGit
    Folder hasil ALDx-Setup.exe: jadikan folder git (sekali), lalu ambil versi terbaru, terapkan, uji.
    Coba isi PR sebelum di-merge.
#>
param(
    [string]$Cabang = "main",
    [switch]$KomitInstaller,
    [switch]$Terbitkan,
    [switch]$JadikanGit,
    [switch]$TanpaUji
)

$ErrorActionPreference = "Stop"
$Akar = Split-Path $PSScriptRoot -Parent
$Repo = "https://github.com/rntrn/aldx_superset.git"
# PowerShell yang sedang menjalankan skrip ini (powershell.exe atau pwsh.exe), dipakai untuk skrip lain.
# Tidak memakai nama "powershell" karena di sebagian komputer tidak ada di PATH.
$PS = (Get-Process -Id $PID).Path
Set-Location $Akar

# ---------- Alat bantu tampilan ----------
$script:nomor = 0
function Langkah([string]$judul) {
    $script:nomor++
    Write-Host "`n[$script:nomor] $judul" -ForegroundColor Cyan
}
function Ok([string]$pesan)    { Write-Host "    OK  $pesan" -ForegroundColor Green }
function Info([string]$pesan)  { Write-Host "    ..  $pesan" }
function Gagal([string]$pesan, [string]$saran) {
    Write-Host "`n    GAGAL: $pesan" -ForegroundColor Red
    if ($saran) { Write-Host "    Yang harus dilakukan: $saran" -ForegroundColor Yellow }
    Stop-Transcript | Out-Null
    exit 1
}
# Jalankan perintah luar; berhenti bila kode keluarnya bukan 0.
# EAP "Continue" di sini: git & docker menulis kemajuan ke stderr, yang di Windows PowerShell 5.1 + "Stop"
# bisa dianggap error fatal walau perintahnya berhasil. Keberhasilan dinilai dari kode keluar.
# Keluaran dialirkan lewat Out-Host agar ikut tercatat di log (transcript Windows PowerShell 5.1 tidak mencatat
# keluaran program luar yang langsung ke konsol; dulu pesan galat terbitkan.ps1 hilang dari log).
function Jalankan([string]$keterangan, [scriptblock]$perintah, [string]$saran) {
    $ErrorActionPreference = "Continue"
    & $perintah 2>&1 | ForEach-Object { "$_" } | Out-Host
    if ($LASTEXITCODE -ne 0) { Gagal "$keterangan (kode $LASTEXITCODE)" $saran }
}
function Diam([scriptblock]$perintah) {         # jalankan tanpa output; kembalikan kode keluar
    $ErrorActionPreference = "Continue"
    & $perintah *> $null
    return $LASTEXITCODE
}

if ($Terbitkan -and $TanpaUji) { Write-Host "-Terbitkan tidak boleh bersama -TanpaUji: installer hanya diterbitkan dari versi yang lulus uji." -ForegroundColor Red; exit 1 }

New-Item -ItemType Directory -Force -Path "$Akar\installer\log" | Out-Null
$log = "$Akar\installer\log\sinkron-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null
Write-Host "ALDx - sinkron laptop ($Akar), cabang: $Cabang" -ForegroundColor White

# ---------- 1. Pemeriksaan awal ----------
Langkah "Pemeriksaan awal"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Gagal "git belum terpasang" "winget install Git.Git, lalu buka PowerShell baru." }
Ok "git $((git --version) -replace 'git version ','')"
if (-not (Test-Path "$Akar\.git")) {
    if (-not $JadikanGit) { Gagal "folder ini dipasang dengan Setup.exe (belum folder git)" "jalankan lagi dengan tambahan -JadikanGit (sekali saja)." }
    Langkah "Jadikan folder git (sekali saja)"
    if (Test-Path "$Akar\.env") {
        Copy-Item "$Akar\.env" "$Akar\installer\log\env-cadangan-$(Get-Date -Format 'yyyyMMdd-HHmmss').env"
        Ok ".env dicadangkan ke installer\log (tidak akan diubah)"
    }
    Jalankan "git init gagal" { git init -q } ""
    Jalankan "menambah alamat GitHub gagal" { git remote add origin $Repo } ""
    Jalankan "mengunduh dari GitHub gagal" { git fetch origin $Cabang } "cek internet & login GitHub (jendela login Git akan muncul untuk repo privat)."
    # -f: berkas program diganti versi GitHub. .env, backup\, log & data Docker tidak dilacak git, jadi tidak tersentuh.
    Jalankan "mengambil berkas versi GitHub gagal" { git checkout -q -f -B $Cabang --track "origin/$Cabang" } ""
    Ok "folder kini mengikuti $Repo ($Cabang)"
}

if ((Diam { docker info }) -ne 0) { Gagal "Docker Desktop belum menyala" "buka Docker Desktop, tunggu sampai 'Engine running', lalu jalankan skrip ini lagi." }
Ok "Docker Desktop menyala"

# Perubahan lokal (kecuali folder installer yang memang belum masuk repo) akan menghalangi pull.
# Berkas baru yang tidak dilacak (??) tidak menghalangi pull; server/gateway.conf ditulis ulang otomatis oleh Pusat Kendali.
$kotor = git status --porcelain | Where-Object { $_ -notmatch '^\?\? ' -and $_ -notmatch 'server/gateway\.conf$' }
if ($kotor) {
    Write-Host ($kotor -join "`n")
    Gagal "ada perubahan lokal yang belum di-commit (daftar di atas)" "commit atau simpan dulu (git stash), supaya tidak hilang saat versi baru diambil."
}
Ok "tidak ada perubahan lokal yang tertunda"

# ---------- 2. Ambil versi baru ----------
Langkah "Ambil versi terbaru dari GitHub"
$sebelum = (git rev-parse --short HEAD)
Jalankan "git fetch gagal" { git fetch origin $Cabang } "cek internet / login GitHub (git credential), lalu ulangi."
Jalankan "pindah ke cabang $Cabang gagal" { git checkout $Cabang } "pastikan nama cabang benar: git branch -r"
Jalankan "git pull gagal" { git pull --ff-only origin $Cabang } "riwayat lokal berbeda dengan GitHub; hubungi pengembang (jangan dipaksa)."
$sesudah = (git rev-parse --short HEAD)
if ($sebelum -eq $sesudah) { Ok "sudah versi terbaru ($sesudah)" } else { Ok "diperbarui $sebelum -> $sesudah" }
git log -1 --format="    ..  %h %s (%cd)" --date=short
if (-not (Test-Path "$Akar\docs\31-catatan-versi.md")) {
    Write-Host "    !!  docs\31-catatan-versi.md tidak ada: perubahan terbaru belum di-merge ke $Cabang (PR masih terbuka?)." -ForegroundColor Yellow
}

# ---------- 3. Terapkan ----------
Langkah "Terapkan ke Docker (data & .env tidak diubah)"
Jalankan "menyalakan layanan gagal" { & $PS -NoProfile -ExecutionPolicy Bypass -File "$Akar\scripts\start.ps1" } "lihat scripts\logs.ps1, atau jalankan PASANG.cmd untuk perbaikan."
# Konfigurasi di config\ di-mount ke container: restart agar kode Python & halaman baru terbaca.
Jalankan "restart web & backgrounder gagal" { docker compose restart superset superset-worker superset-beat } "lihat scripts\logs.ps1"
Info "menunggu web sehat..."
$batas = (Get-Date).AddMinutes(4)
do {
    Start-Sleep -Seconds 5
    $status = docker compose ps superset --format "{{.Status}}"
} until ($status -match "\(healthy\)" -or (Get-Date) -gt $batas)
if ($status -notmatch "\(healthy\)") { Gagal "web belum sehat setelah 4 menit ($status)" "lihat scripts\logs.ps1 superset; kirim isi log ke pengembang." }
Ok "web sehat"
Jalankan "build-dashboards gagal" { & $PS -NoProfile -ExecutionPolicy Bypass -File "$Akar\scripts\build-dashboards.ps1" } "lihat pesan di atas; biasanya cukup diulang."
Ok "menu, izin & role diperbarui"

# ---------- 4. Uji ----------
if ($TanpaUji) {
    Langkah "Uji otomatis dilewati (-TanpaUji)"
} else {
    Langkah "Uji otomatis (scripts\uji.ps1)"
    Jalankan "ada uji yang GAGAL" { & $PS -NoProfile -ExecutionPolicy Bypass -File "$Akar\scripts\uji.ps1" } "baca baris GAGAL di atas; installer TIDAK diterbitkan sebelum semua lulus."
    Ok "semua uji LULUS"
}

# ---------- 5. Simpan skrip installer ke repo ----------
if ($KomitInstaller) {
    Langkah "Simpan installer\setup & .github\workflows ke repo"
    $ada = @("installer/setup", ".github/workflows") | Where-Object { Test-Path "$Akar\$_" }
    if (-not $ada) { Gagal "folder installer\setup maupun .github\workflows tidak ditemukan" "salin dulu kedua folder itu ke $Akar." }
    git add -- $ada                                   # installer/setup/Output diabaikan .gitignore
    $berkas = git diff --cached --name-only
    if (-not $berkas) {
        Ok "sudah tersimpan di repo, tidak ada yang baru"
    } else {
        Write-Host ($berkas | ForEach-Object { "    +   $_" } | Out-String)
        # Pengaman: jangan pernah mengunggah rahasia atau hasil build.
        $terlarang = $berkas | Where-Object { $_ -match '\.(env|pfx|p12|exe|bin|whl|zip)$|/Output/' }
        if ($terlarang) { git reset -q; Gagal "berkas terlarang ikut terpilih: $($terlarang -join ', ')" "hapus/pindahkan berkas itu dari folder installer, lalu ulangi." }
        Jalankan "commit gagal" { git commit -q -m "Installer: skrip pembangun (installer/setup) dan workflow GitHub Actions" } "atur identitas git: git config user.name / user.email"
        Jalankan "push gagal" { git push origin $Cabang } "cek login GitHub; bila main dilindungi, push ke cabang lain lalu buat PR."
        Ok "$($berkas.Count) berkas di-commit & di-push"
    }
}

# ---------- 6. Terbitkan installer ----------
if ($Terbitkan) {
    Langkah "Bangun & terbitkan installer (online, offline, HapusTotal)"
    $skrip = "$Akar\installer\setup\terbitkan.ps1"
    if (-not (Test-Path $skrip)) { Gagal "installer\setup\terbitkan.ps1 tidak ada" "salin folder installer\setup ke $Akar (lalu pakai -KomitInstaller)." }
    # Lisensi driver ini melarang dibagikan ulang: tidak boleh ikut masuk paket offline.
    $larangan = @(Get-ChildItem "$Akar\docker\wheels\hdbcli-*.whl" -ErrorAction SilentlyContinue) +
                @(Get-ChildItem "$Akar\docker\oracle\*.zip" -ErrorAction SilentlyContinue)
    if ($larangan) { Gagal "berkas berlisensi terbatas ada di folder build: $($larangan.Name -join ', ')" "pindahkan berkas itu keluar dari folder ALDx selama membangun installer." }
    Ok "tidak ada driver berlisensi terbatas di folder build"
    if (-not (Test-Path "$Akar\config\sps_studio\static\huruf\huruf.css")) { Gagal "berkas huruf dashboard tidak ada" "git pull ulang; folder config\sps_studio\static\huruf wajib ikut installer." }

    # Perkakas: Inno Setup 6 (pembuat installer) & GitHub CLI yang sudah login (unggah ke Releases). Dipasang bila belum.
    $winget = "--accept-source-agreements", "--accept-package-agreements", "-e", "--silent"
    $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
              "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        Info "memasang Inno Setup 6 (sekali saja)..."
        Jalankan "memasang Inno Setup gagal" { winget install --id JRSoftware.InnoSetup @winget } "pasang manual: https://jrsoftware.org/isdl.php, lalu ulangi."
    }
    Ok "Inno Setup 6 terpasang"
    $cariGh = { @((Get-Command gh -ErrorAction SilentlyContinue).Source, "$env:ProgramFiles\GitHub CLI\gh.exe",
                  "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe") |
                Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1 }
    $gh = & $cariGh
    if (-not $gh) {
        Info "memasang GitHub CLI (sekali saja)..."
        Jalankan "memasang GitHub CLI gagal" { winget install --id GitHub.cli @winget } "pasang manual: https://cli.github.com, lalu ulangi."
        $gh = & $cariGh
        if (-not $gh) { Gagal "GitHub CLI sudah dipasang tapi belum terbaca" "tutup PowerShell, buka lagi, lalu jalankan perintah ini lagi." }
    }
    if ((Diam { & $gh auth status }) -ne 0) {
        Info "GitHub CLI belum login: browser akan terbuka. Salin kode 8 huruf yang tampil di sini, tempel di browser, lalu Authorize."
        & $gh auth login --hostname github.com --git-protocol https --web          # interaktif: tidak dialirkan ke Out-Host
        if ((Diam { & $gh auth status }) -ne 0) { Gagal "login GitHub belum berhasil" "jalankan: & `"$gh`" auth login   lalu ulangi perintah ini." }
    }
    Ok "GitHub CLI login ($gh)"

    # terbitkan.ps1 menolak folder yang tidak bersih (berkas baru pun dihitung). Paket .bundle dipindah ke log.
    Get-ChildItem "$Akar\*.bundle" -ErrorAction SilentlyContinue | ForEach-Object {
        Move-Item $_.FullName "$Akar\installer\log\" -Force; Info "paket $($_.Name) dipindah ke installer\log"
    }
    $kotorRilis = git status --porcelain
    if ($kotorRilis) {
        Write-Host ($kotorRilis -join "`n")
        Gagal "folder belum bersih (daftar di atas); installer harus sama persis dengan versi di git" "commit & push berkas itu, atau pindahkan keluar folder ALDx, lalu ulangi."
    }
    Ok "folder bersih & sama dengan GitHub ($(git rev-parse --short HEAD))"
    $ps = (Get-Command pwsh -ErrorAction SilentlyContinue).Source; if (-not $ps) { $ps = $PS }
    Info "memakai $ps (pembangunan offline bisa 20-40 menit)"
    Jalankan "terbitkan.ps1 gagal" { & $ps -NoProfile -ExecutionPolicy Bypass -File $skrip } "baca pesan di atas (Inno Setup terpasang? login GitHub? semua perubahan sudah di-push?)."
    Ok "installer diterbitkan; cek tanggal berkas di GitHub > Releases"
}

Write-Host "`nSELESAI. Versi: $(git rev-parse --short HEAD). Buka aplikasi lalu tekan Ctrl + F5." -ForegroundColor Green
Write-Host "Langkah berikutnya bila belum: uji pasang -> hapus -> pasang ulang memakai installer baru (docs\31-catatan-versi.md)."
Write-Host "Catatan lengkap: $log"
Stop-Transcript | Out-Null
exit 0
