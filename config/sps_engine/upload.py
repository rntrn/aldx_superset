"""Upload Excel/CSV langsung ke ALDx Engine (ClickHouse internal).

Superset bawaan tidak mendukung upload ke ClickHouse. Modul ini menambahkannya
HANYA untuk koneksi "ALDx Engine (ClickHouse)"; koneksi ClickHouse lain (mis. milik
sistem sumber) tetap tidak bisa ditulisi. Tabel dibuat dengan tipe hasil tebakan
(tabel.py) dan ENGINE MergeTree.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def pasang() -> None:
    from superset.commands.database.exceptions import DatabaseUploadFailed
    from superset.db_engine_specs.clickhouse import ClickHouseConnectEngineSpec

    from sps_engine import klien as K, tabel as T
    from sps_engine.ekstrak import adalah_engine

    if getattr(ClickHouseConnectEngineSpec, "_sps_upload", False):
        return

    def df_to_sql(cls, database, table, df, to_sql_kwargs):
        if not adalah_engine(database):
            raise DatabaseUploadFailed(message="Upload ke ClickHouse hanya diizinkan ke ALDx Engine.")
        k, db = K.klien(), K.nama_db()
        nama = T.nama_aman(table.table)
        k.perintah(f"CREATE DATABASE IF NOT EXISTS {db}")
        if T.ada(k, db, nama):
            aksi = to_sql_kwargs.get("if_exists", "fail")
            if aksi == "fail":
                raise ValueError("Tabel sudah ada")            # Superset menampilkan pesan bawaan
            if aksi == "append":
                T.isi_tambah(k, db, nama, [df], T.tipe_tabel(k, db, nama))
                return
        T.isi_penuh(k, db, nama, [df], [])
        log.info("ALDx upload ke engine: %s (%d baris)", nama, len(df))

    ClickHouseConnectEngineSpec.supports_file_upload = True
    ClickHouseConnectEngineSpec.df_to_sql = classmethod(df_to_sql)
    ClickHouseConnectEngineSpec._sps_upload = True
