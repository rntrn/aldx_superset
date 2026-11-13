"""Alat Asisten AI untuk TABEL database (bukan hanya dataset): cari_tabel & daftarkan_tabel.

Contoh: "scan di sps_engine semua tabel berawalan data_penerbangan" -> cari_tabel(pola="data_penerbangan")
        -> daftar tabel + kolom + jumlah baris (ALDx Engine) + apakah sudah jadi dataset
        -> "daftarkan semuanya" -> daftarkan_tabel(...) -> dataset baru siap dianalisis/digabung.

Hak akses:
    - melihat tabel mentah butuh akses ke database itu (Admin, atau role dengan database_access/all_database_access);
      pengguna lain hanya melihat tabel yang SUDAH menjadi dataset yang boleh ia akses
    - mendaftarkan dataset butuh izin membuat dataset (can_write Dataset)
"""

from __future__ import annotations

import fnmatch

from sps_ai import alat

MAKS_TABEL = 60          # tabel yang dikembalikan
MAKS_KOLOM_RINCI = 25    # tabel yang kolomnya dibaca (tiap tabel = satu kueri metadata)
MAKS_DAFTAR = 30         # tabel per pendaftaran


def _database(database: str | int | None):
    """Database menurut id/nama; tanpa nilai = ALDx Engine bila ada, selain itu satu-satunya database."""
    from superset import db
    from superset.models.core import Database

    from sps_engine import ekstrak
    semua = db.session.query(Database).all()
    if database not in (None, ""):
        for d in semua:
            if str(d.id) == str(database) or d.database_name.lower() == str(database).lower() \
                    or str(database).lower() in d.database_name.lower():
                return d
        raise alat.InputSalah(f"Database '{database}' tidak ditemukan. Pilih: {', '.join(d.database_name for d in semua)}.")
    engine = [d for d in semua if ekstrak.adalah_engine(d)]
    if engine or len(semua) == 1:
        return (engine or semua)[0]
    raise alat.InputSalah(f"Sebutkan database: {', '.join(d.database_name for d in semua)}.")


def _boleh_mentah(d) -> bool:
    from superset import security_manager as sm
    return sm.is_admin() or sm.can_access_database(d) or sm.can_access("all_database_access", "all_database_access")


def _cocok(nama: str, pola: str) -> bool:
    if not pola:
        return True
    p = pola.lower()
    return fnmatch.fnmatch(nama.lower(), p) if any(c in p for c in "*?") else p in nama.lower()


def _baris_engine(d, skema: str) -> dict[str, int]:
    """Jumlah baris per tabel dari metadata ClickHouse (tanpa memindai data). {} untuk database lain."""
    from sps_engine import ekstrak
    if not ekstrak.adalah_engine(d):
        return {}
    try:
        df = d.get_df(f"SELECT name, total_rows FROM system.tables WHERE database = '{skema.replace(chr(39), '')}'")
        return {str(n): int(r or 0) for n, r in zip(df["name"], df["total_rows"])}
    except Exception:  # noqa: BLE001 - jumlah baris hanya informasi tambahan
        return {}


def cari_tabel(pola: str = "", database: str | int | None = None, skema: str | None = None) -> dict:
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable
    from superset.sql.parse import Table

    d = _database(database)
    skema = skema or (d.get_default_schema(None) if hasattr(d, "get_default_schema") else None) or ""
    dataset = {(t.schema or "", t.table_name): t for t in db.session.query(SqlaTable).filter_by(database_id=d.id)
               if not t.sql}
    if not _boleh_mentah(d):                    # tanpa akses database: hanya dataset yang boleh diakses
        cocok = [t for (s, n), t in dataset.items() if _cocok(n, pola) and sm.can_access_datasource(t)]
        return {"database": d.database_name, "skema": skema, "hanya_dataset": True,
                "catatan": "Anda tidak punya akses ke seluruh database ini; yang tampil hanya tabel yang sudah menjadi dataset.",
                "tabel": [{"nama": t.table_name, "dataset_id": t.id, "kolom": [c.column_name for c in t.columns][:40]}
                          for t in cocok[:MAKS_TABEL]]}
    nama = sorted(n for n, _, _ in d.get_all_table_names_in_schema(None, skema) if _cocok(n, pola))
    baris = _baris_engine(d, skema)
    hasil = []
    for i, n in enumerate(nama[:MAKS_TABEL]):
        item = {"nama": n, "dataset_id": getattr(dataset.get((skema, n)), "id", None)}
        if n in baris:
            item["baris"] = baris[n]
        if i < MAKS_KOLOM_RINCI:
            try:
                item["kolom"] = [f"{c['column_name']} ({str(c['type']).split('(')[0]})" for c in d.get_columns(Table(n, skema))][:40]
            except Exception:  # noqa: BLE001 - tabel tanpa izin baca/terkunci: lewati rinciannya
                item["kolom"] = []
        hasil.append(item)
    return {"database": d.database_name, "database_id": d.id, "skema": skema, "jumlah": len(nama),
            "tabel": hasil, **({"catatan": f"Ditampilkan {MAKS_TABEL} dari {len(nama)} tabel; persempit pola."}
                               if len(nama) > MAKS_TABEL else {})}


def daftarkan_tabel(tabel: list[str], database: str | int | None = None, skema: str | None = None) -> dict:
    """Jadikan tabel database sebagai dataset (yang sudah ada dipakai ulang). Kembalikan id dataset."""
    from flask import g
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable

    if not sm.can_access("can_write", "Dataset"):
        raise alat.IzinDitolak("Anda belum punya izin membuat dataset.")
    d = _database(database)
    if not _boleh_mentah(d):
        raise alat.IzinDitolak(f"Anda tidak punya akses ke database '{d.database_name}'.")
    skema = skema or (d.get_default_schema(None) if hasattr(d, "get_default_schema") else None) or ""
    ada = set(n for n, _, _ in d.get_all_table_names_in_schema(None, skema))
    hasil, dilewati = [], []
    for n in list(dict.fromkeys(str(x) for x in tabel))[:MAKS_DAFTAR]:
        if n not in ada:
            dilewati.append(f"{n}: tidak ada di {d.database_name}.{skema}")
            continue
        t = db.session.query(SqlaTable).filter_by(database_id=d.id, schema=skema or None, table_name=n, sql=None).first()
        baru = t is None
        if baru:
            t = SqlaTable(table_name=n, schema=skema or None, database=d, owners=[g.user] if getattr(g, "user", None) else [])
            db.session.add(t)
            db.session.flush()
            t.fetch_metadata()
        hasil.append({"nama": n, "dataset_id": t.id, "baru": baru, "kolom": len(t.columns)})
    db.session.commit()
    return {"database": d.database_name, "skema": skema, "dataset": hasil, "dilewati": dilewati}
