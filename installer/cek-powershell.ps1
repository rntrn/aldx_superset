# Dipanggil PASANG.cmd: memastikan PowerShell ini boleh menjalankan skrip, lalu membuka blokir
# berkas hasil unduhan (tanda "berasal dari internet") di folder ALDx. Kode keluar 0 = siap.
param([string]$Folder = (Split-Path $PSScriptRoot -Parent))
Get-ChildItem -LiteralPath $Folder -Recurse -File -ErrorAction SilentlyContinue |
    Unblock-File -ErrorAction SilentlyContinue
exit 0
