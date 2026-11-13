"""Gabung beberapa dataset menjadi satu dataset "denormal" (lebar) secara otomatis (alat Asisten AI: gabung_dataset).

Contoh permintaan: "buatkan dataset detail dari latihan_penjualan, latihan_cabang, latihan_lokasi_pelanggan".

Langkah:
    1. cari kolom penghubung antar-dataset: kolom bernama sama yang mirip kunci (kd_, id_, kode, no_, ..._id),
       selain kolom umum (nama, tanggal, total, ...)
    2. periksa hubungan: kunci UNIK di sisi kanan (mis. kd_cabang di latihan_cabang) = aman (banyak-ke-satu).
       Kunci TIDAK unik di kedua sisi = banyak-ke-banyak -> dataset itu DILEWATI, karena baris akan berlipat ganda
       dan semua angka (SUM, COUNT) menjadi salah.
    3. dataset utama = tabel transaksi (kunci tidak unik, baris terbanyak); yang lain LEFT JOIN ke sana
    4. simpan lewat Persiapan data (sps_studio.prep.simpan): hak akses data (RLS) semua dataset asal ikut
       diwariskan, dan hanya role yang boleh memakai SEMUA dataset asal yang diberi akses.

Semua pemeriksaan memakai hak akses pengguna yang bertanya.
"""

from __future__ import annotations

import re

from sps_ai import alat

UMUM = {"id", "nama", "name", "keterangan", "description", "deskripsi", "status", "created_at", "updated_at",
        "created_by", "updated_by", "created_on", "changed_on", "tanggal", "tgl", "tahun", "bulan", "total", "jumlah",
        "nilai", "provinsi", "kota", "saluran", "kategori"}
POLA_KUNCI = re.compile(r"^(kd_|kode|id_|no_|nomor|npwp|nip|nik)|(_id|_kd|_kode|_code|_no)$", re.I)
MAKS_DATASET = 6


def _kolom(t) -> list[str]:
    return [c.column_name for c in t.columns if c.is_active is not False and not c.expression]


def kunci_bersama(kiri: list[str], kanan: list[str]) -> list[tuple[str, str]]:
    """Pasangan (kolom kiri, kolom kanan) bernama sama yang mirip kunci. Kosong bila tidak ada."""
    peta = {k.lower(): k for k in kiri}
    sama = [(peta[k.lower()], k) for k in kanan if k.lower() in peta and k.lower() not in UMUM]
    return [p for p in sama if POLA_KUNCI.search(p[1])]


def _hitung(t, kunci: list[str]) -> tuple[int, int]:
    """(jumlah baris, jumlah kombinasi kunci berbeda) dengan hak akses pengguna."""
    metrik = [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "n"}]
    n = int(alat.jalankan_objek(t, metrik, [], [], [], 1)["baris"][0]["n"] or 0)
    unik = len(alat.jalankan_objek(t, metrik, kunci, [], [], 100_000)["baris"])
    return n, unik


