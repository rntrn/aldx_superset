"""Ekspor & impor berkas .ald / .aldx .

    .ald    "workbook": definisi dashboard / chart / dataset. TANPA data. Saat dibuka, chart mengambil
            data dari koneksi di server tujuan (hak akses & RLS penerima yang berlaku).
    .aldx   "paket": seperti .ald, ditambah (opsional) SALINAN DATA tiap dataset (Parquet).
            Data diambil sebagai PEMBUAT berkas, jadi hanya berisi baris yang boleh ia lihat (RLS).
            Saat diimpor, data dimuat ke ALDx Engine sehingga dashboard langsung jalan tanpa koneksi sumber.

Isi ZIP di dalam berkas (sebelum dienkripsi, lihat sandi.py):
    manifest.json             judul, jenis, pembuat, daftar koneksi (nama & jenis saja) & dataset
    superset/...yaml          definisi ekspor resmi Superset (dashboards/, charts/, datasets/, metadata.yaml)
                              databases/ DIBUANG: berkas tidak pernah membawa alamat server, user, atau password
    data/<uuid dataset>.parquet   hanya .aldx dengan data

Impor:
    1. periksa()  buka berkas, tampilkan isi, sarankan koneksi tujuan untuk tiap koneksi asal
    2. impor()    koneksi asal -> koneksi tujuan yang DIPILIH penerima (harus boleh ia akses),
                  mode "salinan" (objek baru) atau "timpa" (perbarui objek dengan UUID sama)

Keamanan data impor:
    - memuat data ke ALDx Engine hanya untuk peran di Pengaturan "berkas.peran_muat_data" (bawaan Admin)
    - dataset hasil data .aldx otomatis diberi aturan RLS: hanya pengimpor & Admin yang melihat barisnya,
      sampai Admin membagikannya (ubah/hapus aturan "ALDx berkas: ..." di Kelola › Hak akses data)
    - setiap ekspor/impor tercatat di jejak audit (sps_audit)
"""

from __future__ import annotations

import io
import json
import logging
import re
import uuid as _uuid
import zipfile
from datetime import datetime, timezone

import yaml

import sps_audit
from sps_berkas import sandi
from sps_berkas.sandi import GalatBerkas

log = logging.getLogger(__name__)

FORMAT = ("ald", "aldx")
MAKS_ISI_MB = 4096                         # batas total isi ZIP setelah diekstrak (cegah "zip bomb")
POLA_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


# --- Jenis objek -------------------------------------------------------------------------------
def _jenis(nama: str) -> dict:
    """Perintah ekspor/impor Superset, model, dan izin untuk satu jenis objek."""
    from superset.commands.chart.export import ExportChartsCommand
    from superset.commands.chart.importers.v1 import ImportChartsCommand
    from superset.commands.dashboard.export import ExportDashboardsCommand
    from superset.commands.dashboard.importers.v1 import ImportDashboardsCommand
    from superset.commands.dataset.export import ExportDatasetsCommand
    from superset.commands.dataset.importers.v1 import ImportDatasetsCommand
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    peta = {
        "dashboard": dict(ekspor=ExportDashboardsCommand, impor=ImportDashboardsCommand, model=Dashboard,
                          izin="Dashboard", folder="dashboards/", judul="dashboard_title",
                          alamat=lambda o: f"/superset/dashboard/{o.id}/"),
        "chart": dict(ekspor=ExportChartsCommand, impor=ImportChartsCommand, model=Slice,
                      izin="Chart", folder="charts/", judul="slice_name",
                      alamat=lambda o: f"/explore/?slice_id={o.id}"),
        "dataset": dict(ekspor=ExportDatasetsCommand, impor=ImportDatasetsCommand, model=SqlaTable,
                        izin="Dataset", folder="datasets/", judul="table_name",
                        alamat=lambda o: f"/explore/?datasource_type=table&datasource_id={o.id}"),
    }
    if nama not in peta:
        raise GalatBerkas("Jenis harus dashboard, chart, atau dataset.")
    return peta[nama]


def _boleh(aksi: str, model: str) -> bool:
    from superset import security_manager as sm
    return sm.is_admin() or sm.can_access(aksi, model)


