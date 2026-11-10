<#
.SYNOPSIS
    Menghilangkan peringatan "tidak aman" browser untuk ALDx HTTPS (sertifikat buatan sendiri).

.DESCRIPTION
    Jalankan di KOMPUTER PENGGUNA (atau di server, untuk browser di server itu).
    Mengambil sertifikat dari alamat ALDx, lalu memasangnya ke "Trusted Root" pengguna Windows ini
    (tidak perlu hak Administrator). Setelah itu Edge/Chrome tidak memperingatkan lagi.
    Untuk banyak komputer sekaligus: sebarkan server\tls\aldx.crt lewat Group Policy kantor.

.PARAMETER Alamat
    Alamat ALDx, mis. https://srv-aldx:8088 (bawaan: https://localhost:<SUPERSET_PORT>).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\percayai-sertifikat.ps1 -Alamat https://srv-aldx:8088
#>
param([string]$Alamat = "")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $Alamat) {
    $port = if (Test-Path ".env") { (Select-String -Path ".env" -Pattern "^SUPERSET_PORT=(\d+)").Matches.Groups[1].Value } else { "" }
    $Alamat = "https://localhost:$(if ($port) { $port } else { '8088' })"
}
$u = [Uri]$Alamat
if ($u.Scheme -ne "https") { throw "Alamat harus diawali https:// (HTTPS belum aktif? lihat server\tls\README.md)." }

# Ambil sertifikat langsung dari server (tanpa memeriksa keabsahannya; justru itu yang akan dipercaya).
$tcp = New-Object System.Net.Sockets.TcpClient($u.Host, $(if ($u.Port -gt 0) { $u.Port } else { 443 }))
try {
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, { $true })
    $ssl.AuthenticateAsClient($u.Host)
    $sert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
} finally { $tcp.Close() }

Write-Host "Sertifikat : $($sert.Subject)"
Write-Host "Berlaku    : sampai $($sert.NotAfter.ToString('dd-MM-yyyy'))"
Write-Host "Sidik      : $($sert.Thumbprint)"
$toko = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$toko.Open("ReadWrite")
try { $toko.Add($sert) } finally { $toko.Close() }     # Windows menampilkan konfirmasi: pilih Yes
Write-Host "`nSelesai. Tutup & buka ulang browser, lalu buka $Alamat" -ForegroundColor Green
exit 0
