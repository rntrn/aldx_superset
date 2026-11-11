# Skenario Uji (UAT) ALDx

Dihasilkan dari `skenario.py`. Isi hasilnya di **`lembar-uji.xlsx`**.

Total **133 skenario**. Prioritas *Tinggi* wajib lulus sebelum dipakai pengguna.

## Uji asap (± 15 menit)

Setelah instalasi/upgrade, jalankan `scripts\uji.ps1` lalu skenario bertanda **asap**: A01, A02, B01, B09, C01, D01, D07, D11, E04, F04, F12, G01, G07, J01, J05.

## A. Instalasi & perawatan

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| A01 | 4 Admin server | Tinggi/asap | Instalasi baru dengan PASANG.cmd | Docker Desktop menyala, folder di D:\superset | Klik dua kali PASANG.cmd, isi password admin, lewati isian opsional, klik Pasang | Semua langkah selesai; halaman Selesai menampilkan alamat; browser membuka halaman login |
| A02 | 4 Admin server | Tinggi/asap | Uji otomatis | A01 | Jalankan scripts\uji.ps1 | 55/55 LULUS, kode keluar 0 |
| A03 | 4 Admin server | Tinggi | Pemeriksaan prasyarat menolak kondisi tidak layak | Docker Desktop DIMATIKAN | Jalankan PASANG.cmd | Baris 'Docker Desktop menyala' GAGAL, tombol Lanjut nonaktif; setelah Docker dinyalakan & Periksa ulang: OK |
| A04 | 4 Admin server | Tinggi | Pindah metadata lama ke PostgreSQL | Instalasi lama (MYSQL_HOST=host.docker.internal + XAMPP menyala, atau MariaDB) | Jalankan PASANG.cmd, centang Pindahkan data | Dashboard, chart, user, koneksi lama tampil di versi baru; .env METADB_JENIS=postgres; upload lama terbaca dari ALDx Engine |
| A05 | 4 Admin server | Tinggi | Instalasi ulang tidak menghapus data | A01 + ada chart buatan sendiri | Jalankan PASANG.cmd lagi (password admin dikosongkan) | Selesai tanpa galat; chart tetap ada; password admin tidak berubah |
| A06 | 4 Admin server | Tinggi | Cadangan & pemulihan metadata | A01 | scripts\cadangkan.ps1 → hapus 1 chart → scripts\cadangkan.ps1 -Pulihkan backup\metadb-<terbaru>.dump | Chart yang dihapus kembali |
| A07 | 4 Admin server | Sedang | Cadangan & pemulihan ALDx Engine | Ada data latihan | scripts\cadangkan.ps1 -Engine → -PulihkanEngine backup\engine\engine-<terbaru>.zip | Berkas .zip terbentuk; setelah pemulihan dataset latihan tetap bisa dibuka |
| A08 | 4 Admin server | Sedang | Versi komponen | A01 | scripts\versi.ps1 | Kolom Diminta = Berjalan untuk Superset, PostgreSQL, ClickHouse, Redis, nginx |
| A09 | 4 Admin server | Sedang | Restart komputer | A01 | Restart Windows, buka Docker Desktop, tunggu 3 menit | Semua container menyala sendiri; uji.ps1 LULUS |
| A10 | 4 Admin server | Sedang | Data latihan | A01 | scripts\data-latihan.ps1 dua kali | Dataset latihan_penjualan (4.320 baris), latihan_lokasi_pelanggan (1.500) & latihan_cabang (6) ada, tidak berganda; dashboard latihan ada |
| A11 | 4 Admin server | Tinggi | Urutan menyala setelah Docker mati | A01 | Quit Docker Desktop → buka lagi → ikuti 19-runbook §2.1 | Semua container healthy tanpa perintah tambahan; uji.ps1 LULUS |
| A12 | 4 Admin server | Sedang | Simulasi gangguan engine | A01 | docker compose stop engine → ikuti pohon keputusan 19-runbook §4 → perbaiki | Penyebab ditemukan dari docker compose ps; setelah start engine + restart worker, uji.ps1 LULUS |
| A13 | 4 Admin server | Tinggi | Instalasi baru netral + akun lokal | Komputer tanpa instalasi SPS | PASANG.cmd → Login & pengguna: Akun lokal → isi 2 baris (peran Pengguna & Analis) → Pasang | Login akun baru berhasil; Settings → List Users: peran sesuai (Analis punya sql_lab); tidak ada koneksi selain ALDx Engine; LDAP_SERVERS kosong; password tidak ada di .env & log |
| A14 | 4 Admin server | Sedang | Instalasi dengan LDAP | Server LDAP uji terjangkau | PASANG.cmd → Login & pengguna: LDAP → isi server, domain, search base, admin LDAP → Uji koneksi → Pasang | Uji koneksi OK; .env LDAP_* terisi; login username jaringan berhasil; admin lokal tetap bisa login |
| A15 | 4 Admin server | Sedang | Berkas lisensi ikut terpasang | A01 | Buka folder instalasi (mis. D:\superset); buka LICENSE, NOTICE, THIRD-PARTY-LICENSES.md | Ketiga berkas ada; LICENSE = Apache License 2.0; NOTICE menyebut ALDx & Apache Superset; tidak ada logo instansi di branding\ |

