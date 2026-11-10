"""Data halaman Status (proses, kinerja, pemakaian).

Sumber:
    sps_node      detak tiap container: CPU, RAM, jumlah proses (lihat jalankan.py)
    Redis         memori cache, rasio hit, panjang antrean backgrounder
    gateway       koneksi aktif (nginx stub_status)
    tabel logs    aktivitas pengguna & waktu muat chart (dicatat Superset)
    tabel query   query SQL Lab
"""

from __future__ import annotations

import logging
import statistics
import urllib.request
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select

from sps_server import lingkungan, penyimpanan, tuning

log = logging.getLogger(__name__)
AKSI_CHART = "ChartDataRestApi.data"


def _aman(fungsi, *args) -> Any:
    try:
        return fungsi(*args)
    except Exception as exc:  # noqa: BLE001 - satu sumber mati tidak boleh merusak halaman
        log.warning("ALDx monitor: %s gagal: %s", fungsi.__name__, exc)
        return {"galat": str(exc)[:200]}


def redis() -> dict:
    import redis as redis_lib

    r = lingkungan.redis()
    if not r.aktif:
        return {"aktif": False}
    klien = redis_lib.Redis.from_url(r.url(0), socket_timeout=2)
    info = klien.info()
    hit, miss = info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
    return {
        "aktif": True, "versi": info.get("redis_version"),
        "memori_mb": round(info.get("used_memory", 0) / 1048576, 1),
        "memori_maks_mb": round(info.get("maxmemory", 0) / 1048576, 1),
        "rasio_hit": round(hit / (hit + miss) * 100, 1) if hit + miss else None,
        "klien": info.get("connected_clients"),
        "kunci_dibuang": info.get("evicted_keys"),
        "antrean": {a: klien.llen(a) for a in tuning.ANTREAN},          # tugas menunggu
    }


def gateway() -> dict:
    with urllib.request.urlopen("http://gateway:8081/sps-gateway-status", timeout=2) as resp:  # noqa: S310
        baris = resp.read().decode().splitlines()
    angka = baris[2].split()
    return {"aktif": True, "koneksi_aktif": int(baris[0].split(":")[1]),
            "total_permintaan": int(angka[2]),
            "membaca": int(baris[3].split()[1]), "menulis": int(baris[3].split()[3]),
            "menunggu": int(baris[3].split()[5])}


def aktivitas() -> dict:
    from superset import db
    from superset.models.core import Log
    from superset.models.slice import Slice

    sekarang = datetime.now()
    s = db.session
    aktif_15 = s.query(func.count(func.distinct(Log.user_id))).filter(
        Log.dttm >= sekarang - timedelta(minutes=15), Log.user_id.isnot(None)).scalar()
    pengguna_24 = s.query(func.count(func.distinct(Log.user_id))).filter(
        Log.dttm >= sekarang - timedelta(hours=24), Log.user_id.isnot(None)).scalar()
    durasi = [d for (d,) in s.query(Log.duration_ms).filter(
        Log.action == AKSI_CHART, Log.dttm >= sekarang - timedelta(hours=24),
        Log.duration_ms.isnot(None)).order_by(Log.id.desc()).limit(5000)]
    lambat = (s.query(Log.slice_id, Slice.slice_name, func.max(Log.duration_ms), func.count(Log.id))
              .outerjoin(Slice, Slice.id == Log.slice_id)
              .filter(Log.action == AKSI_CHART, Log.dttm >= sekarang - timedelta(hours=24))
              .group_by(Log.slice_id, Slice.slice_name)
              .order_by(func.max(Log.duration_ms).desc()).limit(10).all())
    per_jam = s.execute(select(Log.dttm).where(and_(Log.action == AKSI_CHART,
                                                    Log.dttm >= sekarang - timedelta(hours=24)))).scalars().all()
    hitung = [0] * 24
    for t in per_jam:
        jam_lalu = int((sekarang - t).total_seconds() // 3600)
        if 0 <= jam_lalu < 24:
            hitung[23 - jam_lalu] += 1
    return {
        "pengguna_aktif_15m": aktif_15, "pengguna_24j": pengguna_24,
        "chart_24j": len(durasi),
        "chart_median_ms": int(statistics.median(durasi)) if durasi else None,
        "chart_p95_ms": int(sorted(durasi)[int(len(durasi) * 0.95) - 1]) if len(durasi) >= 20 else None,
        "chart_per_jam": hitung,
        "chart_lambat": [{"id": i, "nama": n or f"(chart {i})", "maks_ms": m, "jumlah": c}
                         for i, n, m, c in lambat if i],
    }


def sqllab() -> dict:
    from superset import db
    from superset.models.sql_lab import Query

    sejak = datetime.now() - timedelta(hours=24)
    rows = db.session.query(Query.status, func.count(Query.id)).filter(
        Query.changed_on >= sejak).group_by(Query.status).all()
    return {str(st): n for st, n in rows}


def cadangan() -> dict:
    """Status cadangan terakhir dari server/status/cadangan.json (ditulis scripts\\cadangkan.ps1)."""
    import json
    import os
    from pathlib import Path
    berkas = Path(os.environ.get("SPS_SERVER_DIR", "/app/server")) / "status" / "cadangan.json"
    if not berkas.exists():
        return {}
    isi = json.loads(berkas.read_text(encoding="utf-8-sig"))      # PowerShell menulis UTF-8 dengan BOM
    for k in ("cadangan", "uji-pulih", "salin"):
        if k in isi and isi[k].get("waktu"):
            umur = datetime.now() - datetime.strptime(isi[k]["waktu"], "%Y-%m-%d %H:%M")
            isi[k]["umur_jam"] = round(umur.total_seconds() / 3600, 1)
    return isi


def status() -> dict:
    """Seluruh data halaman Status dalam satu panggilan."""
    node = _aman(penyimpanan.daftar_node)
    return {
        "waktu": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "node": node,
        "redis": _aman(redis),
        "gateway": _aman(gateway),
        "aktivitas": _aman(aktivitas),
        "sqllab": _aman(sqllab),
        "cadangan": _aman(cadangan),
    }


def menunggu_diterapkan(atur: dict, node: list[dict]) -> list[dict]:
    """Pengaturan 'terapkan' yang nilainya berbeda dari yang dipakai container saat start."""
    from flask import current_app
    from sps_server import skema

    saat_start = current_app.config.get("SPS_SERVER_SAAT_START", {})
    for n in node:                              # nilai proses dari node yang online
        if n.get("online"):
            saat_start = {**saat_start, **n.get("nilai_saat_start", {})}
    beda = []
    for a in skema.DAFTAR:
        if a.berlaku == skema.TERAPKAN and a.kunci in saat_start and saat_start[a.kunci] != atur[a.kunci]:
            beda.append({"kunci": a.kunci, "label": a.label, "aktif": saat_start[a.kunci], "baru": atur[a.kunci]})
    return beda


def rekomendasi(node: list[dict], atur: dict) -> list[dict]:
    """Hitung ulang auto-tuning untuk tiap node online (pratinjau sebelum diterapkan)."""
    hasil = []
    for n in node:
        if not n.get("online") or n.get("layanan") not in ("web", "worker"):
            continue
        c = tuning.Perangkat(cpu=n.get("cpu") or 1, ram_mb=n.get("ram_mb") or 1024)
        p = tuning.proses_web(c, atur) if n["layanan"] == "web" else tuning.proses_worker(c, atur)
        hasil.append({"nama": n["nama"], "sekarang": n.get("proses"), "rekomendasi": p})
    return hasil