def rencana(dataset_ids: list[int]) -> dict:
    """Tentukan dataset utama, urutan gabung, kunci, dan yang dilewati (tanpa menyimpan apa pun)."""
    ids = list(dict.fromkeys(int(i) for i in dataset_ids))
    if not 2 <= len(ids) <= MAKS_DATASET:
        raise alat.InputSalah(f"Pilih 2–{MAKS_DATASET} dataset untuk digabung.")
    ds = [alat._dataset(i) for i in ids]                      # menolak dataset yang tidak boleh diakses
    if len({t.database_id for t in ds}) > 1:
        raise alat.InputSalah("Dataset harus berada di database/koneksi yang sama untuk digabung.")
    kolom = {t.id: _kolom(t) for t in ds}

    # Kunci tiap pasangan & keunikannya di masing-masing sisi.
    hubung: dict[tuple[int, int], list[tuple[str, str]]] = {}
    for a in ds:
        for b in ds:
            if a.id != b.id and (k := kunci_bersama(kolom[a.id], kolom[b.id])):
                hubung[(a.id, b.id)] = k
    if not hubung:
        raise alat.InputSalah("Tidak ditemukan kolom penghubung (mis. kd_cabang, id_pelanggan) yang sama di dataset ini. "
                              "Gabungkan manual lewat Kueri Visual atau Persiapan data.")
    statistik = {}
    for (a, b), k in hubung.items():
        t = next(x for x in ds if x.id == b)
        kunci_b = [kb for _, kb in k]
        if (b, tuple(kunci_b)) not in statistik:
            statistik[(b, tuple(kunci_b))] = _hitung(t, kunci_b)

    def unik(b: int, kunci_b: list[str]) -> bool:
        n, u = statistik[(b, tuple(kunci_b))]
        return n == u

    # Dataset utama: yang terhubung ke paling banyak dataset lain dengan kunci yang UNIK di sisi lain (banyak-ke-satu),
    # lalu yang barisnya terbanyak (tabel transaksi).
    def skor(t):
        ke_dimensi = sum(1 for (a, b), k in hubung.items() if a == t.id and unik(b, [kb for _, kb in k]))
        baris = max((statistik[(t.id, tuple(kb for _, kb in k))][0] for (a, b), k in hubung.items() if b == t.id), default=0)
        return ke_dimensi, baris
    utama = max(ds, key=skor)

    langkah, dilewati, terpakai = [], [], [utama.id]
    ada = {k.lower() for k in kolom[utama.id]}         # kolom yang sudah ada di hasil: tidak diambil dua kali
    sisa = [t for t in ds if t.id != utama.id]
    while sisa:
        maju = False
        for t in list(sisa):
            pasangan = next(((a, hubung[(a, t.id)]) for a in terpakai if (a, t.id) in hubung), None)
            if pasangan is None:
                continue
            asal, k = pasangan
            kunci_kanan = [kb for _, kb in k]
            sisa.remove(t)
            maju = True
            if not unik(t.id, kunci_kanan):
                n, u = statistik[(t.id, tuple(kunci_kanan))]
                dilewati.append({"dataset": t.table_name, "alasan":
                                 f"banyak-ke-banyak: {', '.join(kunci_kanan)} tidak unik di '{t.table_name}' ({n} baris, "
                                 f"{u} nilai kunci) maupun di dataset utama. Menggabungkannya melipatgandakan baris "
                                 "sehingga SUM/COUNT menjadi salah. Buat dataset terpisah untuknya."})
                continue
            ambil = [c for c in kolom[t.id] if c.lower() not in ada and c not in kunci_kanan]
            if not ambil:
                dilewati.append({"dataset": t.table_name, "alasan": "semua kolomnya sudah ada di dataset utama"})
                continue
            ada |= {c.lower() for c in ambil}
            langkah.append({"jenis": "gabung", "dataset_id": t.id, "tipe": "left", "kolom": ambil,
                            "kunci": [{"kiri": ka, "kanan": kb} for ka, kb in k],
                            "_nama": t.table_name, "_asal": next(x.table_name for x in ds if x.id == asal)})
            terpakai.append(t.id)
        if not maju:
            dilewati += [{"dataset": t.table_name, "alasan": "tidak punya kolom penghubung dengan dataset lain"} for t in sisa]
            break
    return {"utama": utama, "langkah": langkah, "dilewati": dilewati}


def nama_bebas(nama: str, database_id: int) -> str:
    """Nama dataset yang belum dipakai: detail_x, detail_x_2, detail_x_3, ... (maks. 30 karakter)."""
    from superset import db
    from superset.connectors.sqla.models import SqlaTable
    dasar = re.sub(r"[^a-z0-9_]", "_", nama)[:27].strip("_") or "gabungan"
    for n in range(1, 100):
        calon = dasar if n == 1 else f"{dasar}_{n}"
        if not db.session.query(SqlaTable).filter_by(table_name=calon, database_id=database_id).first():
            return calon
    raise alat.InputSalah("Terlalu banyak dataset bernama sama; beri nama lain.")


def gabung(dataset_ids: list[int], nama: str = "") -> dict:
    from sps_studio import prep
    r = rencana(dataset_ids)
    if not r["langkah"]:
        raise alat.InputSalah("Tidak ada dataset yang aman digabung. " +
                              " ".join(f"{d['dataset']}: {d['alasan']}" for d in r["dilewati"]))
    nama = nama_bebas((nama or f"detail_{r['utama'].table_name}").lower(), r["utama"].database_id)
    langkah = [{k: v for k, v in l.items() if not k.startswith("_")} for l in r["langkah"]]
    hasil = prep.simpan(r["utama"].id, langkah, nama)
    return {**hasil, "dataset_utama": r["utama"].table_name,
            "gabung": [f"LEFT JOIN {l['_nama']} ON " + " AND ".join(f"{l['_asal']}.{k['kiri']} = {l['_nama']}.{k['kanan']}"
                                                                    for k in l["kunci"]) for l in r["langkah"]],
            "dilewati": r["dilewati"]}
