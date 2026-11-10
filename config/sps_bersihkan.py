"""Menghapus objek profil DJP (dashboard Beranda & Home Nasional) dari instalasi yang tidak memakainya.

Dijalankan oleh scripts\\bersihkan-profil-djp.ps1:
    python /app/pythonpath/sps_bersihkan.py            # dashboard, chart, dataset, aturan RLS-nya
    python /app/pythonpath/sps_bersihkan.py --koneksi  # + koneksi sumber DJP yang sudah tidak dipakai dataset lain

Yang dihapus HANYA objek buatan dashboard-as-code profil DJP:
    dashboard  slug "beranda", "home-nasional"
    dataset    berawalan "beranda__", "home_nasional__" (+ chart yang memakainya, + aturan RLS "akses__<dataset>")
Dataset latihan, dataset buatan pengguna, dan ALDx Engine tidak disentuh.
Setelah ini, build-dashboards tidak membangunnya lagi kecuali SPS_PROFIL_DJP=1 di .env.
"""

from __future__ import annotations

import sys

SLUG = ("beranda", "home-nasional")
AWALAN = ("beranda__", "home_nasional__")
KONEKSI_DJP = ("Oracle DMP (GENAPP)", "Oracle Dashboard (IKU)", "Oracle Dashboard (DASHBD)", "Oracle Dashboard (TABLEAU)",
               "ClickHouse DMP_OLAP")


def bersihkan(koneksi: bool = False) -> list[str]:
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter, SqlaTable
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    hasil = []
    for d in db.session.query(Dashboard).filter(Dashboard.slug.in_(SLUG)).all():
        hasil.append(f"dashboard '{d.dashboard_title}'")
        db.session.delete(d)

    dataset = [t for t in db.session.query(SqlaTable).all() if t.table_name.startswith(AWALAN)]
    for t in dataset:
        for c in db.session.query(Slice).filter_by(datasource_type="table", datasource_id=t.id).all():
            db.session.delete(c)
        rls = db.session.query(RowLevelSecurityFilter).filter_by(name=f"akses__{t.table_name}").one_or_none()
        if rls is not None:
            db.session.delete(rls)
        db.session.delete(t)
    if dataset:
        hasil.append(f"{len(dataset)} dataset ({', '.join(sorted(t.table_name for t in dataset))}) beserta chart-nya")
    db.session.flush()

    if koneksi:
        for nama in KONEKSI_DJP:
            k = db.session.query(Database).filter_by(database_name=nama).one_or_none()
            if k is None:
                continue
            sisa = db.session.query(SqlaTable).filter_by(database_id=k.id).count()
            if sisa:
                hasil.append(f"koneksi '{nama}' DIBIARKAN: masih dipakai {sisa} dataset lain")
                continue
            db.session.delete(k)
            hasil.append(f"koneksi '{nama}'")
    db.session.commit()
    return hasil


def main() -> None:
    from superset.app import create_app
    with create_app().app_context():
        hasil = bersihkan(koneksi="--koneksi" in sys.argv)
    for h in hasil or ["tidak ada objek profil DJP yang perlu dihapus"]:
        print(f"OK  {h}")


if __name__ == "__main__":
    main()
