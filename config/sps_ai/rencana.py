"""ALDx Rencana: Asisten AI MENGUBAH isi aplikasi lewat operasi kecil -> pratinjau -> Simpan -> Urungkan.

Model AI (atau penerjemah niat niat.py, tanpa model) hanya menulis OPERASI dalam bahasa manusia:
    {"op": "tambah_filter", "dashboard": "tes1", "kolom": "cabang"}
Server yang menyelesaikan sisanya: nama -> id (boleh tidak persis), kolom -> kolom sah tiap dataset,
hak akses & kepemilikan, lalu menyusun PRATINJAU. Belum ada yang berubah sampai pengguna menekan
"Simpan perubahan" di panel AI (POST /asisten/api/rencana/<id>/simpan).

    susun(operasi, username, konteks)  -> peristiwa {"tipe": "rencana", id, baris, peringatan, ...}
    simpan(id, username)               -> snapshot "sebelum" disimpan, operasi dijalankan
    urungkan(id, username)             -> objek dikembalikan ke snapshot (bila belum diubah lagi sesudahnya)
    batal(id, username)

Butuh(pesan, pilihan) = informasi kurang/ambigu: AI bertanya balik, `pilihan` tampil sebagai tombol
(satu klik = perintah lengkap yang bisa langsung dipahami penerjemah niat).

Snapshot (tabel sps_ai_rencana) dihapus otomatis setelah UMUR_SIMPAN_HARI; usulan yang tidak disimpan
kedaluwarsa setelah UMUR_USULAN_JAM. Operasi baru: tambah ke OPERASI, _rencana_<op>, _terapkan_<op>.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text

from sps_ai import alat

log = logging.getLogger(__name__)

OPERASI = {
    "tambah_filter": "Tambah filter dashboard (berlaku di semua chart yang punya kolomnya)",
    "hapus_filter": "Hapus filter dashboard",
    "ganti_judul_dashboard": "Ganti judul dashboard",
    "tambah_chart": "Tambah chart yang sudah ada ke dashboard",
    "buang_chart": "Keluarkan chart dari dashboard (chart-nya tidak dihapus)",
    "ganti_judul_chart": "Ganti judul chart",
    "ubah_jenis_chart": "Ubah jenis chart (batang, garis, pie, tabel, angka, ...)",
}
MAKS_OPERASI = 10
UMUR_USULAN_JAM = 24
UMUR_SIMPAN_HARI = 7
JENIS_FILTER = ("pilihan", "rentang", "waktu")

# kata pengguna -> jenis Studio (sps_studio/aturan.py ATURAN_TANDA)
SINONIM_JENIS = {
    "batang": "batang", "bar": "batang", "kolom": "batang", "column": "batang", "histogram": "batang",
    "garis": "garis", "line": "garis", "tren": "garis", "trend": "garis",
    "pie": "pie", "donat": "pie", "donut": "pie", "lingkaran": "pie", "kue": "pie",
    "tabel": "tabel", "table": "tabel", "pivot": "tabel_pivot", "tabel pivot": "tabel_pivot",
    "angka": "angka", "kpi": "angka", "big number": "angka", "angka besar": "angka", "kartu": "angka",
    "area": "area", "treemap": "treemap", "peta panas": "peta_panas", "heatmap": "peta_panas",
    "corong": "funnel", "funnel": "funnel", "sebar": "sebar", "scatter": "sebar", "bubble": "sebar",
    "radar": "radar", "sunburst": "sunburst", "waterfall": "waterfall", "air terjun": "waterfall",
    "awan kata": "awan_kata", "wordcloud": "awan_kata", "word cloud": "awan_kata", "sankey": "sankey",
    "gauge": "gauge", "meter": "gauge", "box plot": "box_plot", "boxplot": "box_plot",
}


class Butuh(ValueError):
    """Informasi kurang atau ambigu: tanyakan ke pengguna. pilihan = perintah lengkap untuk tombol."""
    def __init__(self, pesan: str, pilihan: list[str] | None = None):
        super().__init__(pesan)
        self.pilihan = [p for p in (pilihan or []) if p][:6]


# --- Penyimpanan -----------------------------------------------------------------------------
_metadata = MetaData()
TABEL = Table(
    "sps_ai_rencana", _metadata,
    Column("id", String(36), primary_key=True),
    Column("username", String(64), index=True),
    Column("dibuat", DateTime), Column("diubah", DateTime),
    Column("status", String(16)),            # usulan | disimpan | diurungkan | batal
    Column("operasi", Text),                 # operasi yang sudah diselesaikan (id, kolom sah)
    Column("cap", Text),                     # {"dashboard:4": changed_on, ...} saat pratinjau / sesudah simpan
    Column("sebelum", Text),                 # snapshot objek sebelum disimpan (untuk Urungkan)
    Column("ringkasan", Text),
)


def _db():
    from superset import db
    TABEL.create(bind=db.engine, checkfirst=True)
    return db


def _baca(rid: str, username: str) -> dict:
    db = _db()
    r = db.session.execute(TABEL.select().where(TABEL.c.id == str(rid))).mappings().first()
    if r is None or r["username"] != username[:64]:
        raise LookupError("Rencana perubahan tidak ditemukan (sudah kedaluwarsa atau milik akun lain).")
    return dict(r)


def _tulis(rid: str, **isi) -> None:
    db = _db()
    db.session.execute(TABEL.update().where(TABEL.c.id == rid).values(diubah=datetime.now(), **isi))
    db.session.commit()


def _bersihkan_lama() -> None:
    db = _db()
    db.session.execute(TABEL.delete().where(TABEL.c.dibuat < datetime.now() - timedelta(days=UMUR_SIMPAN_HARI)))


# --- Menemukan objek dari kata-kata pengguna ----------------------------------------------------
def norm(s: Any) -> str:
    return re.sub(r"[^0-9a-z]+", " ", str(s or "").lower()).strip()


def _pilih(teks: str, calon: list[tuple[str, Any]], jenis: str, perintah: str = "") -> Any:
    """calon = [(nama, objek)]. Persis > memuat > mirip. Tidak ada / ambigu -> Butuh."""
    t = norm(teks)
    if not t:
        raise Butuh(f"{jenis.capitalize()} mana yang dimaksud?",
                    [perintah.format(n) for n, _ in calon[:5]] if perintah else None)
    rapat = t.replace(" ", "")                       # "tes1" = "tes 1" = "TES-1"
    persis = [o for n, o in calon if norm(n) == t] or [o for n, o in calon if norm(n).replace(" ", "") == rapat]
    if len(persis) == 1:
        return persis[0]
    memuat = persis or [o for n, o in calon if t in norm(n) or (len(norm(n)) >= 3 and norm(n) in t)]
    if len(memuat) == 1:
        return memuat[0]
    nama = {id(o): n for n, o in calon}
    kembar = [norm(nama[id(o)]) for o in memuat]
    if len(set(kembar)) < len(kembar):              # nama sama persis: bedakan dengan #id (dipahami cari_*)
        nama = {id(o): f"{nama[id(o)]} #{o.id}" for o in memuat}
    if len(memuat) > 1:
        raise Butuh(f"Ada {len(memuat)} {jenis} yang cocok dengan '{teks}'. Yang mana?",
                    [perintah.format(nama[id(o)]) for o in memuat[:5]] if perintah else None)
    mirip = difflib.get_close_matches(t, [norm(n) for n, _ in calon], n=4, cutoff=0.6)
    if len(mirip) == 1 and difflib.SequenceMatcher(None, t, mirip[0]).ratio() >= 0.8:
        return next(o for n, o in calon if norm(n) == mirip[0])
    usul = [n for n, _ in calon if norm(n) in mirip]
    raise Butuh(f"{jenis.capitalize()} '{teks}' tidak ditemukan." + (" Mungkin maksud Anda:" if usul else ""),
                [perintah.format(n) for n in usul] if perintah else None)


def _dari_alamat(alamat: str, pola: str) -> str | None:
    m = re.search(pola, alamat or "")
    return m.group(1) if m else None


def cari_dashboard(teks: Any, konteks: dict | None = None, perintah: str = ""):
    from superset import db, security_manager
    from superset.models.dashboard import Dashboard

    teks = str(teks or "").strip()
    m = re.search(r"#(\d+)\s*$", teks)
    teks = m.group(1) if m else teks
    if not teks or norm(teks) in ("ini", "dashboard ini", "halaman ini", "yang ini"):
        kunci = _dari_alamat((konteks or {}).get("alamat", ""), r"/superset/dashboard/([^/?#]+)")
        if kunci:
            from sps_ai import wawasan
            d = wawasan._cari_dashboard(kunci)
            if d is not None and security_manager.can_access_dashboard(d):
                return d
        teks = ""                                  # "dashboard ini" di luar halaman dashboard: tanyakan
    if teks.isdigit():
        d = db.session.query(Dashboard).get(int(teks))
        if d is not None and security_manager.can_access_dashboard(d):
            return d
    semua = [d for d in db.session.query(Dashboard).order_by(Dashboard.changed_on.desc()).limit(500)
             if security_manager.can_access_dashboard(d)]
    calon = [(d.dashboard_title or f"Dashboard {d.id}", d) for d in semua]
    return _pilih(teks, calon, "dashboard", perintah)


def _chart_boleh(c) -> bool:
    from sps_ai import wawasan
    return wawasan._boleh_chart(c)


def cari_chart(teks: Any, dash=None, konteks: dict | None = None, perintah: str = ""):
    from superset import db
    from superset.models.slice import Slice

    teks = str(teks or "").strip()
    m = re.search(r"#(\d+)\s*$", teks)
    teks = m.group(1) if m else teks
    if not teks or norm(teks) in ("ini", "chart ini", "grafik ini", "yang ini"):
        sid = _dari_alamat((konteks or {}).get("alamat", ""), r"slice_id=(\d+)")
        if sid:
            c = db.session.query(Slice).get(int(sid))
            if c is not None and _chart_boleh(c):
                return c
        teks = ""
    if teks.isdigit():
        c = db.session.query(Slice).get(int(teks))
        if c is not None and _chart_boleh(c):
            return c
    if dash is not None:
        calon = [(c.slice_name, c) for c in dash.slices if _chart_boleh(c)]
    else:
        calon = [(c.slice_name, c) for c in db.session.query(Slice).order_by(Slice.changed_on.desc()).limit(500)
                 if _chart_boleh(c)]
    return _pilih(teks, calon, "chart", perintah)


def _kolom_dataset(t) -> list:
    return [c for c in t.columns if c.is_active is not False]


def _punya_kolom(chart, kolom: str) -> bool:
    ds = getattr(chart, "datasource", None)
    return bool(ds) and any(c.column_name == kolom for c in _kolom_dataset(ds))


def _punya_waktu(chart) -> bool:
    ds = getattr(chart, "datasource", None)
    return bool(ds) and (bool(getattr(ds, "main_dttm_col", None)) or any(c.is_dttm for c in _kolom_dataset(ds)))


def kolom_dashboard(dash) -> dict[str, dict]:
    """{nama kolom: {kolom, label, dataset_ids, charts, dttm, teks}} untuk semua dataset chart di dashboard."""
    hasil: dict[str, dict] = {}
    for c in dash.slices:
        ds = getattr(c, "datasource", None)
        if not ds or not _chart_boleh(c):
            continue
        for k in _kolom_dataset(ds):
            h = hasil.setdefault(k.column_name, {"kolom": k.column_name, "label": k.verbose_name or "",
                                                 "dataset_ids": [], "charts": set(), "dttm": bool(k.is_dttm),
                                                 "teks": "CHAR" in str(k.type or "").upper() or "TEXT" in str(k.type or "").upper()
                                                 or "STRING" in str(k.type or "").upper()})
            if ds.id not in h["dataset_ids"]:
                h["dataset_ids"].append(ds.id)
            h["charts"].add(c.id)
    return hasil


_KODE = re.compile(r"(^|_)(id|kd|kode|key|uuid|no|nomor)(_|$)", re.I)


def saran_kolom(dash, n: int = 6) -> list[str]:
    """Kolom yang paling cocok jadi filter: dimiliki banyak chart, teks/waktu, bukan kode."""
    kol = kolom_dashboard(dash)

    def skor(h):
        return (len(h["charts"]), h["teks"] or h["dttm"], not _KODE.search(h["kolom"]))
    return [h["kolom"] for h in sorted(kol.values(), key=skor, reverse=True)][:n]


def cari_kolom(teks: Any, dash, perintah: str = "") -> dict:
    kol = kolom_dashboard(dash)
    if not kol:
        raise Butuh(f"Dashboard '{dash.dashboard_title}' belum punya chart dengan dataset yang bisa difilter.")
    calon = [(h["kolom"], h) for h in kol.values()] + [(h["label"], h) for h in kol.values() if h["label"]]
    if not str(teks or "").strip():
        raise Butuh(f"Filter berdasarkan kolom apa? Kolom yang dimiliki chart di dashboard '{dash.dashboard_title}':",
                    [perintah.format(k) for k in saran_kolom(dash)])
    try:
        return _pilih(str(teks), calon, "kolom", "")
    except Butuh as e:
        raise Butuh(str(e) + " Kolom yang tersedia:", [perintah.format(k) for k in saran_kolom(dash)]) from None


_AWALAN_NAMA = re.compile(r"^(?:nm|nama)\s+")


def kolom_dari_teks(dash, teks: Any) -> str:
    """Tebak kolom filter dari KALIMAT PENGGUNA bila model AI tidak mengisinya ('pengguna bisa memilih saluran
    penjualan' -> saluran). Hanya kolom milik chart di dashboard itu; frasa terpanjang menang; kembar -> '' (tanya)."""
    t = f" {norm(teks)} "
    judul = norm(dash.dashboard_title)
    if judul:
        t = t.replace(f" {judul} ", " ").replace(f" {judul.replace(' ', '')} ", " ")
    terbaik: dict[int, set] = {}
    for h in kolom_dashboard(dash).values():
        frasa = {norm(h["kolom"]), norm(h["label"]), _AWALAN_NAMA.sub("", norm(h["kolom"]))} - {""}
        for f in frasa:
            if len(f) >= 3 and f" {f} " in t:
                terbaik.setdefault(len(f), set()).add(h["kolom"])
    if not terbaik:
        return ""
    calon = terbaik[max(terbaik)]
    return next(iter(calon)) if len(calon) == 1 else ""


def jenis_chart(teks: Any) -> str:
    from sps_studio.aturan import ATURAN_TANDA
    t = norm(teks).replace("grafik ", "").replace("chart ", "").replace("diagram ", "").strip()
    if t.replace(" ", "_") in ATURAN_TANDA:
        return t.replace(" ", "_")
    for kata in sorted(SINONIM_JENIS, key=len, reverse=True):
        if kata in t:
            return SINONIM_JENIS[kata]
    raise Butuh(f"Jenis chart '{teks}' tidak dikenal.",
                [f"jenis {j}" for j in ("batang", "garis", "pie", "tabel", "angka", "treemap")])


# --- Kepemilikan & cap waktu --------------------------------------------------------------------
def _milik(obj, jenis: str) -> None:
    from superset import security_manager
    from superset.exceptions import SupersetSecurityException
    try:
        security_manager.raise_for_ownership(obj)
    except SupersetSecurityException:
        nama = getattr(obj, "dashboard_title", None) or getattr(obj, "slice_name", "")
        raise alat.IzinDitolak(f"Anda bukan pemilik {jenis} '{nama}', jadi tidak boleh mengubahnya. "
                               "Minta pemiliknya atau Admin.") from None


def _cap(obj) -> str:
    return obj.changed_on.isoformat() if getattr(obj, "changed_on", None) else ""


def _objek(kunci: str):
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    jenis, oid = kunci.split(":")
    return db.session.query(Dashboard if jenis == "dashboard" else Slice).get(int(oid))


# --- Menyusun rencana (pratinjau) ----------------------------------------------------------------
def _filter_dash(dash) -> list[dict]:
    try:
        return json.loads(dash.json_metadata or "{}").get("native_filter_configuration") or []
    except ValueError:
        return []


def _rencana_tambah_filter(o: dict, konteks) -> dict:
    dash = cari_dashboard(o.get("dashboard"), konteks, f"tambah filter {o.get('kolom') or ''} di dashboard {{}}".replace("  ", " "))
    _milik(dash, "dashboard")
    jenis = str(o.get("jenis") or "").strip().lower()
    tebakan = ""
    if jenis == "waktu" or norm(o.get("kolom")) in ("waktu", "tanggal", "periode", "rentang waktu"):
        kandidat = [c for c in dash.slices if _punya_waktu(c)]
        if not kandidat:
            raise Butuh(f"Tidak ada chart di '{dash.dashboard_title}' yang datasetnya punya kolom waktu.")
        ds = kandidat[0].datasource
        kol = ds.main_dttm_col or next(c.column_name for c in _kolom_dataset(ds) if c.is_dttm)
        masuk = [c.id for c in dash.slices if _punya_waktu(c)]
        h = {"kolom": kol, "dataset_ids": [ds.id], "dttm": True}
        jenis = "waktu"
    else:
        diminta = str(o.get("kolom") or "").strip()
        tebakan = "" if diminta else kolom_dari_teks(dash, (konteks or {}).get("pertanyaan"))
        h = cari_kolom(diminta or tebakan, dash, f"tambah filter {{}} di dashboard {dash.dashboard_title}")
        masuk = [c.id for c in dash.slices if _punya_kolom(c, h["kolom"])]
        jenis = jenis if jenis in JENIS_FILTER else ("waktu" if h["dttm"] else "pilihan")
    from sps_studio import dasbor
    import hashlib
    fid = dasbor.AWALAN_FILTER + hashlib.sha1(f"{h['dataset_ids'][0]}:{h['kolom']}".encode()).hexdigest()[:12]
    for f in _filter_dash(dash):
        sasaran = (f.get("targets") or [{}])[0]
        if f.get("id") == fid or (jenis != "waktu" and (sasaran.get("column") or {}).get("name") == h["kolom"]):
            raise Butuh(f"Dashboard '{dash.dashboard_title}' sudah punya filter '{f.get('name')}' untuk kolom itu.")
    luar = [c.slice_name for c in dash.slices if c.id not in masuk]
    nama = (str(o.get("nama") or "").strip() or ("Rentang waktu" if jenis == "waktu" else
            (kolom_dashboard(dash).get(h["kolom"], {}).get("label") or h["kolom"].replace("_", " ").title())))[:100]
    teks = f"Dashboard **{dash.dashboard_title}**: tambah filter **{nama}** ({jenis}, kolom `{h['kolom']}`), " \
           f"berlaku di **{len(masuk)} dari {len(dash.slices)}** chart"
    return {"op": "tambah_filter", "dashboard_id": dash.id, "dataset_id": h["dataset_ids"][0], "kolom": h["kolom"],
            "jenis": jenis, "nama": nama, "kunci": [f"dashboard:{dash.id}"], "teks": teks,
            "peringatan": ([f"Kolom `{h['kolom']}` ditebak dari kalimat Anda; tekan Batal bila keliru."] if tebakan else []) +
                          ([f"Tidak berlaku untuk: {', '.join(luar[:6])}{'…' if len(luar) > 6 else ''} "
                            f"(datasetnya tidak punya kolom `{h['kolom']}`)."] if luar else []),
            "buka": f"/superset/dashboard/{dash.id}/"}


def _rencana_hapus_filter(o: dict, konteks) -> dict:
    dash = cari_dashboard(o.get("dashboard"), konteks, "hapus filter di dashboard {}")
    _milik(dash, "dashboard")
    ada = _filter_dash(dash)
    if not ada:
        raise Butuh(f"Dashboard '{dash.dashboard_title}' tidak punya filter.")
    calon = []
    for f in ada:
        kol = ((f.get("targets") or [{}])[0].get("column") or {}).get("name") or ""
        calon += [(f.get("name") or kol, f)] + ([(kol, f)] if kol else [])
    f = _pilih(str(o.get("kolom") or o.get("nama") or ""), calon, "filter",
               f"hapus filter {{}} di dashboard {dash.dashboard_title}")
    return {"op": "hapus_filter", "dashboard_id": dash.id, "filter_id": f["id"], "kunci": [f"dashboard:{dash.id}"],
            "teks": f"Dashboard **{dash.dashboard_title}**: hapus filter **{f.get('name')}**", "peringatan": [],
            "buka": f"/superset/dashboard/{dash.id}/"}


def _rencana_ganti_judul_dashboard(o: dict, konteks) -> dict:
    dash = cari_dashboard(o.get("dashboard"), konteks, "ganti judul dashboard {} menjadi ...")
    _milik(dash, "dashboard")
    judul = str(o.get("judul") or "").strip()[:500]
    if not judul:
        raise Butuh(f"Judul baru untuk dashboard '{dash.dashboard_title}' apa?")
    return {"op": "ganti_judul_dashboard", "dashboard_id": dash.id, "judul": judul, "kunci": [f"dashboard:{dash.id}"],
            "teks": f"Ganti judul dashboard **{dash.dashboard_title}** → **{judul}**", "peringatan": [],
            "buka": f"/superset/dashboard/{dash.id}/"}


def _rencana_tambah_chart(o: dict, konteks) -> dict:
    dash = cari_dashboard(o.get("dashboard"), konteks, f"tambah chart {o.get('chart') or '...'} ke dashboard {{}}")
    _milik(dash, "dashboard")
    c = cari_chart(o.get("chart"), None, konteks, f"tambah chart {{}} ke dashboard {dash.dashboard_title}")
    if c in dash.slices:
        raise Butuh(f"Chart '{c.slice_name}' sudah ada di dashboard '{dash.dashboard_title}'.")
    return {"op": "tambah_chart", "dashboard_id": dash.id, "chart_id": c.id, "kunci": [f"dashboard:{dash.id}"],
            "teks": f"Dashboard **{dash.dashboard_title}**: tambah chart **{c.slice_name}** (baris baru di bawah)",
            "peringatan": [], "buka": f"/superset/dashboard/{dash.id}/"}


def _rencana_buang_chart(o: dict, konteks) -> dict:
    dash = cari_dashboard(o.get("dashboard"), konteks, f"keluarkan chart {o.get('chart') or '...'} dari dashboard {{}}")
    _milik(dash, "dashboard")
    c = cari_chart(o.get("chart"), dash, konteks, f"keluarkan chart {{}} dari dashboard {dash.dashboard_title}")
    return {"op": "buang_chart", "dashboard_id": dash.id, "chart_id": c.id, "kunci": [f"dashboard:{dash.id}"],
            "teks": f"Dashboard **{dash.dashboard_title}**: keluarkan chart **{c.slice_name}** (chart-nya tetap ada)",
            "peringatan": [], "buka": f"/superset/dashboard/{dash.id}/"}


def _rencana_ganti_judul_chart(o: dict, konteks) -> dict:
    c = cari_chart(o.get("chart"), None, konteks, "ganti judul chart {} menjadi ...")
    _milik(c, "chart")
    judul = str(o.get("judul") or "").strip()[:250]
    if not judul:
        raise Butuh(f"Judul baru untuk chart '{c.slice_name}' apa?")
    return {"op": "ganti_judul_chart", "chart_id": c.id, "judul": judul, "kunci": [f"chart:{c.id}"],
            "teks": f"Ganti judul chart **{c.slice_name}** → **{judul}**", "peringatan": [],
            "buka": f"/explore/?slice_id={c.id}"}


def _params_jenis_baru(c, jenis: str) -> tuple[str, dict, str]:
    """viz_type + params baru untuk chart `c` dengan jenis `jenis`; juga dipakai saat pratinjau (validasi)."""
    from sps_ai import wawasan
    p = wawasan._params(c)
    spec = p.get("sps_studio")
    if spec:                                        # chart Studio: ubah tanda lalu bangun ulang dengan pembangun Studio
        from sps_studio import lembar
        t, lb = lembar.dari_dict({**spec, "tanda": jenis, "judul": c.slice_name, "dataset_id": c.datasource_id})
        if lb.pakai_analitik:
            raise Butuh(f"Chart '{c.slice_name}' memakai ramalan/analitik; ubah jenisnya di Studio Visual.")
        try:
            lembar.periksa_tanda(lb)
        except alat.InputSalah as e:
            raise Butuh(f"Chart '{c.slice_name}' tidak bisa jadi {jenis}: {e}") from None
        viz, baru = lembar.ke_superset(t, lb)
        return viz, baru, "Studio"
    if jenis not in alat.JENIS_CHART:
        raise Butuh(f"Chart '{c.slice_name}' dibuat di editor lanjutan; lewat Asisten jenisnya hanya bisa diubah ke "
                    f"{', '.join(alat.JENIS_CHART)}. Jenis lain: buka di Studio Visual.",
                    [f"ubah chart {c.slice_name} menjadi {j}" for j in ("batang", "garis", "pie", "tabel")])
    metrik, kelompok = wawasan._metrik(p), wawasan._kelompok(p)
    if not metrik:
        raise Butuh(f"Chart '{c.slice_name}' tidak punya metrik yang bisa dipakai ulang.")
    try:
        viz, baru = alat.params_chart(jenis, metrik, kelompok, [])
    except alat.InputSalah as e:
        raise Butuh(f"Chart '{c.slice_name}' tidak bisa jadi {jenis}: {e}") from None
    for k in ("adhoc_filters", "granularity_sqla", "time_range", "color_scheme", "row_limit"):
        if k in p:
            baru[k] = p[k]
    return viz, baru, "lanjutan"


def _rencana_ubah_jenis_chart(o: dict, konteks) -> dict:
    from sps_studio.aturan import ATURAN_TANDA
    c = cari_chart(o.get("chart"), None, konteks, f"ubah chart {{}} menjadi {o.get('jenis') or 'batang'}")
    _milik(c, "chart")
    jenis = jenis_chart(o.get("jenis"))
    viz, _, _ = _params_jenis_baru(c, jenis)
    if viz == c.viz_type:
        raise Butuh(f"Chart '{c.slice_name}' sudah berjenis {ATURAN_TANDA.get(jenis, {}).get('label', jenis)}.")
    return {"op": "ubah_jenis_chart", "chart_id": c.id, "jenis": jenis, "kunci": [f"chart:{c.id}"],
            "teks": f"Ubah chart **{c.slice_name}** menjadi **{ATURAN_TANDA.get(jenis, {}).get('label', jenis)}**",
            "peringatan": [], "buka": f"/explore/?slice_id={c.id}"}


RENCANA = {n: globals()[f"_rencana_{n}"] for n in OPERASI}


def susun(operasi: list[dict], username: str, konteks: dict | None = None) -> dict:
    """Operasi (bahasa manusia) -> peristiwa rencana untuk panel AI. Melempar Butuh / IzinDitolak / InputSalah."""
    if not isinstance(operasi, list) or not operasi:
        raise alat.InputSalah("Tidak ada operasi. Isi `operasi` dengan minimal satu perubahan.")
    if len(operasi) > MAKS_OPERASI:
        raise alat.InputSalah(f"Maksimal {MAKS_OPERASI} perubahan sekaligus.")
    hasil = []
    for o in operasi:
        if not isinstance(o, dict) or o.get("op") not in RENCANA:
            raise alat.InputSalah(f"Operasi '{(o or {}).get('op') if isinstance(o, dict) else o}' tidak dikenal. "
                                  f"Pilih: {', '.join(OPERASI)}.")
        hasil.append(RENCANA[o["op"]](o, konteks))
    cap = {k: _cap(_objek(k)) for r in hasil for k in r["kunci"]}
    rid = str(uuid.uuid4())
    db = _db()
    _bersihkan_lama()
    db.session.execute(TABEL.insert().values(
        id=rid, username=username[:64], dibuat=datetime.now(), diubah=datetime.now(), status="usulan",
        operasi=json.dumps(hasil, ensure_ascii=False), cap=json.dumps(cap), sebelum="",
        ringkasan="\n".join(r["teks"] for r in hasil)[:4000]))
    db.session.commit()
    return {"tipe": "rencana", "id": rid, "status": "usulan", "baris": [r["teks"] for r in hasil],
            "peringatan": [p for r in hasil for p in r["peringatan"]], "buka": hasil[-1].get("buka")}


# --- Menerapkan ------------------------------------------------------------------------------------
def _ambil(model, oid: int):
    from superset import db
    obj = db.session.query(model).get(int(oid))
    if obj is None:
        raise alat.InputSalah("Objek yang akan diubah sudah tidak ada.")
    return obj


def _dash(oid):
    from superset.models.dashboard import Dashboard
    d = _ambil(Dashboard, oid)
    _milik(d, "dashboard")
    return d


def _chart(oid):
    from superset.models.slice import Slice
    c = _ambil(Slice, oid)
    _milik(c, "chart")
    return c


def _meta(dash) -> dict:
    try:
        return json.loads(dash.json_metadata or "{}")
    except ValueError:
        return {}


def _lingkup_ulang(dash, meta: dict) -> None:
    """Filter berlingkup seluruh dashboard: chart yang datasetnya tidak punya kolom target dikecualikan."""
    for f in meta.get("native_filter_configuration") or []:
        scope = f.get("scope") or {}
        if scope.get("rootPath", ["ROOT_ID"]) != ["ROOT_ID"]:
            continue
        kol = ((f.get("targets") or [{}])[0].get("column") or {}).get("name")
        waktu = f.get("filterType") == "filter_time"
        cocok = (lambda c: _punya_waktu(c)) if waktu else (lambda c: not kol or _punya_kolom(c, kol))
        f["chartsInScope"] = [c.id for c in dash.slices if cocok(c)]
        scope["excluded"] = [c.id for c in dash.slices if not cocok(c)]
        f["scope"] = {"rootPath": ["ROOT_ID"], **scope}


def _terapkan_tambah_filter(r: dict) -> None:
    from sps_studio import dasbor
    dash = _dash(r["dashboard_id"])
    meta = _meta(dash)
    f = dasbor.filter_native([{"nama": r["nama"], "dataset_id": r["dataset_id"], "kolom": r["kolom"],
                               "jenis": r["jenis"]}], [c.id for c in dash.slices])[0]
    ada = meta.get("native_filter_configuration") or []
    if any(x.get("id") == f["id"] for x in ada):
        raise alat.InputSalah(f"Filter '{r['nama']}' sudah ada.")
    meta["native_filter_configuration"] = [*ada, f]
    _lingkup_ulang(dash, meta)
    dash.json_metadata = json.dumps(meta)


def _terapkan_hapus_filter(r: dict) -> None:
    dash = _dash(r["dashboard_id"])
    meta = _meta(dash)
    ada = meta.get("native_filter_configuration") or []
    meta["native_filter_configuration"] = [f for f in ada if f.get("id") != r["filter_id"]]
    if len(meta["native_filter_configuration"]) == len(ada):
        raise alat.InputSalah("Filter itu sudah tidak ada.")
    dash.json_metadata = json.dumps(meta)


def _terapkan_ganti_judul_dashboard(r: dict) -> None:
    dash = _dash(r["dashboard_id"])
    dash.dashboard_title = r["judul"]
    pos = json.loads(dash.position_json or "{}")
    if isinstance(pos.get("HEADER_ID"), dict):
        pos["HEADER_ID"].setdefault("meta", {})["text"] = r["judul"]
        dash.position_json = json.dumps(pos)


def _terapkan_tambah_chart(r: dict) -> None:
    from superset.models.slice import Slice
    dash, c = _dash(r["dashboard_id"]), _ambil(Slice, r["chart_id"])
    if not _chart_boleh(c):
        raise alat.IzinDitolak("Chart itu tidak boleh Anda pakai.")
    pos = json.loads(dash.position_json or "{}")
    if not pos:
        pos = {"DASHBOARD_VERSION_KEY": "v2", "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
               "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]}}
    akhir = uuid.uuid4().hex[:8]
    rid, cid = f"ROW-ai{akhir}", f"CHART-ai{akhir}"
    pos.setdefault("GRID_ID", {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]})
    pos["GRID_ID"].setdefault("children", []).append(rid)
    pos[rid] = {"type": "ROW", "id": rid, "children": [cid], "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"}}
    pos[cid] = {"type": "CHART", "id": cid, "children": [], "parents": ["ROOT_ID", "GRID_ID", rid],
                "meta": {"width": 6, "height": 50, "chartId": c.id, "uuid": str(c.uuid), "sliceName": c.slice_name}}
    dash.position_json = json.dumps(pos)
    dash.slices = [*dash.slices, c]
    meta = _meta(dash)
    _lingkup_ulang(dash, meta)
    dash.json_metadata = json.dumps(meta)


