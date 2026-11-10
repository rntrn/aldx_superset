"""Membangun / memperbarui semua dashboard "as code" di Superset.

Dijalankan oleh scripts/build-dashboards.ps1:
    python /app/pythonpath/sps_build_dashboards.py

Menambah dashboard baru: buat modul sps_dash_<nama>.py berisi objek
Dashboard (contoh: sps_dash_home.py), lalu daftarkan di DASHBOARDS.

Dashboard profil DJP (Beranda & Home Nasional) hanya dibangun bila SPS_PROFIL_DJP=1 di .env
DAN koneksi sumbernya ada (Oracle DMP). Perusahaan lain: otomatis dilewati.
Menghapus yang sudah terlanjur dibuat: scripts\bersihkan-profil-djp.ps1
"""

import os

from sps_dash_beranda import BERANDA
from sps_dash_home import HOME_NASIONAL
from sps_ai.tampilan import siapkan_izin
from sps_dashboard_builder import build
import sps_engine
import sps_identitas
import sps_server
import sps_studio
import sps_superadmin

DASHBOARDS = [BERANDA, HOME_NASIONAL]


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
        profil_djp = os.environ.get("SPS_PROFIL_DJP") == "1"
        for dashboard in DASHBOARDS:
            if not profil_djp:
                print(f"--  '{dashboard.title}' dilewati (profil DJP tidak aktif: SPS_PROFIL_DJP kosong)")
                continue
            if not _koneksi_ada(dashboard.database_name):
                print(f"--  '{dashboard.title}' dilewati (koneksi '{dashboard.database_name}' tidak ada; profil DJP)")
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


if __name__ == "__main__":
    main()
