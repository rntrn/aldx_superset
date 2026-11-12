# 32 · Perbandingan Fitur dengan Tableau, Power BI, Looker & Sigma

Peta fitur unggulan empat produk BI dan padanannya di ALDx. Dipakai sebagai **peta jalan**: apa yang sudah ada,
apa yang baru diadopsi, dan apa yang sengaja ditunda beserta alasannya.

Status: ✅ ada · 🆕 baru diadopsi (November 2026) · ⏳ kandidat berikutnya · ✖ tidak diadopsi.

## 1. Ringkasan

| Fitur | Unggulan di | ALDx | Di mana |
|---|---|---|---|
| Seret-lepas kolom ke rak, *Show Me* | Tableau | ✅ | Studio Visual ([12](12-studio-visual.md)) |
| Hierarki & telusur bertingkat (drill down) | Tableau, Power BI | ✅ | Studio › Hierarki |
| **Ukuran & kolom terdefinisi** (*measure / calculated column*) | Power BI (DAX), Tableau, Looker (LookML) | 🆕 | Studio › **+ Ukuran / + Dimensi** |
| **Drill-through** antar halaman dengan filter terbawa | Power BI | 🆕 | tombol **Telusuri** di dashboard ([25 §2b](25-berkas-filter-global-ulasan.md)) |
| **Top N** | Tableau, Power BI | 🆕 | Studio › *N teratas* |
| Klik-filter antar-chart (cross filter), drill to detail, drill by | Power BI, Tableau | ✅ | dashboard |
| Ramalan, tren, garis acuan, anomali | Tableau, Power BI | ✅ | Studio › Analitik ([17](17-katalog-chart-peta-prediksi.md)) |
| Ekstrak ke mesin kolom (Hyper / VertiPaq) | Tableau, Power BI | ✅ | ALDx Engine ([13](13-sps-engine-ekstrak.md)) |
| Lapisan semantik: metrik didefinisikan sekali, dipakai semua | Looker | ✅/🆕 | definisi tersimpan di **dataset**: dipakai semua chart, Explore & pengguna |
| Rumus gaya spreadsheet langsung di atas data gudang | Sigma | 🆕 (sebagian) | dialog rumus: klik kolom, contoh rumus, **Uji rumus** |
| Tanya data dengan bahasa sehari-hari (Q&A, Pulse) | Power BI, Tableau | ✅ | Asisten AI ([23](23-asisten-ai-peran-ahli.md)) |
| Sematkan dengan RLS per penonton | Looker, Sigma, Power BI | ✅ | [30](30-sematkan-dashboard.md) |
| Langganan laporan, riwayat versi, tata letak ponsel | semua | ✅ | [26](26-langganan-versi-ponsel-lihat-sebagai.md) |
| Story / presentasi berurutan | Tableau | ✅ | Story |
| Parameter *what-if* (geser angka, chart ikut berubah) | Power BI, Tableau | ⏳ | lihat §2 |
| **Kalkulasi cepat** (% dari total, kumulatif, YoY) | Tableau | 🆕 | Studio › **Hitung** |
| **Template dashboard** (*Quick create*) | Power BI, Tableau | 🆕 | Susun dashboard › **Dari template…** |
| **Kelompokkan nilai** (*Group*) & skala warna tabel | Tableau, Power BI | 🆕 | Studio: klik kanan dimensi; Tabel › *Skala warna sel* |
| Peringatan data (*data alerts*) saat angka melewati ambang | Power BI, Looker | ✅ | menu **Peringatan data** ([26 §1b](26-langganan-versi-ponsel-lihat-sebagai.md)) |
| *Bookmark* (simpan keadaan filter bernama) | Power BI | 🆕 | **Tampilan tersimpan** di panel Telusuri ([25 §2c](25-berkas-filter-global-ulasan.md)) |
| Tabel input (ketik data langsung ke gudang) | Sigma | ✖ | menulis ke database sumber berisiko; pakai impor Excel/CSV |
| Bahasa model sendiri (DAX, LookML) | Power BI, Looker | ✖ | ALDx memakai SQL baku agar tidak ada bahasa baru yang harus dipelajari |

## 2. Kandidat berikutnya & alasan ditunda

| Kandidat | Nilai | Risiko / keterkaitan | Rencana aman |
|---|---|---|---|
| Parameter *what-if* | simulasi (mis. kenaikan harga 5%) | rumus ukuran harus menerima nilai dari pengguna → perlu templat Jinja, yang membuat dataset **tidak bisa diekstrak** dan cache per nilai | batasi ke Studio (dihitung di browser atas hasil kueri), tidak menyentuh dataset |
| YoY / perubahan % dari periode lalu | sangat sering dipakai | perlu tahu butir waktu (bulan vs hari) & periode yang bolong; % dari total & kumulatif **sudah ada** | hitung di server setelah kueri, sama seperti kalkulasi cepat lain |
| Peringatan data | pemantauan otomatis | memakai penjadwal & email yang sama dengan Langganan laporan; salah ambang = banjir email | tumpangkan pada Langganan laporan dengan batas 1 email per hari |
| Bookmark | berbagi tampilan tersaring | bentrok dengan filter global & `native_filters_key` Superset | simpan sebagai tautan bernama per dashboard |

## 3. Prinsip saat mengadopsi

1. **Tidak menambah bahasa baru**: rumus = SQL baku yang sudah dikenal Superset & Explore.
2. **Satu sumber kebenaran**: definisi disimpan di dataset (bukan di chart), sehingga angka sama di mana pun.
3. **Gagal dengan aman**: rumus diuji ke sumber sebelum disimpan; drill-through yang tidak bisa membaca filter
   hanya menampilkan "belum ada filter aktif", tidak pernah membuat dashboard galat.
4. **Hak akses tidak berubah**: semua fitur baru berjalan di dalam kueri dataset, jadi RLS tetap berlaku.
