"""Ekspor dashboard ke PowerPoint (.pptx) tanpa pustaka tambahan.

Browser memotret setiap chart di dashboard (html-to-image, sama dengan Ekspor PNG) lalu mengirimkannya ke sini;
server menyusun berkas .pptx (format Office Open XML = zip berisi XML) dengan:
    slide 1      judul dashboard, tanggal, filter yang aktif
    slide 2..n   satu chart per slide: judul di atas, gambar di tengah (rasio dijaga)

    POST /pptx/api/buat   {"judul": "...", "keterangan": "...", "slide": [{"judul": "...", "png": "data:image/png;base64,..."}]}
                          -> berkas .pptx (unduhan)

Gambar hanya diterima bila benar PNG/JPEG dan totalnya di bawah batas; teks di-escape (aman untuk XML).
Berkas terbuka di PowerPoint, Google Slides, Keynote, dan LibreOffice Impress.
"""

from __future__ import annotations

import base64
import binascii
import io
import re
import struct
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

from flask import Blueprint, Response, jsonify, request

bp = Blueprint("sps_pptx", __name__, url_prefix="/pptx")
LEBAR, TINGGI = 12192000, 6858000          # 16:9 dalam EMU (1 cm = 360000 EMU)
TEPI = 457200                              # 1,27 cm
MAKS_SLIDE = 60
MAKS_BYTE = 40 * 1024 * 1024               # total gambar
_PNG, _JPG = b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"

NS_P = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ' \
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ' \
       'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


class GambarSalah(ValueError):
    pass


def _ukuran_gambar(isi: bytes) -> tuple[str, int, int]:
    """(ekstensi, lebar px, tinggi px) dari kepala PNG/JPEG."""
    if isi.startswith(_PNG):
        w, h = struct.unpack(">II", isi[16:24])
        return "png", w, h
    if isi.startswith(_JPG):
        i = 2
        while i < len(isi) - 9:
            if isi[i] != 0xFF:
                i += 1
                continue
            penanda, panjang = isi[i + 1], struct.unpack(">H", isi[i + 2:i + 4])[0]
            if penanda in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", isi[i + 5:i + 9])
                return "jpeg", w, h
            i += 2 + panjang
    raise GambarSalah("Gambar harus PNG atau JPEG.")


def dekode(data_url: str) -> bytes:
    try:
        return base64.b64decode(str(data_url).split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise GambarSalah("Gambar tidak terbaca.") from None


def _teks(id_, nama, x, y, w, h, teks, ukuran, tebal=False, warna="1F2933", rata="l") -> str:
    baris = "".join(f'<a:p><a:pPr algn="{rata}"/><a:r><a:rPr lang="id-ID" sz="{ukuran}" b="{int(tebal)}" dirty="0">'
                    f'<a:solidFill><a:srgbClr val="{warna}"/></a:solidFill></a:rPr><a:t>{escape(b)}</a:t></a:r></a:p>'
                    for b in str(teks).split("\n")) or '<a:p><a:endParaRPr lang="id-ID"/></a:p>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{id_}" name="{nama}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'<a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" anchor="t"><a:normAutofit/></a:bodyPr><a:lstStyle/>{baris}</p:txBody></p:sp>')


def _gambar(id_, rid, x, y, w, h, alt) -> str:
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{id_}" name="Chart" descr="{escape(alt, {chr(34): "&quot;"})}"/>'
            f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def _slide(isi: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld {NS_P}><p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            f'{isi}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


def _rels(daftar: list[tuple[str, str, str]]) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">' +
            "".join(f'<Relationship Id="{i}" Type="{REL}/{t}" Target="{g}"/>' for i, t, g in daftar) + "</Relationships>")


TEMA = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="ALDx"><a:themeElements>'
        '<a:clrScheme name="ALDx"><a:dk1><a:srgbClr val="1F2933"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="1F4E79"/></a:dk2><a:lt2><a:srgbClr val="F4F6F9"/></a:lt2>'
        + "".join(f'<a:accent{i}><a:srgbClr val="{w}"/></a:accent{i}>' for i, w in
                  enumerate(("E11D74", "1F4E79", "0F9488", "F2A900", "8B47C9", "5F6B7A"), 1)) +
        '<a:hlink><a:srgbClr val="1F4E79"/></a:hlink><a:folHlink><a:srgbClr val="8B47C9"/></a:folHlink></a:clrScheme>'
        '<a:fontScheme name="ALDx"><a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
        '<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="ALDx"><a:fillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
        '</a:fillStyleLst><a:lnStyleLst>' + '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3 +
        '</a:lnStyleLst><a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 +
        '</a:effectStyleLst><a:bgFillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
        '</a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')

KOSONG_TREE = ('<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
               '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
               '</p:grpSpPr></p:spTree></p:cSld>')
MASTER = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster {NS_P}>{KOSONG_TREE}'
          '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
          'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
          '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
          '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>')
_TREE_LAYOUT = KOSONG_TREE.replace("<p:cSld>", '<p:cSld name="Kosong">')
LAYOUT = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout {NS_P} type="blank" preserve="1">'
          f'{_TREE_LAYOUT}<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')


