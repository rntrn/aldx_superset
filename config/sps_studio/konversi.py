"""Chart dari editor lanjutan (Explore, impor, Asisten AI lama) -> lembar kerja Studio.

Studio Visual adalah satu-satunya editor chart: chart yang tidak dibuat di Studio dibuka sebagai lembar kerja bila
pengaturannya bisa diwakili rak Studio (jenis umum, metrik AGREGAT(kolom)/tersimpan/COUNT(*), dimensi kolom biasa,
filter sederhana). Yang tidak bisa (metrik/kolom SQL bebas, tabel mentah, jenis khusus) tetap dibuka di Mode lanjutan.

    spec(chart)          -> spesifikasi lembar kerja (bentuk sama dengan params.sps_studio), atau TakBisa
    bisa_cepat(viz, p)   -> perkiraan murah tanpa query (untuk daftar chart & tanda "lanjutan")
"""

from __future__ import annotations

import json
import re
from typing import Any

from sps_ai import alat

VIZ_KE_TANDA = {
    "big_number_total": "angka", "table": "tabel", "pivot_table_v2": "tabel_pivot", "pie": "pie",
    "echarts_timeseries_bar": "batang", "dist_bar": "batang", "echarts_timeseries_line": "garis", "line": "garis",
    "echarts_area": "area", "treemap_v2": "treemap", "funnel": "funnel", "word_cloud": "awan_kata",
}
_AGG = re.compile(r"^\s*(SUM|AVG|COUNT|MIN|MAX|COUNT_DISTINCT)\s*\(\s*([A-Za-z0-9_$#.]+|\*)\s*\)\s*$", re.I)
_KOLOM = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")


class TakBisa(ValueError):
    """Chart ini tidak bisa diwakili lembar kerja Studio (alasan di pesan)."""


def _params(chart) -> dict:
    try:
        return json.loads(chart.params or "{}")
    except ValueError:
        return {}


def _daftar(v) -> list:
    return v if isinstance(v, list) else [v] if v else []


def _metrik(p: dict) -> list:
    return _daftar(p.get("metrics")) or _daftar(p.get("metric"))


def _dimensi_mentah(viz: str, p: dict) -> list:
    if viz in ("echarts_timeseries_bar", "echarts_timeseries_line", "echarts_area"):
        return _daftar(p.get("x_axis")) + _daftar(p.get("groupby"))[:1]
    if viz == "dist_bar":
        return _daftar(p.get("groupby")) + _daftar(p.get("columns"))[:1]
    if viz == "line":
        return _daftar(p.get("granularity_sqla")) + _daftar(p.get("groupby"))[:1]
    if viz == "pivot_table_v2":
        return _daftar(p.get("groupbyRows")) + _daftar(p.get("groupbyColumns"))
    if viz == "word_cloud":
        return _daftar(p.get("series"))
    if viz == "big_number_total":
        return []
    return _daftar(p.get("groupby"))


