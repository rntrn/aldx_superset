"""Pindah metadata versi lama (MySQL XAMPP / MariaDB) ke PostgreSQL, dan upload lama ke ALDx Engine.

Dipanggil oleh scripts/pindah-metadata.ps1 di dalam container superset:

    python /app/pythonpath/sps_pindah_meta.py salin    # metadata MySQL -> PostgreSQL
    python /app/pythonpath/sps_pindah_meta.py upload   # tabel database sps_upload -> ALDx Engine

Alur "salin" (sumber hanya DIBACA, jadi aman diulang):
    1. Baca revisi Alembic sumber.
    2. Bangun struktur PostgreSQL tepat di revisi itu (`superset db upgrade <revisi>`),
       sehingga kolom & tipe sama persis dengan sumber.
    3. Kosongkan tabel tujuan, salin semua baris per potongan (tipe diubah bila perlu:
       tinyint -> boolean, BINARY(16) -> UUID, tanggal 0000-00-00 -> NULL).
    4. Tabel tambahan SPS (sps_*) yang belum ada dibuat dari struktur sumber.
    5. Setel ulang SEQUENCE agar id baru melanjutkan id lama.
Setelah itu skrip PowerShell menjalankan `superset db upgrade` (ke versi terbaru) & `superset init`.
"""

from __future__ import annotations

import subprocess
import sys
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import mysql, postgresql

from sps_server.lingkungan import uri_metadata, uri_metadata_lama

POTONGAN = 2000
DILEWATI = {"alembic_version"}


def info(pesan: str) -> None:
    print(pesan, flush=True)


# --- Konversi nilai ---------------------------------------------------------------------------

def _tipe_umum(kolom: sa.Column) -> sa.types.TypeEngine:
    """Tipe MySQL -> tipe umum SQLAlchemy untuk membuat tabel tambahan di PostgreSQL."""
    t = kolom.type
    if isinstance(t, mysql.TINYINT) and getattr(t, "display_width", None) == 1:
        return sa.Boolean()
    if isinstance(t, (mysql.LONGTEXT, mysql.MEDIUMTEXT, mysql.TINYTEXT)):
        return sa.Text()
    if isinstance(t, (mysql.LONGBLOB, mysql.MEDIUMBLOB, mysql.TINYBLOB, mysql.BLOB)):
        return sa.LargeBinary()
    try:
        return t.as_generic()
    except NotImplementedError:
        return sa.Text()


def pengubah(kolom_tujuan: sa.Column):
    """Fungsi yang menyesuaikan satu nilai sumber ke tipe kolom tujuan PostgreSQL."""
    t = kolom_tujuan.type

    if isinstance(t, sa.Boolean):
        return lambda v: None if v is None else bool(int(v)) if not isinstance(v, bool) else v
    if isinstance(t, postgresql.UUID):
        def ke_uuid(v):
            if v is None:
                return None
            if isinstance(v, (bytes, bytearray)) and len(v) == 16:
                return str(uuid.UUID(bytes=bytes(v)))
            return str(uuid.UUID(str(v)))
        return ke_uuid
    if isinstance(t, (sa.DateTime, sa.Date)):
        return lambda v: None if isinstance(v, str) and v.startswith("0000") else v
    if isinstance(t, (sa.String, sa.Text)):
        def ke_teks(v):
            if isinstance(v, (bytes, bytearray)):
                v = bytes(v).decode("utf-8", "replace")
            return v.replace("\x00", "") if isinstance(v, str) else v
        return ke_teks
    if isinstance(t, sa.LargeBinary):
        return lambda v: v.encode() if isinstance(v, str) else v
    return lambda v: v


# --- Langkah "salin" ---------------------------------------------------------------------------

def revisi_sumber(sumber: sa.engine.Engine) -> str:
    with sumber.connect() as c:
        return c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()


def bangun_struktur(revisi: str) -> None:
    info(f"Membangun struktur PostgreSQL pada revisi {revisi} ...")
    subprocess.run(["superset", "db", "upgrade", revisi], check=True)


def salin_tabel(sumber, tujuan, t_sumber: sa.Table, t_tujuan: sa.Table) -> int:
    kolom = [k.name for k in t_tujuan.columns if k.name in t_sumber.c]
    ubah = {k: pengubah(t_tujuan.c[k]) for k in kolom}
    pilih = sa.select(*[t_sumber.c[k] for k in kolom])
    total = 0
    with sumber.connect().execution_options(stream_results=True) as cs, tujuan.begin() as ct:
        ct.execute(sa.text("SET session_replication_role = replica"))   # FK dicek setelah semua masuk
        hasil = cs.execute(pilih)
        while baris := hasil.fetchmany(POTONGAN):
            ct.execute(t_tujuan.insert(), [{k: ubah[k](r._mapping[k]) for k in kolom} for r in baris])
            total += len(baris)
    return total