def boleh_muat_data() -> bool:
    """K9: hanya peran di Pengaturan "berkas.peran_muat_data" (bawaan Admin) yang boleh memuat data berkas ke
    ALDx Engine. Superadmin selalu boleh. Peran lain tetap bisa mengimpor definisi (tanpa data)."""
    import sps_superadmin
    from flask import g
    if sps_superadmin.adalah():
        return True
    izinkan = set(_atur().get("berkas.peran_muat_data") or ["Admin"])
    return any(r.name in izinkan for r in getattr(g.user, "roles", []) or [])


NAMA_RLS_IMPOR = "ALDx berkas: {tabel} (khusus {user})"


def _kunci_untuk_pengimpor(tabel_baru: list[str], pengimpor: str) -> int:
    """P3: dataset hasil data .aldx hanya terlihat oleh pengimpor (dan Admin) sampai dibagikan.

    Satu aturan RLS Base per dataset: klausa benar hanya untuk pengimpor; role Admin dikecualikan.
    Membagikan = Admin mengubah / menghapus aturan itu di Kelola › Hak akses data (RLS).
    """
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import RowLevelSecurityFilter, SqlaTable
    from superset.utils.core import RowLevelSecurityFilterType

    from sps_engine.ekstrak import database_engine
    engine, n = database_engine(), 0
    nama_aman = pengimpor.replace("'", "''")
    admin = sm.find_role("Admin")
    for t in db.session.query(SqlaTable).filter(SqlaTable.database_id == engine.id,
                                                SqlaTable.table_name.in_(tabel_baru)):
        r = RowLevelSecurityFilter(
            name=NAMA_RLS_IMPOR.format(tabel=t.table_name, user=pengimpor)[:255],
            filter_type=RowLevelSecurityFilterType.BASE,
            clause=f"'{{{{ current_username() }}}}' = '{nama_aman}'",
            description=("Dibuat otomatis saat impor berkas .aldx: data hanya terlihat oleh pengimpor & Admin. "
                         "Hapus atau ubah aturan ini untuk membagikan data."))
        r.tables.append(t)
        if admin:
            r.roles.append(admin)
        db.session.add(r)
        n += 1
    db.session.commit()
    return n


def _atur() -> dict:
    from sps_server import penyimpanan
    return penyimpanan.nilai_semua()


# --- Ekspor ------------------------------------------------------------------------------------
def _ambil_ekspor(perintah, ids: list[int]) -> dict[str, str]:
    """Jalankan ekspor Superset (hanya objek yang boleh diakses pengguna) -> {nama berkas: isi yaml}."""
    from superset.commands.exceptions import CommandException
    try:
        return {nama: isi() for nama, isi in perintah(ids).run()}
    except CommandException as exc:
        raise GalatBerkas("Objek tidak ditemukan atau Anda tidak berhak mengaksesnya.") from exc


def _info_koneksi(isi: dict[str, str]) -> list[dict]:
    hasil = []
    for nama, teks in isi.items():
        if nama.startswith("databases/"):
            c = yaml.safe_load(teks)
            hasil.append({"uuid": c["uuid"], "nama": c["database_name"],
                          "jenis": str(c.get("sqlalchemy_uri", "")).split(":", 1)[0].split("+")[0]})
    return hasil


def _info_dataset(isi: dict[str, str]) -> list[dict]:
    hasil = []
    for nama, teks in isi.items():
        if nama.startswith("datasets/"):
            c = yaml.safe_load(teks)
            hasil.append({"uuid": c["uuid"], "nama": c["table_name"], "skema": c.get("schema"),
                          "koneksi_uuid": c["database_uuid"], "virtual": bool(c.get("sql"))})
    return hasil


