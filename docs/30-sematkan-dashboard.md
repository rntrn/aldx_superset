# 30 · Sematkan Dashboard ke Web / Aplikasi Lain

Dashboard ALDx bisa ditampilkan di dalam halaman web atau aplikasi lain (portal intranet, aplikasi internal,
situs mitra) memakai `<iframe>`. Penonton **tidak perlu akun ALDx**; datanya tetap dibatasi:

| Lapisan | Siapa yang menentukan | Contoh |
|---|---|---|
| **RLS token** (baris yang boleh dilihat) | server aplikasi induk, saat meminta token | `kd_cabang = 'C01'` |
| **Filter URL** (mempersempit tampilan) | alamat `<iframe>` | `f.kategori=Elektronik` |
| **Domain** (situs yang boleh membingkai) | Admin ALDx (`.env`) | `https://portal.kantor.local` |

## 1. Menyiapkan (Admin ALDx)

1. Isi `.env`, lalu `scripts\start.ps1`:

   ```
   SPS_SEMATKAN_DOMAIN=https://portal.kantor.local          # asal halaman induk, pisah koma
   SPS_SEMATKAN_KUNCI=<rahasia acak min. 32 karakter>      # hanya untuk SERVER aplikasi induk
   SPS_SEMATKAN_MENIT=15                                    # umur token (bawaan 15 menit)
   ```

2. Menu **Dashboard & Story → Sematkan ke web lain** (Admin) → **Nyalakan** pada dashboard yang boleh disematkan.
   Tombol **Cara pakai** menampilkan contoh kode yang sudah berisi alamat dan id dashboard tersebut.
3. **Matikan** kapan saja: semua halaman yang menyematkan dashboard itu langsung berhenti menampilkannya.

## 2. Menyematkan (pengembang aplikasi induk)

**Langkah 1: server meminta token** (jangan dari browser; kunci harus tetap rahasia):

```bash
curl -X POST https://aldx.kantor.local/sematkan/api/token \
  -H "X-ALDx-Kunci: <SPS_SEMATKAN_KUNCI>" -H "Content-Type: application/json" \
  -d '{"dashboard": "<uuid>", "pengguna": "budi", "rls": ["kd_cabang = '\''C01'\''"]}'
```

Jawaban: `{"token": "eyJ...", "berlaku_detik": 900, "alamat": "/sematkan/d/<uuid>"}`

| Isian | Arti |
|---|---|
| `dashboard` | uuid sematan (dari halaman Sematkan), id, atau slug dashboard |
| `pengguna` | nama penonton (untuk log); bukan akun ALDx |
| `rls` | daftar syarat SQL baris yang boleh dilihat penonton ini. Bentuk `{"clause": "...", "dataset": 12}` membatasi satu dataset saja. Tanpa `rls` = semua baris dashboard |

**Langkah 2: halaman menampilkan dashboard**:

```html
<iframe src="https://aldx.kantor.local/sematkan/d/<uuid>?token=<token>&f.cabang=Bandung"
        style="width:100%;height:720px;border:0"></iframe>
```

Token habis? Kirim token baru tanpa memuat ulang halaman:
`iframe.contentWindow.postMessage({aldxToken: "<token baru>"}, "https://aldx.kantor.local")`.

### Filter dari alamat

| Bentuk | Jenis filter dashboard | Contoh |
|---|---|---|
| `f.<kolom>=a,b` | pilihan | `f.cabang=Bandung,Jakarta` |
| `f.<kolom>.min=` / `.max=` | rentang angka | `f.tahun.min=2024&f.tahun.max=2025` |
| `f.waktu=` | rentang waktu | `f.waktu=Last month` atau `f.waktu=2025-01-01 : 2025-12-31` |
| `judul=1` | tampilkan judul dashboard | |

Filter berlaku bila dashboard punya filter di kolom bernama sama (pencocok yang sama dengan
[filter global](25-berkas-filter-global-ulasan.md)), dan hanya mempersempit data; tidak bisa melebihi RLS token.

## 3. Keamanan

- Tanpa token sah tidak ada data. Token ditandatangani server ALDx (turunan `SUPERSET_SECRET_KEY`), hanya berlaku
  untuk dashboard yang disebut, membawa aturan RLS-nya, dan kedaluwarsa sendiri.
- Kunci server dibandingkan dengan cara aman-waktu; aturan RLS berisi `;` atau komentar SQL ditolak.
- Hanya asal di `SPS_SEMATKAN_DOMAIN` yang boleh membingkai, dan hanya untuk halaman `/sematkan/d/` & `/embedded/`
  (header `Content-Security-Policy: frame-ancestors`). Halaman ALDx lain tetap menolak dibingkai situs lain.
- Penonton memakai role **Penonton Sematan** (izin baca minimum, salinan izin baca Gamma), dibuat `build-dashboards`.
- Setiap token tercatat di log: `ALDx sematkan: token untuk dashboard <id>, pengguna <nama>, <n> aturan rls`.

## 4. Masalah umum

| Gejala | Penyebab | Tindakan |
|---|---|---|
| Halaman putih / "refused to connect" | asal halaman induk tidak ada di `SPS_SEMATKAN_DOMAIN` | tambahkan asalnya persis (`https://host:port`), lalu `scripts\start.ps1` |
| "Dashboard tidak tersedia untuk disematkan" | sematan dashboard dimatikan | nyalakan di halaman Sematkan |
| `401 Kunci salah` | header `X-ALDx-Kunci` tidak sama dengan `.env` | periksa kunci di server induk |
| `503 Sematan belum diaktifkan` | `SPS_SEMATKAN_KUNCI` kosong | isi lalu `scripts\start.ps1` |
| Data kosong | RLS token tidak cocok dengan isi data | periksa nama kolom & nilai di `rls` |

## 5. Untuk pengembang

| Berkas | Isi |
|---|---|
| `config/sps_sematkan.py` | halaman bingkai, token tamu, izin bingkai per jalur (`IzinBingkai`), role penonton |
| `config/sps_sematkan.html` | halaman admin Sematkan |
| `config/superset_config.py` | `EMBEDDED_SUPERSET`, `GUEST_TOKEN_JWT_SECRET`, `GUEST_ROLE_NAME` |

Halaman bingkai memakai mekanisme sematan resmi Superset (`/embedded/<uuid>`, guest token) dan menambahkan
filter dari alamat lewat `native_filters`.
