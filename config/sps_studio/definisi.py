"""Ukuran & dimensi TERDEFINISI di Studio (padanan "New measure" / "New column" Power BI).

    Ukuran  = rumus AGREGAT atas kolom dataset, mis.  SUM(laba) / SUM(penjualan)
              -> metrik tersimpan dataset (SqlMetric). Dihitung ulang di setiap tingkat pengelompokan,
                 jadi rasio tetap benar per cabang, per bulan, maupun total (seperti measure DAX).
    Dimensi = rumus PER BARIS, mis.  CASE WHEN penjualan >= 1000000 THEN 'Besar' ELSE 'Kecil' END
              -> kolom hitung dataset (TableColumn.expression). Bisa dipakai di rak, filter, hierarki.

Keduanya milik DATASET: langsung tersedia untuk semua chart, dashboard, Explore, dan pengguna dataset itu,
dan tetap tunduk pada hak akses & RLS dataset (rumus hanya dijalankan di dalam kueri dataset).

Pengaman:
    - rumus diperiksa sqlglot: tanpa subquery, perintah SQL, komentar, tabel lain, atau kolom yang tidak ada;
    - ukuran wajib berisi fungsi agregat; dimensi tidak boleh berisi agregat / fungsi jendela;
    - rumus DIUJI ke database sumber (1 baris) sebelum disimpan: rumus salah tidak pernah tersimpan;
    - hanya definisi buatan Studio (bertanda aldx_definisi) yang bisa diubah/dihapus dari sini;
      kolom asli & metrik lain tidak tersentuh. Definisi yang dipakai chart tidak bisa dihapus.

    POST /studio/api/definisi/<dataset_id>/uji     {jenis, rumus}
    POST /studio/api/definisi/<dataset_id>         {jenis: "ukuran"|"dimensi", nama, rumus, format, keterangan, lama}
    POST /studio/api/definisi/<dataset_id>/hapus   {jenis, nama}
"""

from __future__ import annotations

import json
import re

import sqlglot
from sqlglot import exp

from sps_ai import alat

TANDA = "aldx_definisi"
_NAMA = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,59}$")
FORMAT = {"angka": "SMART_NUMBER", "ribuan": ",.0f", "desimal": ",.2f", "persen": ".1%", "rupiah": "$,.0f"}
_DILARANG = (exp.Subquery, exp.Select, exp.Union, exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
             exp.Command, exp.Alter)
MAKS_RUMUS = 2000


def _boleh_ubah() -> None:
    from superset import security_manager
    if not security_manager.can_access("can_write", "Dataset"):
        raise alat.IzinDitolak("Membuat ukuran/dimensi butuh izin mengubah dataset (role Alpha/Admin).")


def periksa(t, jenis: str, rumus: str) -> str:
    """Validasi bentuk rumus. Kembalikan rumus bersih atau InputSalah berbahasa pengguna."""
    rumus = str(rumus or "").strip()
    if not rumus:
        raise alat.InputSalah("Rumus masih kosong.")
    if len(rumus) > MAKS_RUMUS or ";" in rumus or "--" in rumus or "/*" in rumus:
        raise alat.InputSalah("Rumus terlalu panjang atau berisi ';' / komentar SQL.")
    try:
        pohon = sqlglot.parse_one(rumus)
    except sqlglot.errors.SqlglotError as exc:
        raise alat.InputSalah(f"Rumus tidak bisa dibaca: {str(exc).splitlines()[0][:160]}") from exc
    if pohon is None or isinstance(pohon, _DILARANG) or any(isinstance(n, _DILARANG) for n in pohon.walk()):
        raise alat.InputSalah("Rumus tidak boleh berisi subquery atau perintah SQL.")
    ada = {c.column_name.lower() for c in t.columns}
    for c in pohon.find_all(exp.Column):
        if c.table:
            raise alat.InputSalah("Rumus tidak boleh merujuk tabel lain.")
        if c.name.lower() not in ada:
            raise alat.InputSalah(f"Kolom '{c.name}' tidak ada di dataset. Klik nama kolom di daftar untuk menyisipkan.")
    agregat = pohon.find(exp.AggFunc) is not None
    if jenis == "ukuran" and not agregat:
        raise alat.InputSalah("Ukuran harus memakai fungsi agregat, mis. SUM(penjualan), AVG(harga), "
                              "COUNT(DISTINCT id), atau SUM(laba) / SUM(penjualan).")
    if jenis == "dimensi" and (agregat or pohon.find(exp.Window) is not None):
        raise alat.InputSalah("Dimensi dihitung per baris, jadi tidak boleh memakai SUM/AVG/COUNT. "
                              "Untuk hasil penjumlahan buat Ukuran.")
    if jenis not in ("ukuran", "dimensi"):
        raise alat.InputSalah("Jenis harus 'ukuran' atau 'dimensi'.")
    return rumus


