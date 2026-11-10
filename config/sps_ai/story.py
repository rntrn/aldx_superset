"""Story: rangkaian beberapa dashboard berurutan + narasi (presentasi data berurutan).

Disimpan di tabel sps_story (database metadata sps_superset). Setiap langkah
menampilkan satu dashboard (iframe) beserta judul & narasinya. Hak akses
dashboard tetap berlaku: langkah yang dashboard-nya tidak boleh dibuka
penonton ditampilkan terkunci.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, select

from sps_ai.alat import InputSalah, IzinDitolak

MAKS_LANGKAH = 30
_metadata = MetaData()
STORY = Table(
    "sps_story", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("judul", String(255), nullable=False),
    Column("keterangan", Text),
    Column("pemilik", String(64), nullable=False),
    Column("publik", Boolean, default=False),
    Column("langkah", Text, nullable=False),      # JSON: [{dashboard_id, judul, narasi}]
    Column("dibuat", DateTime),
    Column("diubah", DateTime),
)


def _db():
    from superset import db
    STORY.create(bind=db.engine, checkfirst=True)
    return db


def _user():
    from flask import g
    return g.user


def _admin() -> bool:
    from superset import security_manager
    return security_manager.is_admin()


def _boleh_lihat(row) -> bool:
    return bool(row["publik"]) or row["pemilik"] == _user().username or _admin()


def _boleh_ubah(row) -> bool:
    return row["pemilik"] == _user().username or _admin()


def _dashboard(dashboard_id: int):
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    d = db.session.query(Dashboard).get(int(dashboard_id))
    return d if d is not None and security_manager.can_access_dashboard(d) else None


def daftar() -> list[dict]:
    db = _db()
    rows = db.session.execute(select(STORY).order_by(STORY.c.diubah.desc())).mappings().all()
    return [{"id": r["id"], "judul": r["judul"], "keterangan": r["keterangan"] or "",
             "pemilik": r["pemilik"], "publik": bool(r["publik"]),
             "jumlah_langkah": len(json.loads(r["langkah"])), "boleh_ubah": _boleh_ubah(r)}
            for r in rows if _boleh_lihat(r)]


def ambil(story_id: int) -> dict:
    db = _db()
    r = db.session.execute(select(STORY).where(STORY.c.id == int(story_id))).mappings().first()
    if r is None or not _boleh_lihat(r):
        raise IzinDitolak("Story tidak ditemukan atau Anda tidak berhak melihatnya.")
    langkah = []
    for s in json.loads(r["langkah"]):
        d = _dashboard(s["dashboard_id"])
        langkah.append({**s, "terkunci": d is None,
                        "url": f"/superset/dashboard/{d.id}/?standalone=2" if d else "",  # 2 = tanpa navbar & judul
                        "judul_dashboard": d.dashboard_title if d else ""})
    return {"id": r["id"], "judul": r["judul"], "keterangan": r["keterangan"] or "",
            "pemilik": r["pemilik"], "publik": bool(r["publik"]), "langkah": langkah,
            "boleh_ubah": _boleh_ubah(r)}


def simpan(data: dict, story_id: int | None = None) -> dict:
    db = _db()
    if story_id:                                   # cek hak ubah dulu, baru isi
        r = db.session.execute(select(STORY).where(STORY.c.id == int(story_id))).mappings().first()
        if r is None or not _boleh_ubah(r):
            raise IzinDitolak("Hanya pemilik story (atau Admin) yang boleh mengubahnya.")

    judul = str(data.get("judul", "")).strip()[:255]
    if not judul:
        raise InputSalah("Judul story wajib diisi.")
    langkah = []
    for s in (data.get("langkah") or [])[:MAKS_LANGKAH]:
        d = _dashboard(s.get("dashboard_id", 0))
        if d is None:
            raise InputSalah(f"Dashboard {s.get('dashboard_id')} tidak ada atau tidak boleh Anda akses.")
        langkah.append({"dashboard_id": d.id, "judul": str(s.get("judul") or d.dashboard_title)[:255],
                        "narasi": str(s.get("narasi", ""))[:5000]})
    if not langkah:
        raise InputSalah("Story butuh minimal satu dashboard.")

    nilai = {"judul": judul, "keterangan": str(data.get("keterangan", ""))[:2000],
             "publik": bool(data.get("publik")), "langkah": json.dumps(langkah), "diubah": datetime.now()}
    if story_id:
        db.session.execute(STORY.update().where(STORY.c.id == int(story_id)).values(**nilai))
    else:
        hasil = db.session.execute(STORY.insert().values(
            **nilai, pemilik=_user().username, dibuat=datetime.now()))
        story_id = hasil.inserted_primary_key[0]
    db.session.commit()
    return {"id": story_id, "url": f"/asisten/story/{story_id}"}


def hapus(story_id: int) -> None:
    db = _db()
    r = db.session.execute(select(STORY).where(STORY.c.id == int(story_id))).mappings().first()
    if r is None or not _boleh_ubah(r):
        raise IzinDitolak("Hanya pemilik story (atau Admin) yang boleh menghapusnya.")
    db.session.execute(STORY.delete().where(STORY.c.id == int(story_id)))
    db.session.commit()
