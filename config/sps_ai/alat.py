"""Alat (tools) yang dipakai agent, Auto Chart, dan Story.

ATURAN UTAMA: semua fungsi berjalan sebagai user yang sedang login (g.user).
    - Dataset yang tidak boleh diakses user -> IzinDitolak.
    - Query lewat ChartDataCommand resmi Superset -> RLS (hak akses data) berlaku.
    - Membuat chart/dashboard butuh izin tulis (role Alpha/Admin).
Spesifikasi dari model AI TIDAK dipercaya begitu saja: nama kolom, metrik,
operator, dan jenis chart divalidasi terhadap dataset & daftar yang diizinkan.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from flask import g

AGREGAT = ("SUM", "AVG", "COUNT", "MIN", "MAX", "COUNT_DISTINCT")
OPERATOR = ("==", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "LIKE")
_POLA_METRIK = re.compile(r"^\s*(SUM|AVG|COUNT|MIN|MAX|COUNT_DISTINCT)\s*\(\s*([A-Za-z0-9_$#.]+)\s*\)\s*$", re.I)

# jenis chart (bahasa pengguna) -> viz_type Superset
JENIS_CHART = {
    "angka": "big_number_total",
    "tabel": "table",
    "pie": "pie",
    "batang": "echarts_timeseries_bar",
    "garis": "echarts_timeseries_line",
}


class IzinDitolak(PermissionError):
    """User tidak punya izin untuk tindakan ini."""


class InputSalah(ValueError):
    """Spesifikasi (biasanya dari model AI) tidak valid."""


# --- Dataset -------------------------------------------------------------------
def _dataset(dataset_id: int):
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable

    table = db.session.query(SqlaTable).get(int(dataset_id))
    if table is None:
        raise InputSalah(f"Dataset {dataset_id} tidak ada.")
    if not security_manager.can_access_datasource(table):
        raise IzinDitolak(f"Anda tidak punya akses ke dataset {table.table_name}.")
    return table


def _nama_tampil(table) -> str:
    return table.table_name.split("__", 1)[-1].replace("_", " ")


def daftar_dataset(kata_kunci: str = "", batas: int = 50) -> list[dict]:
    """Dataset yang boleh diakses user, opsional disaring kata kunci."""
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable

    kata = (kata_kunci or "").lower().strip()
    hasil = []
    for t in db.session.query(SqlaTable).order_by(SqlaTable.table_name):
        teks = f"{t.table_name} {t.description or ''}".lower()
        if kata and kata not in teks:
            continue
        if security_manager.can_access_datasource(t):
            hasil.append({"id": t.id, "nama": t.table_name, "keterangan": t.description or "",
                          "database_id": t.database_id})
    return hasil[:batas]


def info_dataset(dataset_id: int) -> dict:
    t = _dataset(dataset_id)
    return {
        "id": t.id, "nama": t.table_name, "keterangan": t.description or "",
        "kolom": [{"nama": c.column_name, "tipe": c.type or "", "keterangan": c.description or ""}
                  for c in t.columns if c.is_active is not False],
        "metrik": [{"nama": m.metric_name, "label": m.verbose_name or m.metric_name,
                    "rumus": m.expression} for m in t.metrics],
    }


# --- Validasi spesifikasi -------------------------------------------------------
def _kolom_sah(t, nama: str) -> str:
    peta = {c.column_name.lower(): c.column_name for c in t.columns}
    if str(nama).lower() not in peta:
        raise InputSalah(f"Kolom '{nama}' tidak ada di dataset {t.table_name}.")
    return peta[str(nama).lower()]


def metrik_obj(t, spec: str) -> Any:
    """'penjualan' (metrik tersimpan) atau 'SUM(kolom)' -> objek metrik Superset."""
    simpan = {m.metric_name.lower(): m.metric_name for m in t.metrics}
    if str(spec).lower() in simpan:
        return simpan[str(spec).lower()]
    cocok = _POLA_METRIK.match(str(spec))
    if not cocok:
        raise InputSalah(f"Metrik '{spec}' tidak dikenal. Pakai metrik tersimpan atau "
                         f"AGREGAT(kolom) dengan AGREGAT salah satu {', '.join(AGREGAT)}.")
    agg, kolom = cocok.group(1).upper(), _kolom_sah(t, cocok.group(2))
    return {"expressionType": "SIMPLE", "column": {"column_name": kolom},
            "aggregate": agg, "label": f"{agg}({kolom})"}


def label_metrik(m: Any) -> str:
    return m if isinstance(m, str) else m["label"]


def _filter_bersih(t, filters: list[dict] | None) -> list[dict]:
    hasil = []
    for f in filters or []:
        op = str(f.get("op", "==")).upper()
        if op not in OPERATOR:
            raise InputSalah(f"Operator '{op}' tidak diizinkan.")
        val = f.get("nilai", f.get("val"))
        if op in ("IN", "NOT IN") and not isinstance(val, list):
            val = [val]
        hasil.append({"col": _kolom_sah(t, f.get("kolom", f.get("col"))), "op": op, "val": val})
    return hasil


# --- Query ----------------------------------------------------------------------
def jalankan_query(dataset_id: int, metrik: list[str] | None = None,
                   kelompok: list[str] | None = None, filter: list[dict] | None = None,
                   urut_turun: bool = True, batas: int = 100) -> dict:
    """Ambil data teragregasi (atau baris mentah bila tanpa metrik) - RLS berlaku."""
    t = _dataset(dataset_id)
    metrics = [metrik_obj(t, m) for m in (metrik or [])]
    columns = [_kolom_sah(t, k) for k in (kelompok or [])]
    if not metrics and not columns:
        columns = [c.column_name for c in t.columns]
    orderby = [[metrics[0], not urut_turun]] if metrics else []
    return jalankan_objek(t, metrics, columns, _filter_bersih(t, filter), orderby, batas)


def jalankan_objek(t, metrics: list, columns: list, filters: list[dict], orderby: list,
                   batas: int) -> dict:
    """Inti eksekusi (dipakai Asisten AI & Studio): ChartDataCommand sebagai user -> RLS berlaku."""
    from superset.commands.chart.data.get_data_command import ChartDataCommand
    from superset.common.query_context_factory import QueryContextFactory

    query = {"columns": columns, "metrics": metrics, "filters": filters,
             "row_limit": max(1, min(int(batas), 10000)), "orderby": orderby}
    ctx = QueryContextFactory().create(
        datasource={"id": t.id, "type": "table"}, queries=[query],
        form_data={"datasource": f"{t.id}__table", "viz_type": "table"})
    command = ChartDataCommand(ctx)
    command.validate()                         # cek akses -> SupersetSecurityException
    hasil = command.run()["queries"][0]
    baris = [{k: _iso(v) for k, v in b.items()} for b in hasil.get("data") or []]
    return {"dataset": t.table_name, "kolom": hasil.get("colnames") or [], "baris": baris, "sql_dipotong": False}


def _iso(v):
    """Tanggal -> teks ISO. Tanpa ini kolom Date/Date32 (mis. ClickHouse) dikirim Flask sebagai
    "Sat, 01 Mar 2025 00:00:00 GMT": label sumbu jadi panjang dan urutan periode bisa salah."""
    from datetime import date, datetime
    if isinstance(v, datetime):
        return v.date().isoformat() if (v.hour, v.minute, v.second, v.microsecond) == (0, 0, 0, 0) else v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    return v


# --- Chart & dashboard ------------------------------------------------------------
def params_chart(jenis: str, metrics: list, kelompok: list[str], filters: list[dict]) -> tuple[str, dict]:
    """Bentuk params chart Superset dari spesifikasi sederhana."""
    if jenis not in JENIS_CHART:
        raise InputSalah(f"Jenis chart '{jenis}' tidak dikenal. Pilih: {', '.join(JENIS_CHART)}.")
    if not metrics:
        raise InputSalah("Chart butuh minimal satu metrik.")
    viz = JENIS_CHART[jenis]
    adhoc = [{"expressionType": "SIMPLE", "clause": "WHERE", "subject": f["col"],
              "operator": f["op"], "comparator": f["val"]} for f in filters]
    p: dict[str, Any] = {"viz_type": viz, "adhoc_filters": adhoc, "row_limit": 1000}
    if jenis == "angka":
        p.update(metric=metrics[0], y_axis_format="SMART_NUMBER")
    elif jenis == "pie":
        if not kelompok:
            raise InputSalah("Pie butuh satu kolom kelompok.")
        p.update(metric=metrics[0], groupby=kelompok[:1], donut=True, show_labels=True,
                 label_type="key_percent", number_format="SMART_NUMBER", sort_by_metric=True,
                 legendOrientation="right", row_limit=12)
    elif jenis in ("batang", "garis"):
        if not kelompok:
            raise InputSalah("Grafik batang/garis butuh kolom sumbu X.")
        p.update(x_axis=kelompok[0], xAxisForceCategorical=True, metrics=metrics,
                 groupby=kelompok[1:2], x_axis_sort_asc=(jenis == "garis"),
                 y_axis_format="SMART_NUMBER", show_value=(jenis == "batang"),
                 show_legend=len(kelompok) > 1, truncateXAxis=True)
        if jenis == "batang":
            p["orientation"] = "vertical"
    else:  # tabel
        p.update(query_mode="aggregate", groupby=kelompok, metrics=metrics,
                 order_desc=True, show_cell_bars=True, server_page_length=25)
    return viz, p


def explore_url(dataset_id: int, params: dict) -> str:
    fd = {**params, "datasource": f"{dataset_id}__table"}
    return f"/explore/?form_data={quote(json.dumps(fd))}"


def buat_chart(dataset_id: int, jenis: str, judul: str, metrik: list[str],
               kelompok: list[str] | None = None, filter: list[dict] | None = None,
               simpan: bool = True) -> dict:
    """Buat chart. Tanpa izin tulis -> kembalikan tautan Explore (belum disimpan)."""
    from superset import security_manager
    from superset.commands.chart.create import CreateChartCommand

    t = _dataset(dataset_id)
    metrics = [metrik_obj(t, m) for m in metrik]
    kolom = [_kolom_sah(t, k) for k in (kelompok or [])]
    viz, params = params_chart(jenis, metrics, kolom, _filter_bersih(t, filter))
    judul = (judul or f"{jenis.title()} {t.table_name}")[:250]
    url_explore = explore_url(t.id, params)

    if not simpan or not security_manager.can_access("can_write", "Chart"):
        return {"judul": judul, "disimpan": False, "url": url_explore,
                "catatan": "Belum disimpan (butuh izin membuat chart). Buka tautan untuk melihat/menyimpan."}
    chart = CreateChartCommand({
        "slice_name": judul, "viz_type": viz, "params": json.dumps(params),
        "datasource_id": t.id, "datasource_type": "table",
    }).run()
    return {"id": chart.id, "judul": judul, "disimpan": True, "jenis": jenis,
            "url": f"/explore/?slice_id={chart.id}"}


def buat_dashboard(judul: str, chart_ids: list[int], keterangan: str = "") -> dict:
    """Susun chart milik user menjadi dashboard baru (belum dipublikasikan)."""
    from superset import db, security_manager
    from superset.commands.dashboard.create import CreateDashboardCommand
    from superset.models.slice import Slice

    if not security_manager.can_access("can_write", "Dashboard"):
        raise IzinDitolak("Anda tidak punya izin membuat dashboard (butuh role Alpha/Admin).")
    charts = [c for c in db.session.query(Slice).filter(Slice.id.in_(chart_ids))
              if security_manager.can_access_chart(c)]
    if not charts:
        raise InputSalah("Tidak ada chart yang bisa dimasukkan ke dashboard.")

    dash = CreateDashboardCommand({
        "dashboard_title": (judul or "Dashboard Otomatis")[:500],
        "position_json": json.dumps(_posisi(judul, charts, keterangan)),
        "json_metadata": json.dumps({"cross_filters_enabled": True}),
        "published": False,
    }).run()
    dash.slices = charts
    db.session.commit()
    return {"id": dash.id, "judul": dash.dashboard_title, "url": f"/superset/dashboard/{dash.id}/"}


def _posisi(judul: str, charts: list, keterangan: str) -> dict:
    """Tata letak: angka 4 per baris (lebar 3), chart lain 2 per baris (lebar 6)."""
    pos: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": judul}},
    }
    baris: list[list] = []
    angka = [c for c in charts if c.viz_type == "big_number_total"]
    lain = [c for c in charts if c.viz_type != "big_number_total"]
    baris += [[(c, 3, 25) for c in angka[i:i + 4]] for i in range(0, len(angka), 4)]
    baris += [[(c, 6, 50) for c in lain[i:i + 2]] for i in range(0, len(lain), 2)]
    if keterangan:
        baris.insert(0, [("md", 12, 10)])
    for n, isi in enumerate(baris, 1):
        rid = f"ROW-{n}"
        pos["GRID_ID"]["children"].append(rid)
        pos[rid] = {"type": "ROW", "id": rid, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        for item, lebar, tinggi in isi:
            if item == "md":
                iid = f"MARKDOWN-{n}"
                pos[iid] = {"type": "MARKDOWN", "id": iid, "children": [],
                            "parents": ["ROOT_ID", "GRID_ID", rid],
                            "meta": {"width": 12, "height": tinggi, "code": keterangan}}
            else:
                iid = f"CHART-{item.id}"
                pos[iid] = {"type": "CHART", "id": iid, "children": [],
                            "parents": ["ROOT_ID", "GRID_ID", rid],
                            "meta": {"width": lebar, "height": tinggi, "chartId": item.id,
                                     "uuid": str(item.uuid), "sliceName": item.slice_name}}
            pos[rid]["children"].append(iid)
    return pos


def daftar_dashboard(kata_kunci: str = "", hanya_siap: bool = False) -> list[dict]:
    """Dashboard yang boleh diakses user.

    hanya_siap=True (pilihan Story): hanya dashboard yang berisi chart DAN sudah dipublikasikan
    atau milik user sendiri; judul kembar diberi penanda agar bisa dibedakan.
    """
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    kata = (kata_kunci or "").lower().strip()
    uid = getattr(g.user, "id", None)
    hasil = []
    for d in db.session.query(Dashboard).order_by(Dashboard.dashboard_title, Dashboard.id):
        if kata and kata not in (d.dashboard_title or "").lower():
            continue
        if not security_manager.can_access_dashboard(d):
            continue
        milik = any(o.id == uid for o in d.owners)
        if hanya_siap and (not d.slices or not (d.published or milik)):
            continue
        hasil.append({"id": d.id, "judul": d.dashboard_title or f"Dashboard {d.id}",
                      "url": f"/superset/dashboard/{d.slug or d.id}/", "terbit": bool(d.published),
                      "chart": [s.slice_name for s in d.slices][:20]})
    if hanya_siap:
        hitung: dict[str, int] = {}
        for h in hasil:
            hitung[h["judul"]] = hitung.get(h["judul"], 0) + 1
        for h in hasil:
            label = [] if h["terbit"] else ["draf"]
            if hitung[h["judul"]] > 1:
                label.append(f"#{h['id']}, {len(h['chart'])} chart")
            if label:
                h["judul"] = f"{h['judul']} ({'; '.join(label)})"
    return hasil[:50]
