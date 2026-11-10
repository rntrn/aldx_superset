"""Halaman Pusat Kendali Server (/pusat-kendali/) — khusus Admin.

Tab: Status · Topologi · Pengaturan* · Batas data* · Identitas & Tema · Hubungkan data · Ekstrak · Hak akses* · Riwayat
     (* = pengaturan vital, khusus Superadmin; lihat sps_superadmin.py)
"""

from __future__ import annotations

import logging
from functools import wraps
from pathlib import Path

from flask import Blueprint, g, jsonify, redirect, render_template_string, request

import sps_superadmin
from sps_server import batas, izin, monitor, penyimpanan, skema

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
MENU = "Pusat Kendali Server"
bp = Blueprint("sps_server", __name__, url_prefix="/pusat-kendali")


def _khusus_admin(halaman: bool = False):
    def dekor(fungsi):
        @wraps(fungsi)
        def bungkus(*args, **kwargs):
            from flask_login import current_user
            from superset import db, security_manager
            if not current_user.is_authenticated:
                return redirect(f"/login/?next={request.path}") if halaman else (jsonify(error="Belum login"), 401)
            g.user = current_user._get_current_object()
            if not security_manager.is_admin():
                pesan = "Pusat Kendali Server hanya untuk Admin."
                if halaman:
                    from sps_tolak import halaman_tolak
                    return halaman_tolak(pesan)
                return jsonify(error=pesan), 403
            try:
                return fungsi(*args, **kwargs)
            except ValueError as exc:
                db.session.rollback()
                return jsonify(error=str(exc)), 400
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                log.exception("ALDx server: galat halaman")
                return jsonify(error=f"Terjadi kesalahan: {exc}"), 500
        return bungkus
    return dekor


def _data() -> dict:
    return request.get_json(silent=True) or {}


