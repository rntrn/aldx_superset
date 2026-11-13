"""Masuk dengan SSO (OpenID Connect): Microsoft Entra ID / Azure AD, Google Workspace, Okta, Keycloak, dll.

SSO adalah jalan masuk TAMBAHAN, bukan pengganti: halaman login tetap punya formulir password (akun lokal & LDAP),
sehingga Superadmin tetap bisa masuk bila penyedia SSO atau internet bermasalah.

Alur (authorization code + PKCE, standar OIDC):
    1. GET /sso/masuk     simpan state, nonce, code_verifier di sesi -> alihkan ke penyedia
    2. pengguna login di penyedia (MFA, kebijakan perusahaan berlaku di sana)
    3. GET /sso/kembali   tukar code -> token (server ke server), periksa id_token: tanda tangan (JWKS), penerbit,
                          audiens, nonce, kedaluwarsa; email harus di domain yang diizinkan
    4. akun dicari menurut email (atau dibuat dengan role bawaan bila SSO_BUAT_AKUN=1) -> masuk

Pengaturan (.env, lihat .env.example; kosong = SSO mati, tombol tidak tampil):
    SSO_DISCOVERY_URL   alamat .well-known/openid-configuration penyedia
    SSO_CLIENT_ID / SSO_CLIENT_SECRET   dari pendaftaran aplikasi di penyedia (rahasia: hanya di .env)
    SSO_NAMA            label tombol, mis. "Microsoft"            SSO_DOMAIN   domain email yang boleh, mis. kantor.co.id
    SSO_BUAT_AKUN       1 = akun dibuat otomatis saat pertama masuk (role SSO_ROLE_BAWAAN, bawaan Gamma)
    SSO_ALAMAT_KEMBALI  (opsional) alamat lengkap /sso/kembali bila ALDx di balik proxy dengan nama lain
Alamat kembali yang didaftarkan di penyedia: https://<alamat-aldx>/sso/kembali
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from flask import Blueprint, flash, redirect, request, session

log = logging.getLogger(__name__)
bp = Blueprint("sps_sso", __name__, url_prefix="/sso")
BATAS_WAKTU = 10                  # detik, permintaan ke penyedia
SIMPAN_DISCOVERY = 3600           # detik
_tembolok: dict = {}


class SsoGagal(Exception):
    """Pesan aman untuk ditampilkan di halaman login."""


@dataclass(frozen=True)
class Setelan:
    discovery: str
    client_id: str
    client_secret: str
    nama: str = "SSO"
    domain: tuple[str, ...] = ()
    buat_akun: bool = False
    role_bawaan: str = "Gamma"
    alamat_kembali: str = ""
    izinkan_http: bool = False       # HANYA untuk uji lokal; produksi wajib https
    tambahan: dict = field(default_factory=dict)

    @classmethod
    def dari_env(cls) -> "Setelan | None":
        e = os.environ.get
        if not (e("SSO_DISCOVERY_URL") and e("SSO_CLIENT_ID")):
            return None
        return cls(discovery=e("SSO_DISCOVERY_URL", "").strip(), client_id=e("SSO_CLIENT_ID", "").strip(),
                   client_secret=e("SSO_CLIENT_SECRET", "").strip(), nama=(e("SSO_NAMA") or "SSO").strip()[:40],
                   domain=tuple(d.strip().lower().lstrip("@") for d in e("SSO_DOMAIN", "").split(",") if d.strip()),
                   buat_akun=e("SSO_BUAT_AKUN", "0").strip() == "1", role_bawaan=(e("SSO_ROLE_BAWAAN") or "Gamma").strip(),
                   alamat_kembali=e("SSO_ALAMAT_KEMBALI", "").strip(), izinkan_http=e("SSO_UJI_HTTP", "0") == "1")


def aktif() -> Setelan | None:
    return Setelan.dari_env()


def _ambil_json(url: str, s: Setelan, data: dict | None = None) -> dict:
    if not (url.startswith("https://") or (s.izinkan_http and url.startswith("http://"))):
        raise SsoGagal("Alamat penyedia SSO harus https.")
    badan = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=badan, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=BATAS_WAKTU) as r:            # proxy kantor dari HTTPS_PROXY
            return json.loads(r.read(2_000_000))
    except urllib.error.HTTPError as e:
        log.warning("ALDx SSO: %s menjawab %s %s", url.split("?")[0], e.code, e.read(500))
        raise SsoGagal("Penyedia SSO menolak permintaan. Periksa pengaturan SSO (client ID/secret, alamat kembali).") from None
    except (OSError, ValueError) as e:
        log.warning("ALDx SSO: gagal menghubungi %s (%s)", url.split("?")[0], e)
        raise SsoGagal("Penyedia SSO tidak bisa dihubungi. Coba lagi, atau masuk dengan password.") from None


def discovery(s: Setelan) -> dict:
    t = _tembolok.get(s.discovery)
    if t and time.monotonic() - t[0] < SIMPAN_DISCOVERY:
        return t[1]
    d = _ambil_json(s.discovery, s)
    for k in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not d.get(k):
            raise SsoGagal("Alamat discovery SSO tidak lengkap.")
    _tembolok[s.discovery] = (time.monotonic(), d)
    return d


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _alamat_kembali(s: Setelan) -> str:
    return s.alamat_kembali or request.url_root.rstrip("/") + "/sso/kembali"


def email_dari_klaim(k: dict) -> str:
    """Email dari id_token: email (Google/Okta/Keycloak), preferred_username / upn (Microsoft)."""
    if k.get("email_verified") is False:
        raise SsoGagal("Email akun SSO belum terverifikasi di penyedia.")
    for kunci in ("email", "preferred_username", "upn"):
        v = str(k.get(kunci) or "").strip().lower()
        if "@" in v:
            return v
    raise SsoGagal("Penyedia SSO tidak mengirim email. Tambahkan scope/klaim email di pendaftaran aplikasi.")


def domain_boleh(email: str, s: Setelan) -> bool:
    return not s.domain or email.rsplit("@", 1)[-1] in s.domain


def periksa_id_token(id_token: str, s: Setelan, d: dict, nonce: str) -> dict:
    import jwt
    try:
        kunci = jwt.PyJWKClient(d["jwks_uri"], timeout=BATAS_WAKTU).get_signing_key_from_jwt(id_token)
        klaim = jwt.decode(id_token, kunci.key, algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"],
                           audience=s.client_id, issuer=d["issuer"], leeway=60,
                           options={"require": ["exp", "iat", "iss", "aud"]})
    except jwt.PyJWTError as e:
        log.warning("ALDx SSO: id_token ditolak (%s)", e)
        raise SsoGagal("Tanda masuk dari penyedia SSO tidak sah.") from None
    if not secrets.compare_digest(str(klaim.get("nonce") or ""), nonce):
        raise SsoGagal("Sesi SSO tidak cocok. Ulangi masuk.")
    return klaim


def cari_atau_buat(email: str, klaim: dict, s: Setelan):
    from superset import security_manager as sm
    user = sm.find_user(email=email) or sm.find_user(username=email)
    if user is None:
        if not s.buat_akun:
            raise SsoGagal("Akun Anda belum terdaftar di ALDx. Minta Admin menambahkan email Anda (Kelola › Pengguna).")
        role = sm.find_role(s.role_bawaan)
        if role is None:
            log.error("ALDx SSO: role '%s' (SSO_ROLE_BAWAAN) tidak ada", s.role_bawaan)
            raise SsoGagal("Pengaturan role SSO salah. Hubungi Admin.")
        nama = str(klaim.get("name") or email.split("@")[0]).strip()
        depan, _, belakang = nama.partition(" ")
        user = sm.add_user(username=email, first_name=(klaim.get("given_name") or depan or email)[:64],
                           last_name=(klaim.get("family_name") or belakang or "-")[:64], email=email, role=role)
        if not user:
            raise SsoGagal("Akun tidak bisa dibuat. Hubungi Admin.")
        log.info("ALDx SSO: akun baru %s (role %s)", email, s.role_bawaan)
    if not user.is_active:
        raise SsoGagal("Akun Anda dinonaktifkan. Hubungi Admin.")
    return user


@bp.route("/masuk")
def masuk():
    s = aktif()
    if s is None:
        return redirect("/login/")
    try:
        d = discovery(s)
    except SsoGagal as e:
        flash(str(e), "warning")
        return redirect("/login/")
    verifier = _b64(secrets.token_bytes(48))
    session["sps_sso"] = {"state": secrets.token_urlsafe(24), "nonce": secrets.token_urlsafe(24), "verifier": verifier,
                          "lanjut": _lanjut(request.args.get("next", "")), "waktu": int(time.time())}
    q = {"response_type": "code", "client_id": s.client_id, "redirect_uri": _alamat_kembali(s),
         "scope": "openid email profile", "state": session["sps_sso"]["state"], "nonce": session["sps_sso"]["nonce"],
         "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256"}
    return redirect(d["authorization_endpoint"] + ("&" if "?" in d["authorization_endpoint"] else "?") + urllib.parse.urlencode(q))


def _lanjut(url: str) -> str:
    return url if url.startswith("/") and not url.startswith("//") else ""


@bp.route("/kembali")
def kembali():
    from flask_login import login_user
    from superset import security_manager as sm

    import sps_audit
    s, simpan = aktif(), session.pop("sps_sso", None)
    try:
        if s is None:
            raise SsoGagal("SSO tidak aktif.")
        if request.args.get("error"):
            raise SsoGagal(f"Penyedia SSO: {request.args.get('error_description') or request.args['error']}"[:200])
        if not simpan or not secrets.compare_digest(request.args.get("state", ""), simpan["state"]) \
                or time.time() - simpan["waktu"] > 600:
            raise SsoGagal("Sesi SSO kedaluwarsa atau tidak cocok. Ulangi masuk.")
        d = discovery(s)
        token = _ambil_json(d["token_endpoint"], s, {
            "grant_type": "authorization_code", "code": request.args.get("code", ""), "redirect_uri": _alamat_kembali(s),
            "client_id": s.client_id, "client_secret": s.client_secret, "code_verifier": simpan["verifier"]})
        if not token.get("id_token"):
            raise SsoGagal("Penyedia SSO tidak mengirim id_token (scope openid).")
        klaim = periksa_id_token(token["id_token"], s, d, simpan["nonce"])
        email = email_dari_klaim(klaim)
        if not domain_boleh(email, s):
            sps_audit.catat("login", "SSO ditolak (domain)", email, oleh=email)
            raise SsoGagal("Email ini tidak termasuk domain yang diizinkan.")
        user = cari_atau_buat(email, klaim, s)
    except SsoGagal as e:
        log.info("ALDx login SSO: GAGAL (%s)", e)
        flash(str(e), "warning")
        return redirect("/login/")
    sm._ensure_admin_role(user)
    sm.lengkapi_role(user)
    sm.update_user_auth_stat(user, success=True)
    login_user(user, remember=False)
    sps_audit.catat("login", f"Masuk SSO ({s.nama})", user.username, oleh=user.username)
    log.info("ALDx login SSO %s: BERHASIL", user.username)
    from flask import current_app
    return redirect(simpan.get("lanjut") or current_app.config["SPS_IDENTITAS"]["halaman_depan"])


def daftarkan(app) -> None:
    app.register_blueprint(bp)
