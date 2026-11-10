# Modul Khusus · Runbook Admin: Menyalakan, Memeriksa, Memulihkan

| Identitas | |
|---|---|
| Peserta | admin server & petugas jaga (on-call), termasuk cadangan admin |
| Durasi | 1 sesi × 150 menit (praktik ±70%) |
| Prasyarat | Level 4 (atau terbiasa PowerShell & Docker Desktop) |
| Bahan peserta | [19-runbook-faq-admin.md](../19-runbook-faq-admin.md) (cetak §7 *Kartu perintah ringkas*), [04-troubleshooting.md](../04-troubleshooting.md) |
| Lingkungan | **server/VM uji** per 2 peserta, ALDx terpasang, data latihan dimuat, `uji.ps1` LULUS |
| Hasil | peserta bisa menyalakan & mematikan dengan benar, menemukan penyebab gangguan dengan urutan lapis, dan memulihkan dari cadangan |

> **Jangan pernah berlatih di server produksi.** Semua simulasi gangguan di modul ini sengaja merusak.

## Tujuan pembelajaran

1. Menyebutkan 7 container, lapisnya, dan **urutan menyala**;
2. menjalankan SOP menyalakan, mematikan, dan restart satu komponen;
3. melakukan **cek kesehatan harian** dalam 5 menit;
4. menemukan penyebab gangguan dengan **pohon keputusan** (lapis bawah dulu);
5. mencadangkan dan **memulihkan** metadata;
6. menjawab pertanyaan pengguna yang paling sering (FAQ).

## Persiapan pengajar (H-1)

