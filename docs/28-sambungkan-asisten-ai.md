# 28 · Menyambungkan Asisten AI (lokal, cloud gratis, cloud berbayar)

Panduan **satu pintu** untuk menghidupkan Asisten AI: dari memasang model sampai mengisi key.
Cukup pilih **satu** jalur. Jalur bisa ditambah atau diganti kapan saja **tanpa memasang ulang dan tanpa restart**.

| Jalur | Biaya | Data | Cocok untuk |
|---|---|---|---|
| **A. Lokal** (Ollama, LM Studio, Jan, llama.cpp) | gratis | **tidak keluar** dari komputer | kantor, data sensitif, tanpa internet |
| **B. Cloud gratis** (Gemini, Groq, OpenRouter, Cerebras, Mistral, GitHub Models) | gratis, kuota harian | pertanyaan dikirim ke penyedia; **angka hasil query tidak** | mencoba cepat, komputer kecil |
| **C. Cloud berbayar** (OpenAI, Anthropic Claude, xAI Grok, DeepSeek) | per pemakaian | sama seperti B | jawaban paling pintar & cepat |

## 1. Di mana menyambungkannya

Ada empat tempat. Hasilnya sama:

1. **Di aplikasi (termudah):** tekan `Ctrl + I` atau ikon ✦ di kanan atas untuk membuka panel **Asisten AI**.
   Bila belum ada model, layar **Sambungkan Asisten AI** langsung muncul. Setelah itu, layar ini bisa dibuka
   kapan saja lewat ikon **sambung** (🔗) di kepala panel.
   - Tab **Lokal**: status Ollama / LM Studio / Jan / llama.cpp, model yang sudah terdeteksi, dan langkah memasang
     lengkap dengan tombol **Salin** perintah.
   - Tab **Cloud gratis** / **Cloud berbayar**: tombol **Buat key ↗**, kolom untuk menempel key, lalu **Simpan**.
     Sebelum disimpan, key diuji langsung ke penyedianya. Key tersimpan **terenkripsi** di database dan berlaku
     di semua node. Hanya **Admin** yang bisa mengisi; pengguna lain melihat statusnya saja.
   - Tombol **Periksa lagi**: deteksi ulang tanpa menunggu.
2. **Di Pusat Kendali › Asisten AI** (Admin; juga menu **Kelola › Asisten AI**): semua isi layar di atas dalam bentuk
   tabel, ditambah **Uji** (mengirim pertanyaan pendek dan menampilkan waktu jawab) dan **Jadikan bawaan** (model yang
   dipakai pertama kali oleh semua pengguna).
3. **Di installer:** halaman **Asisten AI** (kini selalu tampil, boleh dilewati) berisi tombol **Periksa**,
   **Unduh Ollama / LM Studio**, pilihan layanan cloud, dan **? Cara membuat key**.
4. **Di berkas `.env`** (untuk tim TI): `AI_GEMINI_API_KEY=...` dan seterusnya, lalu `docker compose up -d`.
   Key di `.env` didahulukan daripada key yang diisi lewat aplikasi.

Setiap pengisian dan penghapusan key dicatat di **Pusat Kendali › Riwayat** (kelompok *Asisten AI*).

---

## 2. Jalur A: model lokal

Model lokal **tidak** berjalan di Docker. Pasang aplikasinya di **Windows komputer server yang sama** dengan ALDx.
ALDx memeriksa alamat berikut setiap 60 detik, dan **semua model chat yang sudah diunduh langsung muncul**
di pilihan model. Nama model tidak perlu ditulis di mana pun.

| Aplikasi | Port | Diperiksa di alamat |
|---|---|---|
| Ollama | 11434 | `http://host.docker.internal:11434/v1` |
| LM Studio | 1234 | `http://host.docker.internal:1234/v1` |
| Jan | 1337 | `http://host.docker.internal:1337/v1` |
| llama.cpp (`llama-server`) | 8080 | `http://host.docker.internal:8080/v1` |

Model embedding (mis. `bge-m3`, `nomic-embed-text`) dilewati secara otomatis karena tidak bisa menjawab pertanyaan.

### 2.1 Memilih model sesuai RAM

Model harus mendukung **tool calling** (pemanggilan fungsi). Semua contoh di bawah sudah mendukungnya.

| RAM komputer | Contoh model (Ollama) | Unduhan | Catatan |
|---|---|---|---|
| 8 GB | `qwen3:4b` | ± 2,5 GB | cukup untuk tanya data sederhana |
| 16 GB | `qwen3:8b` atau `gpt-oss:20b` | 5–13 GB | **disarankan** untuk kantor |
| 32 GB+ / ada GPU NVIDIA | `qwen3:14b`, `qwen3:30b` | 9–19 GB | paling pintar untuk analisis |

Tanpa GPU, satu jawaban bisa makan waktu 10–90 detik, dan itu normal. Dengan GPU, jauh lebih cepat.
Nama model di penyedia bisa berganti; pilih versi *instruct* terbaru dari keluarga yang sama.

