"""Penyimpanan komentar & rating (tabel sps_ulasan di database metadata).

Status:  menunggu  -> belum terlihat orang lain (hanya penulis & Superadmin), bila moderasi aktif
         tampil     -> terlihat semua yang boleh membuka dashboard/chart itu
         ditolak    -> disembunyikan Superadmin (penulis melihat alasannya)
Rating:  1-5 bintang, opsional. Rata-rata memakai rating TERAKHIR tiap pengguna yang berstatus tampil.
Balasan: induk_id = id komentar yang dibalas (satu tingkat). Balasan tidak membawa rating.
@sebut:  "@username" di teks -> pemberitahuan untuk orang itu (tabel sps_notifikasi), juga untuk penulis
         komentar yang dibalas. Dikirim saat komentar TAMPIL (langsung, atau setelah disetujui moderator).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, and_, func, inspect, select, text

JENIS = ("dashboard", "chart")
STATUS = ("menunggu", "tampil", "ditolak")
MAKS_TEKS = 2000

_metadata = MetaData()
ULASAN = Table(
    "sps_ulasan", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("jenis", String(16), nullable=False, index=True),
    Column("objek_id", Integer, nullable=False, index=True),
    Column("pengguna", String(128), nullable=False, index=True),
    Column("nama", String(255)),
    Column("teks", Text),
    Column("nilai", Integer),                          # 1..5, kosong = hanya komentar
    Column("status", String(16), nullable=False, index=True),
    Column("dibuat", DateTime, nullable=False),
    Column("moderator", String(128)),
    Column("dimoderasi", DateTime),
    Column("alasan", String(500)),
    Column("induk_id", Integer, index=True),          # balasan untuk komentar ini
)
NOTIF = Table(
    "sps_notifikasi", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("pengguna", String(128), nullable=False, index=True),
    Column("teks", String(500)),
    Column("alamat", String(300)),
    Column("dibuat", DateTime, nullable=False),
    Column("dibaca", Boolean, default=False, index=True),
)
POLA_SEBUT = re.compile(r"(?<![\w@])@([\w.\-]+(?:@[\w.\-]+\.\w+)?)")
_siap = False


def _db():
    """Buat tabel bila belum ada; instalasi lama: tambah kolom induk_id (sekali per proses)."""
    global _siap
    from superset import db
    if not _siap:
        _metadata.create_all(bind=db.engine, checkfirst=True)
        if "induk_id" not in {c["name"] for c in inspect(db.engine).get_columns("sps_ulasan")}:
            with db.engine.begin() as c:
                c.execute(text("ALTER TABLE sps_ulasan ADD COLUMN induk_id INTEGER"))
        _siap = True
    return db


def _baris(r) -> dict:
    d = dict(r._mapping)
    for k in ("dibuat", "dimoderasi"):
        d[k] = d[k].isoformat() if d[k] else None
    return d


def tambah(jenis: str, objek_id: int, pengguna: str, nama: str, teks: str, nilai: int | None, moderasi: bool,
           induk_id: int | None = None) -> dict:
    db = _db()
    status = "menunggu" if moderasi else "tampil"
    with db.engine.begin() as c:
        r = c.execute(ULASAN.insert().values(jenis=jenis, objek_id=objek_id, pengguna=pengguna, nama=nama,
                                             teks=teks, nilai=None if induk_id else nilai, status=status,
                                             induk_id=induk_id,
                                             dibuat=datetime.now(timezone.utc).replace(tzinfo=None)))
        u = ambil(r.inserted_primary_key[0], c)
    if status == "tampil":
        beri_tahu(u)
    return u


def _sekarang() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def beri_tahu(u: dict) -> int:
    """Pemberitahuan untuk @sebut di teks + penulis komentar induk. Tidak untuk diri sendiri. Kembalikan jumlah."""
    from superset import security_manager as sm
    disebut = {nama.rstrip(".-") for nama in POLA_SEBUT.findall(u.get("teks") or "")}
    tujuan = set(disebut)
    if u.get("induk_id"):
        induk = ambil(u["induk_id"])
        if induk:
            tujuan.add(induk["pengguna"])
    tujuan.discard(u["pengguna"])
    alamat = (f"/superset/dashboard/{u['objek_id']}/" if u["jenis"] == "dashboard"
              else f"/explore/?slice_id={u['objek_id']}")
    n = 0
    with _db().engine.begin() as c:
        for nama in sorted(tujuan)[:20]:
            user = sm.find_user(username=nama)
            if user is None or not user.is_active:
                continue
            aksi = "menyebut Anda" if nama in disebut else "membalas komentar Anda"
            c.execute(NOTIF.insert().values(pengguna=nama, alamat=alamat, dibuat=_sekarang(), dibaca=False,
                                            teks=f"{u.get('nama') or u['pengguna']} {aksi}: {(u.get('teks') or '')[:200]}"))
            n += 1
    return n


def notifikasi(pengguna: str, batas: int = 20) -> dict:
    db = _db()
    q = select(NOTIF).where(NOTIF.c.pengguna == pengguna).order_by(NOTIF.c.id.desc()).limit(batas)
    daftar = [{**dict(r._mapping), "dibuat": r.dibuat.isoformat()} for r in db.session.execute(q)]
    belum = int(db.session.execute(select(func.count()).where(
        and_(NOTIF.c.pengguna == pengguna, NOTIF.c.dibaca.is_(False)))).scalar() or 0)
    return {"belum_dibaca": belum, "daftar": daftar}


def tandai_dibaca(pengguna: str) -> None:
    with _db().engine.begin() as c:
        c.execute(NOTIF.update().where(NOTIF.c.pengguna == pengguna).values(dibaca=True))


def ambil(ulasan_id: int, c=None) -> dict | None:
    db = _db()
    q = select(ULASAN).where(ULASAN.c.id == ulasan_id)
    r = (c.execute(q) if c is not None else db.session.execute(q)).first()
    return _baris(r) if r else None


def daftar(jenis: str, objek_id: int, pengguna: str, semua: bool) -> list[dict]:
    """Ulasan yang tampil + milik pengguna sendiri (semua status). `semua` = Superadmin melihat semuanya."""
    db = _db()
    q = select(ULASAN).where(and_(ULASAN.c.jenis == jenis, ULASAN.c.objek_id == objek_id))
    if not semua:
        q = q.where((ULASAN.c.status == "tampil") | (ULASAN.c.pengguna == pengguna))
    return [_baris(r) for r in db.session.execute(q.order_by(ULASAN.c.dibuat.desc()).limit(500))]


def ringkasan(jenis: str, objek_id: int) -> dict:
    """Rata-rata rating (rating terakhir tiap pengguna yang tampil) & jumlahnya."""
    db = _db()
    terakhir = (select(ULASAN.c.pengguna, func.max(ULASAN.c.id).label("id"))
                .where(and_(ULASAN.c.jenis == jenis, ULASAN.c.objek_id == objek_id,
                            ULASAN.c.status == "tampil", ULASAN.c.nilai.isnot(None)))
                .group_by(ULASAN.c.pengguna).subquery())
    r = db.session.execute(select(func.avg(ULASAN.c.nilai), func.count()).join(
        terakhir, ULASAN.c.id == terakhir.c.id)).first()
    return {"rata": round(float(r[0]), 2) if r and r[0] is not None else None, "jumlah": int(r[1] if r else 0)}


def jumlah_baru(pengguna: str, detik: int = 60) -> int:
    """Banyaknya ulasan pengguna ini dalam `detik` terakhir (pembatas spam)."""
    from datetime import timedelta
    db = _db()
    batas = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=detik)
    return int(db.session.execute(select(func.count()).where(
        and_(ULASAN.c.pengguna == pengguna, ULASAN.c.dibuat >= batas))).scalar() or 0)


def antrean(status: str = "menunggu", batas: int = 200) -> list[dict]:
    db = _db()
    q = select(ULASAN).where(ULASAN.c.status == status).order_by(ULASAN.c.dibuat.desc()).limit(batas)
    return [_baris(r) for r in db.session.execute(q)]


def jumlah_menunggu() -> int:
    db = _db()
    return int(db.session.execute(select(func.count()).where(ULASAN.c.status == "menunggu")).scalar() or 0)


def moderasi(ulasan_id: int, status: str, moderator: str, alasan: str = "") -> dict | None:
    db = _db()
    lama = ambil(ulasan_id)
    with db.engine.begin() as c:
        c.execute(ULASAN.update().where(ULASAN.c.id == ulasan_id).values(
            status=status, moderator=moderator, alasan=alasan[:500] or None,
            dimoderasi=datetime.now(timezone.utc).replace(tzinfo=None)))
        u = ambil(ulasan_id, c)
    if u and status == "tampil" and lama and lama["status"] != "tampil":
        beri_tahu(u)                                  # baru terlihat sekarang: kirim pemberitahuan @sebut / balasan
    return u


def hapus(ulasan_id: int) -> None:
    db = _db()
    with db.engine.begin() as c:
        c.execute(ULASAN.delete().where(ULASAN.c.id == ulasan_id))
