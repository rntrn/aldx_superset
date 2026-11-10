"""Status model AI: hanya model yang benar-benar AKTIF yang ditampilkan.

Model dianggap aktif bila servernya menjawab GET {base_url}/models dalam 2 detik:
    - tidak terjangkau / timeout / SSL ditolak  -> tidak aktif (mis. LM Studio belum dinyalakan)
    - model LOKAL (tanpa key) yang menjawab daftar model tetapi model di ai.yaml
      tidak ada di daftar itu                    -> tidak aktif (model belum diunduh)
    - jawaban HTTP lainnya                       -> aktif (server ada; galat key tampil saat dipakai)
Hasil disimpan 60 detik per proses agar halaman tidak melambat.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

log = logging.getLogger(__name__)
UMUR_DETIK = 60
BATAS_DETIK = 2
_tembolok: dict[tuple[str, str, str], tuple[float, bool]] = {}
_kunci = threading.Lock()


def _periksa(m) -> bool:
    headers = {"Authorization": f"Bearer {m.api_key}"} if m.api_key else {}
    verify = os.environ.get("AI_CA_BUNDLE") or True
    try:
        r = requests.get(f"{m.base_url}/models", headers=headers, timeout=BATAS_DETIK, verify=verify)
    except requests.RequestException:
        return False
    if m.api_key or r.status_code != 200:
        return True
    try:
        nama = [str(x.get("id") or x.get("name") or "").lower() for x in (r.json().get("data") or [])]
    except ValueError:
        return True
    dicari = m.model.lower()
    return not nama or any(n == dicari or n.startswith(dicari + ":") or n.split("/")[-1] == dicari for n in nama)


def aktif(daftar: list) -> list:
    """Saring daftar ModelAI menjadi yang aktif saja (urutan dipertahankan)."""
    sekarang, perlu = time.monotonic(), []
    with _kunci:
        for m in daftar:
            k = (m.id, m.base_url, m.model)
            if k not in _tembolok or sekarang - _tembolok[k][0] > UMUR_DETIK:
                perlu.append(m)
    if perlu:
        with ThreadPoolExecutor(max_workers=min(8, len(perlu))) as kolam:
            hasil = list(kolam.map(_periksa, perlu))
        with _kunci:
            for m, ok in zip(perlu, hasil):
                _tembolok[(m.id, m.base_url, m.model)] = (sekarang, ok)
                log.info("ALDx AI: model %s %s", m.id, "aktif" if ok else "TIDAK aktif")
    return [m for m in daftar if _tembolok[(m.id, m.base_url, m.model)][1]]


# --- Model lokal ditemukan otomatis -------------------------------------------------------
# Model selain chat (embedding, reranker, suara, gambar) tidak bisa menjawab pertanyaan.
_BUKAN_CHAT = re.compile(r"embed|bge|nomic|e5-|minilm|rerank|whisper|clip|tts|vision-encoder|stable-diffusion|flux", re.I)
_temuan: dict[str, tuple[float, list[str], bool]] = {}


def _daftar_model(base_url: str) -> tuple[bool, list[str]]:
    try:
        r = requests.get(f"{base_url}/models", timeout=BATAS_DETIK)
        if r.status_code != 200:
            return False, []
        data = r.json().get("data") or []
    except (requests.RequestException, ValueError, AttributeError):
        return False, []
    nama = [str(x.get("id") or x.get("name") or "") for x in data if isinstance(x, dict)]
    return True, [n for n in nama if n and not _BUKAN_CHAT.search(n)]


def temukan(sumber: list[dict]) -> list[dict]:
    """Tanya setiap server lokal (Ollama, LM Studio, ...) model apa saja yang sudah diunduh.

    Kembali: [{nama, base_url, aktif, model: [..]}], disimpan 60 detik.
    """
    sekarang = time.monotonic()
    perlu = [s for s in sumber if s["base_url"] not in _temuan or sekarang - _temuan[s["base_url"]][0] > UMUR_DETIK]
    if perlu:
        with ThreadPoolExecutor(max_workers=min(8, len(perlu))) as kolam:
            hasil = list(kolam.map(lambda s: _daftar_model(s["base_url"]), perlu))
        with _kunci:
            for s, (hidup, model) in zip(perlu, hasil):
                lama = _temuan.get(s["base_url"])
                _temuan[s["base_url"]] = (sekarang, model, hidup)
                if not lama or lama[1:] != (model, hidup):
                    log.info("ALDx AI: %s %s, model: %s", s["nama"], "menyala" if hidup else "tidak menyala",
                             ", ".join(model) or "-")
    return [{"nama": s["nama"], "base_url": s["base_url"], "aktif": _temuan[s["base_url"]][2],
             "model": _temuan[s["base_url"]][1]} for s in sumber]


def lupakan() -> None:
    """Kosongkan tembolok (setelah key diubah atau tombol Periksa lagi)."""
    with _kunci:
        _tembolok.clear()
        _temuan.clear()


def ada_yang_aktif() -> bool:
    """Apakah ada model AI yang siap dipakai. Tidak pernah melempar galat."""
    try:
        from sps_ai import pengaturan
        return bool(pengaturan.muat().model)
    except Exception:  # noqa: BLE001
        log.debug("ALDx AI: status model tidak terbaca", exc_info=True)
        return False
