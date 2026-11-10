"""Ekstrak: salinan dataset sumber (Oracle/ClickHouse DMP/MySQL) di ALDx Engine.

Siklus:
    buat()       daftarkan ekstrak (status "baru") -> penyegaran pertama dijadwalkan
    segarkan()   baca sumber per potongan -> isi tabel engine (penuh: tukar atomik,
                 inkremental: hanya baris dengan kolom_inkremental > nilai terakhir)
                 -> daftarkan/perbarui dataset Superset "ekstrak__<nama>"
    jatuh_tempo()  dipanggil penjadwal tiap 5 menit -> ekstrak yang waktunya tiba

Keamanan (sama seperti dataset sumber):
    - aturan hak akses (RLS) sumber juga dipasang ke dataset ekstrak (kolom sama)
    - role yang boleh memakai sumber juga boleh memakai ekstrak
    - sumber dibaca utuh oleh sistem; pembatasan per pegawai terjadi saat query ekstrak

Tabel metadata: sps_ekstrak (daftar ekstrak) & sps_ekstrak_log (riwayat penyegaran).
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text, column, delete, insert,
                        literal, select, text, update)

from sps_engine import klien as K, tabel as T

log = logging.getLogger(__name__)

POTONGAN = 50_000                       # baris per potongan baca/tulis
NAMA_DB_ENGINE = "ALDx Engine (ClickHouse)"
NAMA_DB_ENGINE_LAMA = ("SPS Engine (ClickHouse)",)          # nama sebelum ganti nama ke ALDx (dipindah otomatis)


def _ganti_nama_izin(lama: str, baru: str) -> None:
    """Izin skema "[nama lama].[skema]" tidak ikut diganti Superset; ganti di sini agar peran tetap berhak."""
    from superset import db, security_manager as sm
    for vm in db.session.query(sm.viewmenu_model).filter(sm.viewmenu_model.name.like(f"[{lama}].%")):
        vm.name = f"[{baru}]" + vm.name[len(lama) + 2:]


def adalah_engine(database) -> bool:
    """True bila koneksi ini ALDx Engine (nama baru atau nama lama yang belum dipindah)."""
    return database is not None and database.database_name in (NAMA_DB_ENGINE, *NAMA_DB_ENGINE_LAMA)
JENIS_JADWAL = ("manual", "jam", "harian", "mingguan")
POLA_JINJA = re.compile(r"{{|{%")

_meta = MetaData()
EKSTRAK = Table(
    "sps_ekstrak", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nama", String(120)), Column("dataset_asal_id", Integer), Column("dataset_id", Integer),
    Column("tabel", String(160)), Column("mode", String(20)), Column("kolom_inkremental", String(120)),
    Column("nilai_terakhir", Text), Column("jadwal", Text), Column("berikutnya", DateTime),
    Column("status", String(20)), Column("pesan", Text), Column("mulai", DateTime), Column("selesai", DateTime),
    Column("durasi_detik", Integer), Column("baris_terakhir", Integer), Column("baris_total", Integer),
    Column("ukuran_byte", Integer), Column("chart_dipindah", Text), Column("dibuat", DateTime),
    Column("oleh", String(64)))
LOG = Table(
    "sps_ekstrak_log", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ekstrak_id", Integer), Column("mulai", DateTime), Column("selesai", DateTime),
    Column("status", String(20)), Column("baris", Integer), Column("pemicu", String(40)), Column("pesan", Text))


class GalatEkstrak(ValueError):
    """Masukan/keadaan ekstrak tidak sah (pesan untuk pengguna)."""


# --- Basis data metadata ------------------------------------------------------------------
def _engine_meta():
    from superset import db
    _meta.create_all(bind=db.engine, checkfirst=True)
    return db.engine


def _baris(r) -> dict:
    d = dict(r)
    for k in ("berikutnya", "mulai", "selesai", "dibuat"):
        if d.get(k):
            d[k] = d[k].isoformat(sep=" ", timespec="seconds")
    d["jadwal"] = json.loads(d["jadwal"] or "{}")
    d["chart_dipindah"] = json.loads(d["chart_dipindah"] or "[]")
    return d


def daftar() -> list[dict]:
    with _engine_meta().connect() as c:
        return [_baris(r) for r in c.execute(select(EKSTRAK).order_by(EKSTRAK.c.nama)).mappings()]


def ambil(ekstrak_id: int) -> dict:
    with _engine_meta().connect() as c:
        r = c.execute(select(EKSTRAK).where(EKSTRAK.c.id == int(ekstrak_id))).mappings().first()
    if r is None:
        raise GalatEkstrak("Ekstrak tidak ditemukan.")
    return _baris(r)


def riwayat(ekstrak_id: int, batas: int = 30) -> list[dict]:
    with _engine_meta().connect() as c:
        rows = c.execute(select(LOG).where(LOG.c.ekstrak_id == int(ekstrak_id))
                         .order_by(LOG.c.id.desc()).limit(batas)).mappings()
        return [{**r, "mulai": r["mulai"].isoformat(sep=" ", timespec="seconds"),
                 "selesai": r["selesai"].isoformat(sep=" ", timespec="seconds") if r["selesai"] else None}
                for r in rows]


def _ubah(ekstrak_id: int, **nilai) -> None:
    with _engine_meta().begin() as c:
        c.execute(update(EKSTRAK).where(EKSTRAK.c.id == int(ekstrak_id)).values(**nilai))


# --- Jadwal ------------------------------------------------------------------------------------
def periksa_jadwal(j: dict) -> dict:
    jenis = str(j.get("jenis") or "manual")
    if jenis not in JENIS_JADWAL:
        raise GalatEkstrak(f"Jadwal harus salah satu: {', '.join(JENIS_JADWAL)}.")
    hasil = {"jenis": jenis}
    if jenis == "jam":
        hasil["setiap"] = max(1, min(24, int(j.get("setiap") or 1)))
    if jenis in ("harian", "mingguan"):
        hasil["jam"] = max(0, min(23, int(j.get("jam") or 2)))
    if jenis == "mingguan":
        hasil["hari"] = max(0, min(6, int(j.get("hari") or 0)))       # 0 = Senin
    return hasil


def berikutnya(j: dict, dari: datetime) -> datetime | None:
    """Waktu penyegaran berikutnya setelah `dari` (None = manual)."""
    jenis = j.get("jenis", "manual")
    if jenis == "manual":
        return None
    if jenis == "jam":
        return dari.replace(minute=0, second=0, microsecond=0) + timedelta(hours=j.get("setiap", 1))
    kandidat = dari.replace(hour=j.get("jam", 2), minute=0, second=0, microsecond=0)
    if jenis == "harian":
        return kandidat if kandidat > dari else kandidat + timedelta(days=1)
    selisih = (j.get("hari", 0) - kandidat.weekday()) % 7
    kandidat += timedelta(days=selisih)
    return kandidat if kandidat > dari else kandidat + timedelta(days=7)


def jatuh_tempo(sekarang: datetime | None = None) -> list[int]:
    sekarang = sekarang or datetime.now()
    with _engine_meta().connect() as c:
        return [r.id for r in c.execute(select(EKSTRAK.c.id).where(
            EKSTRAK.c.berikutnya.isnot(None), EKSTRAK.c.berikutnya <= sekarang, EKSTRAK.c.status != "berjalan"))]


# --- Sumber -----------------------------------------------------------------------------------
def _dataset(dataset_id: int):
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    t = db.session.query(SqlaTable).get(int(dataset_id))
    if t is None:
        raise GalatEkstrak(f"Dataset {dataset_id} tidak ada.")
    return t


def _kolom_sumber(t) -> list[str]:
    return [c.column_name for c in t.columns if c.is_active is not False and not c.expression]


def periksa_sumber(t) -> None:
    if adalah_engine(t.database) and not (t.sql or "").strip():
        # Tabel fisik engine tidak perlu disalin. Dataset VIRTUAL di engine boleh: hasil SQL-nya
        # disimpan jadi tabel (lebih cepat, mis. "Simpan jadi dataset > Fisik" di Kueri Visual).
        raise GalatEkstrak("Dataset ini sudah berupa tabel di ALDx Engine.")
    if t.sql and POLA_JINJA.search(t.sql):
        raise GalatEkstrak("Dataset memakai template filter ({{ … }}) sehingga isinya berubah per filter. "
                           "Buka SQL-nya di SQL Lab, hapus bagian {{ … }}, simpan sebagai dataset baru, "
                           "lalu ekstrak dataset baru itu.")
    if not _kolom_sumber(t):
        raise GalatEkstrak("Dataset belum punya kolom; buka dan sinkronkan kolomnya dulu.")


def _query_sumber(t, kolom_inkremental: str | None = None, nilai: Any = None):
    """SELECT seluruh kolom sumber (tanpa RLS: ekstrak dibaca utuh oleh sistem)."""
    from sqlalchemy import table
    kolom = _kolom_sumber(t)
    if t.sql:
        dari = text(t.sql.replace(":", r"\:")).columns(*[column(k) for k in kolom]).subquery("sumber")
    else:
        dari = table(t.table_name, *[column(k) for k in kolom], schema=t.schema or None).alias("sumber")
    q = select(*[dari.c[k] for k in kolom])
    if kolom_inkremental and nilai is not None:
        q = q.where(dari.c[kolom_inkremental] > literal(nilai))
    return str(q.compile(dialect=t.database.get_dialect(), compile_kwargs={"literal_binds": True}))


def _potongan(t, sql: str):
    """Baca sumber per potongan (hemat memori untuk tabel besar)."""
    import pandas as pd
    with t.database.get_sqla_engine(catalog=t.catalog, schema=t.schema) as eng:
        with eng.connect() as conn:
            yield from pd.read_sql(text(sql), conn, chunksize=POTONGAN)


# --- Dataset Superset untuk ekstrak -----------------------------------------------------------------
def database_engine():
    """Koneksi Superset ke ALDx Engine (dibuat bila belum ada)."""
    from superset import db
    from superset.models.core import Database
    from sps_server import lingkungan

    d = db.session.query(Database).filter_by(database_name=NAMA_DB_ENGINE).one_or_none()
    if d is None:                              # instalasi lama: ganti nama (izin ikut diganti oleh Superset)
        d = db.session.query(Database).filter(Database.database_name.in_(NAMA_DB_ENGINE_LAMA)).first()
        if d is not None:
            lama, d.database_name = d.database_name, NAMA_DB_ENGINE
            _ganti_nama_izin(lama, NAMA_DB_ENGINE)
    if d is None:
        d = Database(database_name=NAMA_DB_ENGINE, expose_in_sqllab=True, allow_dml=False)
        db.session.add(d)
    d.set_sqlalchemy_uri(lingkungan.engine().uri)
    db.session.commit()
    return d


def _tipe_superset(tipe_ch: str) -> tuple[str, bool]:
    t = tipe_ch.replace("LowCardinality(", "").replace("Nullable(", "").rstrip(")")
    return t, t.startswith(("DateTime", "Date"))


def _daftarkan_dataset(baris: dict, asal, tipe: dict[str, str]):
    """Buat/perbarui dataset Superset untuk tabel ekstrak + salin RLS, akses & metrik dari sumber."""
    from superset import db
    from superset.connectors.sqla.models import SqlMetric, SqlaTable, TableColumn

    eng = database_engine()
    t = db.session.query(SqlaTable).get(baris["dataset_id"]) if baris.get("dataset_id") else None
    if t is None:
        t = SqlaTable(table_name=baris["tabel"], schema=K.nama_db(), database=eng,
                      description=f"Ekstrak dari '{asal.table_name}' ({asal.database.database_name}).",
                      owners=list(asal.owners or []))
        db.session.add(t)
    ada = {c.column_name for c in t.columns}
    for nama, tch in tipe.items():
        if nama not in ada:
            jenis, waktu = _tipe_superset(tch)
            t.columns.append(TableColumn(column_name=nama, type=jenis, is_dttm=waktu, groupby=True, filterable=True))
    metrik_ada = {m.metric_name for m in t.metrics}
    for m in asal.metrics:                        # rumus disalin apa adanya (cek bila memakai fungsi khas Oracle)
        if m.metric_name not in metrik_ada:
            t.metrics.append(SqlMetric(metric_name=m.metric_name, expression=m.expression,
                                        verbose_name=m.verbose_name, d3format=m.d3format))
    db.session.flush()
    _salin_rls(asal, t)
    _salin_akses(asal, t)
    db.session.commit()
    return t


def _salin_rls(asal, baru) -> None:
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    for r in db.session.query(RowLevelSecurityFilter).all():
        if asal in r.tables and baru not in r.tables:
            r.tables.append(baru)                 # aturan & kolom sama persis -> filter sama


def _salin_akses(asal, baru) -> None:
    from superset import security_manager as sm
    pv_asal = sm.find_permission_view_menu("datasource_access", asal.get_perm())
    pv_baru = sm.add_permission_view_menu("datasource_access", baru.get_perm())
    for role in sm.get_all_roles():
        if pv_asal in role.permissions and pv_baru not in role.permissions:
            sm.add_permission_role(role, pv_baru)


def _kolom_rls(t) -> list[str]:
    """Kolom hak akses sumber -> dipakai sebagai urutan penyimpanan tabel ekstrak."""
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    kolom = {c.column_name.lower(): c.column_name for c in t.columns}
    hasil = []
    for r in db.session.query(RowLevelSecurityFilter).all():
        if t in r.tables:
            for _, k in re.findall(r"(\w+)\s*=\s*'([^']*)'", r.clause or ""):
                if k.lower() in kolom and kolom[k.lower()] not in hasil:
                    hasil.append(kolom[k.lower()])
    return hasil


# --- Operasi -------------------------------------------------------------------------------------
def buat(dataset_asal_id: int, nama: str, mode: str, kolom_inkremental: str | None, jadwal: dict, oleh: str) -> dict:
    asal = _dataset(dataset_asal_id)
    periksa_sumber(asal)
    if mode not in ("penuh", "inkremental"):
        raise GalatEkstrak("Mode harus 'penuh' atau 'inkremental'.")
    if mode == "inkremental":
        kolom = {k.lower(): k for k in _kolom_sumber(asal)}
        if not kolom_inkremental or kolom_inkremental.lower() not in kolom:
            raise GalatEkstrak("Pilih kolom inkremental (mis. tanggal/periode/ID yang selalu naik).")
        kolom_inkremental = kolom[kolom_inkremental.lower()]
    nama = T.nama_aman(nama or asal.table_name).lower()
    tabel = f"ekstrak__{nama}"[:120]
    with _engine_meta().connect() as c:
        if c.execute(select(EKSTRAK.c.id).where(EKSTRAK.c.tabel == tabel)).first():
            raise GalatEkstrak(f"Ekstrak '{nama}' sudah ada.")
    j = periksa_jadwal(jadwal or {})
    with _engine_meta().begin() as c:
        hasil = c.execute(insert(EKSTRAK).values(
            nama=nama, dataset_asal_id=asal.id, tabel=tabel, mode=mode, kolom_inkremental=kolom_inkremental,
            jadwal=json.dumps(j), berikutnya=datetime.now(), status="baru", dibuat=datetime.now(), oleh=oleh,
            chart_dipindah="[]"))
        baru = hasil.inserted_primary_key[0]
    return ambil(baru)                          # dibaca setelah transaksi selesai (commit)


def segarkan(ekstrak_id: int, pemicu: str = "manual", penuh: bool = False) -> dict:
    """Jalankan penyegaran (dipanggil tugas backgrounder)."""
    e = ambil(ekstrak_id)
    if e["status"] == "berjalan":
        raise GalatEkstrak("Penyegaran sedang berjalan.")
    mulai = datetime.now()
    t0 = time.monotonic()
    _ubah(ekstrak_id, status="berjalan", mulai=mulai, pesan=None)
    k, db_engine = K.klien(), K.nama_db()
    try:
        k.perintah(f"CREATE DATABASE IF NOT EXISTS {db_engine}")
        asal = _dataset(e["dataset_asal_id"])
        periksa_sumber(asal)
        tambah = e["mode"] == "inkremental" and not penuh and e["nilai_terakhir"] and T.ada(k, db_engine, e["tabel"])
        nilai_lama = json.loads(e["nilai_terakhir"]) if tambah else None
        kolom_ink = next((c for c in asal.columns if c.column_name == e["kolom_inkremental"]), None)
        if isinstance(nilai_lama, str) and kolom_ink is not None and kolom_ink.is_temporal:
            nilai_lama = datetime.fromisoformat(nilai_lama)      # dibandingkan sebagai tanggal di sumber
        sql = _query_sumber(asal, e["kolom_inkremental"] if tambah else None, nilai_lama)
        from sps_server import batas, penyimpanan          # batas data: Pusat Kendali › Batas data
        atur = penyimpanan.nilai_semua()
        batas.periksa_kuota_engine(atur)
        maks_baris = batas.berlaku(atur, "ekstrak.baris_maks")
        # nilai terakhir disimpan apa adanya (tanggal sebagai teks ISO) agar bisa dibandingkan
        maks = {"nilai": json.loads(e["nilai_terakhir"]) if tambah else None}

        def lacak(potongan):
            potongan = batas.batasi_baris(potongan, maks_baris, f"Ekstrak '{e['nama']}'",
                                          awal=int(e.get("baris_total") or 0) if tambah else 0)
            for df in potongan:
                if e["kolom_inkremental"] and e["kolom_inkremental"] in df and len(df):
                    m = df[e["kolom_inkremental"]].max()
                    m = m.isoformat() if hasattr(m, "isoformat") else (m.item() if hasattr(m, "item") else m)
                    maks["nilai"] = m if maks["nilai"] is None or m > maks["nilai"] else maks["nilai"]
                yield df

        if tambah:
            tipe = T.tipe_tabel(k, db_engine, e["tabel"])
            baris = T.isi_tambah(k, db_engine, e["tabel"], lacak(_potongan(asal, sql)), tipe)
        else:
            baris, tipe = T.isi_penuh(k, db_engine, e["tabel"], lacak(_potongan(asal, sql)), _kolom_rls(asal))
        ds = _daftarkan_dataset(e, asal, tipe)
        st = T.statistik(k, db_engine, e["tabel"])
        selesai = datetime.now()
        _ubah(ekstrak_id, status="siap", selesai=selesai, durasi_detik=int(time.monotonic() - t0),
              baris_terakhir=baris, baris_total=st["baris"], ukuran_byte=st["ukuran_byte"], dataset_id=ds.id,
              nilai_terakhir=json.dumps(maks["nilai"], default=str),
              berikutnya=berikutnya(e["jadwal"], selesai))
        _catat(ekstrak_id, mulai, "siap", baris, pemicu, f"{'Tambahan' if tambah else 'Penuh'}: {baris} baris")
        log.info("ALDx ekstrak %s: %s baris (%s)", e["nama"], baris, "tambahan" if tambah else "penuh")
    except Exception as exc:  # noqa: BLE001 - simpan galat agar terlihat di Pusat Kendali
        from superset import db
        db.session.rollback()
        log.exception("ALDx ekstrak %s gagal", e["nama"])
        pesan = str(exc).split("\n")[0][:500]
        _ubah(ekstrak_id, status="gagal", selesai=datetime.now(), pesan=pesan,
              durasi_detik=int(time.monotonic() - t0), berikutnya=berikutnya(e["jadwal"], datetime.now()))
        _catat(ekstrak_id, mulai, "gagal", 0, pemicu, pesan)
    return ambil(ekstrak_id)


def _catat(ekstrak_id, mulai, status, baris, pemicu, pesan) -> None:
    with _engine_meta().begin() as c:
        c.execute(insert(LOG).values(ekstrak_id=ekstrak_id, mulai=mulai, selesai=datetime.now(), status=status,
                                     baris=baris, pemicu=pemicu, pesan=pesan))


def ubah_jadwal(ekstrak_id: int, jadwal: dict) -> dict:
    j = periksa_jadwal(jadwal)
    _ubah(ekstrak_id, jadwal=json.dumps(j), berikutnya=berikutnya(j, datetime.now()))
    return ambil(ekstrak_id)


# --- Pindahkan chart ke ekstrak (chart langsung memakai ekstrak) ---------------------------------
def _ganti_sumber_chart(chart_ids: list[int], dari: int, ke: int) -> list[int]:
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    dipindah = []
    for c in db.session.query(Slice).filter(Slice.id.in_(chart_ids)).all():
        if c.datasource_id != dari:
            continue
        p = json.loads(c.params or "{}")
        p["datasource"] = f"{ke}__table"
        if "sps_studio" in p:
            p["sps_studio"]["dataset_id"] = ke
        c.datasource_id, c.params, c.query_context = ke, json.dumps(p), None
        dipindah.append(c.id)
    for d in db.session.query(Dashboard).all():               # target filter dashboard ikut pindah
        meta = json.loads(d.json_metadata or "{}")
        ubah = False
        for f in meta.get("native_filter_configuration") or []:
            for tg in f.get("targets") or []:
                if tg.get("datasetId") == dari and set(f.get("chartsInScope") or []) & set(dipindah):
                    tg["datasetId"], ubah = ke, True
        if ubah:
            d.json_metadata = json.dumps(meta)
    db.session.commit()
    return dipindah


def pindahkan_chart(ekstrak_id: int) -> dict:
    from superset import db
    from superset.models.slice import Slice
    e = ambil(ekstrak_id)
    if not e["dataset_id"]:
        raise GalatEkstrak("Ekstrak belum pernah berhasil disegarkan.")
    ids = [c.id for c in db.session.query(Slice).filter_by(datasource_id=e["dataset_asal_id"]).all()]
    dipindah = _ganti_sumber_chart(ids, e["dataset_asal_id"], e["dataset_id"])
    _ubah(ekstrak_id, chart_dipindah=json.dumps(sorted(set(e["chart_dipindah"]) | set(dipindah))))
    return {"dipindah": len(dipindah)}


def kembalikan_chart(ekstrak_id: int) -> dict:
    e = ambil(ekstrak_id)
    n = _ganti_sumber_chart(e["chart_dipindah"], e["dataset_id"], e["dataset_asal_id"])
    _ubah(ekstrak_id, chart_dipindah="[]")
    return {"dikembalikan": len(n)}


def hapus(ekstrak_id: int) -> None:
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.slice import Slice
    e = ambil(ekstrak_id)
    if e["dataset_id"] and db.session.query(Slice).filter_by(datasource_id=e["dataset_id"]).count():
        raise GalatEkstrak("Masih ada chart yang memakai ekstrak ini. Kembalikan chart ke sumber asli dulu.")
    T.hapus(K.klien(), K.nama_db(), e["tabel"])
    if e["dataset_id"]:
        t = db.session.query(SqlaTable).get(e["dataset_id"])
        if t is not None:
            db.session.delete(t)
            db.session.commit()
    with _engine_meta().begin() as c:
        c.execute(delete(LOG).where(LOG.c.ekstrak_id == ekstrak_id))
        c.execute(delete(EKSTRAK).where(EKSTRAK.c.id == ekstrak_id))
