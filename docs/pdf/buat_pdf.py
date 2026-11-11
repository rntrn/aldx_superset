"""Membuat ulang semua PDF dokumentasi ALDx dari sumber Markdown.

Sumber tetap berkas .md; PDF hanya hasil cetak. Jalankan setelah dokumen diubah:

    python docs/pdf/buat_pdf.py                 # semua PDF
    python docs/pdf/buat_pdf.py --hanya dokumen # satu kelompok: dokumen | manual | tutorial | bahan-ajar | uji | runbook

Butuh Python 3.10+ dengan:  pip install markdown pypdf playwright  lalu  playwright install chromium
(atau isi ALDX_CHROMIUM dengan jalur Chromium yang sudah ada).

Alur:  Markdown -> HTML (gaya ALDx "Tinta & Sakura": hitam, abu, putih + pink) -> PDF A4 lewat Chromium.
Berkas gabungan (manual, tutorial, bahan ajar) mendapat sampul, daftar isi, bookmark, dan tautan antar-dokumen
di dalam PDF. presentasi-sosialisasi.pdf dibuat terpisah (sumber slide di luar repo) dan tidak disentuh skrip ini.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import markdown

AKAR = Path(__file__).resolve().parents[2]
DOCS = AKAR / "docs"
KELUAR = DOCS / "pdf"
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]


# ---------------------------------------------------------------------------------------------
# 1. Daftar PDF yang dibuat
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Berkas:
    keluar: str                 # jalur relatif terhadap docs/pdf
    judul: str
    sumber: tuple[Path, ...]
    kelompok: str
    keterangan: str = ""        # tampil di sampul (hanya berkas gabungan)

    @property
    def gabungan(self) -> bool:
        return len(self.sumber) > 1


def _dokumen_teknis() -> list[Path]:
    return sorted(DOCS.glob("[0-9][0-9]-*.md"))


def daftar_berkas() -> list[Berkas]:
    tutorial = [DOCS / "tutorial" / f for f in ("README.md", "level-1-pengguna.md", "level-2-analis.md",
                                                "level-3-admin-data.md", "level-4-admin-server.md")]
    ajar = [DOCS / "bahan-ajar" / f for f in ("README.md", "level-1-pengguna.md", "level-2-analis.md",
                                              "level-3-admin-data.md", "level-4-admin-server.md",
                                              "modul-runbook-admin.md")]
    hasil = [Berkas(f"dokumen/{p.stem}.pdf", _judul(p), (p,), "dokumen") for p in _dokumen_teknis()]
    hasil += [
        Berkas("cara-pasang.pdf", "Cara Memasang ALDx", (AKAR / "CARA-PASANG.md",), "manual"),
        Berkas("manual-lengkap.pdf", "Manual Lengkap", (AKAR / "README.md", AKAR / "CARA-PASANG.md", *_dokumen_teknis()),
               "manual", "Panduan pasang + seluruh dokumentasi teknis: arsitektur, instalasi, operasional, sumber data, "
               "hak akses, identitas, Pusat Kendali, Studio, ALDx Engine, akun, sizing, upgrade, installer, runbook, "
               "Asisten AI, berkas & filter global, keamanan, versi."),
        Berkas("tutorial-semua-level.pdf", "Tutorial Semua Level", tuple(tutorial), "tutorial",
               "Tutorial bergambar Level 1 Pengguna sampai Level 4 Admin server."),
        Berkas("bahan-ajar-lengkap.pdf", "Bahan Ajar Lengkap", tuple(ajar), "bahan-ajar",
               "Modul pengajar Level 1–4 dan modul runbook admin: rencana sesi, latihan, kunci jawaban, kuis."),
        Berkas("pengujian-uat.pdf", "Pengujian & UAT",
               (DOCS / "pengujian" / "README.md", DOCS / "pengujian" / "skenario-uji.md"), "uji",
               "Uji otomatis, uji asap, dan seluruh skenario UAT (isian di lembar-uji.xlsx)."),
        Berkas("kartu-runbook-admin.pdf", "Runbook & FAQ Admin", (DOCS / "19-runbook-faq-admin.md",), "runbook"),
    ]
    hasil += [Berkas(f"per-level/tutorial-{p.stem}.pdf", _judul(p), (p,), "tutorial") for p in tutorial[1:]]
    hasil += [Berkas(f"per-level/bahan-ajar-{p.stem}.pdf", _judul(p), (p,), "bahan-ajar") for p in ajar[1:]]
    return hasil


# ---------------------------------------------------------------------------------------------
# 2. Markdown -> HTML
# ---------------------------------------------------------------------------------------------
def _judul(md: Path) -> str:
    for baris in md.read_text(encoding="utf-8").splitlines():
        if baris.startswith("# "):
            return baris[2:].strip()
    return md.stem


def _id_dokumen(md: Path) -> str:
    return "d-" + re.sub(r"[^a-z0-9]+", "-", str(md.relative_to(AKAR)).lower()).strip("-")


_TAG_BOLEH = re.compile(r"</?(br|b|i|kbd|sub|sup|small|details|summary)\b|<(https?://|mailto:)", re.I)
_KODE = re.compile(r"(```.*?```|`[^`\n]+`)", re.S)


def _amankan_kurung(teks: str) -> str:
    """'<nama>' di luar kode adalah teks, bukan tag HTML: tulis sebagai &lt;nama&gt;."""
    potong = _KODE.split(teks)
    for i in range(0, len(potong), 2):                     # indeks genap = di luar kode
        potong[i] = re.sub(r"<(?=[^<>\n]*>)", lambda m: m.group(0) if _TAG_BOLEH.match(potong[i], m.start())
                           else "&lt;", potong[i])
    return "".join(potong)


def _slug(prefiks: str):
    def buat(teks: str, pemisah: str) -> str:
        dasar = re.sub(r"[^\w\s-]", "", teks.lower(), flags=re.U).strip()
        return f"{prefiks}--{re.sub(r'[\s]+', pemisah, dasar)}"
    return buat


def md_ke_html(md: Path, dalam_paket: set[Path]) -> str:
    """Satu dokumen -> potongan HTML. Tautan ke dokumen lain di paket yang sama menjadi tautan internal."""
    pid = _id_dokumen(md)
    mesin = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
                              extension_configs={"toc": {"slugify": _slug(pid), "permalink": False}})
    isi = mesin.convert(_amankan_kurung(md.read_text(encoding="utf-8")))

    def tautan(m: re.Match) -> str:
        href = html.unescape(m.group(2))
        if re.match(r"^(https?:|mailto:|#)", href):
            if href.startswith("#"):
                return f'{m.group(1)}"#{pid}--{href[1:]}"'
            return m.group(0)
        jalur, _, jangkar = href.partition("#")
        tujuan = (md.parent / jalur).resolve()
        if tujuan in dalam_paket:
            tid = _id_dokumen(tujuan)
            return f'{m.group(1)}"#{tid}--{jangkar}"' if jangkar else f'{m.group(1)}"#{tid}"'
        if tujuan.exists() and tujuan.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".gif"):
            return f'{m.group(1)}"{tujuan.as_uri()}"'
        return 'data-luar="1"'                                # berkas di luar PDF: teks tanpa tautan

    isi = re.sub(r'(href=)"([^"]*)"', tautan, isi)
    isi = re.sub(r'(src=)"(?!https?:|data:)([^"]*)"',
                 lambda m: f'{m.group(1)}"{(md.parent / html.unescape(m.group(2))).resolve().as_uri()}"', isi)
    return f'<section class="dok" id="{pid}">{isi}</section>'


# ---------------------------------------------------------------------------------------------
# 3. Halaman HTML lengkap (gaya ALDx)
# ---------------------------------------------------------------------------------------------
GAYA = """
@import url("{font}");
@page {{ size: A4; margin: 18mm 18mm 16mm 18mm; }}
:root {{ --utama:#18181B; --abu:#3F3F46; --aksen:#E11D74; --aksen-muda:#FDE8F1; --teks:#27272A;
         --garis:#E4E4E7; --muda:#F4F4F5; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Plus Jakarta Sans", "Segoe UI", Arial, sans-serif; color: var(--teks); font-size: 10.5pt;
        line-height: 1.5; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ color: var(--utama); font-size: 22pt; line-height: 1.2; margin: 0 0 14pt; padding-bottom: 8pt;
      border-bottom: 2.2pt solid var(--aksen); }}
