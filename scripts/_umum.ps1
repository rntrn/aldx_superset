<#
.SYNOPSIS
    Fungsi bersama untuk skrip lain (di-dot-source: . "$PSScriptRoot\_umum.ps1").
    Tidak untuk dijalankan langsung.
#>

function Get-EnvValue([string]$Name) {
    <# Nilai KEY dari .env, atau string kosong. #>
    $m = Select-String -Path ".env" -Pattern "^$Name=(.*)$" | Select-Object -First 1
    if ($m) { return $m.Matches.Groups[1].Value.Trim() }
    return ""
}

function Set-EnvValue([string]$Name, [string]$Value) {
    <# Ganti baris KEY=... di .env, atau tambahkan di akhir bila belum ada. #>
    $text = Get-Content ".env" -Raw
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"
    if ($text -match $pattern) {
        $text = [regex]::Replace($text, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ "$Name=$Value" })
    } else {
        $text = $text.TrimEnd() + "`r`n$Name=$Value`r`n"
    }
    Set-Content ".env" $text -NoNewline
}

function Get-AlamatWeb {
    <# Alamat web aplikasi di komputer ini, mis. http://localhost:8088 atau https://localhost:8088 (SPS_HTTPS=1). #>
    $skema = if ((Get-EnvValue "SPS_HTTPS") -eq "1") { "https" } else { "http" }
    $port = Get-EnvValue "SUPERSET_PORT"; if (-not $port) { $port = "8088" }
    return "${skema}://localhost:$port"
}

function New-RandomSecret([int]$Bytes = 24) {
    <# String acak aman untuk password (huruf & angka saja). #>
    $buf = New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    return ([Convert]::ToBase64String($buf) -replace "[^A-Za-z0-9]", "")
}

function Initialize-ServerEnv {
    <# Pastikan password container & variabel Pusat Kendali ada di .env (aman dijalankan berulang).
       Hanya nilai placeholder (GANTI_DENGAN_...) atau kosong yang dibuat; nilai yang sudah ada TIDAK diubah. #>
    $rahasia = [ordered]@{
        "REDIS_PASSWORD"       = "GANTI_DENGAN_PASSWORD_REDIS"
        "METADB_PASSWORD"      = "GANTI_DENGAN_PASSWORD_METADB"
        "ENGINE_PASSWORD"      = "GANTI_DENGAN_PASSWORD_ENGINE"
    }
    foreach ($k in $rahasia.Keys) {
        $v = Get-EnvValue $k
        if (-not $v -or $v -eq $rahasia[$k]) {
            Set-EnvValue $k (New-RandomSecret)
            Write-Host "$k dibuat otomatis di .env." -ForegroundColor Green
        }
    }
    # Nama lama REDIS_BIND -> CLUSTER_BIND (berlaku untuk Redis, metadb & engine).
    $bindLama = Get-EnvValue "REDIS_BIND"
    if ($bindLama -and -not (Get-EnvValue "CLUSTER_BIND")) { Set-EnvValue "CLUSTER_BIND" $bindLama }
    foreach ($k in @("ENGINE_HOST=engine", "ENGINE_PORT=8123", "ENGINE_DATABASE=sps_engine", "ENGINE_USER=sps",
                     "ENGINE_PORT_HOST=8124", "METADB_HOST=metadb", "METADB_PORT=5432",
                     "METADB_DATABASE=sps_superset", "METADB_USER=superset", "METADB_PORT_HOST=5433")) {
        $n, $v = $k -split "=", 2
        if (-not (Get-EnvValue $n)) { Set-EnvValue $n $v }
    }
    # Role dasar semua pengguna (nama role yang sudah ada di .env tidak diubah).
    if (-not (Get-EnvValue "SPS_ROLE_PENGGUNA")) { Set-EnvValue "SPS_ROLE_PENGGUNA" "Pengguna" }
    if (-not (Get-EnvValue "NODE_NAMA")) {
        Set-EnvValue "NODE_NAMA" $env:COMPUTERNAME
        Write-Host "NODE_NAMA = $env:COMPUTERNAME" -ForegroundColor Green
    }
}

function Get-SumberMetaLama {
    <# Dari mana metadata lama perlu dipindah ke PostgreSQL?
       "xampp"   : versi pertama, metadata di MySQL XAMPP Windows
       "mariadb" : versi sebelumnya, metadata di container MariaDB (volume sps_metadb)
       $null     : sudah PostgreSQL / instalasi baru (tidak ada yang dipindah) #>
    if ((Get-EnvValue "METADB_JENIS") -eq "postgres") { return $null }
    if ((Get-EnvValue "MYSQL_HOST") -eq "host.docker.internal") { return "xampp" }
    $mysqlPw = Get-EnvValue "MYSQL_PASSWORD"
    if ($mysqlPw -and $mysqlPw -ne "GANTI_DENGAN_PASSWORD_METADB") {
        docker info *> $null
        if ($LASTEXITCODE -ne 0) { return "mariadb" }   # Docker mati: anggap ada data lama (dicek ulang saat pindah)
        docker volume inspect sps_metadb *> $null
        if ($LASTEXITCODE -eq 0) { return "mariadb" }
    }
    # Tidak ada data lama: tandai langsung sebagai PostgreSQL.
    Set-EnvValue "METADB_JENIS" "postgres"
    return $null
}