def uji(t, jenis: str, rumus: str) -> dict:
    """Jalankan rumus ke sumber (sebagai pengguna, RLS berlaku). Kembalikan contoh hasil."""
    rumus = periksa(t, jenis, rumus)
    adhoc = {"expressionType": "SQL", "sqlExpression": rumus, "label": "hasil"}
    try:
        hasil = (alat.jalankan_objek(t, [adhoc], [], [], [], 1) if jenis == "ukuran"
                 else alat.jalankan_objek(t, [], [adhoc], [], [], 5))
    except (alat.IzinDitolak, alat.InputSalah):
        raise
    except Exception as exc:  # noqa: BLE001 - galat database sumber -> pesan untuk pengguna
        from superset import db
        db.session.rollback()
        raise alat.InputSalah(f"Rumus ditolak database: {str(exc).splitlines()[0][:220]}") from exc
    contoh = [b.get("hasil") for b in hasil["baris"]][:5]
    return {"contoh": contoh, "tipe": _tipe(contoh)}


def _tipe(contoh: list) -> str:
    isi = [v for v in contoh if v is not None]
    if isi and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in isi):
        return "angka"
    if isi and all(isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}", v) for v in isi):
        return "tanggal"
    return "teks"


def _tanda(objek) -> bool:
    try:
        return bool(json.loads(objek.extra or "{}").get(TANDA))
    except (TypeError, ValueError):
        return False


def _dipakai(t, nama: str) -> list[str]:
    """Judul chart dataset ini yang menyebut nama definisi (di params)."""
    from superset import db
    from superset.models.slice import Slice
    pola = f'"{nama}"'
    return [c.slice_name for c in db.session.query(Slice).filter_by(datasource_type="table", datasource_id=t.id)
            if pola in (c.params or "")][:10]


def simpan(dataset_id: int, d: dict) -> dict:
    from superset import db
    from superset.connectors.sqla.models import SqlMetric, TableColumn
    _boleh_ubah()
    t = alat._dataset(dataset_id)
    jenis, nama = str(d.get("jenis") or ""), str(d.get("nama") or "").strip()
    if not _NAMA.match(nama):
        raise alat.InputSalah("Nama: huruf/angka/garis bawah, diawali huruf, maks. 60 karakter (mis. margin_persen).")
    hasil = uji(t, jenis, d.get("rumus"))                        # validasi + uji ke sumber
    rumus = str(d.get("rumus")).strip()
    lama = str(d.get("lama") or "")                              # nama sebelum diubah (mode ubah)
    kolom = {c.column_name.lower(): c for c in t.columns}
    metrik = {m.metric_name.lower(): m for m in t.metrics}
    bentrok = kolom.get(nama.lower()) or metrik.get(nama.lower())
    sasaran = (metrik if jenis == "ukuran" else kolom).get(lama.lower()) if lama else None
    if sasaran is not None and not _tanda(sasaran):
        raise alat.InputSalah(f"'{lama}' bukan definisi buatan Studio; ubah lewat Dataset › Edit.")
    if bentrok is not None and bentrok is not sasaran:
        raise alat.InputSalah(f"Nama '{nama}' sudah dipakai kolom/ukuran lain di dataset ini.")
    if sasaran is not None and lama != nama and _dipakai(t, lama):
        raise alat.InputSalah(f"'{lama}' dipakai chart ({', '.join(_dipakai(t, lama)[:3])}); ganti rumus boleh, ganti nama tidak.")
    ket = str(d.get("keterangan") or "")[:500]
    extra = json.dumps({TANDA: True})
    if jenis == "ukuran":
        m = sasaran or SqlMetric(table=t)
        m.metric_name, m.expression, m.description, m.extra = nama, rumus, ket, extra
        m.verbose_name = str(d.get("label") or "")[:200] or None
        m.d3format = FORMAT.get(str(d.get("format") or "angka"), "SMART_NUMBER")
        db.session.add(m)
    else:
        c = sasaran or TableColumn(table=t)
        c.column_name, c.expression, c.description, c.extra = nama, rumus, ket, extra
        c.verbose_name = str(d.get("label") or "")[:200] or None
        c.type = {"angka": "FLOAT", "tanggal": "DATE"}.get(hasil["tipe"], "STRING")
        c.is_dttm, c.groupby, c.filterable = hasil["tipe"] == "tanggal", True, True
        db.session.add(c)
    db.session.commit()
    return {"nama": nama, "jenis": jenis, **hasil}


def hapus(dataset_id: int, jenis: str, nama: str) -> None:
    from superset import db
    _boleh_ubah()
    t = alat._dataset(dataset_id)
    daftar = t.metrics if jenis == "ukuran" else t.columns
    sasaran = next((x for x in daftar if (x.metric_name if jenis == "ukuran" else x.column_name) == nama), None)
    if sasaran is None or not _tanda(sasaran):
        raise alat.InputSalah(f"'{nama}' bukan definisi buatan Studio.")
    pakai = _dipakai(t, nama)
    if pakai:
        raise alat.InputSalah(f"Masih dipakai {len(pakai)} chart: {', '.join(pakai[:3])}. Lepas dari chart itu dulu.")
    db.session.delete(sasaran)
    db.session.commit()


def info(objek) -> dict:
    """Tambahan untuk panel Data: definisi Studio membawa rumus agar bisa diubah."""
    return {"hitung": True, "rumus": objek.expression} if _tanda(objek) else {}
