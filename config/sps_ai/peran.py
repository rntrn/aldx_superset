"""Peran ahli untuk Asisten AI (panel AI di setiap halaman, perintah garis miring).

    /analis          Analis data       tanya data, buat chart & dashboard        semua pengguna Asisten AI
    /panduan         Pemandu aplikasi  cara memakai menu & fitur                 semua pengguna Asisten AI
    /data-engineer   Data engineer     dataset, koneksi, ekstrak, SQL, kualitas  Analis (SQL Lab) atau Admin
    /ahli-ui-ux      Ahli UI/UX        warna, huruf, tema, aksesibilitas         Admin
    /hw-engineer     HW engineer       CPU/RAM, proses, cache, batas, timeout    Superadmin

PRINSIP KEAMANAN:
    - Setiap alat berjalan sebagai pengguna yang login (hak akses & RLS tetap berlaku).
    - Peran yang mengubah pengaturan HANYA membuat USULAN (peristiwa "usulan"). Perubahan baru terjadi
      setelah manusia menekan "Terapkan", lewat API biasa yang memeriksa hak aksesnya sendiri.
    - Alat ahli (tema, server, batas) hanya membaca konfigurasi, bukan data bisnis/pribadi.

Menambah peran: tambah satu Peran(...) di PERAN, tulis alatnya di ALAT_AHLI + JALANKAN.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from sps_ai import alat

FOLDER_BANTUAN = Path(__file__).resolve().parent.parent / "sps_app" / "static" / "bantuan"


@dataclass(frozen=True)
class Peran:
    id: str
    nama: str
    ikon: str
    ringkas: str
    syarat: str                         # ai | sql | admin | superadmin
    alat: tuple[str, ...]
    sistem: str
    contoh: tuple[str, ...] = field(default_factory=tuple)

    @property
    def perintah(self) -> str:
        return "/" + self.id

    @property
    def publik(self) -> dict:
        return {"id": self.id, "perintah": self.perintah, "nama": self.nama, "ikon": self.ikon,
                "ringkas": self.ringkas, "contoh": list(self.contoh)}


ALAT_ANALIS = ("cari_dataset", "info_dataset", "ambil_data", "saran_otomatis", "buat_chart",
               "buat_dashboard", "cari_dashboard", "info_dashboard", "info_chart", "data_chart", "gabung_dataset",
               "cari_tabel", "daftarkan_tabel")

PERAN: tuple[Peran, ...] = (
    Peran("analis", "Analis data", "chart", "Tanya data, buat chart & dashboard otomatis", "ai", ALAT_ANALIS, """
Peran: ANALIS DATA.
- JANGAN mengarang angka. Semua angka harus berasal dari alat ambil_data.
- Daftar ISI APLIKASI (dataset, dashboard, chart beserta id) sudah ada di instruksi; pakai id-nya langsung.
  Bila belum ada yang cocok, panggil cari_dataset lalu info_dataset.
- Bila pengguna menyebut "dashboard ini", "chart ini", "halaman ini", pakai HALAMAN YANG SEDANG DIBUKA.
  Untuk menganalisis angka di dashboard/chart, panggil data_chart per chart (bukan menebak dari judul).
- Utamakan metrik tersimpan dataset; bila tidak ada, pakai AGREGAT(kolom), mis. SUM(total).
- Untuk permintaan grafik/visual, panggil buat_chart. Untuk "dashboard", buat beberapa chart
  lalu buat_dashboard dengan id chart yang sudah tersimpan.
- Untuk "analisis otomatis"/"apa yang menarik", panggil saran_otomatis.
- Tabel database yang belum jadi dataset: cari_tabel (pola nama) lalu daftarkan_tabel; gabungan beberapa dataset: gabung_dataset.
- Selalu sebut nama chart/dataset/dashboard yang dibuat; tautannya otomatis tampil di bawah jawaban.
- Akhiri dengan saran langkah analisis berikutnya bila relevan (satu kalimat).""",
          ("Penjualan per cabang tahun ini?", "Buatkan grafik batang penjualan per cabang", "Apa yang menarik dari dataset ini?")),
    Peran("panduan", "Pemandu aplikasi", "bantuan", "Cara memakai menu & fitur aplikasi ini", "ai", ("cari_panduan",), """
