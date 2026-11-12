# Bahan Ajar Pelatihan ALDx

Paket untuk **pengajar/fasilitator** yang menyelenggarakan pelatihan di kantor pusat maupun cabang/unit.
Peserta belajar dari [tutorial](../tutorial/README.md); pengajar memakai modul di folder ini.

| Modul | Peserta | Durasi | Kelas maks. |
|---|---|---|---|
| [Level 1 · Pengguna](level-1-pengguna.md) | semua pengguna | 1 × 90 menit | 30 |
| [Level 2 · Analis](level-2-analis.md) | pembuat laporan | 2 × 120 menit | 20 |
| [Level 3 · Admin data](level-3-admin-data.md) | pengelola data | 2 × 120 menit | 12 |
| [Level 4 · Admin server](level-4-admin-server.md) | tim TI | 2 × 150 menit | 8 |
| [Modul khusus · Runbook admin](modul-runbook-admin.md) | admin server & petugas jaga | 1 × 150 menit | 8 |

Setiap modul berisi: tujuan pembelajaran, persiapan, rencana sesi per menit, poin penyampaian,
demo, latihan dengan **kunci jawaban**, kuis dengan kunci, dan daftar periksa kompetensi.
Presentasi pendukung: deck **"ALDx: Sosialisasi"** (versi PDF: [`../pdf/presentasi-sosialisasi.pdf`](../pdf/presentasi-sosialisasi.pdf)).
Semua modul juga tersedia sebagai PDF siap cetak di [`../pdf/`](../pdf/).

## Persiapan umum (H-3)

| Siapa | Apa |
|---|---|
| Admin server | jalankan `scripts\data-latihan.ps1` dan `scripts\uji.ps1` (semua LULUS) |
| Admin server | buat akun/role peserta (tanpa LDAP: Settings → List Users → +): Level 1 → Gamma; Level 2 → + kemampuan *Buat & simpan chart*, *Buat & ubah dashboard*; Level 3 → + *Kelola dataset*, *SQL Lab*, *Upload*; Level 4 → server uji terpisah |
| Pengajar | coba seluruh latihan di modul dengan akun peserta |
| Pengajar | siapkan proyektor; buka dashboard latihan & Studio di tab terpisah |
| Panitia | pastikan semua komputer peserta bisa membuka alamat aplikasi (jaringan kantor/VPN) |

## Data latihan

Semua latihan memakai data **fiktif** perusahaan ritel rekaan *PT Contoh Sejahtera*
(`latihan_penjualan`, `latihan_lokasi_pelanggan`) dengan angka tetap. Peserta boleh mencoba apa saja
tanpa risiko membocorkan data perusahaan. Berkas latihan impor: [`berkas/contoh-target-toko.xlsx`](berkas/contoh-target-toko.xlsx).

Untuk latihan gabung tabel & demo data besar tersedia set **Penerbangan** (fiktif): 6 lembar saling terhubung
(maskapai, bandara, penerbangan, jadwal, penumpang, tiket) dalam tiga ukuran, 1.000 sampai 1 juta tiket lebih.
Kamus data, cara impor, dan angka kunci: [`berkas/README.md`](berkas/README.md).

Untuk latihan **hierarki, ramalan, dan data besar** tersedia `latihan_penjualan_harian` (fiktif, dimuat otomatis
oleh installer): penjualan harian 2021–2025 di 138 outlet, 17 provinsi, 30 kab/kota, 68 kecamatan, 10 subkategori,
**2.337.380 baris**, dengan hierarki bawaan *Wilayah*, *Kalender*, *Produk* dan dashboard
*Latihan: Wilayah & Prediksi*. Lebih besar untuk demo kecepatan: `scripts\data-latihan.ps1 -Skala 4` (± 9,3 juta baris).

| Pertanyaan (data harian) | Jawaban |
|---|---|
| Total penjualan 2021–2025 | **Rp20,31 triliun** (`20.3T`); margin **24,5%**; capaian target **100,4%** |
| Per tahun 2021 / 2022 / 2023 / 2024 / 2025 | 2,52 / 3,57 / 4,19 / 4,83 / 5,20 triliun |
| Pulau / provinsi / kab-kota terbesar | Jawa 12,77 T · DKI Jakarta 4,49 T · Jakarta Selatan 1,99 T |
| Kategori / subkategori terbesar | Elektronik 5,45 T · Ponsel 3,73 T |
| Hari rata-rata tertinggi / terendah | **Sabtu** · **Senin** |
| Bulan tertinggi | **Maret 2025**, Rp579,6 miliar (menjelang Lebaran 31 Mar 2025) |
| Hari tertinggi | **29 Maret 2025**, Rp33,0 miliar |
| Anomali yang ditanam | banjir Jakarta Timur 27 Jan–2 Feb 2025 (turun ± 85%); gangguan sistem Sulawesi Selatan 5 Okt 2023 (Rp0,05 miliar); promo 17 Agustus 2024 Gerai Mekarmulya (OT0105) Rp568 juta |
| Outlet buka sejak 1 Jan 2021 | 115 dari 138 (23 menyusul 2022–2024) |

Angka kunci yang sering dipakai:

| Pertanyaan | Jawaban |
|---|---|
| Total penjualan seluruh data | **Rp667,4 miliar** (`667B` di dashboard) |
| Total per tahun 2023 / 2024 / 2025 | 194,2 / 220,6 / 252,6 miliar |
| Cabang terbesar | Cabang Jakarta, 234,2 miliar |
| Kategori terbesar | Elektronik, 208,8 miliar |
| Saluran terbesar | Online, 227,5 miliar |
| Bulan tertinggi | Maret 2025, 25,9 miliar (ada lonjakan Elektronik Cabang Jakarta) |
| Total jumlah transaksi (dijumlah) | 769.358 |
| Provinsi belanja terbesar (lokasi pelanggan) | ID-JK (DKI Jakarta), 8,8 miliar; 514 pelanggan |

## Evaluasi

- **Kuis** di akhir sesi: lulus bila ≥ 70%.
- **Daftar periksa kompetensi**: pengajar mencentang saat peserta mendemonstrasikan.
- Sertifikat/catatan pelatihan mengikuti ketentuan unit penyelenggara.
- Kumpulkan masukan peserta: apa yang membingungkan → perbaiki tutorial.
