"""Objek desain dashboard Studio: teks/label, gambar, garis pemisah.

Bentuk dari browser (satu kotak di baris penyusun dashboard, lihat dasbor.py):
    {"jenis": "teks", "lebar": 12, "tinggi": 10, "teks": "Kinerja 2025", "huruf": "playfair-display",
     "ukuran": 32, "tebal": true, "miring": false, "warna": "#111827", "latar": "", "rata": "left", "tegak": "center"}
    {"jenis": "gambar", "lebar": 3, "tinggi": 10, "gambar": "<id 32 hex>", "alt": "Logo", "rata": "center", "pas": "contain"}
    [{"jenis": "garis"}]                         # satu baris berisi garis pemisah (komponen DIVIDER Superset)

Teks & gambar menjadi komponen MARKDOWN Superset berisi HTML ber-style (diizinkan oleh
HTML_SANITIZATION_SCHEMA_EXTENSIONS di superset_config.py). Pengaturan aslinya disimpan di
json_metadata.sps_objek agar bisa dibuka & diubah lagi di Studio.

Huruf: berkas woff2 (OFL/Apache 2.0) dibundel di static/huruf/ -> jalan tanpa internet. Aturan @font-face
huruf yang dipakai ditulis ke CSS dashboard (bagian bertanda ALDX-HURUF, CSS buatan pengguna tidak disentuh).

Gambar diunggah ke tabel sps_gambar (metadb, ikut cadangan) dan disajikan di /studio/gambar/<id>.
Alamat itu terbuka tanpa login agar tampil juga di dashboard sematan; id = sha256 isi berkas (tidak bisa ditebak).
Hanya PNG/JPEG/WebP/GIF (dicek dari byte awal, bukan dari nama berkas). SVG ditolak (bisa berisi skrip).
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime

from sqlalchemy import Column, DateTime, LargeBinary, MetaData, String, Table, select

from sps_ai import alat

# kunci -> (label di menu, CSS font-family, punya berkas woff2 di static/huruf/)
HURUF = {
    "bawaan":            ("Bawaan aplikasi", "inherit", False),
    "inter":             ("Inter (modern, netral)", "'Inter', system-ui, sans-serif", True),
    "plus-jakarta-sans": ("Plus Jakarta Sans (ramah)", "'Plus Jakarta Sans', system-ui, sans-serif", True),
    "montserrat":        ("Montserrat (tegas, geometris)", "'Montserrat', system-ui, sans-serif", True),
    "poppins":           ("Poppins (bulat, bersih)", "'Poppins', system-ui, sans-serif", True),
    "space-grotesk":     ("Space Grotesk (futuristik)", "'Space Grotesk', system-ui, sans-serif", True),
    "oswald":            ("Oswald (ramping, judul besar)", "'Oswald', 'Arial Narrow', sans-serif", True),
    "playfair-display":  ("Playfair Display (serif elegan)", "'Playfair Display', Georgia, serif", True),
    "lora":              ("Lora (serif bacaan)", "'Lora', Georgia, serif", True),
    "roboto-slab":       ("Roboto Slab (slab, laporan)", "'Roboto Slab', Georgia, serif", True),
    "jetbrains-mono":    ("JetBrains Mono (angka, kode)", "'JetBrains Mono', ui-monospace, monospace", True),
}
TINGGI_SAH = (6, 10, 16, 26, 40, 52)            # unit grid Superset (±8 px): 50 px ... 420 px
RATA_SAH = {"left", "center", "right"}
TEGAK_SAH = {"start": "flex-start", "center": "center", "end": "flex-end"}
PAS_SAH = {"contain", "cover"}
MAKS_TEKS = 2000
MAKS_GAMBAR = 3 * 1024 * 1024
TANDA_GAMBAR = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF87a": "image/gif",
                b"GIF89a": "image/gif"}
AWAL_CSS, AKHIR_CSS = "/* ALDX-HURUF mulai (dibuat Studio, jangan diubah) */", "/* ALDX-HURUF selesai */"
# Kotak Markdown Superset berlatar kartu putih + padding 16px; objek ALDx mengatur latarnya sendiri.
CSS_WADAH = (".dashboard-component-chart-holder:has(.aldx-teks),.dashboard-component-chart-holder:has(.aldx-gambar)"
             "{background:transparent!important;box-shadow:none!important;padding:4px!important}")
_WARNA = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_GAMBAR = re.compile(r"^[0-9a-f]{32}$")

_meta = MetaData()
TABEL_GAMBAR = Table("sps_gambar", _meta,
                     Column("id", String(32), primary_key=True), Column("mime", String(40)),
                     Column("isi", LargeBinary), Column("pembuat", String(128)), Column("dibuat", DateTime))


# ---------- Gambar ----------
def _db():
    from superset import db
    TABEL_GAMBAR.create(bind=db.engine, checkfirst=True)
    return db


def jenis_gambar(isi: bytes) -> str | None:
    if isi[:4] == b"RIFF" and isi[8:12] == b"WEBP":
        return "image/webp"
    return next((m for tanda, m in TANDA_GAMBAR.items() if isi.startswith(tanda)), None)


def simpan_gambar(isi: bytes) -> str:
    from flask import g
    from superset import security_manager
    if not security_manager.can_access("can_write", "Dashboard"):
        raise alat.IzinDitolak("Mengunggah gambar butuh izin membuat dashboard.")
    if not isi or len(isi) > MAKS_GAMBAR:
        raise alat.InputSalah("Gambar kosong atau lebih dari 3 MB.")
    mime = jenis_gambar(isi)
    if mime is None:
        raise alat.InputSalah("Format gambar harus PNG, JPEG, WebP, atau GIF.")
    gid = hashlib.sha256(isi).hexdigest()[:32]
    db = _db()
    if db.session.execute(select(TABEL_GAMBAR.c.id).where(TABEL_GAMBAR.c.id == gid)).first() is None:
        db.session.execute(TABEL_GAMBAR.insert().values(id=gid, mime=mime, isi=isi, dibuat=datetime.now(),
                                                         pembuat=getattr(g.user, "username", "")))
        db.session.commit()
    return gid


def baca_gambar(gid: str) -> tuple[bytes, str] | None:
    if not _ID_GAMBAR.match(gid or ""):
        return None
    r = _db().session.execute(select(TABEL_GAMBAR.c.isi, TABEL_GAMBAR.c.mime).where(TABEL_GAMBAR.c.id == gid)).first()
    return (r.isi, r.mime) if r else None


# ---------- Validasi & render ----------
def _warna(v, bawaan: str = "") -> str:
    v = str(v or "").strip()
    return v if _WARNA.match(v) else bawaan


def bersihkan(o: dict) -> dict:
    """Validasi satu objek dari browser -> bentuk baku (nilai di luar daftar sah diganti bawaan)."""
    jenis = o.get("jenis")
    if jenis == "garis":
        return {"jenis": "garis"}
    tinggi = int(o.get("tinggi") or 10)
    dasar = {"jenis": jenis, "lebar": int(o.get("lebar") or 12),
             "tinggi": tinggi if tinggi in TINGGI_SAH else 10,
             "rata": o.get("rata") if o.get("rata") in RATA_SAH else "left"}
    if jenis == "teks":
        teks = str(o.get("teks") or "").strip()[:MAKS_TEKS]
        if not teks:
            raise alat.InputSalah("Kotak teks masih kosong. Isi teksnya atau hapus kotaknya.")
        return {**dasar, "teks": teks, "huruf": o.get("huruf") if o.get("huruf") in HURUF else "bawaan",
                "ukuran": min(max(int(o.get("ukuran") or 16), 10), 96), "tebal": bool(o.get("tebal")),
                "miring": bool(o.get("miring")), "warna": _warna(o.get("warna"), "#111827"),
                "latar": _warna(o.get("latar")), "tegak": o.get("tegak") if o.get("tegak") in TEGAK_SAH else "center"}
    if jenis == "gambar":
        gid = str(o.get("gambar") or "")
        if baca_gambar(gid) is None:
            raise alat.InputSalah("Gambar belum diunggah atau sudah tidak ada.")
        return {**dasar, "gambar": gid, "alt": str(o.get("alt") or "")[:200],
                "pas": o.get("pas") if o.get("pas") in PAS_SAH else "contain"}
    raise alat.InputSalah(f"Jenis objek '{jenis}' tidak dikenal.")


def html_objek(o: dict) -> str:
    """Objek teks/gambar -> isi MARKDOWN Superset (satu baris HTML; teks pengguna di-escape)."""
    if o["jenis"] == "teks":
        gaya = (f"display:flex;flex-direction:column;justify-content:{TEGAK_SAH[o['tegak']]};height:100%;"
                f"box-sizing:border-box;padding:6px 14px;border-radius:10px;line-height:1.25;"
                f"font-family:{HURUF[o['huruf']][1]};font-size:{o['ukuran']}px;"
                f"font-weight:{700 if o['tebal'] else 400};font-style:{'italic' if o['miring'] else 'normal'};"
                f"color:{o['warna']};text-align:{o['rata']};background:{o['latar'] or 'transparent'}")
        isi = "<br>".join(html.escape(b) for b in o["teks"].splitlines())
        return f'<div class="aldx-teks" style="{gaya}"><div>{isi}</div></div>'
    rata = {"left": "flex-start", "center": "center", "right": "flex-end"}[o["rata"]]
    ukuran = "width:100%;height:100%" if o["pas"] == "cover" else "max-width:100%;max-height:100%"
    return (f'<div class="aldx-gambar" style="display:flex;align-items:center;justify-content:{rata};height:100%">'
            f'<img src="/studio/gambar/{o["gambar"]}" alt="{html.escape(o["alt"], quote=True)}" '
            f'style="{ukuran};object-fit:{o["pas"]};border-radius:8px"></div>')


def css_huruf(kunci: set[str]) -> str:
    """Aturan @font-face untuk huruf yang dipakai (berkas lokal, tanpa internet)."""
    aturan = []
    for k in sorted(kunci):
        label, keluarga, ada_berkas = HURUF.get(k, ("", "", False))
        if not ada_berkas:
            continue
        nama = keluarga.split(",")[0]
        for berat in (400, 700):
            aturan.append(f"@font-face{{font-family:{nama};font-style:normal;font-weight:{berat};font-display:swap;"
                          f"src:url(/studio/static/huruf/{k}-latin-{berat}-normal.woff2) format('woff2')}}")
    return "\n".join(aturan)


def gabung_css(css_lama: str | None, kunci: set[str], ada_objek: bool = False) -> str:
    """Ganti bagian ALDX-HURUF di CSS dashboard; CSS lain milik pengguna dibiarkan."""
    lama = css_lama or ""
    if AWAL_CSS in lama and AKHIR_CSS in lama:
        lama = lama[:lama.index(AWAL_CSS)] + lama[lama.index(AKHIR_CSS) + len(AKHIR_CSS):]
    lama = lama.strip()
    baru = "\n".join(x for x in (CSS_WADAH if ada_objek else "", css_huruf(kunci)) if x)
    return (f"{lama}\n\n" if lama else "") + (f"{AWAL_CSS}\n{baru}\n{AKHIR_CSS}" if baru else "")


def daftar_huruf() -> list[dict]:
    return [{"kunci": k, "label": v[0], "keluarga": v[1]} for k, v in HURUF.items()]