@bp.route("/")
@_khusus_admin(halaman=True)
def beranda():
    from flask import current_app
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / "halaman.html").read_text(encoding="utf-8")
    return render_template_string(html, csrf=generate_csrf(), superadmin=sps_superadmin.adalah(),
                                  app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/api/status")
@_khusus_admin()
def api_status():
    atur = penyimpanan.nilai_semua()
    data = monitor.status()
    node = data["node"] if isinstance(data["node"], list) else []
    data["menunggu"] = monitor.menunggu_diterapkan(atur, node)
    data["rekomendasi"] = monitor.rekomendasi(node, atur)
    return jsonify(data)


@bp.route("/api/pengaturan")
@_khusus_admin()
@sps_superadmin.khusus()
def api_pengaturan():
    from superset import security_manager
    roles = sorted(r.name for r in security_manager.get_all_roles())
    daftar = [{**a.publik, "opsi": roles if a.kunci == "upload.peran" else a.opsi} for a in skema.DAFTAR]
    # grup dikirim sebagai daftar agar urutannya tetap (objek JSON diurutkan abjad oleh Flask)
    return jsonify(grup=list(skema.GRUP.items()), daftar=daftar, nilai=penyimpanan.nilai_semua())


@bp.route("/api/pengaturan", methods=["POST"])
@_khusus_admin()
@sps_superadmin.khusus()
def api_simpan():
    berubah = penyimpanan.simpan(_data().get("perubahan") or {}, g.user.username)
    atur = penyimpanan.nilai_semua()
    catatan = []
    if any(k.startswith("upload.") for k in berubah):
        catatan.append("Upload: " + izin.siapkan_upload(atur))
    if "fitur.sqllab_async" in berubah:
        n = izin.terapkan_sqllab_async(atur["fitur.sqllab_async"])
        catatan.append(f"SQL Lab async {'aktif' if atur['fitur.sqllab_async'] else 'mati'} di {n} koneksi")
    return jsonify(
        berubah=berubah, catatan=catatan,
        langsung=[k for k in berubah if skema.PETA[k].berlaku == skema.LANGSUNG],
        terapkan=[k for k in berubah if skema.PETA[k].berlaku == skema.TERAPKAN])


@bp.route("/api/izin")
@_khusus_admin()
@sps_superadmin.khusus()
def api_izin():
    return jsonify(izin.matriks())


@bp.route("/api/izin", methods=["POST"])
@_khusus_admin()
@sps_superadmin.khusus()
def api_ubah_izin():
    d = _data()
    izin.ubah(str(d.get("role", "")), str(d.get("kemampuan", "")), bool(d.get("aktif")), g.user.username)
    return jsonify(izin.matriks())


@bp.route("/api/batas")
@_khusus_admin()
@sps_superadmin.khusus()
def api_batas():
    """Batas data: nilai berlaku, rekomendasi dari perangkat, pemakaian ALDx Engine."""
    return jsonify(batas.hitung(penyimpanan.nilai_semua()))


@bp.route("/api/riwayat")
@_khusus_admin()
def api_riwayat():
    def label(kunci: str) -> str:
        if kunci.startswith("identitas:"):                  # identitas:<isian>
            from sps_identitas import skema as idn
            k = kunci.split(":", 1)[1]
            return "Identitas: " + (idn.PETA[k].label if k in idn.PETA else k)
        if kunci.startswith("izin:"):                       # izin:<role>:<kemampuan>
            _, role, k = kunci.split(":", 2)
            return f"Hak akses {role}: {izin.PETA[k].label if k in izin.PETA else k}"
        return skema.PETA[kunci].label if kunci in skema.PETA else kunci
    return jsonify([{**r, "label": label(r["kunci"])} for r in penyimpanan.riwayat(200)])


@bp.route("/api/audit")
@_khusus_admin()
def api_audit():
    """Jejak audit (sps_audit). ?kelompok=&cari=&hari=&format=csv"""
    import sps_audit
    baris = sps_audit.daftar(batas=5000 if request.args.get("format") == "csv" else 300,
                             kelompok=request.args.get("kelompok", ""), cari=request.args.get("cari", "")[:80],
                             hari=int(request.args.get("hari") or 0))
    if request.args.get("format") == "csv":
        from flask import Response
        sps_audit.catat("data", "Unduh jejak audit", "audit.csv", {"baris": len(baris)})
        return Response(sps_audit.ke_csv(baris), content_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=jejak-audit.csv"})
    return jsonify(baris=baris, kelompok=sps_audit.KELOMPOK)


@bp.route("/api/terkunci")
@_khusus_admin()
def api_terkunci():
    import sps_kunci
    return jsonify(sps_kunci.daftar_terkunci())


@bp.route("/api/terkunci/buka", methods=["POST"])
@_khusus_admin()
def api_buka_kunci():
    """Buka kunci akun. Akun Superadmin hanya boleh dibuka Superadmin."""
    import sps_kunci
    from superset import security_manager
    nama = str(_data().get("username", "")).strip()
    target = security_manager.find_user(username=nama)
    if target and sps_superadmin.adalah(target) and not sps_superadmin.adalah():
        return jsonify(error="Kunci akun Superadmin hanya bisa dibuka Superadmin."), 403
    sps_kunci.buka(nama, g.user.username)
    return jsonify(sps_kunci.daftar_terkunci())


@bp.route("/api/node/hapus", methods=["POST"])
@_khusus_admin()
@sps_superadmin.khusus()
def api_hapus_node():
    penyimpanan.hapus_node(str(_data().get("nama", "")))
    return jsonify(ok=True)


def daftarkan(app) -> None:
    """Dipanggil FLASK_APP_MUTATOR: pengaturan langsung, penjaga upload, halaman & menu."""
    from sps_server import konfig
    konfig.pasang(app)
    app.register_blueprint(bp)
    try:
        from superset.extensions import appbuilder
        appbuilder.add_link(MENU, href="/pusat-kendali/", label=MENU, category="Manage")
    except Exception:  # noqa: BLE001 - menu gagal tidak boleh mematikan Superset
        log.exception("ALDx server: gagal menambah menu")


def siapkan() -> list[str]:
    """Dipanggil build-dashboards: tabel, izin menu Admin, database upload."""
    from superset import db, security_manager as sm
    penyimpanan.pastikan_tabel()
    pv = sm.add_permission_view_menu("menu_access", MENU)
    admin = sm.find_role("Admin")
    if admin and pv not in admin.permissions:
        sm.add_permission_role(admin, pv)
    db.session.commit()
    atur = penyimpanan.nilai_semua()
    hasil = [f"izin menu '{MENU}' untuk Admin"]
    try:
        hasil.append("upload: " + izin.siapkan_upload(atur))
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        hasil.append(f"upload GAGAL disiapkan ({exc})")
    return hasil
