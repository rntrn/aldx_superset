"""Nilai dari environment (.env) yang dipakai bersama superset_config & proses node.

Dipisah dari superset_config agar proses ringan (peluncur node, skrip terapkan)
bisa membaca alamat database/Redis tanpa memuat seluruh Superset.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from urllib.parse import quote_plus


def wajib(nama: str, bawaan: str | None = None) -> str:
    """Ambil environment variable; hentikan start bila kosong."""
    nilai = os.environ.get(nama, bawaan)
    if not nilai:
        raise RuntimeError(f"Variabel '{nama}' wajib diisi di file .env")
    return nilai


def uri_metadata() -> str:
    """URI database metadata Superset (PostgreSQL container metadb, database sps_superset).

    SPS_METADATA_URI hanya untuk pengujian (mis. SQLite); produksi tidak mengisinya.
    """
    if os.environ.get("SPS_METADATA_URI"):
        return os.environ["SPS_METADATA_URI"]
    return "postgresql+psycopg2://{u}:{p}@{h}:{port}/{db}".format(
        u=quote_plus(wajib("METADB_USER", "superset")), p=quote_plus(wajib("METADB_PASSWORD")),
        h=wajib("METADB_HOST", "metadb"), port=wajib("METADB_PORT", "5432"),
        db=wajib("METADB_DATABASE", "sps_superset"))


def uri_metadata_lama() -> str | None:
    """URI metadata MySQL/MariaDB versi lama (XAMPP atau container MariaDB), untuk pindah.

    None bila .env tidak menyimpan pengaturan lama (instalasi baru).
    """
    if os.environ.get("SPS_METADATA_LAMA_URI"):
        return os.environ["SPS_METADATA_LAMA_URI"]
    if not os.environ.get("MYSQL_PASSWORD"):
        return None
    return "mysql+pymysql://{u}:{p}@{h}:{port}/{db}?charset=utf8mb4".format(
        u=quote_plus(os.environ.get("MYSQL_USER", "superset")), p=quote_plus(os.environ["MYSQL_PASSWORD"]),
        h=os.environ.get("MYSQL_HOST", "metadb-lama"), port=os.environ.get("MYSQL_PORT", "3306"),
        db=os.environ.get("MYSQL_DATABASE", "sps_superset"))


@dataclass(frozen=True)
class Engine:
    """ALDx Engine: ClickHouse internal (container "engine") untuk ekstrak, upload, ramalan."""
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def uri(self) -> str:
        """URI SQLAlchemy untuk koneksi Superset (driver clickhouse-connect)."""
        return (f"clickhousedb://{quote_plus(self.user)}:{quote_plus(self.password)}"
                f"@{self.host}:{self.port}/{self.database}")


def engine() -> Engine:
    return Engine(host=os.environ.get("ENGINE_HOST", "engine"), port=int(os.environ.get("ENGINE_PORT", "8123")),
                  user=os.environ.get("ENGINE_USER", "sps"), password=os.environ.get("ENGINE_PASSWORD", ""),
                  database=os.environ.get("ENGINE_DATABASE", "sps_engine"))


@dataclass(frozen=True)
class Redis:
    """Alamat Redis (cache server + antrean backgrounder). host kosong = Redis tidak dipakai."""
    host: str
    port: int
    password: str

    @property
    def aktif(self) -> bool:
        return bool(self.host)

    def url(self, db: int) -> str:
        auth = f":{quote_plus(self.password)}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{db}"


def redis() -> Redis:
    return Redis(host=os.environ.get("REDIS_HOST", "").strip(),
                 port=int(os.environ.get("REDIS_PORT", "6379")),
                 password=os.environ.get("REDIS_PASSWORD", ""))


@dataclass(frozen=True)
class Node:
    """Identitas container ini dalam cluster.

    nama    : nama komputer (node), mis. SRV-DJP-01
    peran   : "utama" (web + backgrounder + cache + gateway) | "tambahan" (web + backgrounder)
    layanan : web | worker | beat  (diisi docker-compose per container)
    alamat  : host:port web node ini yang bisa dijangkau gateway node utama
    """
    nama: str
    peran: str
    layanan: str
    alamat: str


def node() -> Node:
    layanan = os.environ.get("NODE_LAYANAN", "web")
    peran = os.environ.get("NODE_PERAN", "utama")
    alamat = os.environ.get("NODE_ALAMAT", "")
    if not alamat and layanan == "web":
        alamat = "superset:8088" if peran == "utama" else f"{socket.gethostname()}:8088"
    return Node(nama=os.environ.get("NODE_NAMA") or socket.gethostname(),
                peran=peran, layanan=layanan, alamat=alamat)
