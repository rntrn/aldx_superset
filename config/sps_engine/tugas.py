"""Tugas backgrounder (Celery) untuk ekstrak — antrean "ekstrak".

    sps.ekstrak.segarkan  satu penyegaran (dari tombol "Segarkan" atau penjadwal)
    sps.ekstrak.jadwal    tiap 5 menit: kirim ekstrak yang waktunya tiba ke antrean
    sps.ramalan.segarkan  tiap hari 03:00: hitung ulang ramalan Studio (sps_studio/ramalan.py)
"""

from __future__ import annotations

import logging

from superset.extensions import celery_app

from sps_engine import ekstrak

log = logging.getLogger(__name__)
BATAS_DETIK = 6 * 3600          # penyegaran terlama yang diizinkan


@celery_app.task(name="sps.ekstrak.segarkan", soft_time_limit=BATAS_DETIK)
def segarkan(ekstrak_id: int, pemicu: str = "manual", penuh: bool = False) -> dict:
    hasil = ekstrak.segarkan(ekstrak_id, pemicu, penuh)
    return {"status": hasil["status"], "baris": hasil["baris_terakhir"]}


@celery_app.task(name="sps.ekstrak.jadwal")
def jadwal() -> int:
    ids = ekstrak.jatuh_tempo()
    for i in ids:
        segarkan.apply_async(args=[i, "jadwal"], queue="ekstrak")
    if ids:
        log.info("ALDx ekstrak: %d penyegaran terjadwal dikirim", len(ids))
    return len(ids)


@celery_app.task(name="sps.ramalan.segarkan", soft_time_limit=BATAS_DETIK)
def segarkan_ramalan() -> int:
    from sps_studio import ramalan
    n = ramalan.segarkan_semua()
    log.info("ALDx ramalan: %d ramalan diperbarui", n)
    return n
