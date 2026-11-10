"""Simpan identitas di database metadata (dipakai bersama semua node).

Tabel:
    sps_identitas         kunci -> nilai (JSON); hanya yang berbeda dari bawaan
    sps_identitas_berkas  logo/favicon yang diunggah (biner)
Setiap perubahan dicatat di Riwayat Pusat Kendali (kunci "identitas:<isian>").
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, LargeBinary, MetaData, String, Table, Text, delete, func, insert, select

from sps_identitas import skema
from sps_server import penyimpanan as pusat

log = logging.getLogger(__name__)

_meta = MetaData()
NILAI = Table("sps_identitas", _meta,
              Column("kunci", String(40), primary_key=True), Column("nilai", Text),
              Column("diubah", DateTime), Column("oleh", String(64)))
BERKAS = Table("sps_identitas_berkas", _meta,
               Column("nama", String(40), primary_key=True), Column("mime", String(60)),
               Column("isi", LargeBinary), Column("diubah", DateTime))


def pastikan_tabel(e=None) -> None:
    _meta.create_all(bind=e or pusat.engine(), checkfirst=True)


def baca(e=None) -> dict[str, Any]:
    """Bawaan + tersimpan. Database tidak terjangkau -> bawaan (Superset tetap bisa start)."""
    nilai = skema.bawaan()
    try:
        e = e or pusat.engine()
        pastikan_tabel(e)
        with e.connect() as c:
            for r in c.execute(select(NILAI.c.kunci, NILAI.c.nilai)):
                if r.kunci in skema.PETA:
                    nilai[r.kunci] = json.loads(r.nilai)
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx identitas: tidak terbaca, pakai bawaan (%s)", exc)
    return nilai


def ada_isian(e=None) -> bool:
    e = e or pusat.engine()
    pastikan_tabel(e)
    with e.connect() as c:
        return bool(c.execute(select(func.count()).select_from(NILAI)).scalar())


def versi(e=None) -> str:
    """Penanda perubahan: berubah setiap ada isian/berkas yang disimpan."""
    e = e or pusat.engine()
    with e.connect() as c:
        a = c.execute(select(func.max(NILAI.c.diubah), func.count()).select_from(NILAI)).one()
        b = c.execute(select(func.max(BERKAS.c.diubah), func.count()).select_from(BERKAS)).one()
    stempel = max([w for w in (a[0], b[0]) if w] or [datetime(2000, 1, 1)])
    return f"{stempel:%Y%m%d%H%M%S%f}-{a[1]}-{b[1]}"


def simpan(perubahan: dict[str, Any], oleh: str, e=None) -> list[str]:
    """Simpan isian yang berubah. Nilai sama dengan bawaan -> barisnya dihapus."""
    e = e or pusat.engine()
    pastikan_tabel(e)
    lama = baca(e)
    bersih = {k: skema.periksa(k, v) for k, v in perubahan.items()}   # periksa semua dulu
    berubah, sekarang = [], datetime.now()
    with e.begin() as c:
        for k, v in bersih.items():
            if v == lama.get(k):
                continue
            c.execute(delete(NILAI).where(NILAI.c.kunci == k))
            if v != skema.PETA[k].bawaan:
                c.execute(insert(NILAI).values(kunci=k, nilai=json.dumps(v), diubah=sekarang, oleh=oleh))
            c.execute(insert(pusat.RIWAYAT).values(waktu=sekarang, oleh=oleh, kunci=f"identitas:{k}",
                                                   lama=json.dumps(lama.get(k)), baru=json.dumps(v)))
            berubah.append(k)
        if berubah:   # penanda versi tetap bergerak walau isian kembali ke bawaan
            c.execute(delete(NILAI).where(NILAI.c.kunci == "_versi"))
            c.execute(insert(NILAI).values(kunci="_versi", nilai="null", diubah=sekarang, oleh=oleh))
    return berubah


def simpan_berkas(nama: str, mime: str, isi: bytes, oleh: str, e=None) -> None:
    if nama not in skema.BERKAS:
        raise ValueError(f"Berkas '{nama}' tidak dikenal")
    if mime not in skema.MIME_BOLEH:
        raise ValueError("Jenis berkas harus gambar (PNG, SVG, JPG, WEBP, ICO)")
    if not isi or len(isi) > skema.BATAS_BERKAS:
        raise ValueError("Ukuran berkas maksimal 1 MB")
    if mime == "image/svg+xml" and b"<script" in isi.lower():
        raise ValueError("SVG berisi skrip tidak diizinkan")
    e = e or pusat.engine()
    pastikan_tabel(e)
    with e.begin() as c:
        c.execute(delete(BERKAS).where(BERKAS.c.nama == nama))
        c.execute(insert(BERKAS).values(nama=nama, mime=mime, isi=isi, diubah=datetime.now()))
    simpan({nama: "unggah"}, oleh, e)


def ambil_berkas(nama: str, e=None) -> tuple[str, bytes] | None:
    e = e or pusat.engine()
    with e.connect() as c:
        r = c.execute(select(BERKAS.c.mime, BERKAS.c.isi).where(BERKAS.c.nama == nama)).first()
    return (r.mime, bytes(r.isi)) if r else None
