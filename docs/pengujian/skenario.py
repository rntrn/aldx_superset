"""Sumber tunggal skenario uji (UAT) ALDx.

Menghasilkan dua berkas dari daftar SKENARIO di bawah:
    skenario-uji.md     untuk dibaca (tabel per area)
    lembar-uji.xlsx     untuk diisi penguji (hasil, catatan, penguji, tanggal) + ringkasan otomatis

Menambah/mengubah skenario: edit daftar SKENARIO, lalu jalankan
    python docs/pengujian/skenario.py
(butuh Python + openpyxl; bisa di container: docker compose exec superset python /app/... tidak perlu,
 cukup Python di komputer mana pun).
"""

from __future__ import annotations

from pathlib import Path

FOLDER = Path(__file__).resolve().parent

AREA = {
    "A": "Instalasi & perawatan",
    "B": "Login & sesi",
    "C": "Dashboard (Level 1)",
    "D": "Studio Visual (Level 2)",
    "E": "Peta & analitik prediktif",
    "F": "Data, hak akses & ekstrak (Level 3)",
    "G": "Pusat Kendali (Level 4)",
    "H": "Keamanan",
    "I": "Kinerja",
    "J": "Berkas, filter global & ulasan",
    "K": "Dashboard lanjutan & kenyamanan",
}

