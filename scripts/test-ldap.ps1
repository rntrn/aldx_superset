<#
.SYNOPSIS
    Tes login LDAP dari dalam container, tanpa membuka Superset.
    Menanyakan username & password, lalu menampilkan BERHASIL/GAGAL
    beserta nama dan NIP yang terbaca dari Active Directory.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\test-ldap.ps1
#>

Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose run --rm -it superset python /app/pythonpath/sps_ldap.py
