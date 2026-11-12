"""Halaman & API Asisten AI, dipasang di dalam aplikasi Superset (/asisten/).

Karena berjalan di dalam Superset: login, sesi, CSRF, dan hak akses yang sama
dipakai. Semua API butuh login dan role di `peran_boleh` (ai.yaml) atau Admin.
"""

from __future__ import annotations

import logging
import re
from functools import wraps
from pathlib import Path

from flask import Blueprint, g, jsonify, redirect, render_template_string, request

from sps_ai import agen, alat, auto, pengaturan, peran, story

log = logging.getLogger(__name__)
FOLDER = Path(__file__).resolve().parent
bp = Blueprint("sps_ai", __name__, url_prefix="/asisten")
MENU = "Asisten AI"


# --- Akses ---------------------------------------------------------------------------
def _boleh(user) -> bool:
    from superset import security_manager
    if security_manager.is_admin():
        return True
    boleh = set(pengaturan.muat(hanya_aktif=False).peran_boleh)
    return any(r.name in boleh for r in user.roles)


def _butuh_akses(halaman: bool = False):
    def dekor(fungsi):
        @wraps(fungsi)
        def bungkus(*args, **kwargs):
            from flask_login import current_user
            if not current_user.is_authenticated:
                return redirect(f"/login/?next={request.path}") if halaman else (jsonify(error="Belum login"), 401)
            g.user = current_user._get_current_object()
            if not _boleh(g.user):
                pesan = "Anda belum diberi akses Asisten AI. Hubungi admin aplikasi."
                return (pesan, 403) if halaman else (jsonify(error=pesan), 403)
            return _aman(fungsi, *args, **kwargs)
        return bungkus
    return dekor


