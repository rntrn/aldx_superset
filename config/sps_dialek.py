"""Penyesuaian Superset untuk database tertentu & pengaman chart berat.

Dipasang sekali saat start (FLASK_APP_MUTATOR, juga di backgrounder):

    1. Oracle: batas baris memakai ROWNUM.
       Superset 6 menambahkan "FETCH FIRST n ROWS ONLY" (sintaks Oracle 12c+) pada kueri SQL Lab,
       Kueri Visual, sampel dataset, dan dataset virtual. Oracle 11g ke bawah menolaknya dengan
       ORA-00933 "SQL command not properly ended". ROWNUM berlaku di SEMUA versi Oracle:
           SELECT * FROM (<kueri asli>) sps_batas WHERE ROWNUM <= n
    2. Oracle: titik koma di akhir kueri dibuang sebelum dikirim (driver Oracle menolaknya).
    3. Oracle: kolom NUMBER / FLOAT / BINARY_DOUBLE dikenali sebagai ANGKA, sehingga Explore & Studio
       bisa menyarankan ukuran (SUM, AVG, ...). Sebelumnya tampil sebagai tipe "?".
    4. Chart berat (Tree, Graph, Sankey, Sunburst, Treemap, Word cloud, ...) dibatasi
       Pusat Kendali › Pengaturan › "Baris maksimal chart berat" (bawaan 1.000) agar browser tidak macet.
    5. ClickHouse (termasuk ALDx Engine): kolom Float32/Float64/Double (juga di dalam Nullable(...) /
       LowCardinality(...)) dikenali sebagai ANGKA. Superset 6.1 hanya mengenali Int & Decimal, sehingga kolom
       desimal seperti `total` tampil sebagai teks: masuk Dimensi di Studio, tidak bisa dijumlah, dan
       Ramalan/Tren/Anomali tidak bisa dipakai.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

CHART_BERAT = frozenset({"tree_chart", "graph_chart", "sankey_v2", "sankey", "sunburst_v2", "sunburst",
                         "treemap_v2", "treemap", "word_cloud", "chord", "partition", "bubble_v2", "bubble",
                         "deck_scatter", "deck_hex", "deck_arc", "deck_path"})
ALIAS_BATAS = "sps_batas"


# --- 1. Oracle: ROWNUM -----------------------------------------------------------------------------
def _batas_oracle() -> None:
    from sqlglot import exp
    from superset.sql.parse import LimitMethod, SQLStatement

    asli = SQLStatement.set_limit_value
    if getattr(asli, "_sps", False):
        return

    def set_limit_value(self, limit: int, method: LimitMethod = LimitMethod.FORCE_LIMIT) -> None:
        if self.engine != "oracle" or method == LimitMethod.FETCH_MANY:
            return asli(self, limit, method)
        if not isinstance(self._parsed, exp.Query):        # bukan SELECT (mis. DDL): tidak dibatasi
            return None
        self._parsed = (exp.select("*")
                        .from_(exp.Subquery(this=self._parsed.copy(), alias=exp.TableAlias(this=exp.to_identifier(ALIAS_BATAS))))
                        .where(exp.LTE(this=exp.column("ROWNUM"), expression=exp.Literal.number(int(limit)))))
        return None

    set_limit_value._sps = True
    SQLStatement.set_limit_value = set_limit_value


# --- 2 & 3. Oracle: titik koma & tipe angka ----------------------------------------------------------
def _oracle_spec() -> None:
    from sqlalchemy import types
    from superset.db_engine_specs.oracle import OracleEngineSpec
    from superset.utils.core import GenericDataType

    if getattr(OracleEngineSpec, "_sps", False):
        return
    OracleEngineSpec.column_type_mappings = (
        (re.compile(r"^NUMBER\(\d+\)$|^NUMBER\(\d+,\s*0\)$|^(SMALL)?INT(EGER)?$", re.I), types.Integer(), GenericDataType.NUMERIC),
        (re.compile(r"^(NUMBER|DECIMAL|NUMERIC|FLOAT|BINARY_FLOAT|BINARY_DOUBLE|DOUBLE)", re.I), types.Numeric(),
         GenericDataType.NUMERIC),
        (re.compile(r"^(N?VARCHAR2?|N?CHAR|N?CLOB)", re.I), types.String(), GenericDataType.STRING),
    ) + tuple(OracleEngineSpec.column_type_mappings)

    eksekusi_asli = OracleEngineSpec.execute.__func__

    @classmethod
    def execute(cls, cursor, query: str, database, **kwargs):
        return eksekusi_asli(cls, cursor, re.sub(r"[\s;]+$", "", query), database, **kwargs)

    OracleEngineSpec.execute = execute
    OracleEngineSpec._sps = True


# --- 5. ClickHouse: Float/Double = angka ------------------------------------------------------------
def _clickhouse_spec() -> None:
    from sqlalchemy import types
    from superset.db_engine_specs import clickhouse as ch
    from superset.utils.core import GenericDataType

    angka = (re.compile(r"^(Nullable\(|LowCardinality\()*(Float(32|64)?|Double)\b", re.I), types.Float(),
             GenericDataType.NUMERIC)
    for kelas in (ch.ClickHouseBaseEngineSpec, ch.ClickHouseEngineSpec, ch.ClickHouseConnectEngineSpec):
        # Ditempel di setiap kelas yang punya daftar sendiri (bukan warisan), sekali saja.
        if "_sps" not in kelas.__dict__ and ("column_type_mappings" in kelas.__dict__ or kelas is ch.ClickHouseBaseEngineSpec):
            kelas.column_type_mappings = (angka,) + tuple(kelas.column_type_mappings)
            kelas._sps = True


# --- 4. Chart berat -----------------------------------------------------------------------------------
def _batas_chart_berat(app) -> None:
    from superset.common.query_context_factory import QueryContextFactory

    asli = QueryContextFactory.create
    if getattr(asli, "_sps", False):
        return

    def create(self, *, queries, form_data=None, **kwargs):
        jenis = (form_data or {}).get("viz_type")
        if jenis in CHART_BERAT:
            maks = int(app.config.get("SPS_SERVER", {}).get("batas.baris_chart_berat") or 0)
            for q in queries or []:
                if maks and (not q.get("row_limit") or int(q["row_limit"]) > maks):
                    log.info("ALDx: row_limit chart %s dibatasi %s baris", jenis, maks)
                    q["row_limit"] = maks
        return asli(self, queries=queries, form_data=form_data, **kwargs)

    create._sps = True
    QueryContextFactory.create = create


def pasang(app) -> None:
    for nama, fungsi in (("batas Oracle", _batas_oracle), ("spesifikasi Oracle", _oracle_spec),
                         ("tipe angka ClickHouse", _clickhouse_spec),
                         ("chart berat", lambda: _batas_chart_berat(app))):
        try:
            fungsi()
        except Exception:  # noqa: BLE001 - penyesuaian gagal tidak boleh mematikan Superset
            log.exception("ALDx dialek: gagal memasang %s", nama)