## B. Login & sesi

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| B01 | 1 Pengguna | Tinggi/asap | Login akun pengguna | Akun lokal dibuat admin (atau LDAP aktif) | Buka alamat aplikasi, login dengan akun pengguna | Masuk ke halaman depan sesuai Identitas & Tema; nama pengguna tampil di menu |
| B02 | 1 Pengguna | Tinggi | Login admin lokal saat LDAP tidak terjangkau | Putus VPN/LDAP | Login dengan akun admin lokal | Berhasil masuk |
| B03 | 1 Pengguna | Tinggi | Password salah | – | Login dengan password salah | Pesan gagal; tidak masuk |
| B04 | 1 Pengguna | Sedang | Batas percobaan login | – | Coba login salah lebih dari batas per menit (Pusat Kendali → Gateway) | Ditolak sementara (HTTP 429), normal kembali setelah 1 menit |
| B05 | 1 Pengguna | Sedang | Akun LDAP terdaftar otomatis | LDAP aktif; pengguna login pertama kali | Admin cek Settings → List Users | User terdaftar dengan role LDAP_DEFAULT_ROLE + SPS_ROLE_PENGGUNA (+ role "Akses …" bila profil pengguna aktif) |
| B06 | 1 Pengguna | Rendah | Keluar | B01 | Menu Settings → Log out | Kembali ke halaman login; tombol Back tidak membuka data |
| B07 | 1 Pengguna | Sedang | Halaman login beranimasi | – | Buka /login/; lalu aktifkan Windows 'Show animations' = Off dan muat ulang; buka /login/?klasik=1 | Nama, logo & warna perusahaan tampil, latar bergerak; dengan animasi Off latar diam; ?klasik=1 menampilkan login bawaan |
| B08 | 1 Pengguna | Tinggi | Menu mengikuti alur & hak akses | Akun Pengguna, Analis, Admin | Login bergantian, buka menu navbar | Sidebar urut Data › Kueri › Visual › Dashboard & Story, sama di semua halaman; tidak ada item ganda; Pengguna tanpa menu Kueri; Analis punya Kueri Visual & SQL Lab; hanya Admin melihat Hubungkan data & Ekstrak |
| B09 | 1 Pengguna | Tinggi/asap | Cangkang aplikasi & Beranda | B01 | Login; buka beberapa menu kiri; buka /dashboard/list/ langsung di tab baru | Beranda tampil dengan Cari, 5 kartu Bangun laporan (jumlah benar), Lanjutkan, Dashboard; semua halaman tampil di cangkang tanpa navbar ganda; alamat lama dialihkan ke /app/?p=... |
| B10 | 1 Pengguna | Sedang | Cari & pintasan keyboard | B09 | Ctrl + K, ketik 'latihan', Enter; tekan ? ; tekan g lalu d; Ctrl + \ | Palet menemukan dashboard/chart/dataset; panel Cara pakai sesuai halaman (berisi pintasan); g d membuka Daftar dashboard; sidebar ringkas/lebar |
| B11 | 1 Pengguna | Sedang | Ganti bahasa | B09 | Kiri bawah → Bahasa → English, lalu 日本語, lalu Bahasa Indonesia | Menu, Beranda, Studio, panel bantuan berganti bahasa; halaman Superset ikut (EN/JA asli, ID kamus SPS); nilai data tidak berubah |
| B12 | 1 Pengguna | Sedang | Tampilan ponsel | Ponsel / jendela ≤ 760 px | Login dari ponsel; buka Beranda, Daftar dashboard, satu dashboard, menu Lainnya | Bilah tab bawah tampil; laci menu terbuka; tidak ada geser horizontal di Beranda; dashboard terbaca |
| B13 | 1 Pengguna | Tinggi | Panel Asisten AI di setiap halaman | Model AI aktif; akun Pengguna | Di Daftar dashboard tekan Ctrl + I → klik contoh 'Penjualan per cabang tahun ini?'; ketik /panduan cara membuat story | Panel terbuka di kanan (ponsel: layar penuh); jawaban + tabel sesuai hak akses; /panduan menjawab dari isi Cara pakai; hanya peran yang boleh yang tampil |
| B14 | 1 Pengguna | Sedang | Ekspor tabel & grafik | B13 atau Kueri Visual/Studio | Arahkan kursor ke tabel jawaban → Ekspor → Excel, CSV, Teks, Gambar, PDF / cetak, Salin tabel | Berkas terunduh bernama <judul>_<tanggal>; Excel berisi angka (bisa dijumlah); PDF lewat dialog cetak; isi = data di layar |