def _aman(fungsi, *args, **kwargs):
    """Ubah error menjadi pesan yang jelas untuk pengguna."""
    from superset import db
    from superset.exceptions import SupersetSecurityException
    from sps_ai.llm import GagalModel
    error_db = _error_db()
    try:
        return fungsi(*args, **kwargs)
    except (alat.IzinDitolak, SupersetSecurityException) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (alat.InputSalah, LookupError, ValueError, KeyError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400
    except GagalModel as exc:
        return jsonify(error=str(exc)), 502
    except error_db as exc:
        db.session.rollback()
        log.warning("ALDx AI: database sumber gagal: %s", exc)
        return jsonify(error="Database sumber data tidak bisa dihubungi atau query gagal. "
                             "Coba lagi nanti / hubungi admin. Detail: " + str(exc)[:200]), 502
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.exception("ALDx AI: error tak terduga")
        return jsonify(error=f"Terjadi kesalahan: {exc}"), 500


def _error_db() -> tuple:
    from sqlalchemy.exc import DBAPIError
    from superset.commands.chart.exceptions import ChartDataQueryFailedError
    return (DBAPIError, ChartDataQueryFailedError)


def _halaman(nama_file: str, **konteks):
    from flask_wtf.csrf import generate_csrf
    html = (FOLDER / nama_file).read_text(encoding="utf-8")
    from flask import current_app
    return render_template_string(html, csrf=generate_csrf(),
                                  app_name=current_app.config.get("APP_NAME", "ALDx"), **konteks)


def _data() -> dict:
    return request.get_json(silent=True) or {}


# --- Halaman -----------------------------------------------------------------------------
@bp.route("/tab.js")
def tab_js():
    """Skrip tab Asisten AI di Pusat Kendali (data tetap lewat API yang memeriksa hak akses)."""
    from flask import Response
    return Response((FOLDER / "tab.js").read_text(encoding="utf-8"), mimetype="text/javascript")


@bp.route("/")
@_butuh_akses(halaman=True)
def beranda():
    return _halaman("halaman.html")


@bp.route("/story/<int:story_id>")
@_butuh_akses(halaman=True)
def putar_story(story_id: int):
    return _halaman("story.html", story_id=story_id)


# --- API umum ---------------------------------------------------------------------------
@bp.route("/api/awal")
@_butuh_akses()
def api_awal():
    from superset import security_manager
    atur = pengaturan.muat()
    return jsonify(
        model=[m.publik for m in atur.model], bawaan=atur.cari_model(None).id if atur.model else "",
        dataset=alat.daftar_dataset(), user=g.user.username,
        boleh_buat=security_manager.can_access("can_write", "Chart"),
        boleh_dashboard=security_manager.can_access("can_write", "Dashboard"),
    )


@bp.route("/api/dataset/<int:dataset_id>")
@_butuh_akses()
def api_dataset(dataset_id: int):
    return jsonify(alat.info_dataset(dataset_id))


@bp.route("/api/dashboard")
@_butuh_akses()
def api_dashboard():
    return jsonify(alat.daftar_dashboard(request.args.get("q", ""), hanya_siap=request.args.get("siap") == "1"))


# --- Tanya AI ---------------------------------------------------------------------------
@bp.route("/api/peran")
@_butuh_akses()
def api_peran():
    """Peran ahli yang boleh dipakai pengguna ini + model aktif (panel AI di cangkang)."""
    atur = pengaturan.muat()
    return jsonify(peran=[p.publik for p in peran.tersedia()], model=[m.publik for m in atur.model],
                   bawaan=atur.cari_model(None).id if atur.model else "")


@bp.route("/api/chat", methods=["POST"])
@_butuh_akses()
def api_chat():
    """{riwayat, model?, peran?, konteks?: {alamat, judul}} -> {jawaban, peristiwa, status, peran}."""
    from sps_app.tampilan import bahasa_aktif
    d = _data()
    atur = pengaturan.muat()
    model = atur.cari_model(d.get("model"))
    konteks = d.get("konteks") if isinstance(d.get("konteks"), dict) else None
    if konteks:
        konteks = {k: str(konteks.get(k) or "")[:lim] for k, lim in (("alamat", 400), ("judul", 120), ("teks", 4000))}
    return jsonify(agen.jawab(d.get("riwayat") or [], model, atur, g.user.username,
                              peran.ambil(d.get("peran")), konteks, bahasa_aktif()))


# --- Auto chart / dashboard ---------------------------------------------------------------
@bp.route("/api/auto/saran", methods=["POST"])
@_butuh_akses()
def api_auto_saran():
    d = _data()
    return jsonify(auto.sarankan(int(d["dataset_id"]), d.get("fokus", ""), d.get("dimensi") or None,
                                 int(d.get("jumlah") or 20)))


@bp.route("/api/auto/buat", methods=["POST"])
@_butuh_akses()
def api_auto_buat():
    d = _data()
    return jsonify(auto.buat_dari_saran(int(d["dataset_id"]), d.get("pilihan") or [],
                                        d.get("judul_dashboard", "")))


# --- Story ----------------------------------------------------------------------------------
@bp.route("/api/story")
@_butuh_akses()
def api_story_daftar():
    return jsonify(story.daftar())


@bp.route("/api/story", methods=["POST"])
@_butuh_akses()
def api_story_baru():
    return jsonify(story.simpan(_data()))


@bp.route("/api/story/<int:story_id>", methods=["GET", "POST", "DELETE"])
@_butuh_akses()
def api_story(story_id: int):
    if request.method == "POST":
        return jsonify(story.simpan(_data(), story_id))
    if request.method == "DELETE":
        story.hapus(story_id)
        return jsonify(ok=True)
    return jsonify(story.ambil(story_id))


@bp.route("/api/story/narasi", methods=["POST"])
@_butuh_akses()
def api_story_narasi():
    d = _data()
    atur = pengaturan.muat()
    dash = next((x for x in alat.daftar_dashboard() if x["id"] == int(d["dashboard_id"])), None)
    if dash is None:
        raise alat.IzinDitolak("Dashboard tidak ditemukan atau tidak boleh Anda akses.")
    return jsonify(narasi=agen.tulis_narasi(atur.cari_model(d.get("model")), atur,
                                            d.get("judul_story", ""), dash))


# --- Sambungkan AI (panel Asisten AI saat belum ada model, dan Pusat Kendali › Asisten AI) -----------
# Langkah memasang tiap aplikasi lokal (satu sumber untuk panel AI & Pusat Kendali).
# Elemen daftar: teks, atau [teks, perintah yang bisa disalin].
LANGKAH_LOKAL = {
    "Ollama": {"unduh": "https://ollama.com/download", "langkah": [
        "Unduh & pasang Ollama untuk Windows, lalu buka (ikon llama muncul di pojok kanan bawah).",
        ["Unduh model sekali (±2,5 GB), di PowerShell:", "ollama pull qwen3:4b"],
        "Klik Periksa lagi. Model langsung muncul, tanpa restart."]},
    "LM Studio": {"unduh": "https://lmstudio.ai/download", "langkah": [
        "Unduh & pasang LM Studio, lalu buka.",
        "Tab Discover: cari \"qwen3\" (4B untuk laptop, 8B–14B bila RAM ≥ 16 GB) › Download.",
        "Tab Developer: nyalakan Start server (port 1234) + Serve on Local Network, lalu Periksa lagi."]},
    "Jan": {"unduh": "https://jan.ai/download", "langkah": [
        "Unduh & pasang Jan, unduh model dari Hub (mis. Qwen3).",
        "Settings › Local API Server › Start (port 1337), lalu Periksa lagi."]},
    "llama.cpp": {"unduh": "https://github.com/ggml-org/llama.cpp/releases", "langkah": [
        ["Jalankan server dengan model GGUF:", "llama-server -m model.gguf --port 8080 --host 0.0.0.0 --jinja"],
        "Lalu Periksa lagi."]},
}


def _boleh_atur() -> bool:
    from superset import security_manager
    return security_manager.is_admin()


def _daftar_cloud(data: dict) -> list[dict]:
    """Layanan cloud dari ai.yaml, dikelompokkan per key (satu key bisa dipakai beberapa model)."""
    import os
    from sps_ai import kunci_api
    tersimpan = kunci_api.semua()
    hasil: dict[str, dict] = {}
    for m in data.get("model") or []:
        env = (m.get("api_key_env") or "").strip()
        if not env:
            continue
        di_env = os.environ.get(env, "").strip()
        nilai = di_env or tersimpan.get(env, "")
        x = hasil.setdefault(env, {
            "env": env, "kategori": str(m.get("kategori") or "berbayar"), "url_key": str(m.get("url_key") or ""),
            "layanan": re.sub(r"\s*\(.*?\)|^API\s+", "", str(m.get("nama", m["id"])).split("—")[-1].strip()).strip(),
            "model": [], "terisi": bool(nilai), "sumber": "env" if di_env else ("aplikasi" if nilai else ""),
            "samar": kunci_api.samar(nilai) if nilai else "",
        })
        x["model"].append(str(m.get("nama", m["id"])).split("—")[0].strip())
    return list(hasil.values())


@bp.route("/api/sambungan")
@_butuh_akses()
def api_sambungan():
    """Keadaan semua jalur AI: server lokal (+ model yang sudah diunduh) dan layanan cloud."""
    from sps_ai import status
    if request.args.get("segarkan") == "1":
        status.lupakan()
    data = pengaturan.baca_yaml()
    atur = pengaturan.muat()
    lokal = [{**s, "port": s["base_url"].rsplit(":", 1)[-1].split("/")[0], **LANGKAH_LOKAL.get(s["nama"], {})}
             for s in status.temukan(pengaturan.sumber_lokal(data))]
    boleh = _boleh_atur()
    cloud = _daftar_cloud(data)
    if not boleh:                                   # pengguna biasa cukup tahu ada/tidaknya
        cloud = [{k: v for k, v in c.items() if k not in ("samar", "sumber")} for c in cloud]
    model = [{**m.publik, "jalur": "cloud" if m.api_key else "lokal"} for m in atur.model]
    return jsonify(lokal=lokal, cloud=cloud, boleh_atur=boleh, model=model,
                   bawaan=atur.cari_model(None).id if atur.model else "")


@bp.route("/api/bawaan", methods=["POST"])
@_butuh_akses()
def api_bawaan():
    """Admin memilih model yang dipakai pertama kali oleh semua pengguna (menimpa `bawaan:` di ai.yaml)."""
    import sps_audit
    from sps_ai import kunci_api
    if not _boleh_atur():
        return jsonify(error="Hanya Admin yang boleh mengganti model bawaan."), 403
    model_id = str(_data().get("model") or "")
    if model_id and model_id not in {m.id for m in pengaturan.muat().model}:
        raise ValueError("Model itu sedang tidak aktif.")
    kunci_api.simpan(kunci_api.BAWAAN, model_id, g.user.username)
    sps_audit.catat("ai", "model bawaan", model_id or "(ikut ai.yaml)")
    return jsonify(ok=True)


@bp.route("/api/uji", methods=["POST"])
@_butuh_akses()
def api_uji():
    """Uji satu model dengan pertanyaan pendek: apakah menjawab, dan berapa detik."""
    import time
    from sps_ai import llm
    atur = pengaturan.muat()
    model = atur.cari_model(str(_data().get("model") or "") or None)
    mulai = time.monotonic()
    jawab = llm.chat(model, [{"role": "user", "content": "Balas hanya dengan satu kata: siap"}], [], atur.batas_untuk(model))
    teks = str(jawab.get("content") or "").strip()
    return jsonify(ok=True, model=model.nama, detik=round(time.monotonic() - mulai, 1), jawaban=teks[:120])


@bp.route("/api/sambungan", methods=["POST"])
@_butuh_akses()
def api_sambungan_simpan():
    """Admin mengisi / menghapus key cloud. Key diuji dulu ke penyedia sebelum disimpan."""
    import requests
    import sps_audit
    from sps_ai import kunci_api, status
    if not _boleh_atur():
        return jsonify(error="Hanya Admin yang boleh mengisi key AI."), 403
    d = _data()
    env, key = str(d.get("env") or "").strip(), str(d.get("key") or "").strip()
    data = pengaturan.baca_yaml()
    model = [m for m in data.get("model") or [] if env and (m.get("api_key_env") or "").strip() == env]
    if not model:
        raise ValueError("Layanan AI tidak dikenal.")
    if key:
        if len(key) < 10 or any(c.isspace() for c in key):
            raise ValueError("Key tidak valid: salin seluruh key tanpa spasi.")
        try:
            r = requests.get(f"{str(model[0]['base_url']).rstrip('/')}/models", timeout=8,
                             headers={"Authorization": f"Bearer {key}", "x-api-key": key, "anthropic-version": "2023-06-01"},
                             verify=__import__("os").environ.get("AI_CA_BUNDLE") or True)
            if r.status_code in (401, 403):
                raise ValueError("Key ditolak penyedia (401/403). Periksa lagi key yang disalin.")
        except requests.RequestException as exc:
            log.warning("ALDx AI: uji key %s gagal terhubung: %s", env, exc)
            raise ValueError("Penyedia tidak bisa dihubungi dari server (internet / proxy kantor?). "
                             "Key belum disimpan.") from exc
    kunci_api.simpan(env, key, g.user.username)
    status.lupakan()
    sps_audit.catat("ai", "isi key AI" if key else "hapus key AI", env)
    return jsonify(ok=True)


# --- Pemasangan -------------------------------------------------------------------------------
def daftarkan(app) -> None:
    """Dipanggil superset_config.FLASK_APP_MUTATOR: pasang halaman & menu navbar."""
    app.register_blueprint(bp)
    try:
        from superset.extensions import appbuilder
        # Menu selalu tampil bagi yang berhak. Bila belum ada model aktif, panel Asisten AI menampilkan
        # layar "Sambungkan AI" (deteksi model lokal + isi key cloud), bukan menghilang tanpa petunjuk.
        appbuilder.add_link(MENU, href="/asisten/", label=MENU)
    except Exception:  # noqa: BLE001 - menu gagal tidak boleh mematikan Superset
        log.exception("ALDx AI: gagal menambah menu navbar")


def siapkan_izin() -> None:
    """Beri izin menu 'Asisten AI' + akses dataset ke role di peran_boleh (dipanggil build-dashboards)."""
    from superset import security_manager as sm
    pv = sm.add_permission_view_menu("menu_access", MENU)
    for nama in ["Admin", "Superadmin", *pengaturan.muat(hanya_aktif=False).peran_boleh]:
        role = sm.add_role(nama)
        if pv not in role.permissions:
            sm.add_permission_role(role, pv)
