# 29 · Versi Installer, Pembaruan & Menghapus Total

## 1. Tiga cara memasang, bisa beda versi

Installer **membekukan** isi aplikasi pada saat installer itu dibangun. Jadi dua komputer yang dipasang dengan cara
berbeda bisa menjalankan versi yang berbeda.

| Cara memasang | Versi yang terpasang | Kapan versinya diperbarui |
|---|---|---|
| `git clone` / `git pull` / Download ZIP | **selalu terbaru** (cabang `main`) | setiap kali Anda *pull* / unduh ulang |
| **ALDx-Setup.exe** | isi repo **saat exe dibangun** | `installer\setup\buat-installer.ps1` di komputer pengembang, atau GitHub Actions (`setup.yml`) |
| **ALDx-Setup-Offline.exe** + `.bin` | isi repo + image Docker **saat dibangun** | `installer\setup\buat-installer.ps1 -Offline`, atau GitHub Actions (`setup-offline.yml`) |

**Otomatis:** setiap perubahan di cabang `main` repo `aldx_superset` dibangun GitHub Actions
(`.github/workflows/rilis.yml`): installer online, pembersih total, dan paket offline diterbitkan ke Releases dalam
± 30 menit, tanpa komputer pengembang. Judul rilis memuat versinya, catatannya memuat kode commit.

**Aturan versi (wajib tiap pembaruan):**

1. Naikkan `VERSI` di `config/sps_versi_aplikasi.py` = tanggal rilis (`2026.11.13`). Rilis kedua di hari yang sama
   memakai nomor urut: `2026.11.13.2`, `2026.11.13.3`.
2. Catat perubahannya di [31 · Catatan versi](31-catatan-versi.md).
3. Push ke `main`. GitHub Actions **menolak membangun** (langkah *Periksa VERSI*) bila berkas aplikasi (`config`,
   `docker`, `installer`, `scripts`, `docker-compose.yml`) berubah tetapi `VERSI` masih sama dengan rilis yang sudah
   terbit. Perubahan dokumentasi saja tidak perlu menaikkan versi.
4. Setelah berkas terunggah, rilis diterbitkan ulang sehingga **tanggal dan judul di halaman Releases** selalu
   menunjukkan build terakhir.

**Unduhan resmi:** halaman **Releases** repo: *ALDx terbaru* (`ALDx-Setup.exe`, `ALDx-HapusTotal.exe`) dan *ALDx offline*
(`ALDx-Setup-Offline.exe` + `ALDx-Setup-Offline-1.bin` + `ALDx-HapusTotal.exe`). Ukuran berkas di Releases dicocokkan dengan
hasil build sebelum diumumkan. Setiap rilis menyertakan **`ALDx-SHA256.txt`**.

### Versi yang bisa dicocokkan dengan rilis GitHub

Mulai **2026.11.14**, setiap `VERSI` mendapat **rilis tetap** bertag `v<VERSI>` selain dua rilis bergulir:

| Rilis | Isi | Berubah? |
|---|---|---|
| **ALDx terbaru** (tag `terbaru`) | installer online versi terakhir | ya, ditimpa tiap build |
| **ALDx offline** (tag `offline`) | paket offline versi terakhir | ya, ditimpa tiap build |
| **ALDx 2026.11.14** (tag `v2026.11.14`) | `ALDx-Setup.exe`, `ALDx-HapusTotal.exe`, `ALDx-SHA256.txt`, catatan versi | **tidak**: tag menunjuk commit build-nya |

Rantai pencocokan: kaki halaman login `v2026.11.14` = tag git `v2026.11.14` = rilis *ALDx 2026.11.14* = commit di catatan
rilisnya = bagian `## 2026.11.14` di [31 · Catatan versi](31-catatan-versi.md). Di Beranda, nomor versi bisa diklik
untuk membuka rilis itu. Catatan rilis diambil otomatis dari bab 31 (`scripts/catatan-rilis.ps1`); build ditolak bila
bagian versi itu belum ditulis.

**Memeriksa unduhan utuh & asli** (PowerShell, di folder unduhan):

```powershell
(Get-FileHash .\ALDx-Setup.exe -Algorithm SHA256).Hash.ToLower()
Get-Content .\ALDx-SHA256.txt        # baris ALDx-Setup.exe harus sama persis
```

Paket offline (±1,7 GB) hanya disimpan di rilis *offline* (versi terakhir); sidiknya tetap tercatat di `ALDx-SHA256.txt`
rilis versinya. Butuh paket offline versi lama: bangun dari tag-nya (`git checkout v2026.11.14`, lalu
`installer\setup\buat-installer.ps1 -Offline`).

**Membangun installer terbaru sendiri** (tanpa GitHub Actions), di folder repo:

```powershell
winget install JRSoftware.InnoSetup                                   # sekali
pwsh -File installer\setup\buat-installer.ps1 -Offline                # PowerShell 7
# atau Windows PowerShell: powershell -ExecutionPolicy Bypass -File installer\setup\buat-installer.ps1 -Offline
```