# (id, level, prioritas, judul, prasyarat, langkah, hasil diharapkan)
#   level: 1 Pengguna · 2 Analis · 3 Admin data · 4 Admin server
#   prioritas: Tinggi = wajib lulus sebelum dipakai pengguna; "asap" = termasuk uji asap 15 menit
SKENARIO = [
    # A. Instalasi & perawatan
    ("A01", 4, "Tinggi/asap", "Instalasi baru dengan PASANG.cmd", "Docker Desktop menyala, folder di D:\\superset",
     "Klik dua kali PASANG.cmd, isi password admin, lewati isian opsional, klik Pasang",
     "Semua langkah selesai; halaman Selesai menampilkan alamat; browser membuka halaman login"),
    ("A02", 4, "Tinggi/asap", "Uji otomatis", "A01",
     "Jalankan scripts\\uji.ps1", "55/55 LULUS, kode keluar 0"),
    ("A02b", 4, "Sedang", "Versi tampil & status pembaruan", "A01; komputer dengan internet",
     "Buka /login/ (lihat kaki halaman); login → gulir ke bawah Beranda",
     "Login menulis vYYYY.MM.DD; Beranda menulis ALDx vYYYY.MM.DD (+ kode commit bila dipasang dengan git) dan "
     "'✓ Versi terbaru' atau 'Pembaruan tersedia' dengan tautan Unduh installer; tanpa internet tertulis 'Tidak bisa dicek'"),
    ("A03", 4, "Tinggi", "Pemeriksaan prasyarat menolak kondisi tidak layak", "Docker Desktop DIMATIKAN",
     "Jalankan PASANG.cmd", "Baris 'Docker Desktop menyala' GAGAL, tombol Lanjut nonaktif; setelah Docker dinyalakan & Periksa ulang: OK"),
    ("A04", 4, "Tinggi", "Pindah metadata lama ke PostgreSQL", "Instalasi lama (MYSQL_HOST=host.docker.internal + XAMPP menyala, atau MariaDB)",
     "Jalankan PASANG.cmd, centang Pindahkan data",
     "Dashboard, chart, user, koneksi lama tampil di versi baru; .env METADB_JENIS=postgres; upload lama terbaca dari ALDx Engine"),
    ("A05", 4, "Tinggi", "Instalasi ulang tidak menghapus data", "A01 + ada chart buatan sendiri",
     "Jalankan PASANG.cmd lagi (password admin dikosongkan)", "Selesai tanpa galat; chart tetap ada; password admin tidak berubah"),
    ("A06", 4, "Tinggi", "Cadangan & pemulihan metadata", "A01",
     "scripts\\cadangkan.ps1 → hapus 1 chart → scripts\\cadangkan.ps1 -Pulihkan backup\\metadb-<terbaru>.dump",
     "Chart yang dihapus kembali"),
    ("A07", 4, "Sedang", "Cadangan & pemulihan ALDx Engine", "Ada data latihan",
     "scripts\\cadangkan.ps1 -Engine → -PulihkanEngine backup\\engine\\engine-<terbaru>.zip",
     "Berkas .zip terbentuk; setelah pemulihan dataset latihan tetap bisa dibuka"),
    ("A08", 4, "Sedang", "Versi komponen", "A01", "scripts\\versi.ps1",
     "Kolom Diminta = Berjalan untuk Superset, PostgreSQL, ClickHouse, Redis, nginx"),
    ("A09", 4, "Sedang", "Restart komputer", "A01", "Restart Windows, buka Docker Desktop, tunggu 3 menit",
     "Semua container menyala sendiri; uji.ps1 LULUS"),
    ("A10", 4, "Sedang", "Data latihan", "A01", "scripts\\data-latihan.ps1 dua kali",
     "Dataset latihan_penjualan (4.320 baris), latihan_lokasi_pelanggan (1.500) & latihan_cabang (6) ada, tidak berganda; dashboard latihan ada"),
    ("A11", 4, "Tinggi", "Urutan menyala setelah Docker mati", "A01",
     "Quit Docker Desktop → buka lagi → ikuti 19-runbook §2.1", "Semua container healthy tanpa perintah tambahan; uji.ps1 LULUS"),
    ("A12", 4, "Sedang", "Simulasi gangguan engine", "A01",
     "docker compose stop engine → ikuti pohon keputusan 19-runbook §4 → perbaiki",
     "Penyebab ditemukan dari docker compose ps; setelah start engine + restart worker, uji.ps1 LULUS"),
    ("A13", 4, "Tinggi", "Instalasi baru netral + akun lokal", "Komputer tanpa instalasi SPS",
     "PASANG.cmd → Login & pengguna: Akun lokal → isi 2 baris (peran Pengguna & Analis) → Pasang",
     "Login akun baru berhasil; Settings → List Users: peran sesuai (Analis punya sql_lab); tidak ada koneksi selain ALDx Engine; LDAP_SERVERS kosong; password tidak ada di .env & log"),
    ("A14", 4, "Sedang", "Instalasi dengan LDAP", "Server LDAP uji terjangkau",
     "PASANG.cmd → Login & pengguna: LDAP → isi server, domain, search base, admin LDAP → Uji koneksi → Pasang",
     "Uji koneksi OK; .env LDAP_* terisi; login username jaringan berhasil; admin lokal tetap bisa login"),
    ("A15", 4, "Sedang", "Berkas lisensi ikut terpasang", "A01",
     "Buka folder instalasi (mis. D:\\superset); buka LICENSE, NOTICE, THIRD-PARTY-LICENSES.md",
     "Ketiga berkas ada; LICENSE = Apache License 2.0; NOTICE menyebut ALDx & Apache Superset; tidak ada logo instansi di branding\\"),

    # B. Login & sesi
    ("B01", 1, "Tinggi/asap", "Login akun pengguna", "Akun lokal dibuat admin (atau LDAP aktif)",
     "Buka alamat aplikasi, login dengan akun pengguna", "Masuk ke halaman depan sesuai Identitas & Tema; nama pengguna tampil di menu"),
    ("B02", 1, "Tinggi", "Login admin lokal saat LDAP tidak terjangkau", "Putus VPN/LDAP",
     "Login dengan akun admin lokal", "Berhasil masuk"),
    ("B03", 1, "Tinggi", "Password salah", "–", "Login dengan password salah", "Pesan gagal; tidak masuk"),
    ("B04", 1, "Sedang", "Batas percobaan login", "–",
     "Coba login salah lebih dari batas per menit (Pusat Kendali → Gateway)", "Ditolak sementara (HTTP 429), normal kembali setelah 1 menit"),
    ("B05", 1, "Sedang", "Akun LDAP terdaftar otomatis", "LDAP aktif; pengguna login pertama kali",
     "Admin cek Settings → List Users", "User terdaftar dengan role LDAP_DEFAULT_ROLE + SPS_ROLE_PENGGUNA (+ role \"Akses …\" bila profil pengguna aktif)"),
    ("B06", 1, "Rendah", "Keluar", "B01", "Menu Settings → Log out", "Kembali ke halaman login; tombol Back tidak membuka data"),
    ("B07", 1, "Sedang", "Halaman login beranimasi", "–",
     "Buka /login/; lalu aktifkan Windows 'Show animations' = Off dan muat ulang; buka /login/?klasik=1",
     "Nama, logo & warna perusahaan tampil, latar bergerak; dengan animasi Off latar diam; ?klasik=1 menampilkan login bawaan"),
    ("B08", 1, "Tinggi", "Menu mengikuti alur & hak akses", "Akun Pengguna, Analis, Admin",
     "Login bergantian, buka menu navbar",
     "Sidebar urut Data › Kueri › Visual › Dashboard & Story, sama di semua halaman; tidak ada item ganda; Pengguna tanpa menu Kueri; Analis punya Kueri Visual & SQL Lab; hanya Admin melihat Hubungkan data & Ekstrak"),
    ("B09", 1, "Tinggi/asap", "Cangkang aplikasi & Beranda", "B01",
     "Login; buka beberapa menu kiri; buka /dashboard/list/ langsung di tab baru",
     "Beranda tampil dengan Cari, 5 kartu Bangun laporan (jumlah benar), Lanjutkan, Dashboard; semua halaman tampil di cangkang tanpa navbar ganda; alamat lama dialihkan ke /app/?p=..."),
    ("B10", 1, "Sedang", "Cari & pintasan keyboard", "B09",
     "Ctrl + K, ketik 'latihan', Enter; tekan ? ; tekan g lalu d; Ctrl + \\",
     "Palet menemukan dashboard/chart/dataset; panel Cara pakai sesuai halaman (berisi pintasan); g d membuka Daftar dashboard; sidebar ringkas/lebar"),
    ("B11", 1, "Sedang", "Ganti bahasa", "B09",
     "Kiri bawah → Bahasa → English, lalu 日本語, lalu Bahasa Indonesia",
     "Menu, Beranda, Studio, panel bantuan berganti bahasa; halaman Superset ikut (EN/JA asli, ID kamus SPS); nilai data tidak berubah"),
    ("B12", 1, "Sedang", "Tampilan ponsel", "Ponsel / jendela ≤ 760 px",
     "Login dari ponsel; buka Beranda, Daftar dashboard, satu dashboard, menu Lainnya",
     "Bilah tab bawah tampil; laci menu terbuka; tidak ada geser horizontal di Beranda; dashboard terbaca"),
    ("B13", 1, "Tinggi", "Panel Asisten AI di setiap halaman", "Model AI aktif; akun Pengguna",
     "Di Daftar dashboard tekan Ctrl + I → klik contoh 'Penjualan per cabang tahun ini?'; ketik /panduan cara membuat story",
     "Panel terbuka di kanan (ponsel: layar penuh); jawaban + tabel sesuai hak akses; /panduan menjawab dari isi Cara pakai; hanya peran yang boleh yang tampil"),
    ("B14", 1, "Sedang", "Ekspor tabel & grafik", "B13 atau Kueri Visual/Studio",
     "Arahkan kursor ke tabel jawaban → Ekspor → Excel, CSV, Teks, Gambar, PDF / cetak, Salin tabel",
     "Berkas terunduh bernama <judul>_<tanggal>; Excel berisi angka (bisa dijumlah); PDF lewat dialog cetak; isi = data di layar"),

    # C. Dashboard
    ("C01", 1, "Tinggi/asap", "Membuka dashboard latihan", "A10, B01",
     "Dashboards → cari 'latihan' → buka", "8 chart tampil tanpa galat dalam < 10 detik"),
    ("C02", 1, "Tinggi", "Filter dashboard", "C01", "Filter Kategori = Kesehatan & Kecantikan → Apply filters",
     "Total penjualan berubah menjadi ± 53.8B; semua chart penjualan tersaring"),
    ("C03", 1, "Sedang", "Klik-filter", "C01", "Klik potongan Elektronik di pie", "Chart lain tersaring ke Elektronik; klik lagi membatalkan"),
    ("C04", 1, "Sedang", "Unduh CSV & gambar", "Role punya kemampuan Unduh", "⋮ → Download → Export to .CSV, lalu Download as image",
     "Berkas CSV & PNG terunduh"),
    ("C05", 1, "Sedang", "Angka singkat & tooltip", "C01", "Arahkan kursor ke batang Cabang Jakarta",
     "Tooltip menampilkan nilai lengkap ± 234 miliar"),
    ("C06", 1, "Sedang", "Asisten AI menjawab", "Model AI dikonfigurasi, role diizinkan",
     "Tanya: 'total penjualan per cabang tahun 2025'", "Jawaban berupa tabel/grafik; angka Cabang Jakarta 2025 ± 91,0 miliar"),
    ("C07", 1, "Rendah", "Favorit", "C01", "Klik bintang di judul dashboard", "Dashboard muncul di Home → Favorites"),

    # D. Studio Visual
    ("D01", 2, "Tinggi/asap", "Chart batang seret-lepas", "Role analis",
     "Studio → latihan_penjualan → nm_cabang ke Kolom, total ke Baris", "Batang 6 cabang; Jakarta tertinggi; rekomendasi Batang berbingkai emas"),
    ("D02", 2, "Tinggi", "Warna bertumpuk", "D01", "kategori ke Warna", "Batang bertumpuk 5 warna palet SPS; legenda tampil"),
    ("D03", 2, "Tinggi", "Filter lembar", "D01", "saluran ke Filter → centang Online → Terapkan", "Angka berkurang; pil filter tampil"),
    ("D04", 2, "Sedang", "Ganti agregasi", "D01", "Klik pil SUM(total) → Rata-rata", "Pil menjadi AVG(total), grafik berubah"),
    ("D05", 2, "Sedang", "Tukar, urutkan, lihat data, label", "D01", "Klik Tukar, Urutkan, Lihat data; centang Tampilkan nilai",
     "Batang mendatar; terurut; tabel muncul; nilai tertulis"),
    ("D06", 2, "Tinggi", "23 jenis chart", "A10",
     "Ikuti contoh di 17-katalog-chart-peta-prediksi.md untuk setiap jenis", "Semua 23 jenis tergambar di Studio tanpa galat"),
    ("D07", 2, "Tinggi/asap", "Simpan & buka di Explore", "D02", "Judul → Simpan → Buka di Explore",
     "Chart Superset tampil sama (warna, tumpukan) tanpa peringatan 'not up to date'"),
    ("D08", 2, "Sedang", "Buka kembali lembar tersimpan", "D07", "Panel kanan → Lembar kerja tersimpan → klik", "Rak & pilihan kembali seperti saat disimpan"),
    ("D09", 2, "Tinggi", "Susun dashboard", "≥ 2 chart tersimpan",
     "Tab Dashboard → seret 2 chart → atur lebar → Tambah filter nm_cabang → Simpan",
     "Dashboard tampil di menu Dashboards dengan filter Cabang yang bekerja"),
    ("D10", 2, "Sedang", "Tanpa izin simpan", "Akun role Gamma", "Buat chart di Studio → Simpan",
     "Tidak tersimpan; muncul tautan Explore & pesan izin"),
    ("D11", 2, "Tinggi/asap", "Kueri Visual: klik dua kali", "Peran Analis",
     "Kueri → Kueri Visual → pilih database & skema → klik dua kali latihan_penjualan",
     "Hanya tabel skema terpilih yang tampil; kueri langsung dijalankan, 1.000 baris pertama tampil"),
    ("D12", 2, "Tinggi", "Kueri Visual: gabung otomatis & ringkas", "D11",
     "Klik dua kali latihan_lokasi_pelanggan lalu latihan_cabang → kolom pulau, Jumlah belanja, Hitung id_pelanggan → Jalankan",
     "Pesan hijau 'Digabung otomatis … kd_cabang'; Jawa ± Rp18,6 miliar dengan 1.106 pelanggan"),
    ("D13", 2, "Sedang", "Kueri Visual → dataset → Studio", "D12; kemampuan Kelola dataset",
     "Isi nama belanja_per_pulau → Simpan jadi dataset → Buat chart di Studio Visual",
     "Dataset tersimpan; Studio terbuka dengan dataset itu terpilih"),
    ("D14", 2, "Sedang", "Pratinjau Auto Chart sesuai jenis", "Ada model AI aktif",
     "Asisten AI → Auto Chart → latihan_penjualan → Analisis → ganti jenis kartu pie ke batang",
     "Pratinjau pie berupa lingkaran berlegenda; setelah diganti menjadi batang; tidak ada saran kembar kode/nama cabang"),
    ("D15", 2, "Sedang", "Menu Asisten AI hanya bila model aktif", "LM Studio/Ollama terpasang",
     "Matikan server model, tunggu 1 menit, muat ulang; nyalakan lagi, tunggu 1 menit, muat ulang",
     "Saat mati menu Asisten AI hilang (Story tetap di Dashboard & Story); saat menyala menu & model muncul"),
    ("D16", 2, "Sedang", "Story hanya dashboard selesai", "Ada dashboard draf kosong milik orang lain",
     "Dashboard & Story → Story → Story baru → buka pilihan dashboard",
     "Hanya dashboard berisi chart yang terbit atau milik sendiri (ditandai draf) yang tampil"),

    # E. Peta & analitik
    ("D17", 2, "Tinggi", "Chart berat tidak membuat browser macet", "Dataset ≥ 10.000 baris",
     "Explore → Tree Chart (atau Graph/Sankey) → isi Id & Parent → Update chart",
     "Data dibatasi 1.000 baris (Pusat Kendali → Baris maksimal chart berat); halaman tetap responsif; petunjuk Explore tampil"),
    ("D18", 2, "Tinggi", "Hierarki dimensi: buat & telusuri", "A10; peran Analis",
     "Studio → latihan_penjualan → Hierarki ＋ → nama Wilayah, centang provinsi, nm_cabang, kategori → hierarki ke Kolom, "
     "jumlah_transaksi ke Baris → klik satu batang → ▸ → ◂ ◂",
     "Awal 6 provinsi; klik batang → cabang di provinsi itu saja (jalur tampil di pil); ▸ → kategori; ◂ ◂ kembali ke provinsi"),
    ("D20", 2, "Tinggi", "Hierarki dengan seret-tumpuk", "Data latihan harian (A10)",
     "Studio → latihan_penjualan_harian → seret kecamatan ke ATAS kab_kota → isi nama 'Kota & Kecamatan' → Simpan; "
     "seret kelurahan ke atas hierarki itu",
     "Dialog Hierarki baru terbuka dengan urutan 1 kab_kota, 2 kecamatan; tersimpan; kelurahan jadi level ke-3; "
     "hierarki bawaan Wilayah, Kalender, Produk sudah ada"),
    ("D23", 2, "Tinggi", "Ukuran & dimensi terdefinisi", "A10; peran Analis (Alpha)",
     "Studio → latihan_penjualan → + Ukuran: nama rata_transaksi, rumus 'total / jumlah_transaksi' → Uji; ganti "
     "'SUM(total) / SUM(jumlah_transaksi)' → Uji → Simpan; + Dimensi: kelompok_nilai = CASE WHEN total >= 150000000 "
     "THEN 'Besar' ELSE 'Kecil' END → Simpan; pakai keduanya di chart → Simpan chart → coba Hapus definisi",
     "Rumus tanpa agregat ditolak dengan penjelasan; rumus benar menampilkan contoh hasil ± 867.442; keduanya bertanda ƒ; "
     "chart 2 batang (Besar/Kecil); hapus ditolak selama dipakai chart; kolom asli tidak punya menu hapus"),
    ("D24", 2, "Sedang", "N teratas", "Data latihan harian",
     "latihan_penjualan_harian: kab_kota + penjualan → isi N teratas = 5",
     "5 batang: Jakarta Selatan, Jakarta Timur, Kota Surabaya, Jakarta Barat, Kota Makassar; status '5 teratas'"),
    ("D21", 2, "Tinggi", "Tampilkan saya dengan banyak kolom", "A10",
     "latihan_penjualan: periode, kategori, saluran ke rak + total → lihat Tampilkan saya → klik Pie",
     "± 19 dari 23 jenis aktif; Pie memakai kategori, periode & saluran tampil pudar dicoret dan status "
     "'Tidak dipakai Pie: …'"),
    ("D22", 2, "Sedang", "Kolom ID tetap dimensi", "Dataset hasil gabung Kueri Visual (kolom t1.ID_...)",
     "Buka dataset gabungan penerbangan di Studio",
     "Semua kolom ID_…, t1.ID_…, kode_…, NIK ada di Dimensi; Harga & angka lain di Ukuran"),
    ("D19", 2, "Tinggi", "Objek desain dashboard: teks, gambar, garis", "D09; berkas logo PNG",
     "Susun dashboard → Objek: klik Teks → Atur: huruf Playfair Display, 34 px, warna pink, rata tengah; klik Garis; "
     "seret Gambar ke baris baru → unggah logo; seret satu chart ke samping logo → Simpan → buka dashboard; "
     "buka lagi di Studio & ubah teks → Simpan",
     "Judul tampil dengan huruf & warna pilihan tanpa kartu putih; garis pemisah & logo tampil; SVG ditolak; "
     "perubahan teks tersimpan dan CSS buatan sendiri di Superset tidak hilang"),
    ("E01", 2, "Tinggi", "Peta titik", "A10", "latihan_lokasi_pelanggan → lon ke Kolom, lat ke Baris, saluran ke Warna",
     "Rekomendasi Peta titik; titik di 6 wilayah Indonesia, warna per saluran"),
    ("E02", 2, "Tinggi", "Peta provinsi", "A10", "provinsi ke Kolom, belanja ke Baris",
     "Rekomendasi Peta provinsi; DKI Jakarta paling gelap; legenda nilai tampil"),
    ("E03", 2, "Sedang", "Peta di Superset", "E01–E02 disimpan", "Buka chart di Explore",
     "Peta provinsi (Indonesia) & peta titik deck.gl tampil; titik tampil walau ubin peta tidak termuat"),
    ("E04", 2, "Tinggi/asap", "Ramalan", "A10", "periode ke Kolom, total ke Baris → centang Ramalan 6",
     "total tercantum di bagian Ukuran (bukan Dimensi) & tampil SUM(total); garis putus-putus 6 bulan + pita 80/95%; "
     "keterangan 'Holt-Winters (musiman 12)'; label sumbu berformat 2025-03-01"),
    ("E05", 2, "Tinggi", "Tren & anomali", "E04", "Centang Garis tren & Tandai anomali",
     "Garis tren titik-titik; satu titik merah di Maret 2025"),
    ("E08", 2, "Tinggi", "Analitik lengkap & tombol Siapkan", "A10",
     "periode + kategori + saluran ke rak, total ke Baris, jenis Garis → klik 'Siapkan agar analitik aktif' → centang "
     "Rata bergerak 3, Garis rata-rata, Garis median, Tertinggi & terendah, Target 22000000000 → Simpan baru → buka di Explore",
     "Panel aktif setelah Siapkan (kategori & saluran dilepas, dijelaskan); garis rata bergerak, rata-rata/median/target "
     "berlabel ringkas tidak bertumpuk, penanda Tertinggi (Mar 2025) & Terendah; di Explore seri Rata-rata/Median/Target ikut"),
    ("E09", 2, "Tinggi", "Ramalan data harian 2 juta baris", "D20",
     "latihan_penjualan_harian → hierarki Kalender (bulan) ke Kolom, penjualan ke Baris → Ramalan 6 + Tren",
     "Holt-Winters musiman 12; lonjakan menjelang Lebaran tiap tahun terlihat; respons < 2 detik"),
    ("E06", 2, "Tinggi", "Ramalan tersimpan ke dashboard", "E04", "Simpan → buka di Explore",
     "Chart garis berisi seri Aktual, Ramalan, batas 80%/95%, Tren; pesan 'diperbarui otomatis tiap hari'"),
    ("E07", 2, "Tinggi", "Ramalan mengikuti lingkup akses", "Akun uji cabang: scripts\\data-latihan.ps1 -AkunUji (latihan.bandung, latihan.jakarta)",
     "Akun A menyimpan ramalan; akun B membuka chart yang sama", "Akun B tidak melihat angka milik lingkup akun A"),

    # F. Data, hak akses, ekstrak
    ("F01", 3, "Tinggi", "Dataset dari SQL Lab", "Role admin data",
     "SQL Lab → query → Save dataset", "Dataset tampil di Datasets, bisa dipakai di Studio"),
    ("F02", 3, "Tinggi", "Persiapan data", "A10",
     "Kecualikan saluran Reseller → simpan sebagai penjualan_tanpa_reseller", "Dataset baru; total = 667,4 − 97,9 ≈ 569,5 miliar"),
    ("F03", 3, "Tinggi", "Aturan RLS per role", "Role contoh 'Latihan Cabang Bandung' + Akun uji cabang: scripts\\data-latihan.ps1 -AkunUji (latihan.bandung, latihan.jakarta)",
     "Settings → Row Level Security → Regular, dataset latihan_penjualan, role Cabang Bandung, clause nm_cabang = 'Cabang Bandung'",
     "Akun uji hanya melihat Cabang Bandung (± 121,2 miliar); admin melihat semua"),
    ("F04", 3, "Tinggi/asap", "Ekstrak penuh", "Dataset contoh_transaksi (Koneksi 'Contoh sumber (PostgreSQL)' (dimuat data latihan))",
     "Data → Ekstrak ke ALDx Engine → mode Penuh, jadwal Harian 02:00 → Buat & segarkan",
     "Status siap; baris = baris sumber; kolom Berikutnya = besok 02:00"),
    ("F05", 3, "Tinggi", "Ekstrak inkremental", "contoh_transaksi (kolom id_transaksi); tambah data: data-latihan.ps1 -TambahTransaksi 500",
     "Buat ekstrak Inkremental (kolom tanggal) → tambah data di sumber → Segarkan",
     "Baris terakhir = jumlah baris baru saja; total bertambah"),
    ("F05b", 3, "Tinggi", "Impor banyak tabel + cek kapasitas", "Koneksi 'Contoh sumber (PostgreSQL)' (dimuat data latihan): skema toko (6 tabel) & sdm (2 tabel)",
     "Ekstrak → Impor banyak tabel: pilih koneksi & skema → Pilih semua → Cek kapasitas → Impor; lalu Superadmin set "
     "Batas data › Ekstrak baris maksimal lebih kecil dari tabel terbesar → Cek kapasitas lagi",
     "Perkiraan baris & ukuran tampil; vonis Cukup + kebutuhan per tabel; semua tabel jadi ekstrak berstatus siap; "
     "setelah batas diturunkan vonis Tidak cukup, tabel itu ditandai, tombol Impor mati"),
    ("F06", 3, "Tinggi", "RLS ikut ke ekstrak", "F04 dari dataset ber-RLS",
     "Akun uji cabang membuka chart setelah Pakai di chart", "Hanya data cabangnya"),
    ("F07", 3, "Sedang", "Pakai di chart / Kembalikan", "F04", "Klik Pakai di chart lalu Kembalikan chart",
     "Jumlah chart dipindah sesuai; dashboard tetap tampil di kedua kondisi"),
    ("F08", 3, "Sedang", "Hapus ekstrak dilindungi", "F07 (chart masih memakai ekstrak)", "Klik Hapus",
     "Ditolak dengan pesan 'Masih ada chart yang memakai ekstrak ini'"),
    ("F09", 3, "Sedang", "Ekstrak gagal tercatat", "Password sumber diubah salah", "Segarkan",
     "Status gagal + pesan galat; Riwayat mencatat gagal; dashboard tetap memakai data lama"),
    ("F10", 3, "Tinggi", "Upload CSV ke ALDx Engine", "Role dengan kemampuan Upload",
     "+ → Data → Upload CSV → database ALDx Engine", "Tabel & dataset baru; chart bisa dibuat"),
    ("F11", 3, "Sedang", "Batas upload", "F10", "Upload file lebih besar dari batas MB", "Ditolak: 'File terlalu besar. Maksimal … MB'"),
    ("F12", 3, "Tinggi/asap", "Hubungkan database", "Database uji + akun hanya-baca (contoh jadi: koneksi 'Contoh sumber (PostgreSQL)')",
     "Data → Hubungkan data → PostgreSQL → isi → Uji koneksi → Simpan",
     "Uji hijau (versi & schema tampil); koneksi muncul di Settings → Database Connections, hanya-baca, password tidak tampil"),
    ("F13", 3, "Tinggi", "Pesan galat koneksi jelas", "F12", "Uji dengan password salah, lalu dengan port salah",
     "Pesan merah: autentikasi gagal / tidak terjangkau; password tidak tertulis di pesan; tombol Simpan tetap nonaktif"),
    ("F14", 3, "Tinggi", "Impor Excel banyak lembar", "berkas bahan-ajar/berkas/contoh-target-toko.xlsx",
     "Hubungkan data → Berkas → pilih berkas → Impor ke ALDx Engine",
     "2 dataset: contoh_target_toko_target & contoh_target_toko_toko; Buat chart membuka Explore"),
    ("F16", 3, "Tinggi", "Skema yang ditampilkan per koneksi", "Koneksi dengan banyak skema (contoh: 'Contoh sumber (PostgreSQL)' punya toko & sdm)",
     "Hubungkan data → Koneksi tersimpan → Atur skema → centang satu skema → Simpan skema; buka Dataset (+ Dataset), SQL Lab, Kueri Visual",
     "Hanya skema tercentang yang tampil; Kueri Visual langsung memilih skema itu; tabelnya terdaftar"),
    ("F17", 3, "Tinggi", "Oracle lama (11g) di SQL Lab, Kueri Visual & dataset", "Koneksi Oracle 11g",
     "SQL Lab: SELECT * FROM <skema>.<tabel> → Jalankan; Kueri Visual: gabung 2 tabel → Jalankan → Simpan jadi dataset; Buka di SQL Lab",
     "Tidak ada ORA-00933/ORA-00942; maks 1.000 baris; dataset tersimpan; SQL Lab terbuka tanpa 502"),
    ("F15", 3, "Sedang", "Impor Microsoft Access", "Berkas .mdb/.accdb (mis. Northwind)",
     "Hubungkan data → Berkas → pilih berkas → centang tabel → Impor",
     "Tabel terbaca dengan contoh isi; kolom foto/lampiran dilewati; dataset terbentuk"),
    ("F18", 3, "Tinggi", "Impor data latihan Penerbangan (6 lembar)", "berkas bahan-ajar/berkas/contoh-penerbangan-sedang.xlsx",
     "Hubungkan data → Berkas → pilih berkas → centang 6 lembar, awalan terbang → Impor; Kueri Visual: gabung tiket + jadwal + "
     "penerbangan + maskapai, jumlahkan harga (status bukan Refund) per maskapai",
     "6 dataset terbang_*; tiket 150.000 baris; Nusa Air terbesar Rp151,25 miliar, total Rp323,94 miliar "
     "(angka kunci: bahan-ajar/berkas/README.md)"),
    ("F19", 3, "Sedang", "SAP HANA opsional", "Image tanpa hdbcli-*.whl di docker\\wheels",
     "Hubungkan data → lihat kartu SAP HANA, arahkan kursor; jalankan scripts\\uji.ps1",
     "Kartu SAP HANA nonaktif dengan petunjuk unduh driver SAP; uji 'driver database & berkas terpasang' LULUS "
     "dengan catatan 'opsional belum dipasang: SAP HANA'. Setelah hdbcli ditaruh & init.ps1: kartu aktif"),

    # G. Pusat Kendali
    ("G01", 4, "Tinggi/asap", "Status", "A01", "Pusat Kendali → Status", "Semua node online; CPU/RAM tampil; antrean tampil"),
    ("G02", 4, "Tinggi", "Pengaturan langsung", "G01", "Ubah Baris maksimal per chart → Simpan",
     "Tersimpan; berlaku ±10 detik; tercatat di Riwayat"),
    ("G03", 4, "Tinggi", "Pengaturan perlu terapkan", "G01", "Ubah proses backgrounder ekstrak → Simpan → scripts\\terapkan-server.ps1",
     "Lencana 'perlu diterapkan' hilang setelah terapkan; Topologi menunjukkan nilai baru"),
    ("G04", 4, "Tinggi", "Matriks hak akses", "Role contoh 'Latihan Cabang Bandung' (dimuat data latihan)", "Centang/hapus 'Unduh data chart' untuk satu role",
     "Pengguna role itu kehilangan/mendapat menu Download"),
    ("G05", 4, "Sedang", "Non-admin ditolak", "Akun Gamma", "Buka /pusat-kendali/", "Pesan 'Pusat Kendali Server hanya untuk Admin.' (403)"),
    ("G06", 4, "Rendah", "Tambah node", "Komputer kedua", "scripts\\gabung-node.ps1 -Utama <IP>", "Node baru muncul di Status ±1 menit"),
    ("G07", 4, "Tinggi/asap", "Ganti identitas tanpa restart", "G01",
     "Identitas & Tema → ubah Nama aplikasi & Warna utama → Simpan; pengguna lain muat ulang setelah 1 menit",
     "Judul tab, navbar, login & Studio memakai nama/warna baru; tercatat di Riwayat; tanpa restart"),
    ("G08", 4, "Sedang", "Unggah logo & favicon", "G07", "Unggah PNG logo (< 1 MB) dan favicon; lalu 'Pakai otomatis'",
     "Logo tampil di navbar & login; favicon di tab; otomatis kembali ke logo buatan sistem"),
    ("G09", 4, "Sedang", "Preset tema", "G07", "Klik preset Hijau, lalu Netral",
     "Warna & motif berganti; Netral mengembalikan semua isian ke bawaan"),
    ("G10", 4, "Tinggi", "Batas data: rekomendasi, angka, tanpa batas", "Akun Superadmin",
     "Pusat Kendali → Batas data → Impor berkas: baris maksimal = 3 → Simpan; impor CSV 10 baris; lalu klik auto → Simpan",
     "Rekomendasi & rumus tampil; impor ditolak dengan pesan 'melebihi batas 3 baris' tanpa dataset terbentuk; setelah auto impor berhasil"),
    ("G11", 4, "Tinggi", "Usulan /hw-engineer & /ahli-ui-ux", "Akun Superadmin; model AI aktif",
     "Ctrl + I di Pusat Kendali → 'Server terasa lambat…' → Abaikan; ulangi → Terapkan. Di Identitas & Tema minta tema baru",
     "Kartu usulan (lama → baru + alasan, cek kontras untuk tema); Abaikan = tidak ada perubahan; Terapkan = tersimpan & tercatat di Riwayat"),
    ("G12", 4, "Sedang", "Logo ALDx \"Tebasan\" & animasi pemuatan", "Akun Admin",
     "Lihat navbar, halaman login, tab browser; buka dashboard berat; ganti preset ke hijau lalu kembali ke netral",
     "Logo huruf A dibelah sayatan pink di latar terang & gelap, favicon tajam; pemuatan menampilkan sayatan melesat; "
     "di preset lain tanda mengikuti warna preset; tidak ada gambar rusak"),
    ("G13", 4, "Sedang", "Tema bawaan Tinta & Sakura", "Akun Admin",
     "Identitas & Tema → preset netral → Terapkan; buka /login/ (jendela Incognito), Beranda, satu dashboard; klik kolom "
     "isian login; lalu preset navy",
     "Login bersih: kanvas gradasi hitam → abu tanpa motif, hanya logo di kiri atas + slogan di kiri bawah, garis data "
     "tergambar & titik cahaya melaju, panel dipotong sayatan pink; tombol hitam berubah pink saat disorot; fokus & tautan "
     "pink; di ponsel kanvas jadi kepala bermiring; navy mengembalikan warna lama"),

    ("G15", 4, "Sedang", "Preset Neon & warna manual", "Akun Admin",
     "Identitas & Tema → preset Neon malam → Simpan; buka /login/ & satu dashboard; lalu ubah Warna aksen kedua manual",
     "Login gelap dengan garis pink & cyan, tombol pink bertulisan gelap saat disorot; pratinjau berubah langsung saat "
     "warna diubah; teks di atas setiap warna tetap terbaca; chart bisa memakai skema ALDx Neon"),
    ("G16", 4, "Tinggi", "Preset Tinta & Sakura setelah preset lain", "Akun Admin; nama perusahaan sudah diisi",
     "Identitas & Tema → preset Hijau segar → lalu preset Tinta & Sakura",
     "Warna kembali hitam-abu + pink (bukan tetap hijau); nama aplikasi, nama perusahaan, dan logo TIDAK berubah"),
    ("G14", 4, "Tinggi", "Sematkan dashboard ke web lain", ".env: SPS_SEMATKAN_DOMAIN & SPS_SEMATKAN_KUNCI; halaman uji di domain itu",
     "Sematkan → Nyalakan dashboard latihan → minta token (curl, rls nm_cabang = 'Cabang Bandung') → buka iframe "
     "/sematkan/d/<uuid>?token=…&f.kategori=Elektronik; ulangi dari domain lain; kunci salah; rls berisi ';'",
     "Dashboard tampil tanpa login, hanya Cabang Bandung & Elektronik; domain lain diblokir; kunci salah 401; rls ';' 400; "
     "Matikan → iframe berhenti tampil; halaman ALDx biasa tetap tidak bisa dibingkai"),

    # H. Keamanan
    ("H01", 1, "Tinggi", "RLS dashboard antar-pengguna", "Akun uji cabang: scripts\\data-latihan.ps1 -AkunUji (latihan.bandung, latihan.jakarta)",
     "Keduanya membuka dashboard ber-RLS yang sama", "Masing-masing hanya melihat cabangnya; total berbeda"),
    ("H02", 1, "Tinggi", "Cache tidak bocor", "H01", "Pengguna A membuka dashboard; segera pengguna B membuka chart yang sama",
     "B tidak melihat angka A (kunci cache memakai sidik lingkup)"),
    ("H03", 3, "Tinggi", "Upload ke ClickHouse lain ditolak", "Akses upload; ada koneksi ClickHouse selain ALDx Engine", "Coba upload ke koneksi ClickHouse itu",
     "Ditolak: 'Upload ke ClickHouse hanya diizinkan ke ALDx Engine.'"),
    ("H04", 4, "Tinggi", "Berkas rahasia tidak tersaji", "–", "Buka http://server:8088/.env dan /static/../.env",
     "404, isi .env tidak pernah tampil"),
    ("H05", 4, "Tinggi", "Password tidak tercatat", "A01", "Cari password admin & ENGINE_PASSWORD di installer\\log dan docker compose logs",
     "Tidak ditemukan"),
    ("H06", 4, "Sedang", "Port internal tertutup", "CLUSTER_BIND=127.0.0.1", "Dari komputer lain: Test-NetConnection server -Port 5433/8124/6379",
     "Semua gagal tersambung"),
    ("H07", 2, "Sedang", "Asisten AI memakai hak akses user", "Akun uji cabang", "Tanya total penjualan per cabang",
     "Hanya cabang akun itu yang muncul"),
    ("H09", 3, "Tinggi", "Koneksi wizard hanya-baca", "F12", "SQL Lab pada koneksi baru: jalankan UPDATE/INSERT/DELETE",
     "Ditolak (DML tidak diizinkan)"),
    ("H10", 2, "Tinggi", "Kueri Visual tunduk RLS", "Akun Analis dengan aturan RLS cabang",
     "Kueri Visual → latihan_penjualan → kolom nm_cabang, Jumlah total → Jalankan",
     "Hanya cabang akun itu yang muncul (sama dengan SQL Lab & dashboard)"),
    ("H12", 4, "Tinggi", "Installer: Superadmin email & username LDAP opsional", "Jaringan kantor/VPN (opsional)",
     "PASANG.cmd → Akun Superadmin (email & password) → Login kantor: centang LDAP, isi username Superadmin → Pasang → login dengan email lalu dengan username jaringan",
     "Email selalu bisa login (juga saat LDAP mati); username jaringan melihat tab Pengaturan/Batas data/Hak akses; password tidak ada di .env"),
    ("H13", 1, "Tinggi", "Akun terkunci setelah salah password", "Akun uji", "Login dengan password salah 5 kali, lalu dengan password benar",
     "Pesan 'Akun dikunci sementara… coba lagi pukul …'; password benar ditolak sampai kunci habis atau Admin membuka di Pusat Kendali › Riwayat"),
    ("H14", 4, "Tinggi", "Jejak audit lengkap", "H13; akun Admin", "Unduh CSV dari chart, ekspor berkas .ald, ubah role pengguna, lalu buka Pusat Kendali › Riwayat",
     "Semua aksi tampil dengan waktu, pengguna & alamat IP; Unduh CSV menghasilkan berkas yang terbaca Excel"),
    ("H15", 3, "Tinggi", "Data .aldx impor tertutup untuk orang lain", "Berkas .aldx berisi data; akun Admin & akun cabang",
     "Admin mengimpor dengan 'Pakai data di berkas'; akun cabang membuka dataset hasil impor",
     "Akun cabang melihat 0 baris; ada aturan 'ALDx berkas: … (khusus admin)' di Hak akses data; akun non-Admin tidak bisa mencentang 'Pakai data'"),
    ("H16", 4, "Sedang", "Hak minimum role bawaan", "build-dashboards sudah dijalankan", "Pusat Kendali › Hak akses; login akun Pengguna dan cek menu",
     "Pengguna tidak melihat menu Pusat Kendali/Databases/Action Log; peringatan kuning muncul bila ada non-Admin ber-role Alpha"),
    ("H11", 4, "Tinggi", "Pengaturan vital khusus Superadmin", "Akun Admin biasa (bukan Superadmin)",
     "Buka Pusat Kendali; coba buka ?tab=pengaturan; di Kelola › Pengguna beri diri sendiri role Superadmin",
     "Tab Pengaturan, Batas data, Hak akses tidak tampil; API menjawab 403; pemberian role Superadmin ditolak"),
    ("H08", 4, "Sedang", "Tanpa telemetri pihak ketiga", "–", "Buka DevTools → Network saat membuka dashboard",
     "Tidak ada permintaan ke scarf.sh atau domain luar selain ubin peta"),

    # J. Berkas .ald/.aldx, filter global, komentar & rating (docs/25)
    ("J01", 2, "Tinggi/asap", "Ekspor .ald & impor sebagai salinan", "Dashboard latihan",
     "Dashboard & Story → Berkas .ald / .aldx → Dashboard latihan → .ald → Kunci server → Unduh; lalu Impor berkas itu → Salinan baru",
     "Berkas terunduh; ringkasan 'terverifikasi'; dashboard '(salinan)' terbuka dengan chart yang sama; dataset lama tidak berubah"),
    ("J02", 2, "Tinggi", "Paket .aldx berisi data sesuai hak akses", "Akun uji cabang: scripts\\data-latihan.ps1 -AkunUji (latihan.bandung, latihan.jakarta)",
     "Ekspor .aldx + Sertakan salinan data dengan akun cabang; impor dengan akun admin → Pakai data di berkas",
     "Jumlah baris di ringkasan = baris yang boleh dilihat akun cabang; dashboard hasil impor memakai ALDx Engine"),
    ("J03", 2, "Tinggi", "Berkas berkata sandi & berkas rusak", "J01",
     "Ekspor dengan Kata sandi; impor tanpa sandi, dengan sandi salah, lalu sandi benar; ubah 1 byte berkas lalu impor",
     "Tanpa/salah sandi ditolak; sandi benar terbuka; berkas diubah ditolak"),
    ("J04", 3, "Tinggi", "Berkas tanpa rahasia koneksi", "J01",
     "Cek isi berkas (tidak bisa dibuka tanpa kunci); Impor ke koneksi tujuan lain",
     "Tidak ada alamat/user/password koneksi; hanya koneksi yang boleh diakses penerima yang bisa dipilih"),
    ("J05", 1, "Tinggi/asap", "Filter global di semua dashboard & Story", "Dashboard latihan & latihan-wilayah (keduanya punya filter Kategori)",
     "Tombol corong → Kategori = Elektronik → Terapkan; buka dashboard lain & Story",
     "Kedua dashboard langsung tersaring Elektronik (209B dan 5,45T); lencana corong = 1; hapus semua = kembali normal"),
    ("J12", 1, "Tinggi", "Telusuri ke dashboard lain (drill-through)", "Dashboard latihan & latihan-wilayah",
     "Dashboard latihan → klik irisan Elektronik di pie → tombol Telusuri → pilih Latihan: Wilayah & Prediksi → "
     "klik chip ← di bilah atas",
     "Panel menulis 'kategori: Elektronik' dan menawarkan dashboard Wilayah; tujuan terbuka tersaring (total 5,45 T); "
     "chip Kembali mengantar ke dashboard asal; tanpa filter aktif panel memberi petunjuk"),
    ("D25", 2, "Tinggi", "Kalkulasi cepat: % dari total & kumulatif", "latihan_penjualan",
     "Studio → periode ke Kolom, total ke Baris, Garis → Hitung = % dari total, lalu Kumulatif → Simpan baru → buka di Explore",
     "% dari total: sumbu bertanda %, jumlah semua titik 100%; Kumulatif: garis selalu naik, titik akhir = total (±667 M); "
     "chart tersimpan sama dengan pratinjau; pilihan Hitung mati untuk Pie"),
    ("D26", 2, "Sedang", "Skala warna tabel & Kelompokkan nilai", "latihan_penjualan",
     "Tabel nm_cabang × total → centang Skala warna sel; klik kanan nm_cabang → Kelompokkan nilai… → kelompok Jawa = "
     "Jakarta, Bandung, Surabaya; nilai lain = Lainnya → Buat dimensi → pakai di Batang",
     "Sel Jakarta paling pekat; dimensi nm_cabang_kelompok bertanda ƒ; batang Jawa ±493 M dan Lainnya ±175 M; "
     "klik kanan → Ubah rumus… menampilkan CASE WHEN"),
    ("D27", 2, "Tinggi", "Dashboard dari template", "latihan_penjualan",
     "Susun dashboard → Dari template… → dataset latihan_penjualan, ukuran utama total, Ringkasan eksekutif → Buat → "
     "Simpan dashboard → Buka; ulangi untuk dua template lain",
     "Kanvas terisi judul, kotak angka, tren + ramalan, komposisi, 10 teratas, peta; filter Saluran/Kategori/Cabang/"
     "Rentang waktu terpasang; dashboard terbuka tanpa galat dan filter menyaring semua chart"),
    ("D28", 2, "Tinggi", "YoY (% vs tahun lalu)", "latihan_penjualan",
     "Studio → periode ke Kolom, total ke Baris, Garis → Hitung = % vs tahun lalu (YoY) → Simpan baru → buka di Explore; "
     "ganti dimensi ke nm_cabang",
     "12 bulan pertama kosong; Januari 2024 ±15,8%; chart tersimpan menampilkan angka yang sama; pilihan YoY mati "
     "untuk dimensi bukan tanggal"),
    ("J13", 1, "Tinggi", "Tampilan tersimpan (bookmark)", "Dashboard Latihan: Wilayah & Prediksi",
     "Pilih Kategori = Elektronik → Terapkan → Telusuri → nama 'Elektronik saja' → Simpan tampilan ini; hapus filter; "
     "Telusuri → klik 'Elektronik saja'; login akun lain; hapus dengan ×",
     "Dashboard terbuka tersaring Elektronik; tampilan tidak terlihat di akun lain; × menghapus; tanpa filter aktif "
     "kotak simpan tidak muncul"),
    ("F25", 3, "Sedang", "Jejak data (lineage)", "A10; akun Analis dengan akses terbatas",
     "Data → Jejak data → pilih latihan_penjualan → arahkan kursor ke sebuah dashboard → klik sebuah chart; ulangi sebagai Analis",
     "Empat kolom Sumber/Dataset/Chart/Dashboard terisi; chart pemakai tersorot; klik membuka chart; Analis hanya melihat "
     "dataset & chart yang boleh ia akses"),
    ("K13", 1, "Sedang", "Label kesegaran data", "Dashboard latihan",
     "Buka dashboard latihan → lihat label di bilah atas → arahkan kursor → klik",
     "Label 'Data: … lalu' tampil; tooltip merinci tiap dataset & waktu diperbarui; klik membuka Jejak data; "
     "label hilang di halaman selain dashboard"),
    ("D29", 2, "Sedang", "Simulasi what-if", "latihan_penjualan",
     "Studio → nm_cabang × total, Batang → geser Simulasi ke +10% → Simpan baru → buka chart tersimpan",
     "Batang naik 10% (total ±667 M → ±734 M); status menulis 'hanya pratinjau'; chart tersimpan tetap nilai asli; "
     "slider mati saat Hitung dipakai"),
    ("J14", 1, "Tinggi", "Drill-through lewat klik kanan", "Dashboard latihan",
     "Klik kanan sebuah sel/batang/irisan pada chart → Telusuri ke dashboard lain… → pilih dashboard tujuan; ulangi pada kotak angka",
     "Butir muncul di menu klik kanan; panel Telusuri terbuka dengan nilai yang diklik sebagai filter; tujuan terbuka "
     "tersaring; pada kotak angka menu menutup dan panel memberi petunjuk"),
    ("D30", 2, "Tinggi", "Dashboard bertab & tinggi kotak", "Studio, 3 lembar kerja",
     "Susun dashboard → 2 lembar kerja di tab 1, tinggi kotak pertama 'Sangat tinggi' → + Tab → klik dua kali → 'Rincian' "
     "→ lembar ke-3 → Simpan → buka dashboard → buka lagi di Studio",
     "Dashboard punya tab Tab 1 & Rincian; kotak pertama lebih tinggi; lembar yang sama ditolak di tab lain; dibuka "
     "lagi di Studio dengan tab & tinggi yang sama"),
    ("D31", 2, "Sedang", "Tooltip kaya & Jelaskan perubahan", "latihan_penjualan",
     "Garis periode × total → arahkan kursor ke Februari 2024 → klik kanan Maret 2024 → Jelaskan perubahan",
     "Tooltip menulis porsi dari total & ▲ 9,1% vs sebelumnya; dialog: naik ±1,6 M (+10%), saluran paling menjelaskan, "
     "Online & Grosir penyumbang terbesar"),
    ("E10", 2, "Sedang", "Analitik per Warna", "latihan_penjualan",
     "Garis periode × total, saluran ke Warna → centang Garis tren & Ramalan → Simpan baru",
     "Tiap saluran punya garis tren & ramalan; seri tidak bertumpuk; simpan memberi catatan 'hanya tampil di Studio'"),
    ("K14", 1, "Sedang", "Ekspor dashboard ke PowerPoint", "Dashboard latihan-wilayah",
     "Buka dashboard → tombol PowerPoint di bilah atas → buka berkas di PowerPoint/LibreOffice",
     "Berkas .pptx terunduh: slide sampul + satu chart per slide dengan judul; tombol tidak tampil di halaman selain dashboard"),
    ("G20", 4, "Sedang", "Kesehatan kueri", "Akun Admin; beberapa dashboard sudah dibuka",
     "Kelola → Kesehatan kueri → ganti periode 24 jam / 30 hari; buka sebagai akun bukan Admin",
     "Ringkasan (median, p95, lambat, gagal), chart & dashboard terurut p95 dengan saran; akun bukan Admin ditolak"),
    ("H17", 4, "Tinggi", "Masuk dengan SSO", "Aplikasi terdaftar di Entra ID/Google/Keycloak; SSO_* di .env",
     "Halaman login → Masuk dengan … → login di penyedia; ulangi dengan email domain lain; matikan internet lalu login password",
     "Akun dengan domain benar masuk (dibuat otomatis bila SSO_BUAT_AKUN=1); domain lain ditolak dengan pesan; login "
     "password tetap berfungsi; tercatat di jejak audit"),
    ("K15", 2, "Tinggi", "Asisten AI: gabung dataset detail", "Model AI tersambung; izin membuat dataset",
     "Panel ✦ → 'dari latihan_cabang, latihan_lokasi_pelanggan, latihan_penjualan buatkan dataset detail' → buka tautan "
     "dataset → hitung baris; login akun Latihan Cabang Bandung",
     "Dataset baru = latihan_penjualan + kolom cabang (4.320 baris, total sama dengan asal); latihan_lokasi_pelanggan "
     "dilewati dengan alasan banyak-ke-banyak; akun Bandung hanya melihat kd_cabang C02"),
    ("K16", 1, "Sedang", "Asisten AI: model lambat", "Model lokal kecil tanpa GPU",
     "Ajukan permintaan bertahap (mis. buat dashboard 4 chart)",
     "Bila melewati ±5 menit, jawaban menyebut langkah yang sudah selesai dan saran; tidak ada pesan 'tidak terbaca'"),
    ("K12", 3, "Sedang", "Peringatan data", "SMTP terpasang (tanpa SMTP: cek log)",
     "Dashboard & Story → Peringatan data → + Peringatan → SQL SELECT SUM(total) FROM latihan_penjualan, syarat > 0, "
     "jadwal tiap menit, penerima email sendiri",
     "Peringatan tercatat berjalan; email diterima (atau tercatat di log bila mode uji); masa tenang mencegah email berulang"),
    ("K11", 1, "Sedang", "Asisten AI: ringkas dashboard", "Model AI tersambung",
     "Buka sebuah dashboard → panel ✦ → klik Ringkas dashboard ini dalam 5 poin",
     "Tombol cepat hanya muncul di halaman dashboard; jawaban merujuk angka di dashboard yang sedang dibuka"),
    ("J06", 1, "Sedang", "Komentar & rating dimoderasi", "Akun pengguna & Superadmin",
     "Pengguna: dashboard → tombol komentar → 4 bintang + komentar → Kirim; Superadmin: Kelola → Moderasi ulasan → Tampilkan",
     "Sebelum disetujui hanya penulis & Superadmin yang melihat; sesudahnya semua; rata-rata rating tampil"),
    ("J07", 1, "Sedang", "Balasan & @sebut", "J06; dua akun", "A menulis komentar menyebut @B; B membalas komentar A",
     "Saran nama muncul saat mengetik @; B mendapat titik di avatar & pemberitahuan; balasan tampil menjorok di bawah komentar A"),
    ("J08", 1, "Sedang", "Filter global rentang & per akun", "Dashboard latihan-wilayah (filter Tahun rentang & Rentang waktu)",
     "Corong → Tahun dari 2024 sampai 2025 → Terapkan (lalu ganti: Rentang waktu, Tanggal tertentu 2025-01-01 : 2026-01-01); buka ALDx dari komputer/ponsel lain",
     "Total penjualan 10T (2024-2025), lalu 5,2T (tahun 2025); filter yang sama sudah aktif di perangkat lain"),
    ("J09", 3, "Sedang", "Ekspor .aldx besar di latar", "Backgrounder menyala; dashboard dengan data", "Ekspor .aldx + data → pindah halaman → kembali ke Berkas",
     "Pesan 'disiapkan di latar'; bagian Ekspor terakhir berubah siap; Unduh berhasil; akun lain tidak bisa mengunduh"),
    ("J11", 1, "Sedang", "Filter global: pilih nilai, chip & kecualikan", "Dashboard latihan; layar ≥ 1280 px",
     "Corong → Cabang → ketik 'ban' → pilih Cabang Bandung dari daftar → Terapkan; × pada chip di bilah atas; "
     "terapkan lagi lalu centang Kecualikan dashboard ini → Terapkan",
     "Daftar nilai hanya berisi cabang yang boleh dilihat; chip 'Cabang Bandung' tampil & angka tersaring; × = kembali normal; "
     "dikecualikan = dashboard tanpa filter, chip redup bertanda 'dikecualikan', dashboard lain tetap tersaring"),
    ("J10", 4, "Rendah", "Moderasi massal", "≥ 3 komentar menunggu", "Moderasi ulasan → Pilih semua → Tampilkan terpilih",
     "Semua tampil; lencana jumlah menunggu di menu & avatar hilang; tercatat di jejak audit"),

    # K. Dashboard lanjutan & kenyamanan
    ("K01", 2, "Tinggi", "Riwayat versi & pulihkan", "Pemilik dashboard", "Ubah judul/tata letak → Simpan → Riwayat versi → Pulihkan versi sebelumnya",
     "Judul/tata letak kembali; versi sebelum pemulihan tercatat; pengguna bukan pemilik tidak bisa memulihkan"),
    ("K02", 2, "Sedang", "Tata letak ponsel", "Pemilik dashboard; ponsel", "Tata ponsel → balik urutan, sembunyikan 1 chart → Simpan → buka di ponsel",
     "Urutan sesuai pengaturan, chart tersembunyi tidak tampil; layar lebar tidak berubah"),
    ("K03", 3, "Tinggi", "Lihat sebagai…", "Admin; dua akun beda cabang", "Kelola → Lihat sebagai… → akun cabang A → dashboard latihan → Tampilkan",
     "Setiap chart menampilkan angka cabang A & aturan RLS-nya; tercatat di jejak audit; akun non-Admin ditolak (403)"),
    ("K04", 3, "Sedang", "Langganan laporan", "SMTP_* di .env", "Langganan laporan → + Laporan chart, CSV, jadwal tiap jam ke email sendiri",
     "Email berisi CSV diterima; tanpa SMTP_HOST laporan hanya tercatat (tidak dikirim)"),
    ("K05", 2, "Rendah", "Lencana Resmi", "Pemilik dashboard", "Ubah properti → Sertifikasi: Tim Data → buka Beranda & Ctrl+K",
     "Lencana Resmi di Beranda; dashboard itu paling atas di hasil cari"),
    ("K06", 2, "Sedang", "Kueri Visual tersimpan", "Akun Analis", "Kueri Visual: gabung 2 tabel → nama → Simpan kueri → muat ulang → buka dari Kueri tersimpan",
     "Susunan kembali lengkap; Jalankan memberi hasil sama; kueri tidak terlihat akun lain"),
    ("K07", 1, "Rendah", "Mode gelap", "–", "Avatar → Tampilan → Gelap; buka dashboard & SQL Lab; kembali Terang",
     "Cangkang, dashboard & SQL Lab gelap dan terbaca; kembali terang tanpa sisa"),
    ("K08", 1, "Sedang", "Warna kategori sama", "Dua akun beda cabang", "Keduanya membuka chart Komposisi kategori",
     "Warna tiap kategori sama untuk kedua akun"),
    ("K09", 4, "Tinggi", "Cadangan terjadwal & uji pulih", "Windows server, admin", "jadwal-cadangan.ps1 → Start-ScheduledTask kedua tugas → Pusat Kendali Status",
     "Kartu Cadangan terakhir hijau & uji pulih OK; backup\\cadangan.log berisi OK"),
    ("K10", 4, "Sedang", "Uji beban", "Di luar jam kerja", "uji-beban.ps1 -Akun <admin> -Pengguna 50 -Detik 120",
     "KESIMPULAN: CUKUP (p95 < 5 dtk, gagal < 1%), atau ikuti saran sizing bila KURANG"),

    # I. Kinerja
    ("I01", 1, "Sedang", "Dashboard ekstrak cepat", "Dashboard memakai ekstrak", "Buka dashboard (cache dikosongkan: Force refresh)",
     "Semua chart < 3 detik"),
    ("I02", 4, "Sedang", "Beban bersamaan", "≥ 20 penguji", "Semua membuka & menyaring dashboard latihan pada menit yang sama",
     "Tidak ada galat; Status: CPU web < 85%; antrean kembali 0 dalam 1 menit"),
    ("I03", 4, "Sedang", "Penyegaran ekstrak besar", "Sumber ≥ 10 juta baris", "Segarkan ekstrak penuh saat jam kerja",
     "Dashboard tetap bisa dibuka selama penyegaran; selesai < batas 6 jam"),
    ("I04", 4, "Rendah", "Ramalan harian", "Ada chart ramalan", "Cek keesokan hari setelah 03:00",
     "Kolom diperbarui di tabel sps_ramalan berganti; chart memuat data terbaru"),
    ("I05", 3, "Sedang", "Data besar 1 juta tiket", "scripts\\data-penerbangan.ps1 (berkas besar dibuat)",
     "Hubungkan data → Berkas → contoh-penerbangan-besar.xlsx → Impor; buat chart pendapatan per bulan dari tiket + jadwal; "
     "ulangi setelah ekstrak",
     "Impor selesai tanpa melebihi batas (atau pesan batas jelas); 1.000.000 baris tiket; pendapatan Rp2,28 triliun; "
     "chart tampil < 5 detik setelah ekstrak"),
]

