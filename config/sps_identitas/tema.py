"""Identitas -> tema Superset, CSS bersama, dan gambar SVG (logo, favicon, spinner) otomatis.

Fungsi murni (tanpa database) agar mudah diuji:
    token_superset(nilai, versi)   token THEME_DEFAULT Superset
    css(nilai, versi)              /identitas/tema.css: variabel warna, hiasan, animasi
    svg_logo / svg_favicon / svg_spinner
"""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from sps_identitas import skema

STATIS = "/static/assets/images/sps"      # folder branding/ (logo bawaan, font)


# --- Warna --------------------------------------------------------------------------------
def _rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def campur(a: str, b: str, porsi_b: float) -> str:
    """Campur dua warna; porsi_b 0..1 bagian warna b."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex([x + (y - x) * porsi_b for x, y in zip(ra, rb)])


def terang(hex_: str) -> float:
    """Luminans relatif WCAG 0..1."""
    def kanal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (kanal(v) for v in _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def teks_di_atas(hex_: str) -> str:
    """Putih atau hitam, mana yang lebih kontras di atas warna ini."""
    return "#FFFFFF" if terang(hex_) < 0.42 else "#111827"


def palet(n: dict[str, Any]) -> dict[str, str]:
    u, a = n["warna_utama"], n["warna_aksen"]
    return {"utama": u, "utama_gelap": campur(u, "#000000", .25), "utama_terang": campur(u, "#FFFFFF", .22),
            "utama_muda": campur(u, "#FFFFFF", .9), "aksen": a, "aksen_muda": campur(a, "#FFFFFF", .82),
            "teks_utama": teks_di_atas(u), "teks_aksen": teks_di_atas(a), "latar": n["warna_latar"]}


# --- Berkas -------------------------------------------------------------------------------
def url_berkas(nama: str, nilai: dict[str, Any], versi: str) -> str:
    """Alamat logo/favicon untuk browser (selalu lewat /identitas agar bisa diganti tanpa restart)."""
    return f"/identitas/berkas/{nama}?v={versi}"


def teks_kaki(n: dict[str, Any]) -> str:
    return n["teks_kaki"].replace("{tahun}", str(date.today().year)).replace("{perusahaan}", n["nama_perusahaan"] or n["nama_aplikasi"])


# --- Tema Superset --------------------------------------------------------------------------
def token_superset(n: dict[str, Any], versi: str, dasar: dict[str, Any]) -> dict[str, Any]:
    """Token tema Superset = token dasar (superset_config) + identitas."""
    p = palet(n)
    return {**dasar,
            "brandAppName": n["nama_aplikasi"],
            "brandLogoAlt": n["nama_perusahaan"] or n["nama_aplikasi"],
            "brandLogoUrl": url_berkas("logo", n, versi),
            "brandLogoHref": n["halaman_depan"],
            "brandSpinnerUrl": f"/identitas/berkas/spinner?v={versi}",
            "colorPrimary": p["utama"],
            "colorLink": p["utama_terang"] if terang(p["utama"]) < .05 else p["utama"],
            "fontFamily": skema.FONT[n["font"]],
            "borderRadius": skema.SUDUT[n["sudut"]],
            "colorBgLayout": n["warna_latar"],
            "motion": bool(n["animasi"])}


def token_gelap(token: dict[str, Any]) -> dict[str, Any]:
    """Token mode gelap: buang warna latar terang agar algoritma gelap Superset yang menentukan latar & teks."""
    gelap = {k: v for k, v in token.items() if k not in ("colorBgLayout", "colorBgBase", "colorTextBase")}
    gelap["colorEditorSelection"] = "#5c4d1a"
    return gelap


# --- CSS bersama ---------------------------------------------------------------------------
_POLA = {
    "gelombang": ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='24' "
                  "viewBox='0 0 160 24'%3E%3Cpath d='M0 12 Q20 0 40 12 T80 12 T120 12 T160 12' fill='none' "
                  "stroke='{w}' stroke-opacity='.35' stroke-width='2'/%3E%3C/svg%3E\")", "160px 24px"),
    "titik": ("radial-gradient({w}55 1.4px, transparent 1.6px)", "16px 16px"),
    "garis": ("repeating-linear-gradient(135deg, {w}33 0 2px, transparent 2px 12px)", "auto"),
    "polos": ("none", "auto"),
}


def pola(n: dict[str, Any], warna: str) -> tuple[str, str]:
    gambar, ukuran = _POLA[n["hiasan"]]
    w = warna.replace("#", "%23") if n["hiasan"] == "gelombang" else warna
    return gambar.replace("{w}", w), ukuran


def css(n: dict[str, Any], versi: str) -> str:
    """CSS yang disisipkan ke SEMUA halaman (Superset & halaman ALDx)."""
    p = palet(n)
    gambar, ukuran = pola(n, p["aksen"])
    var = "\n".join(f"  --sps-{k.replace('_', '-')}: {v};" for k, v in p.items())
    # Gerak elegan: pendek, sekali jalan, tanpa animasi berulang. Hormati "kurangi gerakan" di sistem operasi.
    animasi = """
