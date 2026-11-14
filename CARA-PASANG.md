# Cara Memasang ALDx

Panduan ini untuk siapa saja, tidak perlu paham pemrograman. Ada **3 bagian**:
**A** dikerjakan tim TI sekali saja, **B** (atau **C**) dikerjakan pengguna biasa.
Waktu: ± 30–60 menit untuk pemasangan pertama (sebagian besar menunggu unduhan).

---

## A. Persiapan komputer (tim TI, sekali saja, butuh hak admin)

1. Komputer: **Windows 10/11 64-bit** atau Windows Server 2019+, RAM minimal **8 GB** (disarankan 16 GB),
   ruang disk kosong minimal **40 GB**.
2. Pasang **Docker Desktop** dari <https://www.docker.com/products/docker-desktop/>
   (pilih *Use WSL 2*). Mulai ulang komputer bila diminta.
3. Masukkan akun pengguna yang akan memakai ALDx ke grup **docker-users**:
   klik kanan Start › *Computer Management* › *Local Users and Groups* › *Groups* › **docker-users** ›
   *Add…* › ketik nama akun › OK. Lalu pengguna itu **keluar (sign out) dan masuk lagi**.
4. Buka Docker Desktop sebagai pengguna itu › ⚙ *Settings* › *Resources*: CPU **4**, Memory **8 GB** › *Apply & restart*.

Setelah ini, langkah B / C **tidak** memerlukan hak admin.

## B. Memasang dengan ALDx-Setup.exe (cara utama)

