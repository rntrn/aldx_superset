"""Auto-tuning: hitung jatah sumber daya & jumlah proses dari perangkat keras node.

Dua tingkat, proses dibagi di tiap node:

1. alokasi_container()  - dijalankan skrip terapkan di TIAP node.
   Dari total CPU/RAM Docker node -> batas CPU/RAM untuk container web,
   backgrounder & Redis.
2. proses_web() / proses_worker() - dijalankan peluncur saat container start.
   Dari batas CPU/RAM container itu sendiri -> jumlah proses & thread.

Karena tahap 2 terjadi saat start, node baru yang bergabung langsung
"menyetel diri" sesuai kemampuannya (auto-tuning saat dihubungkan).
Nilai yang diisi angka oleh admin (bukan "auto") selalu dihormati.

Rumus (perkiraan konservatif untuk Superset 6, Python 3.10):
    node utama: Redis 10%, ALDx Engine 25%, katalog 6% dari RAM tersedia; sisanya web 60% / worker 40%
    proses web        = min(2 × CPU + 1, RAM_web / 700 MB), 1..16
    thread per proses = 8 bila RAM per proses ≥ 1,2 GB, selain itu 4
    proses backgrounder total = min(2 × CPU, RAM_worker / 450 MB), 1..24
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sps_server.skema import AUTO

MB_PER_PROSES_WEB = 700
MB_PER_PROSES_WORKER = 450
MB_BEAT = 256
CGROUP = Path("/sys/fs/cgroup")


@dataclass(frozen=True)
class Perangkat:
    cpu: float        # inti CPU yang boleh dipakai
    ram_mb: int       # RAM yang boleh dipakai


def _baca(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def perangkat_host() -> Perangkat:
    """Total CPU & RAM yang dimiliki Docker di node ini (VM Docker Desktop / server Linux)."""
    ram_kb = next((int(baris.split()[1]) for baris in _baca(Path("/proc/meminfo")).splitlines()
                   if baris.startswith("MemTotal:")), 4 * 1024 * 1024)
    return Perangkat(cpu=float(os.cpu_count() or 1), ram_mb=ram_kb // 1024)


def perangkat_container() -> Perangkat:
    """Batas CPU & RAM container ini (cgroup v2). Tanpa batas -> sama dengan host."""
    host = perangkat_host()
    cpu = host.cpu
    kuota = _baca(CGROUP / "cpu.max").split()
    if len(kuota) == 2 and kuota[0] != "max":
        cpu = min(cpu, int(kuota[0]) / int(kuota[1]))
    ram = host.ram_mb
    batas = _baca(CGROUP / "memory.max")
    if batas.isdigit():
        ram = min(ram, int(batas) // (1024 * 1024))
    return Perangkat(cpu=max(cpu, 0.5), ram_mb=ram)


def pemakaian_container(sebelumnya: dict | None = None) -> dict[str, Any]:
    """Pemakaian CPU (%) & RAM (MB) container ini sejak pembacaan sebelumnya."""
    usec = next((int(b.split()[1]) for b in _baca(CGROUP / "cpu.stat").splitlines()
                 if b.startswith("usage_usec")), None)
    sekarang = {"usec": usec, "waktu": time.monotonic()}
    cpu_persen = None
    if usec is not None and sebelumnya and sebelumnya.get("usec") is not None:
        rentang = max(sekarang["waktu"] - sebelumnya["waktu"], 0.001)
        cpu_persen = round((usec - sebelumnya["usec"]) / 1e6 / rentang / perangkat_container().cpu * 100, 1)
    ram = _baca(CGROUP / "memory.current")
    return {"cpu_persen": cpu_persen, "ram_terpakai_mb": int(ram) // (1024 * 1024) if ram.isdigit() else None,
            "_mentah": sekarang}


def _batas(n: float, bawah: int, atas: int) -> int:
    return int(max(bawah, min(atas, n)))


def _pilih(nilai: Any, otomatis: int) -> int:
    return otomatis if nilai == AUTO else int(nilai)


# --- Tahap 1: jatah container per node --------------------------------------------------
def alokasi_container(host: Perangkat, peran: str, atur: dict[str, Any]) -> dict[str, Any]:
    """Batas CPU/RAM tiap container. Kembalikan nilai + catatan peringatan."""
    catatan = []
    tersedia = host.ram_mb * (100 - atur["sumber.cadangan_persen"]) // 100
    redis = engine = metadb = 0
    if peran == "utama":
        redis = _pilih(atur["sumber.redis_ram_mb"], _batas(tersedia * 0.10, 256, 2048))
        engine = _pilih(atur["sumber.engine_ram_mb"], _batas(tersedia * 0.25, 1024, 16384))
        metadb = _pilih(atur["sumber.metadb_ram_mb"], _batas(tersedia * 0.06, 512, 1024))
        tersedia -= redis + engine + metadb + MB_BEAT
    web = _pilih(atur["sumber.web_ram_mb"], int(tersedia * 0.6))
    worker = _pilih(atur["sumber.worker_ram_mb"], int(tersedia * 0.4))
    web_cpu = _pilih(atur["sumber.web_cpu"], _batas(round(host.cpu * 0.6), 1, 128))
    worker_cpu = _pilih(atur["sumber.worker_cpu"], _batas(round(host.cpu * 0.5), 1, 128))

    if web < 1024:
        catatan.append(f"RAM web hanya {web} MB (< 1 GB): naikkan memori Docker Desktop "
                       "(Settings → Resources) minimal 6 GB.")
    if web + worker + redis + engine + metadb + (MB_BEAT if peran == "utama" else 0) > host.ram_mb:
        catatan.append("Total jatah RAM melebihi RAM Docker; container bisa dimatikan sistem (OOM).")
    return {"web_ram_mb": web, "worker_ram_mb": worker, "redis_ram_mb": redis,
            "engine_ram_mb": engine, "metadb_ram_mb": metadb,
            "web_cpu": web_cpu, "worker_cpu": worker_cpu, "beat_ram_mb": MB_BEAT, "catatan": catatan}


# --- Tahap 2: jumlah proses di dalam container -------------------------------------------------
def proses_web(c: Perangkat, atur: dict[str, Any]) -> dict[str, int]:
    worker = _pilih(atur["web.worker"],
                    _batas(min(2 * c.cpu + 1, c.ram_mb / MB_PER_PROSES_WEB), 1, 16))
    thread = _pilih(atur["web.thread"], 8 if c.ram_mb / worker >= 1200 else 4)
    return {"worker": worker, "thread": thread, "timeout": int(atur["web.timeout_detik"]),
            "daur_ulang": int(atur["web.daur_ulang"])}


def proses_worker(c: Perangkat, atur: dict[str, Any]) -> dict[str, int]:
    """Jumlah proses per antrean backgrounder (0 = antrean tidak dilayani di node ini)."""
    total = _batas(min(2 * c.cpu, c.ram_mb / MB_PER_PROSES_WORKER), 1, 24)
    tetap = {"cache": int(atur["antrean.cache"]), "laporan": int(atur["antrean.laporan"]),
             "ekstrak": int(atur["antrean.ekstrak"])}
    sisa = max(1, total - sum(tetap.values()))
    chart_async = bool(atur["fitur.chart_async"])
    sqllab_auto = math.ceil(sisa / 2) if chart_async else sisa
    sqllab = _pilih(atur["antrean.sqllab"], sqllab_auto)
    grafik = _pilih(atur["antrean.grafik"], max(1, sisa - sqllab_auto) if chart_async else 0)
    return {"sqllab": sqllab, "grafik": grafik, **tetap}


# Nama antrean Celery untuk tiap jenis tugas (dipakai konfig.py & peluncur).
ANTREAN = {
    "sqllab": ["sql_lab.get_sql_results", "query_execution.execute_sql"],
    "grafik": ["load_chart_data_into_cache", "load_explore_json_into_cache"],
    "cache": ["cache-warmup", "fetch_url", "sps.warna.kunci"],
    "ekstrak": ["sps.ekstrak.segarkan", "sps.ekstrak.jadwal", "sps.ramalan.segarkan", "sps.berkas.ekspor"],
    "laporan": ["reports.scheduler", "reports.execute", "reports.prune_log", "prune_logs",
                "prune_query", "prune_tasks", "cache_chart_thumbnail", "cache_dashboard_thumbnail",
                "cache_dashboard_screenshot", "slack.cache_channels", "tasks.execute"],
}
