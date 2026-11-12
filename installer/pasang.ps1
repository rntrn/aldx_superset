<#
.SYNOPSIS
    Wizard instalasi ALDx (Next - Next). Dibuka oleh PASANG.cmd.

.DESCRIPTION
    Mode RINGKAS (bawaan): Pemeriksaan -> Superadmin -> Pasang -> Selesai. Semua isian lain memakai nilai bawaan
    dan bisa diubah nanti di Pusat Kendali. Centang "Atur pengaturan lanjutan" di halaman Superadmin untuk
    menampilkan halaman bertanda (L).

    Halaman wizard (yang tidak relevan dilewati otomatis):
      1. Pemeriksaan      Docker menyala, CPU/RAM Docker, disk, port bebas, internet
      2. Superadmin       WAJIB: email, nama, password (akun lokal; tidak butuh LDAP)
      3. Identitas    (L) nama aplikasi & perusahaan, warna, logo, port, HTTPS (semua bisa diubah nanti)
      4. Pengguna     (L) opsional: akun lain (email + peran), password kosong = P@ssw0rd
      5. Login kantor (L) opsional: LDAP / Active Directory (boleh diisi nanti; uji koneksi tidak wajib)
      6. Asisten AI   (L) opsional: periksa model lokal (Ollama / LM Studio) atau key cloud
      7. Data lama        hanya bila ada metadata versi lama (XAMPP / MariaDB) -> PostgreSQL
      8. Pasang           menjalankan skrip di folder scripts\ berurutan + log
      9. Selesai          alamat web & tombol Buka

    Semua langkah memakai skrip yang sama dengan instalasi manual (scripts\*.ps1),
    jadi hasilnya identik. Log lengkap: installer\log\pasang-<waktu>.log
    Mengulang PASANG.cmd aman: nilai .env yang sudah ada dipakai sebagai isian awal, data tidak dihapus.
#>

$ErrorActionPreference = "Stop"
# PowerShell yang sama dengan yang menjalankan wizard (Windows PowerShell atau PowerShell 7, dipilih PASANG.cmd).
$script:PSH = (Get-Process -Id $PID).Path
$AKAR = Split-Path $PSScriptRoot -Parent
Set-Location $AKAR
. "$AKAR\scripts\_umum.ps1"
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# ============================================================================
# 1. Data isian (nilai awal dari .env bila ada, kalau tidak dari .env.example)
# ============================================================================
$envAda = Test-Path ".env"                # dicatat sebelum .env dibuat: data Docker tanpa .env = "data yatim"
if (-not $envAda) { Copy-Item ".env.example" ".env" }
function Nilai([string]$k, [string]$bawaan = "") {
    $v = Get-EnvValue $k
    if (-not $v -or $v -like "GANTI_DENGAN*") { return $bawaan }
    return $v
}
$sumberLama = Get-SumberMetaLama          # "xampp" | "mariadb" | $null (lihat scripts\_umum.ps1)
$perluPindah = [bool]$sumberLama
$sudahTerpasang = -not $perluPindah -and ((docker volume ls -q 2>$null) -contains "sps_metadb_pg")
# Data yatim: volume data Docker masih ada (folder dihapus / uninstall tanpa hapus data) tetapi .env-nya hilang.
# Password internal & kunci enkripsi lama ikut hilang -> pengguna memilih: mulai baru (dicadangkan dulu) / pakai data lama.
$dataYatim = $sudahTerpasang -and -not $envAda
if ($dataYatim) { $sudahTerpasang = $false }

$UTAMA = [System.Drawing.Color]::FromArgb(24, 24, 27)       # warna utama preset bawaan "Tinta & Sakura" (#18181B)
$AKSEN = [System.Drawing.Color]::FromArgb(225, 29, 116)     # aksen pink (#E11D74)
$REDUP = [System.Drawing.Color]::FromArgb(95, 107, 122)
$HIJAU = [System.Drawing.Color]::FromArgb(11, 122, 82)
$MERAH = [System.Drawing.Color]::FromArgb(180, 35, 24)
$KUNING = [System.Drawing.Color]::FromArgb(138, 109, 0)
$HURUF = New-Object System.Drawing.Font("Segoe UI", 9.5)
$TEBAL = New-Object System.Drawing.Font("Segoe UI Semibold", 10)
$JUDUL = New-Object System.Drawing.Font("Segoe UI Semibold", 14)
$KARAKTER_TERLARANG = '[\$"''`#\s\\]'      # merusak .env / docker compose
$POLA_EMAIL = '^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
$PW_BAWAAN = "P@ssw0rd"

# ============================================================================
# 2. Jendela & kerangka halaman
# ============================================================================
$form = New-Object System.Windows.Forms.Form
$form.AutoScaleDimensions = New-Object System.Drawing.SizeF(96, 96)
$form.AutoScaleMode = "Dpi"                 # skala tampilan Windows 125-150%: semua kontrol ikut membesar
$form.Text = "Pasang ALDx"
$form.ClientSize = New-Object System.Drawing.Size(760, 540)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"; $form.MaximizeBox = $false
$form.Font = $HURUF; $form.BackColor = [System.Drawing.Color]::White

$kepala = New-Object System.Windows.Forms.Panel
$kepala.Dock = "Top"; $kepala.Height = 70; $kepala.BackColor = $UTAMA
$lblJudul = New-Object System.Windows.Forms.Label
$lblJudul.ForeColor = [System.Drawing.Color]::White; $lblJudul.Font = $JUDUL
$lblJudul.Location = "24,12"; $lblJudul.AutoSize = $true
$lblSub = New-Object System.Windows.Forms.Label
$lblSub.ForeColor = [System.Drawing.Color]::FromArgb(212, 212, 216); $lblSub.Location = "26,42"; $lblSub.AutoSize = $true
$kepala.Controls.AddRange(@($lblJudul, $lblSub))
$garis = New-Object System.Windows.Forms.Panel
$garis.Dock = "Top"; $garis.Height = 4; $garis.BackColor = $AKSEN

$isi = New-Object System.Windows.Forms.Panel
$isi.Location = "24,90"; $isi.Size = "712,380"

$bawah = New-Object System.Windows.Forms.Panel
$bawah.Dock = "Bottom"; $bawah.Height = 58; $bawah.BackColor = [System.Drawing.Color]::FromArgb(244, 244, 245)
$btnKembali = New-Object System.Windows.Forms.Button
$btnKembali.Text = "< Kembali"; $btnKembali.Size = "100,32"; $btnKembali.Location = "430,13"
$btnLanjut = New-Object System.Windows.Forms.Button
$btnLanjut.Text = "Lanjut >"; $btnLanjut.Size = "110,32"; $btnLanjut.Location = "536,13"
$btnLanjut.BackColor = $UTAMA; $btnLanjut.ForeColor = [System.Drawing.Color]::White; $btnLanjut.FlatStyle = "Flat"
$btnBatal = New-Object System.Windows.Forms.Button
$btnBatal.Text = "Batal"; $btnBatal.Size = "90,32"; $btnBatal.Location = "652,13"
$lblLangkah = New-Object System.Windows.Forms.Label
$lblLangkah.Location = "24,20"; $lblLangkah.AutoSize = $true; $lblLangkah.ForeColor = $REDUP
$bawah.Controls.AddRange(@($lblLangkah, $btnKembali, $btnLanjut, $btnBatal))
$form.Controls.AddRange(@($isi, $garis, $kepala, $bawah))

# --- Pembuat kontrol kecil ----------------------------------------------------
function Teks([string]$t, [int]$x, [int]$y, [int]$lebar = 680, $warna = $null, $huruf = $null) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $t; $l.Location = "$x,$y"; $l.MaximumSize = "$lebar,0"; $l.AutoSize = $true
    if ($warna) { $l.ForeColor = $warna }
    if ($huruf) { $l.Font = $huruf }
    return $l
}
function Bantuan([string]$judul, [string]$teks, [string]$url = "") {
    <# Jendela "cara mengisi". Bila ada $url: tombol Ya membuka halaman itu di browser. #>
    if ($url) {
        $j = [System.Windows.Forms.MessageBox]::Show("$teks`r`n`r`nBuka halamannya sekarang?`r`n$url", "Cara mengisi: $judul", "YesNo", "Information")
        if ($j -eq "Yes") { Start-Process $url }
    } else { [void][System.Windows.Forms.MessageBox]::Show($teks, "Cara mengisi: $judul", "OK", "Information") }
}
function Tombol-Bantuan([int]$x, [int]$y, [string]$judul, [string]$teks, [string]$url = "") {
    <# Tombol "?" kecil di samping isian; teks bantuan disimpan di Tag (dibaca saat diklik). #>
    $b = New-Object System.Windows.Forms.Button
    $b.Text = "?"; $b.Location = "$x,$($y - 1)"; $b.Size = "26,25"; $b.TabStop = $false
    $b.Tag = @{ judul = $judul; teks = $teks; url = $url }
    $b.Add_Click({ param($s) Bantuan $s.Tag.judul $s.Tag.teks $s.Tag.url })
    return $b
}
function Isian([string]$label, [int]$y, [string]$nilai = "", [switch]$Rahasia, [int]$lebar = 380, [string]$Bantu = "", [string]$Url = "") {
    <# Label + kotak isian (+ tombol "?" bila -Bantu diisi). Kembali @(label, kotak[, tombol]); kotak selalu [1]. #>
    $l = Teks $label 0 ($y + 4) 220
    $t = New-Object System.Windows.Forms.TextBox
    $t.Location = "230,$y"; $t.Width = $lebar; $t.Text = $nilai
    if ($Rahasia) { $t.UseSystemPasswordChar = $true }
    if ($Bantu) { return @($l, $t, (Tombol-Bantuan (236 + $lebar) $y $label $Bantu $Url)) }
    return @($l, $t)
}