def _dimensi(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        nama = str(x.get("sqlExpression") or x.get("column_name") or "").strip()
        if _KOLOM.match(nama):
            return nama
    raise TakBisa("ada kolom berupa rumus SQL")


def _ukuran(t, m) -> dict:
    tersimpan = {x.metric_name for x in t.metrics}
    if isinstance(m, str):
        if m in tersimpan:
            return {"field": m, "peran": "ukuran", "metrik": True}
        if m.lower() == "count":
            return {"field": "__baris__", "peran": "ukuran"}
        raise TakBisa(f"metrik '{m}' tidak ada di dataset")
    if not isinstance(m, dict):
        raise TakBisa("metrik tidak dikenal")
    if m.get("expressionType") == "SIMPLE":
        agg = str(m.get("aggregate") or "").upper()
        kol = (m.get("column") or {}).get("column_name")
        if agg == "COUNT" and not kol:
            return {"field": "__baris__", "peran": "ukuran"}
        if agg in lembar_agregat() and kol:
            return {"field": kol, "peran": "ukuran", "agg": agg}
    if m.get("expressionType") == "SQL":
        cocok = _AGG.match(str(m.get("sqlExpression") or ""))
        if cocok:
            agg, kol = cocok.group(1).upper(), cocok.group(2)
            if kol == "*":
                return {"field": "__baris__", "peran": "ukuran"}
            return {"field": kol, "peran": "ukuran", "agg": agg}
    raise TakBisa("ada metrik berupa rumus SQL")


def lembar_agregat() -> tuple[str, ...]:
    from sps_studio.lembar import AGREGAT
    return AGREGAT


def _filter(f: dict) -> list[dict]:
    if f.get("clause", "WHERE") != "WHERE":
        raise TakBisa("ada filter HAVING")
    if f.get("expressionType") != "SIMPLE":
        raise TakBisa("ada filter berupa SQL")
    op, nilai, kol = str(f.get("operator") or "").upper(), f.get("comparator"), f.get("subject")
    if op == "TEMPORAL_RANGE":
        if str(nilai or "No filter") == "No filter":
            return []
        raise TakBisa("ada rentang waktu tetap di chart")
    if op in ("IN", "=="):
        return [{"field": kol, "op": "IN", "nilai": _daftar(nilai) if op == "IN" else [nilai]}]
    if op in (">=", "<="):
        return [{"field": kol, "op": op, "nilai": nilai}]
    raise TakBisa(f"ada filter '{op}' yang tidak tersedia di Studio")


def bisa_cepat(viz: str, p: dict) -> bool:
    """Perkiraan tanpa menyentuh database: jenis dikenal, tidak ada SQL bebas, tabel bukan mode mentah."""
    if viz not in VIZ_KE_TANDA or (viz == "table" and p.get("query_mode") == "raw"):
        return False
    try:
        for x in _dimensi_mentah(viz, p):
            _dimensi(x)
        for m in _metrik(p):
            if isinstance(m, dict) and m.get("expressionType") == "SQL" and not _AGG.match(str(m.get("sqlExpression") or "")):
                return False
        for f in p.get("adhoc_filters") or []:
            _filter(f)
    except TakBisa:
        return False
    return bool(_metrik(p))


def spec(chart, params: dict | None = None) -> dict:
    """Spesifikasi lembar kerja untuk `chart` (params bawaan: params chart saat ini). TakBisa bila tidak terwakili."""
    from sps_ai.auto import spec_dari
    from sps_studio import lembar

    p = params if params is not None else _params(chart)
    viz = chart.viz_type
    tanda = VIZ_KE_TANDA.get(viz)
    if not tanda:
        raise TakBisa(f"jenis '{viz}' belum didukung lembar kerja")
    if viz == "table" and p.get("query_mode") == "raw":
        raise TakBisa("tabel mode baris mentah")
    t = chart.datasource
    if t is None or getattr(chart, "datasource_type", "table") != "table":
        raise TakBisa("sumber data bukan dataset")
    ukuran = [_ukuran(t, m) for m in _metrik(p)]
    if not ukuran:
        raise TakBisa("chart tanpa metrik")
    dims = [_dimensi(x) for x in _dimensi_mentah(viz, p)]
    rak = spec_dari(tanda, ukuran, dims, mendatar=p.get("orientation") == "horizontal")
    filter_ = [x for f in p.get("adhoc_filters") or [] for x in _filter(f)]
    hasil: dict[str, Any] = {"dataset_id": t.id, "tanda": tanda, "judul": chart.slice_name, **rak, "filter": filter_,
                             "batas": int(p.get("row_limit") or 1000),
                             "label": bool(p.get("show_value") or p.get("show_labels") or p.get("show_values"))}
    try:
        _, lb = lembar.dari_dict(hasil)
        lembar.periksa_tanda(lb)
    except (alat.InputSalah, alat.IzinDitolak, ValueError) as e:
        raise TakBisa(str(e)) from None
    return hasil
