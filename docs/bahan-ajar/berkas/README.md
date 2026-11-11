# Berkas Latihan

Berkas contoh untuk latihan impor dan untuk mencoba ALDx setelah instalasi. Semua isinya **fiktif**.

| Berkas | Isi | Ukuran | Dipakai di |
|---|---|---|---|
| `contoh-target-toko.xlsx` | target penjualan PT Contoh Sejahtera (2 lembar) | 7 KB | Level 3, latihan 1 |
| `contoh-penerbangan-kecil.xlsx` | data penerbangan, 6 lembar, 1.000 tiket | 0,1 MB | coba cepat, Level 1–2 |
| `contoh-penerbangan-sedang.xlsx` | data penerbangan, 6 lembar, 150.000 tiket | 8,7 MB | Level 3, Kueri Visual, filter global |
| `contoh-penerbangan-besar.xlsx` | data penerbangan, 6 lembar, 1.000.000 tiket | 58 MB | demo kemampuan, ekstrak, uji beban |

Berkas **besar tidak disertakan** (terlalu besar untuk dibagikan). Buat sendiri dalam beberapa menit:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\data-penerbangan.ps1                          # 1 juta tiket
powershell -ExecutionPolicy Bypass -File scripts\data-penerbangan.ps1 -Tiket 3000000 -Format csv  # 3 juta, CSV
```

Hasilnya muncul di folder ini. Lebih dari 1 juta tiket dalam Excel dipecah menjadi lembar `tiket_1`, `tiket_2`, …
(satu lembar Excel maksimal 1.048.576 baris). Format CSV tidak punya batas baris.

---

## 1. Data Penerbangan

Sistem reservasi rekaan: 8 maskapai, 26 bandara Indonesia, 152 nomor penerbangan, periode **2023–2025**.

### Relasi antar tabel

```
maskapai ──1:N── penerbangan ──1:N── jadwal ──1:N── tiket ──N:1── penumpang
                   │      │
         asal ─────┘      └───── tujuan
                   (keduanya N:1 ke bandara)
