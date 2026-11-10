"""Hitung nilai yang butuh restart & tulis berkas gateway (dipanggil terapkan-server.ps1).

    python -m sps_server.terapkan utama      node utama (web + backgrounder + cache + gateway)
    python -m sps_server.terapkan tambahan   node tambahan (web + backgrounder)

stdout : baris KEY=VALUE untuk blok "SERVER" di .env (dibaca docker-compose)
stderr : ringkasan untuk admin
berkas : /app/server/gateway.conf (hanya node utama)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sps_server import gateway, penyimpanan, tls, tuning

# Folder server/ proyek (di container: /app/server, di-mount dari D:\superset\server).
GATEWAY_CONF = Path(os.environ.get("SPS_SERVER_DIR", "/app/server")) / "gateway.conf"
MB_OVERHEAD_REDIS = 128        # memori Redis di luar data cache


def blok_env(peran: str) -> tuple[dict[str, str], list[str]]:
    atur = penyimpanan.nilai_semua()
    host = tuning.perangkat_host()
    a = tuning.alokasi_container(host, peran, atur)
    env = {
        "WEB_CPUS": str(a["web_cpu"]), "WEB_MEM": f"{a['web_ram_mb']}m",
        "WORKER_CPUS": str(a["worker_cpu"]), "WORKER_MEM": f"{a['worker_ram_mb']}m",
        "BEAT_MEM": f"{a['beat_ram_mb']}m",
    }
    if peran == "utama":
        env["REDIS_MEM_MB"] = str(a["redis_ram_mb"])
        env["REDIS_MEM_LIMIT"] = f"{a['redis_ram_mb'] + MB_OVERHEAD_REDIS}m"
        env["ENGINE_MEM"] = f"{a['engine_ram_mb']}m"
        env["METADB_MEM"] = f"{a['metadb_ram_mb']}m"
        # PostgreSQL: shared_buffers ~25% RAM container, effective_cache_size ~75% (anjuran resmi).
        env["METADB_BUFFER"] = f"{max(32, a['metadb_ram_mb'] // 4)}MB"
        env["METADB_CACHE"] = f"{max(96, a['metadb_ram_mb'] * 3 // 4)}MB"

    ringkas = [f"Perangkat Docker node ini: {host.cpu:g} CPU, {host.ram_mb} MB RAM",
               f"Web       : {a['web_cpu']} CPU, {a['web_ram_mb']} MB",
               f"Backgrounder: {a['worker_cpu']} CPU, {a['worker_ram_mb']} MB"]
    if peran == "utama":
        ringkas.append(f"Cache (Redis): {a['redis_ram_mb']} MB · ALDx Engine: {a['engine_ram_mb']} MB · "
                       f"Katalog: {a['metadb_ram_mb']} MB")
    ringkas += [f"PERINGATAN: {c}" for c in a["catatan"]]

    if peran == "utama":
        web_lain = [n["alamat"] for n in penyimpanan.daftar_node()
                    if n["layanan"] == "web" and n["peran"] == "tambahan" and n["online"] and n["alamat"]]
        if tls.aktif():
            ringkas.append(tls.pastikan())
        GATEWAY_CONF.write_text(gateway.buat_conf(atur, web_lain, https=tls.aktif()), encoding="utf-8")
        ringkas.append(f"Gateway: {1 + len(web_lain)} node web ({', '.join(['utama', *web_lain])})")
    return env, ringkas


def main() -> int:
    peran = sys.argv[1] if len(sys.argv) > 1 else "utama"
    if peran not in ("utama", "tambahan"):
        print("Peran harus 'utama' atau 'tambahan'", file=sys.stderr)
        return 2
    env, ringkas = blok_env(peran)
    for k, v in env.items():
        print(f"{k}={v}")
    for baris in ringkas:
        print(baris, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