Peran: PEMANDU APLIKASI. Jelaskan cara memakai aplikasi langkah demi langkah, ringkas.
- Selalu panggil cari_panduan dulu; jawab HANYA berdasarkan isi panduan itu. Bila tidak ada, katakan terus terang
  dan sarankan menekan tombol ? (Cara pakai) atau menghubungi admin.
- Sebutkan nama menu persis seperti di layar dan pintasan keyboard bila ada.""",
          ("Bagaimana membuat dashboard dari nol?", "Apa pintasan keyboard di SQL Lab?", "Bedanya ekstrak penuh dan inkremental?")),
    Peran("data-engineer", "Data engineer", "tabel", "Dataset, koneksi, ekstrak, SQL & kualitas data", "sql",
          ("cari_dataset", "info_dataset", "ambil_data", "daftar_koneksi", "daftar_ekstrak", "batas_data", "gabung_dataset",
           "cari_tabel", "daftarkan_tabel"), """
Peran: DATA ENGINEER senior (pemodelan data, ETL, performa kueri, SQL lintas dialek).
- Periksa struktur nyata lewat alat (info_dataset, daftar_koneksi, daftar_ekstrak) sebelum menyarankan.
- Saran ekstrak: pakai mode inkremental bila ada kolom tanggal/ID yang selalu naik; kolom hak akses (RLS)
  wajib ikut disalin; perhatikan batas data (batas_data).