```

| Gabungkan | Kolom kunci |
|---|---|
| tiket → jadwal | `tiket.id_jadwal = jadwal.id_jadwal` |
| tiket → penumpang | `tiket.id_penumpang = penumpang.id_penumpang` |
| jadwal → penerbangan | `jadwal.no_penerbangan = penerbangan.no_penerbangan` |
| penerbangan → maskapai | `penerbangan.kd_maskapai = maskapai.kd_maskapai` |
| penerbangan → bandara | `penerbangan.asal = bandara.kd_iata` (atau `tujuan`) |

### Kamus data

**maskapai** (8 baris, nama rekaan)

| Kolom | Arti |
|---|---|
| `kd_maskapai` | kode 2 huruf (kunci) |
| `nm_maskapai` | nama maskapai |
| `jenis_layanan` | Layanan penuh / Layanan menengah / Berbiaya hemat / Regional |
| `tahun_berdiri` | tahun |

**bandara** (26 baris)

| Kolom | Arti |
|---|---|
| `kd_iata` | kode bandara 3 huruf (kunci), mis. CGK |
| `nm_bandara`, `kota` | nama & kota |
| `provinsi` | kode provinsi ISO, mis. `ID-BA` (untuk peta provinsi) |
| `pulau` | Jawa, Sumatra, Kalimantan, Sulawesi, Bali & Nusa Tenggara, Maluku, Papua |
| `lintang`, `bujur` | koordinat (untuk peta titik) |

**penerbangan** (152 baris: satu nomor = satu rute satu arah)

| Kolom | Arti |
|---|---|
| `no_penerbangan` | mis. `NA101` (kunci) |
| `kd_maskapai` | maskapai yang melayani |
| `asal`, `tujuan` | kode bandara |
| `jarak_km`, `durasi_menit` | jarak lurus & lama terbang terjadwal |
| `tipe_pesawat`, `kapasitas` | jenis pesawat & jumlah kursi |
| `jam_berangkat` | jam tetap, `HH:MM` |

**jadwal** (satu baris = satu keberangkatan pada satu tanggal)

| Kolom | Arti |
|---|---|
| `id_jadwal` | mis. `J000001` (kunci) |
| `no_penerbangan`, `tanggal` | penerbangan & tanggal terbang |
| `jam_berangkat`, `jam_tiba` | `jam_tiba` sudah termasuk keterlambatan |
| `status` | Tepat waktu / Terlambat / Batal |
| `menit_terlambat` | 0 bila tidak terlambat |

**penumpang** (nama rekaan)

| Kolom | Arti |
|---|---|
| `id_penumpang` | mis. `P0000001` (kunci) |
| `nm_penumpang`, `jenis_kelamin` | nama & L/P |
| `kelompok_usia` | < 18, 18-24, 25-34, 35-44, 45-54, 55+ |
| `kota_domisili` | kota |
| `keanggotaan` | Reguler / Silver / Gold |

**tiket** (tabel fakta, paling besar)

| Kolom | Arti |
|---|---|
| `no_tiket` | mis. `TK000000001` (kunci) |
| `id_jadwal`, `id_penumpang` | penerbangan yang dibeli & pembelinya |
| `kelas` | Ekonomi / Bisnis (Bisnis hanya maskapai layanan penuh & menengah) |
| `saluran` | Aplikasi seluler / Situs web / Agen perjalanan daring / Loket bandara |
| `tgl_beli`, `hari_sebelum_terbang` | tanggal beli & jarak hari ke tanggal terbang |
| `harga` | rupiah |
| `bagasi_kg` | 0, 7, 15, 20, 30 |
| `status` | Terbang / Refund / No-show (jadwal Batal → semua tiketnya Refund) |

**Pendapatan** = jumlah `harga` tiket berstatus **Terbang** dan **No-show** (Refund dikembalikan).

### Pola yang sengaja ditanam

| Pola | Untuk latihan |
|---|---|
| Tren naik tiap tahun | grafik garis, ramalan |
| Lonjakan mudik Lebaran (±7 hari), libur Juli, akhir tahun | musiman, ramalan |
| Keterlambatan lebih sering Desember–Februari (musim hujan) | perbandingan bulan |
| **Insiden:** semua jadwal dari/ke DPS **batal 12–13 November 2024** | deteksi anomali, filter tanggal |
| Harga naik bila dibeli mendekati hari terbang | sebar (scatter) `hari_sebelum_terbang` vs `harga` |
| Sebagian penumpang sering terbang | 10 penumpang teratas, keanggotaan |

### Cara memakai

| Ingin | Jalur | Batas bawaan |
|---|---|---|
| Semua lembar sekaligus (**disarankan**) | Pusat Kendali → **Hubungkan data → Berkas** → centang 6 lembar, awalan mis. `terbang` | `auto` (ikut RAM server) |
| Satu lembar saja | **+ → Data → Upload Excel** | 25 MB, 200.000 baris |

Berkas **kecil** dan **sedang** lolos kedua jalur. Berkas **besar** hanya lewat *Hubungkan data → Berkas*;
bila ditolak karena melebihi batas, minta Superadmin menaikkan **Batas data** ([24](../../24-superadmin-dan-batas-data.md)).
Setelah impor, data tidak punya RLS (tidak berisi data per cabang).

Ide demo setelah impor:
1. **Kueri Visual**: gabungkan `tiket` + `jadwal` + `penerbangan` + `bandara` → pendapatan per pulau asal.
2. **Studio Visual**: peta titik bandara (lintang/bujur) berukuran jumlah keberangkatan.
3. Garis pendapatan per bulan + **ramalan** 6 bulan; lihat lonjakan Lebaran.
4. Persentase jadwal terlambat per maskapai dan per bulan; temukan insiden DPS.
5. **Filter global** maskapai & rentang tanggal untuk semua dashboard.
6. Berkas besar: bandingkan kecepatan kueri sebelum dan sesudah **ekstrak** ke ALDx Engine.

### Angka kunci (untuk memeriksa hasil)

Isi selalu sama setiap kali dibuat (benih acak tetap).

| Pertanyaan | Kecil | Sedang | Besar |
|---|---|---|---|
| Jumlah baris jadwal / penumpang / tiket | 300 / 600 / 1.000 | 1.100 / 40.000 / 150.000 | 7.000 / 250.000 / 1.000.000 |
| Pendapatan | Rp1,98 miliar | Rp323,94 miliar | Rp2,28 triliun |
| Pendapatan 2023 / 2024 / 2025 | Rp565,4 juta / Rp486,9 juta / Rp924,9 juta | Rp86,56 / 97,01 / 140,37 miliar | Rp616,59 / 755,60 / 903,61 miliar |
| Maskapai pendapatan terbesar | Nusa Air, Rp908,4 juta | Nusa Air, Rp151,25 miliar | Nusa Air, Rp1,10 triliun |
| Rute tiket terlaku | SUB → CGK, 59 tiket | DPS → CGK, 7.276 tiket | SUB → CGK, 49.626 tiket |
| Bandara keberangkatan tersibuk | CGK, 98 jadwal | CGK, 368 jadwal | CGK, 2.448 jadwal |
| Bulan pendapatan tertinggi | Mei 2025, Rp168,0 juta | Maret 2025 (Lebaran), Rp19,30 miliar | April 2024 (Lebaran), Rp99,41 miliar |
| Jadwal terlambat / batal | 14,3% / 5 jadwal | 18,0% / 70 jadwal | 17,5% / 165 jadwal |
| Rata-rata keterlambatan | 53 menit | 51 menit | 53 menit |
| Jadwal batal karena insiden DPS | 0 (sampel terlalu kecil) | 56 jadwal | 56 jadwal |
| Tingkat isian kursi | 1,9% (sampel) | 77,3% | 81,0% |
| Tiket Refund / No-show | 48 / 28 | 14.485 / 4.198 | 61.762 / 29.164 |

Berkas **kecil** adalah sampel acak: cocok untuk mencoba fitur, tetapi angka isian kursi & insiden tidak bermakna.
Angka untuk jumlah tiket sendiri (`-Tiket`) dicetak di layar saat berkas dibuat.

---

## 2. Untuk pengembang

| Berkas | Fungsi |
|---|---|
| `config/sps_latihan_penerbangan.py` | generator: data induk (`MASKAPAI`, `BANDARA`, `RUTE`), fungsi `buat_*()`, `tulis_excel()`, `angka_kunci()` |
| `scripts/data-penerbangan.ps1` | menjalankan generator di container `superset`, lalu menyalin hasil ke folder ini |

Jalankan langsung (butuh Python 3.10+ dengan `numpy`, `pandas`, `openpyxl`):

```
python config/sps_latihan_penerbangan.py --ukuran sedang --keluar docs/bahan-ajar/berkas/contoh-penerbangan-sedang.xlsx
python config/sps_latihan_penerbangan.py --help
```

Resep:
- **Tambah bandara**: satu baris di `BANDARA` (kode, nama, kota, provinsi ISO, pulau, lintang, bujur, bobot keramaian).
- **Tambah rute**: satu baris di `RUTE` (asal, tujuan, daftar kode maskapai). Nomor penerbangan dibuat otomatis untuk dua arah.
- **Ubah ukuran preset**: `UKURAN` (tiket, jadwal, penumpang). Jadwal × kapasitas harus lebih besar dari jumlah tiket.
- **Ubah pola**: `LEBARAN`, `INSIDEN`, `_bobot_tanggal()`.

Setiap perubahan generator mengubah angka kunci: buat ulang berkas kecil & sedang, lalu perbarui tabel di atas dan
kunci jawaban di [level-3-admin-data.md](../level-3-admin-data.md).
