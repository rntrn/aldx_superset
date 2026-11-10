"""Simpan hasil analitik (ramalan & tren) sebagai dataset di ALDx Engine agar tampil di chart
Superset & dashboard — Superset sendiri tidak punya ramalan Holt-Winters.

Alur saat lembar kerja dengan Ramalan disimpan (lembar.simpan):
    1. hitung ulang analitik sebagai user yang menyimpan (RLS berlaku)
    2. tulis tabel engine  ramalan__<kode>  (format panjang: periode, urutan, seri, nilai, sidik)
    3. daftarkan dataset + aturan RLS "sidik = sps_sidik()"  -> hanya pegawai dengan LINGKUP
       AKSES SAMA dengan pembuat yang melihat baris ini (angka hasil RLS tidak bocor)
    4. chart Superset = garis per seri (Aktual, Ramalan, batas 80%/95%, Tren)

Penyegaran: tugas "sps.ramalan.segarkan" tiap hari 03:00 (sps_engine/tugas.py) menghitung ulang
semua ramalan sebagai pembuatnya. Tabel metadata: sps_ramalan.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, insert, select, update

log = logging.getLogger(__name__)

NAMA_RLS = "ALDx ramalan (lingkup pembuat)"
NAMA_RLS_LAMA = "SPS ramalan (lingkup pembuat)"           # nama sebelum ganti nama ke ALDx (dipindah otomatis)
_meta = MetaData()
RAMALAN = Table(
    "sps_ramalan", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chart_id", Integer), Column("dataset_asal_id", Integer), Column("dataset_id", Integer),
    Column("tabel", String(160)), Column("spec", Text), Column("oleh", String(64)),
    Column("diperbarui", DateTime), Column("pesan", Text))


def _engine_meta():
    from superset import db
    _meta.create_all(bind=db.engine, checkfirst=True)
    return db.engine


def daftar() -> list[dict]:
    with _engine_meta().connect() as c:
        return [dict(r) for r in c.execute(select(RAMALAN)).mappings()]


def _milik_chart(chart_id: int | None) -> dict | None:
    if not chart_id:
        return None
    with _engine_meta().connect() as c:
        r = c.execute(select(RAMALAN).where(RAMALAN.c.chart_id == int(chart_id))).mappings().first()
    return dict(r) if r else None


# --- Isi tabel ------------------------------------------------------------------------------------
def baris_panjang(analitik: dict, sidik: str):
    """Hasil prediksi.analisis -> tabel panjang (satu baris per periode x seri)."""
    import pandas as pd

    xs, xr = analitik["x"], analitik["x_ramalan"]
    rows = []

    def tambah(label_x, urutan, seri, nilai):
        if nilai is not None:
            rows.append({"periode": str(label_x), "urutan": urutan, "seri": seri, "nilai": float(nilai),
                         "sidik": sidik})

    for u, s in analitik["seri"].items():
        for i, x in enumerate(xs):
            tambah(x, i, u, analitik["aktual"][u][i])
            if "tren" in s:
                tambah(x, i, f"Tren {u}", s["tren"]["nilai"][i])
        r = s.get("ramalan")
        if r:
            n = len(xs)
            tambah(xs[-1], n - 1, f"Ramalan {u}", analitik["aktual"][u][-1])     # garis menyambung
            for j, x in enumerate(xr):
                tambah(x, n + j, f"Ramalan {u}", r["nilai"][j])
                for k, nama in (("bawah80", "batas bawah 80%"), ("atas80", "batas atas 80%"),
                                ("bawah95", "batas bawah 95%"), ("atas95", "batas atas 95%")):
                    tambah(x, n + j, f"Ramalan {u} {nama}", r[k][j])
    return pd.DataFrame(rows, columns=["periode", "urutan", "seri", "nilai", "sidik"])


def _tulis(tabel: str, df) -> None:
    from sps_engine import klien as K, tabel as T
    k, db = K.klien(), K.nama_db()
    k.perintah(f"CREATE DATABASE IF NOT EXISTS {db}")
    T.isi_penuh(k, db, tabel, [df], ["sidik", "seri", "urutan"])


def _pastikan_rls(ds) -> None:
    """Satu aturan Base untuk semua dataset ramalan: baris hanya untuk lingkup akses yang sama."""
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    from superset.utils.core import RowLevelSecurityFilterType

    r = db.session.query(RowLevelSecurityFilter).filter_by(name=NAMA_RLS).one_or_none()
    if r is None:                                     # instalasi lama: pakai & ganti nama aturan yang sudah ada
        r = db.session.query(RowLevelSecurityFilter).filter_by(name=NAMA_RLS_LAMA).one_or_none()
        if r is not None:
            r.name = NAMA_RLS
    if r is None:
        r = RowLevelSecurityFilter(name=NAMA_RLS, filter_type=RowLevelSecurityFilterType.BASE,
                                   clause="sidik = '{{ sps_sidik() }}'",
                                   description="Dibuat Studio Visual: ramalan hanya terlihat oleh pegawai "
                                               "dengan lingkup akses sama dengan pembuatnya.")
        db.session.add(r)
    if ds not in r.tables:
        r.tables.append(ds)


PERINGATAN_SISTEM = ("**Dataset sistem ALDx**: hasil ramalan Studio Visual, diperbarui otomatis tiap malam. "
                     "Jangan diubah atau dihapus; ubah ramalannya dari chart di Studio Visual.")


def tandai_sistem(t) -> None:
    """U17: beri tanda peringatan (ikon ⚠ di daftar dataset) agar tidak dikira dataset biasa."""
    import json
    extra = json.loads(t.extra or "{}")
    if extra.get("warning_markdown") != PERINGATAN_SISTEM:
        extra["warning_markdown"] = PERINGATAN_SISTEM
        t.extra = json.dumps(extra)


def tandai_semua() -> str:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    daftar = db.session.query(SqlaTable).filter(SqlaTable.table_name.like("ramalan\\_\\_%", escape="\\")).all()
    for t in daftar:
        tandai_sistem(t)
    db.session.commit()
    return f"{len(daftar)} dataset ramalan ditandai sebagai dataset sistem"


def _daftarkan(tabel: str, asal, ds_id: int | None):
    from superset import db
    from superset.connectors.sqla.models import SqlMetric, SqlaTable, TableColumn
    from sps_engine import klien as K
    from sps_engine.ekstrak import _salin_akses, database_engine

    t = db.session.query(SqlaTable).get(ds_id) if ds_id else None
    if t is None:
        t = SqlaTable(table_name=tabel, schema=K.nama_db(), database=database_engine(),
                      description=f"Ramalan Studio dari '{asal.table_name}'.", owners=list(asal.owners or []))
        for nama, jenis in (("periode", "String"), ("urutan", "Int64"), ("seri", "String"),
                            ("nilai", "Float64"), ("sidik", "String")):
            t.columns.append(TableColumn(column_name=nama, type=jenis, groupby=nama != "nilai", filterable=True))
        t.metrics.append(SqlMetric(metric_name="nilai", expression="MAX(nilai)", verbose_name="Nilai",
                                    d3format="SMART_NUMBER"))
        db.session.add(t)
        db.session.flush()
    tandai_sistem(t)
    _pastikan_rls(t)
    _salin_akses(asal, t)
    db.session.commit()
    return t


# --- API untuk lembar.simpan & tugas harian ----------------------------------------------------------
def siapkan(asal, lembar, chart_id: int | None) -> tuple[int, str]:
    """Hitung & tulis ramalan untuk lembar ini. Kembalikan (dataset_id, tabel)."""
    import sps_akses
    from sps_studio import lembar as L

    hasil = L.jalankan(asal, lembar)
    an = hasil["analitik"]
    if not an or not any("ramalan" in s or "tren" in s for s in an["seri"].values()):
        raise L.alat.InputSalah("Data belum cukup untuk ramalan (minimal 4 periode).")
    dim = hasil["dimensi"][0]
    urut = {str(x): i for i, x in enumerate(an["x"])}
    an["aktual"] = {u: [None] * len(an["x"]) for u in an["seri"]}
    for b in hasil["baris"]:
        if str(b.get(dim)) in urut:
            for u in an["seri"]:
                an["aktual"][u][urut[str(b[dim])]] = b.get(u)

    lama = _milik_chart(chart_id)
    tabel = lama["tabel"] if lama else f"ramalan__{uuid.uuid4().hex[:10]}"
    try:
        _tulis(tabel, baris_panjang(an, sps_akses.sidik_akses()))
    except Exception as exc:  # noqa: BLE001
        raise L.alat.InputSalah("ALDx Engine tidak bisa dihubungi sehingga ramalan tidak dapat disimpan "
                                f"({str(exc).splitlines()[0][:120]}). Matikan Ramalan atau coba lagi.") from exc
    ds = _daftarkan(tabel, asal, lama["dataset_id"] if lama else None)
    return ds.id, tabel


def params_chart(lembar, ds) -> dict:
    """Params chart Superset (garis per seri) untuk dataset ramalan."""
    from sps_studio.lembar import SKEMA_WARNA
    return {"viz_type": "echarts_timeseries_line", "datasource": f"{ds.id}__table", "x_axis": "periode",
            "xAxisForceCategorical": True, "x_axis_sort_asc": True, "groupby": ["seri"], "metrics": ["nilai"],
            "row_limit": 10000, "color_scheme": SKEMA_WARNA, "show_legend": True, "rich_tooltip": True,
            "y_axis_format": "SMART_NUMBER", "markerEnabled": True, "markerSize": 4, "truncateXAxis": True,
            "adhoc_filters": [], "sps_studio": lembar.ke_dict()}


def catat(chart_id: int, asal_id: int, ds_id: int, tabel: str, lembar, oleh: str) -> None:
    lama = _milik_chart(chart_id)
    nilai = dict(chart_id=chart_id, dataset_asal_id=asal_id, dataset_id=ds_id, tabel=tabel,
                 spec=json.dumps(lembar.ke_dict()), oleh=oleh, diperbarui=datetime.now(), pesan=None)
    with _engine_meta().begin() as c:
        if lama:
            c.execute(update(RAMALAN).where(RAMALAN.c.id == lama["id"]).values(**nilai))
        else:
            c.execute(insert(RAMALAN).values(**nilai))


def segarkan_semua() -> int:
    """Hitung ulang semua ramalan sebagai pembuatnya (dipanggil tugas harian)."""
    from superset import db, security_manager
    from superset.utils.core import override_user
    from sps_studio import lembar as L

    jumlah = 0
    for r in daftar():
        user = security_manager.find_user(username=r["oleh"])
        try:
            if user is None:
                raise ValueError(f"user '{r['oleh']}' tidak ada")
            with override_user(user):
                asal, lb = L.dari_dict(json.loads(r["spec"]))
                siapkan(asal, lb, r["chart_id"])
            pesan = None
            jumlah += 1
        except Exception as exc:  # noqa: BLE001 - satu ramalan gagal tidak menghentikan yang lain
            db.session.rollback()
            pesan = str(exc).splitlines()[0][:300]
            log.warning("ALDx ramalan chart %s gagal disegarkan: %s", r["chart_id"], pesan)
        with _engine_meta().begin() as c:
            c.execute(update(RAMALAN).where(RAMALAN.c.id == r["id"]).values(diperbarui=datetime.now(), pesan=pesan))
    return jumlah