def _terapkan_buang_chart(r: dict) -> None:
    dash = _dash(r["dashboard_id"])
    cid = int(r["chart_id"])
    pos = json.loads(dash.position_json or "{}")
    buang = [k for k, v in pos.items() if isinstance(v, dict) and v.get("type") == "CHART"
             and (v.get("meta") or {}).get("chartId") == cid]
    for k in buang:
        induk = (pos[k].get("parents") or [None])[-1]
        pos.pop(k)
        while induk in pos:
            pos[induk]["children"] = [x for x in pos[induk].get("children", []) if x in pos and x not in buang]
            if pos[induk]["children"] or pos[induk].get("type") not in ("ROW", "COLUMN"):
                break
            atas = (pos[induk].get("parents") or [None])[-1]       # baris/kolom kosong ikut dibuang
            pos.pop(induk)
            if atas in pos:
                pos[atas]["children"] = [x for x in pos[atas].get("children", []) if x != induk]
            induk = atas
    dash.position_json = json.dumps(pos)
    dash.slices = [s for s in dash.slices if s.id != cid]
    meta = _meta(dash)
    for f in meta.get("native_filter_configuration") or []:
        f["chartsInScope"] = [x for x in f.get("chartsInScope") or [] if x != cid]
        if isinstance(f.get("scope"), dict):
            f["scope"]["excluded"] = [x for x in f["scope"].get("excluded") or [] if x != cid]
    dash.json_metadata = json.dumps(meta)


