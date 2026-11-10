"""Dashboard "Home Nasional" - padanan halaman /Home engineN di Superset.

Sumber query: engineN app/Models/Mpemby.php (versi Oracle), koneksi
"Oracle DMP (GENAPP)" = grup database `default` engineN.

Bagian yang dipindahkan (nama method engineN dalam kurung):
    KPI penerimaan          (getRenpen, getPen, getPenl, getWaktuData)
    Per jenis pajak         (getPiePen)
    Sektor dominan          (getSektdom, 10 teratas)
    Payment compliance      (paycompNas, paycompPus)
    Strength of figure      (sofNas)
    WP terdaftar & PPM/PKM  (getWPterdaftar, getPPMPKM, grafWPTerdaftar)
    Breakdown penerimaan    (getWpsk + getBreakdownPen)
    Dashboard WP            (Wpbyrlpr, ringkasan per kelompok)
    Follow the money        (getKat, nasional & WP pusat)

Hak akses: data di sini NASIONAL (tanpa kolom kanwil/kpp), jadi setiap
dataset memakai akses={} -> hanya user berlingkup "semua" (Kantor Pusat &
Admin) yang melihat angka, sama seperti /Home engineN yang khusus KPDJP.
Dashboard juga dibatasi untuk role "DJP Pusat".

Semua dataset membaca filter "tahun" dan "bulan" lewat sps_periode()
(lihat sps_jinja.py). Kolom tahun/bulan sengaja ikut dikeluarkan setiap
dataset agar filter dashboard berlaku untuk semua chart.

Jalankan: scripts\\build-dashboards.ps1
"""

from __future__ import annotations

from sps_dashboard_builder import Chart, Dashboard, Dataset, Markdown, Metric, SelectFilter

DATABASE = "Oracle DMP (GENAPP)"

# Baris pembuka setiap SQL: periode dari filter dashboard (tervalidasi).
PERIODE = (
    "{% set p = sps_periode(filter_values('tahun', remove_filter=True), "
    "filter_values('bulan', remove_filter=True)) %}\n"
)
KOLOM_PERIODE = "'{{ p.tahun }}' AS tahun, '{{ p.bulan }}' AS bulan"

RUPIAH = ",.0f"
PERSEN = ".2%"


def ratio(numerator: str, denominator: str) -> str:
    return f"SUM({numerator}) / NULLIF(SUM({denominator}), 0)"


def growth(now: str, before: str) -> str:
    return f"SUM({now}) / NULLIF(SUM({before}), 0) - 1"


