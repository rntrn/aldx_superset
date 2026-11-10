@echo off
setlocal EnableExtensions
rem =========================================================================
rem  PASANG.cmd - pemasang ALDx. Cukup KLIK DUA KALI berkas ini.
rem  Tidak perlu "Run as administrator" dan tidak perlu membuka CMD/PowerShell.
rem  (Dari CMD: ketik lengkap, mis. D:\ALDx\PASANG.cmd. Dari Terminal/PowerShell: .\PASANG.cmd)
rem
rem  Yang dilakukan berkas ini sebelum membuka wizard (installer\pasang.ps1):
rem    1. pindah ke folder tempat PASANG.cmd berada (dari mana pun dijalankan)
rem    2. menolak bila dijalankan dari DALAM berkas ZIP (harus diekstrak dulu)
rem    3. membuka blokir berkas hasil unduhan (tanda "dari internet" di Windows)
rem    4. memilih PowerShell yang diizinkan di komputer ini (Windows PowerShell, atau PowerShell 7)
rem    5. bila wizard berhenti karena galat, jendela tidak langsung tertutup
rem =========================================================================
cd /d "%~dp0"
title Pemasang ALDx

rem --- 2. Jangan dari dalam ZIP --------------------------------------------
set "DIR=%~dp0"
if /i not "%DIR:\AppData\Local\Temp\=%"=="%DIR%" (
  echo.
  echo  PASANG.cmd dibuka dari DALAM berkas ZIP.
  echo  Ekstrak dulu: klik kanan berkas ZIP ^> Extract All... ^> pilih mis. D:\ALDx
  echo  lalu klik dua kali PASANG.cmd di folder hasil ekstrak.
  echo.
  pause
  exit /b 1
)
if not exist "%~dp0installer\pasang.ps1" (
  echo.
  echo  Berkas installer\pasang.ps1 tidak ditemukan. Pastikan seluruh folder ALDx tersalin utuh.
  echo.
  pause
  exit /b 1
)

rem --- 3 & 4. Buka blokir & pilih PowerShell --------------------------------
set "PSH="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\cek-powershell.ps1" "%~dp0." >nul 2>&1
if not errorlevel 1 set "PSH=powershell.exe"
if not defined PSH (
  where pwsh.exe >nul 2>&1
  if not errorlevel 1 (
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\cek-powershell.ps1" "%~dp0." >nul 2>&1
    if not errorlevel 1 set "PSH=pwsh.exe"
  )
)
if not defined PSH (
  echo.
  echo  PowerShell tidak diizinkan menjalankan skrip di komputer ini ^(kebijakan kantor / GPO^).
  echo  Minta tim TI mengizinkan skrip PowerShell untuk folder ini, atau memasang PowerShell 7,
  echo  lalu klik dua kali PASANG.cmd lagi. Rincian: CARA-PASANG.md bagian "Masalah umum".
  echo.
  pause
  exit /b 1
)

rem --- 5. Wizard ------------------------------------------------------------
%PSH% -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0installer\pasang.ps1" %*
if errorlevel 1 (
  echo.
  echo  Pemasang berhenti karena galat. Catatan lengkap ada di folder installer\log\
  echo  Kirim berkas log terbaru itu ke tim TI / pengembang.
  echo.
  pause
)
endlocal
