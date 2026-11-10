"""Penguncian akun setelah salah password berulang (K4).

Aturan (Pusat Kendali › Pengaturan › Gateway & keamanan):
    keamanan.login_maks_gagal   salah password berturut-turut sebelum dikunci (bawaan 5; 0 = mati)
    keamanan.login_kunci_menit  lama terkunci (bawaan 15 menit)

Berlaku untuk akun lokal (email) DAN login LDAP (NIP). Hitungan per username, jadi tidak bisa
dielakkan dengan berganti komputer. Selama terkunci, password yang benar pun ditolak.
Login berhasil = hitungan kembali 0. Kunci habis sendiri, dibuka Admin di Pusat Kendali › Riwayat,
atau darurat lewat scripts\\buka-kunci.ps1 (mis. Superadmin satu-satunya terkunci).

Tabel sps_kunci_login (database metadata): username, gagal, terakhir_gagal, kunci_sampai.
Setiap kejadian dicatat di jejak audit (sps_audit, kelompok "login").
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, delete, insert, select, update

import sps_audit

log = logging.getLogger(__name__)

_meta = MetaData()
KUNCI = Table("sps_kunci_login", _meta,
              Column("username", String(128), primary_key=True),
              Column("gagal", Integer, default=0),
              Column("terakhir_gagal", DateTime),
              Column("kunci_sampai", DateTime))

JENDELA_MENIT = 60          # salah password lebih lama dari ini tidak dihitung lagi


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


def pastikan_tabel() -> None:
    _meta.create_all(bind=_engine(), checkfirst=True)


def _aturan() -> tuple[int, int]:
    from sps_server import penyimpanan
    atur = penyimpanan.nilai_semua()
    return int(atur.get("keamanan.login_maks_gagal", 5)), int(atur.get("keamanan.login_kunci_menit", 15))


def _kunci(username: str) -> str:
    return (username or "").strip().lower()[:128]


def terkunci_sampai(username: str) -> datetime | None:
    """Waktu kunci berakhir, atau None bila akun boleh mencoba login."""
    try:
        with _engine().connect() as c:
            r = c.execute(select(KUNCI.c.kunci_sampai).where(KUNCI.c.username == _kunci(username))).first()
    except Exception as exc:  # noqa: BLE001 - tabel belum ada / database sibuk: jangan halangi login
        log.warning("ALDx kunci: tidak terbaca (%s)", exc)
        return None
    if r and r.kunci_sampai and r.kunci_sampai > datetime.now():
        return r.kunci_sampai
    return None


def gagal(username: str, jalur: str) -> datetime | None:
    """Catat satu salah password. Kembalikan waktu kunci berakhir bila akun baru saja dikunci."""
    maks, menit = _aturan()
    u, sekarang = _kunci(username), datetime.now()
    sps_audit.catat("login", f"Login gagal ({jalur})", u, oleh=u)
    if maks <= 0 or not u:
        return None
    try:
        with _engine().begin() as c:
            # Bersihkan catatan lama tanpa kunci aktif (mis. tebakan username acak) agar tabel tidak membengkak.
            c.execute(delete(KUNCI).where((KUNCI.c.terakhir_gagal < sekarang - timedelta(days=1))
                                          & ((KUNCI.c.kunci_sampai.is_(None)) | (KUNCI.c.kunci_sampai < sekarang))))
            r = c.execute(select(KUNCI).where(KUNCI.c.username == u)).mappings().first()
            hitung = 1
            if r and r["terakhir_gagal"] and r["terakhir_gagal"] > sekarang - timedelta(minutes=JENDELA_MENIT):
                hitung = (r["gagal"] or 0) + 1
            sampai = sekarang + timedelta(minutes=menit) if hitung >= maks else None
            nilai = dict(gagal=0 if sampai else hitung, terakhir_gagal=sekarang, kunci_sampai=sampai)
            if r:
                c.execute(update(KUNCI).where(KUNCI.c.username == u).values(**nilai))
            else:
                c.execute(insert(KUNCI).values(username=u, **nilai))
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx kunci: gagal mencatat (%s)", exc)
        return None
    if sampai:
        log.warning("ALDx login %s: DIKUNCI sampai %s (%d kali salah)", u, sampai, hitung)
        sps_audit.catat("login", "Akun dikunci", u, {"sampai": f"{sampai:%Y-%m-%d %H:%M}", "salah": hitung}, oleh=u)
    return sampai


def berhasil(username: str) -> None:
    u = _kunci(username)
    sps_audit.catat("login", "Login berhasil", u, oleh=u)
    try:
        with _engine().begin() as c:
            c.execute(delete(KUNCI).where(KUNCI.c.username == u))
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx kunci: gagal mereset (%s)", exc)


def daftar_terkunci() -> list[dict]:
    with _engine().connect() as c:
        rows = c.execute(select(KUNCI).where(KUNCI.c.kunci_sampai > datetime.now())
                         .order_by(KUNCI.c.kunci_sampai.desc())).mappings().all()
    return [{"username": r["username"], "sampai": f"{r['kunci_sampai']:%Y-%m-%d %H:%M}"} for r in rows]


def buka(username: str, oleh: str) -> None:
    u = _kunci(username)
    with _engine().begin() as c:
        c.execute(delete(KUNCI).where(KUNCI.c.username == u))
    sps_audit.catat("login", "Kunci akun dibuka", u, oleh=oleh)


def pesan(sampai: datetime) -> str:
    return (f"Akun dikunci sementara karena terlalu banyak salah password. "
            f"Coba lagi pukul {sampai:%H:%M}, atau minta Admin membukanya.")


if __name__ == "__main__":
    # Darurat (scripts\buka-kunci.ps1): python sps_kunci.py            -> daftar akun terkunci
    #                                   python sps_kunci.py <username> -> buka kunci akun itu
    import sys

    from superset.app import create_app
    with create_app().app_context():
        pastikan_tabel()
        if len(sys.argv) > 1:
            buka(sys.argv[1], "skrip buka-kunci")
            print(f"Kunci akun '{sys.argv[1]}' dibuka.")
        terkunci = daftar_terkunci()
        print("Akun terkunci: " + (", ".join(f"{x['username']} (s.d. {x['sampai']})" for x in terkunci) or "tidak ada"))