function Assert-SudahPindah {
    <# Metadata versi lama (XAMPP / MariaDB) harus dipindah dulu agar data tidak "hilang". #>
    $sumber = Get-SumberMetaLama
    if ($sumber) {
        Write-Host "Metadata masih di $sumber (versi lama). Pindahkan dulu ke PostgreSQL:" -ForegroundColor Yellow
        Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\pindah-metadata.ps1   (atau jalankan PASANG.cmd)"
        exit 1
    }
}

function Import-ImageOffline {
    <# Paket OFFLINE (ALDx-Setup-Offline.exe): offline\aldx-images.tar.gz berisi semua image (Superset ALDx sudah jadi,
       PostgreSQL, ClickHouse, Redis, nginx). Dimuat ke Docker sekali per versi paket (offline\versi.txt dicatat di
       .env SPS_OFFLINE_VERSI). Mengembalikan $true bila paket offline dipakai -> image tidak perlu dibangun/diunduh. #>
    $tar = "offline\aldx-images.tar.gz"
    if (-not (Test-Path $tar)) { return $false }
    $versi = if (Test-Path "offline\versi.txt") { (Get-Content "offline\versi.txt" -Raw).Trim() } else { "?" }
    docker image inspect "sps-superset:$(Get-EnvValue 'SUPERSET_VERSION')" *> $null
    if ($LASTEXITCODE -eq 0 -and (Get-EnvValue "SPS_OFFLINE_VERSI") -eq $versi) {
        Write-Host "Image paket offline ($versi) sudah dimuat."; return $true
    }
    Write-Host "Memuat image dari paket offline ($versi, beberapa menit, tanpa internet)..."
    docker load -i $tar | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Gagal memuat $tar (berkas rusak? salin ulang paket offline)." }
    Set-EnvValue "SPS_OFFLINE_VERSI" $versi
    return $true
}

function Sync-MetadbPassword {
    <# Samakan password user metadb di PostgreSQL dengan .env (METADB_PASSWORD).
       Perlu bila volume data lama dipakai lagi dengan .env baru (password acak baru) -> tanpa ini:
       "password authentication failed for user superset". Lewat socket lokal di dalam container
       (tanpa password); perintah SQL dikirim lewat stdin, jadi password tidak tampil di daftar proses/log. #>
    $u = Get-EnvValue "METADB_USER"; if (-not $u) { $u = "superset" }
    $pw = (Get-EnvValue "METADB_PASSWORD") -replace "'", "''"
    $sql = "ALTER USER `"$u`" WITH PASSWORD '$pw';"
    $hasil = $sql | docker compose exec -T metadb psql -q -U $u -d postgres -v ON_ERROR_STOP=1 2>&1
    $sql = $null; $pw = $null
    if ($LASTEXITCODE -eq 0) { Write-Host "Password metadb sesuai .env." }
    else { Write-Host "Peringatan: password metadb tidak bisa disamakan ($(($hasil | Out-String).Trim()))" -ForegroundColor Yellow }
}

function Wait-Container([string[]]$Layanan, [int]$Detik = 180) {
    <# Nyalakan layanan docker compose & tunggu sampai sehat (healthcheck).
       Container yang sudah berstatus "unhealthy" (mis. sisa percobaan sebelumnya) dibuat ulang dulu,
       karena --wait langsung gagal bila status lama masih unhealthy. Bila gagal, 40 baris log
       terakhir layanan yang bermasalah ditampilkan (ikut tercatat di log installer). #>
    $sakit = @(docker compose ps -a --format "{{.Service}} {{.Health}} {{.State}}" @Layanan 2>$null |
        Where-Object { $_ -match "unhealthy|exited|restarting|dead" } | ForEach-Object { ($_ -split " ")[0] })
    if ($sakit.Count) {
        Write-Host "Membuat ulang container: $($sakit -join ', ') (status sebelumnya tidak sehat)" -ForegroundColor Yellow
        docker compose up -d --force-recreate @sakit
    }
    docker compose up -d --wait --wait-timeout $Detik @Layanan
    if ($LASTEXITCODE -ne 0) {
        $gagal = @(docker compose ps -a --format "{{.Service}} {{.Health}} {{.State}}" @Layanan 2>$null |
            Where-Object { $_ -notmatch " healthy running" } | ForEach-Object { ($_ -split " ")[0] })
        if (-not $gagal.Count) { $gagal = $Layanan }
        foreach ($l in $gagal) {
            Write-Host "`n----- 40 baris log terakhir: $l -----" -ForegroundColor Yellow
            $ErrorActionPreference = "Continue"     # log docker di stderr bukan galat
            docker compose logs --no-color --tail 40 $l 2>&1 | ForEach-Object { "$_" }
        }
        throw "Container $($gagal -join ', ') tidak sehat. Log di atas menunjukkan penyebabnya (docs\19-runbook-faq-admin.md bagian 4)."
    }
}
