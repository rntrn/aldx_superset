"""Klien model AI berformat OpenAI-compatible (POST {base_url}/chat/completions).

Satu klien untuk semua penyedia: Ollama, LM Studio, vLLM, OpenAI, Azure,
Gemini, Anthropic, DeepSeek, dll. Jaringan kantor:
    AI_CA_BUNDLE  path sertifikat root kantor (SSL inspection), mis. /app/certs/kantor.pem
    HTTPS_PROXY   bila internet kantor lewat proxy
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from sps_ai.pengaturan import ModelAI

log = logging.getLogger(__name__)


class GagalModel(RuntimeError):
    """Model tidak bisa dihubungi atau menjawab error."""


def chat(model: ModelAI, pesan: list[dict], alat: list[dict], batas_detik: int) -> dict[str, Any]:
    """Kirim percakapan + daftar alat, kembalikan `message` dari model."""
    headers = {"Content-Type": "application/json"}
    if model.api_key:
        headers["Authorization"] = f"Bearer {model.api_key}"
    body: dict[str, Any] = {"model": model.model, "messages": pesan, "temperature": 0.1}
    if alat:                                   # sebagian penyedia menolak daftar alat kosong
        body.update(tools=alat, tool_choice="auto")
    verify: Any = os.environ.get("AI_CA_BUNDLE") or True
    try:
        r = requests.post(f"{model.base_url}/chat/completions", json=body, headers=headers,
                          timeout=batas_detik, verify=verify)
    except requests.exceptions.SSLError as exc:
        log.warning("ALDx AI: SSL ke %s gagal: %s", model.base_url, exc)
        raise GagalModel(f"Sertifikat SSL ke model '{model.nama}' ditolak. "
                         "Admin: isi AI_CA_BUNDLE (lihat certs/README.md).") from exc
    except requests.Timeout as exc:
        raise GagalModel(f"Model '{model.nama}' terlalu lama menjawab. Coba pertanyaan lebih singkat "
                         "atau pilih model lain.") from exc
    except requests.RequestException as exc:
        log.warning("ALDx AI: model %s tidak terhubung: %s", model.base_url, exc)  # detail teknis ke log
        raise GagalModel(f"Model '{model.nama}' sedang tidak aktif atau tidak bisa dihubungi. "
                         "Pilih model lain, atau minta admin menyalakannya (mis. Ollama).") from exc
    if r.status_code in (401, 403):
        raise GagalModel(f"Model '{model.nama}' menolak akses: API key salah atau kedaluwarsa.")
    if r.status_code >= 400:
        log.warning("ALDx AI: model %s error %s: %s", model.base_url, r.status_code, r.text[:500])
        raise GagalModel(f"Model '{model.nama}' mengembalikan error ({r.status_code}). Detail ada di log.")
    try:
        return r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as exc:
        raise GagalModel(f"Jawaban model tidak dikenali: {r.text[:300]}") from exc