# --- Dataset -----------------------------------------------------------------
DATASETS = [
    Dataset(
        key="periode",
        description="Pilihan filter Tahun (6 tahun terakhir) dan Bulan (01-12).",
        sql="""
SELECT t.tahun, b.bulan
FROM (SELECT TO_CHAR(EXTRACT(YEAR FROM SYSDATE) - LEVEL + 1) AS tahun
      FROM DUAL CONNECT BY LEVEL <= 6) t
CROSS JOIN (SELECT LPAD(LEVEL, 2, '0') AS bulan FROM DUAL CONNECT BY LEVEL <= 12) b
""",
        columns=["tahun", "bulan"],
        akses=None,   # data referensi: semua orang boleh melihat pilihan filter
    ),
    Dataset(
        key="kpi",
        description="Target, realisasi, dan realisasi tahun lalu s.d. bulan terpilih.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE},
  (SELECT SUM(RENPEN) FROM MVTARGET_AR
    WHERE TAHUN = '{{{{ p.tahun }}}}' AND BULAN <= '{{{{ p.bulan }}}}') AS renpen,
  (SELECT SUM(TOTAL) FROM DASHBOARD_WP_BLN_RKP
    WHERE TAHUN = '{{{{ p.tahun }}}}' AND BULAN BETWEEN '01' AND '{{{{ p.bulan }}}}') AS pen,
  (SELECT SUM(TOTAL) FROM DASHBOARD_WP_BLN_RKP
    WHERE TAHUN = '{{{{ p.tahun_lalu }}}}' AND BULAN BETWEEN '01' AND '{{{{ p.bulan }}}}') AS penl,
  (SELECT TO_CHAR(MAX(DW_PROCESS_DATE), 'dd-mm-yyyy hh24:mi') FROM DASHBOARD_WP_BLN_RKP
    WHERE TAHUN = '{{{{ p.tahun }}}}') AS update_data
FROM DUAL
""",
        columns=["tahun", "bulan", "renpen", "pen", "penl", "update_data"],
        metrics=[
            Metric("target", "SUM(renpen)", "Target", RUPIAH),
            Metric("penerimaan", "SUM(pen)", "Penerimaan", RUPIAH),
            Metric("penerimaan_lalu", "SUM(penl)", "Penerimaan Tahun Lalu", RUPIAH),
            Metric("capaian", ratio("pen", "renpen"), "Capaian", PERSEN),
            Metric("growth", growth("pen", "penl"), "Growth", PERSEN),
        ],
    ),
    Dataset(
        key="jenis_pajak",
        description="7 jenis pajak dengan penerimaan terbesar.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, x.nm_pajak, x.penerimaan, x.penerimaan_lalu
FROM (
  SELECT NM_PAJAK AS nm_pajak,
    ROUND(SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR <= '{{{{ p.bulan }}}}'
                   THEN ROUND(TOTAL) ELSE 0 END)) AS penerimaan,
    ROUND(SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR <= '{{{{ p.bulan }}}}'
                   THEN ROUND(TOTAL) ELSE 0 END)) AS penerimaan_lalu
  FROM PERJENIS_MV
  WHERE THNBYR IN ('{{{{ p.tahun }}}}', '{{{{ p.tahun_lalu }}}}')
  GROUP BY NM_PAJAK
  ORDER BY penerimaan DESC
) x
WHERE ROWNUM <= 7
""",
        columns=["tahun", "bulan", "nm_pajak", "penerimaan", "penerimaan_lalu"],
        metrics=[
            Metric("penerimaan", "SUM(penerimaan)", "Penerimaan", RUPIAH),
            Metric("penerimaan_lalu", "SUM(penerimaan_lalu)", "Penerimaan Tahun Lalu", RUPIAH),
            Metric("growth", growth("penerimaan", "penerimaan_lalu"), "Growth", PERSEN),
        ],
    ),
    Dataset(
        key="sektor",
        description="10 sektor (kategori KLU) dengan penerimaan terbesar pada bulan terpilih.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, x.kd_kategori, x.nm_kategori, x.total, x.wpbyr
FROM (
  SELECT a.kd_kategori, NVL(b.NM_KATEGORI, 'UNKNOWN') AS nm_kategori, a.total, a.wpbyr
  FROM (SELECT KATEGORI AS kd_kategori, SUM(TOTAL) AS total, SUM(WPBAYAR) AS wpbyr
        FROM PERKATEGORI_MV
        WHERE THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}'
        GROUP BY KATEGORI) a
  LEFT JOIN (SELECT DISTINCT KD_KATEGORI, NM_KATEGORI FROM REF_KLU) b
         ON a.kd_kategori = b.KD_KATEGORI
  ORDER BY a.total DESC
) x
WHERE ROWNUM <= 10
""",
        columns=["tahun", "bulan", "kd_kategori", "nm_kategori", "total", "wpbyr"],
        metrics=[
            Metric("penerimaan", "SUM(total)", "Penerimaan", RUPIAH),
            Metric("wp_bayar", "SUM(wpbyr)", "WP Bayar", RUPIAH),
        ],
    ),
    Dataset(
        key="paycomp_nasional",
        description="Payment compliance nasional: jumlah WP menurut banyaknya bulan membayar.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, JMLBLN AS jmlbulan, SUM(JMLWP) AS jmlwp, SUM(TOTAL) AS total
FROM DASHBOARD_WP_BLN_REKAP
WHERE TAHUN = '{{{{ p.tahun }}}}' AND JMLBLN <= TO_NUMBER('{{{{ p.bulan }}}}')
GROUP BY JMLBLN
""",
        columns=["tahun", "bulan", "jmlbulan", "jmlwp", "total"],
        metrics=[
            Metric("jumlah_wp", "SUM(jmlwp)", "Jumlah WP", RUPIAH),
            Metric("penerimaan", "SUM(total)", "Penerimaan", RUPIAH),
        ],
    ),
    Dataset(
        key="paycomp_pusat",
        description="Payment compliance WP pusat.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, JMLBULAN AS jmlbulan, JMLWP AS jmlwp, TOTAL AS total
FROM GRAFPUS_REKAP
WHERE TAHUN = '{{{{ p.tahun }}}}' AND JMLBULAN <= TO_NUMBER('{{{{ p.bulan }}}}')
""",
        columns=["tahun", "bulan", "jmlbulan", "jmlwp", "total"],
        metrics=[
            Metric("jumlah_wp", "SUM(jmlwp)", "Jumlah WP", RUPIAH),
            Metric("penerimaan", "SUM(total)", "Penerimaan", RUPIAH),
        ],
    ),
    Dataset(
        key="sof",
        description="Strength of figure: WP bayar dan penerimaan per lapisan setoran.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, NO AS no_urut, LAPISAN AS lapisan,
       SUM(ROUND(WPBYR)) AS wpbyr, SUM(ROUND(TOTAL)) AS total
FROM IKU_SOF
WHERE TAHUN = '{{{{ p.tahun }}}}' AND BULAN = '{{{{ p.bulan }}}}'
GROUP BY NO, LAPISAN
""",
        columns=["tahun", "bulan", "no_urut", "lapisan", "wpbyr", "total"],
        metrics=[
            Metric("wp_bayar", "SUM(wpbyr)", "WP Bayar", RUPIAH),
            Metric("penerimaan", "SUM(total)", "Penerimaan", RUPIAH),
            Metric("urutan", "MIN(no_urut)", "Urutan"),
        ],
    ),
    Dataset(
        key="ringkas_wp",
        description="WP terdaftar (kumulatif) dan hasil PPM/PKM/SBP s.d. bulan terpilih.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE},
  (SELECT SUM(CASE WHEN TAHUN <= '{{{{ p.tahun }}}}' THEN ROUND(JUMLAHWP) ELSE 0 END)
     FROM WP_TERDAFTAR) AS wp_terdaftar,
  (SELECT SUM(CASE WHEN TAHUN <= '{{{{ p.tahun_lalu }}}}' THEN ROUND(JUMLAHWP) ELSE 0 END)
     FROM WP_TERDAFTAR) AS wp_terdaftar_lalu,
  k.ppm, k.pkm, k.sbp
FROM (SELECT SUM(PPM) AS ppm, SUM(PKM) AS pkm, SUM(SBP) AS sbp
      FROM PPMPKM
      WHERE THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR <= '{{{{ p.bulan }}}}') k
""",
        columns=["tahun", "bulan", "wp_terdaftar", "wp_terdaftar_lalu", "ppm", "pkm", "sbp"],
        metrics=[
            Metric("wp_terdaftar", "SUM(wp_terdaftar)", "WP Terdaftar", RUPIAH),
            Metric("growth_wp_terdaftar", growth("wp_terdaftar", "wp_terdaftar_lalu"),
                   "Growth WP Terdaftar", PERSEN),
            Metric("ppm", "SUM(ppm)", "Penerimaan PPM", RUPIAH),
            Metric("pkm", "SUM(pkm)", "Penerimaan PKM", RUPIAH),
            Metric("sbp", "SUM(sbp)", "Penerimaan SBP", RUPIAH),
        ],
    ),
    Dataset(
        key="wp_terdaftar_tahunan",
        description="Jumlah WP terdaftar kumulatif 11 tahun terakhir.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE}, y.tahun_wp,
  (SELECT SUM(JUMLAHWP) FROM WP_TERDAFTAR w WHERE w.TAHUN <= y.tahun_wp) AS jumlahwp
FROM (SELECT TO_CHAR({{{{ p.tahun }}}} - LEVEL + 1) AS tahun_wp
      FROM DUAL CONNECT BY LEVEL <= 11) y
""",
        columns=["tahun", "bulan", "tahun_wp", "jumlahwp"],
        metrics=[Metric("jumlah_wp", "SUM(jumlahwp)", "WP Terdaftar", RUPIAH)],
    ),
    Dataset(
        key="breakdown",
        description="Breakdown penerimaan WP Strategis (WPS) dan Kewilayahan (WPK) pada bulan terpilih.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE},
  CASE b.flag WHEN 'WPS' THEN 'Strategis (WPS)' ELSE 'Kewilayahan (WPK)' END AS kelompok,
  s.jml AS wp_terdaftar, b.wp_bayar, b.wp_bayar_lalu, b.penerimaan, b.penerimaan_lalu
FROM (
  SELECT FLAG_WPS_WPK AS flag,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBYR) ELSE 0 END) AS wp_bayar,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBYR) ELSE 0 END) AS wp_bayar_lalu,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTAL) ELSE 0 END) AS penerimaan,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTAL) ELSE 0 END) AS penerimaan_lalu
  FROM BREAKDOWN_PEN
  WHERE FLAG_WPS_WPK IN ('WPS', 'WPK')
  GROUP BY FLAG_WPS_WPK
) b
LEFT JOIN (SELECT FLAG_WPS_WPK AS flag, SUM(ROUND(JUMLAHWP)) AS jml
           FROM WPSK_MV GROUP BY FLAG_WPS_WPK) s ON b.flag = s.flag