Setelah setiap perbaikan, pengembang menjalankan `.\scripts\sinkron-laptop.ps1 -Terbitkan` (memanggil
`installer\setup\terbitkan.ps1` setelah uji lulus). Persiapan sekali dikerjakan otomatis: **Inno Setup 6** dan
**GitHub CLI** dipasang lewat `winget` bila belum ada, lalu **login GitHub** dibuka di browser (salin kode 8 huruf
dari layar). Berkas `.bundle` di folder dipindah ke `installer\log`; berkas lain yang belum di-commit membuat
proses berhenti dengan daftar berkasnya. Seluruh pesan tercatat di `installer\log\sinkron-*.log`. Hasilnya: installer online
**dan** offline di Releases selalu sama dengan versi terbaru di git.

Hasil di `installer\setup\Output\`: `ALDx-Setup.exe` (online), `ALDx-HapusTotal.exe` (pembersih total), dan
`ALDx-Setup-Offline.exe` + `ALDx-Setup-Offline-*.bin`
(semua berkas offline harus berada di **satu folder**). Setiap berkas dipindai Windows Defender; Docker Desktop Installer
diperiksa tanda tangan resminya. Tanpa sertifikat tanda tangan kode, Windows SmartScreen bisa menampilkan *"Windows protected
your PC"* saat pertama dibuka: klik **More info › Run anyway** (lihat [18 › Peringatan Windows & antivirus](18-installer.md)).

> **Bila GitHub Actions tidak berjalan** (kuota menit habis, repo dipindah, atau workflow dimatikan), exe di Releases
> **tidak ikut diperbarui** dan tetap berisi versi lama. Cek tanggal berkas di halaman Releases sebelum dipakai.

### Cara mengetahui versi yang terpasang

| Di mana | Cara |
|---|---|
| Halaman login | kaki halaman: `v2026.11.13.3` (versi terpasang; plus kode commit bila dipasang dengan git) |
| Beranda (bawah) | `ALDx v2026.11.13 · a1b2c3d · ✓ Versi terbaru`, atau **Pembaruan tersedia: v…** + tautan *Unduh installer* & *Apa yang baru* (Admin). Dicek ke GitHub tiap 6 jam; tanpa internet tertulis *tidak bisa dicek* |
| Aplikasi | fitur terbaru terlihat? Versi November 2026: menu **Sematkan ke web lain**, bagian **Objek** di Studio › Susun dashboard, chip filter global di bilah atas. Daftar lengkap: [31 · Catatan versi](31-catatan-versi.md) |
| Folder instalasi | `git log -1 --oneline` (bila dipasang dengan git), atau `scripts\versi.ps1` |
| Paket offline | berkas `offline\versi.txt` (tanggal + kode commit) |

### Cara termudah memperbarui (sudah terpasang)

**Jalankan installer versi baru di atas instalasi lama, Next-Next.** Folder sama, `.env`, data, dashboard, dan pengguna
tetap. Tidak perlu menghapus versi lama.

| Komputer | Unduh dari Releases | Langkah |
|---|---|---|
| Ada internet | *ALDx terbaru*: `ALDx-Setup.exe` | klik dua kali → Next-Next → Selesai |
| Tanpa internet | *ALDx offline*: `ALDx-Setup-Offline.exe` + semua `ALDx-Setup-Offline-*.bin` (satu folder) | klik dua kali `ALDx-Setup-Offline.exe` → Next-Next |

Lalu buka ALDx dan tekan `Ctrl + F5`. Versi baru terlihat di kaki halaman login (mis. `v2026.11.13.3`). Jangan
memakai `ALDx-HapusTotal.exe` untuk memperbarui: itu menghapus semua data.

### Menyamakan versi di komputer lain

1. **Dengan git (paling pasti):** di PowerShell, di folder instalasi jalankan
   `Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1`
   (folder hasil Setup.exe: tambah `-JadikanGit` sekali untuk menjadikannya folder git; `.env` & data tidak disentuh). Skrip ini mengambil versi terbaru,
   menerapkannya ke Docker, memperbarui menu & izin, lalu menjalankan uji. Data & pengaturan dipertahankan.
   Tambah `-KomitInstaller -Terbitkan` untuk sekalian menerbitkan installer baru ke Releases (pengembang).
   Cara manual langkah demi langkah (termasuk memilih/kembali ke versi tertentu): [README › Pasang & perbarui dengan git](../README.md#pasang--perbarui-dengan-git-tanpa-exe).
2. **Dengan Setup.exe:** pastikan exe di Releases dibangun **setelah** perubahan terakhir, lalu jalankan di atas
   instalasi lama (folder sama, data dipertahankan).
3. **Tanpa internet:** pakai installer offline (lihat tabel di atas), atau salin folder instalasi dari komputer yang
   sudah terbaru (tanpa `.env` dan `backup\`), lalu jalankan `PASANG.cmd`.

Setelah memperbarui, ikuti bagian *Perlu dilakukan setelah memperbarui* di [catatan versi](31-catatan-versi.md), lalu muat ulang browser
dengan `Ctrl + F5`.

## 2. Menghapus ALDx

| Cara | Untuk | Yang tersisa |
|---|---|---|
| Settings › Apps › ALDx › **Uninstall**, pilih *hapus data* = **Tidak** | pasang ulang / perbaikan | data (volume Docker) & `.env`: kembali saat dipasang ulang ke folder yang sama |
| Settings › Apps › ALDx › **Uninstall**, pilih *hapus bersih* = **Ya** | berhenti memakai di komputer ini | **tidak ada**, kecuali cadangan di *Dokumen\ALDx-cadangan-…* (sama dengan hapus total) |
| **Hapus total** (`scripts\hapus-total.ps1`) | komputer bersih sepenuhnya, mis. sebelum dipindah ke orang lain | **tidak ada**, kecuali cadangan di folder yang Anda pilih |

## 3. Hapus total (uninstall bersih)

Tiga cara, hasilnya sama:

| Cara | Kapan dipakai |
|---|---|
| **ALDx-HapusTotal.exe** (Releases, satu berkas 2 MB) | paling mudah; juga bila folder ALDx sudah terhapus, Settings › Apps rusak, atau ALDx dipasang dari git/ZIP. Klik dua kali › pilih folder ALDx (terisi otomatis) › **Hapus** |
| Menu Start › ALDx › **Hapus total (bersih)** | ALDx dipasang dengan Setup.exe |
| PowerShell (di bawah) | otomatisasi / pilihan lanjutan |

Bila folder ALDx sudah tidak ada, data tidak bisa dicadangkan, tetapi container, image, volume, Kubernetes, dan jejak
Windows ALDx tetap dibersihkan (dicari dari namanya).

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File D:\ALDXsuperset\scripts\hapus-total.ps1
```

