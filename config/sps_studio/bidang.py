"""Panel Data: kolom dataset dibagi menjadi Dimensi & Ukuran.

Aturan saat membaca sumber data:
    Ukuran  = kolom angka yang bukan kode/ID/waktu (mis. total, jumlah_wp)
              + metrik tersimpan dataset + "Jumlah baris"
    Dimensi = selain itu (teks, tanggal, kode/ID seperti kd_cabang, ID_Tiket, t1.ID_Penerbangan, tahun/bulan)
              + kolom geografis: lintang/bujur (lat, lon) & provinsi -> untuk peta
"""

from __future__ import annotations

from sps_ai import alat
from sps_ai.auto import POLA_WAKTU, kolom_pengenal
from sps_studio.lembar import BARIS, LABEL_BARIS, peran_geo

def _jenis(c) -> str:
    if peran_geo(c.column_name):
        return "geo"
    if c.is_temporal or POLA_WAKTU.search(c.column_name):
        return "tanggal"
    return "angka" if c.is_numeric else "teks"


def daftar(dataset_id: int) -> dict:
    t = alat._dataset(dataset_id)
    dimensi, ukuran = [], []
    for c in sorted((c for c in t.columns if c.is_active is not False), key=lambda c: c.column_name.lower()):
        jenis = _jenis(c)
        nama = c.column_name
        item = {"field": nama, "label": c.verbose_name or nama, "jenis": jenis, "keterangan": c.description or ""}
        if jenis == "angka" and not kolom_pengenal(nama):
            ukuran.append({**item, "peran": "ukuran", "agg": "SUM"})
        else:
            dimensi.append({**item, "peran": "dimensi", "waktu": jenis == "tanggal",
                            "geo": peran_geo(nama), "dttm": bool(c.is_dttm)})
    for m in sorted(t.metrics, key=lambda m: m.metric_name.lower()):
        ukuran.append({"field": m.metric_name, "label": m.verbose_name or m.metric_name, "jenis": "metrik",
                       "peran": "ukuran", "metrik": True, "keterangan": m.description or m.expression})
    ukuran.append({"field": BARIS, "label": LABEL_BARIS, "jenis": "angka", "peran": "ukuran", "agg": "COUNT"})
    return {"id": t.id, "nama": t.table_name, "dimensi": dimensi, "ukuran": ukuran}