LEVEL = {1: "1 Pengguna", 2: "2 Analis", 3: "3 Admin data", 4: "4 Admin server"}


def tulis_md() -> None:
    baris = ["# Skenario Uji (UAT) ALDx", "",
             "Dihasilkan dari `skenario.py`. Isi hasilnya di **`lembar-uji.xlsx`**.", "",
             f"Total **{len(SKENARIO)} skenario**. Prioritas *Tinggi* wajib lulus sebelum dipakai pengguna.", "",
             "## Uji asap (± 15 menit)", "",
             "Setelah instalasi/upgrade, jalankan `scripts\\uji.ps1` lalu skenario bertanda **asap**: " +
             ", ".join(s[0] for s in SKENARIO if "asap" in s[2]) + ".", ""]
    for kode, nama in AREA.items():
        baris += [f"## {kode}. {nama}", "",
                  "| ID | Level | Prioritas | Skenario | Prasyarat | Langkah | Hasil diharapkan |",
                  "|---|---|---|---|---|---|---|"]
        for s in SKENARIO:
            if s[0].startswith(kode):
                baris.append("| " + " | ".join([s[0], LEVEL[s[1]], s[2], s[3], s[4], s[5], s[6]]).replace("\n", " ") + " |")
        baris.append("")
    (FOLDER / "skenario-uji.md").write_text("\n".join(baris), encoding="utf-8")


