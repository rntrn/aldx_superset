<#
.SYNOPSIS
    Darurat: atur ulang password akun (mis. Superadmin) dan buka kuncinya, tanpa memasang ulang.

.DESCRIPTION
    Ditanya: email akun, password baru (diketik dua kali, tidak tampil di layar).
    Password dikirim lewat stdin ke config\sps_pengguna.py, TIDAK pernah ditulis ke berkas atau log.
    Nama & peran akun yang sudah ada tidak diubah (kecuali -Peran diisi); akun dinonaktifkan diaktifkan lagi.
    Akun yang belum ada hanya dibuat bila -Peran diisi. Kunci karena salah password berulang ikut dibuka.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\atur-password.ps1
    powershell -ExecutionPolicy Bypass -File scripts\atur-password.ps1 -Akun admin@perusahaan.co.id
#>
param([string]$Akun = "", [ValidateSet("", "Superadmin", "Admin", "Analis", "Pengguna")][string]$Peran = "")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Teks-Biasa([securestring]$s) {
    $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

if (-not $Akun) { $Akun = (Read-Host "Email akun (login)").Trim() }
if ($Akun -notmatch "^[^@\s]+@[^@\s]+\.[^@\s]+$") { Write-Host "Email tidak sah." -ForegroundColor Red; exit 1 }
$pw = Teks-Biasa (Read-Host "Password baru (min. 10 karakter)" -AsSecureString)
if ($pw.Length -lt 10) { Write-Host "Password minimal 10 karakter." -ForegroundColor Red; exit 1 }
if ($pw -ne (Teks-Biasa (Read-Host "Ulangi password" -AsSecureString))) { Write-Host "Ulangan tidak sama." -ForegroundColor Red; exit 1 }

$json = ConvertTo-Json -Compress -InputObject @([ordered]@{ username = $Akun; email = $Akun; nama = ""; password = $pw; peran = $Peran })
$pw = $null
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$ErrorActionPreference = "Continue"                       # log INFO Superset di stderr
$json | docker compose exec -T superset python /app/pythonpath/sps_pengguna.py 2>&1 |
    Where-Object { "$_" -match "^(OK|GAGAL)" } | ForEach-Object { Write-Host "$_" }
$hasil = $LASTEXITCODE; $json = $null
if ($hasil -ne 0) { Write-Host "Gagal. Pastikan ALDx menyala (Docker Desktop & container)." -ForegroundColor Red; exit $hasil }

docker compose exec -T superset python /app/pythonpath/sps_kunci.py $Akun 2>&1 | Where-Object { "$_" -notmatch "INFO|WARNING" } | Out-Host
Write-Host "`nSelesai. Login dengan $Akun dan password baru." -ForegroundColor Green