def _terapkan_ganti_judul_chart(r: dict) -> None:
    _chart(r["chart_id"]).slice_name = r["judul"]


def _terapkan_ubah_jenis_chart(r: dict) -> None:
    c = _chart(r["chart_id"])
    viz, params, _ = _params_jenis_baru(c, r["jenis"])
    c.viz_type, c.params, c.query_context = viz, json.dumps(params), None


TERAPKAN = {n: globals()[f"_terapkan_{n}"] for n in OPERASI}

_KOLOM_SNAP = {"dashboard": ("dashboard_title", "position_json", "json_metadata", "css"),
               "chart": ("slice_name", "viz_type", "params", "query_context", "datasource_id")}


def _snapshot(kunci: str) -> dict:
    obj = _objek(kunci)
    snap = {k: getattr(obj, k) for k in _KOLOM_SNAP[kunci.split(":")[0]]}
    if kunci.startswith("dashboard:"):
        snap["slices"] = [s.id for s in obj.slices]
    return snap


def _pulihkan(kunci: str, snap: dict) -> None:
    from superset import db
    from superset.models.slice import Slice
    obj = _objek(kunci)
    if obj is None:
        raise alat.InputSalah("Objek sudah dihapus; tidak bisa diurungkan.")
    _milik(obj, kunci.split(":")[0])
    for k in _KOLOM_SNAP[kunci.split(":")[0]]:
        setattr(obj, k, snap.get(k))
    if "slices" in snap:
        obj.slices = db.session.query(Slice).filter(Slice.id.in_(snap["slices"] or [0])).all()


