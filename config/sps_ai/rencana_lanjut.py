"""ALDx Rencana fase 4: dataset (ukuran/dimensi terdefinisi, label kolom), story, dan HAPUS chart/dashboard.

Dimuat oleh rencana.py (OPERASI/RENCANA/TERAPKAN digabung). Bedanya dengan operasi fase 1: setiap _terapkan_*
di sini MENGEMBALIKAN catatan cara mengurungkan ("urung"), karena perubahannya bukan sekadar kolom dashboard/chart:

    {"jenis": "definisi", ...}   ukuran/dimensi baru -> dihapus lagi (sps_studio/definisi.py)
    {"jenis": "label", ...}      label kolom -> label lama
    {"jenis": "story_baru"/"story_ubah"/"story_hapus", ...}
    {"jenis": "impor", "ald": base64, ...}
        HAPUS chart/dashboard: sebelum dihapus, objeknya diekspor sebagai berkas .ald (sps_berkas, kunci server).
        Urungkan = impor berkas itu kembali (mode timpa, koneksi asal) lalu chart dipasang lagi di dashboard-nya.

Semua tetap lewat pratinjau -> Simpan -> Urungkan di panel AI; snapshot dihapus otomatis setelah 7 hari.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from sps_ai import alat
from sps_ai import rencana as R

OPERASI = {
    "tambah_ukuran": "Tambah ukuran (metrik) terdefinisi ke dataset: nama + rumus agregat, mis. SUM(laba)/SUM(penjualan)",
    "tambah_dimensi": "Tambah dimensi (kolom hitung) ke dataset: nama + rumus per baris",
    "ganti_label_kolom": "Ganti label tampilan sebuah kolom dataset",
    "buat_story": "Buat story dari satu atau beberapa dashboard (pisahkan dengan koma)",
    "tambah_ke_story": "Tambah dashboard sebagai langkah baru di sebuah story",
    "hapus_story": "Hapus story",
    "hapus_chart": "Hapus chart (bisa diurungkan selama 7 hari)",
    "hapus_dashboard": "Hapus dashboard; chart-nya tetap ada (bisa diurungkan selama 7 hari)",
}


# --- Menemukan dataset & story ---------------------------------------------------------------------
def cari_dataset(teks: Any, konteks: dict | None = None, perintah: str = ""):
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable

    teks = str(teks or "").strip()
    m = re.search(r"#(\d+)\s*$", teks)
    teks = m.group(1) if m else teks
    if not teks or R.norm(teks) in ("ini", "dataset ini", "yang ini"):
        did = R._dari_alamat((konteks or {}).get("alamat", ""), r"(?:datasource_id|dataset)=(\d+)")
        teks = did or ""
    if teks.isdigit():
        t = db.session.query(SqlaTable).get(int(teks))
        if t is not None and security_manager.can_access_datasource(t):
            return t
    calon = [(t.table_name, t) for t in db.session.query(SqlaTable).order_by(SqlaTable.changed_on.desc()).limit(500)
             if security_manager.can_access_datasource(t)]
    return R._pilih(teks, calon, "dataset", perintah)


def cari_story(teks: Any, perintah: str = "") -> dict:
    from sps_ai import story
    calon = [(s["judul"], s) for s in story.daftar() if s.get("boleh_ubah")]
    if not calon:
        raise R.Butuh("Belum ada story milik Anda.")
    s = R._pilih(str(teks or ""), calon, "story", perintah)
    return s


def _daftar_dashboard(teks: str, konteks) -> list:
    bagian = [x.strip() for x in re.split(r",|\bdan\b|;", str(teks or "")) if x.strip()]
    if not bagian:
        raise R.Butuh("Dashboard apa saja yang masuk story ini?")
    return [R.cari_dashboard(x, konteks) for x in bagian]


# --- Dataset ----------------------------------------------------------------------------------------
def _rencana_definisi(o: dict, konteks, jenis: str) -> dict:
    from sps_studio import definisi
    t = cari_dataset(o.get("dataset"), konteks, f"tambah {jenis} {o.get('nama') or '...'} = {o.get('rumus') or '...'} di dataset {{}}")
    definisi._boleh_ubah()
    nama, rumus = str(o.get("nama") or "").strip(), str(o.get("rumus") or "").strip()
    if not nama or not rumus:
        raise R.Butuh(f"Nama dan rumus {jenis} apa? Contoh: tambah {jenis} margin = SUM(laba) / SUM(penjualan) di dataset {t.table_name}"
                      if jenis == "ukuran" else
                      f"Nama dan rumus {jenis} apa? Contoh: tambah dimensi kelompok = CASE WHEN total >= 1000000 THEN 'Besar' "
                      f"ELSE 'Kecil' END di dataset {t.table_name}")
    if any(n.lower() == nama.lower() for n in [c.column_name for c in t.columns] + [m.metric_name for m in t.metrics]):
        raise R.Butuh(f"Nama '{nama}' sudah dipakai di dataset {t.table_name}. Pilih nama lain.")
    hasil = definisi.uji(t, jenis, rumus)                     # rumus salah -> InputSalah, tidak pernah tersimpan
    contoh = hasil.get("contoh") or []
    return {"op": f"tambah_{jenis}", "dataset_id": t.id, "nama": nama, "rumus": rumus, "kunci": [],
            "teks": f"Dataset **{t.table_name}**: tambah {jenis} **{nama}** = `{rumus}`"
                    + (f" (contoh hasil: {contoh[0]})" if contoh else ""),
            "peringatan": [], "buka": f"/studio/?dataset={t.id}"}


def _rencana_tambah_ukuran(o: dict, konteks) -> dict:
    return _rencana_definisi(o, konteks, "ukuran")


def _rencana_tambah_dimensi(o: dict, konteks) -> dict:
    return _rencana_definisi(o, konteks, "dimensi")


def _terapkan_definisi(r: dict, jenis: str) -> dict:
    from sps_studio import definisi
    definisi.simpan(r["dataset_id"], {"jenis": jenis, "nama": r["nama"], "rumus": r["rumus"]})
    return {"jenis": "definisi", "dataset_id": r["dataset_id"], "def_jenis": jenis, "nama": r["nama"]}


def _terapkan_tambah_ukuran(r: dict) -> dict:
    return _terapkan_definisi(r, "ukuran")


def _terapkan_tambah_dimensi(r: dict) -> dict:
    return _terapkan_definisi(r, "dimensi")


def _rencana_ganti_label_kolom(o: dict, konteks) -> dict:
    from sps_studio import definisi
    t = cari_dataset(o.get("dataset"), konteks, f"ganti label kolom {o.get('kolom') or '...'} menjadi ... di dataset {{}}")
    definisi._boleh_ubah()
    calon = [(c.column_name, c) for c in t.columns] + [(c.verbose_name, c) for c in t.columns if c.verbose_name]
    c = R._pilih(str(o.get("kolom") or ""), calon, "kolom", f"ganti label kolom {{}} menjadi ... di dataset {t.table_name}")
    judul = str(o.get("judul") or "").strip()[:200]
    if not judul:
        raise R.Butuh(f"Label baru untuk kolom '{c.column_name}' apa?")
    return {"op": "ganti_label_kolom", "dataset_id": t.id, "kolom": c.column_name, "judul": judul, "kunci": [],
            "teks": f"Dataset **{t.table_name}**: label kolom `{c.column_name}` → **{judul}**", "peringatan": [],
            "buka": f"/studio/?dataset={t.id}"}


def _kolom(dataset_id: int, nama: str):
    t = alat._dataset(int(dataset_id))
    c = next((x for x in t.columns if x.column_name == nama), None)
    if c is None:
        raise alat.InputSalah(f"Kolom '{nama}' sudah tidak ada.")
    return c


def _terapkan_ganti_label_kolom(r: dict) -> dict:
    from sps_studio import definisi
    definisi._boleh_ubah()
    c = _kolom(r["dataset_id"], r["kolom"])
    lama, c.verbose_name = c.verbose_name, r["judul"]
    return {"jenis": "label", "dataset_id": r["dataset_id"], "kolom": r["kolom"], "lama": lama}


# --- Story ------------------------------------------------------------------------------------------
def _rencana_buat_story(o: dict, konteks) -> dict:
    judul = str(o.get("judul") or "").strip()[:255]
    if not judul:
        raise R.Butuh("Judul story apa? Contoh: buat story Ringkasan Bulanan dari dashboard A, B")
    dash = _daftar_dashboard(o.get("dashboard"), konteks)
    return {"op": "buat_story", "judul": judul, "dashboard_ids": [d.id for d in dash], "kunci": [],
            "teks": f"Buat story **{judul}**: " + " → ".join(f"**{d.dashboard_title}**" for d in dash),
            "peringatan": [], "buka": "/asisten/?tab=story"}


def _terapkan_buat_story(r: dict) -> dict:
    from sps_ai import story
    h = story.simpan({"judul": r["judul"], "langkah": [{"dashboard_id": i} for i in r["dashboard_ids"]]})
    return {"jenis": "story_baru", "id": h["id"]}


def _isi_story(story_id: int) -> dict:
    from sps_ai import story
    s = story.ambil(story_id)
    return {"judul": s["judul"], "keterangan": s["keterangan"], "publik": s["publik"],
            "langkah": [{"dashboard_id": x["dashboard_id"], "judul": x.get("judul"), "narasi": x.get("narasi", "")}
                        for x in s["langkah"]]}


def _rencana_tambah_ke_story(o: dict, konteks) -> dict:
    s = cari_story(o.get("story"), f"tambahkan dashboard {o.get('dashboard') or '...'} ke story {{}}")
    d = R.cari_dashboard(o.get("dashboard"), konteks, f"tambahkan dashboard {{}} ke story {s['judul']}")
    return {"op": "tambah_ke_story", "story_id": s["id"], "dashboard_id": d.id, "kunci": [],
            "teks": f"Story **{s['judul']}**: tambah langkah **{d.dashboard_title}** di akhir", "peringatan": [],
            "buka": f"/asisten/story/{s['id']}"}


def _terapkan_tambah_ke_story(r: dict) -> dict:
    from sps_ai import story
    lama = _isi_story(r["story_id"])
    story.simpan({**lama, "langkah": [*lama["langkah"], {"dashboard_id": r["dashboard_id"]}]}, r["story_id"])
    return {"jenis": "story_ubah", "id": r["story_id"], "lama": lama}


def _rencana_hapus_story(o: dict, konteks) -> dict:
    s = cari_story(o.get("story"), "hapus story {}")
    return {"op": "hapus_story", "story_id": s["id"], "kunci": [],
            "teks": f"**Hapus** story **{s['judul']}** ({s['jumlah_langkah']} langkah; dashboard-nya tidak ikut terhapus)",
            "peringatan": [], "buka": "/asisten/?tab=story"}


def _terapkan_hapus_story(r: dict) -> dict:
    from sps_ai import story
    lama = _isi_story(r["story_id"])
    story.hapus(r["story_id"])
    return {"jenis": "story_hapus", "lama": lama}


# --- Hapus chart / dashboard (snapshot .ald untuk Urungkan) -----------------------------------------
def ekspor_ald(jenis: str, ids: list[int]) -> tuple[str, str]:
    """(nama berkas, isi base64) berkas .ald (tanpa data, kunci server) berisi objek ini saat ini."""
    from sps_berkas import paket
    try:
        nama, isi, _ = paket.ekspor(jenis, ids, "ald", catatan="Snapshot ALDx Rencana sebelum perubahan")
    except ValueError as e:
        raise alat.IzinDitolak(f"Snapshot .ald untuk Urungkan tidak bisa dibuat ({e}).") from None
    return nama, base64.b64encode(isi).decode()


def _rencana_hapus_chart(o: dict, konteks) -> dict:
    c = R.cari_chart(o.get("chart"), None, konteks, "hapus chart {}")
    R._milik(c, "chart")
    dash = [d.dashboard_title for d in c.dashboards]
    return {"op": "hapus_chart", "chart_id": c.id, "kunci": [],
            "teks": f"**Hapus** chart **{c.slice_name}**", "buka": "/studio/",
            "peringatan": [f"Chart ini juga hilang dari dashboard: {', '.join(dash[:5])}{'…' if len(dash) > 5 else ''}. "
                           "Urungkan memasangnya kembali."] if dash else []}


def _terapkan_hapus_chart(r: dict) -> dict:
    from superset import db
    from superset.commands.chart.delete import DeleteChartCommand
    from superset.commands.chart.exceptions import ChartDeleteFailedReportsExistError
    from superset.models.slice import Slice
    c = db.session.query(Slice).get(int(r["chart_id"]))
    if c is None:
        raise alat.InputSalah("Chart itu sudah tidak ada.")
    R._milik(c, "chart")
    nama, ald = ekspor_ald("chart", [c.id])
    dash = [{"id": d.id, "position_json": d.position_json, "json_metadata": d.json_metadata,
             "slices": [s.id for s in d.slices]} for d in c.dashboards]
    uuid_, cid = str(c.uuid), c.id
    try:
        DeleteChartCommand([cid]).run()
    except ChartDeleteFailedReportsExistError:
        raise alat.InputSalah("Chart masih dipakai Langganan laporan / Peringatan data; hapus jadwalnya dulu.") from None
    return {"jenis": "impor", "objek": "chart", "nama": nama, "ald": ald, "uuid": uuid_, "lama_id": cid, "dashboard": dash}


def _rencana_hapus_dashboard(o: dict, konteks) -> dict:
    d = R.cari_dashboard(o.get("dashboard"), konteks, "hapus dashboard {}")
    R._milik(d, "dashboard")
    return {"op": "hapus_dashboard", "dashboard_id": d.id, "kunci": [],
            "teks": f"**Hapus** dashboard **{d.dashboard_title}** ({len(d.slices)} chart-nya tetap ada)",
            "peringatan": [], "buka": "/dashboard/list/"}


def _terapkan_hapus_dashboard(r: dict) -> dict:
    from superset import db
    from superset.commands.dashboard.delete import DeleteDashboardCommand
    from superset.models.dashboard import Dashboard
    d = db.session.query(Dashboard).get(int(r["dashboard_id"]))
    if d is None:
        raise alat.InputSalah("Dashboard itu sudah tidak ada.")
    R._milik(d, "dashboard")
    nama, ald = ekspor_ald("dashboard", [d.id])
    uuid_ = str(d.uuid)
    DeleteDashboardCommand([d.id]).run()
    return {"jenis": "impor", "objek": "dashboard", "nama": nama, "ald": ald, "uuid": uuid_}


# --- Mengurungkan -----------------------------------------------------------------------------------
def _ganti_id(nilai, lama: int, baru: int):
    """Ganti id chart lama -> baru di position_json / json_metadata (chartId, chartsInScope, excluded, ...)."""
    if isinstance(nilai, dict):
        return {k: (baru if k == "chartId" and v == lama else _ganti_id(v, lama, baru)) for k, v in nilai.items()}
    if isinstance(nilai, list):
        return [baru if isinstance(x, int) and x == lama else _ganti_id(x, lama, baru) for x in nilai]
    return nilai


def _impor_kembali(u: dict) -> None:
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    from sps_berkas import paket
    isi = base64.b64decode(u["ald"])
    info = paket.periksa(isi)
    peta = {k["uuid"]: k["saran"] for k in info["manifest"].get("koneksi", []) if k.get("saran")}
    kurang = [k["nama"] for k in info["manifest"].get("koneksi", []) if not k.get("saran")]
    if kurang:
        raise alat.InputSalah(f"Koneksi asal ({', '.join(kurang)}) tidak tersedia; impor snapshot .ald lewat menu Berkas.")
    paket.impor(isi, None, peta, mode="timpa", pakai_data=False)
    if u["objek"] != "chart":
        return
    baru = db.session.query(Slice).filter(Slice.uuid == u["uuid"]).first()
    if baru is None:
        raise alat.InputSalah("Chart tidak terbentuk kembali dari snapshot.")
    for s in u.get("dashboard") or []:                # pasang lagi di dashboard tempatnya semula
        d = db.session.query(Dashboard).get(s["id"])
        if d is None:
            continue
        d.position_json = json.dumps(_ganti_id(json.loads(s["position_json"] or "{}"), u["lama_id"], baru.id))
        d.json_metadata = json.dumps(_ganti_id(json.loads(s["json_metadata"] or "{}"), u["lama_id"], baru.id))
        ids = [baru.id if i == u["lama_id"] else i for i in s["slices"]]
        d.slices = db.session.query(Slice).filter(Slice.id.in_(ids or [0])).all()


def urungkan(u: dict) -> None:
    from sps_ai import story
    from sps_studio import definisi
    jenis = u.get("jenis")
    if jenis == "definisi":
        definisi.hapus(u["dataset_id"], u["def_jenis"], u["nama"])
    elif jenis == "label":
        _kolom(u["dataset_id"], u["kolom"]).verbose_name = u["lama"]
    elif jenis == "story_baru":
        story.hapus(u["id"])
    elif jenis == "story_ubah":
        story.simpan(u["lama"], u["id"])
    elif jenis == "story_hapus":
        story.simpan(u["lama"])
    elif jenis == "impor":
        _impor_kembali(u)
    else:
        raise alat.InputSalah(f"Catatan urungkan '{jenis}' tidak dikenal.")


RENCANA = {n: globals()[f"_rencana_{n}"] for n in OPERASI}
TERAPKAN = {n: globals()[f"_terapkan_{n}"] for n in OPERASI}
