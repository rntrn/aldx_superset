"""Menerjemahkan pengaturan pusat (skema.py) menjadi konfigurasi Superset.

Dipanggil dari dua tempat:
    terapkan_ke_config(globals())  - akhir superset_config.py, saat proses start
    pasang(app)                    - FLASK_APP_MUTATOR: muat ulang pengaturan "langsung"
                                     tiap ~10 detik + penjaga upload Excel/CSV
"""

from __future__ import annotations

import hashlib
import os
import logging
import re
import time
from datetime import timedelta
from typing import Any

from sps_server import lingkungan, penyimpanan, tuning

log = logging.getLogger(__name__)

DETIK_CEK_ULANG = 10
DB_REDIS = {"broker": 0, "cache": 1, "status": 2, "hasil_sqllab": 3, "batas_laju": 4, "async": 5}
UPLOAD_PATH = re.compile(r"^/api/v1/database/(\d+)/upload/?$")


# --- Pengaturan "langsung" (boleh berubah saat Superset berjalan) -----------------------------
def config_langsung(atur: dict[str, Any]) -> dict[str, Any]:
    jenis = set(atur["upload.jenis"])
    return {
        "ROW_LIMIT": atur["batas.baris_chart"],
        "SQL_MAX_ROW": atur["batas.baris_sql"],
        "DISPLAY_MAX_ROW": atur["batas.baris_tampil_sql"],
        "SAMPLES_ROW_LIMIT": atur["batas.baris_sampel"],
        "FILTER_SELECT_ROW_LIMIT": atur["batas.baris_filter"],
        "SUPERSET_WEBSERVER_TIMEOUT": atur["timeout.chart_detik"],
        "SQLLAB_TIMEOUT": atur["timeout.sqllab_detik"],
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=atur["timeout.sesi_menit"]),
        "ALLOWED_EXTENSIONS": jenis,
        "CSV_EXTENSIONS": jenis & {"csv", "tsv", "txt"},
        "EXCEL_EXTENSIONS": jenis & {"xlsx", "xls"},
        "COLUMNAR_EXTENSIONS": jenis & {"parquet", "zip"},
        "SPS_SERVER": atur,                                   # dibaca penjaga upload
    }


def _timeout_cache(atur: dict[str, Any]) -> int:
    return max(1, int(atur["cache.data_detik"]))          # 0 berarti "praktis tanpa cache"


# --- Saat start ---------------------------------------------------------------------------------
def terapkan_ke_config(ns: dict[str, Any]) -> None:
    """Isi namespace superset_config dengan nilai dari pengaturan pusat."""
    atur = penyimpanan.nilai_semua()
    ns.update(config_langsung(atur))
    ns["SPS_SERVER_SAAT_START"] = dict(atur)                # untuk deteksi "menunggu diterapkan"
    ns["SQLLAB_ASYNC_TIME_LIMIT_SEC"] = atur["timeout.sqllab_async_detik"]

    # Superset berada di belakang gateway (nginx): pakai IP asli klien untuk batas laju & log.
    ns["ENABLE_PROXY_FIX"] = True
    if os.environ.get("SPS_HTTPS", "").strip() in ("1", "ya", "true"):   # gateway HTTPS: cookie hanya lewat HTTPS
        ns["SESSION_COOKIE_SECURE"] = True
        ns["PREFERRED_URL_SCHEME"] = "https"
    # Host & port TIDAK diambil dari header: gateway meneruskan Host asli (mis. localhost:8088).
    ns["PROXY_FIX_CONFIG"] = {"x_for": 1, "x_proto": 1, "x_host": 0, "x_port": 0, "x_prefix": 0}

    r = lingkungan.redis()
    _batas_laju(ns, atur, r)
    if not r.aktif:
        log.warning("ALDx server: REDIS_HOST kosong -> tanpa cache server & backgrounder")
        ns["DATA_CACHE_CONFIG"] = {"CACHE_TYPE": "SimpleCache",
                                   "CACHE_DEFAULT_TIMEOUT": _timeout_cache(atur)}
        return
    _cache(ns, atur, r)
    _backgrounder(ns, atur, r)