""",
        columns=["tahun", "bulan", "kelompok", "wp_terdaftar", "wp_bayar", "wp_bayar_lalu",
                 "penerimaan", "penerimaan_lalu"],
        metrics=[
            Metric("wp_terdaftar", "SUM(wp_terdaftar)", "WP Terdaftar", RUPIAH),
            Metric("wp_bayar", "SUM(wp_bayar)", "WP Bayar", RUPIAH),
            Metric("ratio_wp_bayar", ratio("wp_bayar", "wp_terdaftar"), "Ratio WP Bayar", PERSEN),
            Metric("growth_wp_bayar", growth("wp_bayar", "wp_bayar_lalu"), "Growth WP Bayar", PERSEN),
            Metric("penerimaan", "SUM(penerimaan)", "Penerimaan", RUPIAH),
            Metric("growth_penerimaan", growth("penerimaan", "penerimaan_lalu"),
                   "Growth Penerimaan", PERSEN),
        ],
    ),
    Dataset(
        key="dashboard_wp",
        description="Dashboard WP: jumlah WP, yang bayar, dan yang lapor per kelompok (tahun terpilih).",
        sql=PERIODE + "\n".join(
            [f"SELECT {KOLOM_PERIODE}, x.* FROM ("]
            + [
                ("  UNION ALL\n" if i else "")
                + f"  SELECT {i + 1} AS urutan, '{label}' AS kelompok, SUM({wp}) AS wp, "
                  f"SUM({byr}) AS bayar, SUM({lpr}) AS lapor\n"
                  "  FROM DASHBOARD_BESAR_BYRLPR WHERE TAHUN = '{{ p.tahun }}'"
                for i, (label, wp, byr, lpr) in enumerate([
                    ("WP Aktif (Normal)", "WPNORMAL", "NORMALBYR", "NORMALLPR"),
                    ("WP NE", "WPNE", "NEBYR", "NELPR"),
                    ("WP DE", "WPDE", "DEBYR", "DELPR"),
                    ("WP Badan", "WPBADAN", "BADANBYR", "BADANLPR"),
                    ("WP Orang Pribadi", "WPOP", "OPBYR", "OPLPR"),
                    ("WP Instansi Pemerintah", "WPPEMUNGUT", "PEMUNGUTBYR", "PEMUNGUTLPR"),
                    ("WP Lama", "WPLAMA", "LAMABYR", "LAMALPR"),
                    ("WP Baru", "WPBARU", "BARUBYR", "BARULPR"),
                ])
            ]
            + [") x"]
        ),
        columns=["tahun", "bulan", "urutan", "kelompok", "wp", "bayar", "lapor"],
        metrics=[
            Metric("jumlah_wp", "SUM(wp)", "Jumlah WP", RUPIAH),
            Metric("wp_bayar", "SUM(bayar)", "WP Bayar", RUPIAH),
            Metric("ratio_bayar", ratio("bayar", "wp"), "Ratio Bayar", PERSEN),
            Metric("wp_lapor", "SUM(lapor)", "WP Lapor", RUPIAH),
            Metric("ratio_lapor", ratio("lapor", "wp"), "Ratio Lapor", PERSEN),
            Metric("urutan", "MIN(urutan)", "Urutan"),
        ],
    ),
    Dataset(
        key="kategori",
        description="Follow the money: populasi, WP bayar, PDB, dan penerimaan per kategori KBLI.",
        sql=PERIODE + f"""