## C. Dashboard (Level 1)

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| C01 | 1 Pengguna | Tinggi/asap | Membuka dashboard latihan | A10, B01 | Dashboards → cari 'latihan' → buka | 8 chart tampil tanpa galat dalam < 10 detik |
| C02 | 1 Pengguna | Tinggi | Filter dashboard | C01 | Filter Kategori = Kesehatan & Kecantikan → Apply filters | Total penjualan berubah menjadi ± 53.8B; semua chart penjualan tersaring |
| C03 | 1 Pengguna | Sedang | Klik-filter | C01 | Klik potongan Elektronik di pie | Chart lain tersaring ke Elektronik; klik lagi membatalkan |
| C04 | 1 Pengguna | Sedang | Unduh CSV & gambar | Role punya kemampuan Unduh | ⋮ → Download → Export to .CSV, lalu Download as image | Berkas CSV & PNG terunduh |
| C05 | 1 Pengguna | Sedang | Angka singkat & tooltip | C01 | Arahkan kursor ke batang Cabang Jakarta | Tooltip menampilkan nilai lengkap ± 234 miliar |
| C06 | 1 Pengguna | Sedang | Asisten AI menjawab | Model AI dikonfigurasi, role diizinkan | Tanya: 'total penjualan per cabang tahun 2025' | Jawaban berupa tabel/grafik; angka Cabang Jakarta 2025 ± 91,0 miliar |
| C07 | 1 Pengguna | Rendah | Favorit | C01 | Klik bintang di judul dashboard | Dashboard muncul di Home → Favorites |

## D. Studio Visual (Level 2)

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| D01 | 2 Analis | Tinggi/asap | Chart batang seret-lepas | Role analis | Studio → latihan_penjualan → nm_cabang ke Kolom, total ke Baris | Batang 6 cabang; Jakarta tertinggi; rekomendasi Batang berbingkai emas |
| D02 | 2 Analis | Tinggi | Warna bertumpuk | D01 | kategori ke Warna | Batang bertumpuk 5 warna palet SPS; legenda tampil |
| D03 | 2 Analis | Tinggi | Filter lembar | D01 | saluran ke Filter → centang Online → Terapkan | Angka berkurang; pil filter tampil |
| D04 | 2 Analis | Sedang | Ganti agregasi | D01 | Klik pil SUM(total) → Rata-rata | Pil menjadi AVG(total), grafik berubah |
| D05 | 2 Analis | Sedang | Tukar, urutkan, lihat data, label | D01 | Klik Tukar, Urutkan, Lihat data; centang Tampilkan nilai | Batang mendatar; terurut; tabel muncul; nilai tertulis |
| D06 | 2 Analis | Tinggi | 23 jenis chart | A10 | Ikuti contoh di 17-katalog-chart-peta-prediksi.md untuk setiap jenis | Semua 23 jenis tergambar di Studio tanpa galat |
| D07 | 2 Analis | Tinggi/asap | Simpan & buka di Explore | D02 | Judul → Simpan → Buka di Explore | Chart Superset tampil sama (warna, tumpukan) tanpa peringatan 'not up to date' |
| D08 | 2 Analis | Sedang | Buka kembali lembar tersimpan | D07 | Panel kanan → Lembar kerja tersimpan → klik | Rak & pilihan kembali seperti saat disimpan |
| D09 | 2 Analis | Tinggi | Susun dashboard | ≥ 2 chart tersimpan | Tab Dashboard → seret 2 chart → atur lebar → Tambah filter nm_cabang → Simpan | Dashboard tampil di menu Dashboards dengan filter Cabang yang bekerja |
| D10 | 2 Analis | Sedang | Tanpa izin simpan | Akun role Gamma | Buat chart di Studio → Simpan | Tidak tersimpan; muncul tautan Explore & pesan izin |
| D11 | 2 Analis | Tinggi/asap | Kueri Visual: klik dua kali | Peran Analis | Kueri → Kueri Visual → pilih database & skema → klik dua kali latihan_penjualan | Hanya tabel skema terpilih yang tampil; kueri langsung dijalankan, 1.000 baris pertama tampil |
| D12 | 2 Analis | Tinggi | Kueri Visual: gabung otomatis & ringkas | D11 | Klik dua kali latihan_lokasi_pelanggan lalu latihan_cabang → kolom pulau, Jumlah belanja, Hitung id_pelanggan → Jalankan | Pesan hijau 'Digabung otomatis … kd_cabang'; Jawa ± Rp18,6 miliar dengan 1.106 pelanggan |
| D13 | 2 Analis | Sedang | Kueri Visual → dataset → Studio | D12; kemampuan Kelola dataset | Isi nama belanja_per_pulau → Simpan jadi dataset → Buat chart di Studio Visual | Dataset tersimpan; Studio terbuka dengan dataset itu terpilih |
| D14 | 2 Analis | Sedang | Pratinjau Auto Chart sesuai jenis | Ada model AI aktif | Asisten AI → Auto Chart → latihan_penjualan → Analisis → ganti jenis kartu pie ke batang | Pratinjau pie berupa lingkaran berlegenda; setelah diganti menjadi batang; tidak ada saran kembar kode/nama cabang |
| D15 | 2 Analis | Sedang | Menu Asisten AI hanya bila model aktif | LM Studio/Ollama terpasang | Matikan server model, tunggu 1 menit, muat ulang; nyalakan lagi, tunggu 1 menit, muat ulang | Saat mati menu Asisten AI hilang (Story tetap di Dashboard & Story); saat menyala menu & model muncul |
| D16 | 2 Analis | Sedang | Story hanya dashboard selesai | Ada dashboard draf kosong milik orang lain | Dashboard & Story → Story → Story baru → buka pilihan dashboard | Hanya dashboard berisi chart yang terbit atau milik sendiri (ditandai draf) yang tampil |
| D17 | 2 Analis | Tinggi | Chart berat tidak membuat browser macet | Dataset ≥ 10.000 baris | Explore → Tree Chart (atau Graph/Sankey) → isi Id & Parent → Update chart | Data dibatasi 1.000 baris (Pusat Kendali → Baris maksimal chart berat); halaman tetap responsif; petunjuk Explore tampil |

