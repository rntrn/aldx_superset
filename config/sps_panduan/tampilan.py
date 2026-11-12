"""Halaman /panduan/: render Markdown docs/ menjadi HTML dengan tampilan aplikasi."""

from __future__ import annotations

import html
import os
import re
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, abort, jsonify, redirect, render_template_string, request, send_from_directory

FOLDER = Path(__file__).resolve().parent
DOCS = Path(os.environ.get("SPS_DOCS_DIR", "/app/docs"))
AKAR = Path(os.environ.get("SPS_DOCS_AKAR", "/app/docs-akar"))      # CARA-PASANG.md
bp = Blueprint("sps_panduan", __name__, url_prefix="/panduan")

# Halaman di luar docs/ (berkas di akar repo).
LUAR = {"cara-pasang": "CARA-PASANG.md"}          # CHANGELOG = log pengembangan, tidak ditampilkan

# Sidebar per peran: (judul kelompok, [(halaman, judul)]). Bab yang tidak terdaftar tetap bisa dibuka.
NAVIGASI = [
    ("Mulai", [("00-mulai-di-sini", "Peta dokumentasi"), ("cara-pasang", "Cara pasang"),
               ("22-cangkang-aplikasi", "Mengenal aplikasi")]),
    ("Pengguna & analis", [("21-kueri-visual-dan-alur-menu", "Menu & Kueri Visual"), ("12-studio-visual", "Studio Visual"),
                           ("17-katalog-chart-peta-prediksi", "Katalog chart, peta, ramalan"),
                           ("28-sambungkan-asisten-ai", "Menyambungkan Asisten AI"),
                           ("23-asisten-ai-peran-ahli", "Asisten AI di setiap halaman"),
                           ("10-asisten-ai", "Auto chart, dashboard & Story"),
                           ("25-berkas-filter-global-ulasan", "Berkas .aldx, filter global, ulasan"),
                           ("26-langganan-versi-ponsel-lihat-sebagai", "Langganan, versi, ponsel")]),
    ("Admin data", [("06-sumber-data", "Hubungkan sumber data"), ("08-hak-akses-data", "Hak akses data (RLS)"),
                    ("13-sps-engine-ekstrak", "ALDx Engine & ekstrak"), ("07-dashboard-sebagai-kode", "Dashboard sebagai kode"),
                    ("30-sematkan-dashboard", "Sematkan ke web lain")]),
    ("Admin server", [("18-installer", "Installer"), ("02-instalasi", "Instalasi manual"), ("01-arsitektur", "Arsitektur"),
                      ("03-operasional", "Operasional harian"), ("11-pusat-kendali-server", "Pusat Kendali"),
                      ("24-superadmin-dan-batas-data", "Superadmin & batas data"), ("14-akun-dan-akses", "Akun & akses komponen"),
                      ("05-login-ldap", "Login lokal & LDAP"), ("09-identitas-tema", "Identitas & tema"),
                      ("20-model-ai-lokal", "Model AI lokal (rinci)"), ("15-sizing", "Sizing CPU, RAM, disk"),
                      ("16-upgrade-downgrade", "Upgrade & downgrade"),
                      ("29-versi-pembaruan-hapus-total", "Versi & hapus total"), ("31-catatan-versi", "Catatan versi"), ("32-perbandingan-fitur-bi", "Perbandingan fitur BI"), ("19-runbook-faq-admin", "Runbook & FAQ"),
                      ("04-troubleshooting", "Troubleshooting"), ("27-daftar-periksa-audit-keamanan", "Audit keamanan")]),
    ("Tutorial", [("tutorial/", "Ringkasan"), ("tutorial/level-1-pengguna", "Level 1 · Pengguna"),
                  ("tutorial/level-2-analis", "Level 2 · Analis"), ("tutorial/level-3-admin-data", "Level 3 · Admin data"),
                  ("tutorial/level-4-admin-server", "Level 4 · Admin server")]),
    ("Bahan ajar", [("bahan-ajar/", "Ringkasan"), ("bahan-ajar/level-1-pengguna", "Level 1 · Pengguna"),
                    ("bahan-ajar/level-2-analis", "Level 2 · Analis"), ("bahan-ajar/level-3-admin-data", "Level 3 · Admin data"),
                    ("bahan-ajar/level-4-admin-server", "Level 4 · Admin server"),
                    ("bahan-ajar/modul-runbook-admin", "Runbook admin")]),
    ("Lainnya", [("pengujian/", "Skenario uji (UAT)"), ("pdf/", "Versi PDF")]),
]

_TAG_HTML = re.compile(r"^</?(a|b|i|u|s|br|hr|img|sup|sub|kbd|code|small|strong|em|mark|span|div|p|details|summary|"
                       r"table|thead|tbody|tr|th|td|ul|ol|li|pre|blockquote|h[1-6]|center|picture|source|video)\b", re.I)


