"""Autentikasi ke Active Directory / LDAP memakai ldap3 (Python murni). Opsional: aktif bila LDAP_SERVERS terisi.

Cara kerjanya (sama dengan aplikasi intranet DJP "engineN", ldap_auth):
    1. Bind ke AD sebagai  DOMAIN\\username  dengan password pengguna sendiri
       (tanpa akun layanan / service account).
    2. Bila bind berhasil, cari data pegawai di LDAP_SEARCH_BASE
       untuk mengambil nama (displayName), NIP (employeeNumber), dan email.
    3. Server dicoba berurutan; server cadangan hanya dipakai bila server
       sebelumnya TIDAK BISA DIHUBUNGI. Password salah tidak dicoba ulang ke
       server lain, supaya akun AD tidak cepat terkunci.

Modul ini tidak bergantung pada Superset, sehingga bisa dites mandiri:
    python /app/pythonpath/sps_ldap.py        (lihat scripts/test-ldap.ps1)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from ldap3 import Connection, Server, SIMPLE
from ldap3.core.exceptions import LDAPException, LDAPSocketOpenError
from ldap3.utils.conv import escape_filter_chars

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 5
RECEIVE_TIMEOUT_SECONDS = 10
ATTRIBUTES = ["displayName", "employeeNumber", "mail", "sAMAccountName"]


@dataclass(frozen=True)
class LdapSettings:
    """Pengaturan LDAP; nilainya dari .env (default = nilai engineN)."""

    servers: tuple[str, ...]
    domain: str
    search_base: str

    @classmethod
    def from_env(cls) -> "LdapSettings":
        servers = os.environ.get("LDAP_SERVERS", "")             # kosong = LDAP tidak dipakai
        return cls(
            servers=tuple(s.strip() for s in servers.split(",") if s.strip()),
            domain=os.environ.get("LDAP_DOMAIN", ""),
            search_base=os.environ.get("LDAP_SEARCH_BASE", ""),
        )


def aktif() -> bool:
    """LDAP dipakai bila LDAP_SERVERS terisi. Kosong = login akun lokal saja (perusahaan tanpa AD)."""
    return bool(LdapSettings.from_env().servers)


@dataclass(frozen=True)
class LdapUser:
    """Data pegawai hasil login LDAP yang berhasil."""

    username: str
    display_name: str
    nip: str
    email: str


def authenticate(username: str, password: str, settings: LdapSettings | None = None) -> LdapUser | None:
    """Kembalikan LdapUser bila username/password benar, None bila tidak."""
    if not username or not password:
        return None  # password kosong = "anonymous bind" di AD; wajib ditolak

    settings = settings or LdapSettings.from_env()
    bind_user = f"{settings.domain}\\{username}"

    for url in settings.servers:
        server = Server(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)
        conn = Connection(
            server,
            user=bind_user,
            password=password,
            authentication=SIMPLE,
            receive_timeout=RECEIVE_TIMEOUT_SECONDS,
            read_only=True,
        )
        try:
            if not conn.bind():
                log.info("LDAP: login ditolak untuk %s di %s", username, url)
                return None  # password salah: jangan coba server lain
            return _read_user(conn, username, settings.search_base)
        except LDAPSocketOpenError:
            log.warning("LDAP: server %s tidak bisa dihubungi, coba server berikutnya", url)
        except LDAPException:
            log.exception("LDAP: kesalahan saat login %s di %s", username, url)
            return None
        finally:
            conn.unbind()

    log.error("LDAP: semua server tidak bisa dihubungi: %s", ", ".join(settings.servers))
    return None


def _read_user(conn: Connection, username: str, search_base: str) -> LdapUser | None:
    """Cari data pegawai; wajib tepat satu hasil (sama seperti engineN)."""
    name = escape_filter_chars(username)
    search_filter = (
        "(&(objectCategory=person)(objectClass=user)"
        f"(|(sAMAccountName={name})(cn={name}*)))"
    )
    conn.search(search_base, search_filter, attributes=ATTRIBUTES, size_limit=2)

    if len(conn.entries) != 1:
        log.info("LDAP: %s ditemukan %d data di %s (harus 1)", username, len(conn.entries), search_base)
        return None

    entry = conn.entries[0]
    return LdapUser(
        username=username,
        display_name=_value(entry, "displayName") or username,
        nip=_value(entry, "employeeNumber"),
        email=_value(entry, "mail"),
    )


def _value(entry, attribute: str) -> str:
    """Ambil nilai atribut sebagai teks; kosong bila tidak ada."""
    return str(entry[attribute].value or "") if attribute in entry else ""


if __name__ == "__main__":
    # Tes mandiri: tanya username & password, tampilkan hasilnya.
    import getpass

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = authenticate(input("Username: ").strip(), getpass.getpass("Password: "))
    print(f"\nBERHASIL: {result}" if result else "\nGAGAL: lihat pesan di atas")