## E. Peta & analitik prediktif

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| E01 | 2 Analis | Tinggi | Peta titik | A10 | latihan_lokasi_pelanggan → lon ke Kolom, lat ke Baris, saluran ke Warna | Rekomendasi Peta titik; titik di 6 wilayah Indonesia, warna per saluran |
| E02 | 2 Analis | Tinggi | Peta provinsi | A10 | provinsi ke Kolom, belanja ke Baris | Rekomendasi Peta provinsi; DKI Jakarta paling gelap; legenda nilai tampil |
| E03 | 2 Analis | Sedang | Peta di Superset | E01–E02 disimpan | Buka chart di Explore | Peta provinsi (Indonesia) & peta titik deck.gl tampil; titik tampil walau ubin peta tidak termuat |
| E04 | 2 Analis | Tinggi/asap | Ramalan | A10 | periode ke Kolom, total ke Baris → centang Ramalan 6 | Garis putus-putus 6 bulan + pita 80/95%; keterangan 'Holt-Winters (musiman 12)' |
| E05 | 2 Analis | Tinggi | Tren & anomali | E04 | Centang Garis tren & Tandai anomali | Garis tren titik-titik; satu titik merah di Maret 2025 |
| E06 | 2 Analis | Tinggi | Ramalan tersimpan ke dashboard | E04 | Simpan → buka di Explore | Chart garis berisi seri Aktual, Ramalan, batas 80%/95%, Tren; pesan 'diperbarui otomatis tiap hari' |
| E07 | 2 Analis | Tinggi | Ramalan mengikuti lingkup akses | Dua akun beda cabang (role RLS berbeda) | Akun A menyimpan ramalan; akun B membuka chart yang sama | Akun B tidak melihat angka milik lingkup akun A |

