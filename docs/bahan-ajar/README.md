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