# --- Pekerjaan di latar (jendela tetap responsif) ------------------------------
# Satu pekerjaan sekaligus: Start-Job (proses terpisah) + Timer yang memeriksa hasilnya.
$script:tugasLatar = $null
$pewaktu = New-Object System.Windows.Forms.Timer; $pewaktu.Interval = 250
$pewaktu.Add_Tick({
    $t = $script:tugasLatar
    if (-not $t -or $t.Job.State -eq "Running") { return }
    $pewaktu.Stop(); $script:tugasLatar = $null
    $h = @(Receive-Job $t.Job -ErrorAction SilentlyContinue); Remove-Job $t.Job -Force
    & $t.Selesai $h
})
function Mulai-Latar([scriptblock]$kerja, [object[]]$argumen, [scriptblock]$selesai) {
    if ($script:tugasLatar) { return $false }
    $script:tugasLatar = @{ Job = Start-Job -ScriptBlock $kerja -ArgumentList $argumen; Selesai = $selesai }
    $pewaktu.Start(); return $true
}

# ============================================================================
# 3. Halaman
# ============================================================================
$HALAMAN = @()

# --- 3.1 Pemeriksaan ----------------------------------------------------------
$pPeriksa = New-Object System.Windows.Forms.Panel; $pPeriksa.Dock = "Fill"
$daftarCek = New-Object System.Windows.Forms.ListView
$daftarCek.View = "Details"; $daftarCek.Location = "0,40"; $daftarCek.Size = "712,280"
$daftarCek.FullRowSelect = $true; $daftarCek.HeaderStyle = "Nonclickable"
[void]$daftarCek.Columns.Add("Pemeriksaan", 220); [void]$daftarCek.Columns.Add("Hasil", 80); [void]$daftarCek.Columns.Add("Keterangan", 390)
$btnCekUlang = New-Object System.Windows.Forms.Button
$btnCekUlang.Text = "Periksa ulang"; $btnCekUlang.Location = "0,330"; $btnCekUlang.Size = "120,30"
$pPeriksa.Controls.AddRange(@((Teks "Installer memeriksa komputer ini. Semua baris harus OK atau Peringatan untuk melanjutkan." 0 6), $daftarCek, $btnCekUlang))
$script:cekLulus = $false

function Tambah-Cek([string]$nama, [string]$hasil, [string]$ket) {
    $i = New-Object System.Windows.Forms.ListViewItem($nama)
    [void]$i.SubItems.Add($hasil); [void]$i.SubItems.Add($ket)
    $i.ForeColor = switch ($hasil) { "OK" { $HIJAU } "GAGAL" { $MERAH } default { $KUNING } }
    [void]$daftarCek.Items.Add($i)
    [System.Windows.Forms.Application]::DoEvents()
}

function Port-Bebas([int]$port) {
    <# Port dipakai program lain (bukan Docker milik instalasi ini)? #>
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) { return "" }
    $nama = (Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue).ProcessName
    if ($nama -match "docker|wslrelay|vpnkit|com\.docker") { return "" }
    return $nama
}

function Jalankan-Pemeriksaan {
    $daftarCek.Items.Clear(); $gagal = $false
    $form.Cursor = "WaitCursor"
    # Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Tambah-Cek "Docker Desktop terpasang" "GAGAL" "Minta TI memasang Docker Desktop (CARA-PASANG.md bagian A), lalu Periksa ulang."; $gagal = $true
    } else {
        $versi = docker info --format "{{.ServerVersion}}" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $versi) {
            Tambah-Cek "Docker Desktop menyala" "GAGAL" "Buka Docker Desktop, tunggu ikon paus diam, lalu Periksa ulang. Tetap gagal: akun ini belum di grup docker-users (minta TI)."; $gagal = $true
        } else {
            Tambah-Cek "Docker Desktop menyala" "OK" "Docker $versi"
            docker compose version 2>$null | Out-Null
            if ($LASTEXITCODE -ne 0) { Tambah-Cek "Docker Compose v2" "GAGAL" "Perbarui Docker Desktop."; $gagal = $true }
            $cpu = [int](docker info --format "{{.NCPU}}" 2>$null)
            $ramGb = [math]::Round([double](docker info --format "{{.MemTotal}}" 2>$null) / 1GB, 1)
            if ($cpu -lt 2) { Tambah-Cek "CPU untuk Docker" "GAGAL" "$cpu inti. Minimal 2 (disarankan 4+)."; $gagal = $true }
            elseif ($cpu -lt 4) { Tambah-Cek "CPU untuk Docker" "Peringatan" "$cpu inti. Cukup untuk uji coba; produksi disarankan 4+." }
            else { Tambah-Cek "CPU untuk Docker" "OK" "$cpu inti" }
            if ($ramGb -lt 4) { Tambah-Cek "RAM untuk Docker" "GAGAL" "$ramGb GB. Minimal 4 GB (Docker Desktop > Settings > Resources / .wslconfig)."; $gagal = $true }
            elseif ($ramGb -lt 8) { Tambah-Cek "RAM untuk Docker" "Peringatan" "$ramGb GB. Produksi disarankan 8 GB+ (docs\15-sizing.md)." }
            else { Tambah-Cek "RAM untuk Docker" "OK" "$ramGb GB" }
        }
    }
    # Disk
    $drive = (Get-Item $AKAR).PSDrive
    $bebasGb = [math]::Round($drive.Free / 1GB)
    if ($bebasGb -lt 15) { Tambah-Cek "Ruang disk $($drive.Name):" "GAGAL" "$bebasGb GB bebas. Minimal 15 GB."; $gagal = $true }
    elseif ($bebasGb -lt 40) { Tambah-Cek "Ruang disk $($drive.Name):" "Peringatan" "$bebasGb GB bebas. Disarankan 40 GB+ (ekstrak & cadangan)." }
    else { Tambah-Cek "Ruang disk $($drive.Name):" "OK" "$bebasGb GB bebas" }
    # Port (dibaca dari .env, sama dengan docker-compose.yml)
    # Port web dipakai program lain pada pemasangan baru: pilih otomatis port bebas berikutnya (8089, 8090, ...).
    $portWeb = [int]$aPort[1].Text
    if (-not $sudahTerpasang -and (Port-Bebas $portWeb)) {
        $pengganti = @(($portWeb + 1)..($portWeb + 20) | Where-Object { -not (Port-Bebas $_) })[0]
        if ($pengganti) {
            Tambah-Cek "Port $portWeb (Web)" "Peringatan" "Dipakai program '$(Port-Bebas $portWeb)'. Otomatis memakai port $pengganti."
            $aPort[1].Text = "$pengganti"; $portWeb = 0
        }
    }
    $daftarPort = @(@([int](Nilai "METADB_PORT_HOST" "5433"), "Katalog"), @([int](Nilai "ENGINE_PORT_HOST" "8124"), "Engine"), @(6379, "Cache"))
    if ($portWeb) { $daftarPort = @(, @($portWeb, "Web")) + $daftarPort }
    foreach ($p in $daftarPort) {
        $pemakai = Port-Bebas $p[0]
        if ($pemakai) { Tambah-Cek "Port $($p[0]) ($($p[1]))" "GAGAL" "Dipakai program '$pemakai'. Tutup program itu, lalu Periksa ulang."; $gagal = $true }
        else { Tambah-Cek "Port $($p[0]) ($($p[1]))" "OK" "bebas" }
    }
    # Internet: pertama kali, image diunduh dari Docker Hub (15-40 menit). Instalasi ulang tidak butuh internet.
    if (Test-Path "$AKAR\offline\aldx-images.tar.gz") {
        Tambah-Cek "Internet (unduh image)" "OK" "paket offline: semua image sudah ada, internet tidak diperlukan"
    } elseif (-not $sudahTerpasang) {
        $online = Test-NetConnection "registry-1.docker.io" -Port 443 -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($online) { Tambah-Cek "Internet (unduh image)" "OK" "Docker Hub terjangkau" }
        else { Tambah-Cek "Internet (unduh image)" "Peringatan" "Docker Hub tidak terjangkau. Pasang pertama butuh internet/proxy kantor (docs\18-installer.md)." }
    }
    # Folder & instalasi lama
    if ($AKAR -match "\s") { Tambah-Cek "Lokasi folder" "Peringatan" "Path mengandung spasi: $AKAR. Disarankan D:\superset." }
    else { Tambah-Cek "Lokasi folder" "OK" $AKAR }
    if ($perluPindah) { Tambah-Cek "Instalasi lama ($sumberLama)" "Peringatan" "Ditemukan. Data akan dipindah ke PostgreSQL (halaman Data lama)." }
    elseif ($sudahTerpasang) { Tambah-Cek "Instalasi sebelumnya" "OK" "Ditemukan. Data dipertahankan; installer hanya memperbarui." }
    elseif ($dataYatim) { Tambah-Cek "Data pemasangan sebelumnya" "Peringatan" "Ditemukan di Docker tanpa berkas pengaturan. Pilih di halaman Data sebelumnya." }
    $form.Cursor = "Default"
    $script:cekLulus = -not $gagal
    $btnLanjut.Enabled = $script:cekLulus
}
$btnCekUlang.Add_Click({ Jalankan-Pemeriksaan })
$HALAMAN += @{ Judul = "Pemeriksaan komputer"; Sub = "Docker, CPU, RAM, disk, port, dan internet"; Panel = $pPeriksa;
               Masuk = { Jalankan-Pemeriksaan }; Sah = { if (-not $script:cekLulus) { "Perbaiki baris GAGAL lalu klik Periksa ulang." } } }