## F. Data, hak akses & ekstrak (Level 3)

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| F01 | 3 Admin data | Tinggi | Dataset dari SQL Lab | Role admin data | SQL Lab → query → Save dataset | Dataset tampil di Datasets, bisa dipakai di Studio |
| F02 | 3 Admin data | Tinggi | Persiapan data | A10 | Kecualikan saluran Reseller → simpan sebagai penjualan_tanpa_reseller | Dataset baru; total = 667,4 − 97,9 ≈ 569,5 miliar |
| F03 | 3 Admin data | Tinggi | Aturan RLS per role | Role Cabang Bandung + akun uji | Settings → Row Level Security → Regular, dataset latihan_penjualan, role Cabang Bandung, clause nm_cabang = 'Cabang Bandung' | Akun uji hanya melihat Cabang Bandung (± 121,2 miliar); admin melihat semua |
| F04 | 3 Admin data | Tinggi/asap | Ekstrak penuh | Dataset dari koneksi database sumber | Data → Ekstrak ke ALDx Engine → mode Penuh, jadwal Harian 02:00 → Buat & segarkan | Status siap; baris = baris sumber; kolom Berikutnya = besok 02:00 |
| F05 | 3 Admin data | Tinggi | Ekstrak inkremental | Sumber dengan kolom tanggal | Buat ekstrak Inkremental (kolom tanggal) → tambah data di sumber → Segarkan | Baris terakhir = jumlah baris baru saja; total bertambah |
| F06 | 3 Admin data | Tinggi | RLS ikut ke ekstrak | F04 dari dataset ber-RLS | Akun uji cabang membuka chart setelah Pakai di chart | Hanya data cabangnya |
| F07 | 3 Admin data | Sedang | Pakai di chart / Kembalikan | F04 | Klik Pakai di chart lalu Kembalikan chart | Jumlah chart dipindah sesuai; dashboard tetap tampil di kedua kondisi |
| F08 | 3 Admin data | Sedang | Hapus ekstrak dilindungi | F07 (chart masih memakai ekstrak) | Klik Hapus | Ditolak dengan pesan 'Masih ada chart yang memakai ekstrak ini' |
| F09 | 3 Admin data | Sedang | Ekstrak gagal tercatat | Password sumber diubah salah | Segarkan | Status gagal + pesan galat; Riwayat mencatat gagal; dashboard tetap memakai data lama |
| F10 | 3 Admin data | Tinggi | Upload CSV ke ALDx Engine | Role dengan kemampuan Upload | + → Data → Upload CSV → database ALDx Engine | Tabel & dataset baru; chart bisa dibuat |
| F11 | 3 Admin data | Sedang | Batas upload | F10 | Upload file lebih besar dari batas MB | Ditolak: 'File terlalu besar. Maksimal … MB' |
| F12 | 3 Admin data | Tinggi/asap | Hubungkan database | Database uji (mis. PostgreSQL) + akun hanya-baca | Data → Hubungkan data → PostgreSQL → isi → Uji koneksi → Simpan | Uji hijau (versi & schema tampil); koneksi muncul di Settings → Database Connections, hanya-baca, password tidak tampil |
| F13 | 3 Admin data | Tinggi | Pesan galat koneksi jelas | F12 | Uji dengan password salah, lalu dengan port salah | Pesan merah: autentikasi gagal / tidak terjangkau; password tidak tertulis di pesan; tombol Simpan tetap nonaktif |
| F14 | 3 Admin data | Tinggi | Impor Excel banyak lembar | berkas bahan-ajar/berkas/contoh-target-toko.xlsx | Hubungkan data → Berkas → pilih berkas → Impor ke ALDx Engine | 2 dataset: contoh_target_toko_target & contoh_target_toko_toko; Buat chart membuka Explore |
| F16 | 3 Admin data | Tinggi | Skema yang ditampilkan per koneksi | Koneksi database dengan banyak skema (mis. Oracle) | Hubungkan data → Koneksi tersimpan → Atur skema → centang satu skema → Simpan skema; buka Dataset (+ Dataset), SQL Lab, Kueri Visual | Hanya skema tercentang yang tampil; Kueri Visual langsung memilih skema itu; tabelnya terdaftar |
| F17 | 3 Admin data | Tinggi | Oracle lama (11g) di SQL Lab, Kueri Visual & dataset | Koneksi Oracle 11g | SQL Lab: SELECT * FROM <skema>.<tabel> → Jalankan; Kueri Visual: gabung 2 tabel → Jalankan → Simpan jadi dataset; Buka di SQL Lab | Tidak ada ORA-00933/ORA-00942; maks 1.000 baris; dataset tersimpan; SQL Lab terbuka tanpa 502 |
| F15 | 3 Admin data | Sedang | Impor Microsoft Access | Berkas .mdb/.accdb (mis. Northwind) | Hubungkan data → Berkas → pilih berkas → centang tabel → Impor | Tabel terbaca dengan contoh isi; kolom foto/lampiran dilewati; dataset terbentuk |
| F18 | 3 Admin data | Tinggi | Impor data latihan Penerbangan (6 lembar) | berkas bahan-ajar/berkas/contoh-penerbangan-sedang.xlsx | Hubungkan data → Berkas → pilih berkas → centang 6 lembar, awalan terbang → Impor; Kueri Visual: gabung tiket + jadwal + penerbangan + maskapai, jumlahkan harga (status bukan Refund) per maskapai | 6 dataset terbang_*; tiket 150.000 baris; Nusa Air terbesar Rp151,25 miliar, total Rp323,94 miliar (angka kunci: bahan-ajar/berkas/README.md) |
| F19 | 3 Admin data | Sedang | SAP HANA opsional | Image tanpa hdbcli-*.whl di docker\wheels | Hubungkan data → lihat kartu SAP HANA, arahkan kursor; jalankan scripts\uji.ps1 | Kartu SAP HANA nonaktif dengan petunjuk unduh driver SAP; uji 'driver database & berkas terpasang' LULUS dengan catatan 'opsional belum dipasang: SAP HANA'. Setelah hdbcli ditaruh & init.ps1: kartu aktif |

