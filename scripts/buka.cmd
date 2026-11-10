@echo off
rem Membuka ALDx di browser (pintasan "ALDx" di Desktop & menu Start). Logika di buka.ps1.
cd /d "%~dp0.."
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0buka.ps1"
