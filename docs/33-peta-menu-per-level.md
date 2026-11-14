# 33 · Peta Menu per Level

Satu halaman untuk menjawab: **"menu ini untuk siapa, fungsinya apa, dan belajarnya di mana?"**
Urutan baris mengikuti **sidebar** aplikasi (Data › Kueri › Visual › Dashboard & Story › Asisten › Kelola).

## Cara membaca

| Level | Peran bawaan | Intinya | Belajar |
|---|---|---|---|
| **L1 · Pengguna** | Pengguna | membaca & menyaring dashboard, bertanya ke AI | [tutorial](tutorial/level-1-pengguna.md) · [bahan ajar](bahan-ajar/level-1-pengguna.md) |
| **L2 · Analis** | Analis | membuat chart, dashboard, kueri tanpa SQL, laporan terjadwal | [tutorial](tutorial/level-2-analis.md) · [bahan ajar](bahan-ajar/level-2-analis.md) |
| **L3 · Admin data** | Admin | menyambung sumber, menyiapkan dataset, hak akses data, ekstrak | [tutorial](tutorial/level-3-admin-data.md) · [bahan ajar](bahan-ajar/level-3-admin-data.md) |
| **L4 · Admin server** | Admin / Superadmin | memasang, memantau, mengamankan, memperbarui | [tutorial](tutorial/level-4-admin-server.md) · [bahan ajar](bahan-ajar/level-4-admin-server.md) |

Setiap level mengandaikan level sebelumnya. Menu yang tidak diizinkan untuk akun Anda **tidak tampil** di sidebar
(bukan tampil lalu ditolak). Kolom *Akses*: **semua** = semua akun yang login; **izin** = tampil bila role akun punya
izin itu (Analis ke atas biasanya); **Admin** / **Superadmin** = khusus peran tersebut.

## Data

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Hubungkan data** | wizard menyambung database / data warehouse / berkas Access, Excel, CSV; impor banyak tabel | L3 | Admin | L3 §1, §5a |
| **Dataset** | daftar & pengaturan dataset (tabel yang menjadi bahan chart) | L3 | izin | L3 §2 |
| **Jejak data** | sumber → dataset → chart → dashboard; lihat dampak sebelum mengubah/menghapus | L2–L3 | semua yang boleh melihat dataset | L2 §12e, L3 §6a |
| **Persiapan data** | pilih/ganti nama/ubah tipe/hitung/gabung/ringkas kolom tanpa SQL | L3 | izin | L3 §3 |
| **Ekstrak ke ALDx Engine** | salin data ke mesin kolom (ALDx Engine) agar dashboard cepat; jadwal penyegaran | L3 | Admin | L3 §5 |

## Kueri

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Kueri Visual** | klik dua kali tabel = kueri jadi; tabel kedua digabung otomatis; simpan jadi dataset | L2 | izin (Analis) | L2 §12 |
| **SQL Lab** | menulis SQL sendiri (hanya baca) | L2–L3 | izin (`sql_lab`) | L3 §2 |
| **Kueri tersimpan** | kueri yang disimpan dari Kueri Visual / SQL Lab | L2 | izin | L2 §12b |

## Visual

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Studio Visual** | seret-lepas, 23 jenis chart, peta, ramalan, kalkulasi cepat, ambang, simulasi & skenario tersimpan, mini-chart tooltip, susun dashboard (tab, template umum & per bidang) | L2 | semua yang boleh membuat chart | L2 §1–11a |
| **Daftar chart** | mencari, membuka, mengubah, menghapus chart yang pernah dibuat | L2 | izin | L2 §12e |

## Dashboard & Story

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Daftar dashboard** | mencari & membuka dashboard, favorit | L1 | semua | L1 §2–6 |
| **Story** | presentasi berurutan dari dashboard, narasi bisa ditulis AI | L1 (baca) · L2 (buat) | semua / izin | L1 §2, L2 §11 |
| **Langganan laporan** | kirim chart/dashboard lewat email terjadwal | L2 | izin | L2 §12d |
| **Peringatan data** | email hanya bila angka melewati ambang | L2 | izin | L2 §12d |
| **Berkas .ald / .aldx** | simpan & bagikan dashboard/chart/dataset sebagai berkas terenkripsi | L2 | izin | L2 §12a |
| **Sematkan ke web lain** | tampilkan dashboard di portal/aplikasi lain (token tamu + RLS) | L4 | Admin | L4 §10a |

## Asisten

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Auto chart & dashboard** | pilih dataset → saran chart berskor → dashboard jadi | L2 | izin | L2 §12c |
| **Panduan** | dokumentasi di dalam aplikasi (cari, daftar isi, tanpa internet) | L1 | semua | L1 §1 |

## Kelola