def _login():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return redirect(f"/login/?next={request.path}")
    return None


def _berkas(halaman: str) -> Path | None:
    """Nama halaman (tanpa .md) -> berkas Markdown, aman dari ../ keluar folder."""
    halaman = halaman.strip("/")
    if halaman in LUAR:
        p = AKAR / LUAR[halaman]
        return p if p.is_file() else None
    calon = [DOCS / f"{halaman}.md", DOCS / halaman / "README.md"] if halaman else [DOCS / "00-mulai-di-sini.md"]
    for p in calon:
        try:
            p.resolve().relative_to(DOCS.resolve())
        except ValueError:
            return None
        if p.is_file():
            return p
    return None


def _slug(teks: str, sep: str = "-") -> str:
    """Penanda judul gaya GitHub, agar tautan #bagian di dokumen tetap cocok."""
    teks = re.sub(r"<[^>]+>", "", html.unescape(teks)).strip().lower()
    teks = re.sub(r"[^\w\- ]", "", teks)
    return teks.replace(" ", sep)


def _amankan_placeholder(md: str) -> str:
    """<email>, <nama> di teks biasa ditampilkan apa adanya (bukan dianggap tag HTML). Kode tidak disentuh."""
    keluar, di_blok = [], False
    for baris in md.split("\n"):
        if baris.lstrip().startswith("```"):
            di_blok = not di_blok
        if di_blok or baris.lstrip().startswith("```"):
            keluar.append(baris)
            continue
        potong = re.split(r"(`+[^`]*`+)", baris)
        for i in range(0, len(potong), 2):
            potong[i] = re.sub(r"<[^<>\n]+>", lambda m: m.group(0) if _TAG_HTML.match(m.group(0)) or
                               m.group(0).startswith("<!--") or re.match(r"<https?://", m.group(0))
                               else m.group(0).replace("<", "&lt;").replace(">", "&gt;"), potong[i])
        keluar.append("".join(potong))
    return "\n".join(keluar)