def _periksa_cap(cap: dict, pesan: str) -> None:
    for k, v in cap.items():
        obj = _objek(k)
        if obj is None or _cap(obj) != v:
            nama = getattr(obj, "dashboard_title", None) or getattr(obj, "slice_name", None) or k
            raise alat.InputSalah(f"'{nama}' sudah diubah di tempat lain sejak {pesan}. Minta ulang perubahannya.")


def _catat_audit(aksi: str, r: dict, username: str) -> None:
    try:
        import sps_audit
        sps_audit.catat("asisten", aksi, (r.get("ringkasan") or "")[:200], {"rencana": r["id"]}, oleh=username)
    except Exception:  # noqa: BLE001 - audit gagal tidak menggagalkan perubahan
        log.warning("ALDx Rencana: audit tidak tercatat", exc_info=True)


def _ald_sebelum(cap: dict) -> list[dict]:
    """Berkas .ald objek yang akan diubah, diambil SEBELUM perubahan (bisa diunduh dari kartu rencana).
    Gagal membuatnya (mis. tanpa izin ekspor) tidak menghalangi penyimpanan; hanya unduhan yang tidak tersedia."""
    from sps_ai import rencana_lanjut
    hasil = []
    for jenis in ("dashboard", "chart"):
        ids = [int(k.split(":")[1]) for k in cap if k.startswith(jenis + ":")]
        if not ids:
            continue
        try:
            nama, b64 = rencana_lanjut.ekspor_ald(jenis, ids)
            hasil.append({"nama": nama, "b64": b64})
        except Exception:  # noqa: BLE001
            log.info("ALDx Rencana: snapshot .ald %s %s tidak dibuat", jenis, ids, exc_info=True)
    return hasil


