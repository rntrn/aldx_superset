"""Penyimpanan pusat pengaturan server, riwayat perubahan & daftar node.

Semua node (komputer) membaca pengaturan dari database metadata yang SAMA,
jadi admin cukup mengubah di satu tempat (konfigurasi terpusat).

Tabel (dibuat otomatis di database sps_superset):
    sps_server_atur     kunci -> nilai (JSON); hanya yang berbeda dari bawaan
    sps_server_riwayat  siapa mengubah apa, kapan (audit)
    sps_node            detak (heartbeat) tiap container: node, layanan, sumber daya, status
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text, create_engine,
                        delete, func, insert, select, update)
from sqlalchemy.engine import Engine

from sps_server import lingkungan, skema

log = logging.getLogger(__name__)

_meta = MetaData()
ATUR = Table("sps_server_atur", _meta,
             Column("kunci", String(64), primary_key=True),
             Column("nilai", Text), Column("diubah", DateTime), Column("oleh", String(64)))
RIWAYAT = Table("sps_server_riwayat", _meta,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("waktu", DateTime), Column("oleh", String(64)), Column("kunci", String(64)),
                Column("lama", Text), Column("baru", Text))
NODE = Table("sps_node", _meta,
             Column("nama", String(160), primary_key=True),        # "<node>/<layanan>"
             Column("node", String(100)), Column("layanan", String(20)), Column("peran", String(20)),
             Column("alamat", String(200)), Column("info", Text),
             Column("mulai", DateTime), Column("terakhir", DateTime))

DETIK_ONLINE = 90          # node dianggap mati bila tidak berdetak selama ini


# --- Koneksi -----------------------------------------------------------------------
@lru_cache(maxsize=1)
def _engine_mandiri() -> Engine:
    return create_engine(lingkungan.uri_metadata(), pool_pre_ping=True, pool_recycle=3600)


def engine() -> Engine:
    """Engine Superset bila di dalam aplikasi; selain itu engine mandiri (peluncur/skrip)."""
    from flask import has_app_context
    if has_app_context():
        from superset import db
        return db.engine
    return _engine_mandiri()


def pastikan_tabel(e: Engine | None = None) -> None:
    _meta.create_all(bind=e or engine(), checkfirst=True)


# --- Pengaturan --------------------------------------------------------------------------
def baca_tersimpan(e: Engine | None = None) -> dict[str, Any]:
    e = e or engine()
    pastikan_tabel(e)
    with e.connect() as c:
        return {r.kunci: json.loads(r.nilai) for r in c.execute(select(ATUR.c.kunci, ATUR.c.nilai))}


def nilai_semua(e: Engine | None = None) -> dict[str, Any]:
    """Bawaan + yang tersimpan. Database tidak terjangkau -> bawaan (Superset tetap bisa start)."""
    nilai = skema.bawaan()
    try:
        for kunci, v in baca_tersimpan(e).items():
            if kunci in skema.PETA:
                nilai[kunci] = v
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx server: pengaturan tidak terbaca, pakai bawaan (%s)", exc)
    return nilai


def versi(e: Engine | None = None) -> str:
    """Penanda perubahan terakhir; dipakai untuk muat ulang pengaturan 'langsung'."""
    with (e or engine()).connect() as c:
        return str(c.execute(select(func.max(ATUR.c.diubah))).scalar() or "")


def simpan(perubahan: dict[str, Any], oleh: str) -> list[str]:
    """Validasi & simpan. Kembalikan kunci yang benar-benar berubah. ValueError bila tidak sah."""
    lama = nilai_semua()
    baru = dict(lama)
    galat = []
    for kunci, v in perubahan.items():
        if kunci not in skema.PETA:
            galat.append(f"Pengaturan '{kunci}' tidak dikenal.")
            continue
        try:
            baru[kunci] = skema.PETA[kunci].normalkan(v)
        except ValueError as exc:
            galat.append(str(exc))
    galat += [] if galat else skema.periksa_silang(baru)
    if galat:
        raise ValueError(" ".join(galat))

    berubah = [k for k in perubahan if k in skema.PETA and baru[k] != lama[k]]
    if not berubah:
        return []
    sekarang = datetime.now()
    e = engine()
    with e.begin() as c:
        for k in berubah:
            c.execute(delete(ATUR).where(ATUR.c.kunci == k))
            if baru[k] != skema.PETA[k].bawaan:              # simpan hanya yang bukan bawaan
                c.execute(insert(ATUR).values(kunci=k, nilai=json.dumps(baru[k]), diubah=sekarang, oleh=oleh))
            c.execute(insert(RIWAYAT).values(waktu=sekarang, oleh=oleh, kunci=k,
                                             lama=json.dumps(lama[k]), baru=json.dumps(baru[k])))
        # penanda versi tetap berubah walau nilai kembali ke bawaan
        c.execute(delete(ATUR).where(ATUR.c.kunci == "_versi"))
        c.execute(insert(ATUR).values(kunci="_versi", nilai=json.dumps(str(sekarang)), diubah=sekarang, oleh=oleh))
    log.info("ALDx server: %s mengubah %s", oleh, berubah)
    return berubah


def riwayat(batas: int = 100) -> list[dict]:
    with engine().connect() as c:
        rows = c.execute(select(RIWAYAT).order_by(RIWAYAT.c.id.desc()).limit(batas)).mappings()
        return [{**r, "waktu": r["waktu"].isoformat(sep=" ", timespec="seconds")} for r in rows]


# --- Node (heartbeat) ----------------------------------------------------------------------
def detak(nama: str, data: dict[str, Any], mulai: datetime, e: Engine | None = None) -> None:
    """Catat bahwa container `nama` masih hidup, beserta info sumber dayanya."""
    e = e or engine()
    nilai = {"node": data["node"], "layanan": data["layanan"], "peran": data["peran"],
             "alamat": data.get("alamat", ""), "info": json.dumps(data, default=str),
             "mulai": mulai, "terakhir": datetime.now()}
    with e.begin() as c:
        if c.execute(update(NODE).where(NODE.c.nama == nama).values(**nilai)).rowcount == 0:
            c.execute(insert(NODE).values(nama=nama, **nilai))


def daftar_node(e: Engine | None = None) -> list[dict]:
    e = e or engine()
    pastikan_tabel(e)
    batas = datetime.now() - timedelta(seconds=DETIK_ONLINE)
    with e.connect() as c:
        rows = c.execute(select(NODE).order_by(NODE.c.node, NODE.c.layanan)).mappings().all()
    hasil = []
    for r in rows:
        info = json.loads(r["info"] or "{}")
        hasil.append({**info, "nama": r["nama"], "node": r["node"], "layanan": r["layanan"],
                      "peran": r["peran"], "alamat": r["alamat"],
                      "online": r["terakhir"] >= batas,
                      "mulai": r["mulai"].isoformat(sep=" ", timespec="seconds"),
                      "terakhir": r["terakhir"].isoformat(sep=" ", timespec="seconds")})
    return hasil


def hapus_node(nama: str) -> None:
    with engine().begin() as c:
        c.execute(delete(NODE).where(NODE.c.nama == nama))
