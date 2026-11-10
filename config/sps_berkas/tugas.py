"""Ekspor berkas .aldx berisi data di latar belakang (P1).

Menyalin data bisa memakan waktu & RAM. Bila backgrounder (Celery) menyala, ekspor .aldx dengan data dikerjakan
di antrean "ekstrak", bukan di proses web, sehingga tidak kena batas waktu gateway. Pengguna melihat statusnya di
halaman Berkas (bagian "Ekspor terakhir") dan mengunduh setelah siap. Tanpa backgrounder: dikerjakan langsung
seperti biasa (tetap jalan, hanya menunggu).

Tabel sps_berkas_tugas (metadata):
    id, pemilik, status (antre | jalan | siap | gagal), pesan, nama berkas, dibuat, selesai, ukuran, isi (biner)
Hasil disimpan di database metadata (bukan disk lokal) agar node tambahan pun bisa mengerjakannya.
Hasil lebih tua dari SIMPAN_JAM dihapus otomatis. Hanya pemilik yang bisa melihat & mengunduh.

Isi berkas tetap terenkripsi (kunci server / kata sandi) seperti ekspor langsung. Kata sandi TIDAK disimpan:
ia hanya ikut di pesan antrean Redis (internal) dan langsung dipakai worker.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, LargeBinary, MetaData, String, Table, delete, insert, select, update

log = logging.getLogger(__name__)

SIMPAN_JAM = 24
_meta = MetaData()
TUGAS = Table("sps_berkas_tugas", _meta,
              Column("id", String(32), primary_key=True), Column("pemilik", String(128), index=True),
              Column("status", String(10)), Column("pesan", String(500)), Column("nama", String(200)),
              Column("dibuat", DateTime), Column("selesai", DateTime), Column("ukuran", Integer),
              Column("isi", LargeBinary))


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


def pastikan_tabel() -> None:
    _meta.create_all(bind=_engine(), checkfirst=True)


def ada_worker() -> bool:
    """True bila minimal satu backgrounder menjawab (maks. 1 detik)."""
    try:
        from superset.extensions import celery_app
        return bool(celery_app.control.ping(timeout=1.0))
    except Exception:  # noqa: BLE001 - broker mati / belum diatur: kerjakan langsung
        return False


def _ubah(tugas_id: str, **nilai) -> None:
    with _engine().begin() as c:
        c.execute(update(TUGAS).where(TUGAS.c.id == tugas_id).values(**nilai))


def antrekan(pemilik: str, permintaan: dict) -> str:
    """Catat tugas & kirim ke backgrounder. Kembalikan id tugas."""
    pastikan_tabel()
    tugas_id = secrets.token_hex(16)
    with _engine().begin() as c:
        c.execute(delete(TUGAS).where(TUGAS.c.dibuat < datetime.now() - timedelta(hours=SIMPAN_JAM)))
        c.execute(insert(TUGAS).values(id=tugas_id, pemilik=pemilik, status="antre", dibuat=datetime.now(),
                                       pesan="Menunggu backgrounder"))
    ekspor_latar.apply_async(args=[tugas_id, pemilik, permintaan], queue="ekstrak")
    return tugas_id


def jalankan(tugas_id: str, pemilik: str, permintaan: dict) -> None:
    """Kerjakan ekspor sebagai `pemilik` (hak akses & RLS pemilik berlaku)."""
    from superset import security_manager
    from superset.utils.core import override_user

    from sps_berkas import paket
    _ubah(tugas_id, status="jalan", pesan="Menyalin data...")
    try:
        user = security_manager.find_user(username=pemilik)
        if user is None or not user.is_active:
            raise RuntimeError("Akun pemilik tidak aktif.")
        with override_user(user):
            nama, isi, _ = paket.ekspor(**permintaan)
        _ubah(tugas_id, status="siap", nama=nama, isi=isi, ukuran=len(isi), selesai=datetime.now(),
              pesan="Siap diunduh")
    except Exception as exc:  # noqa: BLE001 - pesan galat untuk pengguna
        log.exception("ALDx berkas: ekspor latar %s gagal", tugas_id)
        _ubah(tugas_id, status="gagal", pesan=str(exc)[:500], selesai=datetime.now())


def daftar(pemilik: str) -> list[dict]:
    pastikan_tabel()
    q = (select(TUGAS.c.id, TUGAS.c.status, TUGAS.c.pesan, TUGAS.c.nama, TUGAS.c.dibuat, TUGAS.c.ukuran)
         .where(TUGAS.c.pemilik == pemilik, TUGAS.c.dibuat >= datetime.now() - timedelta(hours=SIMPAN_JAM))
         .order_by(TUGAS.c.dibuat.desc()).limit(20))
    with _engine().connect() as c:
        return [{**r, "dibuat": f"{r['dibuat']:%Y-%m-%d %H:%M}"} for r in c.execute(q).mappings()]


def ambil_isi(tugas_id: str, pemilik: str) -> tuple[str, bytes] | None:
    with _engine().connect() as c:
        r = c.execute(select(TUGAS.c.nama, TUGAS.c.isi).where(
            TUGAS.c.id == tugas_id, TUGAS.c.pemilik == pemilik, TUGAS.c.status == "siap")).first()
    return (r.nama, r.isi) if r else None


try:
    from superset.extensions import celery_app

    @celery_app.task(name="sps.berkas.ekspor", soft_time_limit=3 * 3600)
    def ekspor_latar(tugas_id: str, pemilik: str, permintaan: dict) -> str:
        jalankan(tugas_id, pemilik, permintaan)
        return tugas_id
except Exception:  # noqa: BLE001 - dimuat di luar Superset (mis. uji unit)
    ekspor_latar = None
