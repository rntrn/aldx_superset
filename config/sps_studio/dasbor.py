"""Penyusun dashboard: lembar kerja disusun per baris, lebar diatur per kotak.

Susunan dari browser:
    {"judul": "...", "keterangan": "...",
     "baris": [[{"chart_id": 12, "lebar": 6}, {"chart_id": 13, "lebar": 6}], [...]]}

lebar mengikuti grid Superset (12 kolom per baris): 3 = ¼, 4 = ⅓, 6 = ½, 8 = ⅔, 12 = penuh.
Filter dashboard -> native filter Superset:
    "filter": [{"nama": "Cabang", "dataset_id": 13, "kolom": "kd_cabang", "jenis": "pilihan|rentang"}]
Filter berlaku untuk semua chart yang dataset-nya punya kolom bernama sama (perilaku Superset).
Klik-filter antar-chart (cross filter, padanan "filter action") selalu diaktifkan.

Dashboard buatan Studio ditandai json_metadata.sps_studio = true agar bisa dibuka lagi.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sps_ai import alat

LEBAR_SAH = (3, 4, 6, 8, 12)
JENIS_FILTER = {"pilihan": "filter_select", "rentang": "filter_range"}
AWALAN_FILTER = "NATIVE_FILTER-sps"                # filter milik Studio (lainnya dibiarkan)
TINGGI = {"big_number_total": 26}            # kotak angka lebih pendek
TINGGI_BAWAAN = 52


def _chart(chart_id: int):
    from superset import db, security_manager
    from superset.models.slice import Slice

    c = db.session.query(Slice).get(int(chart_id))
    if c is None or not security_manager.can_access_chart(c):
        raise alat.IzinDitolak(f"Chart {chart_id} tidak ada atau tidak boleh Anda pakai.")
    return c


def posisi(judul: str, keterangan: str, baris: list[list[dict]]) -> tuple[dict, list]:
    """position_json Superset + daftar chart yang dipakai."""
    pos: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": judul}},
    }
    charts = []

    def baris_baru(n: int) -> str:
        rid = f"ROW-sps{n}"
        pos["GRID_ID"]["children"].append(rid)
        pos[rid] = {"type": "ROW", "id": rid, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        return rid

    if keterangan.strip():
        rid = baris_baru(0)
        pos["MARKDOWN-sps"] = {"type": "MARKDOWN", "id": "MARKDOWN-sps", "children": [],
                               "parents": ["ROOT_ID", "GRID_ID", rid],
                               "meta": {"width": 12, "height": 12, "code": keterangan}}
        pos[rid]["children"].append("MARKDOWN-sps")

    for n, isi in enumerate((b for b in baris if b), 1):
        if sum(int(k.get("lebar", 6)) for k in isi) > 12:
            raise alat.InputSalah(f"Baris {n}: total lebar lebih dari 12 (penuh).")
        rid = baris_baru(n)
        for k in isi:
            lebar = int(k.get("lebar", 6))
            if lebar not in LEBAR_SAH:
                raise alat.InputSalah(f"Lebar {lebar} tidak sah; pilih {LEBAR_SAH}.")
            c = _chart(k["chart_id"])
            cid = f"CHART-sps{c.id}"
            if cid in pos:
                raise alat.InputSalah(f"Chart '{c.slice_name}' dipakai dua kali.")
            pos[cid] = {"type": "CHART", "id": cid, "children": [], "parents": ["ROOT_ID", "GRID_ID", rid],
                        "meta": {"width": lebar, "height": TINGGI.get(c.viz_type, TINGGI_BAWAAN),
                                 "chartId": c.id, "uuid": str(c.uuid), "sliceName": c.slice_name}}
            pos[rid]["children"].append(cid)
            charts.append(c)
    if not charts:
        raise alat.InputSalah("Seret minimal satu lembar kerja ke kanvas dashboard.")
    return pos, charts


def filter_native(daftar: list[dict], chart_ids: list[int]) -> list[dict]:
    """Filter Studio -> native_filter_configuration Superset."""
    hasil, lihat = [], set()
    for f in daftar or []:
        t = alat._dataset(int(f.get("dataset_id") or 0))
        kolom = alat._kolom_sah(t, str(f.get("kolom", "")))
        jenis = str(f.get("jenis") or "pilihan")
        if jenis not in JENIS_FILTER:
            raise alat.InputSalah(f"Jenis filter '{jenis}' tidak dikenal.")
        fid = AWALAN_FILTER + hashlib.sha1(f"{t.id}:{kolom}".encode()).hexdigest()[:12]
        if fid in lihat:
            raise alat.InputSalah(f"Filter kolom '{kolom}' dipasang dua kali.")
        lihat.add(fid)
        hasil.append({
            "id": fid, "type": "NATIVE_FILTER", "filterType": JENIS_FILTER[jenis],
            "name": (str(f.get("nama") or "").strip() or kolom)[:100], "description": "",
            "targets": [{"datasetId": t.id, "column": {"name": kolom}}],
            "controlValues": {"enableEmptyFilter": False, "defaultToFirstItem": False, "multiSelect": True,
                              "searchAllOptions": False, "inverseSelection": False},
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [], "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "chartsInScope": chart_ids, "tabsInScope": [],
        })
    return hasil


def simpan(data: dict, dashboard_id: int | None = None) -> dict:
    from superset import db, security_manager
    from superset.commands.dashboard.create import CreateDashboardCommand
    from superset.models.dashboard import Dashboard

    if not security_manager.can_access("can_write", "Dashboard"):
        raise alat.IzinDitolak("Anda belum punya izin membuat dashboard.")
    judul = (str(data.get("judul") or "").strip() or "Dashboard Studio")[:500]
    pos, charts = posisi(judul, str(data.get("keterangan") or ""), data.get("baris") or [])
    filter_studio = filter_native(data.get("filter") or [], [c.id for c in charts])
    meta = {"sps_studio": True, "cross_filters_enabled": True, "color_scheme": "djpWarna"}

    if dashboard_id:
        dash = db.session.query(Dashboard).get(int(dashboard_id))
        if dash is None:
            raise alat.InputSalah("Dashboard tidak ditemukan.")
        security_manager.raise_for_ownership(dash)         # hanya pemilik / Admin
        lama = json.loads(dash.json_metadata or "{}")
        lain = [f for f in lama.get("native_filter_configuration") or []
                if not str(f.get("id", "")).startswith(AWALAN_FILTER)]     # filter buatan Superset tetap
        dash.dashboard_title, dash.position_json = judul, json.dumps(pos)
        dash.json_metadata = json.dumps({**lama, **meta, "native_filter_configuration": filter_studio + lain})
    else:
        dash = CreateDashboardCommand({"dashboard_title": judul, "position_json": json.dumps(pos),
                                       "json_metadata": json.dumps({**meta, "native_filter_configuration": filter_studio}),
                                       "published": False}).run()
    dash.slices = charts
    db.session.commit()
    return {"id": dash.id, "judul": dash.dashboard_title, "url": f"/superset/dashboard/{dash.id}/"}


def buka(dashboard_id: int) -> dict:
    """Susunan dashboard Studio -> bentuk yang dipahami kanvas browser."""
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    dash = db.session.query(Dashboard).get(int(dashboard_id))
    if dash is None or not security_manager.can_access_dashboard(dash):
        raise alat.IzinDitolak("Dashboard tidak ditemukan atau tidak boleh Anda buka.")
    pos = json.loads(dash.position_json or "{}")
    keterangan = next((v["meta"].get("code", "") for v in pos.values()
                       if isinstance(v, dict) and v.get("type") == "MARKDOWN"), "")
    baris = []
    for rid in pos.get("GRID_ID", {}).get("children", []):
        isi = [{"chart_id": pos[i]["meta"]["chartId"], "lebar": pos[i]["meta"]["width"],
                "judul": pos[i]["meta"].get("sliceName", "")}
               for i in pos.get(rid, {}).get("children", []) if pos.get(i, {}).get("type") == "CHART"]
        if isi:
            baris.append(isi)
    jenis = {v: k for k, v in JENIS_FILTER.items()}
    filter_ = [{"nama": f["name"], "dataset_id": f["targets"][0]["datasetId"],
                "kolom": f["targets"][0]["column"]["name"], "jenis": jenis.get(f["filterType"], "pilihan")}
               for f in json.loads(dash.json_metadata or "{}").get("native_filter_configuration") or []
               if str(f.get("id", "")).startswith(AWALAN_FILTER)]
    return {"id": dash.id, "judul": dash.dashboard_title, "keterangan": keterangan, "baris": baris,
            "filter": filter_}


def daftar() -> list[dict]:
    """Dashboard buatan Studio yang boleh dibuka user."""
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    rows = (db.session.query(Dashboard).filter(Dashboard.json_metadata.like('%"sps_studio": true%'))
            .order_by(Dashboard.changed_on.desc()).limit(100).all())
    return [{"id": d.id, "judul": d.dashboard_title, "url": f"/superset/dashboard/{d.id}/"}
            for d in rows if security_manager.can_access_dashboard(d)]