def _salin_data(ds_info: dict, maks_baris: int) -> tuple[bytes | None, dict]:
    """Ambil isi dataset SEBAGAI pengguna yang login (aturan RLS berlaku) -> Parquet."""
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import SqlaTable

    t = db.session.query(SqlaTable).filter_by(uuid=_uuid.UUID(ds_info["uuid"])).one_or_none()
    if t is None or not sm.can_access_datasource(t):
        return None, {"lewati": "tidak berhak mengakses dataset"}
    kolom = [c.column_name for c in t.columns if not c.expression]
    hasil = t.query({"columns": kolom, "metrics": [], "groupby": None, "filter": [], "extras": {},
                     "is_timeseries": False, "row_limit": (maks_baris + 1) if maks_baris else None,
                     "orderby": [], "granularity": None, "from_dttm": None, "to_dttm": None})
    if hasil.status != "success" or hasil.df is None:
        return None, {"lewati": "kueri gagal: " + str(hasil.error_message or "")[:200]}
    df = hasil.df
    terpotong = bool(maks_baris) and len(df) > maks_baris
    if terpotong:
        df = df.head(maks_baris)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue(), {"baris": len(df), "terpotong": terpotong}


def _nama_berkas(judul: str, format_: str) -> str:
    dasar = re.sub(r"[^A-Za-z0-9._-]+", "-", judul).strip("-")[:80] or "berkas"
    return f"{dasar}.{format_}"


def periksa_ekspor(jenis: str, ids: list[int], format_: str, dengan_data: bool = False,
                   kata_sandi: str | None = None, catatan: str = "") -> dict:
    """Cek permintaan ekspor (format, izin, pengaturan) tanpa membuat berkas. Kembalikan info jenis."""
    if format_ not in FORMAT:
        raise GalatBerkas("Format harus ald atau aldx.")
    j = _jenis(jenis)
    if not ids:
        raise GalatBerkas("Pilih minimal satu objek.")
    if not _boleh("can_export", j["izin"]):
        raise GalatBerkas(f"Anda tidak punya izin ekspor {jenis}.")
    if dengan_data and format_ != "aldx":
        raise GalatBerkas("Data hanya bisa dibawa berkas .aldx.")
    if dengan_data and not _atur().get("berkas.snapshot_data", True):
        raise GalatBerkas("Admin menonaktifkan berkas berisi data (Pusat Kendali › Pengaturan › Berkas).")
    if kata_sandi is not None and len(kata_sandi) < 8:
        raise GalatBerkas("Kata sandi minimal 8 karakter.")
    return j


def ekspor(jenis: str, ids: list[int], format_: str, dengan_data: bool = False,
           kata_sandi: str | None = None, catatan: str = "") -> tuple[str, bytes, dict]:
    """Buat berkas .ald/.aldx. Kembalikan (nama berkas, isi, manifest)."""
    from flask import g

    j = periksa_ekspor(jenis, ids, format_, dengan_data, kata_sandi, catatan)
    atur = _atur()

    isi = _ambil_ekspor(j["ekspor"], ids)
    koneksi, dataset = _info_koneksi(isi), _info_dataset(isi)
    utama = [yaml.safe_load(t) for n, t in isi.items() if n.startswith(j["folder"])]
    judul = utama[0].get(j["judul"], "berkas") if len(utama) == 1 else f"{len(utama)} {jenis}"

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for nama, teks in isi.items():
            if not nama.startswith("databases/"):       # alamat & akun koneksi tidak pernah ikut
                z.writestr("superset/" + nama, teks)
        if dengan_data:
            maks = int(atur.get("berkas.baris_snapshot") or 0)
            for d in dataset:
                data, info = _salin_data(d, maks)
                d.update(info)
                if data is not None:
                    d["data"] = f"data/{d['uuid']}.parquet"
                    z.writestr(d["data"], data)
        manifest = {
            "format": format_, "jenis": jenis, "judul": judul, "catatan": catatan[:2000],
            "dibuat_oleh": getattr(g.user, "username", "?"),
            "dibuat": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "isi": {k: sum(1 for n in isi if n.startswith(k + "s/")) for k in ("dashboard", "chart", "dataset")},
            "koneksi": koneksi, "dataset": dataset, "dengan_data": bool(dengan_data),
        }
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    berkas = sandi.bungkus(zbuf.getvalue(), format_, kata_sandi or None)
    log.info("ALDx berkas: %s mengekspor %s %s -> .%s (data=%s, sandi=%s)", manifest["dibuat_oleh"], jenis, ids,
             format_, bool(dengan_data), bool(kata_sandi))
    sps_audit.catat("berkas", "Ekspor berkas", judul, {"format": format_, "data": bool(dengan_data),
                                                       "sandi": bool(kata_sandi), "jenis": jenis, "ids": ids})
    return _nama_berkas(judul, format_), berkas, manifest


