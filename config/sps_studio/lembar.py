"""Lembar kerja: rak Kolom/Baris/Filter + kartu Marks -> query & chart Superset.

Spesifikasi lembar kerja (JSON dari browser, juga disimpan di params chart "sps_studio"):

    {"dataset_id": 13, "judul": "Penjualan per Cabang", "tanda": "batang",
     "kolom": [pil], "baris": [pil], "warna": pil|null, "ukuran": pil|null,
     "label": true, "filter": [{"field": "tahun", "op": "IN", "nilai": [2025]}],
     "urut": "turun"|"naik"|"", "batas": 1000,
     "analitik": {"ramalan": 6, "tren": true, "anomali": true}}   panel Analitik (prediksi.py)

    pil = {"field": "total", "peran": "ukuran", "agg": "SUM"}      kolom angka teragregasi
          {"field": "penerimaan", "peran": "ukuran", "metrik": true} metrik tersimpan dataset
          {"field": "__baris__", "peran": "ukuran"}                  Jumlah baris (COUNT(*))
          {"field": "kd_cabang", "peran": "dimensi"}

Semua query lewat ChartDataCommand sebagai user yang login -> hak akses data (RLS) berlaku.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from sps_ai import alat

AGREGAT = ("SUM", "AVG", "COUNT", "COUNT_DISTINCT", "MIN", "MAX")
BARIS = "__baris__"
LABEL_BARIS = "Jumlah baris"
SKEMA_WARNA = "djpWarna"          # didaftarkan di superset_config (EXTRA_CATEGORICAL_COLOR_SCHEMES)
# Palet kategori DJP: lolos uji buta warna (dataviz validate_palette). Urutan TETAP, jangan diputar.
WARNA = ["#2a5bb8", "#e0a100", "#1baf7a", "#eb6834", "#6250d6", "#e87ba4", "#008300", "#e34948"]
SKEMA_RUNTUN = "djpBiru"           # satu hue terang -> gelap, untuk peta panas
RUNTUN = ["#EAF1FB", "#7FA3DE", "#2a5bb8", "#1F2F5F"]
TANDA_ANALITIK = ("garis", "area", "batang")   # ramalan/tren/anomali: satu dimensi berurutan

# Aturan "Tampilkan Saya": kebutuhan tiap jenis tanda. Dikirim apa adanya ke browser.
#   dim/ukuran : [min, maks] jumlah dimensi & ukuran
#   grup       : kelompok tombol di panel Tampilkan Saya
#   waktu      : butuh dimensi tanggal          geo: "titik" = butuh kolom lintang & bujur
ATURAN_TANDA: dict[str, dict[str, Any]] = {
    # Angka
    "angka":       {"label": "Angka besar", "grup": "Angka", "dim": [0, 0], "ukuran": [1, 1], "viz": "big_number_total"},
    "angka_tren":  {"label": "Angka + tren", "grup": "Angka", "dim": [1, 1], "ukuran": [1, 1], "viz": "big_number",
                    "waktu": True},
    "gauge":       {"label": "Gauge", "grup": "Angka", "dim": [0, 0], "ukuran": [1, 1], "viz": "gauge_chart"},
    # Tabel
    "tabel":       {"label": "Tabel", "grup": "Tabel", "dim": [0, 9], "ukuran": [0, 9], "viz": "table"},
    "tabel_pivot": {"label": "Tabel pivot", "grup": "Tabel", "dim": [2, 4], "ukuran": [1, 4], "viz": "pivot_table_v2"},
    "peta_panas":  {"label": "Peta panas", "grup": "Tabel", "dim": [2, 2], "ukuran": [1, 1], "viz": "heatmap_v2"},
    # Perbandingan & tren
    "batang":      {"label": "Batang", "grup": "Perbandingan", "dim": [1, 2], "ukuran": [1, 5],
                    "viz": "echarts_timeseries_bar"},
    "batang_100":  {"label": "Batang 100%", "grup": "Perbandingan", "dim": [2, 2], "ukuran": [1, 1],
                    "viz": "echarts_timeseries_bar"},
    "garis":       {"label": "Garis", "grup": "Perbandingan", "dim": [1, 2], "ukuran": [1, 5],
                    "viz": "echarts_timeseries_line"},
    "area":        {"label": "Area", "grup": "Perbandingan", "dim": [1, 2], "ukuran": [1, 3], "viz": "echarts_area"},
    "waterfall":   {"label": "Waterfall", "grup": "Perbandingan", "dim": [1, 1], "ukuran": [1, 1], "viz": "waterfall"},
    "radar":       {"label": "Radar", "grup": "Perbandingan", "dim": [1, 1], "ukuran": [3, 8], "viz": "radar"},
    # Komposisi
    "pie":         {"label": "Pie", "grup": "Komposisi", "dim": [1, 1], "ukuran": [1, 1], "viz": "pie"},
    "treemap":     {"label": "Treemap", "grup": "Komposisi", "dim": [1, 2], "ukuran": [1, 1], "viz": "treemap_v2"},
    "sunburst":    {"label": "Sunburst", "grup": "Komposisi", "dim": [2, 3], "ukuran": [1, 1], "viz": "sunburst_v2"},
    "funnel":      {"label": "Corong", "grup": "Komposisi", "dim": [1, 1], "ukuran": [1, 1], "viz": "funnel"},
    "awan_kata":   {"label": "Awan kata", "grup": "Komposisi", "dim": [1, 1], "ukuran": [1, 1], "viz": "word_cloud"},
    # Sebaran & alur
    "sebar":       {"label": "Sebar", "grup": "Sebaran", "dim": [1, 1], "ukuran": [2, 3], "viz": "bubble_v2"},
    "box_plot":    {"label": "Box plot", "grup": "Sebaran", "dim": [2, 2], "ukuran": [1, 1], "viz": "box_plot"},
    "sankey":      {"label": "Sankey", "grup": "Sebaran", "dim": [2, 2], "ukuran": [1, 1], "viz": "sankey_v2"},
    # Peta
    "peta_wilayah":   {"label": "Peta provinsi", "grup": "Peta", "dim": [1, 1], "ukuran": [1, 1],
                       "viz": "country_map"},
    "peta_titik":     {"label": "Peta titik", "grup": "Peta", "dim": [2, 3], "ukuran": [0, 1],
                       "viz": "deck_scatter", "geo": "titik"},
    "peta_kepadatan": {"label": "Peta kepadatan", "grup": "Peta", "dim": [2, 2], "ukuran": [0, 1],
                       "viz": "deck_hex", "geo": "titik"},
}

# Kolom geografis dikenali dari namanya (peran geografis).
POLA_LINTANG = re.compile(r"^(lat|latitude|lintang)(_|$)|_(lat|latitude|lintang)$", re.I)
POLA_BUJUR = re.compile(r"^(lon|lng|long|longitude|bujur)(_|$)|_(lon|lng|longitude|bujur)$", re.I)
POLA_WILAYAH = re.compile(r"(^|_)(prov|provinsi|propinsi|iso_prov|kd_prov|kode_prov)(_|$)", re.I)
# Pusat & zoom peta Indonesia (deck.gl Superset & pratinjau Studio).
VIEWPORT_INDONESIA = {"latitude": -2.5, "longitude": 118.0, "zoom": 3.6, "bearing": 0, "pitch": 0}


def peran_geo(nama: str) -> str:
    """'lintang' | 'bujur' | 'wilayah' | '' menurut nama kolom."""
    if POLA_LINTANG.search(nama):
        return "lintang"
    if POLA_BUJUR.search(nama):
        return "bujur"
    return "wilayah" if POLA_WILAYAH.search(nama) else ""


@dataclass(frozen=True)
class Pil:
    field: str
    peran: str
    agg: str = "SUM"
    metrik: bool = False

    @property
    def label(self) -> str:
        """Nama kolom hasil query (dipakai browser sebagai kunci data)."""
        if self.peran == "dimensi" or self.metrik:
            return self.field
        if self.field == BARIS:
            return LABEL_BARIS
        return f"{self.agg}({self.field})"


@dataclass
class Lembar:
    dataset_id: int
    tanda: str
    judul: str = ""
    kolom: list[Pil] = field(default_factory=list)
    baris: list[Pil] = field(default_factory=list)
    warna: Pil | None = None
    ukuran: Pil | None = None
    label: bool = False
    filter: list[dict] = field(default_factory=list)
    urut: str = ""
    batas: int = 1000
    analitik: dict = field(default_factory=dict)

    # --- Turunan --------------------------------------------------------------------
    @property
    def dimensi(self) -> list[Pil]:
        hasil = [p for p in self.kolom + self.baris if p.peran == "dimensi"]
        if self.warna and self.warna.peran == "dimensi":
            hasil.append(self.warna)
        return _unik(hasil)

    @property
    def ukuran_semua(self) -> list[Pil]:
        hasil = [p for p in self.kolom + self.baris if p.peran == "ukuran"]
        hasil += [p for p in (self.ukuran, self.warna) if p and p.peran == "ukuran"]
        return _unik(hasil)

    @property
    def pakai_analitik(self) -> bool:
        a = self.analitik
        return (self.tanda in TANDA_ANALITIK and len(self.dimensi) == 1
                and bool(a.get("ramalan") or a.get("tren") or a.get("anomali")))

    @property
    def dim_baris(self) -> list[Pil]:
        """Dimensi di rak Baris -> baris tabel pivot (sisanya jadi kolom)."""
        return _unik([p for p in self.baris if p.peran == "dimensi"])

    def geo(self, peran: str) -> Pil | None:
        return next((p for p in self.dimensi if peran_geo(p.field) == peran), None)

    @property
    def horizontal(self) -> bool:
        """Dimensi di Baris & ukuran di Kolom -> batang mendatar."""
        return any(p.peran == "dimensi" for p in self.baris) and \
            not any(p.peran == "dimensi" for p in self.kolom)

    def ke_dict(self) -> dict:
        pil = lambda p: p and {"field": p.field, "peran": p.peran, "agg": p.agg, "metrik": p.metrik}  # noqa: E731
        return {"dataset_id": self.dataset_id, "judul": self.judul, "tanda": self.tanda,
                "kolom": [pil(p) for p in self.kolom], "baris": [pil(p) for p in self.baris],
                "warna": pil(self.warna), "ukuran": pil(self.ukuran), "label": self.label,
                "filter": self.filter, "urut": self.urut, "batas": self.batas, "analitik": self.analitik}


def _unik(pils: list[Pil]) -> list[Pil]:
    lihat, hasil = set(), []
    for p in pils:
        if p.label not in lihat:
            lihat.add(p.label)
            hasil.append(p)
    return hasil


# --- Dari JSON + validasi ---------------------------------------------------------------
def _pil(t, d: dict | None) -> Pil | None:
    if not d:
        return None
    peran = d.get("peran")
    nama = str(d.get("field", ""))
    if peran == "dimensi":
        return Pil(alat._kolom_sah(t, nama), "dimensi")
    if peran != "ukuran":
        raise alat.InputSalah(f"Peran '{peran}' tidak dikenal.")
    if nama == BARIS:
        return Pil(BARIS, "ukuran", "COUNT")
    if d.get("metrik"):
        if nama not in {m.metric_name for m in t.metrics}:
            raise alat.InputSalah(f"Metrik '{nama}' tidak ada di dataset.")
        return Pil(nama, "ukuran", metrik=True)
    agg = str(d.get("agg") or "SUM").upper()
    if agg not in AGREGAT:
        raise alat.InputSalah(f"Agregasi '{agg}' tidak dikenal.")
    return Pil(alat._kolom_sah(t, nama), "ukuran", agg)


def dari_dict(d: dict) -> tuple[Any, Lembar]:
    """Validasi spesifikasi dari browser. Kembalikan (dataset, lembar)."""
    t = alat._dataset(int(d.get("dataset_id") or 0))          # cek akses dataset
    tanda = str(d.get("tanda") or "tabel")
    if tanda not in ATURAN_TANDA:
        raise alat.InputSalah(f"Jenis tanda '{tanda}' tidak dikenal.")
    lembar = Lembar(
        dataset_id=t.id, tanda=tanda, judul=str(d.get("judul") or "")[:250],
        kolom=[_pil(t, p) for p in d.get("kolom") or []],
        baris=[_pil(t, p) for p in d.get("baris") or []],
        warna=_pil(t, d.get("warna")), ukuran=_pil(t, d.get("ukuran")),
        label=bool(d.get("label")), filter=list(d.get("filter") or []),
        urut=str(d.get("urut") or ""), batas=max(1, min(int(d.get("batas") or 1000), 10000)),
        analitik=_analitik(d.get("analitik")))
    return t, lembar


def _analitik(a: dict | None) -> dict:
    from sps_studio.prediksi import MAKS_PERIODE
    a = a or {}
    hasil = {"ramalan": max(0, min(int(a.get("ramalan") or 0), MAKS_PERIODE)),
             "tren": bool(a.get("tren")), "anomali": bool(a.get("anomali"))}
    return hasil if any(hasil.values()) else {}


def periksa_tanda(lembar: Lembar) -> None:
    """Pastikan jumlah dimensi & ukuran cocok dengan jenis tanda (aturan Tampilkan Saya)."""
    a = ATURAN_TANDA[lembar.tanda]
    nd, nu = len(lembar.dimensi), len(lembar.ukuran_semua)
    if not (a["dim"][0] <= nd <= a["dim"][1] and a["ukuran"][0] <= nu <= a["ukuran"][1]):
        raise alat.InputSalah(
            f"{a['label']} butuh {a['dim'][0]}–{a['dim'][1]} dimensi dan {a['ukuran'][0]}–{a['ukuran'][1]} "
            f"ukuran (sekarang {nd} dimensi, {nu} ukuran).")
    if nd + nu == 0:
        raise alat.InputSalah("Seret minimal satu kolom ke rak Kolom atau Baris.")
    if a.get("geo") == "titik" and not (lembar.geo("lintang") and lembar.geo("bujur")):
        raise alat.InputSalah(f"{a['label']} butuh kolom lintang (lat) dan bujur (lon/lng) sebagai dimensi.")


# --- Query -----------------------------------------------------------------------------
def _metrik(p: Pil) -> Any:
    if p.metrik:
        return p.field
    if p.field == BARIS:
        return {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": LABEL_BARIS}
    return {"expressionType": "SIMPLE", "column": {"column_name": p.field}, "aggregate": p.agg, "label": p.label}


def _filter(t, lembar: Lembar) -> list[dict]:
    return alat._filter_bersih(t, [{"kolom": f.get("field"), "op": f.get("op"), "nilai": f.get("nilai")}
                                   for f in lembar.filter])


def jalankan(t, lembar: Lembar) -> dict:
    from sps_studio import prediksi

    metrics = [_metrik(p) for p in lembar.ukuran_semua]
    orderby = [[metrics[0], lembar.urut == "naik"]] if metrics else []    # bawaan: terbesar dulu
    if lembar.pakai_analitik:                       # deret waktu: ambil periode TERBARU bila dibatasi
        orderby = [[lembar.dimensi[0].field, False]]
    hasil = alat.jalankan_objek(t, metrics, [p.field for p in lembar.dimensi], _filter(t, lembar),
                                orderby, lembar.batas)
    analitik = (prediksi.analisis(hasil["baris"], lembar.dimensi[0].label,
                                  [p.label for p in lembar.ukuran_semua], lembar.analitik)
                if lembar.pakai_analitik else None)
    return {"analitik": analitik, "kolom": hasil["kolom"], "baris": hasil["baris"],
            "dimensi": [p.label for p in lembar.dimensi], "ukuran": [p.label for p in lembar.ukuran_semua],
            "dim_baris": [p.label for p in lembar.dim_baris],
            "geo": {p.label: peran_geo(p.field) for p in lembar.dimensi if peran_geo(p.field)}}


def nilai_unik(t, kolom: str, batas: int = 300) -> list:
    """Nilai berbeda sebuah dimensi (untuk dialog filter), terbanyak dulu."""
    nama = alat._kolom_sah(t, kolom)
    hitung = {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "n"}
    hasil = alat.jalankan_objek(t, [hitung], [nama], [], [[hitung, False]], batas)
    return [b[nama] for b in hasil["baris"]]


# --- Ke chart Superset --------------------------------------------------------------------
def ke_superset(t, lembar: Lembar) -> tuple[str, dict]:
    """Ubah lembar kerja menjadi viz_type + params chart Superset."""
    periksa_tanda(lembar)
    D = [p.field for p in lembar.dimensi]
    M = [_metrik(p) for p in lembar.ukuran_semua]
    viz = ATURAN_TANDA[lembar.tanda]["viz"]
    p: dict[str, Any] = {
        "viz_type": viz, "row_limit": lembar.batas, "color_scheme": SKEMA_WARNA,
        "adhoc_filters": [{"expressionType": "SIMPLE", "clause": "WHERE", "subject": f["col"],
                           "operator": f["op"], "comparator": f["val"]} for f in _filter(t, lembar)],
        "sps_studio": lembar.ke_dict(),                     # agar bisa dibuka lagi di Studio
    }
    tanda = lembar.tanda
    if tanda == "angka":
        p.update(metric=M[0], y_axis_format="SMART_NUMBER", header_font_size=0.4)
    elif tanda == "tabel":
        if M:
            p.update(query_mode="aggregate", groupby=D, metrics=M, order_desc=True,
                     show_cell_bars=True, server_page_length=25)
        else:
            p.update(query_mode="raw", all_columns=D, server_page_length=25)
    elif tanda in ("batang", "garis", "area"):
        # Kolom tanggal: sumbu waktu asli (dipaksa kategori -> label "NaN" di Superset)
        kategori = not _kolom_waktu(t, D[0])
        p.update(x_axis=D[0], groupby=D[1:2], metrics=M, xAxisForceCategorical=kategori,
                 x_axis_time_format="smart_date",
                 y_axis_format="SMART_NUMBER", show_legend=len(M) > 1 or len(D) > 1,
                 show_value=lembar.label, truncateXAxis=True, rich_tooltip=True,
                 x_axis_sort_asc=lembar.urut != "turun")
        if tanda == "batang":
            p["orientation"] = "horizontal" if lembar.horizontal else "vertical"
        if len(D) > 1 and tanda in ("batang", "area"):        # warna = dimensi -> bertumpuk
            p["stack"] = "Stack"
        if lembar.urut and tanda == "batang":
            if len(D) > 1:      # ada seri warna: Superset mengurutkan lewat total seri, bukan x_axis_sort
                p.update(x_axis_sort_series="sum", x_axis_sort_series_ascending=lembar.urut == "naik")
            else:
                p.update(x_axis_sort=lembar.ukuran_semua[0].label, x_axis_sort_asc=lembar.urut == "naik")
    elif tanda == "pie":
        p.update(groupby=D[:1], metric=M[0], donut=True, show_labels=True, label_type="key_percent",
                 number_format="SMART_NUMBER", sort_by_metric=True, legendOrientation="right")
    elif tanda == "sebar":
        p.update(entity=D[0], x=M[0], y=M[1], size=M[2] if len(M) > 2 else M[1],
                 max_bubble_size="25", x_axis_format="SMART_NUMBER", y_axis_format="SMART_NUMBER")
    elif tanda == "angka_tren":
        if not _kolom_waktu(t, D[0]):
            raise alat.InputSalah(f"Angka + tren butuh kolom bertipe tanggal; '{D[0]}' bukan tanggal. "
                                  "Untuk tahun/bulan berupa angka pakai Garis.")
        p.update(x_axis=D[0], metric=M[0], time_grain_sqla="P1D", show_trend_line=True,
                 start_y_axis_at_zero=True, y_axis_format="SMART_NUMBER", header_font_size=0.4,
                 subheader_font_size=0.15, rolling_type="None")
    elif tanda == "gauge":
        p.update(groupby=[], metric=M[0], min_val=0, start_angle=225, end_angle=-45, show_progress=True,
                 overlap=True, show_pointer=True, number_format="SMART_NUMBER", font_size=15,
                 split_number=5, animation=True)
    elif tanda == "tabel_pivot":
        baris = [x.field for x in lembar.dim_baris] or D[:1]
        p.update(groupbyRows=baris, groupbyColumns=[d for d in D if d not in baris], metrics=M,
                 aggregateFunction="Sum", metricsLayout="COLUMNS", rowTotals=True, colTotals=True,
                 valueFormat="SMART_NUMBER", combineMetric=False, transposePivot=False)
    elif tanda == "batang_100":
        p.update(x_axis=D[0], groupby=D[1:2], metrics=M, xAxisForceCategorical=not _kolom_waktu(t, D[0]),
                 stack="Expand", x_axis_time_format="smart_date",
                 y_axis_format=".0%", show_legend=True, show_value=lembar.label, rich_tooltip=True,
                 orientation="horizontal" if lembar.horizontal else "vertical", truncateXAxis=True)
    elif tanda == "waterfall":
        p.update(x_axis=D[0], groupby=[], metric=M[0], show_value=lembar.label, y_axis_format="SMART_NUMBER",
                 increase_color={"r": 27, "g": 175, "b": 122, "a": 1},
                 decrease_color={"r": 227, "g": 73, "b": 72, "a": 1},
                 total_color={"r": 42, "g": 91, "b": 184, "a": 1})
    elif tanda == "radar":
        p.update(groupby=D, metrics=M, show_legend=True, show_labels=lembar.label, label_type="value",
                 number_format="SMART_NUMBER", is_circle=False, column_config={})
    elif tanda == "treemap":
        p.update(groupby=D, metric=M[0], show_labels=True, label_type="key_value", number_format="SMART_NUMBER")
    elif tanda == "sunburst":
        p.update(columns=D, metric=M[0], show_labels=True, label_type="key", number_format="SMART_NUMBER")
    elif tanda == "funnel":
        p.update(groupby=D, metric=M[0], sort_by_metric=True, show_labels=True, label_type="key_value_percent",
                 number_format="SMART_NUMBER", legendOrientation="top")
    elif tanda == "awan_kata":
        p.update(series=D[0], metric=M[0], size_from=12, size_to=56, rotation="flat")
    elif tanda == "box_plot":
        p.update(groupby=D[:1], columns=D[1:2], metrics=M, whiskerOptions="Tukey",
                 x_axis_title_margin=15, y_axis_format="SMART_NUMBER")
    elif tanda == "sankey":
        p.update(source=D[0], target=D[1], metric=M[0])
    elif tanda == "peta_wilayah":
        p.update(entity=D[0], metric=M[0], select_country="indonesia", linear_color_scheme=SKEMA_RUNTUN,
                 number_format="SMART_NUMBER")
        p.pop("color_scheme")               # bila ada, country_map memakai warna kategori (bukan gradasi)
    elif tanda in ("peta_titik", "peta_kepadatan"):
        lat, lon = lembar.geo("lintang").field, lembar.geo("bujur").field
        p.update(spatial={"latCol": lat, "lonCol": lon, "type": "latlong"}, viewport=dict(VIEWPORT_INDONESIA),
                 mapbox_style=_ubin_peta(), color_picker={"r": 42, "g": 91, "b": 184, "a": 0.8})
        lain = [d for d in D if d not in (lat, lon)]
        if tanda == "peta_titik":
            p.update(point_radius_fixed={"type": "metric", "value": M[0]} if M else {"type": "fix", "value": 2000},
                     point_unit="square_m" if M else "radius_m", multiplier=1, min_radius=3, max_radius=30,
                     dimension=lain[0] if lain else None)    # warna per nilai; jangan diisi ke groupby juga
        else:
            p.update(size=M[0] if M else "count", grid_size=20000, extruded=False,
                     js_agg_function="sum", point_radius_fixed={"type": "fix", "value": 1000})
    elif tanda == "peta_panas":
        p.update(x_axis=D[0], groupby=D[1:2], metric=M[0], linear_color_scheme=SKEMA_RUNTUN,
                 show_values=lembar.label, normalize_across="heatmap", value_bounds=[None, None],
                 y_axis_format="SMART_NUMBER", sort_x_axis="alpha_asc", sort_y_axis="alpha_asc")
    return viz, p


def _kolom_waktu(t, nama: str) -> bool:
    return any(c.column_name == nama and c.is_dttm for c in t.columns)


def _ubin_peta() -> str:
    """Peta dasar deck.gl: entri pertama DECKGL_BASE_MAP (superset_config, bisa server ubin lokal)."""
    from flask import current_app
    peta = current_app.config.get("DECKGL_BASE_MAP") or []
    return peta[0][0] if peta else "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


# --- Simpan & buka ----------------------------------------------------------------------------
def simpan(t, lembar: Lembar, chart_id: int | None = None) -> dict:
    """Simpan sebagai chart Superset (baru, atau perbarui chart milik sendiri)."""
    from superset import db, security_manager
    from superset.commands.chart.create import CreateChartCommand
    from superset.models.slice import Slice

    from sps_studio import ramalan

    viz, params = ke_superset(t, lembar)
    judul = (lembar.judul or f"{ATURAN_TANDA[lembar.tanda]['label']} {t.table_name}")[:250]
    if not security_manager.can_access("can_write", "Chart"):
        return {"disimpan": False, "url": alat.explore_url(t.id, params),
                "catatan": "Anda belum punya izin menyimpan chart. Buka tautan untuk melihat di Explore."}
    sumber_id, tabel_ramalan, catatan = t.id, None, ""
    if lembar.pakai_analitik and (lembar.analitik.get("ramalan") or lembar.analitik.get("tren")):
        # Superset tidak punya ramalan Holt-Winters: hasil disimpan sebagai dataset di ALDx Engine
        sumber_id, tabel_ramalan = ramalan.siapkan(t, lembar, chart_id)
        from superset.connectors.sqla.models import SqlaTable
        viz, params = "echarts_timeseries_line", ramalan.params_chart(lembar, db.session.query(SqlaTable).get(sumber_id))
        catatan = "Ramalan disimpan di ALDx Engine dan diperbarui otomatis tiap hari."
    elif lembar.analitik.get("anomali"):
        catatan = "Tanda anomali hanya tampil di Studio Visual."
    if chart_id:
        chart = db.session.query(Slice).get(int(chart_id))
        if chart is None:
            raise alat.InputSalah("Chart tidak ditemukan.")
        security_manager.raise_for_ownership(chart)           # hanya pemilik / Admin
        chart.slice_name, chart.viz_type, chart.params = judul, viz, json.dumps(params)
        chart.datasource_id, chart.query_context = sumber_id, None
        db.session.commit()
    else:
        chart = CreateChartCommand({"slice_name": judul, "viz_type": viz, "params": json.dumps(params),
                                    "datasource_id": sumber_id, "datasource_type": "table"}).run()
    if tabel_ramalan:
        from flask import g
        ramalan.catat(chart.id, t.id, sumber_id, tabel_ramalan, lembar, g.user.username)
    return {"disimpan": True, "id": chart.id, "judul": judul, "url": f"/explore/?slice_id={chart.id}",
            "catatan": catatan}


def buka(chart_id: int) -> dict:
    from superset import db, security_manager
    from superset.models.slice import Slice

    chart = db.session.query(Slice).get(int(chart_id))
    if chart is None or not security_manager.can_access_chart(chart):
        raise alat.IzinDitolak("Chart tidak ditemukan atau tidak boleh Anda buka.")
    spec = json.loads(chart.params or "{}").get("sps_studio")
    if not spec:
        raise alat.InputSalah("Chart ini tidak dibuat di Studio; buka lewat Explore.")
    return {**spec, "chart_id": chart.id, "judul": chart.slice_name}


def daftar() -> list[dict]:
    """Lembar kerja Studio yang boleh dibuka user (terbaru dulu)."""
    from superset import db, security_manager
    from superset.models.slice import Slice

    rows = (db.session.query(Slice).filter(Slice.params.like('%"sps_studio"%'))
            .order_by(Slice.changed_on.desc()).limit(200).all())
    hasil = []
    for c in rows:
        if not security_manager.can_access_chart(c):
            continue
        spec = json.loads(c.params or "{}").get("sps_studio", {})
        hasil.append({"id": c.id, "judul": c.slice_name, "tanda": spec.get("tanda"),
                      "dataset_id": spec.get("dataset_id") or c.datasource_id, "spec": spec,
                      "diubah": c.changed_on.isoformat(sep=" ", timespec="minutes") if c.changed_on else ""})
    return hasil