## G. Pusat Kendali (Level 4)

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| G01 | 4 Admin server | Tinggi/asap | Status | A01 | Pusat Kendali → Status | Semua node online; CPU/RAM tampil; antrean tampil |
| G02 | 4 Admin server | Tinggi | Pengaturan langsung | G01 | Ubah Baris maksimal per chart → Simpan | Tersimpan; berlaku ±10 detik; tercatat di Riwayat |
| G03 | 4 Admin server | Tinggi | Pengaturan perlu terapkan | G01 | Ubah proses backgrounder ekstrak → Simpan → scripts\terapkan-server.ps1 | Lencana 'perlu diterapkan' hilang setelah terapkan; Topologi menunjukkan nilai baru |
| G04 | 4 Admin server | Tinggi | Matriks hak akses | Role buatan sendiri (mis. Cabang Bandung) | Centang/hapus 'Unduh data chart' untuk satu role | Pengguna role itu kehilangan/mendapat menu Download |
| G05 | 4 Admin server | Sedang | Non-admin ditolak | Akun Gamma | Buka /pusat-kendali/ | Pesan 'Pusat Kendali Server hanya untuk Admin.' (403) |
| G06 | 4 Admin server | Rendah | Tambah node | Komputer kedua | scripts\gabung-node.ps1 -Utama <IP> | Node baru muncul di Status ±1 menit |
| G07 | 4 Admin server | Tinggi/asap | Ganti identitas tanpa restart | G01 | Identitas & Tema → ubah Nama aplikasi & Warna utama → Simpan; pengguna lain muat ulang setelah 1 menit | Judul tab, navbar, login & Studio memakai nama/warna baru; tercatat di Riwayat; tanpa restart |
| G08 | 4 Admin server | Sedang | Unggah logo & favicon | G07 | Unggah PNG logo (< 1 MB) dan favicon; lalu 'Pakai otomatis' | Logo tampil di navbar & login; favicon di tab; otomatis kembali ke logo buatan sistem |
| G09 | 4 Admin server | Sedang | Preset tema | G07 | Klik preset Hijau, lalu Netral | Warna & motif berganti; Netral mengembalikan semua isian ke bawaan |
| G10 | 4 Admin server | Tinggi | Batas data: rekomendasi, angka, tanpa batas | Akun Superadmin | Pusat Kendali → Batas data → Impor berkas: baris maksimal = 3 → Simpan; impor CSV 10 baris; lalu klik auto → Simpan | Rekomendasi & rumus tampil; impor ditolak dengan pesan 'melebihi batas 3 baris' tanpa dataset terbentuk; setelah auto impor berhasil |
| G11 | 4 Admin server | Tinggi | Usulan /hw-engineer & /ahli-ui-ux | Akun Superadmin; model AI aktif | Ctrl + I di Pusat Kendali → 'Server terasa lambat…' → Abaikan; ulangi → Terapkan. Di Identitas & Tema minta tema baru | Kartu usulan (lama → baru + alasan, cek kontras untuk tema); Abaikan = tidak ada perubahan; Terapkan = tersimpan & tercatat di Riwayat |
| G12 | 4 Admin server | Sedang | Logo ALDx "Tebasan" & animasi pemuatan | Akun Admin | Lihat navbar, halaman login, tab browser; buka dashboard berat; ganti preset ke hijau lalu kembali ke netral | Logo huruf A dibelah sayatan pink di latar terang & gelap, favicon tajam; pemuatan menampilkan sayatan melesat; di preset lain tanda mengikuti warna preset; tidak ada gambar rusak |
| G13 | 4 Admin server | Sedang | Tema bawaan Tinta & Sakura | Akun Admin | Identitas & Tema → preset netral → Terapkan; buka /login/ (jendela Incognito), Beranda, satu dashboard; klik kolom isian login; lalu preset navy | Login gaya poster: kanvas hitam bertekstur, nama raksasa, garis data pink melesat, panel dipotong sayatan pink; tombol hitam berubah pink saat disorot; fokus & tautan pink; nama panjang pindah baris per kata; di ponsel kanvas jadi kepala bermiring; navy mengembalikan warna lama |

## H. Keamanan

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| H01 | 1 Pengguna | Tinggi | RLS dashboard antar-pengguna | Dua akun beda cabang (role RLS berbeda) | Keduanya membuka dashboard ber-RLS yang sama | Masing-masing hanya melihat cabangnya; total berbeda |
| H02 | 1 Pengguna | Tinggi | Cache tidak bocor | H01 | Pengguna A membuka dashboard; segera pengguna B membuka chart yang sama | B tidak melihat angka A (kunci cache memakai sidik lingkup) |
| H03 | 3 Admin data | Tinggi | Upload ke ClickHouse lain ditolak | Akses upload; ada koneksi ClickHouse selain ALDx Engine | Coba upload ke koneksi ClickHouse itu | Ditolak: 'Upload ke ClickHouse hanya diizinkan ke ALDx Engine.' |
| H04 | 4 Admin server | Tinggi | Berkas rahasia tidak tersaji | – | Buka http://server:8088/.env dan /static/../.env | 404, isi .env tidak pernah tampil |
| H05 | 4 Admin server | Tinggi | Password tidak tercatat | A01 | Cari password admin & ENGINE_PASSWORD di installer\log dan docker compose logs | Tidak ditemukan |
| H06 | 4 Admin server | Sedang | Port internal tertutup | CLUSTER_BIND=127.0.0.1 | Dari komputer lain: Test-NetConnection server -Port 5433/8124/6379 | Semua gagal tersambung |
| H07 | 2 Analis | Sedang | Asisten AI memakai hak akses user | Akun uji cabang | Tanya total penjualan per cabang | Hanya cabang akun itu yang muncul |
| H09 | 3 Admin data | Tinggi | Koneksi wizard hanya-baca | F12 | SQL Lab pada koneksi baru: jalankan UPDATE/INSERT/DELETE | Ditolak (DML tidak diizinkan) |
| H10 | 2 Analis | Tinggi | Kueri Visual tunduk RLS | Akun Analis dengan aturan RLS cabang | Kueri Visual → latihan_penjualan → kolom nm_cabang, Jumlah total → Jalankan | Hanya cabang akun itu yang muncul (sama dengan SQL Lab & dashboard) |
| H12 | 4 Admin server | Tinggi | Installer: Superadmin email & username LDAP opsional | Jaringan kantor/VPN (opsional) | PASANG.cmd → Akun Superadmin (email & password) → Login kantor: centang LDAP, isi username Superadmin → Pasang → login dengan email lalu dengan username jaringan | Email selalu bisa login (juga saat LDAP mati); username jaringan melihat tab Pengaturan/Batas data/Hak akses; password tidak ada di .env |
| H13 | 1 Pengguna | Tinggi | Akun terkunci setelah salah password | Akun uji | Login dengan password salah 5 kali, lalu dengan password benar | Pesan 'Akun dikunci sementara… coba lagi pukul …'; password benar ditolak sampai kunci habis atau Admin membuka di Pusat Kendali › Riwayat |
| H14 | 4 Admin server | Tinggi | Jejak audit lengkap | H13; akun Admin | Unduh CSV dari chart, ekspor berkas .ald, ubah role pengguna, lalu buka Pusat Kendali › Riwayat | Semua aksi tampil dengan waktu, pengguna & alamat IP; Unduh CSV menghasilkan berkas yang terbaca Excel |
| H15 | 3 Admin data | Tinggi | Data .aldx impor tertutup untuk orang lain | Berkas .aldx berisi data; akun Admin & akun cabang | Admin mengimpor dengan 'Pakai data di berkas'; akun cabang membuka dataset hasil impor | Akun cabang melihat 0 baris; ada aturan 'ALDx berkas: … (khusus admin)' di Hak akses data; akun non-Admin tidak bisa mencentang 'Pakai data' |
| H16 | 4 Admin server | Sedang | Hak minimum role bawaan | build-dashboards sudah dijalankan | Pusat Kendali › Hak akses; login akun Pengguna dan cek menu | Pengguna tidak melihat menu Pusat Kendali/Databases/Action Log; peringatan kuning muncul bila ada non-Admin ber-role Alpha |
| H11 | 4 Admin server | Tinggi | Pengaturan vital khusus Superadmin | Akun Admin biasa (bukan Superadmin) | Buka Pusat Kendali; coba buka ?tab=pengaturan; di Kelola › Pengguna beri diri sendiri role Superadmin | Tab Pengaturan, Batas data, Hak akses tidak tampil; API menjawab 403; pemberian role Superadmin ditolak |
| H08 | 4 Admin server | Sedang | Tanpa telemetri pihak ketiga | – | Buka DevTools → Network saat membuka dashboard | Tidak ada permintaan ke scarf.sh atau domain luar selain ubin peta |