| Apa | Cara |
|---|---|
| VM uji siap | `scripts\uji.ps1` → semua LULUS di setiap VM |
| Cadangan awal | `scripts\cadangkan.ps1` di setiap VM (untuk pemulihan setelah simulasi) |
| Kartu perintah | cetak [19 §7](../19-runbook-faq-admin.md#7-kartu-perintah-ringkas), satu per peserta |
| Amplop skenario | tulis skenario simulasi 1–5 (di bawah) di kartu terpisah, peserta tidak melihat isinya |

## Rencana sesi

| Menit | Kegiatan | Metode | Rujukan |
|---|---|---|---|
| 0–15 | Peta lapis: Docker → metadb/engine/redis → web → worker/beat → gateway | paparan + gambar di papan | [19 §1](../19-runbook-faq-admin.md#1-susunan-komponen--urutan-menyala) |
| 15–35 | SOP menyalakan & mematikan; `docker compose ps` membaca kolom kesehatan | demo → peserta ikut | [19 §2.1–2.2](../19-runbook-faq-admin.md#21-menyalakan-pagi--setelah-server-restart) |
| 35–45 | Restart satu komponen; aturan "restart lapis atas juga" | demo | [19 §2.3](../19-runbook-faq-admin.md#23-restart-satu-komponen) |
| 45–55 | Cek kesehatan 5 menit | peserta praktik | [19 §3](../19-runbook-faq-admin.md#3-cek-kesehatan-5-menit-harian) |
| 55–115 | **Simulasi gangguan 1–5** (12 menit per skenario: 8 menit cari & perbaiki, 4 menit bahas) | berpasangan | [19 §4](../19-runbook-faq-admin.md#4-mencari-penyebab-gangguan-pohon-keputusan) |
| 115–130 | Cadangan & pemulihan (latihan 6) | peserta praktik | [19 §2.5](../19-runbook-faq-admin.md#25-cadangan--pemulihan) |
| 130–140 | FAQ: tanya-jawab bergiliran dari kartu FAQ | diskusi | [19 §6](../19-runbook-faq-admin.md#6-faq-admin) |
| 140–150 | Kuis & daftar periksa | individu | – |

## Poin penyampaian

- **Satu perintah untuk menyalakan**: `scripts\start.ps1`. Urutan antar-container dijaga Docker
  (`depends_on: healthy`). Urutan lapis dipakai saat **mencari penyebab**, bukan saat menyalakan.
- **Periksa dari bawah ke atas.** Web error sering disebabkan metadb/engine/RAM, bukan web itu sendiri.
- **Restart lapis bawah → restart lapis atas** (koneksi lama terputus).
- **`.env` berubah → `start.ps1`** (bukan `restart`), karena isinya dibaca saat container dibuat.
- **Cadangkan sebelum memperbaiki** apa pun yang menyentuh data.
- **Data tidak ikut hilang** saat `stop.ps1`; hanya `docker volume rm` yang menghapus.
- Catat setiap gangguan: gejala, penyebab, tindakan, durasi. Riwayat ini bahan perbaikan.

## Demo pengajar: menyalakan dari nol

1. Tutup Docker Desktop (*Quit*). Buka web → tidak bisa.
2. "Lapis 0 dulu": buka Docker Desktop, tunggu **Engine running**.
3. `docker compose ps` → container menyala sendiri (`restart: unless-stopped`); tunjukkan kolom `healthy`/`starting`.
4. Tunggu `superset` sehat (±1–2 menit), jalankan `scripts\uji.ps1`.
5. Tunjukkan `scripts\stop.ps1` lalu `scripts\start.ps1`: setelah `stop.ps1`, container **tidak** menyala sendiri saat Docker dibuka ulang.

## Simulasi gangguan (berpasangan)

Pengajar menjalankan perintah perusak di VM peserta tanpa memberi tahu skenarionya. Peserta hanya
menerima **gejala**, lalu mencari penyebab dengan pohon keputusan dan memperbaikinya.

| No | Perintah perusak (pengajar) | Gejala yang diberikan ke peserta |
|---|---|---|
| 1 | `docker compose stop engine` | "Dashboard latihan error, chart tidak muncul" |
| 2 | `docker compose stop redis` | "Web lambat lalu error 500" |
| 3 | `docker compose stop superset-beat` | "Ekstrak terjadwal tadi malam tidak jalan" |
| 4 | ubah `METADB_PASSWORD` di `.env` lalu `scripts\start.ps1` (simpan nilai asli!) | "Web tidak bisa dibuka sama sekali" |
| 5 | `docker compose stop gateway` | "Dari komputer lain tidak bisa membuka aplikasi" |

### Kunci simulasi

| No | Langkah menemukan | Penyebab | Perbaikan |
|---|---|---|---|
| 1 | `docker compose ps` → `sps_engine` tidak ada/`exited`; `uji.ps1` GAGAL di Engine & chart | engine mati | `docker compose start engine` → tunggu `healthy` → `docker compose restart superset-worker` → `uji.ps1` |
| 2 | `ps` → `sps_redis` mati; log superset berisi `Error ... connecting to redis` | cache & antrean mati | `docker compose start redis` → `docker compose restart superset superset-worker superset-beat` |
| 3 | Data → Ekstrak ke ALDx Engine: jadwal terlewat; `ps` → `sps_superset_beat` mati | penjadwal mati | `docker compose start superset-beat`; segarkan ekstrak manual sekali |
| 4 | `ps` → `superset` `restarting`; `docker compose logs --tail 50 superset` → `password authentication failed for user "superset"` | password metadb di `.env` tidak cocok dengan volume | kembalikan nilai asli di `.env` → `scripts\start.ps1`. **Jangan** menghapus volume |
| 5 | dari server: `http://localhost:8089` bisa, `:8088` tidak; `ps` → `sps_gateway` mati | gateway mati | `docker compose start gateway` (atau `scripts\start.ps1`) |

## Latihan

6. **Cadangan & pemulihan**: `scripts\cadangkan.ps1` → buat dashboard baru *Uji Pulih* → pulihkan
   cadangan tadi (`-Pulihkan backup\metadb-....dump`) → apakah *Uji Pulih* masih ada? Mengapa?
7. Tulis urutan **lengkap** menyalakan server setelah listrik padam (dari menekan tombol power sampai uji LULUS).
8. Pengguna melapor "angka saya kosong semua" sementara rekannya normal. Sebutkan 3 hal yang diperiksa.

### Kunci jawaban

| No | Jawaban |
|---|---|
| 6 | **Tidak ada**: pemulihan mengembalikan metadata persis seperti saat dicadangkan; yang dibuat sesudahnya hilang. Karena itu cadangkan **sebelum** perubahan |
| 7 | Nyalakan server → login Windows → buka Docker Desktop, tunggu *Engine running* → (VPN bila perlu) → `docker compose ps` (tunggu `healthy`) → bila ada yang mati: `scripts\start.ps1` → `scripts\uji.ps1` LULUS → buka web & cek satu dashboard |
| 8 | (1) role pengguna di Settings → List Users (masuk role yang benar?), (2) aturan RLS untuk role itu (Settings → Row Level Security), (3) bila profil otomatis/LDAP: log `ALDx akses <user>` & `akses.yaml`. Bukan masalah server bila rekan normal |

## Kuis

1. Urutan memeriksa gangguan yang benar… a) gateway → web → database **b) Docker → metadb/engine/redis → web → worker/beat → gateway** c) acak
2. Setelah `docker compose restart metadb`, sebaiknya juga… a) tidak perlu apa-apa **b) restart superset, worker, beat** c) hapus volume
3. Setelah mengubah `.env`, jalankan… a) `docker compose restart` **b) `scripts\start.ps1`** c) `PASANG.cmd` selalu
4. `scripts\stop.ps1` akan… a) menghapus data **b) mematikan container, data tetap** c) mengosongkan cadangan
5. Ekstrak terjadwal tidak jalan, container yang dicurigai pertama… a) gateway **b) superset-beat** c) metadb
6. Web bisa dari `localhost:8089` tetapi tidak dari `:8088`. Yang mati… **a) gateway** b) metadb c) engine
7. Berkas yang **wajib** disimpan di luar server… a) `docker-compose.yml` **b) folder `backup\` dan `.env`** c) folder `docs\`

**Kunci:** 1b · 2b · 3b · 4b · 5b · 6a · 7b

## Daftar periksa kompetensi

- [ ] Menyebutkan 7 container dan lapisnya tanpa melihat catatan
- [ ] Menyalakan dari Docker mati sampai `uji.ps1` LULUS
- [ ] Menyelesaikan minimal 4 dari 5 simulasi dalam waktu
- [ ] Mencadangkan dan memulihkan metadata
- [ ] Menjelaskan kapan `start.ps1` vs `restart`
- [ ] Menjawab 3 pertanyaan FAQ dengan benar
