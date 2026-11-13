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
DENYUT_DETIK = 10              # jeda tulis "denyut" selama pekerjaan hidup
BATAS_MATI = 45                # tanpa denyut selama ini = prosesnya mati (server dimulai ulang / pekerja web didaur ulang)
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


def kuota(username: str, batas_per_jam: int) -> bool:
    """Hitung satu pertanyaan; False bila pengguna melewati batas per jam. Tanpa Redis / batas 0 = selalu boleh."""
    from superset import security_manager as sm
    if not batas_per_jam or sm.is_admin() or not tersedia():
        return True
    kunci = f"kuota:{username}:{int(time.time() // 3600)}"
    n = (_baca(kunci) or {}).get("n", 0) + 1
    _cache().set(AWALAN + kunci, {"n": n}, timeout=3700)
    return n <= batas_per_jam


def status(job_id: str, username: str, sekarang: float | None = None) -> dict | None:
    """Status milik pengguna. Pekerjaan 'jalan' yang denyutnya berhenti ditandai gagal (thread mati bersama
    prosesnya), supaya layar tidak menunggu selamanya dan pengguna bisa bertanya lagi."""
    j = _baca(job_id)
    if not j or j.get("username") != username:
        return None
    sekarang = sekarang or time.time()
    if j.get("status") == "jalan":
        terakhir = (_baca(f"denyut:{job_id}") or {}).get("t") or j.get("mulai") or 0
        if sekarang - terakhir > BATAS_MATI:
            j = {**j, "status": "gagal", "galat": "Proses Asisten terhenti (server dimulai ulang atau proses web didaur "
                                                   "ulang). Hasil yang sudah tersimpan tetap ada; ulangi pertanyaan Anda."}
            _tulis(job_id, j)
    return j


def batal(job_id: str, username: str) -> bool:
    j = status(job_id, username)
    if not j or j["status"] != "jalan":
        return False
    _tulis(f"batal:{job_id}", {"username": username})
    return True


def mulai(app, user_id: int, username: str, kerja) -> str:
    """Jalankan kerja(kemajuan, dibatalkan) di thread; kembalikan id. kerja mengembalikan dict hasil agen."""
    aktif = _baca(f"pengguna:{username}")
    if aktif and (status(aktif["id"], username) or {}).get("status") == "jalan":
        raise ValueError("Masih ada pertanyaan yang berjalan. Tunggu selesai atau batalkan dulu.")
    job_id = uuid.uuid4().hex
    _tulis(job_id, {"username": username, "status": "jalan", "peristiwa": [], "mulai": time.time()})
    _tulis(f"denyut:{job_id}", {"t": time.time()})
    _tulis(f"pengguna:{username}", {"id": job_id})
    akar = __import__("flask").request.url_root

    berhenti = threading.Event()

    def denyut():
        """Tanda hidup tiap DENYUT_DETIK selama pekerjaan berjalan (termasuk saat menunggu jawaban model yang lama)."""
        with app.app_context():
            while not berhenti.is_set():
                try:
                    _tulis(f"denyut:{job_id}", {"t": time.time()})
                except Exception:  # noqa: BLE001 - gagal menulis denyut tidak boleh menghentikan pekerjaan
                    log.warning("ALDx AI latar: denyut tidak tersimpan")
                berhenti.wait(DENYUT_DETIK)

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
                berhenti.set()
                db.session.remove()

    threading.Thread(target=denyut, name=f"ai-denyut-{job_id[:8]}", daemon=True).start()
    threading.Thread(target=jalan, name=f"ai-{job_id[:8]}", daemon=True).start()
    return job_id
