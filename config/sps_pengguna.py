"""Membuat / memperbarui akun lokal dari installer (mode login "Akun lokal").

Dipanggil installer\\pasang.ps1 setelah Superset menyala; daftar akun dikirim lewat stdin
(tidak pernah ditulis ke berkas, jadi password tidak tertinggal di disk):

    echo '[{"username":"budi","nama":"Budi Santoso","email":"budi@contoh.co.id",
            "password":"...","peran":"Analis"}]' |
        docker compose exec -T superset python /app/pythonpath/sps_pengguna.py

Peran:
    Pengguna  melihat dashboard, Studio Visual, Asisten AI       -> Gamma + SPS_ROLE_PENGGUNA
    Analis    Pengguna + SQL Lab & Kueri Visual                   -> Gamma + SPS_ROLE_PENGGUNA + sql_lab
    Admin     semua menu, Pusat Kendali (tanpa pengaturan vital)  -> Admin
    Superadmin  Admin + pengaturan vital server, batas data, hak akses -> Admin + Superadmin
Akun yang sudah ada: nama, email, password & peran diperbarui; "nama" / "peran" kosong = tidak diubah
(dipakai scripts\\atur-password.ps1). Password tidak pernah dicetak.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROLE_PENGGUNA = os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna"
PERAN = {
    "Pengguna": ["Gamma", ROLE_PENGGUNA],
    "Analis": ["Gamma", ROLE_PENGGUNA, "sql_lab"],
    "Admin": ["Admin"],
    "Superadmin": ["Admin", "Superadmin"],
}
POLA_USERNAME = re.compile(r"^[A-Za-z0-9._@+-]{2,128}$")      # boleh email (mode akun lokal: login = email)


def periksa(a: dict) -> str | None:
    """Kembalikan pesan galat bila isian akun tidak sah."""
    if not a.get("email") and "@" in a.get("username", ""):
        a["email"] = a["username"]                                 # login dengan email
    if not POLA_USERNAME.match(a.get("username", "")):
        return "username/email hanya huruf, angka, titik, @, garis bawah/strip (2-128 karakter)"
    if len(a.get("password", "")) < 8:
        return "password minimal 8 karakter"
    if a.get("peran") not in PERAN and not (a.get("peran") == "" and a.get("_ada")):
        return f"peran harus salah satu dari {', '.join(PERAN)}"
    if "@" not in a.get("email", ""):
        return "email tidak sah"
    return None


def simpan(daftar: list[dict]) -> int:
    from superset import db, security_manager as sm
    gagal = 0
    for a in daftar:
        nama_akun = a.get("username", "?")
        user = sm.find_user(username=nama_akun)
        a["_ada"] = user is not None
        galat = periksa(a)
        if galat:
            print(f"GAGAL {nama_akun}: {galat}")
            gagal += 1
            continue
        depan, _, belakang = (a.get("nama") or nama_akun).strip().partition(" ")
        peran = [sm.add_role(r) for r in PERAN[a["peran"]]] if a.get("peran") else None
        if user is None:
            user = sm.add_user(a["username"], depan[:64], (belakang or "-")[:64], a["email"], peran,
                               password=a["password"])
            if not user:
                print(f"GAGAL {nama_akun}: tidak bisa dibuat (email sudah dipakai akun lain?)")
                gagal += 1
                continue
            print(f"OK    {nama_akun} dibuat ({a['peran']})")
        else:
            if a.get("nama"):
                user.first_name, user.last_name = depan[:64], (belakang or "-")[:64]
            user.email = a["email"]
            if peran:
                user.roles = peran
            user.active = True
            sm.reset_password(user.id, a["password"])
            print(f"OK    {nama_akun} diperbarui ({a.get('peran') or 'peran tetap'})")
    db.session.commit()
    return gagal


def main() -> None:
    from superset.app import create_app
    daftar = json.loads(sys.stdin.read() or "[]")
    with create_app().app_context():
        gagal = simpan(daftar)
    sys.exit(1 if gagal else 0)


if __name__ == "__main__":
    main()