SELECT {KOLOM_PERIODE},
  a.kategori AS kode, a.nmkat, a.populasi, a.populasipus,
  b.wpbyrn, b.wpbyrp, b.kpenn, b.kpenp, b.wpbyrnpus, b.wpbyrppus, b.kpennpus, b.kpenppus,
  c.gdp
FROM (SELECT NVL(KATEGORI, 'X') AS kategori, NVL(NM_KATEGORI, 'UNKNOWN') AS nmkat,
             SUM(POPULASI) AS populasi, SUM(POPULASI_PUSAT) AS populasipus
      FROM POPULASI_KATEGORI GROUP BY KATEGORI, NM_KATEGORI) a
LEFT JOIN (
  SELECT NVL(KATEGORI, 'X') AS kode,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBAYAR) ELSE 0 END) AS wpbyrn,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBAYAR) ELSE 0 END) AS wpbyrp,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTAL) ELSE 0 END) AS kpenn,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTAL) ELSE 0 END) AS kpenp,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBAYARPUS) ELSE 0 END) AS wpbyrnpus,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(WPBAYARPUS) ELSE 0 END) AS wpbyrppus,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTALPUS) ELSE 0 END) AS kpennpus,
    SUM(CASE WHEN THNBYR = '{{{{ p.tahun_lalu }}}}' AND BLNBYR = '{{{{ p.bulan }}}}' THEN ROUND(TOTALPUS) ELSE 0 END) AS kpenppus
  FROM PERKATEGORI_MV
  WHERE THNBYR IN ('{{{{ p.tahun }}}}', '{{{{ p.tahun_lalu }}}}')
  GROUP BY KATEGORI
) b ON a.kategori = b.kode
LEFT JOIN (SELECT KODE AS kode, {{{{ p.kolom_pdb }}}} * 1000000000 AS gdp
           FROM REF_BI_GDP WHERE TAHUN = '{{{{ p.tahun_lalu }}}}') c ON a.kategori = c.kode