def _redis_cache(r: lingkungan.Redis, db: int, awalan: str, timeout: int) -> dict[str, Any]:
    return {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": r.url(db),
            "CACHE_KEY_PREFIX": awalan, "CACHE_DEFAULT_TIMEOUT": timeout}


def _cache(ns: dict[str, Any], atur: dict[str, Any], r: lingkungan.Redis) -> None:
    from flask_caching.backends.rediscache import RedisCache

    db = DB_REDIS["cache"]
    ns["CACHE_CONFIG"] = _redis_cache(r, db, "sps_meta_", 3600)
    ns["DATA_CACHE_CONFIG"] = _redis_cache(r, db, "sps_data_", _timeout_cache(atur))
    ns["FILTER_STATE_CACHE_CONFIG"] = _redis_cache(r, DB_REDIS["status"], "sps_filter_",
                                                   atur["cache.filter_detik"])
    ns["EXPLORE_FORM_DATA_CACHE_CONFIG"] = _redis_cache(r, DB_REDIS["status"], "sps_explore_",
                                                        atur["cache.filter_detik"])
    ns["RESULTS_BACKEND"] = RedisCache(host=r.host, port=r.port, password=r.password or None,
                                       db=DB_REDIS["hasil_sqllab"], key_prefix="sps_sqllab_")


def _batas_laju(ns: dict[str, Any], atur: dict[str, Any], r: lingkungan.Redis) -> None:
    ns["RATELIMIT_ENABLED"] = True
    ns["RATELIMIT_APPLICATION"] = f"{atur['gateway.permintaan_per_detik']} per second"
    ns["RATELIMIT_STORAGE_URI"] = r.url(DB_REDIS["batas_laju"]) if r.aktif else "memory://"
    # Redis mati sesaat tidak boleh membuat login gagal: pakai memori sementara.
    ns["RATELIMIT_IN_MEMORY_FALLBACK_ENABLED"] = True
    ns["RATELIMIT_SWALLOW_ERRORS"] = True
    ns["AUTH_RATE_LIMITED"] = True
    ns["AUTH_RATE_LIMIT"] = f"{atur['gateway.login_per_menit']} per minute"


def _backgrounder(ns: dict[str, Any], atur: dict[str, Any], r: lingkungan.Redis) -> None:
    from celery.schedules import crontab

    rute = {tugas: {"queue": antrean} for antrean, daftar in tuning.ANTREAN.items() for tugas in daftar}
    jadwal: dict[str, Any] = {
        "reports.scheduler": {"task": "reports.scheduler", "schedule": crontab(minute="*", hour="*")},
        "reports.prune_log": {"task": "reports.prune_log", "schedule": crontab(minute=0, hour=0)},
        "sps.ekstrak.jadwal": {"task": "sps.ekstrak.jadwal", "schedule": crontab(minute="*/5")},
        "sps.ramalan.segarkan": {"task": "sps.ramalan.segarkan", "schedule": crontab(minute=0, hour=3)},
        "sps.warna.kunci": {"task": "sps.warna.kunci", "schedule": crontab(minute=30, hour=2)},
        "prune_logs": {"task": "prune_logs", "schedule": crontab(minute=30, hour=1),
                       "kwargs": {"retention_period_days": atur["gateway.log_simpan_hari"],
                                  "max_rows_per_run": 50000}},
    }
    if atur["cache.pemanasan_aktif"]:
        jadwal["cache-warmup"] = {
            "task": "cache-warmup", "schedule": crontab(minute=0, hour=atur["cache.pemanasan_jam"]),
            "kwargs": {"strategy_name": "top_n_dashboards", "top_n": atur["cache.pemanasan_jumlah"],
                       "since": "7 days ago"}}

    class CeleryConfig:  # pylint: disable=too-few-public-methods
        broker_url = r.url(DB_REDIS["broker"])
        result_backend = r.url(DB_REDIS["broker"])
        # superset.tasks.async_queries TIDAK didaftarkan di sini: modul itu dimuat Superset
        # sendiri (butuh app context) saat fitur chart async aktif.
        imports = ("superset.sql_lab", "superset.sql.execution.celery_task", "superset.tasks.scheduler",
                   "superset.tasks.thumbnails", "superset.tasks.cache", "sps_engine.tugas",
                   "sps_berkas.tugas", "sps_warna")
        task_routes = rute
        task_default_queue = "laporan"
        worker_prefetch_multiplier = 1
        task_acks_late = False
        beat_schedule = jadwal
        broker_connection_retry_on_startup = True

    ns["CELERY_CONFIG"] = CeleryConfig
    ns["WEBDRIVER_BASEURL"] = "http://superset:8088/"       # pemanasan cache memanggil web lokal

    if atur["fitur.chart_async"]:
        ns.setdefault("FEATURE_FLAGS", {})["GLOBAL_ASYNC_QUERIES"] = True
        ns["GLOBAL_ASYNC_QUERIES_CACHE_BACKEND"] = {
            "CACHE_TYPE": "RedisCache", "CACHE_REDIS_HOST": r.host, "CACHE_REDIS_PORT": r.port,
            "CACHE_REDIS_PASSWORD": r.password, "CACHE_REDIS_DB": DB_REDIS["async"]}
        ns["GLOBAL_ASYNC_QUERIES_JWT_SECRET"] = hashlib.sha256(
            (ns["SECRET_KEY"] + "|async").encode()).hexdigest()
        ns["GLOBAL_ASYNC_QUERIES_TRANSPORT"] = "polling"