Nyalakan **Docker Desktop** dulu. Skrip menampilkan ringkasan, lalu meminta Anda mengetik `HAPUS`.

| Langkah | Yang dikerjakan |
|---|---|
| 1. Cadangan | metadata (termasuk hierarki, gambar dashboard, filter global & ulasan), isi ALDx Engine, dan `.env` disalin ke **Dokumen\ALDx-cadangan-&lt;waktu&gt;** (di luar folder instalasi). **Cadangan gagal → berhenti, tidak ada yang dihapus** |
| 2. Docker | container, volume data (`sps_metadb_pg`, `sps_engine`), jaringan, dan image ALDx |
| 2b. Kubernetes | bila ada cluster yang menyala (mis. Kubernetes Docker Desktop): namespace `aldx*` dan objek berlabel `app.kubernetes.io/part-of=aldx`. ALDx sendiri tidak memakai Kubernetes, jadi biasanya tidak ada yang dihapus |
| 3. Windows | tugas terjadwal cadangan, sertifikat HTTPS ALDx yang dipercayai, pintasan Desktop & menu Start, entri di Settings › Apps |
| 4. Folder | folder instalasi dihapus beberapa detik setelah jendela tertutup |

**Tidak disentuh:** Docker Desktop, Ollama / LM Studio, project Docker lain, dan cache build Docker. Cache build bisa
dibersihkan manual dengan `docker builder prune` (perintah ini juga menghapus cache project lain).

### Pilihan

| Pilihan | Guna |
|---|---|
| `-Simulasi` | **coba dulu**: tampilkan semua jejak ALDx yang akan dihapus, tanpa menghapus apa pun |
| `-SimpanCadangan D:\Arsip\ALDx` | lokasi cadangan lain (mis. flashdisk / NAS) |
| `-SimpanFolder` | hapus semuanya kecuali folder instalasi (untuk memasang ulang bersih dari folder yang sama) |
| `-TanpaCadangan` | tanpa cadangan; **data hilang permanen** |
| `-Ya` | tanpa pertanyaan (untuk otomatisasi) |
| `-Akar D:\superset` | folder ALDx bila skrip dijalankan dari tempat lain (dipakai ALDx-HapusTotal.exe) |

Kode keluar: `0` berhasil · `1` dibatalkan · `2` Docker Desktop tidak menyala · `3` cadangan gagal (tidak ada yang dihapus).

### Memulihkan di komputer lain

1. Pasang ALDx baru (bagian 1).
2. Salin `env-RAHASIA.env` dari folder cadangan menjadi `.env` di folder instalasi **sebelum** memulihkan:
   password koneksi dan key AI dienkripsi dengan `SUPERSET_SECRET_KEY` di dalamnya.
3. Pulihkan:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -Pulihkan <folder cadangan>\metadb-<waktu>.dump
   powershell -ExecutionPolicy Bypass -File scripts\cadangkan.ps1 -PulihkanEngine <folder cadangan>\engine-<waktu>.zip
   ```