h2 {{ color: var(--utama); font-size: 15pt; padding-left: 8pt; border-left: 3pt solid var(--aksen); margin: 20pt 0 8pt; break-after: avoid; }}
h3 {{ color: var(--utama); font-size: 12pt; margin: 16pt 0 6pt; break-after: avoid; }}
h4 {{ color: var(--utama); font-size: 10.5pt; margin: 12pt 0 4pt; break-after: avoid; }}
p, li {{ orphans: 3; widows: 3; }}
a {{ color: var(--aksen); text-decoration: none; }}
a[data-luar] {{ color: inherit; }}
code {{ font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.8pt; background: var(--muda);
        border-radius: 3pt; padding: 0 2.5pt; }}
pre {{ background: #FAFAFA; border: 0.75pt solid var(--garis); border-left: 3pt solid var(--abu); border-radius: 4pt;
       padding: 7pt 9pt; white-space: pre; overflow: hidden; break-inside: avoid; }}
pre.lipat {{ white-space: pre-wrap; word-break: break-word; }}
pre code {{ background: none; padding: 0; font-size: inherit; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 12pt; font-size: 9pt; }}
thead {{ display: table-header-group; }}
th {{ background: var(--utama); color: #fff; text-align: left; font-weight: 700; padding: 5pt 7pt; }}
td {{ padding: 5pt 7pt; border-bottom: 0.75pt solid var(--garis); vertical-align: top; }}
th, td {{ overflow-wrap: break-word; }}
table.padat {{ table-layout: fixed; font-size: 7.8pt; }}
table.padat th, table.padat td {{ overflow-wrap: anywhere; padding: 4pt 5pt; }}
li code, p code {{ overflow-wrap: anywhere; }}   /* jalur/perintah panjang di paragraf boleh dipenggal */
tr {{ break-inside: avoid; }}
tbody tr:nth-child(even) td {{ background: var(--muda); }}
img {{ max-width: 100%; max-height: 210mm; display: block; margin: 8pt auto; border: 0.75pt solid var(--garis);
       border-radius: 4pt; break-inside: avoid; }}
blockquote {{ margin: 8pt 0; padding: 6pt 10pt; background: var(--aksen-muda); border-left: 3pt solid var(--aksen);
              border-radius: 3pt; }}
blockquote p {{ margin: 0; }}
hr {{ border: 0; border-top: 0.75pt solid var(--garis); margin: 14pt 0; }}
.dok + .dok {{ break-before: page; }}
.sampul {{ height: 255mm; display: flex; flex-direction: column; justify-content: flex-end; break-after: page;
           padding: 22mm 18mm 20mm; border-radius: 8pt; color: #fff; position: relative; overflow: hidden;
           background: radial-gradient(circle at 88% 92%, rgba(225,29,116,.55), transparent 42%),
                       linear-gradient(160deg, #0B0B0D 0%, #18181B 45%, #52525B 100%); }}
.sampul img {{ border: 0; margin: 0; width: 48mm; position: absolute; top: 22mm; left: 18mm; }}
.sampul h1 {{ color: #fff; font-size: 36pt; border-bottom: 3pt solid var(--aksen); margin: 0 0 10pt;
              padding-bottom: 10pt; }}
.sampul .ket {{ font-size: 12pt; color: #E4E4E7; max-width: 150mm; }}
.sampul .tgl {{ margin-top: 14mm; font-size: 10pt; color: #A1A1AA; }}
.isi {{ break-after: page; }}
.isi h2 {{ margin-top: 0; }}
.isi ol {{ padding-left: 16pt; }}
.isi li {{ margin: 2.5pt 0; }}
"""

# Agar tidak ada yang lebih lebar dari kertas (Chromium akan mengecilkan SELURUH halaman):
# blok kode diperkecil sampai muat (diagram ASCII tetap utuh), bila tetap tidak muat dilipat;
# tabel yang terlalu lebar diberi mode "padat" (kolom rata, huruf lebih kecil).
PAS_KODE = """() => { for (const pre of document.querySelectorAll('pre')) {
  let ukuran = 8.8;
  while (pre.scrollWidth > pre.clientWidth && ukuran > 6.4) { ukuran -= 0.2; pre.style.fontSize = ukuran + 'pt'; }
  if (pre.scrollWidth > pre.clientWidth) { pre.style.fontSize = ''; pre.classList.add('lipat'); } }
  for (const t of document.querySelectorAll('table')) {
    if (t.getBoundingClientRect().width > t.parentElement.clientWidth + 1) t.classList.add('padat'); } }"""

KAKI = ('<div style="width:100%;font-family:Arial,sans-serif;font-size:7pt;color:#71717A;padding:0 18mm;'
        'display:flex;justify-content:space-between"><span>{judul}</span>'
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def halaman_html(berkas: Berkas) -> str:
    paket = {p.resolve() for p in berkas.sumber}
    bagian = [md_ke_html(p, paket) for p in berkas.sumber]
    awal = ""
    if berkas.gabungan:
        hari = date.today()
        logo = (AKAR / "branding" / "logo-aldx-putih.svg").as_uri()
        daftar = "".join(f'<li><a href="#{_id_dokumen(p)}">{html.escape(_judul(p))}</a></li>' for p in berkas.sumber)
        awal = (f'<section class="sampul"><img src="{logo}" alt="ALDx"><h1>{html.escape(berkas.judul)}</h1>'
                f'<p class="ket">{html.escape(berkas.keterangan)}</p>'
                f'<p class="tgl">Diperbarui {hari.day} {BULAN[hari.month - 1]} {hari.year}</p></section>'
                f'<section class="isi"><h2>Isi</h2><ol>{daftar}</ol></section>')
    font = (AKAR / "branding" / "fonts" / "fonts.css").as_uri()
    return (f'<!doctype html><html lang="id"><head><meta charset="utf-8"><title>{html.escape(berkas.judul)}</title>'
            f'<style>{GAYA.format(font=font)}</style></head><body>{awal}{"".join(bagian)}</body></html>')


# ---------------------------------------------------------------------------------------------
# 4. HTML -> PDF
# ---------------------------------------------------------------------------------------------
def cetak(daftar: list[Berkas]) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        peramban = pw.chromium.launch(executable_path=os.environ.get("ALDX_CHROMIUM") or None)
        laman = peramban.new_page(viewport={"width": 658, "height": 900})   # lebar isi A4 (174 mm) agar ukur blok kode tepat
        for b in daftar:
            sementara = Path(tmp) / "laman.html"
            sementara.write_text(halaman_html(b), encoding="utf-8")
            laman.goto(sementara.as_uri(), wait_until="networkidle")
            laman.evaluate("document.fonts.ready")
            laman.emulate_media(media="print")
            laman.evaluate(PAS_KODE)
            tujuan = KELUAR / b.keluar
            tujuan.parent.mkdir(parents=True, exist_ok=True)
            laman.pdf(path=str(tujuan), format="A4", print_background=True, display_header_footer=True,
                      header_template="<span></span>", footer_template=KAKI.format(judul=html.escape(b.judul)),
                      margin={"top": "18mm", "bottom": "16mm", "left": "18mm", "right": "18mm"},
                      outline=True, tagged=True)
            _rapikan_metadata(tujuan, b.judul)
            print(f"OK  {b.keluar}")
        peramban.close()


def _rapikan_metadata(pdf: Path, judul: str) -> None:
    """Judul & pembuat PDF = ALDx (bukan nama alat cetak)."""
    import logging
    from pypdf import PdfReader, PdfWriter

    logging.getLogger("pypdf").setLevel(logging.ERROR)     # peringatan trailer PDF bertag Chromium: tidak berbahaya

    tulis = PdfWriter(clone_from=PdfReader(pdf))
    tulis.add_metadata({"/Title": judul, "/Author": "ALDx", "/Creator": "ALDx", "/Producer": "ALDx"})
    with pdf.open("wb") as f:
        tulis.write(f)


def main() -> None:
    p = argparse.ArgumentParser(description="Buat ulang PDF dokumentasi ALDx dari Markdown.")
    p.add_argument("--hanya", choices=["dokumen", "manual", "tutorial", "bahan-ajar", "uji", "runbook"])
    a = p.parse_args()
    daftar = [b for b in daftar_berkas() if not a.hanya or b.kelompok == a.hanya]
    cetak(daftar)
    print(f"{len(daftar)} PDF selesai di {KELUAR}")


if __name__ == "__main__":
    main()
