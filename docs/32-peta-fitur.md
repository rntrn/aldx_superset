# 32 · Peta Fitur & Peta Jalan

Daftar kemampuan ALDx beserta letaknya. Dipakai sebagai **peta jalan**: apa yang sudah ada,
apa yang baru diadopsi, dan apa yang sengaja ditunda beserta alasannya.

Status: ✅ ada · 🆕 baru diadopsi (November 2026) · ⏳ kandidat berikutnya · ✖ tidak diadopsi.

## 1. Ringkasan

| Fitur | ALDx | Di mana |
|---|---|---|
| Seret-lepas kolom ke rak, saran jenis chart otomatis | ✅ | Studio Visual ([12](12-studio-visual.md)) |
| Hierarki & telusur bertingkat | ✅ | Studio › Hierarki |
| **Ukuran & kolom terdefinisi** (rumus tersimpan) | 🆕 | Studio › **+ Ukuran / + Dimensi** |
| **Telusuri ke dashboard lain** antar halaman dengan filter terbawa | 🆕 | tombol **Telusuri** atau **klik kanan chart** di dashboard ([25 §2b](25-berkas-filter-global-ulasan.md)) |
| **N teratas** | 🆕 | Studio › *N teratas* |
| Klik-filter antar-chart, lihat detail baris, telusur per dimensi | ✅ | dashboard |
| Ramalan, tren, garis acuan, anomali | ✅ | Studio › Analitik ([17](17-katalog-chart-peta-prediksi.md)) |
| Ekstrak ke mesin kolom | ✅ | ALDx Engine ([13](13-sps-engine-ekstrak.md)) |
| Lapisan semantik: metrik didefinisikan sekali, dipakai semua | ✅/🆕 | definisi tersimpan di **dataset**: dipakai semua chart, Explore & pengguna |
| Rumus gaya spreadsheet langsung di atas data gudang | 🆕 (sebagian) | dialog rumus: klik kolom, contoh rumus, **Uji rumus** |
| Tanya data dengan bahasa sehari-hari | ✅ | Asisten AI ([23](23-asisten-ai-peran-ahli.md)) |
| Sematkan dengan RLS per penonton | ✅ | [30](30-sematkan-dashboard.md) |
| Langganan laporan, riwayat versi, tata letak ponsel | ✅ | [26](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Presentasi berurutan | ✅ | Story |
| Parameter *what-if* (geser angka, chart ikut berubah) | 🆕 (sebagian) | Studio › **Simulasi** (pratinjau, tidak tersimpan) |
| Jelaskan kenaikan/penurunan | 🆕 | Studio: klik kanan periode → **Jelaskan perubahan** |
| Tooltip kaya | 🆕 | Studio: porsi & perubahan di tooltip |
| Tab & ukuran kotak di dashboard | 🆕 | Studio › Susun dashboard (grid 12 kolom; posisi bebas piksel sengaja tidak) |
| Ekspor PowerPoint | 🆕 | tombol PowerPoint di dashboard |
| SSO (OpenID Connect / Azure AD) | 🆕 | [05](05-login-ldap.md#masuk-dengan-sso-openid-connect) |
| Pemantauan kinerja kueri | 🆕 | Kelola › **Kesehatan kueri** |
| Label kesegaran data | 🆕 | bilah atas dashboard ([26 §7b](26-langganan-versi-ponsel-lihat-sebagai.md)) |
| **Kalkulasi cepat** (% dari total, kumulatif, YoY) | 🆕 | Studio › **Hitung** |
| **Template dashboard** | 🆕 | Susun dashboard › **Dari template…** |
| **Kelompokkan nilai**  & skala warna tabel | 🆕 | Studio: klik kanan dimensi; Tabel › *Skala warna sel* |
| Peringatan data saat angka melewati ambang | ✅ | menu **Peringatan data** ([26 §1b](26-langganan-versi-ponsel-lihat-sebagai.md)) |
| **Jejak data** (asal-usul & dampak perubahan) | 🆕 | menu **Data › Jejak data** ([26 §7](26-langganan-versi-ponsel-lihat-sebagai.md)) |
| Simpan keadaan filter bernama | 🆕 | **Tampilan tersimpan** di panel Telusuri ([25 §2c](25-berkas-filter-global-ulasan.md)) |
| Tabel input (ketik data langsung ke gudang) | ✖ | menulis ke database sumber berisiko; pakai impor Excel/CSV |
| Bahasa model khusus | ✖ | ALDx memakai SQL baku agar tidak ada bahasa baru yang harus dipelajari |

## 2. Kandidat berikutnya & alasan ditunda

| Kandidat | Nilai | Risiko / keterkaitan | Rencana aman |
|---|---|---|---|
| Parameter *what-if* | rumus ukuran harus menerima nilai dari pengguna → perlu templat Jinja, yang membuat dataset **tidak bisa diekstrak** dan cache per nilai | batasi ke Studio (dihitung di browser atas hasil kueri), tidak menyentuh dataset |
| YoY / perubahan % dari periode lalu | perlu tahu butir waktu (bulan vs hari) & periode yang bolong; % dari total & kumulatif **sudah ada** | hitung di server setelah kueri, sama seperti kalkulasi cepat lain |
| Peringatan data | memakai penjadwal & email yang sama dengan Langganan laporan; salah ambang = banjir email | tumpangkan pada Langganan laporan dengan batas 1 email per hari |
| Bookmark | bentrok dengan filter global & `native_filters_key` Superset | simpan sebagai tautan bernama per dashboard |

## 3. Prinsip saat mengadopsi

1. **Tidak menambah bahasa baru**: rumus = SQL baku yang sudah dikenal Superset & Explore.
2. **Satu sumber kebenaran**: definisi disimpan di dataset (bukan di chart), sehingga angka sama di mana pun.
3. **Gagal dengan aman**: rumus diuji ke sumber sebelum disimpan; Telusuri yang tidak bisa membaca filter
   hanya menampilkan "belum ada filter aktif", tidak pernah membuat dashboard galat.
4. **Hak akses tidak berubah**: semua fitur baru berjalan di dalam kueri dataset, jadi RLS tetap berlaku.
