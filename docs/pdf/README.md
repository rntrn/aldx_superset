# docs/pdf — versi PDF siap cetak / kirim

| Berkas | Isi |
|---|---|
| `manual-lengkap.pdf` | README + CARA-PASANG + dokumen teknis 00–29 dalam satu berkas (sampul, daftar isi, bookmark) |
| `dokumen/NN-*.pdf` | setiap dokumen teknis terpisah |
| `dokumen/28-sambungkan-asisten-ai.pdf` | **menyambungkan Asisten AI**: lokal, cloud gratis, cloud berbayar (satu pintu) |
| `dokumen/20-model-ai-lokal.pdf` | **panduan memasang model AI lokal** (Ollama / LM Studio); dibuka dari installer halaman *Asisten AI* |
| `tutorial-semua-level.pdf` | tutorial bergambar level 1–4 |
| `bahan-ajar-lengkap.pdf` | bahan ajar level 1–4 + modul runbook admin |
| `per-level/*.pdf` | tutorial & bahan ajar per level (untuk dibagikan ke peserta/pengajar) |
| `pengujian-uat.pdf` | panduan pengujian + 146 skenario UAT (isian tetap di `../pengujian/lembar-uji.xlsx`) |
| `kartu-runbook-admin.pdf` | runbook & FAQ admin (cetak §7 sebagai kartu perintah) |
| `presentasi-sosialisasi.pdf` | presentasi sosialisasi 21 slide (16:9) |

Sumber tetap berkas Markdown di `docs\`. Setelah dokumen diubah, buat ulang PDF dengan
[`buat_pdf.py`](buat_pdf.py) (pengembang; butuh Python 3.10+):

```
pip install markdown pypdf playwright
playwright install chromium
python docs/pdf/buat_pdf.py                    # semua PDF (±1 menit)
python docs/pdf/buat_pdf.py --hanya dokumen    # satu kelompok: dokumen | manual | tutorial | bahan-ajar | uji | runbook
```

Daftar PDF yang dibuat ada di fungsi `daftar_berkas()`; gaya (huruf, warna, tabel) di `GAYA`.
Blok kode yang lebar otomatis diperkecil agar diagram tidak terpotong. `presentasi-sosialisasi.pdf`
dibuat dari sumber slide terpisah dan tidak diubah oleh skrip ini.
