"""Peluncur proses tiap container (pengganti perintah bawaan image Superset).

    python -m sps_server.jalankan web      Gunicorn (proses & thread dari auto-tuning)
    python -m sps_server.jalankan worker   Celery: satu kelompok proses per antrean
    python -m sps_server.jalankan beat     Celery beat: penjadwal tugas

Alur:
    1. baca pengaturan pusat + ukur CPU/RAM container   (auto-tuning)
    2. jalankan proses anak
    3. setiap 30 detik: kirim detak (heartbeat) ke tabel sps_node
       -> tampil di Pusat Kendali: node, proses, pemakaian CPU/RAM
    4. bila satu proses anak berhenti -> hentikan semua & keluar,
       Docker akan menyalakan ulang container (restart: unless-stopped)
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

from sps_server import lingkungan, penyimpanan, tuning

log = logging.getLogger("sps_server.jalankan")
DETIK_DETAK = 30
CELERY_APP = "--app=superset.tasks.celery_app:app"


def perintah_web(p: dict[str, int]) -> list[list[str]]:
    port = os.environ.get("NODE_PORT_WEB", "8088")         # di dalam container selalu 8088
    return [["gunicorn", "--bind", f"0.0.0.0:{port}",
             "--workers", str(p["worker"]), "--worker-class", "gthread", "--threads", str(p["thread"]),
             "--timeout", str(p["timeout"]), "--graceful-timeout", "30", "--keep-alive", "5",
             "--max-requests", str(p["daur_ulang"]), "--max-requests-jitter", str(p["daur_ulang"] // 10),
             "--limit-request-line", "0", "--limit-request-field_size", "0",
             "--access-logfile", "-", "--error-logfile", "-",
             "superset.app:create_app()"]]


def perintah_worker(p: dict[str, int], nama_node: str) -> list[list[str]]:
    return [["celery", CELERY_APP, "worker", "-Q", antrean, "-c", str(n), "-n", f"{antrean}@{nama_node}",
             "-O", "fair", "-l", "INFO", "--max-tasks-per-child", "200"]
            for antrean, n in p.items() if n > 0]


def perintah_beat() -> list[list[str]]:
    return [["celery", CELERY_APP, "beat", "-l", "INFO",
             "-s", "/tmp/celerybeat-schedule", "--pidfile", "/tmp/celerybeat.pid"]]


def rencana(layanan: str, atur: dict[str, Any], node: lingkungan.Node) -> tuple[dict, list[list[str]]]:
    """Hitung jumlah proses (auto-tuning) dan susun perintahnya."""
    c = tuning.perangkat_container()
    if layanan == "web":
        p = tuning.proses_web(c, atur)
        return p, perintah_web(p)
    if layanan == "worker":
        p = tuning.proses_worker(c, atur)
        return p, perintah_worker(p, node.nama)
    if layanan == "beat":
        return {"beat": 1}, perintah_beat()
    raise SystemExit(f"Layanan tidak dikenal: {layanan} (pakai web | worker | beat)")


def _detak(node: lingkungan.Node, proses: dict, atur: dict, mulai: datetime, sebelumnya: dict) -> dict:
    pakai = tuning.pemakaian_container(sebelumnya)
    c, host = tuning.perangkat_container(), tuning.perangkat_host()
    data = {"node": node.nama, "layanan": node.layanan, "peran": node.peran, "alamat": node.alamat,
            "cpu": c.cpu, "ram_mb": c.ram_mb, "host_cpu": host.cpu, "host_ram_mb": host.ram_mb,
            "cpu_persen": pakai["cpu_persen"], "ram_terpakai_mb": pakai["ram_terpakai_mb"],
            "proses": proses, "nilai_saat_start": {k: atur[k] for k in atur
                                                   if k.split(".")[0] in ("web", "antrean", "fitur")}}
    try:
        penyimpanan.detak(f"{node.nama}/{node.layanan}", data, mulai)
    except Exception as exc:  # noqa: BLE001 - database sementara mati: proses tetap jalan
        log.warning("Detak gagal: %s", exc)
    return pakai["_mentah"]


def main(layanan: str) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    node = lingkungan.node()
    atur = penyimpanan.nilai_semua()
    proses, perintah = rencana(layanan, atur, node)
    log.info("Node %s (%s) layanan %s -> %s", node.nama, node.peran, layanan, proses)
    if not perintah:
        log.warning("Tidak ada proses untuk dijalankan (semua antrean = 0). Container menganggur.")

    anak = [subprocess.Popen(p) for p in perintah]

    def berhenti(signum, _frame):
        log.info("Sinyal %s: menghentikan %d proses", signum, len(anak))
        for a in anak:
            a.send_signal(signal.SIGTERM)

    signal.signal(signal.SIGTERM, berhenti)
    signal.signal(signal.SIGINT, berhenti)

    mulai, sebelumnya, detak_berikut = datetime.now(), None, 0.0
    while True:
        selesai = [a for a in anak if a.poll() is not None]
        if selesai:
            for a in anak:
                if a.poll() is None:
                    a.terminate()
            for a in anak:
                a.wait(timeout=60)
            kode = selesai[0].returncode
            log.info("Proses berhenti (kode %s); container keluar", kode)
            return kode
        if time.monotonic() >= detak_berikut:
            sebelumnya = _detak(node, proses, atur, mulai, sebelumnya)
            detak_berikut = time.monotonic() + DETIK_DETAK
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "web"))