### 2.2 Ollama (disarankan, paling ringan)

1. Unduh: <https://ollama.com/download> › jalankan `OllamaSetup.exe` › **Install**.
   Ikon llama muncul di pojok kanan bawah, dan Ollama menyala otomatis setiap Windows menyala.
2. Buka **PowerShell**, unduh model (sekali):
   ```powershell
   ollama pull qwen3:4b
   ```
3. Di ALDx: panel Asisten AI › **Periksa lagi**. Status Ollama berubah menjadi **siap · 1 model**.
4. Bila tetap *belum menyala* padahal ikon llama ada, izinkan Docker menghubunginya (sekali): Windows › cari
   *Edit the system environment variables* › **Environment Variables…** › *User variables* › **New…**
   `OLLAMA_HOST` = `0.0.0.0` › OK › klik kanan ikon llama › **Quit** › buka lagi Ollama. Bila Firewall bertanya,
   pilih **Allow** (Private).

### 2.3 LM Studio (ada tampilan, mudah dipantau)

1. Unduh: <https://lmstudio.ai/download> › pasang › buka.
2. Tab **Discover** (kaca pembesar) › cari `qwen3` › pilih ukuran sesuai RAM › **Download**.
3. Tab **Developer** › pilih model › nyalakan **Start server** (port 1234) dan aktifkan **Serve on Local Network**.
4. Di ALDx: **Periksa lagi**. Bila statusnya *menyala, belum ada model*, muat modelnya di tab Developer.
5. Agar menyala sendiri: Settings › *Start LM Studio on login* + *Start server automatically*.

### 2.4 Jan

1. Unduh: <https://jan.ai/download> › pasang › **Hub** › unduh model (mis. Qwen3).
2. **Settings › Local API Server** › **Start** (port 1337) › di ALDx **Periksa lagi**.

### 2.5 llama.cpp (untuk tim TI)

```powershell
llama-server -m D:\model\qwen3-8b-q4_k_m.gguf --port 8080 --host 0.0.0.0 --jinja
```
`--jinja` wajib agar tool calling aktif.

### 2.6 Server model di komputer lain (vLLM, Ollama di server GPU)

Tambahkan servernya di `config\ai.yaml` bagian `temukan_lokal` (berlaku tanpa restart):
```yaml
temukan_lokal:
  - nama: Server GPU
    base_url: http://10.1.2.3:8000/v1
```

### 2.7 Jaringan kantor memblokir unduhan model