def simpan(rid: str, username: str) -> dict:
    from superset import db
    from sps_ai import rencana_lanjut
    r = _baca(rid, username)
    if r["status"] != "usulan":
        raise alat.InputSalah(f"Rencana ini sudah {r['status']}.")
    if r["dibuat"] < datetime.now() - timedelta(hours=UMUR_USULAN_JAM):
        raise alat.InputSalah("Rencana ini sudah kedaluwarsa. Minta ulang perubahannya.")
    operasi, cap = json.loads(r["operasi"]), json.loads(r["cap"] or "{}")
    _periksa_cap(cap, "pratinjau dibuat")
    objek = {k: _snapshot(k) for k in cap}
    ald = _ald_sebelum(cap)
    urung: list[dict] = []
    try:
        for o in operasi:
            u = TERAPKAN[o["op"]](o)
            if u:
                urung.append(u)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Sebagian operasi (definisi, story, hapus) menyimpan sendiri: kembalikan yang sudah terjadi.
        for u in reversed(urung):
            try:
                rencana_lanjut.urungkan(u)
                db.session.commit()
            except Exception:  # noqa: BLE001
                db.session.rollback()
                log.exception("ALDx Rencana: gagal mengembalikan %s setelah simpan gagal", u.get("jenis"))
        raise
    ald += [{"nama": u["nama"], "b64": u["ald"]} for u in urung if u.get("jenis") == "impor"]
    sesudah = {k: _cap(_objek(k)) for k in cap}
    _tulis(rid, status="disimpan", cap=json.dumps(sesudah),
           sebelum=json.dumps({"objek": objek, "urung": urung, "ald": ald}, default=str))
    _catat_audit("Simpan perubahan Asisten AI", r, username)
    from sps_ai import wawasan
    wawasan.lupakan()
    return {"ok": True, "status": "disimpan", "buka": operasi[-1].get("buka"), "unduh": len(ald)}


