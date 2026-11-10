"""Jejak audit ALDx: satu tabel untuk semua aksi penting (K5).

Dicatat otomatis:
    buka        membuka dashboard / chart (halaman, bukan tiap permintaan data)  (after_request)
    login       berhasil, gagal, akun dikunci, kunci dibuka           (sps_security, sps_kunci)
    data        unduh/ekspor data chart & SQL Lab (CSV, Excel, ...)     (after_request, tabel ATURAN)
    objek       ekspor/impor dashboard, chart, dataset bawaan Superset  (after_request)
    keamanan    ubah pengguna, role, aturan hak akses data (RLS)        (after_request)
    koneksi     tambah/ubah/hapus koneksi database                       (after_request)
    berkas      ekspor/impor berkas .ald / .aldx                         (sps_berkas)
    ulasan      moderasi komentar                                        (sps_ulasan)
Perubahan pengaturan Pusat Kendali tetap di sps_server_riwayat; tab Riwayat menampilkan keduanya.

Tabel sps_audit (database metadata): waktu, oleh, alamat (IP), kelompok, aksi, objek, rincian (JSON).
Pencatatan TIDAK PERNAH menggagalkan permintaan: galat hanya ditulis ke log.

Pakai dari kode lain:
    import sps_audit
    sps_audit.catat("berkas", "Ekspor berkas", "Dashboard Penjualan", {"format": "aldx"})
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, delete, insert, select

log = logging.getLogger(__name__)

_meta = MetaData()
AUDIT = Table("sps_audit", _meta,
              Column("id", Integer, primary_key=True, autoincrement=True),
              Column("waktu", DateTime, index=True), Column("oleh", String(128)), Column("alamat", String(64)),
              Column("kelompok", String(20), index=True), Column("aksi", String(80)),
              Column("objek", String(250)), Column("rincian", Text))

KELOMPOK = {"buka": "Buka dashboard/chart", "login": "Login", "data": "Unduh data", "objek": "Ekspor/impor objek", "keamanan": "Pengguna & hak akses",
            "koneksi": "Koneksi data", "berkas": "Berkas .ald/.aldx", "ulasan": "Moderasi ulasan",
            "ai": "Asisten AI"}

# (metode, pola alamat, kelompok, aksi). Dicatat bila jawaban sukses (status < 400).
ATURAN = [
    ("GET", r"^/api/v1/dashboard/export/", "objek", "Ekspor dashboard"),
    ("GET", r"^/api/v1/chart/export/", "objek", "Ekspor chart"),
    ("GET", r"^/api/v1/dataset/export/", "objek", "Ekspor dataset"),
    ("POST", r"^/api/v1/(dashboard|chart|dataset|assets)/import/", "objek", "Impor objek"),
    ("GET", r"^/api/v1/sqllab/export/", "data", "Unduh hasil SQL Lab"),
    ("POST", r"^/api/v1/sqllab/export_streaming/", "data", "Unduh hasil SQL Lab"),
    ("POST", r"^/api/v1/security/users/?$", "keamanan", "Tambah pengguna"),
    ("PUT", r"^/api/v1/security/users/\d+", "keamanan", "Ubah pengguna"),
    ("DELETE", r"^/api/v1/security/users/\d+", "keamanan", "Hapus pengguna"),
    ("POST", r"^/api/v1/security/roles/?$", "keamanan", "Tambah role"),
    ("PUT", r"^/api/v1/security/roles/\d+", "keamanan", "Ubah role"),
    ("POST", r"^/api/v1/security/roles/\d+/(permissions|users)", "keamanan", "Ubah isi role"),
    ("DELETE", r"^/api/v1/security/roles/\d+", "keamanan", "Hapus role"),
    ("POST", r"^/api/v1/rowlevelsecurity/?$", "keamanan", "Tambah aturan hak akses data"),
    ("PUT", r"^/api/v1/rowlevelsecurity/\d+", "keamanan", "Ubah aturan hak akses data"),
    ("DELETE", r"^/api/v1/rowlevelsecurity/", "keamanan", "Hapus aturan hak akses data"),
    ("POST", r"^/api/v1/database/?$", "koneksi", "Tambah koneksi"),
    ("PUT", r"^/api/v1/database/\d+$", "koneksi", "Ubah koneksi"),
    ("DELETE", r"^/api/v1/database/\d+$", "koneksi", "Hapus koneksi"),
    ("POST", r"^/hubungkan/api/simpan$", "koneksi", "Tambah koneksi (Hubungkan data)"),
]
_ATURAN = [(m, re.compile(p), k, a) for m, p, k, a in ATURAN]


def _engine():
    from sps_server import penyimpanan
    return penyimpanan.engine()


def pastikan_tabel() -> None:
    _meta.create_all(bind=_engine(), checkfirst=True)


def _alamat() -> str:
    from flask import has_request_context, request
    if not has_request_context():
        return ""
    return (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "") or request.remote_addr or "")[:64]


def _pengguna() -> str:
    from flask import g, has_request_context
    if not has_request_context():
        return "sistem"
    u = getattr(g, "user", None)
    return getattr(u, "username", None) or "anonim"


def catat(kelompok: str, aksi: str, objek: str = "", rincian: dict | None = None, oleh: str | None = None) -> None:
    """Tulis satu baris audit. Tidak pernah melempar galat."""
    baris = dict(waktu=datetime.now(), oleh=(oleh or _pengguna())[:128], alamat=_alamat(), kelompok=kelompok[:20],
                 aksi=aksi[:80], objek=str(objek or "")[:250],
                 rincian=json.dumps(rincian, ensure_ascii=False, default=str) if rincian else None)
    for percobaan in (1, 2):
        try:
            with _engine().begin() as c:
                c.execute(insert(AUDIT).values(**baris))
            return
        except Exception as exc:  # noqa: BLE001
            if percobaan == 1:
                try:
                    pastikan_tabel()          # tabel belum ada (instalasi lama): buat lalu coba sekali lagi
                    continue
                except Exception:  # noqa: BLE001
                    pass
            log.warning("ALDx audit: gagal mencatat %s/%s (%s)", kelompok, aksi, exc)
            return


def daftar(batas: int = 300, kelompok: str = "", cari: str = "", hari: int = 0) -> list[dict]:
    q = select(AUDIT).order_by(AUDIT.c.id.desc()).limit(max(1, min(int(batas), 5000)))
    if kelompok:
        q = q.where(AUDIT.c.kelompok == kelompok)
    if cari:
        pola = f"%{cari}%"
        q = q.where(AUDIT.c.oleh.ilike(pola) | AUDIT.c.objek.ilike(pola) | AUDIT.c.aksi.ilike(pola))
    if hari:
        q = q.where(AUDIT.c.waktu >= datetime.now() - timedelta(days=int(hari)))
    with _engine().connect() as c:
        return [{**r, "waktu": r["waktu"].isoformat(sep=" ", timespec="seconds"),
                 "kelompok_label": KELOMPOK.get(r["kelompok"], r["kelompok"])} for r in c.execute(q).mappings()]


def ke_csv(baris: list[dict]) -> str:
    keluar = io.StringIO()
    w = csv.writer(keluar, delimiter=";")
    w.writerow(["Waktu", "Oleh", "Alamat IP", "Kelompok", "Aksi", "Objek", "Rincian"])
    for r in baris:
        w.writerow([r["waktu"], r["oleh"], r["alamat"], r["kelompok_label"], r["aksi"], r["objek"], r["rincian"] or ""])
    return "﻿" + keluar.getvalue()          # BOM: Excel membaca UTF-8 dengan benar


def bersihkan(hari: int) -> int:
    """Hapus baris lebih tua dari `hari` hari. Kembalikan jumlah baris terhapus."""
    with _engine().begin() as c:
        return c.execute(delete(AUDIT).where(AUDIT.c.waktu < datetime.now() - timedelta(days=hari))).rowcount


# --- Pencatatan otomatis dari permintaan HTTP ----------------------------------------------------
def _format_unduh() -> str:
    """Format unduhan pada /api/v1/chart/data, '' bila hanya menampilkan chart.

    Menampilkan chart = body JSON dengan result_format "json". Unduhan dari menu chart dikirim sebagai formulir
    (field form_data) atau ber-format csv/xlsx. Jadi json hanya dihitung unduhan bila lewat formulir.
    """
    from flask import request
    try:
        isi = request.form.get("form_data") if request.form else None
        data = json.loads(isi) if isi else (request.get_json(silent=True) or {})
        f = str(data.get("result_format") or "").lower()
        if f in ("csv", "xlsx") or (f == "json" and isi):
            return f
        return ""
    except Exception:  # noqa: BLE001
        return ""


_BUKA_DASHBOARD = re.compile(r"^/superset/dashboard/([^/]+)/?$")


def _judul_dashboard(kunci: str) -> str:
    from superset import db
    from superset.models.dashboard import Dashboard
    q = db.session.query(Dashboard.dashboard_title)
    r = (q.filter(Dashboard.id == int(kunci)) if kunci.isdigit() else q.filter(Dashboard.slug == kunci)).first()
    return r[0] if r else kunci


def _judul_chart(kunci: str) -> str:
    from superset import db
    from superset.models.slice import Slice
    r = db.session.query(Slice.slice_name).filter(Slice.id == int(kunci)).first() if kunci.isdigit() else None
    return r[0] if r else kunci


def _setelah(resp):
    from flask import request
    try:
        if resp.status_code >= 400:
            return resp
        if request.method == "GET" and resp.mimetype == "text/html":     # siapa membuka apa (halaman saja)
            m = _BUKA_DASHBOARD.match(request.path)
            if m:
                catat("buka", "Buka dashboard", _judul_dashboard(m.group(1)))
            elif request.path.rstrip("/") == "/explore" and request.args.get("slice_id"):
                catat("buka", "Buka chart", _judul_chart(request.args.get("slice_id", "")))
            return resp
        if request.method in ("GET", "HEAD", "OPTIONS") and "/export" not in request.path:
            return resp
        path = request.path
        if request.method == "POST" and path.startswith("/api/v1/chart/data"):
            f = _format_unduh()
            if f:
                catat("data", "Unduh data chart", request.args.get("slice_id", "") or "chart", {"format": f})
            return resp
        for metode, pola, kelompok, aksi in _ATURAN:
            if request.method == metode and pola.search(path):
                objek = path.rstrip("/").rsplit("/", 1)[-1]
                rincian = {"q": request.args.get("q")} if request.args.get("q") else None
                catat(kelompok, aksi, objek if objek.isdigit() else "", rincian)
                break
    except Exception as exc:  # noqa: BLE001
        log.warning("ALDx audit: %s", exc)
    return resp


def pasang(app) -> None:
    """Dipanggil FLASK_APP_MUTATOR."""
    with app.app_context():
        try:
            pastikan_tabel()
            import sps_kunci
            sps_kunci.pastikan_tabel()
            from sps_server import penyimpanan
            hari = int(penyimpanan.nilai_semua().get("keamanan.audit_simpan_hari", 365))
            terhapus = bersihkan(hari)
            if terhapus:
                log.info("ALDx audit: %d catatan lebih tua dari %d hari dihapus", terhapus, hari)
        except Exception as exc:  # noqa: BLE001 - database belum siap: dicoba lagi saat pencatatan pertama
            log.warning("ALDx audit: tabel belum dibuat (%s)", exc)
    app.after_request(_setelah)
