# 29 · Versi Installer, Pembaruan & Menghapus Total

## 1. Tiga cara memasang, bisa beda versi

Installer **membekukan** isi aplikasi pada saat installer itu dibangun. Jadi dua komputer yang dipasang dengan cara
berbeda bisa menjalankan versi yang berbeda.

| Cara memasang | Versi yang terpasang | Kapan versinya diperbarui |
|---|---|---|
| `git clone` / `git pull` / Download ZIP | **selalu terbaru** (cabang `main`) | setiap kali Anda *pull* / unduh ulang |
| **ALDx-Setup.exe** | isi repo **saat exe dibangun** | `installer\setup\buat-installer.ps1` di komputer pengembang, atau GitHub Actions (`setup.yml`) |
| **ALDx-Setup-Offline.exe** + `.bin` | isi repo + image Docker **saat dibangun** | `installer\setup\buat-installer.ps1 -Offline`, atau GitHub Actions (`setup-offline.yml`) |

**Unduhan resmi:** halaman **Releases** repo: *ALDx terbaru* (`ALDx-Setup.exe`, `ALDx-HapusTotal.exe`) dan *ALDx offline*
(`ALDx-Setup-Offline.exe` + `ALDx-Setup-Offline-1.bin` + `ALDx-HapusTotal.exe`). Ukuran berkas di Releases dicocokkan dengan
hasil build sebelum diumumkan.

**Membangun installer terbaru sendiri** (tanpa GitHub Actions), di folder repo:

```powershell
winget install JRSoftware.InnoSetup                                   # sekali
pwsh -File installer\setup\buat-installer.ps1 -Offline                # PowerShell 7
# atau Windows PowerShell: powershell -ExecutionPolicy Bypass -File installer\setup\buat-installer.ps1 -Offline
```

Setelah setiap perbaikan, pengembang menjalankan `pwsh -File installer\setup\terbitkan.ps1`, sehingga installer online
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
| Aplikasi | fitur terbaru terlihat? Versi November 2026: menu **Sematkan ke web lain**, bagian **Objek** di Studio › Susun dashboard, chip filter global di bilah atas. Daftar lengkap: [31 · Catatan versi](31-catatan-versi.md) |
| Folder instalasi | `git log -1 --oneline` (bila dipasang dengan git), atau `scripts\versi.ps1` |
| Paket offline | berkas `offline\versi.txt` (tanggal + kode commit) |

### Menyamakan versi di komputer lain

1. **Dengan git (paling pasti):** di PowerShell, di folder instalasi jalankan
   `Set-ExecutionPolicy -Scope Process Bypass -Force; .\scripts\sinkron-laptop.ps1`
   (folder hasil Setup.exe: tambah `-JadikanGit` sekali untuk menjadikannya folder git; `.env` & data tidak disentuh). Skrip ini mengambil versi terbaru,
   menerapkannya ke Docker, memperbarui menu & izin, lalu menjalankan uji. Data & pengaturan dipertahankan.
   Tambah `-KomitInstaller -Terbitkan` untuk sekalian menerbitkan installer baru ke Releases (pengembang).
   Cara manual: `git pull`, lalu klik dua kali `PASANG.cmd`.
2. **Dengan Setup.exe:** pastikan exe di Releases dibangun **setelah** perubahan terakhir, lalu jalankan di atas
   instalasi lama (folder sama, data dipertahankan).
3. **Tanpa internet:** salin folder instalasi dari komputer yang sudah terbaru (tanpa `.env` dan `backup\`), lalu
   jalankan `PASANG.cmd`.

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
