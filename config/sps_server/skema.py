"""Daftar semua pengaturan server (satu tempat untuk semua konfigurasi server).

Setiap pengaturan punya:
    kunci     id unik, mis. "web.worker"
    grup      kelompok di halaman Pusat Kendali
    tipe      angka | auto (angka atau "auto") | ya_tidak | pilihan (daftar)
    berlaku   "langsung" = aktif tanpa restart (dibaca ulang tiap ~10 detik)
              "terapkan" = perlu scripts\\terapkan-server.ps1 (restart container)
    istilah   nama lain / istilah teknis (opsional), tampil kecil di bawah label

Menambah pengaturan baru: tambah satu Atur(...) di DAFTAR, lalu pakai nilainya
di konfig.py (untuk config Superset) atau tuning.py (untuk jumlah proses).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

AUTO = "auto"
LANGSUNG = "langsung"
TERAPKAN = "terapkan"


@dataclass(frozen=True)
class Atur:
    kunci: str
    grup: str
    label: str
    tipe: str
    bawaan: Any
    berlaku: str
    istilah: str = ""
    bantuan: str = ""
    min: float | None = None
    maks: float | None = None
    satuan: str = ""
    opsi: list[str] = field(default_factory=list)

    def normalkan(self, nilai: Any) -> Any:
        """Ubah input (dari form/JSON) ke tipe yang benar; ValueError bila tidak sah."""
        if self.tipe == "ya_tidak":
            if isinstance(nilai, str):
                return nilai.strip().lower() in ("1", "true", "ya", "on")
            return bool(nilai)
        if self.tipe == "pilihan":
            daftar = nilai if isinstance(nilai, list) else [s.strip() for s in str(nilai).split(",")]
            daftar = [str(s).strip() for s in daftar if str(s).strip()]
            salah = [s for s in daftar if self.opsi and s not in self.opsi]
            if salah:
                raise ValueError(f"{self.label}: pilihan tidak dikenal {salah}")
            return daftar
        if self.tipe == AUTO and str(nilai).strip().lower() == AUTO:
            return AUTO
        try:
            angka = int(float(str(nilai).strip()))
        except ValueError as exc:
            raise ValueError(f"{self.label}: harus angka{' atau auto' if self.tipe == AUTO else ''}") from exc
        if self.min is not None and angka < self.min:
            raise ValueError(f"{self.label}: minimal {int(self.min)} {self.satuan}".strip())
        if self.maks is not None and angka > self.maks:
            raise ValueError(f"{self.label}: maksimal {int(self.maks)} {self.satuan}".strip())
        return angka

    @property
    def publik(self) -> dict:
        return {k: getattr(self, k) for k in ("kunci", "grup", "label", "tipe", "bawaan", "berlaku",
                                               "istilah", "bantuan", "min", "maks", "satuan", "opsi")}


GRUP = {
    "proses": "Proses (topologi)",
    "sumber": "Jatah CPU & RAM per container",
    "cache": "Cache server",
    "batas": "Batas baris",
    "timeout": "Timeout & sesi",
    "data": "Batas data: upload, impor berkas, ekstrak",
    "gateway": "Gateway & keamanan",
    "fitur": "Fitur pemrosesan",
}

_JENIS_FILE = ["csv", "tsv", "txt", "xlsx", "xls", "parquet"]

DAFTAR: list[Atur] = [
    # --- Proses: berapa banyak "mesin" yang melayani pengguna --------------------------
    Atur("web.worker", "proses", "Proses web", AUTO, AUTO, TERAPKAN,
         "",
         "Proses Gunicorn yang melayani dashboard, chart & API. auto = dari CPU/RAM node.", 1, 32, "proses"),
    Atur("web.thread", "proses", "Thread per proses web", AUTO, AUTO, TERAPKAN,
         "",
         "Permintaan paralel per proses. Banyak query lambat (Oracle) → naikkan.", 1, 64, "thread"),
    Atur("web.timeout_detik", "proses", "Timeout permintaan web", "angka", 330, TERAPKAN,
         "",
         "Permintaan lebih lama dari ini diputus gateway. Harus > timeout chart & SQL Lab.",
         30, 3600, "detik"),
    Atur("web.daur_ulang", "proses", "Daur ulang proses web setiap", "angka", 1000, TERAPKAN,
         "",
         "Proses dimulai ulang setelah sekian permintaan agar memori tetap bersih. 0 = tidak.",
         0, 100000, "permintaan"),
    Atur("antrean.sqllab", "proses", "Backgrounder: SQL Lab", AUTO, AUTO, TERAPKAN,
         "",
         "Proses untuk query SQL Lab berjalan di latar (fitur SQL Lab async).", 0, 32, "proses"),
    Atur("antrean.grafik", "proses", "Backgrounder: chart async", AUTO, AUTO, TERAPKAN,
         "",
         "Proses untuk memuat chart di latar (fitur chart async).", 0, 32, "proses"),
    Atur("antrean.cache", "proses", "Backgrounder: pemanasan cache", "angka", 1, TERAPKAN,
         "", "", 0, 8, "proses"),
    Atur("antrean.ekstrak", "proses", "Backgrounder: penyegaran ekstrak", "angka", 1, TERAPKAN,
         "",
         "Penyegaran ekstrak ALDx Engine yang berjalan bersamaan.", 0, 8, "proses"),
    Atur("antrean.laporan", "proses", "Backgrounder: laporan & alert", "angka", 1, TERAPKAN,
         "",
         "Laporan/alert email terjadwal (butuh pengaturan SMTP).", 0, 8, "proses"),

    # --- Sumber daya per container (diterapkan lewat docker-compose) --------------------
    Atur("sumber.cadangan_persen", "sumber", "Cadangan RAM untuk sistem", "angka", 15, TERAPKAN,
         "",
         "Bagian RAM Docker yang tidak dibagikan ke container.", 5, 50, "%"),
    Atur("sumber.web_cpu", "sumber", "CPU container web", AUTO, AUTO, TERAPKAN,
         "", "Batas inti CPU. auto = 60% CPU node.", 1, 128, "inti"),
    Atur("sumber.web_ram_mb", "sumber", "RAM container web", AUTO, AUTO, TERAPKAN,
         "", "auto = 60% RAM yang tersisa.", 512, 262144, "MB"),
    Atur("sumber.worker_cpu", "sumber", "CPU container backgrounder", AUTO, AUTO, TERAPKAN,
         "", "auto = 50% CPU node (boleh tumpang tindih dengan web).", 1, 128, "inti"),
    Atur("sumber.worker_ram_mb", "sumber", "RAM container backgrounder", AUTO, AUTO, TERAPKAN,
         "", "auto = 40% RAM yang tersisa.", 512, 262144, "MB"),
    Atur("sumber.engine_ram_mb", "sumber", "RAM ALDx Engine (ClickHouse)", AUTO, AUTO, TERAPKAN,
         "", "auto = 25% RAM (1–16 GB). Data ekstrak disimpan di disk.",
         1024, 262144, "MB"),
    Atur("sumber.metadb_ram_mb", "sumber", "RAM database katalog (PostgreSQL)", AUTO, AUTO, TERAPKAN,
         "", "auto = 512–1024 MB.", 384, 16384, "MB"),
    Atur("sumber.redis_ram_mb", "sumber", "RAM cache server (Redis)", AUTO, AUTO, TERAPKAN,
         "", "auto = 10% RAM (256–2048 MB). Penuh → data lama dibuang.",
         128, 65536, "MB"),

    # --- Cache --------------------------------------------------------------------------
    Atur("cache.data_detik", "cache", "Lama hasil query disimpan", "angka", 3600, LANGSUNG,
         "",
         "0 = selalu query ulang ke Oracle/ClickHouse. Cache dipisah per lingkup hak akses.",
         0, 604800, "detik"),
    Atur("cache.filter_detik", "cache", "Lama status filter & explore disimpan", "angka", 86400, TERAPKAN,
         "", "", 600, 2592000, "detik"),
    Atur("cache.pemanasan_aktif", "cache", "Pemanasan cache terjadwal", "ya_tidak", False, TERAPKAN,
         "",
         "Isi cache dashboard paling sering dibuka tiap pagi, agar terbuka cepat.", ),
    Atur("cache.pemanasan_jam", "cache", "Jam pemanasan cache", "angka", 6, TERAPKAN,
         "", "Jam (0–23, zona waktu server).", 0, 23, "jam"),
    Atur("cache.pemanasan_jumlah", "cache", "Jumlah dashboard dipanaskan", "angka", 10, TERAPKAN,
         "", "Dashboard teratas 7 hari terakhir.", 1, 100, "dashboard"),

    # --- Batas baris ---------------------------------------------------------------------
    Atur("batas.baris_chart", "batas", "Baris maksimal per chart", "angka", 5000, LANGSUNG,
         "", "", 100, 1000000, "baris"),
    Atur("batas.baris_sql", "batas", "Baris maksimal hasil SQL Lab", "angka", 100000, LANGSUNG,
         "", "", 100, 5000000, "baris"),
    Atur("batas.baris_tampil_sql", "batas", "Baris ditampilkan di SQL Lab", "angka", 10000, LANGSUNG,
         "", "", 100, 1000000, "baris"),
    Atur("batas.baris_chart_berat", "batas", "Baris maksimal chart berat", "angka", 1000, LANGSUNG,
         "", "Tree, Graph, Sankey, Sunburst, Treemap, Word cloud, peta titik: lebih dari ini membuat browser macet. 0 = tanpa batas.",
         0, 1000000, "baris"),
    Atur("batas.baris_sampel", "batas", "Baris contoh data (View data)", "angka", 1000, LANGSUNG,
         "", "", 10, 100000, "baris"),
    Atur("batas.baris_filter", "batas", "Nilai maksimal di daftar filter", "angka", 10000, LANGSUNG,
         "", "", 100, 1000000, "nilai"),

    # --- Timeout & sesi -------------------------------------------------------------------
    Atur("timeout.chart_detik", "timeout", "Timeout chart & dashboard", "angka", 60, LANGSUNG,
         "", "Harus lebih kecil dari timeout proses web.", 10, 1800, "detik"),
    Atur("timeout.sqllab_detik", "timeout", "Timeout SQL Lab", "angka", 300, LANGSUNG,
         "", "Query langsung (bukan async) juga dibatasi timeout proses web.", 10, 21600, "detik"),
    Atur("timeout.sqllab_async_detik", "timeout", "Timeout SQL Lab async", "angka", 21600, TERAPKAN,
         "", "", 60, 86400, "detik"),
    Atur("timeout.sesi_menit", "timeout", "Lama sesi login", "angka", 480, LANGSUNG,
         "", "Setelah ini pengguna harus login ulang.", 15, 10080, "menit"),

    # --- Batas data (tab Batas data, khusus Superadmin; lihat batas.py) -----------------------
    # Nilai 0 = TANPA BATAS. "auto" = dihitung dari RAM & disk server (batas.py).
    Atur("upload.aktif", "data", "Izinkan upload Excel/CSV", "ya_tidak", True, LANGSUNG,
         "", "Data disimpan di ALDx Engine (ClickHouse internal)."),
    Atur("upload.ukuran_mb", "data", "Upload: ukuran file maksimal", "angka", 25, LANGSUNG,
         "", "Upload Excel/CSV bawaan Superset. 0 = tanpa batas.", 0, 1048576, "MB"),
    Atur("upload.baris_maks", "data", "Upload: baris maksimal per file", "angka", 200000, LANGSUNG,
         "", "0 = tanpa batas.", 0, 1000000000, "baris"),
    Atur("upload.jenis", "data", "Jenis file diizinkan", "pilihan", ["csv", "xlsx", "xls"], LANGSUNG,
         "", "", opsi=_JENIS_FILE),
    Atur("upload.peran", "data", "Role yang boleh upload", "pilihan", ["Alpha"], LANGSUNG,
         "",
         "Admin selalu boleh. Daftar role diambil dari Superset."),
    Atur("impor.ukuran_mb", "data", "Impor berkas: ukuran maksimal", AUTO,
         int(os.environ["SPS_IMPOR_MAKS_MB"]) if os.environ.get("SPS_IMPOR_MAKS_MB", "").isdigit() else AUTO,
         LANGSUNG, "", "Data › Hubungkan data › Berkas (Excel, CSV, Access, ...). auto = dari RAM web; 0 = tanpa batas.",
         0, 1048576, "MB"),
    Atur("impor.baris_maks", "data", "Impor berkas: baris maksimal per tabel", AUTO, AUTO, LANGSUNG,
         "", "auto = ukuran maksimal ÷ ±120 byte per baris; 0 = tanpa batas.", 0, 10000000000, "baris"),
    Atur("ekstrak.baris_maks", "data", "Ekstrak: baris maksimal per ekstrak", AUTO, AUTO, LANGSUNG,
         "", "auto = 25% kuota ALDx Engine ÷ ±40 byte per baris (terkompresi); 0 = tanpa batas.",
         0, 100000000000, "baris"),
    Atur("ekstrak.total_gb", "data", "Kuota disk ALDx Engine (semua ekstrak & impor)", AUTO, AUTO, LANGSUNG,
         "", "auto = 80% dari (ruang kosong + data ALDx Engine); 0 = tanpa batas.",
         0, 1000000, "GB"),

    Atur("berkas.snapshot_data", "data", "Berkas .aldx boleh membawa data", "ya_tidak", True, LANGSUNG,
         "", "Data diambil sesuai hak akses pembuat. Matikan bila data tidak boleh keluar server."),
    Atur("berkas.baris_snapshot", "data", "Berkas .aldx: baris maksimal per dataset", "angka", 100000, LANGSUNG,
         "", "Dataset lebih besar dipotong (ditandai di berkas). 0 = tanpa batas.", 0, 100000000, "baris"),
    Atur("berkas.ukuran_mb", "data", "Berkas .ald/.aldx: ukuran maksimal", "angka", 100, LANGSUNG,
         "", "Membuka berkas butuh ± 3× ukurannya di RAM proses web (berkas, hasil dekripsi, isi ZIP). "
         "Dibatasi juga oleh Impor berkas: ukuran maksimal. 0 = ikut batas impor.", 0, 4096, "MB"),
    Atur("berkas.peran_muat_data", "data", "Peran yang boleh memuat data dari berkas .aldx", "pilihan",
         ["Admin"], LANGSUNG, "",
         "Memuat data = membuat tabel baru di ALDx Engine. Peran lain tetap bisa mengimpor definisi (.ald). "
         "Superadmin selalu boleh.", opsi=["Admin", "Alpha", "sql_lab", "Pengguna", "Gamma"]),

    Atur("ulasan.moderasi", "fitur", "Komentar perlu disetujui Superadmin", "ya_tidak", True, LANGSUNG,
         "", "Komentar & rating baru tampil untuk orang lain setelah disetujui di Kelola › Moderasi ulasan."),

    # --- Gateway & keamanan --------------------------------------------------------------------
    Atur("gateway.permintaan_per_detik", "gateway", "Batas permintaan per pengguna", "angka", 50, TERAPKAN,
         "", "Per alamat IP. Mencegah satu klien membanjiri server.", 5, 1000, "per detik"),
    Atur("gateway.login_per_menit", "gateway", "Batas percobaan login", "angka", 10, TERAPKAN,
         "", "Per alamat IP, mencegah tebak password.", 3, 100, "per menit"),
    Atur("gateway.log_simpan_hari", "gateway", "Simpan log aktivitas", "angka", 180, TERAPKAN,
         "", "Log lebih tua dihapus otomatis tiap malam.",
         7, 3650, "hari"),
    Atur("keamanan.login_maks_gagal", "gateway", "Kunci akun setelah salah password", "angka", 5, LANGSUNG,
         "", "Salah password berturut-turut (per akun, lokal maupun LDAP) sebelum akun dikunci. 0 = tidak dikunci.",
         0, 50, "kali"),
    Atur("keamanan.login_kunci_menit", "gateway", "Lama akun terkunci", "angka", 15, LANGSUNG,
         "", "Selama terkunci, password benar pun ditolak. Admin bisa membuka lebih cepat di tab Riwayat.",
         1, 1440, "menit"),
    Atur("keamanan.audit_simpan_hari", "gateway", "Simpan jejak audit", "angka", 365, LANGSUNG,
         "", "Login, unduh data, ekspor/impor, perubahan pengguna & hak akses. Lebih tua dihapus otomatis.",
         30, 3650, "hari"),

    # --- Fitur pemrosesan -----------------------------------------------------------------------
    Atur("fitur.sqllab_async", "fitur", "SQL Lab async", "ya_tidak", False, LANGSUNG,
         "",
         "Query SQL Lab dijalankan backgrounder; tidak kena timeout proses web."),
    Atur("fitur.chart_async", "fitur", "Chart async", "ya_tidak", False, TERAPKAN,
         "",
         "Chart dimuat di latar oleh backgrounder. Cocok bila banyak chart lambat."),
]

PETA: dict[str, Atur] = {a.kunci: a for a in DAFTAR}


def bawaan() -> dict[str, Any]:
    return {a.kunci: a.bawaan for a in DAFTAR}


def periksa_silang(nilai: dict[str, Any]) -> list[str]:
    # Nilai bawaan WAJIB lolos pemeriksaan ini (diuji di uji_skema).
    """Aturan yang melibatkan lebih dari satu pengaturan. Kembalikan daftar pesan galat."""
    galat = []
    web = nilai["web.timeout_detik"]
    if nilai["timeout.chart_detik"] >= web:
        galat.append(f"Timeout chart ({nilai['timeout.chart_detik']} dtk) harus lebih kecil dari "
                     f"timeout permintaan web ({web} dtk).")
    if not nilai["fitur.sqllab_async"] and nilai["timeout.sqllab_detik"] >= web:
        galat.append(f"Timeout SQL Lab ({nilai['timeout.sqllab_detik']} dtk) harus lebih kecil dari "
                     f"timeout permintaan web ({web} dtk), atau aktifkan SQL Lab async.")
    if nilai["fitur.sqllab_async"] and nilai["antrean.sqllab"] == 0:
        galat.append("SQL Lab async butuh minimal 1 backgrounder SQL Lab.")
    if nilai["fitur.chart_async"] and nilai["antrean.grafik"] == 0:
        galat.append("Chart async butuh minimal 1 backgrounder chart.")
    return galat