## I. Kinerja

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| I01 | 1 Pengguna | Sedang | Dashboard ekstrak cepat | Dashboard memakai ekstrak | Buka dashboard (cache dikosongkan: Force refresh) | Semua chart < 3 detik |
| I02 | 4 Admin server | Sedang | Beban bersamaan | ≥ 20 penguji | Semua membuka & menyaring dashboard latihan pada menit yang sama | Tidak ada galat; Status: CPU web < 85%; antrean kembali 0 dalam 1 menit |
| I03 | 4 Admin server | Sedang | Penyegaran ekstrak besar | Sumber ≥ 10 juta baris | Segarkan ekstrak penuh saat jam kerja | Dashboard tetap bisa dibuka selama penyegaran; selesai < batas 6 jam |
| I04 | 4 Admin server | Rendah | Ramalan harian | Ada chart ramalan | Cek keesokan hari setelah 03:00 | Kolom diperbarui di tabel sps_ramalan berganti; chart memuat data terbaru |
| I05 | 3 Admin data | Sedang | Data besar 1 juta tiket | scripts\data-penerbangan.ps1 (berkas besar dibuat) | Hubungkan data → Berkas → contoh-penerbangan-besar.xlsx → Impor; buat chart pendapatan per bulan dari tiket + jadwal; ulangi setelah ekstrak | Impor selesai tanpa melebihi batas (atau pesan batas jelas); 1.000.000 baris tiket; pendapatan Rp2,28 triliun; chart tampil < 5 detik setelah ekstrak |

