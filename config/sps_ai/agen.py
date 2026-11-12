"""Putaran kerja agent: model <-> alat, sampai model memberi jawaban akhir.

PERAN (peran.py): /analis, /panduan, /data-engineer, /ahli-ui-ux, /hw-engineer. Setiap peran punya
instruksi & daftar alat sendiri; instruksi umum (bahasa, halaman yang sedang dibuka, privasi) sama.

    pertanyaan -> model memilih alat -> alat dijalankan (sebagai user) ->
    hasil dikembalikan ke model -> ... -> jawaban akhir (maks. langkah_maks alat)

PRIVASI (kirim_data di ai.yaml):
    true  -> model menerima isi hasil query (maks. baris_ke_model baris)
    false -> model hanya menerima nama kolom & jumlah baris; isi data
             langsung ditampilkan ke pengguna sebagai "peristiwa" (events)

AUDIT: setiap pertanyaan dicatat di tabel sps_ai_log (siapa, model, alat, status).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text

from sps_ai import alat, auto, llm, peran as P, wawasan
from sps_ai.pengaturan import ModelAI, Pengaturan

log = logging.getLogger(__name__)


BAHASA = {"id": "Bahasa Indonesia", "en": "English", "ja": "日本語 (Japanese)"}


def _sistem(peran: P.Peran | None = None, konteks: dict | None = None, bahasa: str = "id",
            model: ModelAI | None = None, peta: bool = False) -> str:
    """Instruksi sistem: umum (nama aplikasi, bahasa, privasi) + peta pengetahuan + halaman aktif + instruksi peran.

    peta=True: sisipkan ringkasan dataset/dashboard/chart yang boleh diakses (wawasan.py).
    Teks yang tampil di layar hanya diteruskan bila model boleh menerima data (kirim_data).
    """
    try:
        from flask import current_app
        n = current_app.config.get("SPS_IDENTITAS") or {}
    except RuntimeError:                      # di luar aplikasi (uji unit)
        n = {}
    peran = peran or P.PETA_PERAN["analis"]
    teks = SISTEM.replace("{perusahaan}", n.get("nama_perusahaan") or "perusahaan") \
                 .replace("{aplikasi}", n.get("nama_aplikasi") or "ALDx") \
                 .replace("{peran}", peran.nama).replace("{bahasa}", BAHASA.get(bahasa, BAHASA["id"]))
    if peta:
        from flask import g
        katalog = wawasan.ringkasan_katalog(getattr(getattr(g, "user", None), "id", None))
        if katalog:
            teks += ("\n\nISI APLIKASI yang boleh diakses pengguna ini (pakai id di bawah langsung; tidak perlu "
                     "cari_dataset/cari_dashboard bila sudah cocok):\n" + katalog)
    if konteks and konteks.get("alamat"):
        alamat = str(konteks["alamat"])[:400]
        teks += (f"\n\nHALAMAN YANG SEDANG DIBUKA: {str(konteks.get('judul') or '')[:80]} ({alamat[:200]}). "
                 "Pertanyaan seperti \"ini\", \"halaman ini\", \"dashboard ini\" merujuk ke halaman tersebut.")
        rinci = wawasan.konteks_halaman(alamat, dengan_data=bool(model and model.kirim_data)) if peta else ""
        if rinci:
            teks += "\n" + rinci
        layar = str(konteks.get("teks") or "").strip()
        if layar and model is not None and model.kirim_data:
            # Halaman dashboard/chart sudah dijelaskan lengkap di atas; teks layar cukup sedikit.
            teks += ("\nTeks yang tampil di layar pengguna (potongan):\n\"\"\"\n"
                     + layar[:800 if rinci else 2000] + "\n\"\"\"")
    return teks + "\n" + peran.sistem

SISTEM = """Anda adalah asisten AI dengan peran "{peran}" untuk pengguna di {perusahaan},
di aplikasi {aplikasi} (Apache Superset). Selalu jawab dalam {bahasa} yang ringkas dan jelas.

Aturan umum:
- Jawab hanya dari hasil alat & pengetahuan umum; jangan mengarang angka, nama tabel, atau pengaturan.
- Data yang tampil sudah dibatasi sesuai hak akses pengguna; jangan menjanjikan data di luar itu.
- Bila hasil alat berisi "data_tidak_dikirim", angka sudah tampil di layar pengguna:
  jelaskan apa yang ditampilkan tanpa menyebut angka spesifik.
