"""Persiapan data: alur langkah -> dataset virtual Superset.

Alur:  dataset asal -> langkah 1 -> langkah 2 -> ... -> dataset baru

Langkah yang tersedia (JSON dari browser):
    {"jenis": "pilih",      "kolom": ["a", "b"]}                     pilih/buang kolom
    {"jenis": "ganti_nama", "dari": "a", "ke": "a_baru"}
    {"jenis": "ubah_tipe",  "kolom": "a", "tipe": "teks|angka|tanggal"}
    {"jenis": "bersihkan",  "kolom": "a", "aksi": "trim|besar|kecil|isi_kosong", "nilai": "0"}
    {"jenis": "filter",     "kolom": "a", "op": "==", "nilai": ...}
    {"jenis": "hitung",     "nama": "rasio", "rumus": "total / jumlah_transaksi"}
    {"jenis": "agregasi",   "kelompok": ["a"], "ukuran": [{"kolom": "b", "agg": "SUM"}]}
    {"jenis": "gabung",     "dataset_id": 7, "tipe": "inner|left",
                            "kunci": [{"kiri": "kd_cabang", "kanan": "KD_CABANG"}], "kolom": ["NM_CABANG"]}

Setiap langkah membungkus hasil langkah sebelumnya sebagai subquery dan disusun
dengan SQLAlchemy, sehingga SQL-nya otomatis cocok untuk Oracle, ClickHouse, MySQL.

KEAMANAN
    - Pratinjau memakai SQL dataset asal YANG SUDAH difilter hak akses user (RLS).
    - Dataset baru mewarisi aturan hak akses {{ sps_akses(...) }} dataset asal; kolom hak
      akses (mis. KD_CABANG) wajib tetap ada dan tidak diubah, kalau tidak penyimpanan ditolak.
    - Rumus kolom hitung diperiksa sqlglot: tanpa subquery / perintah SQL / kolom asing.
    - Gabung (join): dataset kanan harus boleh diakses user & di database yang sama. Dataset baru
      memakai hak akses KEDUA sisi (AND); untuk left join, baris kanan yang kosong tetap boleh
      (tidak membawa data). Hanya role yang boleh memakai SEMUA dataset asal yang diberi akses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlalchemy import Date, Float, String, and_, cast, column, func, literal, literal_column, select, text
from sqlglot import exp

from sps_ai import alat

NAMA_SAH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,29}$")       # 30 karakter: batas Oracle lama
AGREGAT = {"SUM": func.sum, "AVG": func.avg, "MIN": func.min, "MAX": func.max, "COUNT": func.count}
TIPE = {"teks": String(255), "angka": Float(), "tanggal": Date()}
BERSIH = {"trim": func.trim, "besar": func.upper, "kecil": func.lower}
OP = {"==": lambda c, v: c == v, "!=": lambda c, v: c != v, ">": lambda c, v: c > v, "<": lambda c, v: c < v,
      ">=": lambda c, v: c >= v, "<=": lambda c, v: c <= v, "IN": lambda c, v: c.in_(v),
      "NOT IN": lambda c, v: c.not_in(v), "LIKE": lambda c, v: c.like(v),
      "KOSONG": lambda c, v: c.is_(None), "TIDAK KOSONG": lambda c, v: c.isnot(None)}
DILARANG = (exp.Select, exp.Subquery, exp.Union, exp.Insert, exp.Update, exp.Delete,
            exp.Drop, exp.Create, exp.Command, exp.Table)
POLA_AKSES = re.compile(r"(\w+)\s*=\s*'([^']*)'")
BARIS_PRATINJAU = 500


@dataclass
class Alur:
    """Hasil penerapan langkah: SELECT akhir + asal tiap kolom (untuk warisan hak akses)."""
    query: Any
    kolom: list[str]
    asal: dict[str, str | None] = field(default_factory=dict)   # kolom keluaran -> kolom asal (None = turunan)
    # per langkah gabung: (dataset kanan, tipe join, {kolom kunci kanan (huruf kecil): asal kolom kunci kiri})
    gabung: list[tuple[int, str, dict]] = field(default_factory=list)


def asal_kanan(dataset_id: int, kolom: str) -> str:
    """Penanda asal kolom dari dataset kanan, mis. '#7:KD_CABANG'."""
    return f"#{dataset_id}:{kolom}"


def _nama(n: str) -> str:
    n = str(n or "").strip()
    if not NAMA_SAH.match(n):
        raise alat.InputSalah(f"Nama kolom '{n}' tidak sah (huruf/angka/_, maks. 30, diawali huruf).")
    return n


def _cari(kolom: list[str], nama: str) -> str:
    """Nama kolom sesuai huruf besar/kecil aslinya; galat bila tidak ada."""
    for k in kolom:
        if k.lower() == str(nama).lower():
            return k
    raise alat.InputSalah(f"Kolom '{nama}' tidak ada pada langkah ini.")


def periksa_rumus(rumus: str, kolom: list[str]) -> str:
    """Rumus kolom hitung harus ekspresi sederhana atas kolom yang ada."""
    if ";" in rumus or "--" in rumus or "/*" in rumus:
        raise alat.InputSalah("Rumus tidak boleh berisi ';' atau komentar SQL.")
    try:
        pohon = sqlglot.parse_one(rumus)
    except sqlglot.errors.ParseError as exc:
        raise alat.InputSalah(f"Rumus tidak bisa dibaca: {exc}".split("\n")[0]) from exc
    if isinstance(pohon, DILARANG) or any(isinstance(n, DILARANG) for n in pohon.walk()):
        raise alat.InputSalah("Rumus tidak boleh berisi subquery atau perintah SQL.")
    for c in pohon.find_all(exp.Column):
        if c.table:
            raise alat.InputSalah("Rumus tidak boleh merujuk tabel lain.")
        _cari(kolom, c.name)
    return rumus


def terapkan(dasar, kolom_dasar: list[str], langkah: list[dict], sumber=None) -> Alur:
    """Susun SELECT dari `dasar` (FROM-clause) dengan menerapkan langkah satu per satu.

    sumber(dataset_id, alias) -> (FROM-clause, kolom): dataset kanan untuk langkah gabung.
    """
    alur = Alur(select(*[dasar.c[k] for k in kolom_dasar]), list(kolom_dasar), {k: k for k in kolom_dasar})
    for i, l in enumerate(langkah, 1):
        try:
            alur = _satu_langkah(alur, l, i, sumber)
        except alat.InputSalah as exc:
            raise alat.InputSalah(f"Langkah {i} ({l.get('jenis')}): {exc}") from exc
    return alur


def _satu_langkah(alur: Alur, l: dict, i: int, sumber=None) -> Alur:
    s = alur.query.subquery(f"l{i}")
    kolom, asal = alur.kolom, dict(alur.asal)
    jenis = l.get("jenis")

    def lanjut(query, kolom_baru, asal_baru):
        return Alur(query, kolom_baru, asal_baru, list(alur.gabung))

    if jenis == "pilih":
        pilih = [_cari(kolom, k) for k in l.get("kolom") or []]
        if not pilih:
            raise alat.InputSalah("Pilih minimal satu kolom.")
        return lanjut(select(*[s.c[k] for k in pilih]), pilih, {k: asal[k] for k in pilih})

    if jenis == "ganti_nama":
        dari, ke = _cari(kolom, l.get("dari")), _nama(l.get("ke"))
        if ke.lower() in {k.lower() for k in kolom if k != dari}:
            raise alat.InputSalah(f"Kolom '{ke}' sudah ada.")
        baru = [ke if k == dari else k for k in kolom]
        asal[ke] = asal.pop(dari)
        return lanjut(select(*[s.c[k].label(ke) if k == dari else s.c[k] for k in kolom]), baru, asal)

    if jenis in ("ubah_tipe", "bersihkan"):
        k = _cari(kolom, l.get("kolom"))
        if jenis == "ubah_tipe":
            if l.get("tipe") not in TIPE:
                raise alat.InputSalah(f"Tipe harus salah satu: {', '.join(TIPE)}.")
            ekspr = cast(s.c[k], TIPE[l["tipe"]])
        elif l.get("aksi") == "isi_kosong":
            ekspr = func.coalesce(s.c[k], literal(l.get("nilai", "")))
        elif l.get("aksi") in BERSIH:
            ekspr = BERSIH[l["aksi"]](s.c[k])
        else:
            raise alat.InputSalah(f"Aksi bersihkan harus: {', '.join([*BERSIH, 'isi_kosong'])}.")
        asal[k] = None                                       # nilai berubah -> bukan kolom asli lagi
        return lanjut(select(*[ekspr.label(k) if x == k else s.c[x] for x in kolom]), kolom, asal)

    if jenis == "filter":
        k, op = _cari(kolom, l.get("kolom")), str(l.get("op", "==")).upper()
        if op not in OP:
            raise alat.InputSalah(f"Operator '{op}' tidak dikenal.")
        nilai = l.get("nilai")
        if op in ("IN", "NOT IN") and not isinstance(nilai, list):
            nilai = [v.strip() for v in str(nilai).split(",") if v.strip()]
        return lanjut(select(*[s.c[x] for x in kolom]).where(OP[op](s.c[k], nilai)), kolom, asal)

    if jenis == "hitung":
        nama = _nama(l.get("nama"))
        if nama.lower() in {k.lower() for k in kolom}:
            raise alat.InputSalah(f"Kolom '{nama}' sudah ada.")
        rumus = periksa_rumus(str(l.get("rumus") or ""), kolom)
        dari_sub = select(*[s.c[x] for x in kolom], literal_column(rumus).label(nama)).select_from(s)
        asal[nama] = None
        return lanjut(dari_sub, kolom + [nama], asal)

    if jenis == "agregasi":
        kelompok = [_cari(kolom, k) for k in l.get("kelompok") or []]
        ukuran = []
        for u in l.get("ukuran") or []:
            k, agg = _cari(kolom, u.get("kolom")), str(u.get("agg", "SUM")).upper()
            if agg not in AGREGAT:
                raise alat.InputSalah(f"Agregasi '{agg}' tidak dikenal.")
            ukuran.append((AGREGAT[agg](s.c[k]).label(_nama(f"{agg}_{k}"[:30])), f"{agg}_{k}"[:30]))
        if not ukuran:
            raise alat.InputSalah("Agregasi butuh minimal satu ukuran.")
        q = select(*[s.c[k] for k in kelompok], *[u for u, _ in ukuran]).group_by(*[s.c[k] for k in kelompok])
        hasil = kelompok + [n for _, n in ukuran]
        return lanjut(q, hasil, {**{k: asal[k] for k in kelompok}, **{n: None for _, n in ukuran}})

    if jenis == "gabung":
        return _gabung(s, kolom, asal, l, i, sumber, alur.gabung)

    raise alat.InputSalah(f"Jenis langkah '{jenis}' tidak dikenal.")


def _gabung(s, kolom: list[str], asal: dict, l: dict, i: int, sumber, gabung_lama: list) -> Alur:
    """JOIN dengan dataset lain (kanan). Kolom kanan yang namanya bentrok diberi akhiran _2."""
    if sumber is None:
        raise alat.InputSalah("Gabung tidak tersedia di sini.")
    tipe = str(l.get("tipe") or "inner").lower()
    if tipe not in ("inner", "left"):
        raise alat.InputSalah("Tipe gabung harus 'inner' atau 'left'.")
    id_kanan = int(l.get("dataset_id") or 0)
    dari_kanan, kolom_kanan = sumber(id_kanan, f"g{i}")
    kunci = [(_cari(kolom, k.get("kiri")), _cari(kolom_kanan, k.get("kanan"))) for k in l.get("kunci") or []]
    if not kunci:
        raise alat.InputSalah("Tentukan minimal satu pasangan kolom kunci.")
    ambil = [_cari(kolom_kanan, k) for k in (l.get("kolom") or [])] or \
        [k for k in kolom_kanan if k not in {kn for _, kn in kunci}]
    terpakai = {k.lower() for k in kolom}
    pilihan, label = [], []
    for k in ambil:
        n = k if k.lower() not in terpakai else _nama(f"{k}_2"[:30])
        if n.lower() in terpakai:
            raise alat.InputSalah(f"Nama kolom '{n}' bentrok; ganti nama dulu.")
        terpakai.add(n.lower())
        pilihan.append(dari_kanan.c[k].label(n))
        label.append(n)
        asal[n] = asal_kanan(id_kanan, k)
    syarat = and_(*[s.c[ki] == dari_kanan.c[ka] for ki, ka in kunci])
    q = select(*[s.c[k] for k in kolom], *pilihan).select_from(s.join(dari_kanan, syarat, isouter=tipe == "left"))
    pasangan = {ka.lower(): asal.get(ki) for ki, ka in kunci if asal.get(ki)}
    return Alur(q, kolom + label, asal, [*gabung_lama, (id_kanan, tipe, pasangan)])


# --- SQL dataset asal ----------------------------------------------------------------------
def _kolom_dataset(t) -> list[str]:
    return [c.column_name for c in t.columns if c.is_active is not False and not c.expression]


def _dasar_rls(t, kolom: list[str], alias: str = "dasar"):
    """SQL dataset + filter hak akses USER SAAT INI (untuk pratinjau)."""
    q = t.get_sqla_query(columns=kolom, is_timeseries=False, metrics=[], filter=[], extras={},
                         row_limit=None, groupby=None)
    sql = t.database.compile_sqla_query(q.sqla_query, catalog=t.catalog, schema=t.schema)
    return text(sql.replace(":", r"\:")).columns(*[column(k) for k in kolom]).subquery(alias)


def _dasar_mentah(t, kolom: list[str], alias: str = "dasar"):
    """Sumber dataset TANPA filter user (untuk disimpan; hak akses dipasang sebagai RLS)."""
    if t.sql:
        return text(t.sql.replace(":", r"\:")).columns(*[column(k) for k in kolom]).subquery(alias)
    from sqlalchemy import table
    return table(t.table_name, *[column(k) for k in kolom], schema=t.schema or None).alias(alias)


def _pembuat_sumber(t, pakai_rls: bool):
    """Fungsi penyedia dataset kanan untuk langkah gabung (cek akses & database sama)."""
    def sumber(dataset_id: int, alias: str):
        kanan = alat._dataset(dataset_id)
        if kanan.database_id != t.database_id:
            raise alat.InputSalah(f"Dataset '{kanan.table_name}' ada di database lain; gabung hanya "
                                  "bisa antar-dataset di database yang sama.")
        kolom = _kolom_dataset(kanan)
        return (_dasar_rls if pakai_rls else _dasar_mentah)(kanan, kolom, alias), kolom
    return sumber


def _sql(t, query) -> str:
    return str(query.compile(dialect=t.database.get_dialect(), compile_kwargs={"literal_binds": True}))


def _susun(t, langkah: list[dict], pakai_rls: bool) -> Alur:
    kolom = _kolom_dataset(t)
    dasar = (_dasar_rls if pakai_rls else _dasar_mentah)(t, kolom)
    return terapkan(dasar, kolom, langkah, _pembuat_sumber(t, pakai_rls))


def pratinjau(dataset_id: int, langkah: list[dict]) -> dict:
    """Jalankan alur atas data yang boleh dilihat user; kembalikan contoh baris + SQL."""
    t = alat._dataset(dataset_id)
    alur = _susun(t, langkah, pakai_rls=True)
    df = t.database.get_df(_sql(t, alur.query.limit(BARIS_PRATINJAU)), catalog=t.catalog, schema=t.schema)
    df = df.astype(object).where(df.notna(), None)
    return {"kolom": alur.kolom, "baris": df.to_dict(orient="records"),
            "asal": alur.asal, "sql": _sql(t, _susun(t, langkah, pakai_rls=False).query)}


# --- Simpan sebagai dataset baru ------------------------------------------------------------
def _aturan_akses(t) -> dict[str, str] | None:
    """Pemetaan {{ sps_akses(...) }} sebuah dataset (atribut -> kolom). None = tanpa RLS."""
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter

    aturan = [r for r in db.session.query(RowLevelSecurityFilter).all() if t in r.tables]
    if not aturan:
        return None
    if any("sps_akses" not in (r.clause or "") for r in aturan):
        raise alat.InputSalah(f"Dataset '{t.table_name}' memakai aturan hak akses khusus; "
                              "minta Admin menyiapkan dataset ini.")
    peta: dict[str, str] = {}
    for r in aturan:
        peta.update(dict(POLA_AKSES.findall(r.clause)))
    return peta


def _petakan(t, peta: dict[str, str], asal: dict, penanda, pasangan: dict | None = None) -> dict[str, str]:
    """Kolom hak akses dataset t -> nama kolom di hasil. Galat bila dibuang/diubah.

    pasangan: untuk dataset kanan, kolom kunci gabung -> asal kolom kiri pasangannya. Bila kolom
    hak akses kanan adalah kunci gabung, nilainya SAMA dengan kolom kiri, jadi kolom kiri dipakai.
    """
    balik = {a.lower(): k for k, a in asal.items() if a}
    hasil = {}
    for atribut, kolom_asal in peta.items():
        kunci = penanda(kolom_asal).lower()
        kiri = (pasangan or {}).get(kolom_asal.lower())
        if kunci not in balik and kiri and kiri.lower() in balik:
            kunci = kiri.lower()
        if kunci not in balik:
            raise alat.InputSalah(
                f"Kolom hak akses '{kolom_asal}' ({atribut}) dari '{t.table_name}' harus tetap ada & "
                "tidak diubah, karena dipakai untuk membatasi data per pegawai.")
        hasil[atribut] = balik[kunci]
    return hasil


def klausa_akses(t, alur: Alur) -> str | None:
    """Klausa RLS dataset baru: hak akses dataset asal AND tiap dataset yang digabung."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable

    from sps_dashboard_builder import rls_clause

    bagian = []
    peta = _aturan_akses(t)
    if peta is not None:
        bagian.append(rls_clause(_petakan(t, peta, alur.asal, lambda k: k)))
    for id_kanan, tipe, pasangan in alur.gabung:
        kanan = db.session.query(SqlaTable).get(id_kanan)
        peta = _aturan_akses(kanan)
        if peta is None:
            continue
        akses = _petakan(kanan, peta, alur.asal, lambda k, i=id_kanan: asal_kanan(i, k), pasangan)
        klausa = rls_clause(akses)
        lewat_kiri = all(not alur.asal.get(k, "").startswith("#") for k in akses.values())
        if lewat_kiri and klausa in bagian:      # sama persis dengan hak akses sisi kiri: tidak perlu diulang
            continue
        if tipe == "left" and not lewat_kiri:    # baris kiri tanpa pasangan: kolom kanan kosong, aman
            klausa = f"({klausa} OR {next(iter(akses.values()))} IS NULL)"
        bagian.append(klausa)
    return " AND ".join(bagian) if bagian else None


