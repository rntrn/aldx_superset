"""Koneksi ke ALDx Engine (ClickHouse internal di container "engine").

Satu antarmuka kecil dipakai seluruh modul:
    perintah(sql)          jalankan DDL/DML
    kueri_df(sql)          hasil sebagai pandas.DataFrame
    sisip_df(tabel, df)    masukkan DataFrame ke tabel (nama lengkap db.tabel)

Produksi memakai clickhouse-connect (HTTP 8123). Untuk pengujian tanpa server,
SPS_ENGINE_CHDB=<folder> memakai chDB (mesin ClickHouse yang sama, sebagai pustaka).
"""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

from sps_server import lingkungan


class KlienHttp:
    def __init__(self, e: lingkungan.Engine):
        import clickhouse_connect
        umum = dict(host=e.host, port=e.port, username=e.user, password=e.password,
                    connect_timeout=10, send_receive_timeout=3600)
        try:
            self._c = clickhouse_connect.get_client(database=e.database, **umum)
        except Exception as exc:  # noqa: BLE001
            # Database engine belum ada (mis. inisialisasi pertama container terputus): buat, lalu sambung ulang.
            if "UNKNOWN_DATABASE" not in str(exc) and "does not exist" not in str(exc):
                raise
            awal = clickhouse_connect.get_client(**umum)
            awal.command(f"CREATE DATABASE IF NOT EXISTS `{e.database}`")
            awal.close()
            self._c = clickhouse_connect.get_client(database=e.database, **umum)

    def perintah(self, sql: str):
        return self._c.command(sql)

    def kueri_df(self, sql: str) -> pd.DataFrame:
        return self._c.query_df(sql)

    def sisip_df(self, tabel: str, df: pd.DataFrame) -> None:
        db, _, nama = tabel.rpartition(".")
        self._c.insert_df(nama, df, database=db or None)


class KlienChdb:  # pragma: no cover - hanya untuk pengujian
    def __init__(self, folder: str):
        from chdb import session
        self._s = session.Session(folder)

    def perintah(self, sql: str):
        return self._s.query(sql)

    def kueri_df(self, sql: str) -> pd.DataFrame:
        return self._s.query(sql, "DataFrame")

    def sisip_df(self, tabel: str, df: pd.DataFrame) -> None:
        sumber = df  # noqa: F841 - dibaca chDB lewat fungsi tabel Python(sumber)
        self._s.query(f"INSERT INTO {tabel} SELECT * FROM Python(sumber)")


@lru_cache(maxsize=1)
def klien():
    folder = os.environ.get("SPS_ENGINE_CHDB")
    return KlienChdb(folder) if folder else KlienHttp(lingkungan.engine())


def nama_db() -> str:
    return lingkungan.engine().database