- Jangan pernah meminta atau menampilkan password, API key, atau isi berkas .env."""

_ARR_STR = {"type": "array", "items": {"type": "string"}}
_FILTER = {"type": "array", "items": {"type": "object", "properties": {
    "kolom": {"type": "string"}, "op": {"type": "string", "enum": list(alat.OPERATOR)},
    "nilai": {}}, "required": ["kolom", "op", "nilai"]}}


def _semua_jenis() -> list[str]:
    """Jenis chart untuk alat buat_chart: 5 jenis dasar + semua jenis Studio Visual (treemap, sankey, peta, ...)."""
    from sps_studio.aturan import ATURAN_TANDA
    return list(dict.fromkeys([*alat.JENIS_CHART, *(k for k, a in ATURAN_TANDA.items() if not a.get("waktu"))]))


def _fungsi(nama: str, ket: str, props: dict, wajib: list[str]) -> dict:
    return {"type": "function", "function": {"name": nama, "description": ket, "parameters": {
        "type": "object", "properties": props, "required": wajib}}}


ALAT = [
    _fungsi("cari_dataset", "Cari dataset yang boleh diakses pengguna.",
            {"kata_kunci": {"type": "string"}}, []),
    _fungsi("info_dataset", "Lihat kolom & metrik tersimpan sebuah dataset.",
            {"dataset_id": {"type": "integer"}}, ["dataset_id"]),
    _fungsi("ambil_data", "Ambil data teragregasi. metrik: nama metrik tersimpan atau AGREGAT(kolom).",
            {"dataset_id": {"type": "integer"}, "metrik": _ARR_STR, "kelompok": _ARR_STR,
             "filter": _FILTER, "urut_turun": {"type": "boolean"}, "batas": {"type": "integer"}},
            ["dataset_id", "metrik"]),
    _fungsi("saran_otomatis", "Analisis otomatis dataset: saran chart terbaik + wawasan (tren, konsentrasi, korelasi, segmen).",
            {"dataset_id": {"type": "integer"}, "fokus": {"type": "string"}, "jumlah": {"type": "integer"}},
            ["dataset_id"]),
    _fungsi("buat_chart", "Buat chart. jenis: angka|tabel|pie|batang|garis atau jenis Studio lain (treemap, sankey, peta_panas, tabel_pivot, sebar, radar, peta_wilayah, ...). kelompok = dimensi berurutan; metrik = AGREGAT(kolom).",
            {"dataset_id": {"type": "integer"}, "jenis": {"type": "string", "enum": _semua_jenis()},
             "judul": {"type": "string"}, "metrik": _ARR_STR, "kelompok": _ARR_STR, "filter": _FILTER},
            ["dataset_id", "jenis", "judul", "metrik"]),
    _fungsi("buat_dashboard", "Susun chart (id dari buat_chart yang tersimpan) menjadi dashboard baru.",
            {"judul": {"type": "string"}, "chart_ids": {"type": "array", "items": {"type": "integer"}}},
            ["judul", "chart_ids"]),
    _fungsi("cari_dashboard", "Cari dashboard yang boleh dibuka pengguna.",
            {"kata_kunci": {"type": "string"}}, []),
    _fungsi("info_dashboard", "Isi sebuah dashboard: daftar chart (id, jenis, dataset, metrik, pengelompokan, filter).",
            {"dashboard_id": {"type": "integer"}}, ["dashboard_id"]),
    _fungsi("info_chart", "Rincian sebuah chart: jenis, dataset, metrik, pengelompokan, filter, dashboard tempatnya.",
            {"chart_id": {"type": "integer"}}, ["chart_id"]),
    _fungsi("data_chart", "Ambil angka yang ditampilkan sebuah chart (query chart dijalankan ulang dengan hak akses pengguna).",
            {"chart_id": {"type": "integer"}, "batas": {"type": "integer"}}, ["chart_id"]),
]

LABEL_ALAT = {"cari_dataset": "Mencari dataset", "info_dataset": "Membaca struktur dataset",
              "ambil_data": "Mengambil data", "saran_otomatis": "Menganalisis dataset otomatis",
              "buat_chart": "Membuat chart", "buat_dashboard": "Menyusun dashboard",
              "cari_dashboard": "Mencari dashboard", "cari_panduan": "Membaca panduan",
              "info_dashboard": "Membaca isi dashboard", "info_chart": "Membaca chart", "data_chart": "Mengambil angka chart",
              "daftar_koneksi": "Membaca daftar koneksi", "daftar_ekstrak": "Membaca daftar ekstrak",
              "batas_data": "Membaca batas data", "lihat_tema": "Membaca tema", "cek_kontras": "Menghitung kontras warna",
              "usul_tema": "Menyusun usulan tema", "status_server": "Membaca status server",
              "lihat_pengaturan": "Membaca pengaturan server", "usul_pengaturan": "Menyusun usulan pengaturan"}

# --- Audit ------------------------------------------------------------------------------
_metadata = MetaData()
AI_LOG = Table(
    "sps_ai_log", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("waktu", DateTime), Column("username", String(64)), Column("model", String(64)),
    Column("pertanyaan", Text), Column("alat", Text), Column("status", String(20)),
    Column("durasi_ms", Integer),
)


def _catat(username: str, model_id: str, pertanyaan: str, dipakai: list[str], status: str, mulai: float) -> None:
    from superset import db
    try:
        AI_LOG.create(bind=db.engine, checkfirst=True)
        db.session.execute(AI_LOG.insert().values(
            waktu=datetime.now(), username=username, model=model_id, pertanyaan=pertanyaan[:4000],
            alat=json.dumps(dipakai), status=status, durasi_ms=int((time.time() - mulai) * 1000)))
        db.session.commit()
    except Exception:  # noqa: BLE001 - audit gagal tidak boleh menggagalkan jawaban
        log.exception("ALDx AI: gagal mencatat audit")
        db.session.rollback()


# --- Menjalankan alat ------------------------------------------------------------------
def _jalankan_alat(nama: str, arg: dict, model: ModelAI, atur: Pengaturan, ev: Callable[[dict], None],
                  bahasa: str = "id") -> Any:
    if nama in P.ALAT_AHLI:
        return P.jalankan(nama, arg, ev, bahasa)
    if nama == "cari_dataset":
        return alat.daftar_dataset(arg.get("kata_kunci", ""))
    if nama == "info_dataset":
        return alat.info_dataset(arg["dataset_id"])
    if nama == "cari_dashboard":
        return alat.daftar_dashboard(arg.get("kata_kunci", ""))
    if nama == "info_dashboard":
        return wawasan.info_dashboard(arg["dashboard_id"])
    if nama == "info_chart":
        return wawasan.info_chart(arg["chart_id"])
    if nama == "data_chart":
        h = wawasan.data_chart(arg["chart_id"], min(int(arg.get("batas") or 200), atur.baris_maks))
        ev({"tipe": "tabel", "judul": h["chart"], "kolom": h["kolom"], "baris": h["baris"]})
        if model.kirim_data:
            return {"chart": h["chart"], "kolom": h["kolom"], "jumlah_baris": len(h["baris"]),
                    "baris": h["baris"][:atur.baris_ke_model]}
        return {"chart": h["chart"], "kolom": h["kolom"], "jumlah_baris": len(h["baris"]), "data_tidak_dikirim": True}
    if nama == "ambil_data":
        batas = min(int(arg.get("batas") or 100), atur.baris_maks)
        h = alat.jalankan_query(arg["dataset_id"], arg.get("metrik"), arg.get("kelompok"),
                                arg.get("filter"), bool(arg.get("urut_turun", True)), batas)
        ev({"tipe": "tabel", "judul": h["dataset"], "kolom": h["kolom"], "baris": h["baris"]})
        if model.kirim_data:
            return {"kolom": h["kolom"], "jumlah_baris": len(h["baris"]),
                    "baris": h["baris"][:atur.baris_ke_model]}
        return {"kolom": h["kolom"], "jumlah_baris": len(h["baris"]), "data_tidak_dikirim": True}
    if nama == "saran_otomatis":
        h = auto.sarankan(arg["dataset_id"], arg.get("fokus", ""), None, int(arg.get("jumlah") or 6))
        ev({"tipe": "saran", "dataset_id": arg["dataset_id"], **h})
        if model.kirim_data:
            return h
        return {"saran": [{k: s[k] for k in ("judul", "jenis", "metrik", "kelompok")} for s in h["saran"]],
                "profil": h.get("profil"), "data_tidak_dikirim": True}
    if nama == "buat_chart":
        if arg["jenis"] in alat.JENIS_CHART or arg.get("filter"):
            h = alat.buat_chart(arg["dataset_id"], arg["jenis"], arg.get("judul", ""), arg["metrik"],
                                arg.get("kelompok"), arg.get("filter"))
        else:                       # jenis lain (treemap, sankey, peta, ...): pembangun Studio Visual
            h = auto.buat_satu(arg["dataset_id"], arg)
        ev({"tipe": "chart", **h})
        return h
    if nama == "buat_dashboard":
        h = alat.buat_dashboard(arg["judul"], arg["chart_ids"])
        ev({"tipe": "dashboard", **h})
        return h
    raise alat.InputSalah(f"Alat '{nama}' tidak dikenal.")


def _argumen(panggilan: dict) -> dict:
    a = panggilan.get("function", {}).get("arguments") or "{}"
    return a if isinstance(a, dict) else json.loads(a)


def _riwayat_bersih(riwayat: list[dict]) -> list[dict]:
    hasil = []
    for p in riwayat[-20:]:
        if p.get("role") in ("user", "assistant") and isinstance(p.get("content"), str):
            hasil.append({"role": p["role"], "content": p["content"][:4000]})
    return hasil


def alat_peran(peran: P.Peran) -> list[dict]:
    """Definisi alat (format OpenAI) untuk satu peran."""
    analis = {a["function"]["name"]: a for a in ALAT}
    return [analis.get(n) or P.ALAT_AHLI[n] for n in peran.alat]


def jawab(riwayat: list[dict], model: ModelAI, atur: Pengaturan, username: str, peran: P.Peran | None = None,
          konteks: dict | None = None, bahasa: str = "id") -> dict:
    """Jalankan agent untuk percakapan `riwayat`. Kembalikan jawaban + peristiwa untuk layar."""
    from superset import db
    from superset.exceptions import SupersetSecurityException

    peran = peran or P.PETA_PERAN["analis"]
    daftar_alat = alat_peran(peran)
    mulai, peristiwa, dipakai = time.time(), [], []
    peta = any(n in peran.alat for n in ("cari_dataset", "cari_dashboard", "info_dashboard"))
    pesan = [{"role": "system", "content": _sistem(peran, konteks, bahasa, model, peta)}] + _riwayat_bersih(riwayat)
    pertanyaan = next((p["content"] for p in reversed(pesan) if p["role"] == "user"), "")
    jawaban, status = "", "ok"
    try:
        for langkah in range(atur.langkah_maks + 1):
            boleh_alat = langkah < atur.langkah_maks
            msg = llm.chat(model, pesan, daftar_alat if boleh_alat else [], atur.batas_untuk(model))
            panggilan = (msg.get("tool_calls") or []) if boleh_alat else []
            if not panggilan:
                jawaban = msg.get("content") or ""
                break
            pesan.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": panggilan})
            for p in panggilan:
                nama = p.get("function", {}).get("name", "")
                dipakai.append(nama)
                peristiwa.append({"tipe": "langkah", "teks": LABEL_ALAT.get(nama, nama)})
                try:
                    if nama not in peran.alat:
                        raise alat.IzinDitolak(f"Alat '{nama}' bukan milik peran {peran.perintah}.")
                    hasil = _jalankan_alat(nama, _argumen(p), model, atur, peristiwa.append, bahasa)
                except (alat.IzinDitolak, alat.InputSalah, SupersetSecurityException, KeyError, ValueError,
                        LookupError) as exc:
                    db.session.rollback()
                    hasil = {"error": str(exc)}
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    log.exception("ALDx AI: alat %s gagal", nama)
                    hasil = {"error": f"Alat gagal: {exc}"}
                pesan.append({"role": "tool", "tool_call_id": p.get("id") or nama, "name": nama,
                              "content": json.dumps(hasil, ensure_ascii=False, default=str)[:12000]})
    except llm.GagalModel as exc:
        status, jawaban = "gagal_model", str(exc)
    _catat(username, model.id, f"[{peran.perintah}] {pertanyaan}", dipakai, status, mulai)
    log.info("ALDx AI %s peran=%s model=%s alat=%s status=%s", username, peran.id, model.id, dipakai, status)
    return {"jawaban": jawaban, "peristiwa": peristiwa, "status": status, "peran": peran.id}


def tulis_narasi(model: ModelAI, atur: Pengaturan, judul_story: str, dashboard: dict) -> str:
    """Narasi singkat untuk satu langkah story (hanya dari judul dashboard & chart, tanpa angka)."""
    perintah = (f"Tulis narasi 2-3 kalimat Bahasa Indonesia untuk satu langkah presentasi berjudul "
                f"'{judul_story}'. Dashboard: '{dashboard['judul']}'. Isi chart: {', '.join(dashboard['chart'])}. "
                "Jelaskan apa yang perlu diperhatikan audiens. Jangan menyebut angka.")
    msg = llm.chat(model, [{"role": "system", "content": _sistem()}, {"role": "user", "content": perintah}],
                   [], atur.batas_untuk(model))
    return (msg.get("content") or "").strip()
