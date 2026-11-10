"""Sertifikat HTTPS gateway: dipakai sertifikat kantor bila ada, kalau tidak dibuat sendiri (self-signed).

Berkas (di komputer: server\\tls\\, di container superset: /app/server/tls/, di gateway: /etc/nginx/tls/):
    aldx.crt   sertifikat PEM
    aldx.key   kunci privat PEM

Nama yang dicakup sertifikat buatan sendiri: localhost, 127.0.0.1, NODE_NAMA (nama komputer), dan
SPS_HTTPS_NAMA (pisah koma, mis. "aldx.kantor.local,10.1.2.3").
"""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

FOLDER = Path(os.environ.get("SPS_SERVER_DIR", "/app/server")) / "tls"
SERTIFIKAT, KUNCI = FOLDER / "aldx.crt", FOLDER / "aldx.key"


def aktif() -> bool:
    return os.environ.get("SPS_HTTPS", "").strip() in ("1", "ya", "true")


def nama_dicakup() -> list[str]:
    nama = ["localhost", "127.0.0.1", os.environ.get("NODE_NAMA", "")]
    nama += [x.strip() for x in os.environ.get("SPS_HTTPS_NAMA", "").split(",")]
    return list(dict.fromkeys(n for n in nama if n))


def pastikan() -> str:
    """Pastikan sertifikat ada. Kembalikan keterangan singkat untuk ringkasan."""
    if SERTIFIKAT.exists() and KUNCI.exists():
        return f"HTTPS: memakai sertifikat {SERTIFIKAT.name}"
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    nama = nama_dicakup()
    kunci = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subjek = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, nama[2] if len(nama) > 2 else "localhost"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ALDx")])
    alt = []
    for n in nama:
        try:
            alt.append(x509.IPAddress(ipaddress.ip_address(n)))
        except ValueError:
            alt.append(x509.DNSName(n))
    sekarang = datetime.now(timezone.utc)
    sert = (x509.CertificateBuilder().subject_name(subjek).issuer_name(subjek).public_key(kunci.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(sekarang - timedelta(days=1)).not_valid_after(sekarang + timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(kunci, hashes.SHA256()))
    FOLDER.mkdir(parents=True, exist_ok=True)
    KUNCI.write_bytes(kunci.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                          serialization.NoEncryption()))
    SERTIFIKAT.write_bytes(sert.public_bytes(serialization.Encoding.PEM))
    return f"HTTPS: sertifikat dibuat sendiri untuk {', '.join(nama)} (berlaku 10 tahun)"
