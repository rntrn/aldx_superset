"""Versi APLIKASI ALDx (bukan riwayat versi dashboard = sps_versi.py): tampil di halaman login & Beranda, dan dibandingkan dengan versi terbaru di GitHub.

    VERSI           tanggal rilis (YYYY.MM.DD). WAJIB dinaikkan di setiap perubahan aplikasi, bersama
                    docs/31-catatan-versi.md. Rilis kedua di hari yang sama: tambah nomor urut (2026.11.13.2).
                    GitHub Actions menolak membangun installer bila kode berubah tetapi VERSI tidak (rilis.yml).
    config/versi.json  (opsional, tidak di-commit) ditulis scripts\\sinkron-laptop.ps1: commit & tanggal kode
                       yang terpasang -> Beranda menampilkan "2026.11.13 · a1b2c3d".
    terbaru()       baca VERSI di cabang main repo publik (raw.githubusercontent.com), simpan 6 jam.
                    Tanpa internet = "tidak bisa dicek"; aplikasi tetap jalan normal.

    GET /app/api/versi   (login)  {versi, commit, tanggal, terbaru: {versi, lebih_baru, url} | {pesan}}
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

VERSI = "2026.11.13.7"
REPO = "rntrn/aldx_superset"
URL_SUMBER = f"https://raw.githubusercontent.com/{REPO}/main/config/sps_versi_aplikasi.py"
URL_RILIS = f"https://github.com/{REPO}/releases/tag/terbaru"
URL_CATATAN = f"https://github.com/{REPO}/blob/main/docs/31-catatan-versi.md"
SIMPAN_DETIK = 6 * 3600
BERKAS_BUILD = Path(__file__).with_name("versi.json")
_POLA = re.compile(r'^VERSI\s*=\s*"(\d{4}\.\d{2}\.\d{2}(?:\.\d+)?)"', re.M)
_tembolok: dict = {"waktu": 0.0, "data": None}


def urutan(versi: str) -> tuple[int, ...]:
    """"2026.11.13.2" -> (2026, 11, 13, 2) agar .10 terhitung lebih baru daripada .9."""
    return tuple(int(b) for b in versi.split(".") if b.isdigit())


def info() -> dict:
    """Versi terpasang (+ commit bila dipasang dengan git / sinkron-laptop)."""
    hasil = {"versi": VERSI, "commit": None, "tanggal": None}
    try:
        b = json.loads(BERKAS_BUILD.read_text(encoding="utf-8-sig"))
        hasil.update(commit=str(b.get("commit") or "")[:12] or None, tanggal=str(b.get("tanggal") or "")[:10] or None)
    except (OSError, ValueError):
        pass
    return hasil


def teks_singkat() -> str:
    i = info()
    return f"v{i['versi']}" + (f" · {i['commit'][:7]}" if i["commit"] else "")


def terbaru(paksa: bool = False) -> dict:
    """Versi di repo publik. Tidak pernah melempar galat (tanpa internet = pesan)."""
    if not paksa and _tembolok["data"] and time.monotonic() - _tembolok["waktu"] < SIMPAN_DETIK:
        return _tembolok["data"]
    import urllib.request
    try:
        with urllib.request.urlopen(URL_SUMBER, timeout=3) as r:            # proxy kantor dari HTTPS_PROXY
            m = _POLA.search(r.read(20000).decode("utf-8", "replace"))
        data = ({"versi": m[1], "lebih_baru": urutan(m[1]) > urutan(VERSI), "url": URL_RILIS, "catatan": URL_CATATAN} if m
                else {"pesan": "Versi terbaru tidak terbaca."})
    except Exception:  # noqa: BLE001 - tanpa internet / diblokir proxy
        data = {"pesan": "Tidak bisa dicek (tanpa internet atau diblokir proxy)."}
    _tembolok.update(waktu=time.monotonic(), data=data)
    return data
