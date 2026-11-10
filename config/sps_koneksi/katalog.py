"""Katalog sumber data untuk wizard "Hubungkan data".

Satu entri = satu jenis database. Menambah jenis baru cukup menambah satu Jenis(...)
dan (bila perlu) paket drivernya di docker/wheels/paket.txt.

Setiap isian punya `kunci` yang dipakai di templat URI. Nilai dimasukkan ke URI
dengan aman (quote_plus), jadi password boleh berisi karakter khusus.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Isian:
    kunci: str
    label: str
    bawaan: str = ""
    jenis: str = "teks"          # teks | angka | rahasia | panjang | ya_tidak
    wajib: bool = True
    bantu: str = ""

    @property
    def publik(self) -> dict:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Jenis:
    id: str
    nama: str
    kelompok: str                # database | gudang | cloud
    driver: str                  # modul Python yang harus ada
    isian: tuple[Isian, ...]
    uri: Callable[[dict], str]
    keterangan: str = ""
    extra: Callable[[dict], dict] = field(default=lambda n: {})
    rahasia_extra: Callable[[dict], dict] = field(default=lambda n: {})

    def driver_ada(self) -> bool:
        try:
            return importlib.util.find_spec(self.driver) is not None
        except ModuleNotFoundError:          # paket induk (mis. "snowflake") tidak ada
            return False

    @property
    def publik(self) -> dict:
        return {"id": self.id, "nama": self.nama, "kelompok": self.kelompok, "keterangan": self.keterangan,
                "isian": [i.publik for i in self.isian], "driver_ada": self.driver_ada(),
                "paket": self.driver.split(".")[0]}


KELOMPOK = {"database": "Database", "gudang": "Data warehouse & lakehouse", "cloud": "Layanan cloud",
            "lain": "Lainnya"}


# --- Isian yang sering dipakai -------------------------------------------------------------------
def _host(port: str) -> tuple[Isian, ...]:
    return (Isian("host", "Alamat server", bantu="IP atau nama server, mis. 10.1.2.3 atau db.kantor.local"),
            Isian("port", "Port", port, "angka"))


USER = Isian("user", "Nama pengguna")
PASSWORD = Isian("password", "Password", jenis="rahasia", wajib=False)
DATABASE = Isian("database", "Nama database")


def q(n: dict, k: str) -> str:
    """Nilai isian, aman untuk URI."""
    return quote_plus(str(n.get(k, "") or "").strip())


def _auth(n: dict) -> str:
    return q(n, "user") + (f":{q(n, 'password')}" if n.get("password") else "")


def _dasar(skema: str, n: dict, akhir: str = "") -> str:
    return f"{skema}://{_auth(n)}@{q(n, 'host')}:{q(n, 'port')}/{q(n, 'database')}{akhir}"


def _ssl(n: dict, kunci: str = "sslmode", nilai: str = "require") -> str:
    return f"?{kunci}={nilai}" if n.get("ssl") else ""


SSL = Isian("ssl", "Wajib SSL/TLS", jenis="ya_tidak", wajib=False)

KATALOG: tuple[Jenis, ...] = (
    Jenis("postgresql", "PostgreSQL", "database", "psycopg2", (*_host("5432"), DATABASE, USER, PASSWORD, SSL),
          lambda n: _dasar("postgresql+psycopg2", n, _ssl(n)), "Juga untuk Supabase, Neon, Amazon RDS/Aurora PostgreSQL."),
    Jenis("mysql", "MySQL / MariaDB", "database", "pymysql", (*_host("3306"), DATABASE, USER, PASSWORD),
          lambda n: _dasar("mysql+pymysql", n, "?charset=utf8mb4"), "Juga untuk XAMPP, Amazon RDS MySQL, TiDB."),
    Jenis("mssql", "SQL Server / Azure SQL / Synapse", "database", "pymssql", (*_host("1433"), DATABASE, USER, PASSWORD),
          lambda n: _dasar("mssql+pymssql", n), "Login SQL Server (bukan Windows authentication)."),
    Jenis("oracle", "Oracle", "database", "oracledb",
          (*_host("1521"), Isian("service", "Service name", bantu="mis. ORCLPDB1"), USER, PASSWORD),
          lambda n: f"oracle://{_auth(n)}@{q(n, 'host')}:{q(n, 'port')}/?service_name={q(n, 'service')}",
          "Oracle 11g ke atas (mode thin, tanpa Oracle Client). Pakai service name, bukan SID."),
    Jenis("clickhouse", "ClickHouse", "database", "clickhouse_connect",
          (*_host("8123"), DATABASE, USER, PASSWORD, Isian("ssl", "HTTPS", jenis="ya_tidak", wajib=False)),
          lambda n: _dasar("clickhousedb", n, "?protocol=https" if n.get("ssl") else ""), "Port HTTP (8123 / 8443)."),
    Jenis("snowflake", "Snowflake", "gudang", "snowflake.sqlalchemy",
          (Isian("account", "Account identifier", bantu="mis. xy12345.ap-southeast-1"), USER, PASSWORD, DATABASE,
           Isian("schema", "Schema", "PUBLIC", wajib=False), Isian("warehouse", "Warehouse"),
           Isian("role", "Role", wajib=False)),
          lambda n: (f"snowflake://{_auth(n)}@{q(n, 'account')}/{q(n, 'database')}/{q(n, 'schema') or 'PUBLIC'}"
                     f"?warehouse={q(n, 'warehouse')}" + (f"&role={q(n, 'role')}" if n.get("role") else ""))),
    Jenis("bigquery", "Google BigQuery", "gudang", "sqlalchemy_bigquery",
          (Isian("project", "Project ID"),
           Isian("kredensial", "Kunci service account (JSON)", jenis="panjang",
                 bantu="Tempel isi berkas .json service account. Disimpan terenkripsi.")),
          lambda n: f"bigquery://{q(n, 'project')}",
          rahasia_extra=lambda n: {"credentials_info": json.loads(n["kredensial"])}),
    Jenis("redshift", "Amazon Redshift", "gudang", "sqlalchemy_redshift", (*_host("5439"), DATABASE, USER, PASSWORD),
          lambda n: _dasar("redshift+psycopg2", n, "?sslmode=prefer"), "Endpoint cluster, port 5439."),
    Jenis("databricks", "Databricks SQL", "gudang", "databricks.sqlalchemy",
          (Isian("host", "Server hostname", bantu="mis. adb-123.azuredatabricks.net"),
           Isian("http_path", "HTTP path", bantu="SQL Warehouse > Connection details"),
           Isian("token", "Access token", jenis="rahasia"), Isian("catalog", "Catalog", "hive_metastore"),
           Isian("schema", "Schema", "default")),
          lambda n: (f"databricks://token:{q(n, 'token')}@{q(n, 'host')}:443?http_path={q(n, 'http_path')}"
                     f"&catalog={q(n, 'catalog')}&schema={q(n, 'schema')}")),
    Jenis("trino", "Trino / Starburst / Presto", "gudang", "trino",
          (*_host("8080"), USER, PASSWORD, Isian("catalog", "Catalog"), Isian("schema", "Schema", wajib=False),
           Isian("ssl", "HTTPS", jenis="ya_tidak", wajib=False)),
          lambda n: (f"trino://{_auth(n)}@{q(n, 'host')}:{q(n, 'port')}/{q(n, 'catalog')}"
                     + (f"/{q(n, 'schema')}" if n.get("schema") else "") + ("?protocol=https" if n.get("ssl") else ""))),
    Jenis("athena", "Amazon Athena", "gudang", "pyathena",
          (Isian("region", "Region", "ap-southeast-1"), Isian("s3", "S3 staging dir", bantu="mis. s3://bucket/athena-hasil/"),
           Isian("akses", "Access key ID"), Isian("rahasia", "Secret access key", jenis="rahasia"),
           Isian("schema", "Database (schema)", "default")),
          lambda n: (f"awsathena+rest://{q(n, 'akses')}:{q(n, 'rahasia')}@athena.{q(n, 'region')}.amazonaws.com:443/"
                     f"{q(n, 'schema')}?s3_staging_dir={q(n, 's3')}")),
    Jenis("hana", "SAP HANA", "gudang", "sqlalchemy_hana",
          (*_host("30015"), Isian("database", "Tenant database", wajib=False), USER, PASSWORD),
          lambda n: _dasar("hana", n), "Tenant database kosong = SYSTEMDB."),
    Jenis("vertica", "Vertica", "gudang", "vertica_python", (*_host("5433"), DATABASE, USER, PASSWORD),
          lambda n: _dasar("vertica+vertica_python", n), "Port bawaan 5433."),
    Jenis("druid", "Apache Druid", "gudang", "pydruid", (*_host("8082"), Isian("ssl", "HTTPS", jenis="ya_tidak", wajib=False)),
          lambda n: f"druid{'+https' if n.get('ssl') else ''}://{q(n, 'host')}:{q(n, 'port')}/druid/v2/sql/"),
    Jenis("lain", "Lainnya (URI SQLAlchemy)", "lain", "sqlalchemy",
          (Isian("uri", "URI SQLAlchemy", jenis="rahasia",
                 bantu="Untuk admin berpengalaman, mis. dialek+driver://user:pass@host:port/db"),),
          lambda n: str(n.get("uri", "")).strip(), "Semua database yang driver Python-nya terpasang."),
)
PETA = {j.id: j for j in KATALOG}

# Berkas yang diimpor ke ALDx Engine (bukan dihubungkan langsung).
BERKAS = {".mdb": "Microsoft Access", ".accdb": "Microsoft Access", ".xlsx": "Excel", ".xls": "Excel 97-2003",
          ".csv": "CSV", ".txt": "CSV/teks", ".tsv": "TSV", ".sqlite": "SQLite", ".db": "SQLite",
          ".duckdb": "DuckDB", ".parquet": "Parquet"}


def periksa(jenis: Jenis, n: dict[str, Any]) -> None:
    for i in jenis.isian:
        if i.wajib and i.jenis != "ya_tidak" and not str(n.get(i.kunci, "") or "").strip():
            raise ValueError(f"{i.label} wajib diisi")
        if i.jenis == "angka" and n.get(i.kunci) and not str(n[i.kunci]).isdigit():
            raise ValueError(f"{i.label} harus angka")
    if jenis.id == "bigquery":
        try:
            json.loads(n["kredensial"])
        except ValueError as exc:
            raise ValueError("Kunci service account harus JSON utuh (isi berkas .json)") from exc
