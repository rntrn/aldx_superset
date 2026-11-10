"""Mendaftarkan koneksi sumber data (Oracle & ClickHouse) ke Superset dari .env.

Dijalankan oleh scripts/add-connections.ps1:
    python /app/pythonpath/sps_connections.py

- Koneksi yang password-nya kosong di .env dilewati.
- Aman dijalankan berulang: koneksi yang sudah ada diperbarui, bukan diduplikasi.
- Password disimpan terenkripsi oleh Superset (memakai SUPERSET_SECRET_KEY).

Menambah koneksi baru:
    1. Tambahkan baris di CONNECTIONS di bawah (nama tampilan, jenis, prefix .env).
    2. Isi variabel <PREFIX>_HOST / _PORT / _DB / _USER / _PASSWORD di .env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Connection:
    name: str     # nama yang tampil di Superset
    kind: str     # "oracle" atau "clickhouse"
    prefix: str   # awalan variabel di .env
    nama_lama: tuple[str, ...] = ()     # nama tampilan versi lama (diganti otomatis)
    prefix_lama: str = ""               # awalan .env versi lama (masih dibaca)

    def env(self, field: str) -> str:
        nilai = os.environ.get(f"{self.prefix}_{field}", "").strip()
        if not nilai and self.prefix_lama:
            nilai = os.environ.get(f"{self.prefix_lama}_{field}", "").strip()
        return nilai

    def uri(self) -> str:
        user, password = quote_plus(self.env("USER")), quote_plus(self.env("PASSWORD"))
        host, port, db = self.env("HOST"), self.env("PORT"), self.env("DB")
        if self.kind == "oracle":
            # DB = service name Oracle. Driver: oracledb (lihat superset_config.py).
            return f"oracle://{user}:{password}@{host}:{port}/?service_name={db}"
        if self.kind == "clickhouse":
            return f"clickhousedb://{user}:{password}@{host}:{port}/{db}"
        raise ValueError(f"Jenis koneksi tidak dikenal: {self.kind}")


CONNECTIONS = [
    Connection("Oracle DMP (GENAPP)", "oracle", "ORACLE_DMP"),
    Connection("Oracle Dashboard (IKU)", "oracle", "ORACLE_IKU"),
    Connection("Oracle Dashboard (DASHBD)", "oracle", "ORACLE_DASHBD",
               nama_lama=("Oracle Dashboard (TABLEAU)",), prefix_lama="ORACLE_TABLEAU"),
    Connection("ClickHouse DMP_OLAP", "clickhouse", "CLICKHOUSE"),
]


def register_all() -> None:
    from superset import db
    from superset.app import create_app
    from superset.models.core import Database
    from superset.utils.database import get_or_create_db

    with create_app().app_context():
        for conn in CONNECTIONS:
            for lama in conn.nama_lama:                     # ganti nama koneksi lama (izin ikut diganti Superset)
                d = db.session.query(Database).filter_by(database_name=lama).one_or_none()
                if d is not None and not db.session.query(Database).filter_by(database_name=conn.name).first():
                    d.database_name = conn.name
                    print(f"GANTI   {lama} -> {conn.name}")
            if not conn.env("PASSWORD"):
                print(f"LEWAT   {conn.name}: {conn.prefix}_PASSWORD kosong di .env")
                continue
            database = get_or_create_db(conn.name, conn.uri())
            database.expose_in_sqllab = True
            print(f"OK      {conn.name}")
        db.session.commit()


if __name__ == "__main__":
    register_all()
