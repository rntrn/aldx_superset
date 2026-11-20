"""Status model AI: hanya model yang benar-benar AKTIF yang ditampilkan.

Model dianggap aktif bila servernya menjawab GET {base_url}/models dalam 2 detik:
    - tidak terjangkau / timeout / SSL ditolak  -> tidak aktif (mis. LM Studio belum dinyalakan)
    - model LOKAL (tanpa key) yang menjawab daftar model tetapi model di ai.yaml
      tidak ada di daftar itu                    -> tidak aktif (model belum diunduh)
    - model LOKAL dijawab 401/403                -> tidak aktif: server minta token (LM Studio "Require
                                                    Authentication"); isi token di Sambungkan AI
    - jawaban HTTP lainnya                       -> aktif (server ada; galat key tampil saat dipakai)
LM Studio juga ditanya /api/v0/models: model yang sedang DIMUAT diutamakan (tidak memaksa server ganti model).
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
    headers = {"Authorization": f"Bearer {m.kunci}"} if m.kunci else {}
    verify = os.environ.get("AI_CA_BUNDLE") or True
    try:
        r = requests.get(f"{m.base_url}/models", headers=headers, timeout=BATAS_DETIK, verify=verify)
    except requests.RequestException:
        return False
    if not m.api_key and r.status_code in (401, 403):
        return False                     # server lokal minta token yang belum diisi / salah
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
_temuan: dict[str, tuple[float, dict]] = {}


def _dimuat(base_url: str, headers: dict) -> list[str]:
    """LM Studio: model yang sedang dimuat (GET /api/v0/models, state=loaded). Server lain: []."""
    try:
        r = requests.get(base_url.rsplit("/v1", 1)[0] + "/api/v0/models", headers=headers, timeout=BATAS_DETIK)
        if r.status_code == 200:
            return [str(x.get("id")) for x in r.json().get("data") or [] if x.get("state") == "loaded"]
    except (requests.RequestException, ValueError, AttributeError):
        pass
    return []


def _daftar_model(base_url: str, token: str = "") -> dict:
    """{hidup, model, butuh_token, dimuat}"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    kosong = {"hidup": False, "model": [], "butuh_token": False, "dimuat": []}
    try:
        r = requests.get(f"{base_url}/models", headers=headers, timeout=BATAS_DETIK)
        if r.status_code in (401, 403):
            return {**kosong, "hidup": True, "butuh_token": True}
        if r.status_code != 200:
            return kosong
        data = r.json().get("data") or []
    except (requests.RequestException, ValueError, AttributeError):
        return kosong
    nama = [str(x.get("id") or x.get("name") or "") for x in data if isinstance(x, dict)]
    return {"hidup": True, "model": [n for n in nama if n and not _BUKAN_CHAT.search(n)], "butuh_token": False,
            "dimuat": _dimuat(base_url, headers)}


def temukan(sumber: list[dict]) -> list[dict]:
    """Tanya setiap server lokal (Ollama, LM Studio, ...) model apa saja yang sudah diunduh.

    Kembali: [{nama, base_url, aktif, model: [..], dimuat: [..], butuh_token, env, token}], disimpan 60 detik.
    aktif = server menjawab DAN tidak menunggu token.
    """
    sekarang = time.monotonic()
    kunci_ = lambda s: (s["base_url"], s.get("token", ""))  # noqa: E731 - token berubah = periksa ulang
    perlu = [s for s in sumber if kunci_(s) not in _temuan or sekarang - _temuan[kunci_(s)][0] > UMUR_DETIK]
    if perlu:
        with ThreadPoolExecutor(max_workers=min(8, len(perlu))) as kolam:
            hasil = list(kolam.map(lambda s: _daftar_model(s["base_url"], s.get("token", "")), perlu))
        with _kunci:
            for s, h in zip(perlu, hasil):
                lama = _temuan.get(kunci_(s))
                _temuan[kunci_(s)] = (sekarang, h)
                if not lama or lama[1] != h:
                    log.info("ALDx AI: %s %s, model: %s%s", s["nama"], "menyala" if h["hidup"] else "tidak menyala",
                             ", ".join(h["model"]) or "-", " (BUTUH TOKEN)" if h["butuh_token"] else "")
    hasil = []
    for s in sumber:
        h = _temuan[kunci_(s)][1]
        hasil.append({"nama": s["nama"], "base_url": s["base_url"], "aktif": h["hidup"] and not h["butuh_token"],
                      "model": h["model"], "dimuat": h["dimuat"], "butuh_token": h["butuh_token"],
                      "env": s.get("env", ""), "token": s.get("token", "")})
    return hasil


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