- Saat menulis SQL, sesuaikan dialek database (lihat daftar_koneksi: postgresql, mysql, oracle, mssql,
  clickhouse, ...), tulis di blok ```sql, hanya SELECT (koneksi ALDx selalu baca-saja).
- Untuk cek kualitas data (kosong, duplikat, rentang), boleh pakai ambil_data dengan COUNT/MIN/MAX.
- Tabel yang belum jadi dataset (mis. "semua tabel berawalan data_penerbangan di sps_engine"): cari_tabel, lalu
  daftarkan_tabel bila pengguna ingin menganalisisnya.
- Dataset gabungan/denormal dari beberapa dataset: pakai gabung_dataset (kunci & hak akses otomatis); jelaskan
  dataset yang dilewati karena banyak-ke-banyak dan sarankan dataset terpisah untuknya.
- Anda tidak bisa menjalankan DDL/DML; arahkan pengguna ke menu yang tepat (Kueri Visual, SQL Lab, Ekstrak).""",
          ("Dataset mana yang cocok dijadikan ekstrak?", "Tuliskan SQL total penjualan per bulan", "Cek kualitas kolom di dataset latihan_penjualan")),
    Peran("ahli-ui-ux", "Ahli UI/UX", "studio", "Warna, huruf & tema yang elegan dan mudah dibaca", "admin",
          ("lihat_tema", "cek_kontras", "usul_tema"), """
Peran: AHLI UI/UX & desain visual untuk aplikasi BI perkantoran.
- Baca tema sekarang (lihat_tema) sebelum memberi saran.
- Pegang prinsip: kontras teks minimal 4,5:1 (WCAG AA; cek dengan cek_kontras), satu warna aksen,
  latar netral terang, konsisten dengan identitas instansi, hindari warna terlalu jenuh.
- Untuk perubahan, panggil usul_tema dengan isian yang diubah saja + alasan singkat. Perubahan BARU berlaku
  setelah pengguna menekan "Terapkan"; jangan katakan sudah diterapkan.
- Logo/ikon tidak bisa diubah lewat Anda: arahkan ke Pusat Kendali › Identitas & Tema.""",
          ("Buat tema yang lebih elegan dan tenang", "Apakah warna sekarang cukup kontras?", "Usulkan tema hijau yang tetap profesional")),
    Peran("hw-engineer", "HW engineer", "server", "CPU, RAM, proses, cache, timeout & batas data", "superadmin",
          ("status_server", "lihat_pengaturan", "usul_pengaturan", "batas_data"), """
Peran: HARDWARE/INFRASTRUCTURE ENGINEER untuk server Superset (Gunicorn, Celery, Redis, PostgreSQL, ClickHouse).
- Selalu baca kondisi nyata dulu (status_server, lihat_pengaturan) sebelum menyarankan angka.
- Pedoman: proses web ≈ min(2×CPU+1, RAM web ÷ 700 MB); thread 4–8; backgrounder ≤ 2×CPU; cache Redis
  ±10% RAM; timeout chart < timeout web; naikkan cache bila chart lambat tapi data jarang berubah.
- Untuk perubahan, panggil usul_pengaturan dengan kunci yang diubah saja + alasan. Perubahan BARU berlaku
  setelah Superadmin menekan "Terapkan". Kunci bertanda "terapkan" butuh scripts\\terapkan-server.ps1 (restart).
- Jelaskan dampak (kecepatan vs memori) dalam kalimat sederhana.""",
          ("Server terasa lambat, apa yang perlu diubah?", "Berapa proses web yang ideal untuk server ini?", "Cek batas data upload & ekstrak")),
)
PETA_PERAN = {p.id: p for p in PERAN}


# --- Hak akses peran ------------------------------------------------------------------------
def boleh(p: Peran) -> bool:
    from superset import security_manager as sm
    import sps_superadmin
    if p.syarat == "superadmin":
        return sps_superadmin.adalah()
    if p.syarat == "admin":
        return sm.is_admin()
    if p.syarat == "sql":
        return sm.is_admin() or sm.can_access("menu_access", "SQL Lab") or sm.can_access("can_sqllab", "Superset")
    return True


def tersedia() -> list[Peran]:
    return [p for p in PERAN if boleh(p)]


def ambil(peran_id: str | None) -> Peran:
    p = PETA_PERAN.get((peran_id or "analis").lstrip("/"))
    if p is None:
        raise alat.InputSalah(f"Peran '{peran_id}' tidak dikenal. Pilihan: " + ", ".join(x.perintah for x in PERAN))
    if not boleh(p):
        raise alat.IzinDitolak(f"Peran {p.perintah} tidak tersedia untuk akun Anda.")
    return p


# --- Definisi alat ahli (format OpenAI function calling) --------------------------------------------
def _f(nama: str, ket: str, props: dict, wajib: list[str]) -> dict:
    return {"type": "function", "function": {"name": nama, "description": ket,
                                             "parameters": {"type": "object", "properties": props, "required": wajib}}}


ALAT_AHLI = {
    "cari_panduan": _f("cari_panduan", "Cari isi panduan cara pakai aplikasi (menu, langkah, tips, pintasan).",
                       {"kata_kunci": {"type": "string"}}, ["kata_kunci"]),
    "daftar_koneksi": _f("daftar_koneksi", "Daftar koneksi database yang boleh diakses (nama, dialek). Tanpa alamat/password.", {}, []),
    "daftar_ekstrak": _f("daftar_ekstrak", "Daftar ekstrak ALDx Engine: mode, status, baris, ukuran, jadwal (khusus Admin).", {}, []),
    "batas_data": _f("batas_data", "Batas ukuran/baris data yang berlaku (upload, impor berkas, ekstrak, kuota engine).", {}, []),
    "lihat_tema": _f("lihat_tema", "Identitas & tema saat ini, isian yang bisa diubah, dan daftar preset.", {}, []),
    "cek_kontras": _f("cek_kontras", "Hitung rasio kontras WCAG dua warna hex (#RRGGBB).",
                      {"warna_depan": {"type": "string"}, "warna_latar": {"type": "string"}}, ["warna_depan", "warna_latar"]),
    "usul_tema": _f("usul_tema", "Usulkan perubahan tema (belum diterapkan). perubahan = {isian: nilai}.",
                    {"perubahan": {"type": "object"}, "alasan": {"type": "string"}}, ["perubahan", "alasan"]),
    "status_server": _f("status_server", "Kondisi server: node, CPU, RAM, proses, cache, antrean, chart lambat.", {}, []),
    "lihat_pengaturan": _f("lihat_pengaturan", "Pengaturan server (nilai, bawaan, batas, satuan). grup opsional.",
                           {"grup": {"type": "string"}}, []),
    "usul_pengaturan": _f("usul_pengaturan", "Usulkan perubahan pengaturan server (belum diterapkan). perubahan = {kunci: nilai}.",
                          {"perubahan": {"type": "object"}, "alasan": {"type": "string"}}, ["perubahan", "alasan"]),
}


# --- Pelaksana alat ahli ------------------------------------------------------------------------------
def _cari_panduan(arg: dict, bahasa: str) -> dict:
    berkas = FOLDER_BANTUAN / f"{bahasa}.json"
    data = json.loads((berkas if berkas.exists() else FOLDER_BANTUAN / "id.json").read_text(encoding="utf-8"))
    kata = [k for k in str(arg.get("kata_kunci", "")).lower().split() if len(k) > 2]

    def skor(topik: dict) -> int:
        teks = json.dumps(topik, ensure_ascii=False).lower()
        return sum(teks.count(k) for k in kata)
    urut = sorted(data.items(), key=lambda kv: -skor(kv[1]))
    pilih = [v for _, v in urut[:4] if skor(v) > 0] or [data.get("umum", {})]
    return {"topik": pilih, "semua_judul": [v.get("judul") for v in data.values()]}


def _daftar_koneksi() -> list[dict]:
    from superset import db, security_manager as sm
    from superset.models.core import Database
    return [{"id": d.id, "nama": d.database_name, "dialek": d.backend, "baca_saja": not d.allow_dml}
            for d in db.session.query(Database).order_by(Database.database_name) if sm.can_access_database(d)]


def _daftar_ekstrak() -> list[dict]:
    from superset import security_manager as sm
    if not sm.is_admin():
        raise alat.IzinDitolak("Daftar ekstrak khusus Admin.")
    from sps_engine import ekstrak
    kunci = ("nama", "mode", "kolom_inkremental", "status", "baris_total", "ukuran_byte", "durasi_detik", "selesai", "pesan")
    return [{k: e.get(k) for k in kunci} | {"jadwal": json.loads(e.get("jadwal") or "{}")} for e in ekstrak.daftar()]


def _batas_data() -> list[dict]:
    from sps_server import batas, penyimpanan, skema
    atur = penyimpanan.nilai_semua()
    return [{"kunci": k, "label": skema.PETA[k].label, "pengaturan": atur[k], "berlaku": batas.berlaku(atur, k) or "tanpa batas",
             "satuan": skema.PETA[k].satuan} for k in batas.KUNCI]


def _lihat_tema() -> dict:
    from flask import current_app
    from sps_identitas import skema
    n = current_app.config.get("SPS_IDENTITAS") or skema.bawaan()
    isian = [{**i.publik, "nilai": n.get(i.kunci)} for i in skema.ISIAN if i.jenis != "berkas"]
    return {"isian": isian, "preset": {k: {kk: vv for kk, vv in v.items() if kk.startswith("warna") or kk in ("label", "hiasan")}
                                       for k, v in skema.PRESET.items()}}


def _luminans(hexa: str) -> float:
    from sps_identitas import skema
    if not skema.WARNA.match(hexa or ""):
        raise alat.InputSalah(f"Warna '{hexa}' tidak sah; tulis seperti #1E2A44.")
    kanal = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in kanal]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontras(depan: str, latar: str) -> dict:
    a, b = sorted((_luminans(depan), _luminans(latar)), reverse=True)
    rasio = round((a + 0.05) / (b + 0.05), 2)
    return {"warna_depan": depan, "warna_latar": latar, "rasio": rasio,
            "AA_teks_normal": rasio >= 4.5, "AA_teks_besar": rasio >= 3, "AA_non_teks": rasio >= 3, "AAA": rasio >= 7}


def _usul_tema(arg: dict) -> dict:
    from flask import current_app
    from sps_identitas import skema
    n = current_app.config.get("SPS_IDENTITAS") or skema.bawaan()
    perubahan, rincian, galat = {}, [], []
    for k, v in (arg.get("perubahan") or {}).items():
        try:
            if k in skema.BERKAS:
                raise ValueError(f"{skema.PETA[k].label}: logo/ikon diunggah di Pusat Kendali › Identitas & Tema")
            bersih = skema.periksa(k, v)
        except ValueError as exc:
            galat.append(str(exc))
            continue
        if bersih != n.get(k):
            perubahan[k] = bersih
            rincian.append({"kunci": k, "label": skema.PETA[k].label, "lama": n.get(k), "baru": bersih})
    baru = {**n, **perubahan}
    cek = [{"pasangan": "Teks putih di warna utama", **kontras("#FFFFFF", baru["warna_utama"])},
           {"pasangan": "Teks gelap di latar", **kontras("#0F172A", baru["warna_latar"])},
           {"pasangan": "Warna aksen di latar (elemen, bukan teks)", "non_teks": True,
            **kontras(baru["warna_aksen"], baru["warna_latar"])}]
    return {"jenis": "tema", "perubahan": perubahan, "rincian": rincian, "galat": galat, "kontras": cek,
            "alasan": str(arg.get("alasan", ""))[:600], "api": "/identitas/api"}


def _status_server() -> dict:
    from sps_server import monitor, penyimpanan, tuning
    s = monitor.status()
    node = s["node"] if isinstance(s["node"], list) else []
    atur = penyimpanan.nilai_semua()
    host = tuning.perangkat_host()
    return {"host": {"cpu": host.cpu, "ram_mb": host.ram_mb},
            "node": [{k: n.get(k) for k in ("nama", "layanan", "online", "cpu", "ram_mb", "cpu_persen", "ram_terpakai_mb", "proses")}
                     for n in node],
            "redis": s["redis"], "aktivitas": s["aktivitas"], "sqllab": s["sqllab"],
            "rekomendasi_auto_tuning": monitor.rekomendasi(node, atur)}


def _lihat_pengaturan(arg: dict) -> list[dict]:
    from sps_server import penyimpanan, skema
    atur, grup = penyimpanan.nilai_semua(), arg.get("grup")
    return [{"kunci": a.kunci, "grup": a.grup, "label": a.label, "nilai": atur[a.kunci], "bawaan": a.bawaan, "min": a.min,
             "maks": a.maks, "satuan": a.satuan, "berlaku": a.berlaku, "bantuan": a.bantuan}
            for a in skema.DAFTAR if not grup or a.grup == grup]


def _usul_pengaturan(arg: dict) -> dict:
    from sps_server import penyimpanan, skema
    atur = penyimpanan.nilai_semua()
    perubahan, rincian, galat = {}, [], []
    for k, v in (arg.get("perubahan") or {}).items():
        if k not in skema.PETA:
            galat.append(f"Pengaturan '{k}' tidak dikenal")
            continue
        try:
            bersih = skema.PETA[k].normalkan(v)
        except ValueError as exc:
            galat.append(str(exc))
            continue
        if bersih != atur[k]:
            a = skema.PETA[k]
            perubahan[k] = bersih
            rincian.append({"kunci": k, "label": a.label, "lama": atur[k], "baru": bersih, "satuan": a.satuan,
                            "berlaku": a.berlaku})
    galat += skema.periksa_silang({**atur, **perubahan})
    return {"jenis": "pengaturan", "perubahan": perubahan, "rincian": rincian, "galat": galat,
            "alasan": str(arg.get("alasan", ""))[:600], "api": "/pusat-kendali/api/pengaturan"}


def jalankan(nama: str, arg: dict, ev: Callable[[dict], None], bahasa: str = "id") -> Any:
    """Jalankan alat ahli. Usulan dikirim ke layar sebagai peristiwa 'usulan'."""
    if nama == "cari_panduan":
        return _cari_panduan(arg, bahasa)
    if nama == "daftar_koneksi":
        return _daftar_koneksi()
    if nama == "daftar_ekstrak":
        return _daftar_ekstrak()
    if nama == "batas_data":
        return _batas_data()
    if nama == "lihat_tema":
        return _lihat_tema()
    if nama == "cek_kontras":
        return kontras(str(arg.get("warna_depan", "")).strip(), str(arg.get("warna_latar", "")).strip())
    import sps_superadmin
    from superset import security_manager as sm
    if nama in ("usul_tema", "usul_pengaturan"):
        if nama == "usul_tema" and not sm.is_admin():
            raise alat.IzinDitolak("Usulan tema khusus Admin.")
        if nama == "usul_pengaturan" and not sps_superadmin.adalah():
            raise alat.IzinDitolak("Usulan pengaturan server khusus Superadmin.")
        h = _usul_tema(arg) if nama == "usul_tema" else _usul_pengaturan(arg)
        if h["rincian"]:
            ev({"tipe": "usulan", **h})
        return {k: h[k] for k in ("rincian", "galat")} | {"catatan": "Usulan tampil di layar; menunggu pengguna menekan Terapkan."}
    if nama == "status_server":
        if not sps_superadmin.adalah():
            raise alat.IzinDitolak("Status server lengkap khusus Superadmin.")
        return _status_server()
    if nama == "lihat_pengaturan":
        if not sps_superadmin.adalah():
            raise alat.IzinDitolak("Pengaturan server khusus Superadmin.")
        return _lihat_pengaturan(arg)
    raise alat.InputSalah(f"Alat '{nama}' tidak dikenal.")
