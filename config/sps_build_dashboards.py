"""Membangun / memperbarui semua dashboard "as code" di Superset.

Dijalankan oleh scripts/build-dashboards.ps1:
    python /app/pythonpath/sps_build_dashboards.py

Menambah dashboard "as code": buat modul sps_dash_<nama>.py berisi objek Dashboard
(lihat docs/07-dashboard-sebagai-kode.md), lalu daftarkan di DASHBOARDS.
Dashboard yang koneksi sumbernya belum ada otomatis dilewati.
"""

import os

from sps_ai.tampilan import siapkan_izin
from sps_dashboard_builder import build
import sps_engine
import sps_identitas
import sps_server
import sps_studio
import sps_superadmin

DASHBOARDS: list = []          # objek sps_dashboard_builder.Dashboard dari modul sps_dash_<nama>.py


def _koneksi_ada(nama: str) -> bool:
    from superset import db
    from superset.models.core import Database
    return db.session.query(Database).filter_by(database_name=nama).count() > 0


def main() -> None:
    from superset.app import create_app

    owner = os.environ.get("ADMIN_USERNAME", "admin")
    with create_app().app_context():
        for hasil in sps_identitas.siapkan():        # identitas awal dari .env (preset, nama, logo)
            print(f"OK  {hasil}")
        for dashboard in DASHBOARDS:
            if not _koneksi_ada(dashboard.database_name):
                print(f"--  '{dashboard.title}' dilewati (koneksi '{dashboard.database_name}' belum ada)")
                continue
            print(f"Membangun '{dashboard.title}' ...")
            print(f"OK  {build(dashboard, owner)}")
        siapkan_izin()
        print("OK  izin menu Asisten AI")
        for hasil in sps_engine.siapkan():           # koneksi ALDx Engine + tabel ekstrak
            print(f"OK  {hasil}")
        for hasil in sps_server.siapkan():           # menu Pusat Kendali + upload ke engine
            print(f"OK  {hasil}")
        print(f"OK  {sps_studio.siapkan()}")         # menu Studio Visual
        for hasil in sps_superadmin.siapkan():       # role Superadmin untuk ADMIN_USERNAME
            print(f"OK  {hasil}")
        import sps_security
        for hasil in sps_security.rapikan_role_bawaan():   # hak minimum role bawaan (Gamma/Alpha)
            print(f"OK  {hasil}")
        from sps_studio import ramalan
        print(f"OK  {ramalan.tandai_semua()}")             # dataset ramalan = dataset sistem (U17)
        import sps_warna
        print(f"OK  {sps_warna.kunci_semua()}")              # warna kategori sama untuk semua pengguna
        import sps_sematkan
        for hasil in sps_sematkan.siapkan():                  # role penonton dashboard yang disematkan
            print(f"OK  {hasil}")


if __name__ == "__main__":
    main()