def simpan(dataset_id: int, langkah: list[dict], nama: str) -> dict:
    from flask import g
    from superset import db, security_manager
    from superset.connectors.sqla.models import SqlaTable

    if not security_manager.can_access("can_write", "Dataset"):
        raise alat.IzinDitolak("Anda belum punya izin membuat dataset (kemampuan 'Kelola dataset').")
    t = alat._dataset(dataset_id)
    nama = _nama(nama).lower()
    if db.session.query(SqlaTable).filter_by(table_name=nama, database_id=t.database_id).first():
        raise alat.InputSalah(f"Dataset '{nama}' sudah ada; pakai nama lain.")

    alur = _susun(t, langkah, pakai_rls=False)
    klausa = klausa_akses(t, alur)              # galat bila kolom hak akses hilang -> tidak tersimpan

    baru = SqlaTable(table_name=nama, database=t.database, schema=t.schema, sql=_sql(t, alur.query),
                     description=f"Dibuat di Studio (persiapan data) dari '{t.table_name}'.",
                     owners=[g.user] if getattr(g, "user", None) else [])
    db.session.add(baru)
    db.session.flush()
    baru.fetch_metadata()
    if klausa:
        _pasang_rls(baru, klausa)
    asal_semua = [t] + [db.session.query(SqlaTable).get(i) for i, _, _ in alur.gabung]
    _salin_akses(asal_semua, baru)
    db.session.commit()
    return {"id": baru.id, "nama": baru.table_name, "kolom": len(baru.columns),
            "hak_akses": klausa or "tanpa aturan (sama seperti asal)",
            "url": f"/explore/?datasource_type=table&datasource_id={baru.id}"}


def _pasang_rls(table, clause: str) -> None:
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    from superset.utils.core import RowLevelSecurityFilterType

    db.session.add(RowLevelSecurityFilter(
        name=f"akses__{table.table_name}", filter_type=RowLevelSecurityFilterType.BASE,
        description="Diwariskan dari dataset asal oleh Studio (persiapan data).",
        roles=[], tables=[table], clause=clause))


def _salin_akses(asal: list, baru) -> None:
    """Role yang boleh memakai SEMUA dataset asal boleh memakai dataset baru (baris tetap dibatasi RLS)."""
    from superset import security_manager as sm

    pv_asal = [sm.find_permission_view_menu("datasource_access", t.get_perm()) for t in asal]
    pv_baru = sm.add_permission_view_menu("datasource_access", baru.get_perm())
    for role in sm.get_all_roles():
        if all(pv in role.permissions for pv in pv_asal) and pv_baru not in role.permissions:
            sm.add_permission_role(role, pv_baru)