# --- Buka & periksa ----------------------------------------------------------------------------
def _buka_zip(data: bytes, kata_sandi: str | None) -> tuple[dict, dict, dict[str, bytes], bool]:
    kepala, isi, terverifikasi = sandi.buka(data, kata_sandi)
    try:
        z = zipfile.ZipFile(io.BytesIO(isi))
    except zipfile.BadZipFile as exc:
        raise GalatBerkas("Isi berkas rusak.") from exc
    if sum(i.file_size for i in z.infolist()) > MAKS_ISI_MB * 1024 * 1024:
        raise GalatBerkas("Isi berkas terlalu besar.")
    berkas = {n: z.read(n) for n in z.namelist()
              if n == "manifest.json" or n.startswith(("superset/", "data/"))}
    if "manifest.json" not in berkas:
        raise GalatBerkas("Berkas tidak punya manifest.")
    return kepala, json.loads(berkas["manifest.json"]), berkas, terverifikasi


def _koneksi_boleh() -> list:
    from superset import db, security_manager as sm
    from superset.models.core import Database
    return [d for d in db.session.query(Database).order_by(Database.database_name)
            if sm.is_admin() or sm.can_access_database(d)]


def _uuid_ada(berkas: dict[str, bytes]) -> int:
    """Jumlah objek di berkas yang UUID-nya sudah ada di server ini."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice
    n = 0
    for nama, teks in berkas.items():
        for folder, model in (("superset/dashboards/", Dashboard), ("superset/charts/", Slice),
                              ("superset/datasets/", SqlaTable)):
            if nama.startswith(folder):
                u = yaml.safe_load(teks)["uuid"]
                n += db.session.query(model.id).filter_by(uuid=_uuid.UUID(u)).count()
    return n


def periksa(data: bytes, kata_sandi: str | None = None) -> dict:
    """Ringkasan berkas untuk layar impor + saran koneksi tujuan."""
    kepala, manifest, berkas, terverifikasi = _buka_zip(data, kata_sandi)
    boleh = _koneksi_boleh()
    from sps_engine.ekstrak import adalah_engine
    for k in manifest.get("koneksi", []):
        sama = next((d for d in boleh if str(d.uuid) == k["uuid"]), None) or \
            next((d for d in boleh if d.database_name == k["nama"]), None)
        k["saran"] = sama.id if sama else None
    return {"kepala": kepala, "manifest": manifest, "terverifikasi": terverifikasi,
            "sudah_ada": _uuid_ada(berkas),
            "koneksi_tujuan": [{"id": d.id, "nama": d.database_name, "engine": adalah_engine(d)} for d in boleh],
            "punya_data": any(d.get("data") for d in manifest.get("dataset", [])),
            "boleh_impor": _boleh("can_write", _jenis(manifest["jenis"])["izin"]),
            "boleh_muat_data": boleh_muat_data()}


# --- Impor -------------------------------------------------------------------------------------
def _uuid_baru(berkas: dict[str, bytes]) -> dict[str, str]:
    """Peta UUID lama -> baru untuk semua dashboard, chart, dataset (mode salinan)."""
    peta = {}
    for nama, teks in berkas.items():
        if nama.startswith(("superset/dashboards/", "superset/charts/", "superset/datasets/")):
            peta[yaml.safe_load(teks)["uuid"]] = str(_uuid.uuid4())
    return peta


def _muat_data(parquet: bytes, nama_dataset: str) -> tuple[str, str, dict]:
    """Muat snapshot ke ALDx Engine -> (skema, nama tabel, tipe kolom)."""
    import pandas as pd

    from sps_engine import klien as K, tabel as T
    from sps_server import batas

    batas.periksa_kuota_engine(_atur())
    df = pd.read_parquet(io.BytesIO(parquet))
    nama = T.nama_aman(f"berkas_{_uuid.uuid4().hex[:6]}_{nama_dataset}").lower()[:120]
    _, tipe = T.isi_penuh(K.klien(), K.nama_db(), nama, iter([df]), [])
    return K.nama_db(), nama, tipe


def _hapus_tabel(dibuat: list[str]) -> None:
    from sps_engine import klien as K
    for nama in dibuat:
        try:
            K.klien().perintah(f"DROP TABLE IF EXISTS {K.nama_db()}.`{nama}`")
        except Exception:  # noqa: BLE001 - pembersihan terbaik-usaha
            log.warning("ALDx berkas: gagal menghapus tabel %s", nama)


def _dataset_yang_ada(berkas: dict[str, bytes], ds_data: dict, tujuan: dict, ganti: dict[str, str]) -> set[str]:
    """Dataset yang tabelnya SUDAH terdaftar di koneksi tujuan dipakai apa adanya (tidak diubah, tidak diduplikasi).

    Superset hanya mengizinkan satu dataset per (koneksi, skema, tabel); tanpa langkah ini impor akan
    menimpa definisi dataset milik orang lain. Caranya: UUID dataset di berkas diganti UUID dataset yang ada.
    """
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    ada_uuid = set()
    for nama, teks in berkas.items():
        if not nama.startswith("superset/datasets/"):
            continue
        c = yaml.safe_load(teks)
        if c["uuid"] in ds_data:
            continue
        ada = db.session.query(SqlaTable).filter_by(database_id=tujuan[c["database_uuid"]].id,
                                                   schema=c.get("schema"), table_name=c["table_name"]).first()
        if ada is not None:
            ganti[c["uuid"]] = str(ada.uuid)
            ada_uuid.add(str(ada.uuid))
    return ada_uuid


def _dashboard_salinan(teks: str) -> str:
    """Salinan dashboard: slug dikosongkan (slug unik; Superset akan MENIMPA dashboard ber-slug sama) dan
    judul diberi akhiran "(salinan)" bila judul yang sama sudah ada."""
    from superset import db
    from superset.models.dashboard import Dashboard
    c = yaml.safe_load(teks)
    c["slug"] = None
    if db.session.query(Dashboard.id).filter_by(dashboard_title=c["dashboard_title"]).first():
        c["dashboard_title"] = f"{c['dashboard_title']} (salinan)"
    return yaml.safe_dump(c, sort_keys=False, allow_unicode=True)


def impor(data: bytes, kata_sandi: str | None, peta_koneksi: dict[str, int], mode: str = "salinan",
          pakai_data: bool = True) -> dict:
    """Impor berkas. peta_koneksi: {uuid koneksi asal: id koneksi tujuan}."""
    from flask import g
    from superset import db
    from superset.commands.database.export import ExportDatabasesCommand
    from superset.commands.exceptions import CommandException, CommandInvalidError

    from sps_engine.ekstrak import database_engine

    if mode not in ("salinan", "timpa"):
        raise GalatBerkas("Mode harus salinan atau timpa.")
    _, manifest, berkas, _ = _buka_zip(data, kata_sandi)
    j = _jenis(manifest["jenis"])
    if not _boleh("can_write", j["izin"]):
        raise GalatBerkas(f"Anda tidak punya izin membuat {manifest['jenis']}.")

    boleh = {d.id: d for d in _koneksi_boleh()}
    ds_data = {d["uuid"]: d for d in manifest.get("dataset", []) if pakai_data and d.get("data")}
    if ds_data and not _boleh("can_write", "Dataset"):
        raise GalatBerkas("Memuat data berkas butuh izin membuat dataset.")
    if ds_data and not boleh_muat_data():
        raise GalatBerkas("Peran Anda tidak boleh memuat data dari berkas (Pusat Kendali › Pengaturan › "
                          "Batas data). Hilangkan centang 'Pakai data di berkas' untuk mengimpor definisinya saja.")
    if ds_data and mode == "timpa":
        raise GalatBerkas("Berkas berisi data selalu diimpor sebagai salinan baru (pilih mode salinan).")

    perlu = {d["koneksi_uuid"] for d in manifest.get("dataset", []) if d["uuid"] not in ds_data}
    tujuan = {}
    for k in manifest.get("koneksi", []):
        if k["uuid"] not in perlu:
            continue
        d = boleh.get(int(peta_koneksi.get(k["uuid"]) or 0))
        if d is None:
            raise GalatBerkas(f"Pilih koneksi tujuan untuk '{k['nama']}' (koneksi yang boleh Anda akses).")
        tujuan[k["uuid"]] = d

    ganti = _uuid_baru(berkas) if mode == "salinan" else {}
    dipakai = _dataset_yang_ada(berkas, ds_data, tujuan, ganti)
    engine, dibuat = (database_engine() if ds_data else None), []
    isi: dict[str, str] = {}
    try:
        for nama, mentah in berkas.items():
            if not nama.startswith("superset/"):
                continue
            teks = mentah.decode("utf-8")
            if ganti:
                teks = POLA_UUID.sub(lambda m: ganti.get(m.group(0), m.group(0)), teks)
            if nama.startswith("superset/datasets/"):
                c = yaml.safe_load(teks)
                asal = next((d for u, d in ds_data.items() if ganti.get(u, u) == c["uuid"]), None)
                if asal is not None:                               # data ikut: arahkan ke ALDx Engine
                    skema, tabel, _ = _muat_data(berkas[asal["data"]], c["table_name"])
                    dibuat.append(tabel)
                    c.update(database_uuid=str(engine.uuid), schema=skema, table_name=tabel, sql=None, catalog=None)
                    c["description"] = (f"Data dari berkas .aldx '{manifest['judul']}' "
                                        f"(dibuat {manifest['dibuat_oleh']}, {manifest['dibuat'][:10]}).")
                else:
                    c["database_uuid"] = str(tujuan[c["database_uuid"]].uuid)
                    c["catalog"] = None
                teks = yaml.safe_dump(c, sort_keys=False, allow_unicode=True)
            elif nama.startswith("superset/dashboards/") and mode == "salinan":
                teks = _dashboard_salinan(teks)
            isi[nama[len("superset/"):]] = teks
        for d in {*tujuan.values(), *([engine] if engine else [])}:
            isi[f"databases/sps_{d.id}.yaml"] = ExportDatabasesCommand._file_content(d)

        if manifest["jenis"] == "dataset":       # dataset yang sudah ada tidak diimpor ulang (tidak diubah)
            isi = {n: t for n, t in isi.items()
                   if not (n.startswith("datasets/") and yaml.safe_load(t)["uuid"] in dipakai)}
        sebelum = {o.id for o in db.session.query(j["model"].id)}
        if any(n.startswith(j["folder"]) for n in isi):
            j["impor"](isi, overwrite=(mode == "timpa")).run()
    except CommandInvalidError as exc:
        _hapus_tabel(dibuat)
        if "already exists" in str(exc) or "overwrite" in str(exc):
            raise GalatBerkas("Objek di berkas sudah ada di server ini. Pilih mode Salinan baru atau Timpa.") from exc
        raise GalatBerkas(f"Berkas tidak valid untuk server ini: {str(exc)[:300]}") from exc
    except CommandException as exc:
        _hapus_tabel(dibuat)
        raise GalatBerkas(f"Impor gagal: {str(exc)[:300]}") from exc
    except Exception:
        _hapus_tabel(dibuat)
        raise

    uuid_utama = [ganti.get(u, u) for u in
                  (yaml.safe_load(t)["uuid"] for n, t in berkas.items() if n.startswith("superset/" + j["folder"]))]
    objek = db.session.query(j["model"]).filter(j["model"].uuid.in_([_uuid.UUID(u) for u in uuid_utama])).all()
    pengimpor = getattr(g.user, "username", "?")
    dikunci = _kunci_untuk_pengimpor(dibuat, pengimpor) if dibuat else 0
    log.info("ALDx berkas: %s mengimpor '%s' (%s, data=%d tabel)", pengimpor, manifest["judul"], mode, len(dibuat))
    sps_audit.catat("berkas", "Impor berkas", manifest["judul"],
                    {"mode": mode, "tabel_data": len(dibuat), "dibuat_oleh": manifest.get("dibuat_oleh")})
    return {"jenis": manifest["jenis"], "judul": manifest["judul"], "tabel_data": len(dibuat), "dataset_dipakai": len(dipakai),
            "dikunci_pengimpor": dikunci,
            "objek": [{"id": o.id, "nama": getattr(o, j["judul"]), "alamat": j["alamat"](o),
                       "baru": o.id not in sebelum} for o in objek]}