def tulis_xlsx() -> None:
    from openpyxl import Workbook
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    huruf = Font(name="Arial", size=10)
    tebal = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    judul = Font(name="Arial", size=14, bold=True, color="1F4E79")
    navy = PatternFill("solid", fgColor="1F4E79")
    isian = PatternFill("solid", fgColor="FFF6DB")
    garis = Border(*(Side(style="thin", color="D5DCE4"),) * 4)
    bungkus = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()
    # --- Petunjuk
    p = wb.active
    p.title = "Petunjuk"
    teks = [("Lembar Uji (UAT) ALDx", judul), ("", huruf),
            ("1. Kerjakan skenario di sheet 'Skenario Uji' berurutan per area.", huruf),
            ("2. Isi HANYA kolom berlatar kuning: Hasil, Catatan, Penguji, Tanggal.", huruf),
            ("3. Hasil: Lulus · Gagal · Diblokir (tidak bisa diuji karena skenario lain gagal) · Tidak diuji.", huruf),
            ("4. Bila Gagal: tulis apa yang terjadi + tangkapan layar (nama berkas) di Catatan.", huruf),
            ("5. Sheet 'Ringkasan' terhitung otomatis.", huruf), ("", huruf),
            ("Contoh pengisian (jangan diketik di sheet Skenario Uji):", Font(name="Arial", size=10, bold=True))]
    for i, (t, f) in enumerate(teks, 1):
        p.cell(row=i, column=1, value=t).font = f
    contoh = [("ID", "Hasil", "Catatan", "Penguji", "Tanggal"),
              ("C02", "Gagal", "Filter Kesehatan & Kecantikan: total tetap 667B. Layar: C02.png", "Budi (Cabang Bandung)", "2026-11-03")]
    for r, row in enumerate(contoh, len(teks) + 1):
        for c, v in enumerate(row, 1):
            cell = p.cell(row=r, column=c, value=v)
            cell.font = tebal if r == len(teks) + 1 else huruf
            if r == len(teks) + 1:
                cell.fill = navy
    p.column_dimensions["A"].width = 18
    for col in "BCDE":
        p.column_dimensions[col].width = 26
    p.column_dimensions["C"].width = 48

    # --- Skenario
    s = wb.create_sheet("Skenario Uji")
    kepala = ["ID", "Area", "Level", "Prioritas", "Skenario", "Prasyarat", "Langkah", "Hasil diharapkan",
              "Hasil", "Catatan", "Penguji", "Tanggal"]
    lebar = [7, 22, 13, 12, 30, 26, 48, 48, 12, 34, 16, 12]
    for c, (h, w) in enumerate(zip(kepala, lebar), 1):
        cell = s.cell(row=1, column=c, value=h)
        cell.font, cell.fill, cell.alignment, cell.border = tebal, navy, bungkus, garis
        s.column_dimensions[get_column_letter(c)].width = w
    for r, sk in enumerate(SKENARIO, 2):
        nilai = [sk[0], AREA[sk[0][0]], LEVEL[sk[1]], sk[2], sk[3], sk[4], sk[5], sk[6], None, None, None, None]
        for c, v in enumerate(nilai, 1):
            cell = s.cell(row=r, column=c, value=v)
            cell.font, cell.alignment, cell.border = huruf, bungkus, garis
            if c >= 9:
                cell.fill = isian
        s.cell(row=r, column=12).number_format = "yyyy-mm-dd"
    akhir = len(SKENARIO) + 1
    dv = DataValidation(type="list", formula1='"Lulus,Gagal,Diblokir,Tidak diuji"', allow_blank=True)
    s.add_data_validation(dv)
    dv.add(f"I2:I{akhir}")
    hijau, merah = PatternFill("solid", fgColor="E3F6EE"), PatternFill("solid", fgColor="FDECEC")
    s.conditional_formatting.add(f"I2:I{akhir}", CellIsRule(operator="equal", formula=['"Lulus"'], fill=hijau))
    s.conditional_formatting.add(f"I2:I{akhir}", CellIsRule(operator="equal", formula=['"Gagal"'], fill=merah))
    s.freeze_panes = "B2"
    s.auto_filter.ref = f"A1:L{akhir}"

    # --- Ringkasan (rumus)
    g = wb.create_sheet("Ringkasan")
    g["A1"] = "Ringkasan hasil uji"
    g["A1"].font = judul
    kol = ["Area", "Jumlah", "Lulus", "Gagal", "Diblokir", "Belum diisi", "% Lulus", "Prioritas Tinggi gagal"]
    for c, h in enumerate(kol, 1):
        cell = g.cell(row=3, column=c, value=h)
        cell.font, cell.fill, cell.border = tebal, navy, garis
    rng = lambda k: f"'Skenario Uji'!${k}$2:${k}${akhir}"  # noqa: E731
    for r, nama in enumerate(AREA.values(), 4):
        g.cell(row=r, column=1, value=nama)
        g.cell(row=r, column=2, value=f'=COUNTIF({rng("B")},A{r})')
        for c, hasil in ((3, "Lulus"), (4, "Gagal"), (5, "Diblokir")):
            g.cell(row=r, column=c, value=f'=COUNTIFS({rng("B")},$A{r},{rng("I")},"{hasil}")')
        g.cell(row=r, column=6, value=f'=COUNTIFS({rng("B")},$A{r},{rng("I")},"")')
        g.cell(row=r, column=7, value=f"=IF(B{r}=0,0,C{r}/B{r})")
        g.cell(row=r, column=8, value=f'=COUNTIFS({rng("B")},$A{r},{rng("I")},"Gagal",{rng("D")},"Tinggi*")')
    t = 4 + len(AREA)
    g.cell(row=t, column=1, value="TOTAL").font = Font(name="Arial", size=10, bold=True)
    for c in range(2, 9):
        huruf_kol = get_column_letter(c)
        g.cell(row=t, column=c, value=f"=IF(B{t}=0,0,C{t}/B{t})" if c == 7 else f"=SUM({huruf_kol}4:{huruf_kol}{t - 1})")
    for r in range(4, t + 1):
        g.cell(row=r, column=7).number_format = "0.0%"
        for c in range(1, 9):
            g.cell(row=r, column=c).border = garis
            if g.cell(row=r, column=c).font != Font(name="Arial", size=10, bold=True):
                g.cell(row=r, column=c).font = huruf if r < t else Font(name="Arial", size=10, bold=True)
    g.cell(row=t + 2, column=1, value="Siap dipakai pengguna bila: Prioritas Tinggi gagal = 0 dan semua skenario Tinggi berstatus Lulus.").font = huruf
    g.column_dimensions["A"].width = 36
    for c in "BCDEFGH":
        g.column_dimensions[c].width = 13
    g.column_dimensions["H"].width = 22
    wb.save(FOLDER / "lembar-uji.xlsx")


if __name__ == "__main__":
    tulis_md()
    tulis_xlsx()
    print(f"{len(SKENARIO)} skenario -> skenario-uji.md, lembar-uji.xlsx")