Lihat [20 · Model AI lokal §3b](20-model-ai-lokal.md#3b-bila-jaringan-kantor-memblokir-unduhan-model):
unduh berkas `.gguf` lewat browser lalu impor ke LM Studio. Setelah terunduh, model berjalan **tanpa internet**.

---

## 3. Jalur B: cloud gratis

Semua layanan ini gratis dengan kuota harian. Langkah umumnya: **daftar › buat key › tempel di ALDx › Simpan**.

| Layanan | Halaman key | Langkah singkat | Key diawali |
|---|---|---|---|
| **Google Gemini** | <https://aistudio.google.com/app/apikey> | login akun Google › *Create API key* | `AIza` |
| **Groq** (sangat cepat) | <https://console.groq.com/keys> | daftar (tanpa kartu kredit) › *Create API Key* | `gsk_` |
| **OpenRouter** | <https://openrouter.ai/settings/keys> | daftar › *Create Key* (batas kredit boleh 0); ALDx memakai model `:free` | `sk-or-` |
| **Cerebras** (sangat cepat) | <https://cloud.cerebras.ai/> | daftar › *API Keys* › *Generate* | `csk-` |
| **Mistral** | <https://console.mistral.ai/api-keys> | pilih paket *Experiment* (verifikasi nomor HP) › *Create new key* | — |
| **GitHub Models** | <https://github.com/settings/personal-access-tokens/new> | *Fine-grained token* › Permissions › *Models: Read-only* | `github_pat_` |

> **Perhatikan:** di paket gratis, pertanyaan Anda bisa dipakai penyedia untuk melatih modelnya. ALDx **tidak
> mengirim angka hasil query** ke model cloud (`kirim_data: false`). Yang dikirim hanya pertanyaan serta nama
> kolom dan tabel.

## 4. Jalur C: cloud berbayar

Isi saldo di penyedia terlebih dahulu, lalu buat key. Tarif dihitung per pemakaian; cek halaman harga
masing-masing penyedia.

| Layanan | Halaman key | Catatan | Key diawali |
|---|---|---|---|
| **OpenAI** (GPT) | <https://platform.openai.com/api-keys> | isi saldo di *Billing* | `sk-` |
| **Anthropic** (Claude) | <https://console.anthropic.com/settings/keys> | isi saldo di *Billing* | `sk-ant-` |
| **xAI** (Grok) | <https://console.x.ai/> | akun baru biasanya dapat kredit awal | `xai-` |
| **DeepSeek** | <https://platform.deepseek.com/api_keys> | tarif rendah | `sk-` |

Gemini juga punya paket berbayar dengan key yang sama: aktifkan *billing* di Google AI Studio bila kuota
gratisnya kurang.

---

## 5. Mengganti model, menambah layanan, privasi

- **Model yang dipakai pertama kali:** pilih di Pusat Kendali › Asisten AI › **Jadikan bawaan** (atau `bawaan:` di
  `config\ai.yaml`; pilihan di Pusat Kendali didahulukan). Bila model itu tidak aktif, model aktif
  pertama dipakai (urutan: lokal, lalu cloud). Pengguna bisa mengganti model di bawah kotak tanya.
- **Nama model cloud** (mis. `gemini-flash-latest`) diatur di `model:` pada `config\ai.yaml`. Bila muncul
  *model not found*, ganti namanya sesuai halaman model penyedia. Perubahan berlaku tanpa restart.
- **Layanan lain yang kompatibel OpenAI** (Together, Fireworks, Azure OpenAI, server internal): tambahkan satu
  blok `model:` dengan `base_url`, `model`, `api_key_env`, `kategori`, dan `url_key`. Layanan itu otomatis muncul
  di layar Sambungkan AI.
- **Privasi:** `kirim_data: true` hanya untuk model lokal atau layanan yang sudah disetujui resmi.

## 6. Masalah umum

| Gejala | Penyebab | Solusi |
|---|---|---|
| Tidak ada ikon ✦ sama sekali | akun tidak punya akses Asisten AI | Admin: jalankan `scripts\build-dashboards.ps1` (memberi izin ke role Admin, Superadmin, dan role pengguna) |
| Status *belum menyala* padahal aplikasinya terbuka | server lokal hanya menerima dari komputer itu sendiri | Ollama: `OLLAMA_HOST=0.0.0.0`; LM Studio: *Serve on Local Network*; izinkan di Firewall |
| *menyala, belum ada model* | belum ada model yang diunduh/dimuat | `ollama pull qwen3:4b` atau unduh/muat di LM Studio |
| *Key ditolak penyedia (401/403)* | key salah salin / sudah dicabut | buat key baru, tempel ulang tanpa spasi |
| *Penyedia tidak bisa dihubungi dari server* | tidak ada internet / proxy kantor / SSL inspection | taruh sertifikat CA kantor di `certs\`, isi `AI_CA_BUNDLE` di `.env` ([certs/README](../certs/README.md)); atau pakai jalur lokal |
| Key yang diisi lewat aplikasi tidak terbaca setelah pindah server | `SUPERSET_SECRET_KEY` berbeda | isi ulang key di layar Sambungkan AI |
| Jawaban lambat / ngawur | model terlalu kecil untuk pertanyaannya | pakai model lebih besar (§2.1) atau layanan cloud |
| *"terlalu lama menjawab"* | model lokal di CPU melewati batas waktu satu langkah | naikkan `batas_detik_lokal` (bawaan 240 dtk) di `config\ai.yaml`; cloud memakai `batas_detik_model` (120 dtk) |
| *"Server '…' sedang sibuk atau bermasalah (HTTP 503…)"* | penyedia (mis. Gemini gratis) kelebihan beban | ALDx sudah mencoba ulang 2×. Tambahkan model kedua (key gratis lain atau model lokal) agar ALDx otomatis beralih; atau coba lagi beberapa menit kemudian |
| *"Batas … pertanyaan per jam untuk akun Anda tercapai"* | pembatas pemakaian ALDx (melindungi biaya) | tunggu jam berikutnya, atau Admin menaikkan `batas_pertanyaan_per_jam` di `config\ai.yaml` |
| Kartu **Ringkasan AI**: *"butuh model yang boleh membaca angka"* | hanya model cloud `kirim_data: false` yang aktif | pasang model lokal, atau (dengan izin resmi) `kirim_data: true` pada model cloud; atau `ringkasan_dashboard: mati` |
| *"Pertanyaan & riwayat terlalu panjang untuk model …"* | konteks model terlalu kecil walau sudah diringkas otomatis | mulai percakapan baru (tombol +), atau pakai model berkonteks lebih besar |
| *"Kuota/batas permintaan … habis"* (429) | batas harian/menit paket gratis | tunggu, pakai model lain, atau paket berbayar |
| *"Nama model … tidak dikenali"* (404) | penyedia mengganti nama model | perbarui `model:` di `config\ai.yaml` sesuai halaman model penyedia |
| *"belum selesai dalam 15 menit"* | permintaan butuh banyak langkah dan model terlalu lambat | pakai model lebih kuat (cloud, atau lokal dengan GPU), pecah permintaan, atau naikkan `batas_latar_detik` di `config\ai.yaml` |
| *"Server memutus permintaan…"* | instalasi tanpa Redis (mode latar mati), batas ±5 menit | pastikan layanan `redis` berjalan (`docker compose ps`) |
