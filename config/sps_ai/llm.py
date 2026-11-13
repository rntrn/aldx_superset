"""Klien model AI berformat OpenAI-compatible (POST {base_url}/chat/completions).

Satu klien untuk semua penyedia: Ollama, LM Studio, vLLM, OpenAI, Azure,
Gemini, Anthropic, DeepSeek, dll. Jaringan kantor:
    AI_CA_BUNDLE  path sertifikat root kantor (SSL inspection), mis. /app/certs/kantor.pem
    HTTPS_PROXY   bila internet kantor lewat proxy
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import requests

from sps_ai.pengaturan import ModelAI

log = logging.getLogger(__name__)


class GagalModel(RuntimeError):
    """Model tidak bisa dihubungi atau menjawab error.

    sementara=True: sibuk / kuota / jaringan / waktu habis -> layak dicoba ulang atau dialihkan ke model cadangan.
    """
    def __init__(self, pesan: str, sementara: bool = False):
        super().__init__(pesan)
        self.sementara = sementara


COBA_ULANG = (2, 6)                      # detik jeda sebelum percobaan ke-2 dan ke-3 (galat sementara)
STATUS_SEMENTARA = {408, 425, 429, 500, 502, 503, 504, 529}
# Model lokal kecil sering menulis pemanggilan alat sebagai TEKS, bukan field tool_calls resmi.
POLA_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
POLA_BLOK = re.compile(r"```(?:json|tool_call)?\s*(\{.*?\})\s*```", re.S)


def alat_dari_teks(isi: str, nama_alat: set[str]) -> list[dict]:
    """Pemanggilan alat yang ditulis di teks: <tool_call>{"name":..,"arguments":..}</tool_call>, blok ```json```,
    atau seluruh jawaban berupa JSON itu. Hanya nama alat yang memang ditawarkan yang diterima."""
    calon = POLA_TAG.findall(isi or "") or POLA_BLOK.findall(isi or "")
    if not calon and (isi or "").strip().startswith("{"):
        calon = [isi.strip()]
    hasil = []
    for i, teks in enumerate(calon):
        try:
            d = json.loads(teks)
        except ValueError:
            continue
        nama = d.get("name") or (d.get("function") or {}).get("name")
        arg = d.get("arguments", d.get("parameters", (d.get("function") or {}).get("arguments", {})))
        if nama in nama_alat:
            hasil.append({"id": f"teks{i}", "type": "function",
                          "function": {"name": nama, "arguments": arg if isinstance(arg, str) else json.dumps(arg)}})
    return hasil


def _pesan_status(model: ModelAI, kode: int, teks: str) -> str:
    """Penjelasan galat penyedia yang bisa ditindaklanjuti pengguna (detail teknis tetap di log)."""
    if kode in (401, 403):
        return f"Model '{model.nama}' menolak akses: API key salah, kedaluwarsa, atau belum diaktifkan."
    if kode == 429:
        return (f"Kuota/batas permintaan '{model.nama}' habis untuk saat ini (umum pada paket gratis). "
                "Coba lagi beberapa menit lagi, atau pilih model lain.")
    if kode == 404:
        return (f"Nama model '{model.model}' tidak dikenali penyedia '{model.nama}' (nama model sering berganti). "
                "Admin: perbarui 'model:' di config/ai.yaml.")
    if kode in STATUS_SEMENTARA:
        return f"Server '{model.nama}' sedang sibuk atau bermasalah (HTTP {kode}, dari penyedia, bukan ALDx). Coba lagi sebentar lagi."
    pesan = ""
    try:
        pesan = str((json.loads(teks).get("error") or {}).get("message") or "")[:200]
    except (ValueError, AttributeError):
        pass
    return f"Model '{model.nama}' mengembalikan error ({kode}){': ' + pesan if pesan else ''}. Detail ada di log."


def chat(model: ModelAI, pesan: list[dict], alat: list[dict], batas_detik: int) -> dict[str, Any]:
    """Kirim percakapan + daftar alat, kembalikan `message` dari model.

    Galat sementara (sibuk, kuota, jaringan) dicoba ulang hingga 2 kali dengan jeda, selama masih dalam batas_detik.
    Pemanggilan alat yang ditulis sebagai teks (model lokal) diubah menjadi tool_calls resmi."""
    tenggat = time.monotonic() + batas_detik
    for percobaan, jeda in enumerate((*COBA_ULANG, None)):
        try:
            return _chat_sekali(model, pesan, alat, max(5, int(tenggat - time.monotonic())))
        except GagalModel as exc:
            if not exc.sementara or jeda is None or time.monotonic() + jeda + 10 > tenggat:
                raise
            log.info("ALDx AI: %s galat sementara (%s), coba lagi dalam %s dtk", model.id, exc, jeda)
            time.sleep(jeda)
    raise GagalModel("tidak terjangkau")      # tidak pernah sampai sini


def _chat_sekali(model: ModelAI, pesan: list[dict], alat: list[dict], batas_detik: int) -> dict[str, Any]:
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
                         "atau pilih model lain.", sementara=True) from exc
    except requests.RequestException as exc:
        log.warning("ALDx AI: model %s tidak terhubung: %s", model.base_url, exc)  # detail teknis ke log
        raise GagalModel(f"Model '{model.nama}' sedang tidak aktif atau tidak bisa dihubungi. "
                         "Pilih model lain, atau minta admin menyalakannya (mis. Ollama).", sementara=True) from exc
    if r.status_code >= 400:
        log.warning("ALDx AI: model %s error %s: %s", model.base_url, r.status_code, r.text[:500])
        raise GagalModel(_pesan_status(model, r.status_code, r.text), sementara=r.status_code in STATUS_SEMENTARA)
    try:
        msg = r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise GagalModel(f"Jawaban model tidak dikenali: {r.text[:300]}") from exc
    if alat and not msg.get("tool_calls"):
        teks = alat_dari_teks(msg.get("content") or "", {a["function"]["name"] for a in alat})
        if teks:
            msg = {**msg, "content": "", "tool_calls": teks}
    return msg