# --- 3.2 Identitas, alamat & HTTPS ------------------------------------------------------
# Nilai awal saja: setelah terpasang, identitas diubah di Pusat Kendali > Identitas & Tema.
$PRESET = [ordered]@{ "netral" = @("Tinta & Sakura (bawaan)", "#18181B", "#E11D74"); "neon" = @("Neon malam (pink + cyan)", "#11161D", "#FF2E8A"); "navy" = @("Navy & biru (klasik)", "#1E2A44", "#4F7CF7")
    "hijau" = @("Hijau segar", "#0F6E56", "#F4B400")
    "marun" = @("Merah marun", "#7A1F2B", "#E0A100"); "ungu" = @("Ungu modern", "#4B2E83", "#19B5A5")
    "grafit" = @("Grafit & toska", "#263238", "#26A69A") }
$pIdn = New-Object System.Windows.Forms.Panel; $pIdn.Dock = "Fill"
$iNama = Isian "Nama aplikasi" 40 (Nilai "SPS_NAMA_APLIKASI" "ALDx") -Bantu "Nama yang tampil di judul browser, halaman login, dan menu. Contoh: Dashboard Kinerja. Bisa diganti nanti di Pusat Kendali > Identitas & Tema."
$iPerusahaan = Isian "Nama perusahaan / instansi" 72 (Nilai "SPS_NAMA_PERUSAHAAN" "Nama Perusahaan") -Bantu "Nama kantor Anda, tampil di halaman login & kaki halaman. Contoh: PT Maju Jaya."
$iPreset = New-Object System.Windows.Forms.ComboBox
$iPreset.DropDownStyle = "DropDownList"; $iPreset.Location = "230,104"; $iPreset.Width = 260
foreach ($k in $PRESET.Keys) { [void]$iPreset.Items.Add($PRESET[$k][0]) }
$presetAwal = Nilai "SPS_PRESET" "netral"
$iPreset.SelectedIndex = [Math]::Max(0, @($PRESET.Keys).IndexOf($presetAwal))
$iWarna1 = New-Object System.Windows.Forms.Panel; $iWarna1.Size = "28,22"; $iWarna1.Location = "500,105"
$iWarna2 = New-Object System.Windows.Forms.Panel; $iWarna2.Size = "28,22"; $iWarna2.Location = "532,105"
function Warna-Preset {
    $w = $PRESET[@($PRESET.Keys)[$iPreset.SelectedIndex]]
    $iWarna1.BackColor = [System.Drawing.ColorTranslator]::FromHtml($w[1]); $iWarna2.BackColor = [System.Drawing.ColorTranslator]::FromHtml($w[2])
}
$iPreset.Add_SelectedIndexChanged({ Warna-Preset; $script:idnDiubah = $true }); Warna-Preset
$iLogo = Isian "Logo (opsional)" 138 "" -lebar 300; $iLogo[1].ReadOnly = $true
$btnLogo = New-Object System.Windows.Forms.Button; $btnLogo.Text = "Pilih..."; $btnLogo.Location = "536,136"; $btnLogo.Size = "74,26"
$btnLogo.Add_Click({
    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Filter = "Gambar (*.png;*.svg;*.jpg)|*.png;*.svg;*.jpg;*.jpeg"
    if ($d.ShowDialog() -eq "OK") { $iLogo[1].Text = $d.FileName; $script:idnDiubah = $true }
})
$script:idnDiubah = -not $sudahTerpasang
foreach ($t in @($iNama[1], $iPerusahaan[1])) { $t.Add_TextChanged({ $script:idnDiubah = $true }) }
$aPort = Isian "Port web" 205 (Nilai "SUPERSET_PORT" "8088") -lebar 80 -Bantu "Nomor pintu alamat web: http://localhost:8088. Biarkan 8088. Ganti (mis. 8090) hanya bila Pemeriksaan menyebut port dipakai program lain."
$cHttps = New-Object System.Windows.Forms.CheckBox
$cHttps.Text = "Pakai HTTPS (koneksi terenkripsi; sertifikat dibuat otomatis)"; $cHttps.Location = "230,240"; $cHttps.AutoSize = $true
$cHttps.Checked = (Nilai "SPS_HTTPS") -eq "1"
$aNamaServer = Isian "Nama/IP server (opsional)" 268 (Nilai "SPS_HTTPS_NAMA") -lebar 300 -Bantu "Hanya untuk HTTPS. Nama komputer ini di jaringan (lihat Settings > System > About > Device name) dan/atau IP-nya (cmd: ipconfig). Pisah koma, mis. PC-DATA01,10.1.2.3. Kosong = otomatis."
$pIdn.Controls.AddRange(@((Teks "Nama, warna & logo untuk halaman login dan seluruh aplikasi. Semua bisa diganti kapan saja di Pusat Kendali > Identitas & Tema (tanpa restart)." 0 6)) +
    $iNama + $iPerusahaan + @((Teks "Tema warna" 0 108 220), $iPreset, $iWarna1, $iWarna2) + $iLogo + @($btnLogo,
    (Teks "Kosong = logo dibuat otomatis dari nama & warna. PNG/SVG, sebaiknya latar transparan." 230 168 440 $REDUP)) + $aPort +
    @($cHttps) + $aNamaServer + @((Teks "HTTPS: browser memperingatkan sekali karena sertifikat dibuat sendiri; hilangkan dengan scripts\percayai-sertifikat.ps1 di komputer pengguna. Nama/IP server: alamat yang diketik pengguna, pisah koma." 230 298 470 $REDUP)))
$HALAMAN += @{ Judul = "Identitas & alamat"; Sub = "Nama aplikasi, perusahaan, warna, logo, port, HTTPS"; Panel = $pIdn; Masuk = {}; Sah = {
    if (-not $iNama[1].Text.Trim()) { return "Nama aplikasi wajib diisi." }
    if ($iNama[1].Text.Length -gt 40) { return "Nama aplikasi maksimal 40 karakter." }
    if (-not $iPerusahaan[1].Text.Trim()) { return "Nama perusahaan wajib diisi." }
    if ($iLogo[1].Text) {
        if (-not (Test-Path -LiteralPath $iLogo[1].Text)) { return "Berkas logo tidak ditemukan lagi. Pilih ulang, atau kosongkan." }
        if ((Get-Item -LiteralPath $iLogo[1].Text).Length -gt 1MB) { return "Ukuran logo maksimal 1 MB." }
    }
    $port = 0
    if (-not [int]::TryParse($aPort[1].Text.Trim(), [ref]$port) -or $port -lt 1 -or $port -gt 65535) { return "Port web harus angka 1-65535, mis. 8088." }
    if ($aNamaServer[1].Text -match '[^A-Za-z0-9.,:\-\s]') { return "Nama/IP server hanya huruf, angka, titik, minus; pisah koma." }
} }

