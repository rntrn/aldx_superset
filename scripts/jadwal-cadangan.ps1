<#
.SYNOPSIS
    Pasang jadwal otomatis di Windows Task Scheduler: cadangan harian + uji pulih mingguan.

.DESCRIPTION
    Membuat dua tugas terjadwal:
      "ALDx Cadangan Harian"      setiap hari pada -Jam      -> scripts\cadangkan.ps1 -Engine [-Salin <folder>]
      "ALDx Uji Pulih Mingguan"   setiap Minggu pada -JamUji -> scripts\cadangkan.ps1 -UjiPulih
    Hasilnya tercatat di backup\cadangan.log dan tampil di Pusat Kendali > Status (kartu Cadangan).

    Docker Desktop harus menyala pada jam tersebut (biarkan akun Windows server tetap masuk / jangan logout).
    Jalankan dari PowerShell "Run as administrator". Ulangi skrip ini untuk mengubah jam; -Hapus untuk melepas.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\jadwal-cadangan.ps1
    powershell -ExecutionPolicy Bypass -File scripts\jadwal-cadangan.ps1 -Jam 01:30 -Salin \\server-arsip\aldx
    powershell -ExecutionPolicy Bypass -File scripts\jadwal-cadangan.ps1 -Hapus
#>
param([string]$Jam = "02:00", [string]$JamUji = "04:00", [string]$Salin = "", [switch]$Hapus)

$ErrorActionPreference = "Stop"
$folder = Split-Path $PSScriptRoot -Parent
$nama = @("ALDx Cadangan Harian", "ALDx Uji Pulih Mingguan")

foreach ($n in $nama) {
    if (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $n -Confirm:$false }
}
if ($Hapus) { Write-Host "Jadwal cadangan dilepas." -ForegroundColor Green; exit 0 }

function Aksi([string]$argumen) {
    New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $folder `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$folder\scripts\cadangkan.ps1`" $argumen"
}
$argCadangan = "-Engine" + $(if ($Salin) { " -Salin `"$Salin`"" } else { "" })
# Akun yang menjalankan = akun ini (punya akses Docker Desktop); jalan walau layar terkunci, tanpa menyimpan password.
$pemilik = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest
$atur = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 6)

Register-ScheduledTask -TaskName $nama[0] -Action (Aksi $argCadangan) -Principal $pemilik -Settings $atur `
    -Trigger (New-ScheduledTaskTrigger -Daily -At $Jam) -Description "Cadangan metadata & ALDx Engine (backup\)" | Out-Null
Register-ScheduledTask -TaskName $nama[1] -Action (Aksi "-UjiPulih") -Principal $pemilik -Settings $atur `
    -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $JamUji) `
    -Description "Bukti cadangan terbaru bisa dipulihkan (tidak mengubah data)" | Out-Null

Write-Host "Terjadwal:" -ForegroundColor Green
Write-Host "  $($nama[0]) : setiap hari pukul $Jam$(if ($Salin) { ", salinan ke $Salin" })"
Write-Host "  $($nama[1]) : setiap Minggu pukul $JamUji"
Write-Host "Coba sekarang: Start-ScheduledTask -TaskName '$($nama[0])'  lalu lihat backup\cadangan.log"