def urungkan(rid: str, username: str) -> dict:
    from superset import db
    from sps_ai import rencana_lanjut
    r = _baca(rid, username)
    if r["status"] != "disimpan":
        raise alat.InputSalah("Hanya perubahan yang sudah disimpan yang bisa diurungkan.")
    _periksa_cap(json.loads(r["cap"] or "{}"), "perubahan disimpan")
    data = json.loads(r["sebelum"] or "{}")
    if "objek" not in data:                         # format awal: {kunci: snapshot}
        data = {"objek": data, "urung": []}
    try:
        for u in reversed(data.get("urung") or []):   # hapus / definisi / story: catatan khusus, urutan terbalik
            rencana_lanjut.urungkan(u)
        for k, snap in data["objek"].items():
            _pulihkan(k, snap)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    _tulis(rid, status="diurungkan")
    _catat_audit("Urungkan perubahan Asisten AI", r, username)
    from sps_ai import wawasan
    wawasan.lupakan()
    return {"ok": True, "status": "diurungkan", "buka": json.loads(r["operasi"])[-1].get("buka")}


def unduh(rid: str, username: str, i: int = 0) -> tuple[str, bytes]:
    """Berkas .ald 'sebelum perubahan' milik rencana yang sudah disimpan (dihapus otomatis setelah 7 hari)."""
    import base64
    r = _baca(rid, username)
    try:
        daftar = json.loads(r["sebelum"] or "{}").get("ald") or []
    except (ValueError, AttributeError):
        daftar = []
    if not 0 <= i < len(daftar):
        raise LookupError("Snapshot .ald untuk perubahan ini tidak tersedia.")
    return daftar[i]["nama"], base64.b64decode(daftar[i]["b64"])


def batal(rid: str, username: str) -> dict:
    r = _baca(rid, username)
    if r["status"] == "usulan":
        _tulis(rid, status="batal")
    return {"ok": True, "status": "batal"}


# Operasi fase 4 (dataset, story, hapus chart/dashboard): sps_ai/rencana_lanjut.py
from sps_ai import rencana_lanjut as _lanjut  # noqa: E402  (impor di akhir: modul itu memakai fungsi di atas)

OPERASI.update(_lanjut.OPERASI)
RENCANA.update(_lanjut.RENCANA)
TERAPKAN.update(_lanjut.TERAPKAN)
