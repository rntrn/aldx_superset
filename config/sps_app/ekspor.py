"""Ekspor tabel ke Excel (.xlsx) untuk tombol Ekspor di halaman ALDx (static/ekspor.js).

    POST /app/api/ekspor   {"judul": "...", "kolom": [...], "baris": [[...], ...]}  -> berkas .xlsx

Format lain (PNG, PDF, CSV, TXT, salin) dibuat langsung di browser; hanya Excel yang butuh server
agar angka tersimpan sebagai angka (bisa dijumlah di Excel), bukan teks.

Keamanan: endpoint ini hanya mengubah data yang SUDAH tampil di layar pengguna menjadi berkas;
tidak membaca database. Tetap wajib login, dan ukurannya dibatasi BARIS_MAKS.
"""

from __future__ import annotations

import io
import re
from datetime import datetime

from flask import jsonify, request, send_file

BARIS_MAKS = 1_000_000
POLA_ANGKA_ID = re.compile(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$|^-?\d+(,\d+)?$")    # 1.234.567,89
POLA_ANGKA_EN = re.compile(r"^-?\d+(\.\d+)?$")                                   # 1234.5 (nilai mentah)


def angka(nilai):
    """Teks angka berformat Indonesia / mentah -> int/float; selain itu dikembalikan apa adanya."""
    if isinstance(nilai, (int, float)) or nilai is None:
        return nilai
    t = str(nilai).strip().replace(" ", "")
    persen = t.endswith("%")
    t = t.rstrip("%").strip()
    if re.match(r"^-?0\d", t):                     # kode berawalan nol (mis. 007): tetap teks
        return nilai
    if POLA_ANGKA_EN.match(t) and not re.match(r"^-?\d{1,3}\.\d{3}$", t):
        n = float(t)
    elif POLA_ANGKA_ID.match(t):
        n = float(t.replace(".", "").replace(",", "."))
    else:
        return nilai
    n = n / 100 if persen else n
    return int(n) if n.is_integer() and not persen else n


def nama_berkas(judul: str, akhiran: str) -> str:
    dasar = re.sub(r"[^\w\- ]+", "", judul or "data").strip().replace(" ", "_")[:60] or "data"
    return f"{dasar}_{datetime.now():%Y%m%d_%H%M}.{akhiran}"


def buat_xlsx(judul: str, kolom: list, baris: list[list]) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = (re.sub(r"[\[\]:*?/\\]", "", judul) or "Data")[:31]
    ws.append([judul])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Diekspor {datetime.now():%d-%m-%Y %H:%M}"])
    ws["A2"].font = Font(italic=True, color="6A7486")
    ws.append([str(k) for k in kolom])
    for sel in ws[3]:
        sel.font = Font(bold=True, color="FFFFFF")
        sel.fill = PatternFill("solid", fgColor="1E2A44")
        sel.alignment = Alignment(vertical="center")
    lebar = [len(str(k)) for k in kolom]
    for b in baris:
        isi = [angka(v) for v in b]
        ws.append(isi)
        for i, v in enumerate(isi[:len(lebar)]):
            lebar[i] = max(lebar[i], min(60, len(str(v))))
    for i, w in enumerate(lebar, 1):
        ws.column_dimensions[get_column_letter(i)].width = w + 3
    ws.freeze_panes = "A4"
    if kolom:
        ws.auto_filter.ref = f"A3:{get_column_letter(len(kolom))}{3 + len(baris)}"
    keluar = io.BytesIO()
    wb.save(keluar)
    keluar.seek(0)
    return keluar


def api_ekspor():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return jsonify(error="Belum login"), 401
    d = request.get_json(silent=True) or {}
    kolom, baris = d.get("kolom") or [], d.get("baris") or []
    if not isinstance(kolom, list) or not isinstance(baris, list):
        return jsonify(error="Format data tidak sah"), 400
    if len(baris) > BARIS_MAKS:
        return jsonify(error=f"Terlalu banyak baris untuk Excel (maks. {BARIS_MAKS:,})".replace(",", ".")), 400
    judul = str(d.get("judul") or "Data")[:120]
    import sps_audit
    sps_audit.catat("data", "Unduh Excel", judul, {"baris": len(baris)}, oleh=current_user.username)
    return send_file(buat_xlsx(judul, kolom, baris), as_attachment=True, download_name=nama_berkas(judul, "xlsx"),
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
