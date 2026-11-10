"""Batas data: menghitung, menerapkan, dan melepas batas ukuran/baris data.

Pengaturannya ada di skema.py grup "data" (tab Batas data, khusus Superadmin):
    nilai angka  -> batas tetap
    0            -> TANPA BATAS
    "auto"       -> dihitung dari perangkat (lihat REKOMENDASI di bawah)

Rumus rekomendasi (perkiraan aman, bisa ditimpa Superadmin):
    jatah_proses_mb = RAM container web ÷ (jumlah proses web + 1)
    impor/upload MB = jatah_proses_mb ÷ 6        (membaca Excel/CSV ke memori butuh ±5–6× ukuran berkas)
    baris berkas    = MB × 1.048.576 ÷ 120       (±120 byte per baris CSV)
    kuota engine GB = (ruang kosong disk engine + data engine sekarang) × 80%
    baris ekstrak   = kuota engine × 25% ÷ 40    (±40 byte per baris setelah kompresi ClickHouse)

Dipakai oleh:
    sps_koneksi (impor berkas)  -> berlaku("impor.ukuran_mb"), batasi_baris(...)
    sps_engine.ekstrak          -> periksa_kuota_engine(), batasi_baris(...)
    sps_server.konfig           -> upload bawaan Superset (0 = tanpa batas)
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Iterable, Iterator

from sps_server.skema import AUTO, PETA

log = logging.getLogger(__name__)

KUNCI = ("upload.ukuran_mb", "upload.baris_maks", "impor.ukuran_mb", "impor.baris_maks",
         "ekstrak.baris_maks", "ekstrak.total_gb")
FAKTOR_MEMORI_BERKAS = 6
BYTE_PER_BARIS_BERKAS = 120
BYTE_PER_BARIS_EKSTRAK = 40
PORSI_DISK = 0.8
PORSI_SATU_EKSTRAK = 0.25
DETIK_SIMPAN = 300
_tembolok: dict[str, Any] = {"waktu": 0.0, "data": None}


class MelebihiBatas(ValueError):
    """Data melebihi batas yang diatur Superadmin."""


# --- Perangkat & pemakaian ---------------------------------------------------------------------
def _engine_disk() -> dict[str, int | None]:
    """Ruang disk & data ALDx Engine (ClickHouse). None bila engine tidak terjangkau."""
    try:
        from sps_engine import klien as K
        k = K.klien()
        disk = k.kueri_df("SELECT sum(free_space) AS bebas, sum(total_space) AS total FROM system.disks")
        pakai = k.kueri_df(f"SELECT sum(bytes_on_disk) AS b FROM system.parts "
                           f"WHERE database = '{K.nama_db()}' AND active")
        return {"bebas": int(disk["bebas"].iloc[0] or 0), "total": int(disk["total"].iloc[0] or 0),
                "terpakai": int(pakai["b"].iloc[0] or 0)}
    except Exception as exc:  # noqa: BLE001 - engine mati tidak boleh menggagalkan halaman
        log.info("ALDx batas: disk ALDx Engine tidak terbaca (%s)", exc)
        return {"bebas": None, "total": None, "terpakai": None}


def perangkat(atur: dict[str, Any], segar: bool = False) -> dict[str, Any]:
    """RAM web, jumlah proses web, disk engine (disimpan 5 menit)."""
    if not segar and _tembolok["data"] and time.monotonic() - _tembolok["waktu"] < DETIK_SIMPAN:
        return _tembolok["data"]
    from sps_server import tuning
    c = tuning.perangkat_container()
    data = {"ram_web_mb": c.ram_mb, "proses_web": tuning.proses_web(c, atur)["worker"], **_engine_disk()}
    _tembolok.update(waktu=time.monotonic(), data=data)
    return data


def _bulat(n: float) -> int:
    """Bulatkan ke 2 angka penting: 1.234.567 -> 1.200.000 (mudah dibaca & diingat)."""
    if n <= 0:
        return 0
    skala = 10 ** max(0, int(math.log10(n)) - 1)
    return int(n // skala * skala)


def rekomendasi(p: dict[str, Any]) -> dict[str, dict]:
    """Nilai rekomendasi + rumusnya (ditampilkan apa adanya di tab Batas data)."""
    jatah = p["ram_web_mb"] / (p["proses_web"] + 1)
    mb = max(5, min(4096, _bulat(jatah / FAKTOR_MEMORI_BERKAS)))
    baris_berkas = _bulat(mb * 1_048_576 / BYTE_PER_BARIS_BERKAS)
    hasil = {
        "upload.ukuran_mb": {"nilai": mb, "rumus": f"RAM web {p['ram_web_mb']:,} MB ÷ ({p['proses_web']} proses + 1) ÷ {FAKTOR_MEMORI_BERKAS}"},
        "impor.ukuran_mb": {"nilai": mb, "rumus": "sama dengan upload"},
        "upload.baris_maks": {"nilai": baris_berkas, "rumus": f"{mb} MB ÷ {BYTE_PER_BARIS_BERKAS} byte per baris"},
        "impor.baris_maks": {"nilai": baris_berkas, "rumus": f"{mb} MB ÷ {BYTE_PER_BARIS_BERKAS} byte per baris"},
    }
    if p.get("bebas") is not None:
        gb = max(1, int((p["bebas"] + p["terpakai"]) * PORSI_DISK / 1e9))
        hasil["ekstrak.total_gb"] = {"nilai": gb, "rumus": f"(kosong {p['bebas'] / 1e9:,.1f} GB + data engine "
                                                            f"{p['terpakai'] / 1e9:,.2f} GB) × {PORSI_DISK:.0%}"}
        hasil["ekstrak.baris_maks"] = {"nilai": _bulat(gb * 1e9 * PORSI_SATU_EKSTRAK / BYTE_PER_BARIS_EKSTRAK),
                                       "rumus": f"{gb} GB × {PORSI_SATU_EKSTRAK:.0%} ÷ {BYTE_PER_BARIS_EKSTRAK} byte per baris"}
    else:
        for k in ("ekstrak.total_gb", "ekstrak.baris_maks"):
            hasil[k] = {"nilai": 0, "rumus": "ALDx Engine tidak terjangkau: sementara tanpa batas"}
    for v in hasil.values():                                  # format angka Indonesia: 1.234,5
        v["rumus"] = v["rumus"].translate(str.maketrans({",": ".", ".": ","}))
    return hasil


# --- Nilai yang berlaku ------------------------------------------------------------------------------
def berlaku(atur: dict[str, Any], kunci: str) -> int | None:
    """Batas yang berlaku saat ini. None = tanpa batas."""
    v = atur.get(kunci, PETA[kunci].bawaan)
    if v == AUTO:
        v = rekomendasi(perangkat(atur))[kunci]["nilai"]
    v = int(v or 0)
    return v or None


def hitung(atur: dict[str, Any]) -> dict[str, Any]:
    """Data tab Batas data."""
    p = perangkat(atur, segar=True)
    rek = rekomendasi(p)
    daftar = []
    for k in KUNCI:
        a = PETA[k]
        daftar.append({"kunci": k, "label": a.label, "satuan": a.satuan, "nilai": atur[k],
                       "berlaku": berlaku(atur, k), "rekomendasi": rek[k]["nilai"], "rumus": rek[k]["rumus"]})
    return {"perangkat": p, "daftar": daftar}


# --- Penerapan ------------------------------------------------------------------------------------
def _angka(n: int) -> str:
    return f"{n:,}".replace(",", ".")              # 1234567 -> 1.234.567


def _desimal(n: float) -> str:
    return f"{n:,.1f}".translate(str.maketrans({",": ".", ".": ","}))   # 1234,5 -> 1.234,5


def batasi_baris(potongan: Iterable, maks: int | None, apa: str, awal: int = 0) -> Iterator:
    """Teruskan potongan DataFrame; hentikan dengan MelebihiBatas bila baris > maks."""
    total = awal
    for df in potongan:
        total += len(df)
        if maks and total > maks:
            raise MelebihiBatas(f"{apa} melebihi batas {_angka(maks)} baris. Saring datanya, atau minta "
                                "Superadmin menaikkan/melepas batas di Pusat Kendali › Batas data.")
        yield df


def periksa_ukuran(byte: int, atur: dict[str, Any], kunci: str, apa: str) -> None:
    mb = berlaku(atur, kunci)
    if mb and byte > mb * 1_048_576:
        raise MelebihiBatas(f"{apa} {_desimal(byte / 1_048_576)} MB melebihi batas {_angka(mb)} MB. Pecah berkasnya, "
                            "atau minta Superadmin menaikkan/melepas batas di Pusat Kendali › Batas data.")


def periksa_kuota_engine(atur: dict[str, Any]) -> None:
    """Tolak penulisan baru bila data ALDx Engine sudah mencapai kuota."""
    gb = berlaku(atur, "ekstrak.total_gb")
    if not gb:
        return
    terpakai = _engine_disk()["terpakai"]
    if terpakai is not None and terpakai >= gb * 1e9:
        raise MelebihiBatas(f"Kuota ALDx Engine penuh ({_angka(round(terpakai / 1e9))} dari {_angka(gb)} GB). Hapus ekstrak "
                            "yang tidak dipakai, atau minta Superadmin menaikkan kuota di Pusat Kendali › Batas data.")
