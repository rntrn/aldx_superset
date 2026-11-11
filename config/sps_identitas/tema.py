"""Identitas -> tema Superset, CSS bersama, dan gambar SVG (logo, favicon, spinner) otomatis.

Fungsi murni (tanpa database) agar mudah diuji:
    token_superset(nilai, versi)   token THEME_DEFAULT Superset
    css(nilai, versi)              /identitas/tema.css: variabel warna, hiasan, animasi
    svg_logo / svg_favicon / svg_spinner
"""

from __future__ import annotations

from datetime import date
from html import escape
from urllib.parse import quote
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


def kontras(a: str, b: str) -> float:
    """Rasio kontras WCAG antara dua warna (1..21)."""
    x, y = sorted((terang(a), terang(b)), reverse=True)
    return (x + .05) / (y + .05)


def warna_tautan(p: dict[str, str]) -> str:
    """Tautan: warna utama; bila utama hampir hitam, pakai aksen (bila terbaca di putih, >= 4,5:1) atau abu turunannya."""
    if terang(p["utama"]) >= .05:
        return p["utama"]
    return p["aksen"] if kontras(p["aksen"], "#FFFFFF") >= 4.5 else p["utama_terang"]


def teks_di_atas(hex_: str) -> str:
    """Putih atau hitam, mana yang lebih kontras di atas warna ini."""
    return "#FFFFFF" if terang(hex_) < 0.42 else "#111827"


def palet(n: dict[str, Any]) -> dict[str, str]:
    u, a = n["warna_utama"], n["warna_aksen"]
    return {"utama": u, "utama_gelap": campur(u, "#000000", .25), "utama_terang": campur(u, "#FFFFFF", .22),
            "utama_muda": campur(u, "#FFFFFF", .9), "aksen": a, "aksen_muda": campur(a, "#FFFFFF", .82),
            "aksen_terang": campur(a, "#FFFFFF", .25),          # aksen untuk teks di latar gelap (kontras >= 4,5:1)
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
            "colorLink": warna_tautan(p),
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
def _svg_tinta(aksen: str) -> str:
    """Motif sapuan kuas & percikan tinta (abu) dengan semburat warna aksen. Abu tengah = terbaca di latar terang & gelap."""
    abu = "#8A8A93"
    titik = "".join(f"<circle cx='{x}' cy='{y}' r='{r}' fill='{abu}' fill-opacity='.3'/>"
                    for x, y, r in ((22, 20, 2.2), (34, 28, 1.2), (118, 12, 1.6), (204, 56, 2.4), (214, 50, 1.1)))
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='240' height='72' viewBox='0 0 240 72'>"
           f"<path d='M6 58C46 40 92 30 150 22S222 10 236 6L234 12C196 20 150 34 96 44S30 60 8 64Z' "
           f"fill='{abu}' fill-opacity='.1'/>{titik}"
           f"<circle cx='176' cy='40' r='3' fill='{aksen}' fill-opacity='.6'/>"
           f"<circle cx='186' cy='47' r='1.4' fill='{aksen}' fill-opacity='.6'/>"
           f"<circle cx='62' cy='12' r='1.8' fill='{aksen}' fill-opacity='.45'/></svg>")
    return f'url("data:image/svg+xml,{quote(svg)}")'


_POLA = {
    "gelombang": ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='24' "
                  "viewBox='0 0 160 24'%3E%3Cpath d='M0 12 Q20 0 40 12 T80 12 T120 12 T160 12' fill='none' "
                  "stroke='{w}' stroke-opacity='.35' stroke-width='2'/%3E%3C/svg%3E\")", "160px 24px"),
    "titik": ("radial-gradient({w}55 1.4px, transparent 1.6px)", "16px 16px"),
    "garis": ("repeating-linear-gradient(135deg, {w}33 0 2px, transparent 2px 12px)", "auto"),
    "polos": ("none", "auto"),
    "tinta": (_svg_tinta, "360px 108px"),
}


def pola(n: dict[str, Any], warna: str) -> tuple[str, str]:
    gambar, ukuran = _POLA[n["hiasan"]]
    if callable(gambar):
        return gambar(warna), ukuran
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
# Tanda "Tebasan": huruf A tajam yang condong (ambisi, cepat) dibelah sayatan warna aksen yang naik ke kanan
# dan menembus bingkai (presisi, tumbuh, futuristik). Geometri pada kisi 40x40, terbaca sampai 16 px.
_HURUF_A = "M7.5 32.5 L20 10 L32.5 32.5"
_SAYATAN = "M13 26.6 L39.5 19.9"


def _tanda(p: dict[str, str], putih: bool = False) -> str:
    """Tanda (mark) 40x40. putih=True (untuk latar gelap): kotak putih, huruf warna utama."""
    kotak, huruf = ("#FFFFFF", p["utama"]) if putih else (p["utama"], p["teks_utama"])
    return (f'<rect width="40" height="40" rx="10" fill="{kotak}"/>'
            f'<path d="{_HURUF_A}" fill="none" stroke="{huruf}" stroke-width="4" stroke-linejoin="miter" '
            f'stroke-miterlimit="10"/>'
            f'<path d="{_SAYATAN}" stroke="{kotak}" stroke-width="6.2"/>'          # celah: A tampak terbelah
            f'<path d="{_SAYATAN}" stroke="{p["aksen"]}" stroke-width="3.4"/>')


def svg_logo(n: dict[str, Any], putih: bool = False) -> str:
    p = palet(n)
    nama = escape(n["nama_aplikasi"])
    lebar = 58 + int(len(n["nama_aplikasi"]) * 13.5)      # 20 px tebal: huruf besar ±13 px, + jarak aman
    warna = "#FFFFFF" if putih else p["utama"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{lebar}" height="40" viewBox="0 0 {lebar} 40" '
            f'role="img" aria-label="{nama}">{_tanda(p, putih)}'
            f'<text x="50" y="27" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="800" letter-spacing="-.3" '
            f'fill="{warna}">{nama}</text></svg>')


def svg_favicon(n: dict[str, Any]) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 40 40">{_tanda(palet(n))}</svg>'


def svg_spinner(n: dict[str, Any]) -> str:
    """Spinner pemuatan Superset: huruf A tanda ALDx yang dibelah sayatan aksen berulang (SVG animasi, tanpa skrip)."""
    p = palet(n)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 40 40">'
            f'<path d="{_HURUF_A}" fill="none" stroke="{p["utama"]}" stroke-width="4" stroke-linejoin="miter" '
            'stroke-miterlimit="10" opacity=".9"/>'
            '<clipPath id="k"><rect width="40" height="40"/></clipPath><g clip-path="url(#k)">'
            f'<path d="M-30 33 L6 23.6" stroke="{p["aksen"]}" stroke-width="3.4" stroke-linecap="round">'
            '<animateTransform attributeName="transform" type="translate" values="0 0;66 -17" dur="0.9s" '
            'calcMode="spline" keySplines=".6 0 .2 1" repeatCount="indefinite"/></path></g></svg>')
