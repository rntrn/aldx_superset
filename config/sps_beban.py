"""Uji beban ALDx: N pengguna maya membuka dashboard bersamaan (scripts\\uji-beban.ps1).

Satu login, lalu setiap pengguna maya: buka dashboard, minta data SEMUA chart-nya (seperti browser), ulangi selama
--detik. Dicatat waktu tiap permintaan data chart. Hasil: jumlah permintaan, gagal, median & p95 waktu muat,
throughput, dan kesimpulan apakah server cukup untuk jumlah pengguna itu (target: p95 < 5 detik, gagal < 1%).

Dijalankan DI DALAM container superset (memakai paket requests yang sudah ada):
    docker compose exec -T -e SPS_BEBAN_PASSWORD superset python /app/pythonpath/sps_beban.py \\
        --akun admin@perusahaan.co.id --pengguna 50 --detik 120 --dashboard latihan

Catatan:
    - Semua pengguna maya memakai satu akun (hak akses akun itu berlaku). Pilih akun dengan data realistis.
    - --tanpa-cache: minta data segar (force) agar mengukur database, bukan cache. Bawaan: seperti pengguna biasa.
    - Jalankan di luar jam kerja: uji ini sengaja membebani server.
    - Password dibaca dari variabel lingkungan SPS_BEBAN_PASSWORD (tidak dicetak, tidak disimpan).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

TARGET_P95_DETIK = 5.0
TARGET_GAGAL_PERSEN = 1.0
JEDA_DETIK = (2.0, 6.0)        # pengguna membaca dashboard sebentar sebelum membuka lagi


def masuk(alamat: str, akun: str, password: str) -> requests.Session:
    s = requests.Session()
    s.verify = False                                       # sertifikat HTTPS buatan sendiri
    halaman = s.get(f"{alamat}/login/", timeout=30).text
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', halaman) or \
        re.search(r'value="([^"]+)"[^>]*name="csrf_token"', halaman)
    s.post(f"{alamat}/login/", data={"username": akun, "password": password,
                                     "csrf_token": tok.group(1) if tok else ""}, timeout=30)
    if s.get(f"{alamat}/api/v1/me/", timeout=30).status_code != 200:
        raise SystemExit("Login gagal: periksa akun & password (atau akun sedang terkunci).")
    s.headers.update({"X-CSRFToken": s.get(f"{alamat}/api/v1/security/csrf_token/", timeout=30).json()["result"],
                      "Referer": alamat})
    return s


def permintaan_chart(s: requests.Session, alamat: str, dashboard: str) -> list[dict]:
    """Isi permintaan data tiap chart di dashboard (query_context tersimpan chart)."""
    r = s.get(f"{alamat}/api/v1/dashboard/{dashboard}/charts", timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Dashboard '{dashboard}' tidak ditemukan / tidak boleh dibuka ({r.status_code}).")
    hasil = []
    for c in r.json()["result"]:
        detail = s.get(f"{alamat}/api/v1/chart/{c['id']}", timeout=60).json().get("result", {})
        qc = detail.get("query_context")
        if qc:
            hasil.append({"nama": c.get("slice_name"), "qc": json.loads(qc)})
    if not hasil:
        raise SystemExit("Dashboard tidak punya chart dengan query_context (buka & simpan chart sekali).")
    return hasil


def pengguna_maya(nomor: int, induk: requests.Session, alamat: str, dashboard: str, daftar: list[dict],
                  sampai: float, segar: bool, catatan: list, kunci: threading.Lock) -> None:
    # Satu sesi login dipakai bersama (salinan per utas): login berulang akan kena batas login.
    # Tiap pengguna maya tampil dengan alamat IP sendiri (X-Forwarded-For, dibaca ProxyFix) seperti pengguna
    # sungguhan, agar batas permintaan per IP tidak memotong seluruh uji.
    s = requests.Session()
    s.verify = False
    s.cookies.update(induk.cookies)
    s.headers.update(induk.headers)
    s.headers["X-Forwarded-For"] = f"10.250.{nomor // 250}.{nomor % 250 + 1}"
    while time.time() < sampai:
        s.get(f"{alamat}/api/v1/dashboard/{dashboard}", timeout=60)
        for c in daftar:
            qc = dict(c["qc"], force=segar, result_format="json", result_type="full")
            mulai = time.time()
            try:
                kode = s.post(f"{alamat}/api/v1/chart/data", json=qc, timeout=120).status_code
            except requests.RequestException:
                kode = 0
            ok = kode == 200
            with kunci:
                catatan.append((time.time() - mulai, ok))
            if time.time() >= sampai:
                break
        time.sleep(random.uniform(*JEDA_DETIK))       # waktu baca pengguna sebelum membuka dashboard lagi


def main() -> int:
    a = argparse.ArgumentParser(description="Uji beban ALDx")
    a.add_argument("--alamat", default=os.environ.get("SPS_BEBAN_ALAMAT", "http://localhost:8088"))
    a.add_argument("--akun", required=True)
    a.add_argument("--pengguna", type=int, default=20)
    a.add_argument("--detik", type=int, default=120)
    a.add_argument("--dashboard", default="latihan", help="id atau slug dashboard")
    a.add_argument("--tanpa-cache", action="store_true")
    o = a.parse_args()
    password = os.environ.get("SPS_BEBAN_PASSWORD") or ""
    if not password:
        raise SystemExit("Isi SPS_BEBAN_PASSWORD.")
    requests.packages.urllib3.disable_warnings()

    catatan: list = []
    kunci = threading.Lock()
    print(f"Uji beban: {o.pengguna} pengguna maya, {o.detik} detik, dashboard '{o.dashboard}'"
          f"{', tanpa cache' if o.tanpa_cache else ''} ...", flush=True)
    induk = masuk(o.alamat, o.akun, password)
    daftar = permintaan_chart(induk, o.alamat, o.dashboard)
    sampai = time.time() + o.detik
    with ThreadPoolExecutor(max_workers=o.pengguna) as kolam:
        tugas = [kolam.submit(pengguna_maya, i, induk, o.alamat, o.dashboard, daftar, sampai, o.tanpa_cache,
                              catatan, kunci) for i in range(o.pengguna)]
        for t in tugas:
            t.result()

    waktu = sorted(w for w, ok in catatan if ok)
    gagal = sum(1 for _, ok in catatan if not ok)
    total = len(catatan)
    if not waktu:
        print("Semua permintaan GAGAL. Cek: scripts\\logs.ps1")
        return 1
    p95 = waktu[min(len(waktu) - 1, int(len(waktu) * 0.95))]
    persen_gagal = gagal / total * 100
    print(f"\nPermintaan data chart : {total:,}".replace(",", "."))
    print(f"Gagal                 : {gagal} ({persen_gagal:.1f}%)")
    print(f"Waktu muat median     : {statistics.median(waktu):.2f} detik")
    print(f"Waktu muat p95        : {p95:.2f} detik")
    print(f"Throughput            : {total / o.detik:.1f} chart/detik")
    lulus = p95 < TARGET_P95_DETIK and persen_gagal < TARGET_GAGAL_PERSEN
    print("\nKESIMPULAN: " + ("CUKUP" if lulus else "KURANG") +
          f" untuk {o.pengguna} pengguna bersamaan (target p95 < {TARGET_P95_DETIK:g} detik, gagal < "
          f"{TARGET_GAGAL_PERSEN:g}%)." +
          ("" if lulus else " Lihat docs\\15-sizing.md: tambah proses web/RAM, aktifkan ekstrak & cache, atau node."))
    return 0 if lulus else 2


if __name__ == "__main__":
    sys.exit(main())