.dashboard-component-chart-holder,.sps-muncul{animation:sps-muncul .45s cubic-bezier(.2,.8,.2,1) both}
@keyframes sps-muncul{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion: reduce){.dashboard-component-chart-holder,.sps-muncul{animation:none!important}}""" if n["animasi"] else ""
    return f"""/* ALDx identitas v{versi} — dibuat otomatis dari Pusat Kendali > Identitas & Tema. */
@import url("{STATIS}/fonts/fonts.css");
:root{{
{var}
  --sps-font: {skema.FONT[n["font"]]};
  --sps-sudut: {skema.SUDUT[n["sudut"]]}px;
  --sps-pola: {gambar};
  --sps-pola-ukuran: {ukuran};
}}
/* Header halaman ALDx (Pusat Kendali, Studio, Asisten AI): motif hiasan tipis. */
.sps-hiasan{{background-image:var(--sps-pola);background-size:var(--sps-pola-ukuran);background-repeat:repeat-x;
  background-position:0 100%}}
{animasi}
"""


# --- SVG otomatis -----------------------------------------------------------------------------
def _tanda(p: dict[str, str], putih: bool = False) -> str:
    """Tanda (mark) 40x40: kotak membulat berisi tiga batang naik + titik aksen.

    putih=True (untuk latar gelap): kotak putih, batang warna utama.
    """
    kotak, isi = ("#FFFFFF", p["utama"]) if putih else (p["utama"], p["teks_utama"])
    batang = "".join(f'<rect x="{9 + i * 8}" y="{28 - t}" width="5" height="{t + 4}" rx="1.5" fill="{isi}"/>'
                     for i, t in enumerate((6, 11, 16)))
    return (f'<rect width="40" height="40" rx="9" fill="{kotak}"/>{batang}'
            f'<circle cx="31" cy="9" r="3.5" fill="{p["aksen"]}"/>')


def svg_logo(n: dict[str, Any], putih: bool = False) -> str:
    p = palet(n)
    nama = escape(n["nama_aplikasi"])
    lebar = 58 + int(len(n["nama_aplikasi"]) * 13.5)      # 20 px tebal: huruf besar ±13 px, + jarak aman
    warna = "#FFFFFF" if putih else p["utama"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{lebar}" height="40" viewBox="0 0 {lebar} 40" '
            f'role="img" aria-label="{nama}">{_tanda(p, putih)}'
            f'<text x="50" y="27" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700" '
            f'fill="{warna}">{nama}</text></svg>')


def svg_favicon(n: dict[str, Any]) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 40 40">{_tanda(palet(n))}</svg>'


def svg_spinner(n: dict[str, Any]) -> str:
    """Spinner pemuatan Superset: tiga batang naik-turun bergantian (SVG animasi, tanpa skrip)."""
    p = palet(n)
    batang = []
    for i, w in enumerate((p["utama"], p["aksen"], p["utama_terang"])):
        mulai = f"{i * 0.15:.2f}s"
        batang.append(
            f'<rect x="{6 + i * 18}" y="14" width="12" height="36" rx="3" fill="{w}">'
            f'<animate attributeName="height" values="12;36;12" dur="0.9s" begin="{mulai}" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="38;14;38" dur="0.9s" begin="{mulai}" repeatCount="indefinite"/></rect>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">{"".join(batang)}</svg>'
