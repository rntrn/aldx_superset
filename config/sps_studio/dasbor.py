"""Penyusun dashboard: lembar kerja disusun per baris, lebar diatur per kotak.

Susunan dari browser:
    {"judul": "...", "keterangan": "...",
     "baris": [[{"chart_id": 12, "lebar": 6}, {"chart_id": 13, "lebar": 6}], [...]]}

lebar mengikuti grid Superset (12 kolom per baris): 3 = ¼, 4 = ⅓, 6 = ½, 8 = ⅔, 12 = penuh.
tinggi (opsional, per chart) salah satu TINGGI_SAH; tanpa itu memakai tinggi bawaan jenis chart.
Tab (opsional): "tab": [{"judul": "Ringkasan", "baris": [...]}, {"judul": "Rincian", "baris": [...]}]
    menggantikan "baris"; satu tab saja = dashboard biasa tanpa tab.
Selain chart, kotak boleh berupa objek desain (teks/label, gambar, garis pemisah): lihat objek.py.
Filter dashboard -> native filter Superset:
    "filter": [{"nama": "Cabang", "dataset_id": 13, "kolom": "kd_cabang", "jenis": "pilihan|rentang|waktu"}]
"waktu" = rentang waktu (30 hari terakhir, tanggal tertentu, ...) untuk semua chart yang datasetnya punya kolom waktu.
Filter berlaku untuk semua chart yang dataset-nya punya kolom bernama sama (perilaku Superset).
Klik-filter antar-chart (cross filter, padanan "filter action") selalu diaktifkan.

Dashboard buatan Studio ditandai json_metadata.sps_studio = true agar bisa dibuka lagi.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sps_ai import alat
from sps_studio import lembar, objek

LEBAR_SAH = (3, 4, 6, 8, 12)
JENIS_FILTER = {"pilihan": "filter_select", "rentang": "filter_range", "waktu": "filter_time"}
AWALAN_FILTER = "NATIVE_FILTER-sps"                # filter milik Studio (lainnya dibiarkan)
TINGGI = {"big_number_total": 26}            # kotak angka lebih pendek
TINGGI_BAWAAN = 52
TINGGI_SAH = (26, 38, 52, 70, 90)            # pendek .. sangat tinggi (1 satuan = ±8 px)
TINGGI_MIN, TINGGI_MAKS = 8, 300             # tinggi bebas dari editor Superset yang diterima apa adanya
MAKS_TAB = 8


def _chart(chart_id: int):
    from superset import db, security_manager
    from superset.models.slice import Slice

    c = db.session.query(Slice).get(int(chart_id))
    if c is None or not security_manager.can_access_chart(c):
        raise alat.IzinDitolak(f"Chart {chart_id} tidak ada atau tidak boleh Anda pakai.")
    return c


def _tinggi(kotak: dict, viz: str) -> int:
    """Tinggi pilihan Studio, atau tinggi bebas yang diatur di editor Superset (dipertahankan apa adanya)."""
    try:
        t = int(kotak.get("tinggi") or 0)
    except (TypeError, ValueError):
        t = 0
    return t if TINGGI_MIN <= t <= TINGGI_MAKS else TINGGI.get(viz, TINGGI_BAWAAN)


def _lebar(kotak: dict) -> int:
    """Lebar 1-12 (grid Superset). Pilihan Studio ¼ ⅓ ½ ⅔ penuh; lebar lain dari editor Superset dipertahankan."""
    try:
        lebar = int(kotak.get("lebar", 6))
    except (TypeError, ValueError):
        lebar = 0
    if not 1 <= lebar <= 12:
        raise alat.InputSalah(f"Lebar {kotak.get('lebar')} tidak sah; pilih {LEBAR_SAH}.")
    return lebar


# --- Bagian yang tidak dikenal Studio: disalin UTUH dari dashboard lama ------------------------------------
# Komponen buatan editor Superset yang tidak bisa diwakili kanvas Studio (COLUMN berisi beberapa chart, markdown
# biasa, TABS bertingkat, header) tampil sebagai kotak "terkunci" {"jenis": "terkunci", "ref": id komponen}. Saat
# disimpan, komponen itu beserta seluruh isinya disalin dari position_json lama, jadi tidak ada yang hilang.
def _salin_subpohon(lama: dict, akar: str, jalur: list[str]) -> dict:
    hasil: dict[str, Any] = {}

    def jalan(cid: str, induk: list[str]) -> None:
        k = json.loads(json.dumps(lama[cid]))
        k["parents"] = list(induk)
        k["children"] = [a for a in k.get("children") or [] if a in lama]
        hasil[cid] = k
        for a in k["children"]:
            jalan(a, [*induk, cid])
    jalan(akar, jalur)
    return hasil


def _chart_di(komponen: dict) -> list[int]:
    return [int(k["meta"]["chartId"]) for k in komponen.values()
            if isinstance(k, dict) and k.get("type") == "CHART" and (k.get("meta") or {}).get("chartId")]


def _label_komponen(pos: dict, cid: str) -> str:
    k = pos.get(cid) or {}
    jenis = {"COLUMN": "Kolom", "MARKDOWN": "Teks/markdown", "TABS": "Tab bertingkat", "HEADER": "Judul",
             "ROW": "Baris", "CHART": "Chart"}.get(k.get("type"), k.get("type") or "Bagian")
    n = len(_chart_di(_salin_subpohon(pos, cid, []))) if cid in pos else 0
    return f"{jenis} dari editor lanjutan" + (f" ({n} chart)" if n else "")


def _bagian_grid(pos: dict) -> tuple[str | None, list[str]]:
    """(id TABS yang ditampilkan Studio, komponen tingkat GRID yang TIDAK ditampilkan tetapi wajib dipertahankan).

    Dengan tab: hanya TABS pertama yang diedit di Studio; baris lain di luar tab dipertahankan apa adanya."""
    anak = pos.get("GRID_ID", {}).get("children", [])
    wadah_tab = next((i for i in anak if pos.get(i, {}).get("type") == "TABS"), None)
    if not wadah_tab:
        return None, []
    luar = [i for i in anak if i != wadah_tab and i in pos and "MARKDOWN-sps" not in pos[i].get("children", [])]
    return wadah_tab, luar


def posisi(judul: str, keterangan: str, baris: list[list[dict]], tab: list[dict] | None = None,
           lama: dict | None = None) -> tuple[dict, list, dict]:
    """position_json Superset + daftar chart yang dipakai + objek desain {id komponen: pengaturan}.

    tab berisi >= 2 entri -> komponen TABS Superset (GRID > TABS > TAB > ROW); selain itu baris langsung di GRID.
    lama = position_json dashboard yang sedang diedit: sumber kotak "terkunci" & bagian di luar tab (disalin utuh)."""
    pos: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": judul}},
    }
    charts, objek_, terkunci = [], {}, []           # terkunci = id chart di dalam bagian terkunci
    jalur = ["ROOT_ID", "GRID_ID"]                 # leluhur wadah yang sedang diisi (GRID, atau TAB aktif)

    def baris_baru(n: int) -> str:
        rid = f"ROW-sps{n}"
        pos[jalur[-1]]["children"].append(rid)
        pos[rid] = {"type": "ROW", "id": rid, "children": [], "parents": list(jalur),
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        return rid

    if keterangan.strip():
        rid = baris_baru(0)
        pos["MARKDOWN-sps"] = {"type": "MARKDOWN", "id": "MARKDOWN-sps", "children": [],
                               "parents": ["ROOT_ID", "GRID_ID", rid],
                               "meta": {"width": 12, "height": 12, "code": keterangan}}
        pos[rid]["children"].append("MARKDOWN-sps")

    tab = [t for t in (tab or []) if isinstance(t, dict)][:MAKS_TAB]
    if len(tab) > 1:
        pos["TABS-sps"] = {"type": "TABS", "id": "TABS-sps", "children": [], "parents": ["ROOT_ID", "GRID_ID"], "meta": {}}
        pos["GRID_ID"]["children"].append("TABS-sps")
        bagian = []
        for i, t in enumerate(tab, 1):
            tid = f"TAB-sps{i}"
            nama = (str(t.get("judul") or "").strip() or f"Tab {i}")[:60]
            pos[tid] = {"type": "TAB", "id": tid, "children": [], "parents": ["ROOT_ID", "GRID_ID", "TABS-sps"],
                        "meta": {"text": nama, "defaultText": nama, "placeholder": "Tab"}}
            pos["TABS-sps"]["children"].append(tid)
            bagian.append((["ROOT_ID", "GRID_ID", "TABS-sps", tid], t.get("baris") or []))
    else:
        bagian = [(["ROOT_ID", "GRID_ID"], (tab[0].get("baris") if tab else baris) or [])]

    urut = [(j, isi) for j, daftar in bagian for isi in daftar if isi]
    for n, (jalur_baris, isi) in enumerate(urut, 1):
        jalur[:] = jalur_baris
        if isi[0].get("jenis") == "garis":                 # garis pemisah = satu baris tersendiri
            did = f"DIVIDER-sps{n}"
            pos[jalur[-1]]["children"].append(did)
            pos[did] = {"type": "DIVIDER", "id": did, "children": [], "parents": list(jalur)}
            continue
        if sum(_lebar(k) for k in isi) > 12:
            raise alat.InputSalah(f"Baris {n}: total lebar lebih dari 12 (penuh).")
        rid = baris_baru(n)
        for m, k in enumerate(isi):
            lebar = _lebar(k)
            if k.get("jenis") == "terkunci":               # bagian editor lanjutan: salin utuh dari dashboard lama
                ref = str(k.get("ref") or "")
                if not lama or ref not in lama:
                    raise alat.InputSalah("Bagian terkunci sudah tidak ada di dashboard (diubah di tempat lain?). "
                                          "Buka ulang dashboard ini di Studio.")
                sub = _salin_subpohon(lama, ref, [*jalur, rid])
                if isinstance(sub[ref].get("meta"), dict) and "width" in sub[ref]["meta"]:
                    sub[ref]["meta"]["width"] = lebar
                pos.update(sub)
                pos[rid]["children"].append(ref)
                terkunci.extend(_chart_di(sub))
                continue
            if k.get("jenis") in ("teks", "gambar"):
                o = objek.bersihkan({**k, "lebar": lebar})
                mid = f"MARKDOWN-spsobj{n}x{m}"
                pos[mid] = {"type": "MARKDOWN", "id": mid, "children": [], "parents": [*jalur, rid],
                            "meta": {"width": lebar, "height": o["tinggi"], "code": objek.html_objek(o)}}
                pos[rid]["children"].append(mid)
                objek_[mid] = o
                continue
            c = _chart(k["chart_id"])
            cid = f"CHART-sps{c.id}"
            if cid in pos:
                raise alat.InputSalah(f"Chart '{c.slice_name}' dipakai dua kali.")
            # meta komponen lama (mis. judul pengganti sliceNameOverride dari editor Superset) ikut dibawa
            asal = (lama or {}).get(str(k.get("ref") or ""), {})
            meta_lama = asal.get("meta", {}) if asal.get("type") == "CHART" and asal.get("meta", {}).get("chartId") == c.id else {}
            pos[cid] = {"type": "CHART", "id": cid, "children": [], "parents": [*jalur, rid],
                        "meta": {**meta_lama, "width": lebar, "height": _tinggi(k, c.viz_type),
                                 "chartId": c.id, "uuid": str(c.uuid), "sliceName": c.slice_name}}
            pos[rid]["children"].append(cid)
            charts.append(c)
    ganda = {c.id for c in charts} & set(terkunci)
    if ganda:
        raise alat.InputSalah(f"Chart {sorted(ganda)} sudah ada di bagian terkunci; hapus salah satunya.")
    if not charts and not objek_ and not terkunci:
        raise alat.InputSalah("Seret minimal satu lembar kerja atau objek ke kanvas dashboard.")
    from superset import db
    from superset.models.slice import Slice
    charts += db.session.query(Slice).filter(Slice.id.in_(terkunci or [0])).all()   # chart di bagian terkunci tetap ikut
    return pos, charts, objek_


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
        waktu = jenis == "waktu"
        hasil.append({
            "id": fid, "type": "NATIVE_FILTER", "filterType": JENIS_FILTER[jenis],
            "name": (str(f.get("nama") or "").strip() or ("Rentang waktu" if waktu else kolom))[:100], "description": "",
            # filter waktu Superset tidak menunjuk kolom; datasetId/kolom disimpan agar bisa dibuka lagi di Studio
            "targets": [{}] if waktu else [{"datasetId": t.id, "column": {"name": kolom}}],
            "sps_asal": {"dataset_id": t.id, "kolom": kolom},
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
    dash = None
    pos_lama: dict = {}
    if dashboard_id:
        dash = db.session.query(Dashboard).get(int(dashboard_id))
        if dash is None:
            raise alat.InputSalah("Dashboard tidak ditemukan.")
        security_manager.raise_for_ownership(dash)         # hanya pemilik / Admin
        pos_lama = json.loads(dash.position_json or "{}")
    pos, charts, objek_ = posisi(judul, str(data.get("keterangan") or ""), data.get("baris") or [], data.get("tab"),
                                 lama=pos_lama)
    # Bagian di luar tab yang tidak ditampilkan Studio: dipertahankan di tempat semula (sebelum/sesudah tab).
    wadah_tab, luar = _bagian_grid(pos_lama)
    if luar:
        anak_lama = pos_lama["GRID_ID"]["children"]
        sebelum = [i for i in luar if anak_lama.index(i) < anak_lama.index(wadah_tab)]
        for i in luar:
            pos.update(_salin_subpohon(pos_lama, i, ["ROOT_ID", "GRID_ID"]))
        g = pos["GRID_ID"]["children"]
        pos["GRID_ID"]["children"] = sebelum + g + [i for i in luar if i not in sebelum]
        dipakai = {c.id for c in charts}
        from superset.models.slice import Slice
        tambah = [i for i in _chart_di({k: pos[k] for k in pos if isinstance(pos[k], dict)}) if i not in dipakai]
        charts += db.session.query(Slice).filter(Slice.id.in_(tambah or [0])).all()
    filter_studio = filter_native(data.get("filter") or [], [c.id for c in charts])
    huruf = {o["huruf"] for o in objek_.values() if o["jenis"] == "teks"}

    if dash is not None:
        lama = json.loads(dash.json_metadata or "{}")
        lain = [f for f in lama.get("native_filter_configuration") or []
                if not str(f.get("id", "")).startswith(AWALAN_FILTER)]     # filter buatan Superset tetap
        # Pengaturan dari editor Superset (skema warna, klik-filter) TIDAK ditimpa; hanya diisi bila belum ada.
        meta = {**lama, "sps_studio": True, "sps_objek": objek_, "native_filter_configuration": filter_studio + lain}
        meta.setdefault("cross_filters_enabled", True)
        meta.setdefault("color_scheme", lembar.SKEMA_WARNA)
        dash.dashboard_title, dash.position_json = judul, json.dumps(pos)
        dash.css = objek.gabung_css(dash.css, huruf, bool(objek_))
    else:
        meta = {"sps_studio": True, "cross_filters_enabled": True, "color_scheme": lembar.SKEMA_WARNA,
                "sps_objek": objek_, "native_filter_configuration": filter_studio}
        dash = CreateDashboardCommand({"dashboard_title": judul, "position_json": json.dumps(pos),
                                       "css": objek.gabung_css("", huruf, bool(objek_)),
                                       "json_metadata": json.dumps(meta), "published": False}).run()
    dash.slices = charts
    # Cakupan SEMUA filter berlingkup dashboard dihitung ulang: chart yang baru ditambahkan ikut terfilter, chart
    # yang datasetnya tidak punya kolom filter dikecualikan (sama dengan Asisten AI, sps_ai/rencana.py).
    from sps_ai.rencana import _lingkup_ulang
    _lingkup_ulang(dash, meta)
    dash.json_metadata = json.dumps(meta)
    db.session.commit()
    return {"id": dash.id, "judul": dash.dashboard_title, "url": f"/superset/dashboard/{dash.id}/"}


def buka(dashboard_id: int) -> dict:
    """Dashboard (buatan Studio, editor Superset, Asisten AI, impor) -> bentuk yang dipahami kanvas browser.

    Yang bisa diwakili kanvas: baris berisi chart / objek Studio / garis. Selain itu (COLUMN, markdown biasa, TABS
    bertingkat, ...) -> kotak terkunci {"jenis": "terkunci", "ref", "lebar", "judul"} yang disalin utuh saat disimpan."""
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    dash = db.session.query(Dashboard).get(int(dashboard_id))
    if dash is None or not security_manager.can_access_dashboard(dash):
        raise alat.IzinDitolak("Dashboard tidak ditemukan atau tidak boleh Anda buka.")
    pos = json.loads(dash.position_json or "{}")
    meta_dash = json.loads(dash.json_metadata or "{}")
    simpanan = meta_dash.get("sps_objek") or {}
    keterangan = (pos.get("MARKDOWN-sps") or {}).get("meta", {}).get("code", "")

    def terkunci(cid: str, lebar: int | None = None) -> dict:
        k = pos.get(cid, {})
        return {"jenis": "terkunci", "ref": cid, "lebar": int(lebar or (k.get("meta") or {}).get("width") or 12),
                "judul": _label_komponen(pos, cid)}

    def baris_dari(wadah: str) -> list:
        hasil = []
        for rid in pos.get(wadah, {}).get("children", []):
            r = pos.get(rid, {})
            if r.get("type") == "DIVIDER":
                hasil.append([{"jenis": "garis"}])
                continue
            if r.get("type") != "ROW":                     # mis. TABS bertingkat langsung di dalam tab
                hasil.append([terkunci(rid, 12)])
                continue
            isi = []
            for i in r.get("children", []):
                k = pos.get(i, {})
                m = k.get("meta") or {}
                if i == "MARKDOWN-sps":                     # keterangan dashboard: kolom Keterangan
                    continue
                if k.get("type") == "CHART" and m.get("chartId"):
                    isi.append({"chart_id": m["chartId"], "lebar": m.get("width", 4), "judul": m.get("sliceName", ""),
                                "ref": i, **({"tinggi": m["height"]} if m.get("height") else {})})
                elif k.get("type") == "MARKDOWN" and i in simpanan:   # ukuran bisa diubah di Superset: ambil terbaru
                    isi.append({**simpanan[i], "lebar": m.get("width", 12), "tinggi": m.get("height", 10)})
                else:
                    isi.append(terkunci(i))
            if isi:
                hasil.append(isi)
        return hasil

    wadah_tab, luar = _bagian_grid(pos)
    tab = [{"judul": pos[t]["meta"].get("text", ""), "baris": baris_dari(t)}
           for t in pos[wadah_tab]["children"] if t in pos] if wadah_tab else []
    baris = [b for t in tab for b in t["baris"]] if tab else baris_dari("GRID_ID")
    jenis = {v: k for k, v in JENIS_FILTER.items()}
    semua_filter = meta_dash.get("native_filter_configuration") or []
    filter_ = [{"nama": f["name"],
                "dataset_id": (f.get("sps_asal") or {}).get("dataset_id") or f["targets"][0].get("datasetId"),
                "kolom": (f.get("sps_asal") or {}).get("kolom") or (f["targets"][0].get("column") or {}).get("name"),
                "jenis": jenis.get(f["filterType"], "pilihan")}
               for f in semua_filter if str(f.get("id", "")).startswith(AWALAN_FILTER)]
    filter_lain = [f.get("name") or "" for f in semua_filter if not str(f.get("id", "")).startswith(AWALAN_FILTER)]
    catatan = []
    if luar:
        catatan.append(f"{len(luar)} bagian di luar tab ({', '.join(_label_komponen(pos, i) for i in luar[:3])}) tidak "
                       "ditampilkan di Studio, tetapi tetap dipertahankan saat disimpan.")
    return {"id": dash.id, "judul": dash.dashboard_title, "keterangan": keterangan, "baris": baris,
            "tab": tab, "filter": filter_, "filter_lain": filter_lain, "catatan": catatan}


def daftar() -> list[dict]:
    """SEMUA dashboard yang boleh DIUBAH user (pemilik / Admin): buatan Studio, editor Superset, Asisten AI, impor."""
    from superset import db, security_manager
    from superset.exceptions import SupersetSecurityException
    from superset.models.dashboard import Dashboard

    hasil = []
    for d in db.session.query(Dashboard).order_by(Dashboard.changed_on.desc()).limit(300):
        if not security_manager.can_access_dashboard(d):
            continue
        try:
            security_manager.raise_for_ownership(d)
        except SupersetSecurityException:
            continue
        hasil.append({"id": d.id, "judul": d.dashboard_title, "url": f"/superset/dashboard/{d.id}/",
                      "studio": '"sps_studio": true' in (d.json_metadata or "")})
        if len(hasil) >= 150:
            break
    return hasil
