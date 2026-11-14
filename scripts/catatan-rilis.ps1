<#
.SYNOPSIS
    Menyusun catatan rilis untuk satu VERSI dari docs/31-catatan-versi.md (dipakai GitHub Actions: rilis tetap v<VERSI>).

.DESCRIPTION
    Mencari bagian berjudul "## <VERSI> ..." di docs/31-catatan-versi.md, lalu menulis catatan rilis:
    judul, commit, cara pasang, cara memeriksa sidik SHA-256, dan isi bagian versi itu.
    Gagal (exit 1) bila bagian versi belum ditulis: setiap rilis wajib punya catatan versi.

.EXAMPLE
    .\scripts\catatan-rilis.ps1 -Versi 2026.11.14 -Keluar catatan-rilis.md
#>
param(
    [Parameter(Mandatory)][string]$Versi,
    [string]$Keluar = "catatan-rilis.md",
    [string]$Commit = $env:GITHUB_SHA,
    [string]$Repo = $(if ($env:GITHUB_REPOSITORY) { $env:GITHUB_REPOSITORY } else { "rntrn/aldx_superset" })
)
$ErrorActionPreference = "Stop"
$akar = Split-Path $PSScriptRoot -Parent
$baris = Get-Content -Encoding utf8 (Join-Path $akar "docs/31-catatan-versi.md")

# Bagian versi: dari "## <Versi>" sampai judul "## " berikutnya atau garis "---".
$mulai = -1
for ($i = 0; $i -lt $baris.Count; $i++) {
    if ($baris[$i] -match "^## $([regex]::Escape($Versi))(\s|$)") { $mulai = $i; break }
}
if ($mulai -lt 0) {
    Write-Host "::error::Bagian '## $Versi' belum ada di docs/31-catatan-versi.md. Tulis catatan versi sebelum merilis."
    exit 1
}
$isi = @()
for ($i = $mulai + 1; $i -lt $baris.Count; $i++) {
    if ($baris[$i] -match "^(## |---\s*$)") { break }
    # Tautan relatif docs (12-studio-visual.md) diarahkan ke berkas di commit ini agar tetap bisa diklik dari halaman rilis.
    $isi += ($baris[$i] -replace '\]\((\d\d-[^)\s]+\.md[^)\s]*)\)', "](https://github.com/$Repo/blob/v$Versi/docs/`$1)")
}

$pendek = if ($Commit) { $Commit.Substring(0, [Math]::Min(7, $Commit.Length)) } else { "-" }
$teks = @(
    "# ALDx $Versi",
    "",
    "Tag ``v$Versi`` = commit ``$pendek``. Versi ini sama dengan yang tampil di kaki halaman login (``v$Versi``).",
    "",
    "| Berkas | Untuk |",
    "|---|---|",
    "| ``ALDx-Setup.exe`` | pasang / perbarui (online). Pasang di atas versi lama: data & pengaturan tetap |",
    "| ``ALDx-HapusTotal.exe`` | pembersih total (mencadangkan dulu) |",
    "| ``ALDx-SHA256.txt`` | sidik SHA-256 semua berkas versi ini, termasuk paket offline |",
    "",
    "Paket offline versi ini ada di rilis **offline** selama belum ada versi lebih baru (sidiknya tercantum di ``ALDx-SHA256.txt``).",
    "",
    "Memeriksa unduhan (PowerShell): ``(Get-FileHash .\ALDx-Setup.exe -Algorithm SHA256).Hash`` harus sama dengan baris di ``ALDx-SHA256.txt``.",
    "",
    "## Yang berubah",
    ""
) + $isi
Set-Content -Encoding utf8 -Path $Keluar -Value $teks
Write-Host "Catatan rilis v$Versi ditulis ke $Keluar ($($isi.Count) baris isi)."
