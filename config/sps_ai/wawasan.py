"""Pengetahuan Asisten AI tentang isi aplikasi & halaman yang sedang dibuka.

1. PETA PENGETAHUAN (ringkasan_katalog): dataset (+ kolom & metrik utama), dashboard (+ chart di dalamnya),
   dan chart (+ jenis & dataset) yang BOLEH diakses pengguna. Disisipkan ke instruksi sistem, jadi
   pertanyaan dari Beranda pun langsung dipahami ("penjualan cabang Jakarta" -> dataset yang tepat).
   Dibatasi ukurannya & disimpan 2 menit per pengguna.
2. HALAMAN AKTIF (konteks_halaman): alamat dibaca -> dashboard / chart / dataset yang sedang dibuka
   dijelaskan rinci (chart, metrik, pengelompokan, filter). Teks yang tampil di layar dikirim panel
   dan hanya diteruskan ke model bila model boleh menerima data (kirim_data: true).
3. ALAT info_dashboard, info_chart, data_chart: membaca isi dashboard/chart tertentu, data chart
   dijalankan ulang sebagai pengguna (RLS berlaku).
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from urllib.parse import parse_qs, unquote, urlparse

log = logging.getLogger(__name__)

UMUR_DETIK = 120
# Ringkas: model lokal kecil di CPU melambat tajam bila instruksi panjang.
MAKS = {"dataset": 30, "dashboard": 20, "chart": 25, "kolom": 10, "data_chart_halaman": 8}
_tembolok: dict[int, tuple[float, str]] = {}
_kunci = threading.Lock()

JENIS = {"big_number_total": "angka", "big_number": "angka + tren", "table": "tabel", "pivot_table_v2": "tabel pivot",
         "pie": "pie", "echarts_timeseries_bar": "batang", "echarts_timeseries_line": "garis", "dist_bar": "batang",
         "echarts_area": "area", "echarts_timeseries_scatter": "sebar", "treemap_v2": "treemap", "sunburst_v2": "sunburst",
         "funnel": "corong", "gauge_chart": "gauge", "word_cloud": "awan kata", "heatmap_v2": "peta panas",
         "box_plot": "box plot", "sankey_v2": "sankey", "waterfall": "waterfall", "radar": "radar",
         "deck_scatter": "peta titik", "deck_heatmap": "peta kepadatan", "country_map": "peta wilayah"}


# --- Bantu ---------------------------------------------------------------------------------
def _label(m) -> str:
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        if m.get("label"):
            return str(m["label"])
        if m.get("expressionType") == "SQL":
            return str(m.get("sqlExpression") or "")[:60]
        kol = (m.get("column") or {}).get("column_name", "")
        return f"{m.get('aggregate', '')}({kol})"
    return str(m)


def _params(chart) -> dict:
    try:
        return json.loads(chart.params or "{}")
    except ValueError:
        return {}


def _kelompok(p: dict) -> list[str]:
    hasil = []
    for k in ("x_axis", "groupby", "columns", "groupbyRows", "groupbyColumns", "series", "entity"):
        v = p.get(k)
        for x in (v if isinstance(v, list) else [v] if v else []):
            n = x if isinstance(x, str) else (x.get("label") or x.get("sqlExpression") or "") if isinstance(x, dict) else ""
            if n and n not in hasil:
                hasil.append(n)
    return hasil


def _metrik(p: dict) -> list:
    m = p.get("metrics") or ([p["metric"]] if p.get("metric") else [])
    if p.get("metric_2"):
        m = [*m, p["metric_2"]]
    return m if isinstance(m, list) else [m]


def _filter_sederhana(p: dict) -> list[dict]:
    """adhoc_filters bertipe SIMPLE -> filter query; filter SQL dicatat sebagai teks."""
    hasil = []
    for f in p.get("adhoc_filters") or []:
        if f.get("expressionType") == "SIMPLE" and f.get("clause", "WHERE") == "WHERE" and f.get("subject"):
            op = {"==": "==", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<=", "IN": "IN",
                  "NOT IN": "NOT IN", "LIKE": "LIKE", "TEMPORAL_RANGE": None}.get(str(f.get("operator", "")).upper())
            if op:
                hasil.append({"col": f["subject"], "op": op, "val": f.get("comparator")})
    return hasil


def _boleh_chart(chart) -> bool:
    from superset import security_manager
    try:
        return bool(chart.datasource) and security_manager.can_access_datasource(chart.datasource)
    except Exception:  # noqa: BLE001
        return False


def _ringkas_chart(c) -> dict:
    p = _params(c)
    return {"id": c.id, "nama": c.slice_name, "jenis": JENIS.get(c.viz_type, c.viz_type),
            "dataset_id": c.datasource_id, "dataset": getattr(c.datasource, "table_name", ""),
            "metrik": [_label(m) for m in _metrik(p)][:6], "kelompok": _kelompok(p)[:6],
            "filter": [f"{f['col']} {f['op']} {f['val']}" for f in _filter_sederhana(p)][:6]}


# --- 1. Peta pengetahuan ----------------------------------------------------------------------
def ringkasan_katalog(user_id: int | None) -> str:
    """Teks ringkas isi aplikasi yang boleh diakses pengguna (untuk instruksi sistem)."""
    sekarang = time.monotonic()
    with _kunci:
        if user_id in _tembolok and sekarang - _tembolok[user_id][0] < UMUR_DETIK:
            return _tembolok[user_id][1]
    try:
        teks = _susun_katalog()
    except Exception:  # noqa: BLE001 - asisten tetap jalan tanpa peta
        log.exception("ALDx AI: peta pengetahuan gagal disusun")
        teks = ""
    with _kunci:
        _tembolok[user_id] = (sekarang, teks)
    return teks


def _susun_katalog() -> str:
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    baris = []
    ds = [t for t in db.session.query(SqlaTable).order_by(SqlaTable.changed_on.desc()).limit(300)
          if security_manager.can_access_datasource(t)][:MAKS["dataset"]]
    if ds:
        baris.append("DATASET (id · nama · kolom · metrik tersimpan):")
        for t in ds:
            kol = [c.column_name for c in t.columns if c.is_active is not False]
            sisa = f" +{len(kol) - MAKS['kolom']}" if len(kol) > MAKS["kolom"] else ""
            met = [m.metric_name for m in t.metrics if m.metric_name != "count"][:6]
            ket = f" — {t.description[:40]}" if t.description and not t.description.startswith("Impor dari") else ""
            baris.append(f"- [{t.id}] {t.table_name}{ket} · kolom: {', '.join(kol[:MAKS['kolom']])}{sisa}"
                         + (f" · metrik: {', '.join(met)}" if met else ""))
    dash = [d for d in db.session.query(Dashboard).order_by(Dashboard.changed_on.desc()).limit(200)
            if security_manager.can_access_dashboard(d)][:MAKS["dashboard"]]
    if dash:
        baris.append("DASHBOARD (id · judul · chart di dalamnya):")
        for d in dash:
            ch = [s.slice_name for s in d.slices][:12]
            baris.append(f"- [{d.id}] {d.dashboard_title}{'' if d.published else ' (draf)'} · {', '.join(ch) or 'kosong'}")
    di_dashboard = {s.id for d in dash for s in d.slices}
    charts = [c for c in db.session.query(Slice).order_by(Slice.changed_on.desc()).limit(400)
              if c.id not in di_dashboard and _boleh_chart(c)][:MAKS["chart"]]
    if charts:
        baris.append("CHART LAIN di luar dashboard di atas (id · nama · jenis · dataset id):")
        for c in charts:
            baris.append(f"- [{c.id}] {c.slice_name} · {JENIS.get(c.viz_type, c.viz_type)} · dataset {c.datasource_id}")
    return "\n".join(baris)


def lupakan(user_id: int | None = None) -> None:
    with _kunci:
        if user_id is None:
            _tembolok.clear()
        else:
            _tembolok.pop(user_id, None)


# --- 2. Halaman aktif ----------------------------------------------------------------------------
def _cari_dashboard(kunci: str):
    from superset import db
    from superset.models.dashboard import Dashboard
    q = db.session.query(Dashboard)
    return q.get(int(kunci)) if kunci.isdigit() else q.filter(Dashboard.slug == kunci).one_or_none()


def info_dashboard(kunci) -> dict:
    from superset import security_manager
    d = _cari_dashboard(str(kunci))
    if d is None or not security_manager.can_access_dashboard(d):
        raise LookupError("Dashboard tidak ditemukan atau tidak boleh Anda akses.")
    meta = {}
    try:
        meta = json.loads(d.json_metadata or "{}")
    except ValueError:
        pass
    filter_dash = [f.get("name") for f in meta.get("native_filter_configuration") or [] if f.get("name")]
    return {"id": d.id, "judul": d.dashboard_title, "terbit": bool(d.published), "keterangan": d.description or "",
            "filter_dashboard": filter_dash[:12],
            "chart": [_ringkas_chart(c) for c in d.slices if _boleh_chart(c)][:25]}


def info_chart(chart_id: int) -> dict:
    from superset import db
    from superset.models.slice import Slice
    c = db.session.query(Slice).get(int(chart_id))
    if c is None or not _boleh_chart(c):
        raise LookupError("Chart tidak ditemukan atau tidak boleh Anda akses.")
    return {**_ringkas_chart(c), "keterangan": c.description or "",
            "dashboard": [d.dashboard_title for d in c.dashboards][:8]}


def data_chart(chart_id: int, batas: int = 200) -> dict:
    """Jalankan ulang query chart (metrik, pengelompokan, filter sederhana) sebagai pengguna -> RLS berlaku."""
    from superset import db
    from superset.models.slice import Slice
    from sps_ai import alat
    c = db.session.query(Slice).get(int(chart_id))
    if c is None or not _boleh_chart(c):
        raise LookupError("Chart tidak ditemukan atau tidak boleh Anda akses.")
    p = _params(c)
    t = alat._dataset(c.datasource_id)
    metrics, kelompok = _metrik(p), _kelompok(p)
    kolom = [k for k in kelompok if k in {x.column_name for x in t.columns}]
    if not metrics and not kolom:
        # Chart peta (deck_*): kolom koordinat ada di "spatial"; tabel mentah: "all_columns".
        sp = p.get("spatial") if isinstance(p.get("spatial"), dict) else {}
        calon = [sp.get(k) for k in ("lonCol", "latCol", "lonlatCol", "geohashCol", "delimitedColumn")]
        calon += [x for x in (p.get("all_columns") or []) if isinstance(x, str)]
        ada = {x.column_name for x in t.columns}
        kolom = list(dict.fromkeys(c for c in calon if c in ada))[:20]
    if not metrics and not kolom:
        raise LookupError(f"Chart '{c.slice_name}' tidak punya ukuran atau kolom yang bisa diambil.")
    orderby = [[metrics[0], False]] if metrics else []
    h = alat.jalankan_objek(t, metrics, kolom, _filter_sederhana(p), orderby, batas)
    return {"chart": c.slice_name, **h}


def _angka(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        a = abs(v)
        for batas, akhiran in ((1e12, " T"), (1e9, " M"), (1e6, " jt"), (1e3, " rb")):
            if a >= batas:
                return f"{v / batas:,.1f}{akhiran}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".") if isinstance(v, float) else f"{v:,}".replace(",", ".")
    return str(v)[:30]


def ringkas_data(h: dict, baris: int = 6) -> str:
    """Hasil query -> teks pendek: 'Elektronik: 208,8 M; Makanan: 175,8 M; ...'."""
    kol = h.get("kolom") or []
    hasil = []
    for r in (h.get("baris") or [])[:baris]:
        nilai = [_angka(r.get(k)) for k in kol]
        hasil.append(" / ".join(nilai) if len(kol) > 2 else (": ".join(nilai) if len(kol) == 2 else nilai[0] if nilai else ""))
    lebih = len(h.get("baris") or []) - baris
    return "; ".join(hasil) + (f"; … (+{lebih} baris)" if lebih > 0 else "")


def konteks_halaman(alamat: str, dengan_data: bool = False) -> str:
    """Jelaskan objek yang sedang dibuka (dashboard, chart, dataset, daftar) dari alamatnya.

    dengan_data=True (model boleh menerima data): angka tiap chart di dashboard/chart ikut disertakan,
    sehingga pertanyaan "jelaskan dashboard ini" terjawab tanpa memanggil alat berkali-kali.
    """
    if not alamat:
        return ""
    u = urlparse(alamat)
    jalur, q = u.path, parse_qs(u.query)
    try:
        m = re.match(r"^/superset/dashboard/([^/]+)/?$", jalur)
        if m:
            d = info_dashboard(unquote(m.group(1)))
            isi = []
            for i, c in enumerate(d["chart"]):
                teks = (f"  - chart [{c['id']}] {c['nama']} ({c['jenis']}, dataset {c['dataset_id']}): "
                        f"{', '.join(c['metrik']) or '-'} per {', '.join(c['kelompok']) or '(total)'}"
                        + (f"; filter {', '.join(c['filter'])}" if c["filter"] else ""))
                if dengan_data and i < MAKS["data_chart_halaman"]:
                    try:
                        teks += f"\n      angka: {ringkas_data(data_chart(c['id'], 30))}"
                    except Exception as exc:  # noqa: BLE001
                        log.info("ALDx AI: data chart %s untuk konteks gagal: %s", c["id"], exc)
                isi.append(teks)
            return (f"Halaman ini DASHBOARD [{d['id']}] \"{d['judul']}\""
                    + (f", filter dashboard: {', '.join(d['filter_dashboard'])}" if d["filter_dashboard"] else "")
                    + ". Isinya (angka = tanpa filter dashboard):\n" + "\n".join(isi)
                    + ("" if dengan_data else "\nUntuk angka, panggil data_chart dengan id chart di atas."))
        slice_id = (q.get("slice_id") or [None])[0]
        if not slice_id and q.get("form_data"):
            try:
                slice_id = json.loads(q["form_data"][0]).get("slice_id")
            except ValueError:
                pass
        if jalur.startswith("/explore") and slice_id:
            c = info_chart(int(slice_id))
            teks = (f"Halaman ini CHART [{c['id']}] \"{c['nama']}\" ({c['jenis']}) dari dataset [{c['dataset_id']}] "
                    f"{c['dataset']}: metrik {', '.join(c['metrik']) or '-'}; dikelompokkan {', '.join(c['kelompok']) or '-'}"
                    + (f"; filter {', '.join(c['filter'])}" if c["filter"] else ""))
            if dengan_data:
                try:
                    return teks + f".\nAngka: {ringkas_data(data_chart(c['id'], 50), 15)}"
                except Exception:  # noqa: BLE001
                    pass
            return teks + ". Untuk angka, panggil data_chart."
        ds = (q.get("datasource_id") or q.get("dataset_id") or [None])[0]
        m = re.match(r"^/tablemodelview/(?:edit|show)/(\d+)", jalur)
        ds = m.group(1) if m else ds
        if ds and str(ds).split("__")[0].isdigit():
            from sps_ai import alat
            t = alat.info_dataset(int(str(ds).split("__")[0]))
            return (f"Halaman ini memakai DATASET [{t['id']}] {t['nama']}: kolom "
                    f"{', '.join(k['nama'] for k in t['kolom'][:30])}.")
        daftar = {"/dashboard/list": "daftar dashboard", "/chart/list": "daftar chart",
                  "/tablemodelview/list": "daftar dataset", "/sqllab": "SQL Lab", "/kueri": "Kueri Visual",
                  "/studio": "Studio Visual", "/pusat-kendali": "Pusat Kendali", "/app": "Beranda"}
        for awal, nama in daftar.items():
            if jalur.startswith(awal):
                return f"Halaman ini {nama}."
    except LookupError as exc:
        return f"Halaman yang dibuka tidak bisa dibaca: {exc}"
    except Exception:  # noqa: BLE001
        log.exception("ALDx AI: konteks halaman gagal dibaca (%s)", alamat)
    return ""