## J. Berkas, filter global & ulasan

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| J01 | 2 Analis | Tinggi/asap | Ekspor .ald & impor sebagai salinan | Dashboard latihan | Dashboard & Story → Berkas .ald / .aldx → Dashboard latihan → .ald → Kunci server → Unduh; lalu Impor berkas itu → Salinan baru | Berkas terunduh; ringkasan 'terverifikasi'; dashboard '(salinan)' terbuka dengan chart yang sama; dataset lama tidak berubah |
| J02 | 2 Analis | Tinggi | Paket .aldx berisi data sesuai hak akses | Akun cabang (RLS) | Ekspor .aldx + Sertakan salinan data dengan akun cabang; impor dengan akun admin → Pakai data di berkas | Jumlah baris di ringkasan = baris yang boleh dilihat akun cabang; dashboard hasil impor memakai ALDx Engine |
| J03 | 2 Analis | Tinggi | Berkas berkata sandi & berkas rusak | J01 | Ekspor dengan Kata sandi; impor tanpa sandi, dengan sandi salah, lalu sandi benar; ubah 1 byte berkas lalu impor | Tanpa/salah sandi ditolak; sandi benar terbuka; berkas diubah ditolak |
| J04 | 3 Admin data | Tinggi | Berkas tanpa rahasia koneksi | J01 | Cek isi berkas (tidak bisa dibuka tanpa kunci); Impor ke koneksi tujuan lain | Tidak ada alamat/user/password koneksi; hanya koneksi yang boleh diakses penerima yang bisa dipilih |
| J05 | 1 Pengguna | Tinggi/asap | Filter global di semua dashboard & Story | ≥ 2 dashboard dengan filter Cabang | Tombol corong → Cabang = Cabang Bandung → Terapkan; buka dashboard lain & Story | Semua dashboard dengan filter Cabang langsung tersaring Cabang Bandung; lencana corong = 1; hapus semua = kembali normal |
| J06 | 1 Pengguna | Sedang | Komentar & rating dimoderasi | Akun pengguna & Superadmin | Pengguna: dashboard → tombol komentar → 4 bintang + komentar → Kirim; Superadmin: Kelola → Moderasi ulasan → Tampilkan | Sebelum disetujui hanya penulis & Superadmin yang melihat; sesudahnya semua; rata-rata rating tampil |
| J07 | 1 Pengguna | Sedang | Balasan & @sebut | J06; dua akun | A menulis komentar menyebut @B; B membalas komentar A | Saran nama muncul saat mengetik @; B mendapat titik di avatar & pemberitahuan; balasan tampil menjorok di bawah komentar A |
| J08 | 1 Pengguna | Sedang | Filter global rentang & per akun | Dashboard dengan filter Tahun (rentang) & waktu | Corong → Tahun dari 2024; Rentang waktu 30 hari terakhir → Terapkan; buka ALDx dari komputer/ponsel lain | Dashboard tersaring sesuai rentang; filter yang sama sudah aktif di perangkat lain |
| J09 | 3 Admin data | Sedang | Ekspor .aldx besar di latar | Backgrounder menyala; dashboard dengan data | Ekspor .aldx + data → pindah halaman → kembali ke Berkas | Pesan 'disiapkan di latar'; bagian Ekspor terakhir berubah siap; Unduh berhasil; akun lain tidak bisa mengunduh |
| J10 | 4 Admin server | Rendah | Moderasi massal | ≥ 3 komentar menunggu | Moderasi ulasan → Pilih semua → Tampilkan terpilih | Semua tampil; lencana jumlah menunggu di menu & avatar hilang; tercatat di jejak audit |

## K. Dashboard lanjutan & kenyamanan

| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |
|---|---|---|---|---|---|---|
| K01 | 2 Analis | Tinggi | Riwayat versi & pulihkan | Pemilik dashboard | Ubah judul/tata letak → Simpan → Riwayat versi → Pulihkan versi sebelumnya | Judul/tata letak kembali; versi sebelum pemulihan tercatat; pengguna bukan pemilik tidak bisa memulihkan |
| K02 | 2 Analis | Sedang | Tata letak ponsel | Pemilik dashboard; ponsel | Tata ponsel → balik urutan, sembunyikan 1 chart → Simpan → buka di ponsel | Urutan sesuai pengaturan, chart tersembunyi tidak tampil; layar lebar tidak berubah |
| K03 | 3 Admin data | Tinggi | Lihat sebagai… | Admin; dua akun beda cabang | Kelola → Lihat sebagai… → akun cabang A → dashboard latihan → Tampilkan | Setiap chart menampilkan angka cabang A & aturan RLS-nya; tercatat di jejak audit; akun non-Admin ditolak (403) |
| K04 | 3 Admin data | Sedang | Langganan laporan | SMTP_* di .env | Langganan laporan → + Laporan chart, CSV, jadwal tiap jam ke email sendiri | Email berisi CSV diterima; tanpa SMTP_HOST laporan hanya tercatat (tidak dikirim) |
| K05 | 2 Analis | Rendah | Lencana Resmi | Pemilik dashboard | Ubah properti → Sertifikasi: Tim Data → buka Beranda & Ctrl+K | Lencana Resmi di Beranda; dashboard itu paling atas di hasil cari |
| K06 | 2 Analis | Sedang | Kueri Visual tersimpan | Akun Analis | Kueri Visual: gabung 2 tabel → nama → Simpan kueri → muat ulang → buka dari Kueri tersimpan | Susunan kembali lengkap; Jalankan memberi hasil sama; kueri tidak terlihat akun lain |
| K07 | 1 Pengguna | Rendah | Mode gelap | – | Avatar → Tampilan → Gelap; buka dashboard & SQL Lab; kembali Terang | Cangkang, dashboard & SQL Lab gelap dan terbaca; kembali terang tanpa sisa |
| K08 | 1 Pengguna | Sedang | Warna kategori sama | Dua akun beda cabang | Keduanya membuka chart Komposisi kategori | Warna tiap kategori sama untuk kedua akun |
| K09 | 4 Admin server | Tinggi | Cadangan terjadwal & uji pulih | Windows server, admin | jadwal-cadangan.ps1 → Start-ScheduledTask kedua tugas → Pusat Kendali Status | Kartu Cadangan terakhir hijau & uji pulih OK; backup\cadangan.log berisi OK |
| K10 | 4 Admin server | Sedang | Uji beban | Di luar jam kerja | uji-beban.ps1 -Akun <admin> -Pengguna 50 -Detik 120 | KESIMPULAN: CUKUP (p95 < 5 dtk, gagal < 1%), atau ikuti saran sizing bila KURANG |
