"""Aturan jenis chart Studio Visual ("Tampilkan Saya"): data murni tanpa ketergantungan modul lain,
sehingga bisa diimpor dari mana saja (Studio, Auto Chart, Asisten AI) tanpa impor melingkar."""

from __future__ import annotations

from typing import Any

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
