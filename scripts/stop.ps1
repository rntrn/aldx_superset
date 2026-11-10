<#
.SYNOPSIS
    Mematikan container Superset. Data di MySQL tidak terhapus.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose down
Write-Host "Superset dimatikan." -ForegroundColor Yellow
