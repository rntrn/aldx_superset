# 04 · Troubleshooting

Tabel pesan galat. Untuk **urutan memeriksa** per gejala (web tidak terbuka, login gagal, lambat),
ikuti pohon keputusan di [19-runbook-faq-admin.md §4](19-runbook-faq-admin.md#4-mencari-penyebab-gangguan-pohon-keputusan).

Langkah pertama selalu: `scripts\logs.ps1`, cari baris `Error`.
Untuk laporan lengkap (status, user, jaringan AD, log): `scripts\diagnose.ps1` → `diagnosa.txt`.
Setiap percobaan login tercatat di log sebagai `ALDx login ... BERHASIL/GAGAL`.

| Gejala / pesan | Penyebab | Solusi |
|---|---|---|
| `powershell : The term 'powershell' is not recognized` saat menjalankan perintah `powershell -ExecutionPolicy Bypass -File scripts\...` | folder Windows PowerShell tidak tercantum di PATH komputer itu (PowerShell tetap ada) | ganti `powershell` dengan `pwsh` (PowerShell 7) atau jalur lengkap `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`. Pintasan, `PASANG.cmd`, uninstall & jadwal cadangan ALDx sudah memakai jalur lengkap sejak 2026.11.10 |
| Inno Setup: `EndUpdateResource failed ... excluding the Output folder from your antivirus` | antivirus memindai exe yang sedang ditulis | `buat-installer.ps1` mencoba ulang otomatis 3 kali; bila tetap gagal, kecualikan folder `installer\setup\Output` di antivirus. Potongan exe yang gagal dihapus otomatis |
| SQL Lab: `Syntax error ... Expected end of query` (ClickHouse code 62), `ORA-00936`, atau galat sintaks dengan **dua `SELECT`** di editor | tabel diseret dari pohon kiri ke editor yang sudah berisi `SELECT * FROM`; Superset menyisipkan kueri lengkap `SELECT ... LIMIT 100` | Sejak 2026.11.10 ALDx otomatis mengganti sisipan setelah `FROM`/`JOIN` dengan nama tabel saja (muat ulang `Ctrl + F5`). Kueri lama: hapus bagian `SELECT * from` di depan, atau seret tabel ke editor kosong |
| Login: "Akun dikunci sementara karena terlalu banyak salah password" | 5 kali salah password berturut-turut | Tunggu (bawaan 15 menit) atau minta Admin: Pusat Kendali › Riwayat › Buka kunci. Darurat: `scripts\buka-kunci.ps1 -Akun <email/username>` |
| Impor `.aldx`: "Peran Anda tidak boleh memuat data dari berkas" | Pengaturan *Peran yang boleh memuat data* (bawaan Admin) | Hilangkan centang *Pakai data di berkas* (impor definisi saja), atau Superadmin menambah peran di Pengaturan › Batas data |
| `running scripts is disabled on this system` | Kebijakan PowerShell | Jalankan skrip dengan `powershell -ExecutionPolicy Bypass -File ...` |
| `docker: command not found` / `cannot connect to the Docker daemon` | Docker Desktop belum menyala | Buka Docker Desktop, tunggu status **Running** |
| `start.ps1`: "Metadata masih di MySQL XAMPP / MariaDB" | instalasi lama belum dipindah ke PostgreSQL | jalankan `PASANG.cmd` atau `scripts\pindah-metadata.ps1` (XAMPP harus menyala) |
| Browser `refused to connect`, `superset` terus `Restarting` | `metadb` belum sehat / RAM habis | `docker compose ps`; `docker compose logs --tail 50 metadb`; naikkan RAM Docker |
| `could not translate host name "metadb"` / `Connection refused` ke metadb | container metadb mati | `docker compose up -d metadb`, tunggu *healthy* |
| `password authentication failed for user "superset"` | `METADB_PASSWORD` di `.env` diubah setelah volume dibuat | kembalikan nilai lama, atau ganti password di PostgreSQL ([14](14-akun-dan-akses.md)) |
| Tab Ekstrak: "ALDx Engine Mati" / `HTTPConnectionPool(host='engine'...)` | container engine mati / RAM kurang | `docker compose up -d engine`; `docker compose logs engine`; naikkan RAM ALDx Engine ([13](13-sps-engine-ekstrak.md#6-masalah-umum)) |
| `uji.ps1`: Backgrounder tidak menjawab | `superset-worker` mati | `docker compose restart superset-worker` |
| Peta titik tanpa latar peta | browser tidak bisa mengambil ubin OpenStreetMap | normal di jaringan tertutup; isi `SPS_PETA_UBIN` ([17 §3.3](17-katalog-chart-peta-prediksi.md#33-peta-titik--kepadatan)) |
| Installer: port dipakai program lain | aplikasi lain memakai 5433/8124/6379 | tutup program itu, atau ubah `METADB_PORT_HOST`/`ENGINE_PORT_HOST` di `.env` |
| `No module named 'psycopg2'` / driver lain | Image lama tanpa driver | `docker compose build` lalu `scripts\start.ps1` |
| Saat build: `invalid peer certificate: UnknownIssuer` / `CERTIFICATE_VERIFY_FAILED` | Jaringan kantor (SSL inspection) memblokir pypi.org dari dalam Docker | Pasang driver offline: file `.whl` di `docker\wheels\` (lihat README di folder itu) |
| Pindah metadata gagal di tengah | sumber lama mati / koneksi terputus | perbaiki penyebab di log, jalankan ulang `PASANG.cmd` (aman diulang: sumber hanya dibaca) |
| Login LDAP: "Invalid login" padahal password benar | Container tidak menjangkau AD, atau username tidak ditemukan di `LDAP_SEARCH_BASE` | Jalankan `scripts\test-ldap.ps1` dan baca pesannya. Pastikan VPN/jaringan kantor tersambung |
| test-ldap: `tidak bisa dihubungi` | Port LDAP (389, atau 636 untuk `ldaps://`) ke server AD tidak terjangkau dari Docker | Cek dari Windows: `Test-NetConnection <server-AD> -Port 636` (atau `scripts\diagnose.ps1`). Bila Windows bisa tapi Docker tidak, restart Docker Desktop setelah VPN tersambung |
| test-ldap: `ditemukan 0 data` / `2 data` | Pencarian pengguna tidak tepat satu | Periksa `LDAP_SEARCH_BASE`; username harus unik |
| Tidak bisa login sama sekali (LDAP mati) | VPN/AD tidak tersedia | Login dengan akun lokal `admin` (lihat `AUTH_LOCAL_USERS`) |
| Halaman login tampil rusak / tanpa gaya | berkas tema tidak termuat | buka `/login/?klasik=1`; Ctrl+F5; cek [09](09-identitas-tema.md) |
| Hubungkan data: *Driver belum terpasang* | image lama | `docker compose build` lalu `scripts\start.ps1` |
| `Role 'X' (LDAP_DEFAULT_ROLE) tidak ada` | Nama role salah | Pakai `Gamma`, `Alpha`, atau `Admin` (huruf besar-kecil berpengaruh) |
| Oracle: `DPY-3010` / *not supported by python-oracledb in thin mode* | Server Oracle di bawah 12.1 | Pasang Instant Client Linux di `docker\oracle\` (lihat README di sana), lalu `docker compose build` dan `scripts\start.ps1` |
| Build: gagal di `apt-get` / `libaio` | Jaringan memblokir repositori Debian | Unduh `libaio*.deb` via browser ke `docker\oracle\` (link di README folder itu) |
| Oracle: `DPI-1047: Cannot locate a 64-bit Oracle Client library` | Zip Instant Client salah (Windows/32-bit) atau rusak | Pakai **Linux x86-64**, Basic Package, versi 19 |
| Oracle/ClickHouse: *timed out* / `DPY-6005` | Server DB tidak terjangkau dari Docker | Pastikan VPN tersambung; cek dari Windows: `Test-NetConnection HOST -Port PORT` |
| Pengguna tidak melihat data apa pun | aturan RLS tidak cocok / (profil pengguna aktif) profil tidak ditemukan atau tidak cocok aturan `akses.yaml` | cek Settings → Row Level Security; bila profil aktif: log `ALDx akses <username>`, lalu `docs\08-hak-akses-data.md` |
| `'sps_akses' is undefined` | Konfigurasi lama | `docker compose restart` |
| Logo/warna tidak berubah | perubahan identitas belum menyebar / cache browser | tunggu 1 menit lalu Ctrl+F5 |
| `Forbidden` saat buka dashboard | role pengguna tidak diberi akses dashboard itu | atur di dashboard → *Edit properties → Roles*, atau Settings → List Users |
| `Variabel 'X' wajib diisi di file .env` | Nilai di `.env` kosong | Isi variabel tersebut |
| `port is already allocated` (8088) | Port dipakai aplikasi lain | Ganti `SUPERSET_PORT` di `.env`, mis. `8089` |
| Login gagal walau password benar | Admin belum terbuat | `docker compose run --rm superset superset fab reset-password --username admin --password PASSWORD_BARU` |
| Asisten AI: menu tidak muncul / model tidak terhubung | Izin belum dibuat / Ollama mati / key belum diisi | Panel AI › **Sambungkan AI**; tabel masalah di [`28-sambungkan-asisten-ai.md`](28-sambungkan-asisten-ai.md#6-masalah-umum) |
| Studio Visual (grafik, dashboard, persiapan data) | Lihat tabel masalah di [`12-studio-visual.md`](12-studio-visual.md#6-masalah-umum) | |
| Pusat Kendali / gateway 502 / antrean / node | Lihat tabel masalah di [`11-pusat-kendali-server.md`](11-pusat-kendali-server.md#10-masalah-umum) | |
| Halaman web lambat saat pertama dibuka | Superset masih memuat | Tunggu 1–2 menit |
| SQL Lab / Kueri Visual / simpan dataset Oracle: `ORA-00933 SQL command not properly ended` | Oracle 11g tidak mengenal `FETCH FIRST n ROWS` | diperbaiki di versi ini (batas `ROWNUM`, `config/sps_dialek.py`); `docker compose restart superset superset-worker` |
| Kueri Visual Oracle: `ORA-00942 table or view does not exist` | nama ditulis dengan kutip huruf kecil | diperbaiki: nama ditulis sesuai aturan Oracle; pastikan skema yang dipilih benar |
| "Buka di SQL Lab" → `502 Bad Gateway` | kueri panjang di alamat URL | diperbaiki: lewat tautan permanen SQL Lab + buffer gateway lebih besar (`scripts\terapkan-server.ps1`) |
| Chart Tree/Graph/Sankey membuat halaman *Unresponsive* | puluhan ribu simpul digambar browser | dibatasi otomatis (Pusat Kendali → Pengaturan → *Baris maksimal chart berat*, bawaan 1.000); kecilkan *Row limit* |
| Kolom angka Oracle tampil bertanda `?` | tipe `NUMBER` tidak dikenali | diperbaiki: `NUMBER/FLOAT` dikenali sebagai angka |
| Daftar skema berisi ratusan nama | semua skema database tampil | Hubungkan data → Koneksi tersimpan → **Atur skema** ([06 §2a](06-sumber-data.md)) |
| Impor berkas: *"Berkas dikunci kunci server lain (atau diubah)"* | berkas dibuat server lain dengan kunci server | minta pembuat mengunci dengan **kata sandi**, atau samakan `SPS_KUNCI_BERKAS` di `.env` kedua server ([25](25-berkas-filter-global-ulasan.md)) |
| Impor berkas: *"Kata sandi salah, atau berkas telah diubah"* | sandi keliru / berkas rusak saat dikirim | ketik ulang sandi (huruf besar/kecil berpengaruh); minta berkas dikirim ulang |
| Impor berkas: *"Pilih koneksi tujuan..."* | koneksi asal tidak ada di server ini | pilih koneksi yang berisi tabel sama, atau pakai `.aldx` berisi data |
| Filter global tidak berlaku di satu dashboard | dashboard itu tidak punya filter *pilihan* di kolom bernama sama | tambahkan filter native (Value) di kolom itu pada dashboard |
| Komentar tidak terlihat rekan | menunggu persetujuan Superadmin | Superadmin: Kelola → Moderasi ulasan → Tampilkan |

## Mulai ulang dari nol

⚠️ Semua dashboard, chart, user lokal, dan ekstrak akan hilang. Cadangkan dulu bila ragu.
```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
docker compose down
docker volume rm sps_metadb_pg sps_engine
```
Lalu jalankan `PASANG.cmd` lagi.
