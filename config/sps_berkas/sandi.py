"""Enkripsi & tanda tangan berkas .ald / .aldx.

Susunan berkas (biner):

    "ALDX" 0x01 | panjang kepala (4 byte, big-endian) | kepala JSON | isi terenkripsi | tanda (32 byte)

    kepala      JSON terbuka, TANPA isi rahasia: format, versi, enkripsi, kdf, nonce, waktu dibuat.
                Ikut diautentikasi (AAD), jadi kepala yang diubah membuat berkas ditolak.
    isi         ZIP (manifest + definisi Superset + data) dienkripsi AES-256-GCM.
    tanda       HMAC-SHA256 seluruh bagian sebelumnya dengan KUNCI SERVER. Menunjukkan berkas dibuat
                server ini / organisasi yang memakai kunci yang sama ("terverifikasi").

Dua cara mengunci:
    "server"  kunci dari SPS_KUNCI_BERKAS (atau SUPERSET_SECRET_KEY bila kosong). Berkas hanya bisa
              dibuka di server dengan kunci yang sama. Untuk berbagi antar-server, samakan SPS_KUNCI_BERKAS.
    "sandi"   kunci dari kata sandi pembuat (scrypt). Bisa dibuka di server ALDx mana pun dengan sandi itu.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes

AWALAN = b"ALDX\x01"
PANJANG_TANDA = 32
SANDI_MIN = 8
SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1}


class GalatBerkas(ValueError):
    """Berkas rusak, bukan berkas ALDx, atau sandi/kunci salah. Pesannya aman ditampilkan."""


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _rahasia_server() -> bytes:
    from flask import current_app
    rahasia = os.environ.get("SPS_KUNCI_BERKAS") or current_app.config["SECRET_KEY"]
    return rahasia.encode()


def _turunan(tujuan: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"aldx-berkas", info=tujuan).derive(_rahasia_server())


def _kunci(kepala: dict, sandi: str | None) -> bytes:
    if kepala["enkripsi"] == "server":
        return _turunan(b"enkripsi")
    if not sandi:
        raise GalatBerkas("Berkas ini dikunci kata sandi. Isi kata sandinya.")
    k = kepala["kdf"]
    return Scrypt(salt=base64.b64decode(k["garam"]), length=32, n=k["n"], r=k["r"], p=k["p"]).derive(sandi.encode())


def bungkus(isi: bytes, format_: str, sandi: str | None = None) -> bytes:
    """Kunci `isi` (ZIP) menjadi berkas .ald/.aldx. Tanpa sandi = kunci server."""
    if sandi is not None and len(sandi) < SANDI_MIN:
        raise GalatBerkas(f"Kata sandi minimal {SANDI_MIN} karakter.")
    kepala = {"format": format_, "versi": 1, "aplikasi": "ALDx",
              "dibuat": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "enkripsi": "sandi" if sandi else "server", "nonce": _b64(os.urandom(12))}
    if sandi:
        kepala["kdf"] = {"nama": "scrypt", "garam": _b64(os.urandom(16)), **SCRYPT}
    teks = json.dumps(kepala, separators=(",", ":")).encode()
    tubuh = AWALAN + struct.pack(">I", len(teks)) + teks
    rahasia = AESGCM(_kunci(kepala, sandi)).encrypt(base64.b64decode(kepala["nonce"]), isi, tubuh)
    tubuh += rahasia
    return tubuh + hmac.new(_turunan(b"tanda"), tubuh, hashlib.sha256).digest()


def kepala(data: bytes) -> dict:
    """Baca kepala tanpa membuka isi (untuk tahu perlu sandi atau tidak)."""
    if not data.startswith(AWALAN) or len(data) < len(AWALAN) + 4 + PANJANG_TANDA:
        raise GalatBerkas("Bukan berkas .ald / .aldx, atau berkas rusak.")
    (n,) = struct.unpack(">I", data[len(AWALAN):len(AWALAN) + 4])
    try:
        return json.loads(data[len(AWALAN) + 4:len(AWALAN) + 4 + n])
    except ValueError as exc:
        raise GalatBerkas("Kepala berkas rusak.") from exc


def buka(data: bytes, sandi: str | None = None) -> tuple[dict, bytes, bool]:
    """Kembalikan (kepala, isi ZIP, terverifikasi). Gagal bila berkas diubah atau sandi/kunci salah."""
    kp = kepala(data)
    (panjang,) = struct.unpack(">I", data[len(AWALAN):len(AWALAN) + 4])
    n = len(AWALAN) + 4 + panjang
    tubuh, tanda = data[:-PANJANG_TANDA], data[-PANJANG_TANDA:]
    terverifikasi = hmac.compare_digest(hmac.new(_turunan(b"tanda"), tubuh, hashlib.sha256).digest(), tanda)
    if kp.get("enkripsi") == "server" and not terverifikasi:
        raise GalatBerkas("Berkas dikunci kunci server lain (atau diubah). Minta pembuat mengunci dengan kata sandi, "
                          "atau samakan SPS_KUNCI_BERKAS kedua server.")
    try:
        isi = AESGCM(_kunci(kp, sandi)).decrypt(base64.b64decode(kp["nonce"]), tubuh[n:], tubuh[:n])
    except GalatBerkas:
        raise
    except Exception as exc:  # noqa: BLE001 - InvalidTag dll.: jangan bocorkan rincian kriptografi
        raise GalatBerkas("Kata sandi salah, atau berkas telah diubah.") from exc
    return kp, isi, terverifikasi