def buat(judul: str, keterangan: str, slide: list[dict], sekarang: datetime | None = None) -> bytes:
    """slide: [{"judul": str, "gambar": bytes}] -> isi berkas .pptx."""
    if not slide:
        raise GambarSalah("Tidak ada chart untuk diekspor.")
    if len(slide) > MAKS_SLIDE:
        raise GambarSalah(f"Maksimal {MAKS_SLIDE} chart per ekspor.")
    if sum(len(s["gambar"]) for s in slide) > MAKS_BYTE:
        raise GambarSalah("Gambar terlalu besar untuk satu berkas. Ekspor per tab.")
    waktu = (sekarang or datetime.now()).strftime("%d-%m-%Y %H:%M")
    jenis_media, isi_slide, berkas = set(), [], {}

    sampul = (f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="1F4E79"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>')
    isi_slide.append(_slide(
        _teks(2, "Judul", TEPI * 2, TINGGI // 3, LEBAR - TEPI * 4, 1400000, judul or "Dashboard", 4000, True, "FFFFFF") +
        _teks(3, "Keterangan", TEPI * 2, TINGGI // 3 + 1500000, LEBAR - TEPI * 4, 1600000,
              f"{keterangan}\nDiekspor {waktu}".strip(), 1600, False, "DCE6F0")).replace("<p:cSld>", f"<p:cSld>{sampul}"))
    rels_slide = [[("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]]

    tinggi_judul = 700000
    for n, s in enumerate(slide, 1):
        ext, w, h = _ukuran_gambar(s["gambar"])
        jenis_media.add(ext)
        nama = f"gambar{n}.{ext}"
        berkas[f"ppt/media/{nama}"] = s["gambar"]
        ruang_w, ruang_h = LEBAR - 2 * TEPI, TINGGI - 2 * TEPI - tinggi_judul
        skala = min(ruang_w / max(w, 1), ruang_h / max(h, 1))
        gw, gh = int(w * skala), int(h * skala)
        x, y = (LEBAR - gw) // 2, TEPI + tinggi_judul + (ruang_h - gh) // 2
        isi_slide.append(_slide(_teks(2, "Judul", TEPI, TEPI // 2, LEBAR - 2 * TEPI, tinggi_judul, s["judul"] or f"Chart {n}", 2400, True) +
                                _gambar(3, "rId2", x, y, gw, gh, s["judul"] or "Chart")))
        rels_slide.append([("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "image", f"../media/{nama}")])

    n_slide = len(isi_slide)
    tipe = {"png": "image/png", "jpeg": "image/jpeg"}
    berkas["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>' +
        "".join(f'<Default Extension="{e}" ContentType="{tipe[e]}"/>' for e in sorted(jenis_media)) +
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
        "".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                for i in range(1, n_slide + 1)) + "</Types>")
    berkas["_rels/.rels"] = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
        f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="ppt/presentation.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        f'<Relationship Id="rId3" Type="{REL}/extended-properties" Target="docProps/app.xml"/></Relationships>')
    berkas["docProps/core.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>{escape(judul or "Dashboard")}</dc:title><dc:creator>ALDx</dc:creator></cp:coreProperties>')
    berkas["docProps/app.xml"] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties '
                                  'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                                  f'<Application>ALDx</Application><Slides>{n_slide}</Slides></Properties>')
    berkas["ppt/presentation.xml"] = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation {NS_P} saveSubsetFonts="1">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>' +
        "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 2}"/>' for i in range(1, n_slide + 1)) +
        f'</p:sldIdLst><p:sldSz cx="{LEBAR}" cy="{TINGGI}"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    berkas["ppt/_rels/presentation.xml.rels"] = _rels(
        [("rId1", "slideMaster", "slideMasters/slideMaster1.xml"), ("rId2", "theme", "theme/theme1.xml")] +
        [(f"rId{i + 2}", "slide", f"slides/slide{i}.xml") for i in range(1, n_slide + 1)])
    berkas["ppt/slideMasters/slideMaster1.xml"] = MASTER
    berkas["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = _rels(
        [("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "theme", "../theme/theme1.xml")])
    berkas["ppt/slideLayouts/slideLayout1.xml"] = LAYOUT
    berkas["ppt/slideLayouts/_rels/slideLayout1.xml.rels"] = _rels([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")])
    berkas["ppt/theme/theme1.xml"] = TEMA
    for i, (xml, rel) in enumerate(zip(isi_slide, rels_slide), 1):
        berkas[f"ppt/slides/slide{i}.xml"] = xml
        berkas[f"ppt/slides/_rels/slide{i}.xml.rels"] = _rels(rel)

    keluar = io.BytesIO()
    with zipfile.ZipFile(keluar, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", berkas.pop("[Content_Types].xml"))     # wajib pertama
        for nama, isi in berkas.items():
            z.writestr(nama, isi, compress_type=zipfile.ZIP_STORED if nama.startswith("ppt/media/") else zipfile.ZIP_DEFLATED)
    return keluar.getvalue()


def nama_berkas(judul: str) -> str:
    dasar = re.sub(r"[^\w\- ]+", "", judul or "dashboard").strip().replace(" ", "-")[:80] or "dashboard"
    return f"{dasar}.pptx"


@bp.route("/api/buat", methods=["POST"])
def api_buat():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return jsonify(error="Silakan login"), 401
    d = request.get_json(silent=True) or {}
    try:
        slide = [{"judul": str(s.get("judul") or "")[:200], "gambar": dekode(s.get("png") or "")} for s in (d.get("slide") or [])]
        isi = buat(str(d.get("judul") or "")[:200], str(d.get("keterangan") or "")[:600], slide)
    except GambarSalah as e:
        return jsonify(error=str(e)), 400
    r = Response(isi, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    r.headers["Content-Disposition"] = f'attachment; filename="{nama_berkas(d.get("judul") or "")}"'
    return r


def daftarkan(app) -> None:
    app.register_blueprint(bp)