def _tautan(html_isi: str, halaman: str) -> str:
    """Tautan .md -> /panduan/..., berkas akar repo -> halaman panduannya, gambar & PDF -> /panduan/berkas/."""
    if halaman in LUAR:
        folder = ""                          # berkas akar repo: tautannya relatif ke akar
    else:
        folder = "docs/" + (halaman.rstrip("/").rsplit("/", 1)[0] + "/" if "/" in halaman.rstrip("/") or
                            halaman.endswith("/") else "")
        if halaman.endswith("/") and "/" not in halaman.rstrip("/"):
            folder = f"docs/{halaman}"       # README di subfolder, mis. tutorial/

    def ganti(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^([a-z]+:|#|/)", url, re.I):
            return m.group(0)
        jalur, _, jangkar = url.partition("#")
        tanda = f"#{jangkar}" if jangkar else ""
        repo = os.path.normpath(f"{folder}{jalur}").replace("\\", "/")      # jalur relatif ke akar repo
        for k, v in LUAR.items():
            if repo == v:
                return f'{attr}="/panduan/{k}{tanda}"'
        if repo != "docs" and not repo.startswith("docs/"):
            return f'{attr}="#" title="Berkas di folder instalasi: {html.escape(repo)}"'
        rel = repo[5:]
        akhir = rel.rsplit("/", 1)[-1]
        if rel.endswith(".md") or "." not in akhir:                         # halaman panduan
            rel = re.sub(r"(README)?\.md$", "", rel)
            return f'{attr}="/panduan/{rel}{tanda}"'
        return f'{attr}="/panduan/berkas/{rel}{tanda}"'

    html_isi = re.sub(r'(href|src)="([^"]+)"', ganti, html_isi)

    def judul_tautan(m):
        """Teks tautan yang hanya nama berkas ("22-cangkang-aplikasi.md") diganti judul babnya."""
        p = _berkas(m.group(2).strip("/") + ("/" if m.group(2).endswith("/") else ""))
        if p is None:
            return m.group(0)
        j = re.search(r"^#\s+(.+)$", p.read_text(encoding="utf-8"), re.M)
        if not j:
            return m.group(0)
        teks = re.sub(r"[`*]", "", j.group(1)).strip()
        akhir = m.group(4).strip()
        bagian = re.search(r"(§\s*[\w.]+)$", akhir)
        return f'{m.group(1)}{html.escape(teks)}{" " + bagian.group(1) if bagian else ""}</a>'

    return re.sub(r'(<a href="/panduan/([^"#]*)(#[^"]*)?"[^>]*>)\s*((?:\.\./)*[\w./-]+\.md(?:\s*§\s*[\w.]+)?)\s*</a>',
                  judul_tautan, html_isi)


@lru_cache(maxsize=256)
def _render(jalur: str, diubah: float, halaman: str) -> tuple[str, str, list]:
    import markdown
    teks = Path(jalur).read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
                           extension_configs={"toc": {"slugify": _slug, "toc_depth": "2-3"}})
    isi = md.convert(_amankan_placeholder(teks))
    judul = re.search(r"^#\s+(.+)$", teks, re.M)
    daftar = []

    def ratakan(token):                                  # judul tingkat 2 & 3 (toc_depth), urut dokumen
        for t in token:
            daftar.append((t["id"], re.sub(r"<[^>]+>", "", t["name"]), t["level"]))
            ratakan(t.get("children", []))
    ratakan(md.toc_tokens)
    return _tautan(isi, halaman), (judul.group(1).strip() if judul else halaman), daftar


@bp.route("/", defaults={"halaman": ""})
@bp.route("/<path:halaman>")
def baca(halaman: str):
    if (r := _login()) is not None:
        return r
    if halaman.endswith(".md"):
        bersih = halaman[:-3]
        return redirect(f"/panduan/{bersih[:-6] if bersih.endswith('README') else bersih}")
    p = _berkas(halaman)
    if p is None:
        abort(404)
    # README di subfolder: tautannya relatif ke folder itu (kunci diakhiri "/").
    kunci = halaman.strip("/") + ("/" if p.name == "README.md" and halaman.strip("/") else "")
    isi, judul, daftar = _render(str(p), p.stat().st_mtime, kunci)
    from flask import current_app
    sekarang = kunci
    return render_template_string((FOLDER / "halaman.html").read_text(encoding="utf-8"),
                                  isi=isi, judul=re.sub(r"[`*]", "", judul), daftar=daftar, navigasi=NAVIGASI,
                                  sekarang=sekarang or "00-mulai-di-sini",
                                  app_name=current_app.config.get("APP_NAME", "ALDx"))


@bp.route("/berkas/<path:nama>")
def berkas(nama: str):
    """Gambar, PDF, dan lampiran di docs/ (hanya jenis yang aman)."""
    if (r := _login()) is not None:
        return r
    if not re.search(r"\.(png|jpe?g|gif|svg|webp|pdf|xlsx)$", nama, re.I):
        abort(404)
    return send_from_directory(DOCS, nama)


_indeks: dict = {"kunci": None, "isi": []}


def _berkas_md() -> list[tuple[Path, str]]:
    """Semua halaman panduan (tanpa node_modules / .vitepress / public), relatif ke docs/."""
    hasil = []
    for akar, folder, berkas in os.walk(DOCS):
        folder[:] = [f for f in folder if f not in ("node_modules", ".vitepress", "public", "gambar", "pdf")]
        for b in berkas:
            if b.endswith(".md"):
                p = Path(akar) / b
                hasil.append((p, str(p.relative_to(DOCS))[:-3].replace("\\", "/")))
    hasil += [(AKAR / v, k) for k, v in LUAR.items() if (AKAR / v).is_file()]
    return hasil


def _indeks_cari() -> list[tuple[str, str, str]]:
    """(halaman, judul, teks) semua halaman; dibangun ulang hanya bila ada berkas yang berubah."""
    daftar = _berkas_md()
    kunci = tuple(sorted((n, p.stat().st_mtime) for p, n in daftar))
    if _indeks["kunci"] != kunci:
        isi = []
        for p, nama in daftar:
            if nama in ("index", "cara-pasang", "catatan-versi") and p.parent == DOCS:
                continue
            teks = p.read_text(encoding="utf-8")
            judul = (re.search(r"^#\s+(.+)$", teks, re.M) or [None, nama])[1]
            isi.append((nama[:-6] if nama.endswith("README") else nama, judul, teks))
        _indeks.update(kunci=kunci, isi=isi)
    return _indeks["isi"]


@bp.route("/api/cari")
def cari():
    """Pencarian teks penuh sederhana di semua halaman: judul dulu, lalu isi."""
    if _login() is not None:
        return jsonify(error="Belum login"), 401
    q = (request.args.get("q") or "").strip().lower()[:100]
    if len(q) < 2:
        return jsonify(hasil=[])
    hasil = []
    for nama, judul, teks in _indeks_cari():
        i = teks.lower().find(q)
        if i < 0:
            continue
        bagian = None
        for m in re.finditer(r"^#{2,3}\s+(.+)$", teks[:i], re.M):
            bagian = m.group(1)
        cuplik = re.sub(r"[#*`|>\[\]]", "", teks[max(0, i - 60): i + 90]).replace("\n", " ").strip()
        skor = (0 if q in judul.lower() else 1, i)
        hasil.append({"halaman": f"/panduan/{nama}" + (f"#{_slug(bagian)}" if bagian else ""),
                      "judul": re.sub(r"[`*]", "", judul), "bagian": bagian, "cuplik": cuplik, "_skor": skor})
    hasil.sort(key=lambda x: x["_skor"])
    return jsonify(hasil=[{k: v for k, v in h.items() if k != "_skor"} for h in hasil[:20]])