# --- Saat berjalan --------------------------------------------------------------------------------
def pasang(app) -> None:
    """Muat ulang pengaturan 'langsung' secara berkala + jaga batas upload."""
    from flask import jsonify, request

    status = {"cek": 0.0, "versi": None}

    @app.before_request
    def _muat_ulang_pengaturan():
        if time.monotonic() - status["cek"] < DETIK_CEK_ULANG:
            return
        status["cek"] = time.monotonic()
        try:
            v = penyimpanan.versi()
            if v != status["versi"]:
                atur = penyimpanan.nilai_semua()
                app.config.update(config_langsung(atur))
                app.config["DATA_CACHE_CONFIG"]["CACHE_DEFAULT_TIMEOUT"] = _timeout_cache(atur)
                if status["versi"] is not None:
                    log.info("ALDx server: pengaturan langsung dimuat ulang (versi %s)", v)
                status["versi"] = v
        except Exception:  # noqa: BLE001 - jangan ganggu permintaan pengguna
            log.exception("ALDx server: gagal memuat ulang pengaturan")

    @app.before_request
    def _jaga_upload():
        if request.method != "POST" or not UPLOAD_PATH.match(request.path):
            return None
        atur = app.config["SPS_SERVER"]
        if not atur["upload.aktif"]:
            return jsonify(message="Upload Excel/CSV sedang dinonaktifkan admin."), 403
        batas = atur["upload.ukuran_mb"] * 1024 * 1024                  # 0 = tanpa batas
        if batas and (request.content_length or 0) > batas:
            return jsonify(message=f"File terlalu besar. Maksimal {atur['upload.ukuran_mb']} MB."), 413
        return None

    _batasi_baris_upload(app)


def _batasi_baris_upload(app) -> None:
    """Tolak file yang barisnya melebihi upload.baris_maks (dicek setelah file dibaca)."""
    from superset.commands.database.exceptions import DatabaseUploadFailed
    from superset.commands.database.uploaders.base import BaseDataReader

    if getattr(BaseDataReader, "_sps_dibatasi", False):
        return
    asli = BaseDataReader._dataframe_to_database

    def _dataframe_to_database(self, df, database, table_name, schema_name):
        maks = app.config["SPS_SERVER"]["upload.baris_maks"]
        if maks and len(df) > maks:                                    # 0 = tanpa batas
            raise DatabaseUploadFailed(
                message=f"File berisi {len(df):,} baris; maksimal {maks:,} baris.".replace(",", "."))
        return asli(self, df, database, table_name, schema_name)

    BaseDataReader._dataframe_to_database = _dataframe_to_database
    BaseDataReader._sps_dibatasi = True