# --- 3.3 Superadmin (akun lokal; selalu ada, tidak bergantung LDAP) ------------------------
$pSuper = New-Object System.Windows.Forms.Panel; $pSuper.Dock = "Fill"
$emailLama = Nilai "ADMIN_USERNAME"
$sMail = Isian "Email Superadmin (dipakai login)" 50 $(if ($emailLama -match "@") { $emailLama } else { "" }) -lebar 300 -Bantu "Email Anda (tidak perlu email sungguhan yang aktif). Inilah yang diketik di kolom login, BUKAN kata admin. Contoh: budi@kantor.go.id"
$sNama = Isian "Nama lengkap" 85 "" -lebar 300 -Bantu "Nama yang tampil di aplikasi, mis. Budi Santoso."
$sPw = Isian "Password" 120 "" -Rahasia -lebar 200 -Bantu 'Minimal 10 karakter, tanpa spasi dan tanpa tanda $ ` " '' # \. Contoh pola: Kantor2026Aman. Catat di tempat aman. Lupa? menu Start > ALDx > Atur ulang password.'
$sPw2 = Isian "Ulangi password" 155 "" -Rahasia -lebar 200
$cLihatPw = New-Object System.Windows.Forms.CheckBox
$cLihatPw.Text = "Tampilkan password"; $cLihatPw.Location = "470,122"; $cLihatPw.AutoSize = $true
$cLihatPw.Add_CheckedChanged({ $sPw[1].UseSystemPasswordChar = -not $cLihatPw.Checked; $sPw2[1].UseSystemPasswordChar = -not $cLihatPw.Checked })
$ketSuper = if ($sudahTerpasang) { "Instalasi sudah ada: kosongkan email & password bila Superadmin tidak ingin diubah." } else { "Password minimal 10 karakter, tanpa spasi dan tanpa tanda `$ `" ' `` # \" }
# Mode ringkas: tanpa centang ini, halaman (L) dilewati dan nilai bawaan dipakai.
$cLanjutan = New-Object System.Windows.Forms.CheckBox
$cLanjutan.Text = "Atur pengaturan lanjutan (nama & logo, port, HTTPS, pengguna lain, login kantor, Asisten AI)"
$cLanjutan.Location = "0,262"; $cLanjutan.AutoSize = $true
$cLanjutan.Add_CheckedChanged({ Tampilkan $script:ke })        # perbarui "Langkah x dari y"
$pSuper.Controls.AddRange(@((Teks "Superadmin = tingkat tertinggi: semua menu + pengaturan vital. Login dengan email & password ini, juga bila jaringan kantor/LDAP sedang tidak tersedia." 0 6)) +
    $sMail + $sNama + $sPw + $sPw2 + @($cLihatPw, (Teks $ketSuper 230 192 470 $REDUP), $cLanjutan,
    (Teks "Tidak dicentang = langsung Pasang dengan pengaturan bawaan. Semuanya bisa diubah nanti di Pusat Kendali." 18 288 680 $REDUP)))
$HALAMAN += @{ Judul = "Akun Superadmin"; Sub = "Email & password untuk masuk pertama kali"; Panel = $pSuper; Masuk = { [void]$sMail[1].Focus() }; Sah = {
    $mail = $sMail[1].Text.Trim(); $pw = $sPw[1].Text
    if ($sudahTerpasang -and -not $mail -and -not $pw) { return $null }
    if ($mail -notmatch $POLA_EMAIL) { return "Isi email Superadmin yang sah, mis. nama@kantor.go.id." }
    if (-not $sNama[1].Text.Trim()) { return "Isi nama lengkap Superadmin." }
    if ($sudahTerpasang -and -not $pw -and $mail -eq $emailLama) { return $null }
    if ($pw.Length -lt 10) { return "Password Superadmin minimal 10 karakter." }
    if ($pw -match $KARAKTER_TERLARANG) { return "Password tidak boleh berisi spasi atau tanda `$ `" ' `` # \" }
    if ($pw -ne $sPw2[1].Text) { return "Ulangan password tidak sama." }
} }

# --- 3.4 Pengguna lain ------------------------------------------------------------------
# Password dikosongkan = password bawaan P@ssw0rd (minta segera diganti).
# Akun dibuat SETELAH Superset menyala (config\sps_pengguna.py, dikirim lewat stdin: tidak pernah ditulis ke berkas).
$pPengguna = New-Object System.Windows.Forms.Panel; $pPengguna.Dock = "Fill"
$tabelPengguna = New-Object System.Windows.Forms.DataGridView
$tabelPengguna.Location = "0,28"; $tabelPengguna.Size = "712,230"
$tabelPengguna.AllowUserToAddRows = $true; $tabelPengguna.RowHeadersWidth = 28
$tabelPengguna.AutoSizeColumnsMode = "Fill"; $tabelPengguna.BackgroundColor = [System.Drawing.Color]::White
foreach ($k in @(@("email", "Email (login)", 30), @("nama", "Nama lengkap", 26), @("password", "Password", 16), @("ulang", "Ulangi password", 16))) {
    $c = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
    $c.Name = $k[0]; $c.HeaderText = $k[1]; $c.FillWeight = $k[2]; [void]$tabelPengguna.Columns.Add($c)
}
$cPeran = New-Object System.Windows.Forms.DataGridViewComboBoxColumn
$cPeran.Name = "peran"; $cPeran.HeaderText = "Peran"; $cPeran.FillWeight = 14
[void]$cPeran.Items.AddRange(@("Pengguna", "Analis", "Admin", "Superadmin")); [void]$tabelPengguna.Columns.Add($cPeran)
$tabelPengguna.Add_DefaultValuesNeeded({ param($s, $e) $e.Row.Cells["peran"].Value = "Pengguna" })
# Password disamarkan: saat tampil diganti titik, saat diketik memakai karakter rahasia.
$KOLOM_RAHASIA = @(2, 3)
$tabelPengguna.Add_CellFormatting({ param($s, $e)
    if ($KOLOM_RAHASIA -contains $e.ColumnIndex -and $e.Value) { $e.Value = "".PadLeft(([string]$e.Value).Length, [char]0x25CF); $e.FormattingApplied = $true } })
$tabelPengguna.Add_EditingControlShowing({ param($s, $e)
    if ($e.Control -is [System.Windows.Forms.TextBox]) { $e.Control.UseSystemPasswordChar = ($KOLOM_RAHASIA -contains $tabelPengguna.CurrentCell.ColumnIndex) } })
$pPengguna.Controls.AddRange(@((Teks "Tambahkan pengguna lain (boleh kosong; bisa ditambah nanti di Kelola > Pengguna):" 0 0 712 $REDUP), $tabelPengguna,
    (Teks ("Password & ulangi dikosongkan = password bawaan $PW_BAWAAN (minta pengguna segera menggantinya di Info pengguna).`r`n" +
        "Peran:  Pengguna = lihat dashboard, Studio Visual, Asisten AI.   Analis = + SQL Lab & Kueri Visual.   Admin = semua menu & Pusat Kendali.   Superadmin = Admin + pengaturan vital.") 0 266 712 $REDUP)))

function Daftar-Pengguna {
    <# Baris tabel pengguna yang terisi -> daftar hashtable (baris kosong dilewati). Login = email. #>
    $daftar = @()
    foreach ($b in $tabelPengguna.Rows) {
        if ($b.IsNewRow) { continue }
        $m = ([string]$b.Cells["email"].Value).Trim()
        if (-not $m) { continue }
        $pw = [string]$b.Cells["password"].Value
        $daftar += [ordered]@{ username = $m; email = $m; nama = ([string]$b.Cells["nama"].Value).Trim()
                               password = $(if ($pw) { $pw } else { $PW_BAWAAN }); ulang = [string]$b.Cells["ulang"].Value
                               bawaan = -not $pw; peran = [string]$b.Cells["peran"].Value }
    }
    return ,$daftar
}
$HALAMAN += @{ Judul = "Pengguna lain"; Sub = "Opsional - akun dengan email & peran"; Panel = $pPengguna; Masuk = {}; Sah = {
    $tabelPengguna.EndEdit() | Out-Null
    $ada = @{}
    foreach ($a in (Daftar-Pengguna)) {
        if ($a.email -notmatch $POLA_EMAIL) { return "Email '$($a.email)' tidak sah." }
        if ($a.email -eq $sMail[1].Text.Trim()) { return "Email '$($a.email)' sudah dipakai Superadmin." }
        if ($ada.ContainsKey($a.email)) { return "Email '$($a.email)' tertulis dua kali." }
        $ada[$a.email] = 1
        if (-not $a.nama) { return "Isi nama lengkap untuk '$($a.email)'." }
        if (-not $a.bawaan) {
            if ($a.password.Length -lt 8) { return "Password '$($a.email)' minimal 8 karakter (atau kosongkan untuk $PW_BAWAAN)." }
            if ($a.password -ne $a.ulang) { return "Ulangan password '$($a.email)' tidak sama." }
        }
        if (-not $a.peran) { return "Pilih peran untuk '$($a.email)'." }
    }
} }

# --- 3.5 Login kantor (LDAP / Active Directory) - OPSIONAL --------------------------------
# Tidak wajib & tidak harus terhubung saat instalasi. Uji koneksi hanya membantu, bukan syarat.
# Pengguna login dengan username & password jaringan kantor; akun dibuat otomatis saat login pertama.
$pLdap = New-Object System.Windows.Forms.Panel; $pLdap.Dock = "Fill"
$cLdap = New-Object System.Windows.Forms.CheckBox
$cLdap.Text = "Aktifkan login dengan akun jaringan kantor (LDAP / Active Directory)"; $cLdap.Location = "0,30"; $cLdap.AutoSize = $true
$cLdap.Checked = [bool](Nilai "LDAP_SERVERS")
$gLdap = New-Object System.Windows.Forms.Panel; $gLdap.Location = "0,58"; $gLdap.Size = "712,320"
$lServer = Isian "Server LDAP (pisah koma)" 6 (Nilai "LDAP_SERVERS") -lebar 440 -Bantu "Alamat server Active Directory kantor, dari tim TI/jaringan. Format ldaps://IP-atau-nama (port 636, terenkripsi). Dua server cadangan dipisah koma."
$lDomain = Isian "Domain" 38 (Nilai "LDAP_DOMAIN") -lebar 160 -Bantu "Nama domain Windows kantor (bagian sebelum \ saat login Windows, mis. KANTOR\budi). Cek: buka cmd, ketik  echo %USERDOMAIN%"
$lBase = Isian "Search base" 70 (Nilai "LDAP_SEARCH_BASE") -lebar 440 -Bantu "Lokasi daftar pegawai di Active Directory, dari tim TI. Contoh: OU=Karyawan,DC=kantor,DC=local"
$lSuper = Isian "Username yang jadi Superadmin" 102 (Nilai "SPS_SUPERADMIN_USERS") -lebar 300 -Bantu "Username jaringan yang otomatis menjadi Superadmin saat login LDAP. Pisah koma. Boleh kosong."
$lAdmin = Isian "Username yang jadi Admin" 134 (Nilai "LDAP_ADMIN_USERS") -lebar 300 -Bantu "Username jaringan yang otomatis menjadi Admin. Pisah koma. Boleh kosong."
$lAkunUji = Isian "Uji: username" 178 "" -lebar 140
$lPwUji = Isian "Uji: password (tidak disimpan)" 210 "" -Rahasia -lebar 140
$btnUjiLdap = New-Object System.Windows.Forms.Button
$btnUjiLdap.Text = "Uji (opsional)"; $btnUjiLdap.Location = "380,190"; $btnUjiLdap.Size = "120,30"
$lblUjiLdap = Teks "" 510 196 200
$lblPeringatanLdap = Teks "" 230 246 470 $MERAH
$gLdap.Controls.AddRange($lServer + $lDomain + $lBase + $lSuper + $lAdmin + $lAkunUji + $lPwUji + @($btnUjiLdap, $lblUjiLdap, $lblPeringatanLdap,
    (Teks "Pisah koma untuk beberapa username. Boleh dikosongkan & diisi nanti (.env, docs\05-login-ldap.md). Akun lokal (email) tetap bisa login walau LDAP mati." 230 270 470 $REDUP)))
function Atur-Ldap {
    $gLdap.Enabled = $cLdap.Checked
    $lblPeringatanLdap.Text = if ($cLdap.Checked -and $lServer[1].Text -match "(^|,)\s*ldap://") {
        "ldap:// mengirim password tanpa enkripsi. Bila server mendukung, pakai ldaps:// (port 636)." } else { "" }
}
$cLdap.Add_CheckedChanged({ Atur-Ldap }); $lServer[1].Add_TextChanged({ Atur-Ldap }); Atur-Ldap

# Dijalankan di proses terpisah (Start-Job): bind "DOMAIN\username" lalu cari data penggunanya (sama seperti config\sps_ldap.py).
$KERJA_UJI_LDAP = {
    param([string]$server, [string]$domain, [string]$base, [string]$akun, [string]$pw)
    Add-Type -AssemblyName System.DirectoryServices.Protocols
    $pesan = "alamat kosong"
    foreach ($s in $server.Split(",")) {
        $u = $s.Trim(); if (-not $u) { continue }
        $ssl = $u -match "^ldaps://"; $h = $u -replace "^ldaps?://", ""
        $port = if ($h -match ":(\d+)$") { [int]$Matches[1] } elseif ($ssl) { 636 } else { 389 }
        $h = $h -replace ":\d+$", ""
        try {
            $c = New-Object System.DirectoryServices.Protocols.LdapConnection((New-Object System.DirectoryServices.Protocols.LdapDirectoryIdentifier($h, $port)))
            $c.AuthType = [System.DirectoryServices.Protocols.AuthType]::Basic
            $c.SessionOptions.ProtocolVersion = 3; $c.SessionOptions.SecureSocketLayer = $ssl
            if ($ssl) { $c.SessionOptions.VerifyServerCertificate = { $true } }     # sertifikat internal kantor
            $c.Timeout = [TimeSpan]::FromSeconds(8)
            $c.Bind((New-Object System.Net.NetworkCredential("$domain\$akun", $pw)))
            $saring = "(&(objectCategory=person)(objectClass=user)(sAMAccountName=$($akun -replace '[()*\\]', ''))"
            $r = $c.SendRequest((New-Object System.DirectoryServices.Protocols.SearchRequest($base, $saring, "Subtree", @("displayName"))))
            $c.Dispose()
            if ($r.Entries.Count -ne 1) { return @($false, "Login benar, tetapi data $akun tidak ditemukan di Search base.") }
            $nama = $r.Entries[0].Attributes["displayName"]
            return @($true, "Berhasil: " + $(if ($nama) { $nama[0] } else { $akun }))
        } catch [System.DirectoryServices.Protocols.LdapException] {
            if ($_.Exception.ErrorCode -eq 49) { return @($false, "Username atau password salah.") }
            $pesan = $_.Exception.Message
        } catch { $pesan = $_.Exception.Message }
    }
    return @($false, "Tidak terjangkau ($pesan). Boleh dilanjutkan & diuji nanti.")
}
$btnUjiLdap.Add_Click({
    if (-not $lAkunUji[1].Text.Trim() -or -not $lPwUji[1].Text) { $lblUjiLdap.ForeColor = $MERAH; $lblUjiLdap.Text = "Isi username & password uji."; return }
    $lblUjiLdap.ForeColor = $REDUP; $lblUjiLdap.Text = "Menghubungi..."; $btnUjiLdap.Enabled = $false
    [void](Mulai-Latar $KERJA_UJI_LDAP @($lServer[1].Text, $lDomain[1].Text, $lBase[1].Text, $lAkunUji[1].Text.Trim(), $lPwUji[1].Text) {
        param($h)
        $btnUjiLdap.Enabled = $true
        $ok = $h.Count -ge 2 -and $h[0]
        $lblUjiLdap.Text = if ($h.Count -ge 2) { $h[1] } else { "Uji gagal dijalankan." }
        $lblUjiLdap.ForeColor = if ($ok) { $HIJAU } else { $MERAH }
    })
})
$pLdap.Controls.AddRange(@((Teks "Opsional. Lewati bila tidak memakai jaringan kantor; bisa diaktifkan kapan saja nanti." 0 6), $cLdap, $gLdap))
$HALAMAN += @{ Judul = "Login kantor (opsional)"; Sub = "LDAP / Active Directory - boleh dilewati"; Panel = $pLdap; Masuk = {}; Sah = {
    if (-not $cLdap.Checked) { return $null }
    if (-not $lServer[1].Text.Trim()) { return "Isi server LDAP, atau hilangkan centang 'Aktifkan login...'." }
    if (-not $lBase[1].Text.Trim()) { return "Isi Search base LDAP." }
    foreach ($n in (($lSuper[1].Text + "," + $lAdmin[1].Text).Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
        if ($n -notmatch '^[A-Za-z0-9._-]{2,64}$') { return "Username '$n' tidak sah (tanpa spasi; pisah koma)." }
    }
} }

# --- 3.6 Asisten AI: model lokal (Ollama / LM Studio) atau key model cloud ------------
# Model lokal TIDAK berjalan di Docker: dipasang sendiri di Windows (panduan docs\20-model-ai-lokal.md).
$pAi = New-Object System.Windows.Forms.Panel; $pAi.Dock = "Fill"
$lblAiOllama = Teks "Ollama    : belum diperiksa" 0 96 460
$lblAiLms = Teks "LM Studio : belum diperiksa" 0 120 460
$btnAiCek = New-Object System.Windows.Forms.Button
$btnAiCek.Text = "Periksa"; $btnAiCek.Location = "480,100"; $btnAiCek.Size = "100,30"
$btnAiOllama = New-Object System.Windows.Forms.Button
$btnAiOllama.Text = "Unduh Ollama"; $btnAiOllama.Location = "0,150"; $btnAiOllama.Size = "130,30"
$btnAiLms = New-Object System.Windows.Forms.Button
$btnAiLms.Text = "Unduh LM Studio"; $btnAiLms.Location = "140,150"; $btnAiLms.Size = "140,30"
$btnAiPanduan = New-Object System.Windows.Forms.Button
$btnAiPanduan.Text = "Buka panduan langkah demi langkah"; $btnAiPanduan.Location = "290,150"; $btnAiPanduan.Size = "260,30"
# Layanan AI cloud: variabel .env -> @(nama tampil, halaman pembuatan key, langkah). Modelnya diatur di config\ai.yaml.
# Catatan umum layanan gratis: kuota terbatas & data pertanyaan bisa dipakai penyedia untuk melatih model.
$CATATAN_GRATIS = "`r`n`r`nCatatan: paket gratis punya batas kuota harian dan pertanyaan Anda bisa dipakai penyedia untuk melatih model. Angka hasil query TIDAK dikirim (kirim_data: false di config\ai.yaml)."
$AI_CLOUD = [ordered]@{
    "AI_GEMINI_API_KEY"     = @("Google Gemini - gratis", "https://aistudio.google.com/apikey",
        "1. Buka Google AI Studio, login dengan akun Google.`r`n2. Klik Create API key (pilih/buat project).`r`n3. Salin key (diawali AIza...) lalu tempel di kolom API key.$CATATAN_GRATIS")
    "AI_GROQ_API_KEY"       = @("Groq - gratis, sangat cepat", "https://console.groq.com/keys",
        "1. Buka console.groq.com, daftar dengan email/Google (tanpa kartu kredit).`r`n2. Menu API Keys > Create API Key, beri nama ALDx.`r`n3. Salin key (diawali gsk_...) lalu tempel.$CATATAN_GRATIS")
    "AI_OPENROUTER_API_KEY" = @("OpenRouter - model gratis (:free)", "https://openrouter.ai/keys",
        "1. Buka openrouter.ai, Sign up (email/Google/GitHub).`r`n2. Menu Keys > Create Key, beri nama ALDx (batas kredit boleh 0).`r`n3. Salin key (diawali sk-or-...) lalu tempel. ALDx memakai model berakhiran :free.$CATATAN_GRATIS")
    "AI_CEREBRAS_API_KEY"   = @("Cerebras - gratis, sangat cepat", "https://cloud.cerebras.ai",
        "1. Buka cloud.cerebras.ai, daftar dengan email/Google.`r`n2. Menu API Keys > Generate API Key.`r`n3. Salin key (diawali csk-...) lalu tempel.$CATATAN_GRATIS")
    "AI_MISTRAL_API_KEY"    = @("Mistral - gratis (paket Experiment)", "https://console.mistral.ai/api-keys",
        "1. Buka console.mistral.ai, daftar.`r`n2. Pilih paket Experiment (gratis; perlu verifikasi nomor HP).`r`n3. API Keys > Create new key, salin lalu tempel.$CATATAN_GRATIS")
    "AI_GITHUB_TOKEN"       = @("GitHub Models - gratis dengan akun GitHub", "https://github.com/settings/personal-access-tokens/new",
        "1. Login GitHub, buka Settings > Developer settings > Fine-grained tokens > Generate new token.`r`n2. Beri nama ALDx, masa berlaku sesuai kebutuhan.`r`n3. Permissions > Account permissions > Models: Read-only.`r`n4. Generate token, salin (diawali github_pat_...) lalu tempel.$CATATAN_GRATIS")
    "AI_XAI_API_KEY"        = @("Grok (xAI) - kredit awal, lalu berbayar", "https://console.x.ai",
        "1. Buka console.x.ai, daftar/login (akun X atau email).`r`n2. Menu API Keys > Create API Key, beri nama ALDx.`r`n3. Salin key (diawali xai-...) lalu tempel.`r`n`r`nAkun baru biasanya mendapat kredit awal; setelah habis perlu isi saldo. Program berbagi data xAI memberi kredit bulanan (data dipakai melatih model).")
    "AI_OPENAI_API_KEY"     = @("OpenAI (GPT) - berbayar", "https://platform.openai.com/api-keys",
        "1. Buka platform.openai.com, login.`r`n2. Isi saldo di Billing (berbayar per pemakaian).`r`n3. API keys > Create new secret key, salin (diawali sk-...) lalu tempel.")
    "AI_ANTHROPIC_API_KEY"  = @("Anthropic (Claude) - berbayar", "https://console.anthropic.com/settings/keys",
        "1. Buka console.anthropic.com, login.`r`n2. Isi saldo di Billing (berbayar per pemakaian).`r`n3. API Keys > Create Key, salin (diawali sk-ant-...) lalu tempel.")
    "AI_DEEPSEEK_API_KEY"   = @("DeepSeek - berbayar, murah", "https://platform.deepseek.com/api_keys",
        "1. Buka platform.deepseek.com, daftar/login.`r`n2. Isi saldo di Top up (berbayar per pemakaian, tarif rendah).`r`n3. API keys > Create new API key, salin (diawali sk-...) lalu tempel.")
}
$script:kunciAi = @{}
foreach ($k in $AI_CLOUD.Keys) { $script:kunciAi[$k] = Nilai $k }
$aiPilih = New-Object System.Windows.Forms.ComboBox
$aiPilih.DropDownStyle = "DropDownList"; $aiPilih.Location = "230,212"; $aiPilih.Width = 300
foreach ($k in $AI_CLOUD.Keys) { [void]$aiPilih.Items.Add($AI_CLOUD[$k][0]) }
$aiKey = New-Object System.Windows.Forms.TextBox
$aiKey.Location = "230,244"; $aiKey.Width = 300; $aiKey.UseSystemPasswordChar = $true
$aiBantu = New-Object System.Windows.Forms.Button
$aiBantu.Text = "? Cara membuat key"; $aiBantu.Location = "536,211"; $aiBantu.Size = "150,25"; $aiBantu.TabStop = $false
$lblAiTerisi = Teks "" 230 274 470 $HIJAU
function Ai-Terpilih { return @($AI_CLOUD.Keys)[$aiPilih.SelectedIndex] }
function Ai-Status {
    $isi = @($AI_CLOUD.Keys | Where-Object { $script:kunciAi[$_] } | ForEach-Object { ($AI_CLOUD[$_][0] -split " - ")[0] })
    $lblAiTerisi.Text = if ($isi.Count) { "Key terisi: $($isi -join ', ')" } else { "Belum ada key cloud (boleh dikosongkan)." }
}
$aiPilih.Add_SelectedIndexChanged({ $script:muatAi = $true; $aiKey.Text = $script:kunciAi[(Ai-Terpilih)]; $script:muatAi = $false })
$aiKey.Add_TextChanged({ if (-not $script:muatAi) { $script:kunciAi[(Ai-Terpilih)] = $aiKey.Text.Trim(); Ai-Status } })
$aiBantu.Add_Click({ $d = $AI_CLOUD[(Ai-Terpilih)]; Bantuan $d[0] $d[2] $d[1] })
$aiPilih.SelectedIndex = 0; Ai-Status

# Dijalankan di proses terpisah. Ollama: /api/tags ; LM Studio: /v1/models (server aktif).
$KERJA_CEK_AI = {
    $o = try { @(@((Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 3).models | ForEach-Object { $_.name })) } catch { $null }
    $l = try { @(@((Invoke-RestMethod "http://localhost:1234/v1/models" -TimeoutSec 3).data | ForEach-Object { $_.id })) } catch { $null }
    return @{ ollama = $o; lmstudio = $l }
}
function Cek-ModelAi {
    $lblAiOllama.Text = "Ollama    : memeriksa..."; $lblAiLms.Text = "LM Studio : memeriksa..."; $btnAiCek.Enabled = $false
    [void](Mulai-Latar $KERJA_CEK_AI @() {
        param($h)
        $btnAiCek.Enabled = $true
        $r = if ($h.Count) { $h[0] } else { @{ ollama = $null; lmstudio = $null } }
        if ($null -eq $r.ollama) { $lblAiOllama.Text = "Ollama    : tidak terdeteksi"; $lblAiOllama.ForeColor = $REDUP }
        elseif ($r.ollama.Count) { $lblAiOllama.Text = "Ollama    : SIAP (model: $(($r.ollama | Select-Object -First 3) -join ', '))"; $lblAiOllama.ForeColor = $HIJAU }
        else { $lblAiOllama.Text = "Ollama    : aktif, belum ada model (jalankan: ollama pull qwen3:4b)"; $lblAiOllama.ForeColor = $KUNING }
        if ($null -eq $r.lmstudio) { $lblAiLms.Text = "LM Studio : tidak terdeteksi (atau server belum dinyalakan)"; $lblAiLms.ForeColor = $REDUP }
        elseif ($r.lmstudio.Count) { $lblAiLms.Text = "LM Studio : SIAP (model: $(($r.lmstudio | Select-Object -First 3) -join ', '))"; $lblAiLms.ForeColor = $HIJAU }
        else { $lblAiLms.Text = "LM Studio : server menyala, belum ada model (tab Discover > unduh qwen3)"; $lblAiLms.ForeColor = $KUNING }
    })
}
$btnAiCek.Add_Click({ Cek-ModelAi })
$btnAiOllama.Add_Click({ Start-Process "https://ollama.com/download/windows" })
$btnAiLms.Add_Click({ Start-Process "https://lmstudio.ai/download" })
$btnAiPanduan.Add_Click({
    $pdf = "$AKAR\docs\pdf\dokumen\20-model-ai-lokal.pdf"
    if (Test-Path $pdf) { Start-Process $pdf } else { Start-Process "$AKAR\docs\20-model-ai-lokal.md" }
})
$pAi.Controls.AddRange(@(
    (Teks "Asisten AI butuh model AI. Termudah & data tidak keluar kantor: model LOKAL gratis di Windows komputer ini (bukan Docker). Semua model yang sudah diunduh terdeteksi otomatis. Boleh dilewati: setelah terpasang, klik ikon sambung di panel Asisten AI (Ctrl + I)." 0 6 700),
    (Teks "Pilih salah satu: Ollama (disarankan) atau LM Studio (ada tampilan). RAM 8 GB cukup untuk model 4B, 16 GB+ untuk 8B-14B." 0 66 700 $REDUP),
    $lblAiOllama, $lblAiLms, $btnAiCek, $btnAiOllama, $btnAiLms, $btnAiPanduan,
    (Teks "Atau model cloud (data bisa keluar kantor; angka TIDAK dikirim kecuali diizinkan di config\ai.yaml). Boleh isi lebih dari satu:" 0 190 700 $REDUP),
    (Teks "Layanan cloud" 0 216 220), $aiPilih, $aiBantu, (Teks "API key" 0 248 220), $aiKey, $lblAiTerisi))
$HALAMAN += @{ Judul = "Asisten AI"; Sub = "Opsional - model lokal (Ollama/LM Studio) atau key cloud gratis/berbayar"; Panel = $pAi; Masuk = { Cek-ModelAi }; Sah = {} }

# --- 3.7b Data sebelumnya (volume Docker tanpa .env) --------------------------------------------
$pYatim = New-Object System.Windows.Forms.Panel; $pYatim.Dock = "Fill"
$rBaru = New-Object System.Windows.Forms.RadioButton
$rBaru.Text = "Mulai baru (disarankan) - data lama dicadangkan ke folder backup\ lalu dihapus"
$rBaru.Location = "0,70"; $rBaru.AutoSize = $true; $rBaru.Checked = $true
$rPakai = New-Object System.Windows.Forms.RadioButton
$rPakai.Text = "Pakai data lama - dashboard, chart & pengguna kembali"
$rPakai.Location = "0,140"; $rPakai.AutoSize = $true
$pYatim.Controls.AddRange(@((Teks "Data ALDx dari pemasangan sebelumnya masih ada di Docker, tetapi berkas pengaturannya (.env) sudah terhapus." 0 6),
    $rBaru, (Teks "Cocok bila Anda memang ingin memasang dari awal." 18 96 660 $REDUP),
    $rPakai, (Teks "Password koneksi sumber data yang tersimpan harus diisi ulang (kunci enkripsi lama ikut terhapus). Password Superadmin memakai isian halaman sebelumnya." 18 166 660 $REDUP)))
$HALAMAN += @{ Judul = "Data sebelumnya"; Sub = "Mulai baru atau pakai data lama"; Panel = $pYatim; Tampil = { $dataYatim }; Masuk = {}; Sah = {} }

# --- 3.8 Data lama (XAMPP / MariaDB -> PostgreSQL) ---------------------------------------------
$pLama = New-Object System.Windows.Forms.Panel; $pLama.Dock = "Fill"
$cPindah = New-Object System.Windows.Forms.CheckBox
$cPindah.Text = "Pindahkan dashboard, chart, user & pengaturan ke PostgreSQL (container metadb)"; $cPindah.Location = "0,70"; $cPindah.AutoSize = $true; $cPindah.Checked = $true
$teksLama = if ($sumberLama -eq "xampp") { "Instalasi lama ditemukan: metadata masih di MySQL XAMPP. Versi baru menyimpan semuanya di PostgreSQL (container metadb), jadi XAMPP tidak diperlukan lagi." }
            else { "Instalasi versi sebelumnya ditemukan: metadata di MariaDB. Versi baru memakai PostgreSQL (lebih ringan & direkomendasikan Superset)." }
$syaratLama = if ($sumberLama -eq "xampp") { "Syarat: MySQL XAMPP sedang MENYALA. Data XAMPP hanya dibaca (tidak diubah)." }
              else { "Data MariaDB lama hanya dibaca dan disimpan sebagai cadangan (volume sps_metadb)." }
$pLama.Controls.AddRange(@((Teks $teksLama 0 6), $cPindah,
    (Teks $syaratLama 20 100 660 $REDUP),
    (Teks "Bila tidak dicentang, instalasi dibatalkan: tanpa pemindahan, data lama tidak akan terlihat." 20 140 660 $MERAH)))
$HALAMAN += @{ Judul = "Data lama"; Sub = "Pindah ke PostgreSQL"; Panel = $pLama; Tampil = { $perluPindah }; Masuk = {}; Sah = {
    if (-not $cPindah.Checked) { return "Centang pemindahan data untuk melanjutkan." }
    if ($sumberLama -ne "xampp") { return }
    $port = Nilai "MYSQL_PORT" "3306"
    if (-not (Test-NetConnection localhost -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet)) {
        return "MySQL XAMPP (port $port) belum menyala. Buka XAMPP Control Panel > MySQL > Start." }
} }

# --- 3.9 Pasang ------------------------------------------------------------------------
$pPasang = New-Object System.Windows.Forms.Panel; $pPasang.Dock = "Fill"
$lblTahap = Teks "Klik Pasang untuk mulai. Pertama kali bisa 15-40 menit (mengunduh & membangun image)." 0 6 700 $null $TEBAL
$bar = New-Object System.Windows.Forms.ProgressBar
$bar.Location = "0,36"; $bar.Size = "712,16"
$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true; $log.ScrollBars = "Vertical"; $log.ReadOnly = $true; $log.Location = "0,62"; $log.Size = "712,316"
$log.Font = New-Object System.Drawing.Font("Consolas", 8.5); $log.BackColor = [System.Drawing.Color]::FromArgb(250, 251, 252)
$pPasang.Controls.AddRange(@($lblTahap, $bar, $log))
$HALAMAN += @{ Judul = "Pasang"; Sub = "Menjalankan langkah instalasi"; Panel = $pPasang; Masuk = { $btnLanjut.Text = "Pasang" }; Sah = {} }

# --- 3.10 Selesai -------------------------------------------------------------------
$pSelesai = New-Object System.Windows.Forms.Panel; $pSelesai.Dock = "Fill"
$lblSelesai = Teks "" 0 10 700 $null $TEBAL
$btnBuka = New-Object System.Windows.Forms.Button
$btnBuka.Text = "Buka aplikasi"; $btnBuka.Size = "180,36"; $btnBuka.Location = "0,300"
$btnBuka.BackColor = $UTAMA; $btnBuka.ForeColor = [System.Drawing.Color]::White; $btnBuka.FlatStyle = "Flat"
$btnSalin = New-Object System.Windows.Forms.Button
$btnSalin.Text = "Salin alamat"; $btnSalin.Size = "130,36"; $btnSalin.Location = "190,300"
$pSelesai.Controls.AddRange(@($lblSelesai, $btnBuka, $btnSalin))
$HALAMAN += @{ Judul = "Selesai"; Sub = "Aplikasi siap dipakai"; Panel = $pSelesai; Masuk = { $btnLanjut.Text = "Tutup"; $btnKembali.Enabled = $false; $btnBatal.Enabled = $false }; Sah = {} }

# Semua halaman dipasang sekali sejak awal (agar ikut diskalakan DPI); yang tampil diatur Visible.
foreach ($h in $HALAMAN) { $h.Panel.Visible = $false; $isi.Controls.Add($h.Panel) }

# ============================================================================
# 4. Langkah instalasi (dijalankan berurutan, keluaran masuk ke log)
# ============================================================================
New-Item -ItemType Directory -Force "installer\log" | Out-Null
$BERKAS_LOG = "$AKAR\installer\log\pasang-$(Get-Date -Format 'yyyyMMdd-HHmm').log"

function Tulis-Log([string]$t) {
    $t = $t -replace '(://[^:/@\s]+:)[^@\s]+@', '$1***@'      # password di alamat database tidak ikut tercatat
    $log.AppendText($t + "`r`n"); Add-Content -Path $BERKAS_LOG -Value $t
    [System.Windows.Forms.Application]::DoEvents()
}

function Baca-Baru([string]$berkas, [ref]$posisi) {
    <# Baris baru di berkas sejak pembacaan terakhir (berkas sedang ditulis proses lain). #>
    if (-not (Test-Path $berkas)) { return }
    $fs = [System.IO.File]::Open($berkas, "Open", "Read", "ReadWrite")
    try {
        [void]$fs.Seek($posisi.Value, "Begin")
        $sr = New-Object System.IO.StreamReader($fs)
        $teks = $sr.ReadToEnd(); $posisi.Value = $fs.Position
    } finally { $fs.Close() }
    if ($teks) { $teks.TrimEnd("`r", "`n").Split("`n") | ForEach-Object { Tulis-Log $_.TrimEnd("`r") } }
}

function Jalankan([string]$judul, [string]$skrip, [string[]]$argumen = @()) {
    <# Jalankan scripts\<skrip>.ps1 sebagai proses terpisah. Keluarannya ditulis ke berkas
       sementara lalu dibaca berkala, sehingga jendela wizard tetap responsif. #>
    $lblTahap.Text = $judul; Tulis-Log "`r`n==> $judul"
    $keluar = [System.IO.Path]::GetTempFileName(); $galat = [System.IO.Path]::GetTempFileName()
    $arg = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$AKAR\scripts\$skrip.ps1`"") + $argumen
    $p = Start-Process $script:PSH -ArgumentList $arg -WorkingDirectory $AKAR -WindowStyle Hidden -PassThru `
         -RedirectStandardOutput $keluar -RedirectStandardError $galat
    $null = $p.Handle      # wajib di PowerShell 5.1: tanpa ini ExitCode kosong walau proses berhasil
    $pos1 = 0L; $pos2 = 0L
    while (-not $p.HasExited) {
        Baca-Baru $keluar ([ref]$pos1); Baca-Baru $galat ([ref]$pos2)
        [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 200
    }
    $p.WaitForExit()
    Baca-Baru $keluar ([ref]$pos1); Baca-Baru $galat ([ref]$pos2)
    Remove-Item $keluar, $galat -ErrorAction SilentlyContinue
    $kode = $p.ExitCode
    if ($null -eq $kode) { $kode = 0 }   # cadangan: kode tak terbaca dianggap berhasil (galat nyata selalu memberi kode)
    if ($kode -ne 0) { throw "Langkah '$judul' gagal (kode $kode). Lihat log: $BERKAS_LOG" }
}

function Simpan-Isian {
    <# Superadmin selalu akun lokal (email). LDAP opsional: username di SPS_SUPERADMIN_USERS / LDAP_ADMIN_USERS. #>
    $mail = $sMail[1].Text.Trim()
    if ($mail) {
        Set-EnvValue "ADMIN_USERNAME" $mail; Set-EnvValue "ADMIN_EMAIL" $mail
        $nama = $sNama[1].Text.Trim()
        if ($nama) { $d, $b = $nama.Split(" ", 2); Set-EnvValue "ADMIN_FIRSTNAME" $d; Set-EnvValue "ADMIN_LASTNAME" $(if ($b) { $b } else { "-" }) }
    }
    if ($sPw[1].Text) { Set-EnvValue "ADMIN_PASSWORD" $sPw[1].Text }
    Set-EnvValue "AUTH_LOCAL_USERS" (Get-EnvValue "ADMIN_USERNAME")   # akun ber-"@" (email) selalu akun lokal
    if ($script:idnDiubah) {
        Set-EnvValue "SPS_NAMA_APLIKASI" $iNama[1].Text.Trim(); Set-EnvValue "SPS_NAMA_PERUSAHAAN" $iPerusahaan[1].Text.Trim()
        Set-EnvValue "SPS_PRESET" @($PRESET.Keys)[$iPreset.SelectedIndex]
        if ($iLogo[1].Text -and (Test-Path -LiteralPath $iLogo[1].Text)) {
            $tujuan = "logo-kustom" + [System.IO.Path]::GetExtension($iLogo[1].Text).ToLower()
            Copy-Item -LiteralPath $iLogo[1].Text "$AKAR\branding\$tujuan" -Force
            Set-EnvValue "SPS_LOGO" $tujuan
        }
        Set-EnvValue "SPS_IDENTITAS_TERAPKAN" "1"   # dibaca sekali oleh build-dashboards (sps_identitas.siapkan)
    }
    Set-EnvValue "SUPERSET_PORT" $aPort[1].Text.Trim()
    Set-EnvValue "SPS_HTTPS" $(if ($cHttps.Checked) { "1" } else { "" })
    Set-EnvValue "SPS_HTTPS_NAMA" (($aNamaServer[1].Text -split "[,\s]+" | Where-Object { $_ }) -join ",")
    if ($cLdap.Checked) {
        Set-EnvValue "LDAP_SERVERS" $lServer[1].Text.Trim(); Set-EnvValue "LDAP_DOMAIN" $lDomain[1].Text.Trim()
        Set-EnvValue "LDAP_SEARCH_BASE" $lBase[1].Text.Trim()
        Set-EnvValue "SPS_SUPERADMIN_USERS" (($lSuper[1].Text -split "[,\s]+" | Where-Object { $_ }) -join ",")
        Set-EnvValue "LDAP_ADMIN_USERS" (($lAdmin[1].Text -split "[,\s]+" | Where-Object { $_ }) -join ",")
    } else { Set-EnvValue "LDAP_SERVERS" "" }
    foreach ($k in $AI_CLOUD.Keys) { Set-EnvValue $k $script:kunciAi[$k] }
    Initialize-ServerEnv | ForEach-Object { Tulis-Log $_ }
    Tulis-Log ".env diperbarui (password tidak ditampilkan)."
}

function Buat-Pengguna {
    <# Buat/perbarui Superadmin (nama & password) + akun dari tabel.
       Daftar (berisi password) dikirim lewat stdin, tidak pernah ke berkas. #>
    $lain = Daftar-Pengguna
    $script:jumlahPengguna = $lain.Count; $script:jumlahBawaan = @($lain | Where-Object { $_.bawaan }).Count
    $daftar = @($lain | ForEach-Object { [ordered]@{ username = $_.username; email = $_.email; nama = $_.nama; password = $_.password; peran = $_.peran } })
    if ($sPw[1].Text -and $sMail[1].Text.Trim()) {
        $daftar = @([ordered]@{ username = $sMail[1].Text.Trim(); email = $sMail[1].Text.Trim(); nama = $sNama[1].Text.Trim()
                                password = $sPw[1].Text; peran = "Superadmin" }) + $daftar
    }
    if (-not $daftar.Count) { return }
    $lblTahap.Text = "Membuat akun pengguna"; Tulis-Log "`r`n==> Membuat $($daftar.Count) akun pengguna"
    $json = ConvertTo-Json -InputObject @($daftar) -Compress
    $lamaEnc = $OutputEncoding; $OutputEncoding = New-Object System.Text.UTF8Encoding($false)   # nama ber-aksen aman
    $lama = $ErrorActionPreference; $ErrorActionPreference = "Continue"                          # log INFO Superset di stderr
    try {
        $json | docker compose exec -T superset python /app/pythonpath/sps_pengguna.py 2>&1 |
            Where-Object { "$_" -match "^(OK|GAGAL)" } | ForEach-Object { Tulis-Log "$_" }
        if ($LASTEXITCODE -ne 0) { throw "Sebagian akun gagal dibuat (lihat baris GAGAL di log). Klik Kembali untuk memperbaiki, lalu Pasang lagi." }
    } finally { $ErrorActionPreference = $lama; $OutputEncoding = $lamaEnc; $json = $null }
}

function Tunggu-Web([string]$url) {
    <# True bila /health menjawab OK dalam 5 menit. Sertifikat buatan sendiri diterima (hanya untuk cek ini). #>
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    try {
        for ($i = 0; $i -lt 100; $i++) {
            try { if ((Invoke-WebRequest "$url/health" -UseBasicParsing -TimeoutSec 5).Content -match "OK") { return $true } } catch { }
            [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Seconds 3
        }
        return $false
    } finally { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $null }
}

$script:sedangPasang = $false
function Pasang {
    $script:sedangPasang = $true
    $btnLanjut.Enabled = $false; $btnKembali.Enabled = $false; $btnBatal.Enabled = $false
    $lblTahap.ForeColor = [System.Drawing.SystemColors]::ControlText; $log.Clear()
    $langkah = @()
    if ($dataYatim -and $rBaru.Checked) { $langkah += ,@("Mencadangkan & menghapus data pemasangan sebelumnya", "hapus-aldx", @("-MulaiBaru", "-TanpaJeda")) }
    if ($perluPindah) { $langkah += ,@("Memindahkan metadata lama ($sumberLama) ke PostgreSQL", "pindah-metadata", @()) }
    $langkah += ,@("Membangun image & menyiapkan database", "init", @())
    $langkah += ,@("Menyalakan semua container", "start", @())
    $langkah += ,@("Menyiapkan dashboard, menu & ALDx Engine", "build-dashboards", @())
    $langkah += ,@("Memuat data latihan (fiktif) untuk pelatihan", "data-latihan", @())
    $bar.Maximum = $langkah.Count + 2; $bar.Value = 0
    try {
        $lblTahap.Text = "Menyimpan isian ke .env"; Simpan-Isian; $bar.Value++
        foreach ($l in $langkah) { Jalankan $l[0] $l[1] $l[2]; $bar.Value++ }
        Set-EnvValue "SPS_IDENTITAS_TERAPKAN" ""   # identitas sudah masuk database; berikutnya diatur di Pusat Kendali
        Buat-Pengguna
        $lblTahap.Text = "Menunggu web siap"; Tulis-Log "`r`n==> Menunggu web siap"
        $url = Get-AlamatWeb
        $siap = Tunggu-Web $url
        $bar.Value = $bar.Maximum
        Set-EnvValue "ADMIN_PASSWORD" ""          # password admin tidak dibiarkan tersimpan di .env
        Tulis-Log "`r`nSELESAI. Password admin dihapus dari .env."
        $login = "Superadmin: $(Get-EnvValue 'ADMIN_USERNAME')" +
            $(if ($script:jumlahPengguna) { " + $($script:jumlahPengguna) akun lain" } else { "" }) +
            $(if ($script:jumlahBawaan) { "`r`n$($script:jumlahBawaan) akun memakai password bawaan ${PW_BAWAAN}: minta segera diganti (Info pengguna)." } else { "" }) +
            $(if ($cLdap.Checked) { "`r`nPengguna juga bisa login dengan username & password jaringan kantor." } else { "" })
        $lblSelesai.Text = $(if ($siap) { "Instalasi selesai." } else { "Instalasi selesai, tetapi web belum menjawab. Tunggu 2-3 menit lalu klik Buka aplikasi. Bila tetap tidak terbuka: scripts\diagnose.ps1" }) +
            "`r`n`r`nAlamat   : $url`r`n$login" +
            $(if ($cHttps.Checked) { "`r`nHTTPS   : browser memperingatkan sekali (sertifikat dibuat sendiri). Pilih 'Lanjutkan', atau jalankan scripts\percayai-sertifikat.ps1." } else { "" }) +
            "`r`n`r`nPanduan: folder docs\ (PDF: docs\pdf\), mulai dari docs\00-mulai-di-sini.md" +
            $(if ($lblAiOllama.Text -match "SIAP" -or $lblAiLms.Text -match "SIAP") { "`r`nAsisten AI: model lokal siap." }
              else { "`r`nAsisten AI: belum tersambung. Buka aplikasi > panel Asisten AI (Ctrl + I) > Sambungkan AI." }) +
            "`r`nLog instalasi: $BERKAS_LOG"
        $lblSelesai.ForeColor = if ($siap) { [System.Drawing.SystemColors]::ControlText } else { $KUNING }
        $script:alamatWeb = $url
        $script:sedangPasang = $false
        Pindah 1
    } catch {
        Tulis-Log "`r`nGAGAL: $($_.Exception.Message)"
        $lblTahap.Text = "Gagal. Perbaiki penyebab di log (atau klik Kembali untuk mengubah isian), lalu klik Pasang lagi (aman diulang)."
        $lblTahap.ForeColor = $MERAH
        $btnLanjut.Enabled = $true; $btnBatal.Enabled = $true; $btnKembali.Enabled = $true
        $script:sedangPasang = $false
    }
}
$btnBuka.Add_Click({ Start-Process $script:alamatWeb })
$btnSalin.Add_Click({ [System.Windows.Forms.Clipboard]::SetText($script:alamatWeb); $btnSalin.Text = "Tersalin" })

# ============================================================================
# 5. Navigasi (halaman dengan Tampil = $false dilewati)
# ============================================================================
# Urutan: Superadmin tepat setelah Pemeriksaan; halaman lanjutan hanya tampil bila dicentang.
# Asisten AI selalu tampil (opsional, boleh dilewati): tanpa model AI menu Asisten tidak berguna.
$LANJUTAN = @("Identitas & alamat", "Pengguna lain", "Login kantor (opsional)")
$URUTAN = @("Pemeriksaan komputer", "Akun Superadmin", "Data sebelumnya") + $LANJUTAN + @("Data lama", "Pasang", "Selesai")
$HALAMAN = @($URUTAN | ForEach-Object { $j = $_; $HALAMAN | Where-Object { $_.Judul -eq $j } })
foreach ($h in $HALAMAN) { $h.Lanjutan = $LANJUTAN -contains $h.Judul }
$script:ke = 0
$script:bolehTutup = $false
function Boleh-Tampil([int]$i) {
    $h = $HALAMAN[$i]
    if ($h.Lanjutan -and -not $cLanjutan.Checked) { return $false }
    return (-not $h.Tampil) -or [bool](& $h.Tampil)
}
function Tampilkan([int]$i) {
    foreach ($x in $HALAMAN) { $x.Panel.Visible = $false }
    $h = $HALAMAN[$i]; $h.Panel.Visible = $true
    $lblJudul.Text = $h.Judul; $lblSub.Text = $h.Sub
    $terlihat = @(0..($HALAMAN.Count - 1) | Where-Object { Boleh-Tampil $_ })
    $lblLangkah.Text = "Langkah $([array]::IndexOf($terlihat, $i) + 1) dari $($terlihat.Count)"
    $btnKembali.Enabled = $i -gt 0; $btnLanjut.Text = "Lanjut >"; $btnLanjut.Enabled = $true
    & $h.Masuk
}
function Pindah([int]$arah) {
    $i = $script:ke + $arah
    while ($i -gt 0 -and $i -lt $HALAMAN.Count - 1 -and -not (Boleh-Tampil $i)) { $i += $arah }
    $script:ke = [Math]::Max(0, [Math]::Min($i, $HALAMAN.Count - 1)); Tampilkan $script:ke
}
$btnLanjut.Add_Click({
    $h = $HALAMAN[$script:ke]
    if ($h.Judul -eq "Selesai") { $script:bolehTutup = $true; $form.Close(); return }
    if ($h.Judul -eq "Pasang") { Pasang; return }
    $pesan = & $h.Sah
    if ($pesan) { [void][System.Windows.Forms.MessageBox]::Show($pesan, "Periksa isian", "OK", "Warning"); return }
    Pindah 1
})
$btnKembali.Add_Click({ Pindah -1 })
$btnBatal.Add_Click({ $form.Close() })
$form.Add_FormClosing({
    param($s, $e)
    if ($script:sedangPasang) {
        [void][System.Windows.Forms.MessageBox]::Show("Instalasi sedang berjalan. Tunggu sampai selesai atau gagal; menutup sekarang bisa meninggalkan instalasi setengah jadi.", "Sedang memasang", "OK", "Information")
        $e.Cancel = $true; return
    }
    if (-not $script:bolehTutup -and $HALAMAN[$script:ke].Judul -ne "Selesai") {
        $j = [System.Windows.Forms.MessageBox]::Show("Batalkan instalasi? Isian yang belum dipasang tidak disimpan.", "Batal", "YesNo", "Question")
        if ($j -ne "Yes") { $e.Cancel = $true }
    }
})

$cLanjutan.Checked = $sudahTerpasang       # pasang ulang: tampilkan semua isian lama untuk ditinjau
Tampilkan 0
[void]$form.ShowDialog()
