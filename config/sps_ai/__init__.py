"""Asisten AI ALDx - agent analitik di dalam Superset.

Pengguna bertanya dalam bahasa sehari-hari; agent mencari dataset, mengambil
data, menjelaskan hasilnya, dan membuatkan chart. Model AI bisa dipilih:
lokal (Ollama, dll.) atau API (OpenAI, Gemini, Claude, dll.) - lihat config/ai.yaml.

Struktur modul:
    pengaturan.py  membaca ai.yaml (+ API key dari .env)
    llm.py         klien model berformat OpenAI-compatible
    alat.py        "tangan" agent: cari dataset, ambil data, buat chart, dst.
                   SEMUA berjalan sebagai user yang login -> hak akses & RLS berlaku
    agen.py        putaran kerja agent (model <-> alat) + catatan audit
    tampilan.py    halaman /asisten/ dan API-nya
    halaman.html   tampilan chat

Dipasang ke Superset oleh superset_config.py (FLASK_APP_MUTATOR -> daftarkan).
"""

from sps_ai.tampilan import daftarkan  # noqa: F401
