"""Warna kategori tetap per dashboard (U10).

Masalah: Superset memberi warna kategori menurut urutan kemunculan di browser. Pengguna dengan data berbeda
(mis. RLS per cabang) bisa melihat "Elektronik" biru, pengguna lain oranye, pada chart yang sama.

Solusi: tulis `label_colors` di metadata dashboard. Superset memakai label_colors untuk SEMUA penonton, jadi
warna sama untuk semua orang. Nilai kategori diambil dari kolom dimensi tiap chart (sebagai Admin, tanpa RLS,
maks. MAKS_NILAI per kolom), diurutkan abjad, lalu diberi warna palet ALDx secara bergiliran.
Warna yang sudah diatur pembuat dashboard (label_colors yang ada) tidak diubah.

Dijalankan:
    - scripts\\build-dashboards.ps1 (semua dashboard)
    - backgrounder tiap malam 02:30 (tugas sps.warna.kunci) untuk dashboard & kategori baru
"""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

MAKS_NILAI = 60                     # kategori lebih banyak dari ini biasanya bukan untuk diwarnai satu per satu
KUNCI_DIMENSI = ("groupby", "columns", "series", "entity", "groupbyRows", "groupbyColumns")


def _palet() -> list[str]:
    from flask import current_app
    skema = current_app.config.get("EXTRA_CATEGORICAL_COLOR_SCHEMES") or []
    bawaan = next((s for s in skema if s.get("isDefault")), skema[0] if skema else None)
    return list(bawaan["colors"]) if bawaan else ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]


def _dimensi(form_data: dict) -> list[str]:
    nama = []
    for k in KUNCI_DIMENSI:
        v = form_data.get(k)
        for x in (v if isinstance(v, list) else [v] if v else []):
            if isinstance(x, str):
                nama.append(x)
            elif isinstance(x, dict) and x.get("sqlExpression") is None and x.get("column_name"):
                nama.append(x["column_name"])
    return list(dict.fromkeys(nama))


def kunci_dashboard(dash) -> int:
    """Lengkapi label_colors satu dashboard. Kembalikan jumlah label baru."""
    meta = json.loads(dash.json_metadata or "{}")
    warna = dict(meta.get("label_colors") or {})
    nilai: set[str] = set()
    for chart in dash.slices:
        ds = chart.datasource
        if ds is None:
            continue
        try:
            fd = json.loads(chart.params or "{}")
        except ValueError:
            continue
        kolom_ada = {c.column_name: c for c in ds.columns}
        for kol in _dimensi(fd):
            c = kolom_ada.get(kol)
            if c is None or c.is_dttm or (c.type or "").upper().startswith(("INT", "FLOAT", "DECIMAL", "NUMERIC", "DOUBLE")):
                continue
            try:
                isi = ds.values_for_column(column_name=kol, limit=MAKS_NILAI + 1)
            except Exception as exc:  # noqa: BLE001 - sumber mati: lewati kolom ini
                log.info("ALDx warna: %s.%s dilewati (%s)", ds.table_name, kol, exc)
                continue
            if len(isi) <= MAKS_NILAI:
                nilai.update(str(v) for v in isi if v is not None)
    palet, baru = _palet(), 0
    terpakai = len(warna)
    for v in sorted(nilai):
        if v not in warna:
            warna[v] = palet[(terpakai + baru) % len(palet)]
            baru += 1
    if baru:
        meta["label_colors"] = warna
        dash.json_metadata = json.dumps(meta)
    return baru


def kunci_semua() -> str:
    """Semua dashboard, dijalankan sebagai Admin (data lengkap tanpa RLS)."""
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard
    from superset.utils.core import override_user

    admin = next((u for u in security_manager.get_all_users() if u.is_active
                  and any(r.name == "Admin" for r in u.roles)), None)
    if admin is None:
        return "warna kategori: tidak ada akun Admin aktif"
    total = jumlah = 0
    with override_user(admin):
        for d in db.session.query(Dashboard).all():
            n = kunci_dashboard(d)
            total += n
            jumlah += bool(n)
    db.session.commit()
    return f"warna kategori tetap: {total} label baru di {jumlah} dashboard"


try:
    from superset.extensions import celery_app

    @celery_app.task(name="sps.warna.kunci")
    def tugas_kunci() -> str:
        hasil = kunci_semua()
        log.info("ALDx %s", hasil)
        return hasil
except Exception:  # noqa: BLE001 - dimuat di luar Superset
    tugas_kunci = None
