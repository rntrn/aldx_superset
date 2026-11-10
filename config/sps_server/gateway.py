"""Gateway (nginx) di depan semua proses web — pintu masuk & pembagi beban.

Tugas gateway:
    - satu alamat untuk pengguna (http://server:8088)
    - membagi beban ke semua node web (least_conn) & failover bila satu node mati
    - menolak upload yang terlalu besar sebelum sampai ke Superset
    - timeout di sisi depan (sedikit lebih lama dari timeout proses web)

Berkas server/gateway.conf DIBUAT ULANG oleh scripts\\terapkan-server.ps1 dari
pengaturan pusat + daftar node web yang online.
"""

from __future__ import annotations

import re
from typing import Any

_IP = re.compile(r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$")


def _baris_server(alamat: str) -> str:
    # "resolve": nginx menanyakan ulang IP container saat container dibuat ulang.
    opsi = "" if _IP.match(alamat) else " resolve"
    return f"    server {alamat}{opsi} max_fails=3 fail_timeout=30s;"


def _batas_unggah_mb(atur: dict[str, Any]) -> int:
    """Ukuran unggahan terbesar yang diizinkan (upload Superset & impor berkas) + 5 MB. 0 = tanpa batas."""
    from sps_server import batas
    nilai = [batas.berlaku(atur, k) for k in ("upload.ukuran_mb", "impor.ukuran_mb")]
    return 0 if None in nilai else max(nilai) + 5


def _blok_https(https: bool) -> str:
    """HTTPS di port yang sama: permintaan http:// otomatis dialihkan ke https:// (kode 497 nginx)."""
    if not https:
        return "    listen 80;"
    return """    listen 80 ssl;
    ssl_certificate     /etc/nginx/tls/aldx.crt;
    ssl_certificate_key /etc/nginx/tls/aldx.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    error_page 497 =301 https://$http_host$request_uri;     # http:// ke port ini -> https://"""


def buat_conf(atur: dict[str, Any], alamat_web: list[str], https: bool = False) -> str:
    alamat = list(dict.fromkeys(["superset:8088", *alamat_web]))      # unik, node utama pertama
    timeout = int(atur["web.timeout_detik"]) + 5
    upload_mb = _batas_unggah_mb(atur)
    servers = "\n".join(_baris_server(a) for a in alamat)
    return f"""# =============================================================================
#  DIBUAT OTOMATIS oleh scripts\\terapkan-server.ps1 - JANGAN diedit manual.
#  Ubah lewat halaman Pusat Kendali Server, lalu jalankan skrip tersebut.
#  Node web: {len(alamat)}
# =============================================================================
resolver 127.0.0.11 valid=10s ipv6=off;    # DNS internal Docker

upstream superset_web {{
    zone superset_web 64k;
    least_conn;
{servers}
    keepalive 32;
}}

server {{
{_blok_https(https)}
    client_max_body_size {upload_mb}m;            # 0 = tanpa batas (Pusat Kendali > Batas data)
    # Alamat & header panjang (mis. kueri panjang, cookie besar) tidak boleh berujung 414/502.
    large_client_header_buffers 8 64k;
    proxy_buffer_size 64k;
    proxy_buffers 16 64k;
    proxy_busy_buffers_size 128k;
    proxy_connect_timeout 5s;
    proxy_send_timeout {timeout}s;
    proxy_read_timeout {timeout}s;

    location / {{
        proxy_pass http://superset_web;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # node mati / sibuk -> coba node lain (hanya untuk permintaan baca)
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }}
}}

# Status gateway untuk halaman Pusat Kendali: port internal tanpa HTTPS, hanya jaringan Docker/kantor.
server {{
    listen 8081;
    location = /sps-gateway-status {{
        stub_status;
        allow 127.0.0.1; allow 10.0.0.0/8; allow 172.16.0.0/12; allow 192.168.0.0/16;
        deny all;
    }}
}}
"""