def setel_sequence(tujuan) -> None:
    """Lanjutkan setiap SEQUENCE dari id terbesar.

    Dua bentuk: kolom SERIAL (default nextval) dan SEQUENCE bernama `<tabel>_id_seq`
    yang dipakai Flask-AppBuilder (ab_user, ab_role, ab_view_menu, ...).
    """
    sql = sa.text("""
        SELECT table_name, column_name, pg_get_serial_sequence(quote_ident(table_name), column_name) AS seq
        FROM information_schema.columns
        WHERE table_schema = 'public' AND column_default LIKE 'nextval(%'
        UNION
        SELECT c.table_name, c.column_name, s.sequence_name
        FROM information_schema.sequences s
        JOIN information_schema.columns c
          ON c.table_schema = 'public' AND c.column_name = 'id' AND s.sequence_name = c.table_name || '_id_seq'
        WHERE s.sequence_schema = 'public'""")
    with tujuan.begin() as c:
        for tabel, kolom, seq in c.execute(sql).all():
            if seq:
                c.execute(sa.text(
                    f'SELECT setval(:s, COALESCE((SELECT MAX("{kolom}") FROM "{tabel}"), 1), '
                    f'(SELECT MAX("{kolom}") FROM "{tabel}") IS NOT NULL)'), {"s": seq})


def salin() -> None:
    uri_lama = uri_metadata_lama()
    if not uri_lama:
        sys.exit("Pengaturan metadata lama (MYSQL_*) tidak ada di .env; tidak ada yang dipindah.")
    sumber = sa.create_engine(uri_lama, pool_pre_ping=True)
    tujuan = sa.create_engine(uri_metadata())

    bangun_struktur(revisi_sumber(sumber))

    meta_s, meta_t = sa.MetaData(), sa.MetaData()
    meta_s.reflect(bind=sumber)
    # Tabel tambahan ALDx yang belum ada di tujuan: buat dari struktur sumber.
    meta_t.reflect(bind=tujuan)
    baru = [t for n, t in meta_s.tables.items() if n not in meta_t.tables and n not in DILEWATI]
    if baru:
        meta_baru = sa.MetaData()
        for t in baru:
            sa.Table(t.name, meta_baru, *[
                sa.Column(k.name, _tipe_umum(k), primary_key=k.primary_key, nullable=k.nullable,
                          autoincrement=k.autoincrement if k.primary_key else False)
                for k in t.columns])
        meta_baru.create_all(bind=tujuan)
        info(f"Tabel tambahan dibuat: {', '.join(t.name for t in baru)}")
        meta_t = sa.MetaData()
        meta_t.reflect(bind=tujuan)

    nama = [t.name for t in meta_t.sorted_tables if t.name in meta_s.tables and t.name not in DILEWATI]
    with tujuan.begin() as c:   # buang baris bawaan migrasi (mis. tema awal) agar id tidak bentrok
        c.execute(sa.text("TRUNCATE " + ", ".join(f'"{n}"' for n in nama) + " RESTART IDENTITY CASCADE"))
    for n in nama:
        jumlah = salin_tabel(sumber, tujuan, meta_s.tables[n], meta_t.tables[n])
        if jumlah:
            info(f"  {n:<40} {jumlah:>8} baris")
    setel_sequence(tujuan)
    info("Metadata selesai disalin ke PostgreSQL.")


# --- Langkah "upload" --------------------------------------------------------------------------

def upload() -> None:
    """Pindahkan dataset di database MySQL `sps_upload` (versi lama) ke ALDx Engine."""
    import pandas as pd
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        from superset import db
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.core import Database
        from sps_engine import klien as K, tabel as T
        from sps_engine.ekstrak import database_engine

        lama = [d for d in db.session.query(Database).all() if "/sps_upload" in (d.sqlalchemy_uri or "")]
        uri_lama = uri_metadata_lama()
        if not lama or not uri_lama:
            info("Tidak ada data upload lama (sps_upload). Lewati.")
            return
        sumber = sa.create_engine(uri_lama.rsplit("/", 1)[0] + "/sps_upload?charset=utf8mb4")
        eng, kl, db_eng = database_engine(), K.klien(), K.nama_db()
        for d in lama:
            for t in db.session.query(SqlaTable).filter_by(database_id=d.id).all():
                if t.sql:   # dataset virtual (SQL) tidak bisa dipindah otomatis
                    info(f"  LEWATI dataset SQL '{t.table_name}' (buat ulang di ALDx Engine)")
                    continue
                nama = T.nama_aman(t.table_name)
                potongan = pd.read_sql_table(t.table_name, sumber, chunksize=50_000)
                baris, _ = T.isi_penuh(kl, db_eng, nama, potongan, urut=[])
                t.database, t.schema, t.table_name = eng, db_eng, nama
                db.session.commit()
                try:
                    t.fetch_metadata()   # baca ulang daftar kolom dari engine
                except Exception as e:   # noqa: BLE001 - data sudah pindah; kolom bisa disinkron manual
                    info(f"  (kolom '{nama}' belum terbaca: {e.__class__.__name__}; buka dataset > Sinkron kolom)")
                info(f"  {nama:<40} {baris:>8} baris -> ALDx Engine")
        info("Upload lama selesai dipindah. Koneksi 'sps_upload' lama boleh dihapus di menu Database.")


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else ""
    {"salin": salin, "upload": upload}.get(perintah, lambda: sys.exit(__doc__))()