| Menu | Fungsi | Level | Akses | Bagian tutorial |
|---|---|---|---|---|
| **Asisten AI** (pengaturan) | sambungkan model lokal/gratis/berbayar, kunci, model bawaan | L4 | Admin | L4 §4c |
| **Pusat Kendali** | status, topologi, pengaturan server, batas data, identitas, riwayat | L4 | Admin (sebagian Superadmin) | L4 §2–7 |
| **Pengguna** | akun, role, aktif/nonaktif | L3–L4 | izin Admin | L3 §4, L4 §5 |
| **Role** | kumpulan izin per peran | L3–L4 | izin Admin | L3 §4, L4 §5 |
| **Lihat sebagai…** | melihat dashboard persis seperti pengguna lain (uji hak akses) | L3 | Admin | L3 §4 |
| **Hak akses data (RLS)** | aturan baris yang boleh dilihat per role | L3 | izin Admin | L3 §4 |
| **Kesehatan kueri** | chart/dashboard lambat (p95), kueri gagal, saran perbaikan | L4 | Admin | L4 §6a |
| **Riwayat kueri** | riwayat kueri SQL Lab | L3–L4 | izin | L3 §6d |
| **Moderasi ulasan** | menyetujui komentar & rating | L4 | Superadmin | L4 §6 |
| **Jejak audit** | siapa melakukan apa (login, unduh, ekspor, hak akses) | L4 | Admin | L4 §6 |

## Alat yang ada di setiap halaman

Bukan menu sidebar, tetapi dipakai semua level:

| Alat | Cara | Level | Bagian tutorial |
|---|---|---|---|
| **Cari / perintah** | `Ctrl + K` | L1 | L1 §1 |
| **Asisten AI** (panel ✦) | `Ctrl + I`; peran `/analis` `/panduan` `/data-engineer` `/ahli-ui-ux` `/hw-engineer` | L1 (pakai) · L3–L4 (data/server) | L1 §6, L3 §6b, L4 §4c |
| **Ringkasan AI** (bilah atas dashboard) | chip ✦ Ringkasan AI: 3–5 poin berangka + *Perlu perhatian*; Perbarui, Tanya lanjut | L1 (baca) · L4 (mode `otomatis`/`klik`/`mati`) | L1 §6, L4 §4c |
| **Cara pakai halaman** | tombol `?` | L1 | L1 §1 |
| **Ekspor** tabel & grafik | tombol Ekspor di pojok: PNG, PDF, Excel, CSV, TXT, salin | L1 | L1 §6a |
| **Filter global** | tombol corong di bilah atas | L1 | L1 §6b |
| **Komentar & rating** | tombol komentar saat dashboard terbuka | L1 | L1 §6c |
| **Telusuri ke dashboard lain** | tombol Telusuri, atau klik kanan chart | L1 | L1 §6e |
| **Tampilan tersimpan** | di panel Telusuri: simpan keadaan filter dengan nama | L1 | L1 §6e |
| **Label kesegaran data** | bilah atas dashboard: *Data: 2 jam lalu* / *Data langsung* | L1 | L1 §6e |
| **Ekspor PowerPoint** | tombol layar presentasi di bilah atas dashboard | L1 | L1 §6e |
| **Mode gelap, bahasa ID/EN/日本語, ponsel** | menu avatar | L1 | L1 §6d |

## Alur kerja 5 langkah (angka di sidebar)

| Langkah | Menu | Hasil |
|---|---|---|
| 1 | Hubungkan data → Dataset | sumber tersambung, dataset siap |
| 2 | Persiapan data (atau Kueri Visual) | data bersih & tergabung |
| 3 | Studio Visual | chart |
| 4 | Daftar dashboard / Susun dashboard | dashboard |
| 5 | Story, Langganan laporan, Ekspor PowerPoint, Sematkan | dibagikan ke pembaca |

Jalan pintas: minta **Asisten AI** (`Ctrl + I`) — *"gabungkan dataset A, B, C"*, *"scan tabel berawalan data_"*,
*"buat dashboard dari dataset ini"* — lalu lanjutkan hasilnya di Studio Visual.

## Jalur belajar menurut peran pekerjaan

| Anda… | Mulai dari | Lalu |
|---|---|---|
| hanya membaca laporan | L1 (1 jam) | selesai; ulangi §6e bila perlu |
| membuat laporan unit kerja | L1 → L2 (3 jam) | Auto chart, laporan terjadwal (L2 §12c–d) |
| mengelola data unit/divisi | L1 → L2 → L3 (3 jam) | Jejak data, gabung via Asisten (L3 §6a–b) |
| tim TI / pengelola server | L1 → L4 (4 jam), L3 bagian RLS | Runbook ([19](19-runbook-faq-admin.md)), audit keamanan ([27](27-daftar-periksa-audit-keamanan.md)) |

Rencana pelatihan lengkap untuk pengajar (kalender, penilaian, tindak lanjut): [bahan-ajar/alur-pelatihan.md](bahan-ajar/alur-pelatihan.md).
