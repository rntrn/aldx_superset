<#
.SYNOPSIS
    Nama lama, tetap ada agar panduan lama masih berlaku. Isinya: scripts\pindah-metadata.ps1
    (memindahkan metadata XAMPP / MariaDB lama ke PostgreSQL).
#>
& "$PSScriptRoot\pindah-metadata.ps1" @args
exit $LASTEXITCODE