""",
        columns=["tahun", "bulan", "kode", "nmkat", "populasi", "populasipus", "wpbyrn", "wpbyrp",
                 "kpenn", "kpenp", "wpbyrnpus", "wpbyrppus", "kpennpus", "kpenppus", "gdp"],
        metrics=[
            # Nasional - rumus sama dengan kolom 6, 7, 11, 12 di engineN
            Metric("populasi", "SUM(populasi)", "Populasi WP", RUPIAH),
            Metric("wp_bayar", "SUM(wpbyrn)", "WP Bayar", RUPIAH),
            Metric("coverage_ratio", ratio("wpbyrn", "populasi"), "Coverage Ratio", PERSEN),
            Metric("growth_wp_bayar", growth("wpbyrn", "wpbyrp"), "Growth WP Bayar", PERSEN),
            Metric("pdb", "SUM(gdp)", "PDB", RUPIAH),
            Metric("realisasi", "SUM(kpenn)", "Realisasi", RUPIAH),
            Metric("collection_ratio", ratio("kpenn", "gdp"), "Collection Ratio", PERSEN),
            Metric("growth_penerimaan", growth("kpenn", "kpenp"), "Growth Penerimaan", PERSEN),
            # WP pusat
            Metric("populasi_pusat", "SUM(populasipus)", "Populasi WP Pusat", RUPIAH),
            Metric("wp_bayar_pusat", "SUM(wpbyrnpus)", "WP Bayar Pusat", RUPIAH),
            Metric("coverage_ratio_pusat", ratio("wpbyrnpus", "populasipus"),
                   "Coverage Ratio Pusat", PERSEN),
            Metric("growth_wp_bayar_pusat", growth("wpbyrnpus", "wpbyrppus"),
                   "Growth WP Bayar Pusat", PERSEN),
            Metric("realisasi_pusat", "SUM(kpennpus)", "Realisasi Pusat", RUPIAH),
            Metric("collection_ratio_pusat", ratio("kpennpus", "gdp"),
                   "Collection Ratio Pusat", PERSEN),
            Metric("growth_penerimaan_pusat", growth("kpennpus", "kpenppus"),
                   "Growth Penerimaan Pusat", PERSEN),
        ],
    ),
]


# --- Chart -------------------------------------------------------------------
def big_number(key: str, title: str, dataset: str, metric: str, number_format: str,
               width: int = 3) -> Chart:
    return Chart(key, title, "big_number_total", dataset, width=width, height=25, params={
        "metric": metric,
        "y_axis_format": number_format,
        "header_font_size": 0.3,
        "subheader_font_size": 0.15,
    })


def pie(key: str, title: str, dataset: str, groupby: str, metric: str) -> Chart:
    return Chart(key, title, "pie", dataset, width=6, height=60, params={
        "groupby": [groupby],
        "metric": metric,
        "row_limit": 20,
        "sort_by_metric": True,
        "donut": True,
        "innerRadius": 40,
        "outerRadius": 75,
        "show_labels": True,
        "label_type": "key_percent",
        "labels_outside": True,
        "number_format": "SMART_NUMBER",
        "show_legend": True,
        "legendOrientation": "right",
    })


def bar(key: str, title: str, dataset: str, x_axis: str, metric: str,
        x_title: str, width: int = 6) -> Chart:
    return Chart(key, title, "echarts_timeseries_bar", dataset, width=width, height=55, params={
        "x_axis": x_axis,
        "xAxisForceCategorical": True,
        "x_axis_sort_asc": True,
        "metrics": [metric],
        "groupby": [],
        "row_limit": 100,
        "orientation": "vertical",
        "show_value": True,
        "y_axis_format": "SMART_NUMBER",
        "x_axis_title": x_title,
        "x_axis_title_margin": 30,
        "show_legend": False,
        "truncateXAxis": True,
    })


def table(key: str, title: str, dataset: str, groupby: list[str], metrics: list[str],
          sort_metric: str | None = None, width: int = 12, height: int = 50) -> Chart:
    params: dict = {
        "query_mode": "aggregate",
        "groupby": groupby,
        "metrics": metrics,
        "all_columns": [],
        "percent_metrics": [],
        "row_limit": 1000,
        "server_page_length": 25,
        "include_search": False,
        "show_cell_bars": True,
        "color_pn": True,
        "order_desc": sort_metric is None,
        "table_timestamp_format": "smart_date",
    }
    if sort_metric:
        params["timeseries_limit_metric"] = sort_metric
    return Chart(key, title, "table", dataset, width=width, height=height, params=params)


CHARTS = [
    big_number("kpi_target", "Target Nasional", "kpi", "target", "SMART_NUMBER"),
    big_number("kpi_penerimaan", "Penerimaan s.d. Bulan", "kpi", "penerimaan", "SMART_NUMBER"),
    big_number("kpi_capaian", "Capaian", "kpi", "capaian", PERSEN, width=2),
    big_number("kpi_growth", "Growth", "kpi", "growth", PERSEN, width=2),
    big_number("kpi_penerimaan_lalu", "Penerimaan Tahun Lalu", "kpi", "penerimaan_lalu",
               "SMART_NUMBER", width=2),
    pie("jenis_pajak", "Per Jenis Pajak", "jenis_pajak", "nm_pajak", "penerimaan"),
    pie("sektor_dominan", "Sektor Dominan", "sektor", "nm_kategori", "penerimaan"),
    bar("paycomp_nasional", "Payment Compliance - Nasional", "paycomp_nasional",
        "jmlbulan", "jumlah_wp", "Jumlah bulan membayar"),
    bar("paycomp_pusat", "Payment Compliance - WP Pusat", "paycomp_pusat",
        "jmlbulan", "jumlah_wp", "Jumlah bulan membayar"),
    table("sof", "Strength of Figure", "sof", ["lapisan"], ["wp_bayar", "penerimaan"],
          sort_metric="urutan", width=6, height=55),
    bar("wp_terdaftar_tahunan", "Grafik WP Terdaftar", "wp_terdaftar_tahunan",
        "tahun_wp", "jumlah_wp", "Tahun"),
    big_number("kpi_wp_terdaftar", "WP Terdaftar", "ringkas_wp", "wp_terdaftar", "SMART_NUMBER"),
    big_number("kpi_ppm", "Penerimaan PPM", "ringkas_wp", "ppm", "SMART_NUMBER"),
    big_number("kpi_pkm", "Penerimaan PKM", "ringkas_wp", "pkm", "SMART_NUMBER"),
    big_number("kpi_sbp", "Penerimaan SBP", "ringkas_wp", "sbp", "SMART_NUMBER"),
    table("breakdown", "Breakdown Penerimaan (WPS / WPK)", "breakdown", ["kelompok"],
          ["wp_terdaftar", "wp_bayar", "ratio_wp_bayar", "growth_wp_bayar",
           "penerimaan", "growth_penerimaan"], height=25),
    table("dashboard_wp", "Dashboard WP", "dashboard_wp", ["kelompok"],
          ["jumlah_wp", "wp_bayar", "ratio_bayar", "wp_lapor", "ratio_lapor"],
          sort_metric="urutan", height=45),
    table("follow_the_money", "Follow the Money - PDB berdasarkan KBLI", "kategori",
          ["kode", "nmkat"],
          ["populasi", "wp_bayar", "coverage_ratio", "growth_wp_bayar",
           "pdb", "realisasi", "collection_ratio", "growth_penerimaan"], height=80),
    table("follow_the_money_pusat", "Follow the Money - WP Pusat", "kategori",
          ["kode", "nmkat"],
          ["populasi_pusat", "wp_bayar_pusat", "coverage_ratio_pusat", "growth_wp_bayar_pusat",
           "pdb", "realisasi_pusat", "collection_ratio_pusat", "growth_penerimaan_pusat"],
          height=80),
]


# --- Tata letak --------------------------------------------------------------
ROWS = [
    Markdown(
        '<div style="background:#1F2F5F;color:#fff;padding:14px 20px;border-radius:8px;'
        'border-bottom:4px solid #F2B705;display:flex;align-items:center;gap:16px">'
        '<img src="/identitas/berkas/logo_putih" alt="Logo" style="height:34px"/>'
        '<div><div style="font-size:18px;font-weight:700">Dashboard Nasional</div>'
        '<div style="font-size:12px;opacity:.85">Direktorat Jenderal Pajak &middot; '
        'pilih <b>Tahun</b> dan <b>s.d. Bulan</b> di panel filter kiri '
        '(kosong = tahun &amp; bulan berjalan)</div></div></div>',
        height=12),
    ["kpi_target", "kpi_penerimaan", "kpi_capaian", "kpi_growth", "kpi_penerimaan_lalu"],
    ["jenis_pajak", "sektor_dominan"],
    Markdown("### Customer Perspective", height=6),
    ["paycomp_nasional", "paycomp_pusat"],
    ["sof", "wp_terdaftar_tahunan"],
    ["kpi_wp_terdaftar", "kpi_ppm", "kpi_pkm", "kpi_sbp"],
    ["breakdown"],
    ["dashboard_wp"],
    Markdown("### Follow the Money\n"
             "Coverage = WP Bayar / Populasi; Collection = Realisasi / PDB "
             "(PDB tahun lalu, kumulatif s.d. triwulan bulan terpilih).", height=10),
    ["follow_the_money"],
    ["follow_the_money_pusat"],
]

FILTERS = [
    SelectFilter("tahun", "Tahun", "periode", "tahun",
                 sort_ascending=False, default_to_first_item=True),
    SelectFilter("bulan", "s.d. Bulan", "periode", "bulan"),
]

HOME_NASIONAL = Dashboard(
    key="home_nasional",
    title="Home Nasional",
    slug="home-nasional",
    database_name=DATABASE,
    datasets=DATASETS,
    charts=CHARTS,
    rows=ROWS,
    filters=FILTERS,
    roles=["DJP Pusat"],
)
