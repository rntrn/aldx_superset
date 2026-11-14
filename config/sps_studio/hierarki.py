"""Hierarki dimensi Studio Visual: beberapa kolom bertingkat dipakai seperti satu kolom.

Contoh: Wilayah = provinsi > kabupaten > kecamatan > kelurahan. Di rak, hierarki tampil di level teratas
(teragregasi); pengguna menelusuri ke level berikutnya (semua nilai) atau ke dalam satu nilai (klik di chart).
Penelusuran dikerjakan di browser: kolom aktif = level saat ini, jalur nilai = filter tambahan. Server hanya
menyimpan definisinya per dataset (dipakai semua orang yang boleh membuka dataset itu).

    GET  /studio/api/hierarki/<dataset_id>              daftar hierarki dataset
    POST /studio/api/hierarki/<dataset_id>              {"nama": "Wilayah", "kolom": ["provinsi", "kabupaten", ...]}
    POST /studio/api/hierarki/<dataset_id>/hapus        {"nama": "Wilayah"}
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, select

from sps_ai import alat

MAKS_LEVEL = 8
_meta = MetaData()
TABEL = Table("sps_hierarki", _meta,
              Column("dataset_id", Integer, primary_key=True), Column("nama", String(80), primary_key=True),
              Column("kolom", Text), Column("pembuat", String(128)), Column("diubah", DateTime))


def _db():
    from superset import db
    TABEL.create(bind=db.engine, checkfirst=True)
    return db


def daftar(dataset_id: int) -> list[dict]:
    t = alat._dataset(dataset_id)                            # cek akses dataset
    ada = {c.column_name for c in t.columns}
    baris = _db().session.execute(select(TABEL).where(TABEL.c.dataset_id == t.id).order_by(TABEL.c.nama)).mappings()
    hasil = []
    for b in baris:
        kolom = [k for k in json.loads(b["kolom"] or "[]") if k in ada]     # kolom yang sudah dihapus dilewati
        if len(kolom) >= 2:
            hasil.append({"nama": b["nama"], "kolom": kolom, "pembuat": b["pembuat"]})
    return hasil


def _boleh_ubah() -> None:
    from superset import security_manager
    if not security_manager.can_access("can_write", "Chart"):
        raise alat.IzinDitolak("Membuat hierarki butuh izin membuat chart (role Alpha/Admin).")


def simpan(dataset_id: int, nama: str, kolom: list[str]) -> dict:
    from flask import g
    _boleh_ubah()
    t = alat._dataset(dataset_id)
    nama = str(nama or "").strip()[:80]
    if not nama:
        raise alat.InputSalah("Beri nama hierarki, mis. Wilayah.")
    kolom = list(dict.fromkeys(alat._kolom_sah(t, str(k)) for k in (kolom or [])))
    if not 2 <= len(kolom) <= MAKS_LEVEL:
        raise alat.InputSalah(f"Hierarki butuh 2 sampai {MAKS_LEVEL} kolom berurutan (dari yang paling umum).")
    db = _db()
    db.session.execute(TABEL.delete().where((TABEL.c.dataset_id == t.id) & (TABEL.c.nama == nama)))
    db.session.execute(TABEL.insert().values(dataset_id=t.id, nama=nama, kolom=json.dumps(kolom),
                                             pembuat=getattr(g.user, "username", ""), diubah=datetime.now()))
    db.session.commit()
    return {"nama": nama, "kolom": kolom}


def pasang_bawaan(dataset_id: int, nama: str, kolom: list[str], pembuat: str = "sistem") -> None:
    """Hierarki bawaan dari data latihan (tanpa cek izin pengguna; hanya dipanggil kode server).
    Tidak menimpa hierarki bernama sama yang sudah diubah admin."""
    db = _db()
    ada = db.session.execute(select(TABEL.c.pembuat).where((TABEL.c.dataset_id == dataset_id) & (TABEL.c.nama == nama))).first()
    if ada is None:
        db.session.execute(TABEL.insert().values(dataset_id=dataset_id, nama=nama, kolom=json.dumps(kolom),
                                                 pembuat=pembuat, diubah=datetime.now()))
        db.session.commit()


def hapus(dataset_id: int, nama: str) -> None:
    _boleh_ubah()
    t = alat._dataset(dataset_id)
    db = _db()
    db.session.execute(TABEL.delete().where((TABEL.c.dataset_id == t.id) & (TABEL.c.nama == str(nama))))
    db.session.commit()