1. Ambil berkas **`ALDx-Setup.exe`** (± 100 MB):
   dari tim TI (flashdisk / folder jaringan), atau GitHub › **Releases** › **ALDx terbaru** › `ALDx-Setup.exe`.
   Versi tertentu: rilis **ALDx 2026.11.14** (tag `v2026.11.14`). Opsional, memastikan unduhan utuh: cocokkan
   `Get-FileHash ALDx-Setup.exe` dengan `ALDx-SHA256.txt` di rilis yang sama ([docs/29](docs/29-versi-pembaruan-hapus-total.md#versi-yang-bisa-dicocokkan-dengan-rilis-github)).
2. Pastikan **Docker Desktop menyala**: ikon paus di pojok kanan bawah layar diam (tidak bergerak).
3. **Klik dua kali `ALDx-Setup.exe`**. Muncul *"Windows protected your PC"*? Klik **More info** › **Run anyway**.
   Peringatan ini muncul karena Setup belum bertanda tangan digital, bukan karena virus. Agar tidak muncul: salin Setup lewat
   flashdisk/folder jaringan (bukan unduh lewat browser), atau klik kanan › *Properties* › centang **Unblock**.
4. Klik **Lanjut** terus:

| Halaman | Yang dilakukan |
|---|---|
| Selamat datang | **Lanjut** |
| Pilih folder | biarkan `D:\superset` › **Lanjut** |
| Pintasan | biarkan tercentang › **Lanjut** › **Pasang** (menyalin berkas, ± 1 menit) |
| Selesai | biarkan centang *Lanjut ke pengaturan ALDx* › **Selesai** |

5. Wizard pengaturan ALDx terbuka sendiri, hanya **3 langkah**:

| Halaman | Yang dilakukan |
|---|---|
| Pemeriksaan | tunggu semua **OK** › **Lanjut**. Ada **GAGAL**? Lihat tabel masalah di bawah, lalu **Periksa ulang** |
| **Akun Superadmin** | isi **email, nama, password** (minimal 10 karakter, catat baik-baik) › **Lanjut** |
| **Pasang** | klik **Pasang**, tunggu sampai selesai (pertama kali 15–40 menit). Jangan tutup jendelanya |
| Selesai | klik **Buka aplikasi** › login dengan email & password Superadmin |

Halaman **Asisten AI** juga tampil: klik **Lanjut** untuk melewatinya (AI bisa disambungkan setelah terpasang).
Pengaturan lain (nama & logo, port, HTTPS, pengguna lain, login kantor) memakai nilai bawaan dan bisa diubah
kapan saja di **Pusat Kendali**. Ingin mengaturnya saat pasang: centang **Atur pengaturan lanjutan** di halaman Superadmin.

## Setelah terpasang: ikuti kartu "Siapkan ALDx"

Setiap pemasangan otomatis membuat **data contoh** (fiktif) untuk mencoba semua fitur: dua dashboard contoh, data
penjualan harian 2,3 juta baris, database sumber contoh, dan role hak akses contoh. Tidak perlu data kantor dulu.

Di **Beranda**, admin melihat kartu **Siapkan ALDx**: lima langkah (AI, data kantor, pengguna, nama & logo, cadangan)
dengan tombol **Mulai →** yang langsung membuka tempatnya. Semua dokumentasi juga ada di aplikasi: menu **Panduan**.

### Hidupkan Asisten AI (opsional, 5 menit)

1. Di aplikasi, tekan **`Ctrl + I`** (atau ikon ✦ di kanan atas). Layar **Sambungkan Asisten AI** muncul.
2. Pilih salah satu:
   - **Lokal (gratis, data tidak keluar):** pasang [Ollama](https://ollama.com/download), lalu di PowerShell jalankan
     `ollama pull qwen3:4b` dan klik **Periksa lagi**.
   - **Cloud gratis:** klik **Buat key ↗** (mis. Google Gemini atau Groq), salin key-nya, tempel, lalu **Simpan**.
   - **Cloud berbayar:** sama seperti di atas untuk OpenAI, Claude, Grok, atau DeepSeek.
3. Selesai. Tidak perlu restart. Panduan lengkap: [docs/28-sambungkan-asisten-ai.md](docs/28-sambungkan-asisten-ai.md).


**Membuka lagi di lain hari:** klik dua kali ikon **ALDx** di Desktop (Docker Desktop dinyalakan otomatis bila perlu).
Dari komputer lain di jaringan kantor: **http://nama-komputer:8088**.
**Mengubah pengaturan / pasang ulang:** menu Start › ALDx › *Pasang - ubah pengaturan ALDx*.

## B2. Komputer tanpa internet: paket offline

Paket offline berisi semua yang dibutuhkan (± 3 GB), termasuk Docker Desktop: **tidak perlu internet sama sekali**.

1. Ambil **semua** berkas paket: `ALDx-Setup-Offline.exe` **dan** semua `ALDx-Setup-Offline-1.bin`, `-2.bin`, …
   (GitHub › Releases › **ALDx offline**, atau dari tim TI). Simpan di **satu folder** yang sama (mis. flashdisk).
2. Klik dua kali **`ALDx-Setup-Offline.exe`**. Docker Desktop belum ada? Setup menawarkan memasangnya dari paket
   (butuh password admin, lalu mulai ulang komputer dan jalankan Setup lagi).
3. Lanjutkan seperti bagian B langkah 4–5. Di halaman Pemeriksaan, baris *Internet* tertulis **paket offline** (OK).

## Memperbarui ALDx (versi baru)

1. Unduh **ALDx-Setup.exe** terbaru (atau paket offline terbaru), lihat versi di judul rilis (*ALDx terbaru (2026.11.14)*).
   Tiap versi juga punya rilis tetap `v<VERSI>`, mis. untuk memasang ulang versi yang sama di komputer lain.
2. Klik dua kali, pasang ke **folder yang sama**. Data, akun, dan pengaturan tetap ada.
3. Buka aplikasi, tekan **Ctrl + F5**.

Apa yang baru dan langkah tambahan (bila ada): [docs/31 · Catatan versi](docs/31-catatan-versi.md).

## Menghapus ALDx

Settings › **Apps** › ALDx › **Uninstall** (atau menu Start › ALDx › *Hapus ALDx*). Nyalakan Docker Desktop dulu. Ditanya:

| Pilihan | Hasil |
|---|---|
| **Tidak** (bawaan) | program & container dihapus. **Data tetap** (dashboard, pengguna) dan kembali bila ALDx dipasang ulang ke folder yang sama |
| **Ya** | **hapus bersih**: cadangan lengkap dibuat dulu di *Dokumen\ALDx-cadangan-…*, lalu container, image, volume data, jaringan, objek Kubernetes ALDx, sertifikat, tugas terjadwal & seluruh folder ALDx dihapus |
| Batal | tidak jadi |

**Hapus total (komputer bersih sepenuhnya):** unduh **ALDx-HapusTotal.exe** (Releases) lalu klik dua kali, atau menu Start ›
ALDx › **Hapus total (bersih)**. Bisa juga bila folder ALDx sudah terhapus. Data dicadangkan dulu ke
*Dokumen\ALDx-cadangan-…*, lalu container, data, image, sertifikat, pintasan, entri Apps, dan folder ALDx dihapus.
Rinci & cara mencoba dulu (`-Simulasi`): [docs/29](docs/29-versi-pembaruan-hapus-total.md).

**Komputer lain berbeda tampilan/fitur?** Setup.exe membekukan versi saat dibangun; `git pull` selalu terbaru.
Lihat [docs/29 §1](docs/29-versi-pembaruan-hapus-total.md).

Lupa password? Menu Start › ALDx › **Atur ulang password**: ketik email & password baru (kunci akun ikut dibuka).

## C. Cara lain: tanpa Setup.exe (folder / ZIP)

Bila hanya punya folder proyek atau ZIP dari GitHub (**Code › Download ZIP**):

1. **Klik kanan** ZIP › **Extract All…** › isi `D:\` › *Extract*. Ganti nama folder hasil (`aldx_superset-main`) menjadi **`superset`**.
   Folder dari flashdisk: salin seluruhnya ke `D:\superset`. Jangan di Desktop/OneDrive, nama folder tanpa spasi.
2. Buka `D:\superset`, **klik dua kali `PASANG.cmd`** (tidak perlu *Run as administrator*). Wizard sama dengan langkah B.5.

---

## Masalah umum

| Yang terlihat | Penyebab | Yang dilakukan |
|---|---|---|
| Jendela hitam muncul sebentar lalu hilang / tidak terjadi apa-apa | PASANG.cmd dibuka dari dalam ZIP, atau berkas belum lengkap | pakai **ALDx-Setup.exe** (bagian B), atau ekstrak ZIP dulu (bagian C) |
| Setup: *"Docker Desktop belum terpasang"* | Docker belum dipasang | minta TI mengerjakan bagian A. Setup boleh dilanjutkan; jalankan *Pasang - ubah pengaturan ALDx* setelah Docker siap |
| *"PowerShell tidak diizinkan menjalankan skrip"* | kebijakan keamanan kantor | minta TI mengizinkan skrip untuk folder ini, atau memasang **PowerShell 7** (PASANG.cmd otomatis memakainya) |
| Mengetik `PASANG.cmd` di Terminal: *"not recognized"* | Terminal/PowerShell butuh awalan `.\` | lebih mudah: **klik dua kali** dari File Explorer. Atau ketik `.\PASANG.cmd` |
| Dari CMD admin: *"not recognized"* | CMD admin mulai di `C:\Windows\System32` | tidak perlu CMD. Klik dua kali PASANG.cmd. Atau ketik lengkap `D:\superset\PASANG.cmd` |
| Pemeriksaan: **Docker Desktop menyala – GAGAL** | Docker belum menyala, atau akun belum masuk grup docker-users | nyalakan Docker Desktop & tunggu ikon paus diam; bila tetap gagal, minta TI mengerjakan bagian A langkah 3 |
| Pemeriksaan: **Port 8088 dipakai** (Peringatan) | ada program lain di port itu | tidak perlu apa-apa: port bebas lain dipilih otomatis (mis. 8089); ikon ALDx di Desktop ikut menyesuaikan |
| Pemeriksaan: **Internet – peringatan** | pemasangan pertama mengunduh ± 3 GB | sambungkan internet / proxy kantor. Tanpa internet: [docs/18-installer.md §6](docs/18-installer.md) |
| **Pasang** berhenti dengan pesan merah | lihat baris terakhir pesannya | klik **Kembali** bila ada isian salah, lalu **Pasang** lagi (aman diulang). Kirim berkas terbaru di `installer\log\` ke TI bila tetap gagal |
| Pasang gagal: *password authentication failed for user "superset"* | folder ALDx dihapus, tetapi data lama masih ada di Docker | pakai Setup/PASANG versi terbaru: halaman **Data sebelumnya** muncul → pilih *Mulai baru* (data lama dicadangkan dulu) atau *Pakai data lama* |
| Antivirus (CrowdStrike, Defender) menghapus Setup / HapusTotal | Setup baru & belum bertanda tangan digital (salah deteksi) | **jangan matikan antivirus**. Pasang tanpa .exe lewat git: [README › Pasang & perbarui dengan git](README.md#pasang--perbarui-dengan-git-tanpa-exe); atau minta TI mengizinkan hash dari `ALDx-SHA256.txt` ([docs/18](docs/18-installer.md#peringatan-windows--antivirus)) |
| Browser: *"Koneksi tidak pribadi"* | HTTPS dengan sertifikat buatan sendiri | klik *Advanced* › *Proceed*. Agar hilang permanen: [docs/11 §9b](docs/11-pusat-kendali-server.md#https) |
| Password Superadmin ditolak / lupa | salah ketik, Caps Lock, atau akun terkunci setelah 5× salah | menu Start › ALDx › **Atur ulang password** (atau `scripts\atur-password.ps1`). Login dengan **email** (bukan *admin*) |

## Setelah terpasang (untuk admin)

- Belajar memakai: [docs/tutorial/](docs/tutorial/README.md) (Level 1 pengguna sampai Level 4 admin server).
- Cadangan otomatis harian: [docs/19-runbook-faq-admin.md §2.5](docs/19-runbook-faq-admin.md).
- Semua dokumen versi PDF: folder [`docs/pdf/`](docs/pdf/).
