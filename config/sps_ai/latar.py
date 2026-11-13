"""Asisten AI di latar belakang: pertanyaan tidak lagi dibatasi timeout permintaan web, dan langkahnya tampil langsung.

Alur:
    POST /asisten/api/chat/mulai          -> {"id": "..."}  (agen berjalan di thread terpisah)
    GET  /asisten/api/chat/status/<id>    -> {"status": "jalan"|"selesai"|"gagal", "peristiwa": [...], "hasil": {...}}
    POST /asisten/api/chat/batal/<id>     -> berhenti sebelum langkah berikutnya

Status disimpan di Redis (cache Superset) agar proses web mana pun bisa menjawab pertanyaan status. Tanpa Redis
(CACHE_TYPE bukan Redis) mode latar tidak dipakai; panel memakai /asisten/api/chat biasa.
Satu pengguna hanya boleh punya satu pertanyaan berjalan. Pekerjaan memakai hak akses pemiliknya (override_user)
dan hanya pemiliknya yang boleh melihat statusnya.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid

log = logging.getLogger(__name__)
SIMPAN_DETIK = 3600            # status disimpan selama ini setelah dibuat
AWALAN = "sps_ai_latar:"


def _cache():
    from superset.extensions import cache_manager
    return cache_manager.cache


def tersedia() -> bool:
    from flask import current_app
    return "redis" in str(current_app.config.get("CACHE_CONFIG", {}).get("CACHE_TYPE", "")).lower()


def _baca(kunci: str) -> dict | None:
    return _cache().get(AWALAN + kunci)


def _tulis(kunci: str, isi: dict) -> None:
    _cache().set(AWALAN + kunci, isi, timeout=SIMPAN_DETIK)


def status(job_id: str, username: str) -> dict | None:
    j = _baca(job_id)
    return j if j and j.get("username") == username else None


def batal(job_id: str, username: str) -> bool:
    j = status(job_id, username)
    if not j or j["status"] != "jalan":
        return False
    _tulis(f"batal:{job_id}", {"username": username})
    return True


def mulai(app, user_id: int, username: str, kerja) -> str:
    """Jalankan kerja(kemajuan, dibatalkan) di thread; kembalikan id. kerja mengembalikan dict hasil agen."""
    aktif = _baca(f"pengguna:{username}")
    if aktif and (_baca(aktif["id"]) or {}).get("status") == "jalan":
        raise ValueError("Masih ada pertanyaan yang berjalan. Tunggu selesai atau batalkan dulu.")
    job_id = uuid.uuid4().hex
    _tulis(job_id, {"username": username, "status": "jalan", "peristiwa": [], "mulai": time.time()})
    _tulis(f"pengguna:{username}", {"id": job_id})
    akar = __import__("flask").request.url_root

    def jalan():
        from flask import g
        from superset import db, security_manager as sm
        from superset.utils.core import override_user
        with app.app_context(), app.test_request_context(base_url=akar):
            user = sm.get_user_by_id(user_id)
            g.user = user
            peristiwa: list[dict] = []

            def kemajuan(ev: dict) -> None:
                if ev.get("tipe") == "langkah":
                    peristiwa.append(ev)
                    _tulis(job_id, {"username": username, "status": "jalan", "peristiwa": list(peristiwa),
                                    "mulai": _baca(job_id)["mulai"]})

            try:
                with override_user(user):
                    hasil = kerja(kemajuan, lambda: _baca(f"batal:{job_id}") is not None)
                _tulis(job_id, {"username": username, "status": "selesai", "hasil": hasil, "peristiwa": peristiwa})
            except Exception as exc:  # noqa: BLE001 - galat apa pun dilaporkan ke layar, bukan menghilang
                log.exception("ALDx AI latar %s gagal", username)
                _tulis(job_id, {"username": username, "status": "gagal", "galat": str(exc)[:500], "peristiwa": peristiwa})
            finally:
                db.session.remove()

    threading.Thread(target=jalan, name=f"ai-{job_id[:8]}", daemon=True).start()
    return job_id
