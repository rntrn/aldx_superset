"""Uji otomatis ALDx: dijalankan di dalam container superset oleh scripts\\uji.ps1.

Memeriksa (tanpa mengubah data pengguna):
    1. Komponen   : metadb, ALDx Engine, Redis, backgrounder (Celery) & antreannya
    2. Data       : dataset latihan ada (scripts\\data-latihan.ps1)
    3. Studio     : 23 jenis chart -> query & konversi ke chart Superset
    4. Analitik   : ramalan Holt-Winters, tren, anomali
    5. Engine     : tabel tukar-atomik & tambahan (tabel sementara uji__otomatis, lalu dihapus)
    6. Halaman    : /health, /app/, /studio/, /pusat-kendali/, /asisten/, /kueri/ (wajib login), aset cangkang,
                    susunan menu alur BI (Data, Kueri, Analisis & Visual, Dashboard & Story)
    7. Keamanan   : upload hanya ke ALDx Engine, RLS ikut di dataset ekstrak, role Superadmin & penjaganya
    8. Tahap 2    : batas data terhitung, ekspor Excel, peran Asisten AI

Hasil: tabel LULUS/GAGAL; kode keluar 1 bila ada yang GAGAL (dipakai upgrade & installer).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import traceback

HASIL: list[tuple[str, str, bool, str]] = []


def uji(kelompok: str, nama: str):
    def dekor(fungsi):
        mulai = time.monotonic()
        try:
            ket = fungsi() or ""
            HASIL.append((kelompok, nama, True, f"{ket} ({time.monotonic() - mulai:.1f} dtk)".strip()))
        except Exception as exc:  # noqa: BLE001 - semua galat dilaporkan sebagai GAGAL
            HASIL.append((kelompok, nama, False, str(exc).splitlines()[0][:160] if str(exc) else repr(exc)))
            if os.environ.get("SPS_UJI_RINCI"):
                traceback.print_exc()
        return fungsi
    return dekor


def jalankan_semua() -> None:
    from superset import db, security_manager as sm
    from superset.connectors.sqla.models import RowLevelSecurityFilter, SqlaTable
    from superset.utils.core import override_user
    from sqlalchemy import text

    import sps_latihan
    from sps_engine import ekstrak, klien as K, tabel as T
    from sps_server import lingkungan
    from sps_studio import lembar, prediksi

    # ---- 1. Komponen
    @uji("Komponen", "metadb (PostgreSQL) terhubung")
    def _():
        with db.engine.connect() as c:
            c.execute(text("SELECT 1"))
            versi = ".".join(map(str, c.dialect.server_version_info or ()))
        return f"{db.engine.dialect.name} {versi}"

    @uji("Komponen", "ALDx Engine (ClickHouse) terhubung")
    def _():
        df = K.klien().kueri_df("SELECT version() AS v")
        return f"versi {df['v'][0]}"

    @uji("Komponen", "Redis terhubung")
    def _():
        import redis
        r = lingkungan.redis()
        if not r.aktif:
            raise RuntimeError("REDIS_HOST kosong")
        redis.Redis(host=r.host, port=r.port, password=r.password or None, socket_timeout=5).ping()
        return f"{r.host}:{r.port}"

    @uji("Komponen", "Backgrounder menjawab & melayani antrean")
    def _():
        from superset.extensions import celery_app
        aktif = celery_app.control.inspect(timeout=5).active_queues() or {}
        if not aktif:
            raise RuntimeError("tidak ada worker yang menjawab (cek container superset-worker)")
        antrean = {q["name"] for daftar in aktif.values() for q in daftar}
        kurang = {"sqllab", "ekstrak", "laporan", "cache"} - antrean
        if kurang:
            raise RuntimeError(f"antrean tanpa worker: {sorted(kurang)}")
        return f"{len(aktif)} worker, antrean {sorted(antrean)}"

    # ---- 2. Data latihan
    ds = {t.table_name: t for t in db.session.query(SqlaTable).filter(
        SqlaTable.table_name.in_(["latihan_penjualan", "latihan_lokasi_pelanggan"])).all()}

    @uji("Data", "Dataset latihan tersedia")
    def _():
        if len(ds) < 2:
            raise RuntimeError("belum ada; jalankan scripts\\data-latihan.ps1")
        return ", ".join(f"{n} (id {t.id})" for n, t in ds.items())

    admin = sm.find_user(username=os.environ.get("ADMIN_USERNAME", "admin")) or \
        next(u for u in sm.get_all_users() if any(r.name == "Admin" for r in u.roles))

    # ---- 3. Studio: 23 jenis chart
    if len(ds) == 2:
        P, L = ds["latihan_penjualan"].id, ds["latihan_lokasi_pelanggan"].id
        D = lambda f: {"field": f, "peran": "dimensi"}                       # noqa: E731
        U = lambda f, agg="SUM": {"field": f, "peran": "ukuran", "agg": agg}  # noqa: E731
        kasus = {
            "angka": (P, [], [U("total")], None), "angka_tren": (P, [D("periode")], [U("total")], None),
            "gauge": (P, [], [U("jumlah_transaksi")], None), "tabel": (P, [D("nm_cabang")], [U("total")], None),
            "tabel_pivot": (P, [D("kategori")], [D("nm_cabang"), U("total")], None),
            "peta_panas": (P, [D("saluran")], [D("kategori")], U("total")),
            "batang": (P, [D("nm_cabang")], [U("total")], D("saluran")),
            "batang_100": (P, [D("nm_cabang")], [U("total")], D("saluran")),
            "garis": (P, [D("periode")], [U("total")], None), "area": (P, [D("periode")], [U("total")], D("saluran")),
            "waterfall": (P, [D("kategori")], [U("total")], None),
            "radar": (P, [D("saluran")], [U("total"), U("jumlah_transaksi"), U("total", "AVG")], None),
            "pie": (P, [D("kategori")], [U("total")], None),
            "treemap": (P, [D("kategori"), D("saluran")], [U("total")], None),
            "sunburst": (P, [D("kategori"), D("saluran")], [U("total")], None),
            "funnel": (P, [D("saluran")], [U("total")], None), "awan_kata": (P, [D("nm_cabang")], [U("total")], None),
            "sebar": (P, [D("nm_cabang"), U("total")], [U("jumlah_transaksi")], None),
            "box_plot": (P, [D("nm_cabang")], [U("total")], D("periode")),
            "sankey": (P, [D("nm_cabang")], [U("total")], D("kategori")),
            "peta_wilayah": (L, [D("provinsi")], [U("belanja")], None),
            "peta_titik": (L, [D("lon")], [D("lat")], D("saluran")), "peta_kepadatan": (L, [D("lon")], [D("lat")], None),
        }
        with override_user(admin):
            for tanda, (dsid, kolom, baris, warna) in kasus.items():
                @uji("Studio", f"chart {lembar.ATURAN_TANDA[tanda]['label']}")
                def _(tanda=tanda, dsid=dsid, kolom=kolom, baris=baris, warna=warna):
                    t, lb = lembar.dari_dict({"dataset_id": dsid, "tanda": tanda, "kolom": kolom, "baris": baris,
                                              "warna": warna})
                    lembar.periksa_tanda(lb)
                    hasil = lembar.jalankan(t, lb)
                    if not hasil["baris"]:
                        raise RuntimeError("query tidak mengembalikan baris")
                    viz, _p = lembar.ke_superset(t, lb)
                    return f"{len(hasil['baris'])} baris -> {viz}"

            # ---- 4. Analitik
            @uji("Analitik", "Ramalan 6 bulan, tren & anomali")
            def _():
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "garis", "kolom": [D("periode")],
                                          "baris": [U("total")], "analitik": {"ramalan": 6, "tren": True, "anomali": True}})
                s = lembar.jalankan(t, lb)["analitik"]["seri"]["SUM(total)"]
                if "musiman 12" not in s["ramalan"]["metode"] or len(s["ramalan"]["nilai"]) != 6:
                    raise RuntimeError(s["ramalan"]["metode"])
                return f"{s['ramalan']['metode']}, R² {s['tren']['r2']}, {len(s['anomali'])} anomali"

            @uji("Studio", "Hierarki dimensi: simpan, baca, telusuri (filter jalur), hapus")
            def _():
                from sps_studio import hierarki
                nama = "uji__hierarki"
                hierarki.simpan(P, nama, ["provinsi", "nm_cabang", "kategori"])
                if not any(h["nama"] == nama for h in hierarki.daftar(P)):
                    raise RuntimeError("hierarki tidak tersimpan")
                atas = lembar.jalankan(*lembar.dari_dict({"dataset_id": P, "tanda": "batang", "kolom": [D("provinsi")],
                                                          "baris": [U("jumlah_transaksi")]}))
                prov = str(atas["baris"][0]["provinsi"])
                dalam = lembar.jalankan(*lembar.dari_dict({"dataset_id": P, "tanda": "batang", "kolom": [D("nm_cabang")],
                                                           "baris": [U("jumlah_transaksi")],
                                                           "filter": [{"field": "provinsi", "op": "IN", "nilai": [prov]}]}))
                hierarki.hapus(P, nama)
                if any(h["nama"] == nama for h in hierarki.daftar(P)) or not dalam["baris"]:
                    raise RuntimeError("telusur/hapus gagal")
                return f"{len(atas['baris'])} provinsi -> {len(dalam['baris'])} cabang di {prov}"

            @uji("Studio", "Tampilkan saya: kolom berlebih diabaikan, jenis tetap bisa dipakai")
            def _():
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "pie", "kolom": [D("periode"), D("kategori")],
                                          "baris": [U("total")], "warna": D("saluran")})
                lembar.periksa_tanda(lb)
                hasil = lembar.jalankan(t, lb)
                if hasil["dimensi"] != ["kategori"] or sorted(lb.diabaikan) != ["periode", "saluran"]:
                    raise RuntimeError(f"pie memakai {hasil['dimensi']}, diabaikan {lb.diabaikan}")
                return f"Pie memakai kategori; diabaikan {', '.join(lb.diabaikan)}"

            @uji("Analitik", "Analitik lengkap: rata bergerak, rata-rata, median, target, tertinggi/terendah")
            def _():
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "garis", "kolom": [D("periode")], "baris": [U("total")],
                                          "analitik": {"rata_bergerak": 3, "rata_rata": True, "median": True,
                                                       "target": 1e9, "ekstrem": True}})
                s = lembar.jalankan(t, lb)["analitik"]["seri"]["SUM(total)"]
                rb = s["rata_bergerak"]["nilai"]
                if rb[:2] != [None, None] or rb[2] is None or not (s["median"] and s["rata_rata"] and s["target"] == 1e9):
                    raise RuntimeError(f"analitik tidak lengkap: {sorted(s)}")
                if s["ekstrem"]["maks"]["nilai"] < s["ekstrem"]["min"]["nilai"]:
                    raise RuntimeError("tertinggi < terendah")
                return f"rata bergerak 3, median, rata-rata, target, tertinggi {s['ekstrem']['maks']['x']}"

            @uji("Studio", "Ukuran & dimensi terdefinisi: validasi rumus, pakai, lindungi, hapus")
            def _():
                from sps_ai import alat
                from sps_studio import definisi
                t = db.session.get(SqlaTable, P)
                for jenis, rumus in (("ukuran", "total / jumlah_transaksi"), ("ukuran", "SUM(total) / (SELECT 1)"),
                                     ("ukuran", "SUM(kolom_ngawur)"), ("dimensi", "SUM(total)"), ("dimensi", "total; DROP TABLE x")):
                    try:
                        definisi.periksa(t, jenis, rumus)
                    except alat.InputSalah:
                        continue
                    raise RuntimeError(f"rumus berbahaya/salah lolos: {jenis} {rumus}")
                for jenis, nama in (("ukuran", "uji__rasio"), ("dimensi", "uji__kelompok")):   # sisa uji sebelumnya
                    try:
                        definisi.hapus(P, jenis, nama)
                    except alat.InputSalah:
                        pass
                definisi.simpan(P, {"jenis": "ukuran", "nama": "uji__rasio", "rumus": "SUM(total) / SUM(jumlah_transaksi)"})
                definisi.simpan(P, {"jenis": "dimensi", "nama": "uji__kelompok",
                                    "rumus": "CASE WHEN total >= 150000000 THEN 'Besar' ELSE 'Kecil' END"})
                h = lembar.jalankan(*lembar.dari_dict({"dataset_id": P, "tanda": "batang", "kolom": [D("uji__kelompok")],
                                                       "baris": [{"field": "uji__rasio", "peran": "ukuran", "metrik": True}]}))
                try:
                    definisi.hapus(P, "dimensi", "kategori")
                    raise RuntimeError("kolom asli bisa dihapus")
                except alat.InputSalah:
                    pass
                definisi.hapus(P, "ukuran", "uji__rasio"); definisi.hapus(P, "dimensi", "uji__kelompok")
                if len(h["baris"]) != 2:
                    raise RuntimeError(f"dimensi terdefinisi salah: {h['baris']}")
                return f"5 rumus salah ditolak; rasio per kelompok: {len(h['baris'])} baris; kolom asli terlindung"

            @uji("Studio", "Kalkulasi cepat (% dari total, kumulatif) & skala warna tabel")
            def _():
                dasar = {"dataset_id": P, "tanda": "garis", "kolom": [D("periode")], "baris": [U("total")]}
                asli = [b["SUM(total)"] for b in lembar.jalankan(*lembar.dari_dict(dasar))["baris"]]
                persen = [b["SUM(total)"] for b in lembar.jalankan(*lembar.dari_dict({**dasar, "kalkulasi": "persen_total"}))["baris"]]
                t, lb = lembar.dari_dict({**dasar, "kalkulasi": "kumulatif"})
                kum = [b["SUM(total)"] for b in lembar.jalankan(t, lb)["baris"]]
                if abs(sum(persen) - 100) > 1e-6 or abs(kum[-1] - sum(asli)) > 1 or kum != sorted(kum):
                    raise RuntimeError(f"persen={sum(persen)} kumulatif akhir={kum[-1]} total={sum(asli)}")
                if lembar.ke_superset(t, lb)[1].get("rolling_type") != "cumsum":
                    raise RuntimeError("kumulatif tidak ikut ke chart Superset")
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "pie", "kolom": [D("kategori")], "baris": [U("total")],
                                          "kalkulasi": "kumulatif"})
                if lembar.jalankan(t, lb)["kalkulasi"]:
                    raise RuntimeError("kalkulasi aktif di Pie (seharusnya hanya Garis/Area/Batang)")
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "tabel", "baris": [D("nm_cabang")], "kolom": [U("total")],
                                          "skala_warna": True})
                p = lembar.ke_superset(t, lb)[1]
                if not p.get("conditional_formatting") or p.get("show_cell_bars"):
                    raise RuntimeError("skala warna tabel tidak ikut ke chart Superset")
                return f"% total = {sum(persen):.0f}; kumulatif akhir = total ({kum[-1]:,.0f}); skala warna tersimpan"

            @uji("Studio", "YoY (% vs tahun lalu) & urutan batang mendatar")
            def _():
                dasar = {"dataset_id": P, "tanda": "garis", "kolom": [D("periode")], "baris": [U("total")]}
                asli = [b["SUM(total)"] for b in sorted(lembar.jalankan(*lembar.dari_dict(dasar))["baris"],
                                                        key=lambda b: prediksi.kunci_urut(b["periode"]))]
                t, lb = lembar.dari_dict({**dasar, "kalkulasi": "yoy"})
                yoy = [b["SUM(total)"] for b in lembar.jalankan(t, lb)["baris"]]
                harap = (asli[12] - asli[0]) / asli[0] * 100
                if any(v is not None for v in yoy[:12]) or abs(yoy[12] - harap) > 1e-6:
                    raise RuntimeError(f"YoY salah: {yoy[:14]} (harap bulan ke-13 = {harap})")
                p = lembar.ke_superset(t, lb)[1]
                if p.get("time_compare") != ["1 year ago"] or p.get("time_range") != lembar.RENTANG_YOY:
                    raise RuntimeError("YoY tidak ikut ke chart Superset")
                t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "batang", "kolom": [D("nm_cabang")], "baris": [U("total")],
                                          "kalkulasi": "yoy"})
                if lembar.jalankan(t, lb)["kalkulasi"]:
                    raise RuntimeError("YoY aktif pada dimensi bukan tanggal")
                arah = {}
                for nama, rak in (("tegak", {"kolom": [D("nm_cabang")], "baris": [U("total")]}),
                                  ("mendatar", {"baris": [D("nm_cabang")], "kolom": [U("total")]})):
                    t, lb = lembar.dari_dict({"dataset_id": P, "tanda": "batang", "urut": "turun", **rak})
                    arah[nama] = lembar.ke_superset(t, lb)[1]["x_axis_sort_asc"]
                if arah != {"tegak": False, "mendatar": True}:
                    raise RuntimeError(f"urutan batang salah: {arah}")
                return f"YoY bulan ke-13 = {yoy[12]:.1f}%; batang mendatar: terbesar di atas"

            @uji("Studio", "Jelaskan perubahan & analitik per Warna")
            def _():
                from sps_ai import alat
                from sps_studio import jelaskan
                spec = {"dataset_id": P, "tanda": "garis", "kolom": [D("periode")], "baris": [U("total")]}
                xs = sorted({b["periode"] for b in lembar.jalankan(*lembar.dari_dict(spec))["baris"]})
                j = jelaskan.jelaskan(spec, xs[14], xs[13])
                if not j["rincian"] or j["rincian"][0]["dimensi"] == "periode":
                    raise RuntimeError(f"tidak ada rincian: {j}")
                if abs(j["kini"] - j["dulu"] - j["selisih"]) > 1e-6 or not all(len(r["teratas"]) <= jelaskan.TERATAS for r in j["rincian"]):
                    raise RuntimeError("selisih/penyumbang salah")
                try:
                    jelaskan.jelaskan({**spec, "tanda": "pie"}, xs[1], xs[0])
                    raise RuntimeError("jelaskan pada Pie lolos")
                except alat.InputSalah:
                    pass
                t, lb = lembar.dari_dict({**spec, "warna": D("saluran"), "analitik": {"tren": True, "ramalan": 3}})
                h = lembar.jalankan(t, lb)
                seri = h["analitik"]["seri"] if h["analitik"] else {}
                if not (h["analitik"] or {}).get("per_warna") or len(seri) != 4 or not all("tren" in s and "ramalan" in s for s in seri.values()):
                    raise RuntimeError(f"analitik per warna salah: {list(seri)}")
                return (f"{j['rincian'][0]['dimensi']} paling menjelaskan ({round(j['rincian'][0]['pusat'])}%); "
                        f"analitik per warna: {', '.join(seri)}")

            @uji("Studio", "Dashboard bertab & tinggi kotak: simpan -> buka sama")
            def _():
                from sps_studio import dasbor
                cid = [x["id"] for x in lembar.daftar()][:3]
                pos, charts, _ = dasbor.posisi("Uji", "", [], [
                    {"judul": "Ringkasan", "baris": [[{"chart_id": cid[0], "lebar": 6, "tinggi": 90}, {"chart_id": cid[1], "lebar": 6}]]},
                    {"judul": "Rincian", "baris": [[{"chart_id": cid[2], "lebar": 12}]]}])
                tab = [k for k, v in pos.items() if isinstance(v, dict) and v.get("type") == "TAB"]
                if pos["GRID_ID"]["children"] != ["TABS-sps"] or len(tab) != 2 or len(charts) != 3:
                    raise RuntimeError(f"struktur tab salah: {pos['GRID_ID']}")
                chart0 = pos[f"CHART-sps{cid[0]}"]
                if chart0["meta"]["height"] != 90 or chart0["parents"][:4] != ["ROOT_ID", "GRID_ID", "TABS-sps", "TAB-sps1"]:
                    raise RuntimeError(f"tinggi/induk chart salah: {chart0}")
                biasa, _, _ = dasbor.posisi("Uji", "", [[{"chart_id": cid[0], "lebar": 6}]], [{"judul": "Satu", "baris": [[{"chart_id": cid[0], "lebar": 6}]]}])
                if "TABS-sps" in biasa:
                    raise RuntimeError("satu tab seharusnya tanpa komponen TABS")
                return "2 tab, tinggi 90 tersimpan; satu tab = dashboard biasa"

            @uji("Asisten AI", "Gabung dataset otomatis: kunci, banyak-ke-banyak dilewati, RLS per role ikut")
            def _():
                from superset.connectors.sqla.models import RowLevelSecurityFilter
                from sps_ai import agen, gabung
                cab = db.session.query(SqlaTable).filter_by(table_name="latihan_cabang").first()
                if cab is None:
                    return "dilewati: latihan_cabang belum ada"
                r = gabung.rencana([cab.id, L, P])
                if r["utama"].id != P or [l["dataset_id"] for l in r["langkah"]] != [cab.id] \
                        or [d["dataset"] for d in r["dilewati"]] != ["latihan_lokasi_pelanggan"]:
                    raise RuntimeError(f"rencana salah: {r['utama'].table_name}, {r['langkah']}, {r['dilewati']}")
                if any(c.lower() in ("nm_cabang", "provinsi") for c in r["langkah"][0]["kolom"]):
                    raise RuntimeError("kolom ganda ikut diambil")
                lama = db.session.query(SqlaTable).filter_by(table_name="uji__gabung").first()
                for x in ([lama] if lama else []):
                    for f in db.session.query(RowLevelSecurityFilter).all():
                        if x in f.tables:
                            db.session.delete(f)
                    db.session.delete(x)
                db.session.commit()
                h = gabung.gabung([cab.id, L, P], "uji__gabung")
                baru = db.session.query(SqlaTable).get(h["id"])
                try:
                    df = baru.database.get_df(f"SELECT COUNT(*) AS n FROM ({baru.sql}) x", schema=baru.schema)
                    asal = baru.database.get_df(f"SELECT COUNT(*) AS n FROM {ds['latihan_penjualan'].table_name}",
                                                schema=ds["latihan_penjualan"].schema)
                    rls = [f for f in db.session.query(RowLevelSecurityFilter).all() if baru in f.tables]
                    sumber = [f for f in db.session.query(RowLevelSecurityFilter).all() if ds["latihan_penjualan"] in f.tables]
                    if int(df["n"][0]) != int(asal["n"][0]):
                        raise RuntimeError(f"baris berlipat: {df['n'][0]} vs {asal['n'][0]}")
                    if len(rls) < len(sumber) or any(set(f.roles) != set(next(s for s in sumber if f.name.startswith(s.name)).roles) for f in rls):
                        raise RuntimeError(f"RLS tidak tersalin: {[f.name for f in rls]}")
                finally:
                    for f in db.session.query(RowLevelSecurityFilter).all():
                        if baru in f.tables:
                            db.session.delete(f)
                    db.session.delete(baru)
                    db.session.commit()
                from sps_ai import latar
                if latar.tersedia():                        # status pertanyaan latar hanya untuk pemiliknya
                    import time as _t
                    latar._tulis("uji__job", {"username": "uji__a", "status": "jalan", "peristiwa": [], "mulai": _t.time()})
                    if latar.status("uji__job", "uji__b") is not None or latar.status("uji__job", "uji__a") is None:
                        raise RuntimeError("status pertanyaan latar bocor ke akun lain")
                    latar._tulis("uji__mati", {"username": "uji__a", "status": "jalan", "peristiwa": [], "mulai": _t.time() - 600})
                    mati = latar.status("uji__mati", "uji__a")           # tanpa denyut = prosesnya mati -> gagal, bukan menunggu selamanya
                    if mati["status"] != "gagal" or "terhenti" not in mati["galat"]:
                        raise RuntimeError(f"pekerjaan mati tidak terdeteksi: {mati}")
                    latar._tulis("uji__hidup", {"username": "uji__a", "status": "jalan", "peristiwa": [], "mulai": _t.time() - 600})
                    latar._tulis("denyut:uji__hidup", {"t": _t.time()})
                    if latar.status("uji__hidup", "uji__a")["status"] != "jalan":
                        raise RuntimeError("pekerjaan yang masih berdenyut dianggap mati")
                if gabung.nama_bebas("latihan_penjualan", ds["latihan_penjualan"].database_id) == "latihan_penjualan":
                    raise RuntimeError("nama dataset bentrok tidak diberi akhiran")
                if not 60 <= agen.batas_total() <= 330:
                    raise RuntimeError(f"batas total AI {agen.batas_total()} tidak di bawah batas web")
                return f"{int(df['n'][0])} baris (tidak berlipat), {len(rls)} aturan RLS tersalin; batas AI {agen.batas_total()} dtk"

            @uji("Asisten AI", "Semua jenis model: alat dari teks, argumen dirapikan, cadangan aman, pindai tabel")
            def _():
                from sps_ai import agen, llm, tabel_db
                from sps_ai.pengaturan import ModelAI, Pengaturan
                t = llm.alat_dari_teks('<tool_call>{"name": "info_dataset", "arguments": {"dataset_id": "latihan_penjualan"}}</tool_call>',
                                       {"info_dataset"})
                if not t or llm.alat_dari_teks('{"name": "hapus_semua", "arguments": {}}', {"info_dataset"}):
                    raise RuntimeError("pembacaan alat dari teks salah")
                a = agen.rapikan_argumen({"dataset_id": "latihan_penjualan", "dataset_ids": "latihan_cabang, 13",
                                          "metrik": "SUM(total)", "chart_ids": ["5", "x"]})
                if a["dataset_id"] != P or a["dataset_ids"][1] != 13 or a["metrik"] != ["SUM(total)"] or a["chart_ids"] != [5]:
                    raise RuntimeError(f"argumen tidak dirapikan: {a}")
                m = lambda i, key, data: ModelAI(i, i, "http://x", "m", key, data)  # noqa: E731
                awan_data, awan_rahasia, lokal = m("a", "k", True), m("b", "k", False), m("c", "", True)
                atur = Pengaturan([awan_data, awan_rahasia, lokal], "a", [], 6, 500, 50, 120)
                if agen.cadangan(atur, awan_data, ["a"]).id != "c":       # data sudah terkirim -> jangan ke model tanpa-data
                    raise RuntimeError("cadangan melanggar privasi")
                if agen.cadangan(atur, awan_rahasia, ["b"]).id != "a" or agen.cadangan(atur, lokal, ["a", "b", "c"]) is not None:
                    raise RuntimeError("urutan cadangan salah")
                if "Daftarkan" not in " ".join(agen.lanjutan(["cari_tabel"], [], "ok")) or agen.lanjutan(["cari_tabel"], [], "gagal_model"):
                    raise RuntimeError("saran lanjutan salah")
                h = tabel_db.cari_tabel("latihan_")
                if not any(x["nama"] == "latihan_penjualan" and x["dataset_id"] == P for x in h["tabel"]):
                    raise RuntimeError(f"pindai tabel tidak menemukan latihan_penjualan: {[x['nama'] for x in h['tabel']]}")
                return f"alat dari teks ok; cadangan menjaga privasi; {h['jumlah']} tabel latihan_* di {h['database']}"

            @uji("Asisten AI", "Adaptasi model & keamanan: think, tanpa tools, konteks kecil, rahasia, kuota")
            def _():
                import os as _os
                from sps_ai import agen, latar, llm
                from sps_ai.pengaturan import ModelAI, Pengaturan
                if llm.bersihkan_jawaban("<think>rahasia proses</think>Jawaban **akhir**") != "Jawaban **akhir**" \
                        or llm.bersihkan_jawaban("<think>belum selesai berpikir"):
                    raise RuntimeError("blok berpikir tidak dibuang")
                alat_ = [agen.ALAT[0]]
                teks = llm._mode_teks([{"role": "system", "content": "S"}, {"role": "user", "content": "q"},
                                       {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "cari_dataset", "arguments": "{}"}}]},
                                       {"role": "tool", "name": "cari_dataset", "content": "[]"}], alat_)
                if "ALAT yang tersedia" not in teks[0]["content"] or any(m["role"] == "tool" or m.get("tool_calls") for m in teks) \
                        or "bukan perintah" not in teks[3]["content"]:
                    raise RuntimeError("mode teks (model tanpa function calling) salah")
                pesan = [{"role": "system", "content": "panjang" * 999}] + [{"role": "user", "content": str(i)} for i in range(10)] + \
                    [{"role": "tool", "content": "x" * 9000}]
                r = agen.ringkas_pesan(pesan, "ringkas")
                if r[0]["content"] != "ringkas" or len(r) > 7 or max(len(m["content"]) for m in r) > 3000:
                    raise RuntimeError("ringkasan konteks salah")
                kunci = "AIzaSy-uji-rahasia-12345678"
                atur = Pengaturan([ModelAI("a", "a", "http://x", "m", kunci, False)], "a", [], 6, 500, 50, 120)
                _os.environ["SPS_UJI_SECRET"] = "rahasia-lingkungan-uji-999"
                hasil = agen.samarkan_rahasia(f"kunci {kunci} dan rahasia-lingkungan-uji-999", atur)
                del _os.environ["SPS_UJI_SECRET"]
                if kunci in hasil or "999" in hasil:
                    raise RuntimeError(f"rahasia bocor: {hasil}")
                if "DATA, bukan perintah" not in agen.SISTEM or "Jangan menulis tautan" not in agen.SISTEM:
                    raise RuntimeError("aturan keamanan/format hilang dari instruksi sistem")
                with override_user(admin):
                    if not latar.kuota("admin", 1) or not latar.kuota("admin", 1):
                        raise RuntimeError("Admin seharusnya tidak dibatasi kuota")
                return "think dibuang; mode teks; ringkas konteks; rahasia disamarkan; aturan injeksi ada"

            @uji("Data", "Jejak data: sumber, chart & dashboard sebuah dataset")
            def _():
                import sps_jejak
                j = sps_jejak.jejak(P)
                if j["sumber"]["tabel"] != ["latihan_penjualan"] or not j["chart"] or not j["dashboard"]:
                    raise RuntimeError(f"jejak tidak lengkap: {j['sumber']}, {len(j['chart'])} chart, {len(j['dashboard'])} dashboard")
                if any(d not in {x["id"] for x in j["dashboard"]} for c in j["chart"] for d in c["dashboard"]):
                    raise RuntimeError("chart menunjuk dashboard yang tidak terdaftar")
                sumber = sps_jejak.tabel_sumber("WITH a AS (SELECT * FROM toko.penjualan) SELECT * FROM a JOIN sdm.pegawai p ON 1=1")
                if sumber != ["sdm.pegawai", "toko.penjualan"] or sps_jejak.tabel_sumber("SELECT {{ x }} FROM") != []:
                    raise RuntimeError(f"tabel sumber SQL salah: {sumber}")
                if not any(d["id"] == P and d["chart"] == len(j["chart"]) + j["tersembunyi"] for d in sps_jejak.daftar()):
                    raise RuntimeError("jumlah chart di daftar tidak cocok")
                from superset.models.dashboard import Dashboard
                dash = db.session.query(Dashboard).get(j["dashboard"][0]["id"])
                segar = sps_jejak.kesegaran(dash)                       # data latihan = tabel engine: usia dari engine
                if not segar["rincian"] or segar["usia_detik"] is None or segar["usia_detik"] < 0 or \
                        any(r["jenis"] not in ("ekstrak", "engine", "langsung") for r in segar["rincian"]):
                    raise RuntimeError(f"kesegaran salah: {segar}")
                return f"{len(j['chart'])} chart, {len(j['dashboard'])} dashboard; tabel sumber SQL terbaca"

            @uji("Studio", "Template dashboard: 3 template menghasilkan lembar kerja yang sah")
            def _():
                from sps_ai import alat
                from sps_studio import templat
                jumlah = {}
                for kunci in templat.TEMPLAT:
                    p, baris = templat.rancang(P, kunci, "total")
                    if p["ukuran"][0]["field"] != "total":
                        raise RuntimeError(f"ukuran utama bukan total: {p['ukuran'][0]}")
                    for isi in baris:
                        if sum(lebar for _, lebar in isi) > 12:
                            raise RuntimeError(f"{kunci}: baris lebih dari 12 kolom")
                        for spec, _ in isi:
                            tt, lb = lembar.dari_dict(spec)
                            lembar.periksa_tanda(lb)
                            lembar.ke_superset(tt, lb)
                    jumlah[kunci] = sum(len(isi) for isi in baris)
                try:
                    templat.rancang(P, "ngawur")
                    raise RuntimeError("template tak dikenal lolos")
                except alat.InputSalah:
                    pass
                return ", ".join(f"{k}: {n} lembar" for k, n in jumlah.items())

            @uji("Analitik", "Saran chart: banyak jenis & semuanya bisa dibangun")
            def _():
                from sps_ai import auto
                jenis, gagal = set(), []
                for ds_id in (P, L):
                    h = auto.sarankan(ds_id, "", None, 40)
                    for sr in {x["jenis"]: x for x in h["saran"]}.values():
                        jenis.add(sr["jenis"])
                        try:
                            tt, lb = lembar.dari_dict({"dataset_id": ds_id, "tanda": sr["jenis"], **sr["spec"]})
                            lembar.ke_superset(tt, lb)
                        except Exception as e:  # noqa: BLE001
                            gagal.append(f"{sr['jenis']}: {e}")
                if gagal or len(jenis) < 12:
                    raise RuntimeError(f"{len(jenis)} jenis; gagal: {gagal[:3]}")
                return f"{len(jenis)} jenis chart diusulkan, semua bisa dibangun"

    @uji("Studio", "Kolom desimal ClickHouse jadi ukuran & tanggal ISO (syarat ramalan)")
    def _():
        from superset.db_engine_specs.clickhouse import ClickHouseConnectEngineSpec as C
        from superset.utils.core import GenericDataType as G
        salah = [t for t in ("Nullable(Float64)", "NULLABLE(FLOAT64)", "Float32", "LowCardinality(Nullable(Float64))",
                             "Nullable(Int64)", "Decimal(18, 2)") if getattr(C.get_column_spec(t), "generic_type", None) != G.NUMERIC]
        teks = C.get_column_spec("LowCardinality(Nullable(String))")
        if salah or teks is None or teks.generic_type != G.STRING:
            raise RuntimeError(f"tipe tidak dikenali sebagai angka: {salah}")
        from datetime import date as _d, datetime as _dt
        from sps_ai.alat import _iso
        if (_iso(_d(2025, 3, 1)), _iso(_dt(2025, 3, 1)), _iso(_dt(2025, 3, 1, 8, 30)), _iso(5)) != \
                ("2025-03-01", "2025-03-01", "2025-03-01T08:30:00", 5):
            raise RuntimeError("tanggal tidak dikirim sebagai ISO")
        return "Float32/64, Double, Int, Decimal = angka; String tetap teks; tanggal ISO"

    @uji("Data", "Data latihan harian: jutaan baris & hierarki Wilayah/Kalender/Produk")
    def _():
        from sps_studio import hierarki
        t = db.session.query(SqlaTable).filter_by(table_name="latihan_penjualan_harian").first()
        if t is None:
            raise RuntimeError("belum ada; jalankan scripts\\data-latihan.ps1")
        from superset.utils.core import override_user
        with override_user(admin):                     # RLS & hak akses dataset dibaca dari g.user
            jumlah = int(lembar.jalankan(*lembar.dari_dict({"dataset_id": t.id, "tanda": "angka",
                                                            "baris": [{"field": "__baris__", "peran": "ukuran"}]}))["baris"][0]["Jumlah baris"])
            nama = {h["nama"] for h in hierarki.daftar(t.id)}
        if jumlah < 1_000_000 or not {"Wilayah", "Kalender", "Produk"} <= nama:
            raise RuntimeError(f"{jumlah} baris, hierarki {sorted(nama)}")
        return f"{jumlah:,}".replace(",", ".") + f" baris, hierarki {', '.join(sorted(nama))}"

    @uji("Data", "Data pendukung latihan: database sumber contoh, role RLS, filter rentang & waktu")
    def _():
        import json as _json
        import sps_latihan_sumber as LS
        from superset.connectors.sqla.models import RowLevelSecurityFilter
        from superset.models.core import Database
        from superset.models.dashboard import Dashboard
        kurang = []
        d = db.session.query(Database).filter_by(database_name=LS.NAMA_KONEKSI).one_or_none()
        if d is None:
            kurang.append("koneksi sumber contoh")
        elif f"{LS.AKUN_BACA}:" not in d.sqlalchemy_uri_decrypted:
            kurang.append("koneksi sumber tidak memakai akun hanya-baca")
        if db.session.query(RowLevelSecurityFilter).filter(RowLevelSecurityFilter.name.like("Latihan: hanya%")).count() < 2:
            kurang.append("aturan RLS contoh")
        dash = db.session.query(Dashboard).filter_by(slug="latihan-wilayah").one_or_none()
        jenis = {f.get("filterType") for f in _json.loads((dash.json_metadata if dash else "") or "{}").get("native_filter_configuration") or []}
        if not {"filter_select", "filter_range", "filter_time"} <= jenis:
            kurang.append(f"filter dashboard wilayah {sorted(jenis)}")
        if kurang:
            raise RuntimeError("belum ada: " + "; ".join(kurang) + " (jalankan scripts\\data-latihan.ps1)")
        return "sumber contoh (hanya-baca), 2 role RLS, filter pilihan + rentang + waktu"

    @uji("Studio", "Kolom ID/kode selalu dimensi (juga dengan alias tabel t1.)")
    def _():
        from sps_ai.auto import kolom_pengenal
        salah = [n for n in ("t1.ID_Penerbangan", "ID_Tiket", "kd_cabang", "provinsi_kode", "NIK", "idPelanggan")
                 if not kolom_pengenal(n)] + [n for n in ("Harga", "total", "t2.harga", "valid_rate") if kolom_pengenal(n)]
        if salah:
            raise RuntimeError(f"salah golong: {salah}")
        return "ID/kode -> dimensi; harga/total -> ukuran"

    @uji("Studio", "Preset tema lolos validasi & tidak menghapus nama perusahaan")
    def _():
        from sps_identitas import skema
        for nama, isi in skema.PRESET.items():
            for k, v in skema.nilai_preset(nama).items():
                skema.periksa(k, v)
        lebih = set(skema.nilai_preset("netral")) - set(skema.KUNCI_TAMPILAN)
        if lebih:
            raise RuntimeError(f"preset bawaan menyentuh {sorted(lebih)}")
        return f"{len(skema.PRESET)} preset; hanya warna, huruf, sudut, hiasan, animasi"

    @uji("Studio", "Objek dashboard: teks aman, huruf lokal, gambar hanya raster")
    def _():
        from pathlib import Path as _P
        from sps_studio import objek
        o = objek.bersihkan({"jenis": "teks", "lebar": 12, "tinggi": 999, "teks": "<script>x</script>\nBaris 2",
                             "huruf": "playfair-display", "ukuran": 500, "warna": "red;}", "rata": "tengah"})
        h = objek.html_objek(o)
        if "<script>" in h or "&lt;script&gt;" not in h or "<br>" not in h:
            raise RuntimeError("teks objek tidak di-escape")
        if (o["tinggi"], o["ukuran"], o["warna"], o["rata"]) != (10, 96, "#111827", "left"):
            raise RuntimeError(f"nilai tidak sah lolos: {o}")
        css = objek.gabung_css(".milik-saya{color:red}", {"playfair-display"}, True)
        css2 = objek.gabung_css(css, set(), False)
        if ".milik-saya" not in css2 or "ALDX-HURUF" in css2 or "playfair-display-latin-700" not in css:
            raise RuntimeError("CSS huruf dashboard salah")
        folder = _P(objek.__file__).parent / "static" / "huruf"
        hilang = [k for k, v in objek.HURUF.items() if v[2] and not (folder / f"{k}-latin-400-normal.woff2").exists()]
        if hilang:
            raise RuntimeError(f"berkas huruf hilang: {hilang}")
        if objek.jenis_gambar(b"\x89PNG\r\n\x1a\n....") != "image/png" or objek.jenis_gambar(b"<svg onload=x>") is not None:
            raise RuntimeError("deteksi format gambar salah")
        return f"{len(objek.HURUF) - 1} huruf lokal, escape & validasi ok"

    @uji("Analitik", "Label periode ramalan")
    def _():
        if prediksi.label_berikut(["2025-11-01", "2025-12-01"], 2) != ["2026-01-01", "2026-02-01"]:
            raise RuntimeError("label bulan salah")
        return "bulanan, tahunan, YYYY-MM"

    # ---- 5. Engine
    @uji("Engine", "Isi penuh (tukar atomik), tambahan, hapus")
    def _():
        import pandas as pd
        k, dbe = K.klien(), K.nama_db()
        k.perintah(f"CREATE DATABASE IF NOT EXISTS {dbe}")
        df = pd.DataFrame({"kd": ["901", "902"], "nilai": [1.5, 2.5], "tgl": pd.to_datetime(["2026-01-01", "2026-02-01"])})
        T.isi_penuh(k, dbe, "uji__otomatis", [df], ["kd"])
        T.isi_penuh(k, dbe, "uji__otomatis", [df], ["kd"])                # kedua kali: EXCHANGE TABLES
        T.isi_tambah(k, dbe, "uji__otomatis", [df.head(1)], T.tipe_tabel(k, dbe, "uji__otomatis"))
        n = T.statistik(k, dbe, "uji__otomatis")["baris"]
        T.hapus(k, dbe, "uji__otomatis")
        if n != 3:
            raise RuntimeError(f"jumlah baris {n}, seharusnya 3")
        return "3 baris benar"

    @uji("Engine", "Daftar & jadwal ekstrak terbaca")
    def _():
        e = ekstrak.daftar()
        return f"{len(e)} ekstrak, {len(ekstrak.jatuh_tempo())} jatuh tempo"

    @uji("Engine", "Impor banyak tabel: perkiraan kapasitas & koneksi sumber")
    def _():
        from sps_engine import impor_banyak as IB
        if IB._perlu_byte(None, 1_000_000) != 300_000 or IB._perlu_byte(1000, None) != 40_000 or IB._perlu_byte(None, None) is not None:
            raise RuntimeError("rumus perkiraan kebutuhan salah")
        kurang = {"postgresql", "mysql", "mssql", "oracle", "clickhouse"} - set(IB.SQL_PERKIRAAN)
        if kurang:
            raise RuntimeError(f"statistik katalog belum ada untuk {sorted(kurang)}")
        return f"{len(IB.koneksi())} koneksi sumber; statistik katalog {len(IB.SQL_PERKIRAAN)} jenis database"

    # ---- 6. Halaman
    from flask import current_app
    klien = current_app.test_client()

    @uji("Halaman", "Versi aplikasi tampil di login & tersedia untuk Beranda")
    def _():
        import re as _re
        import sps_versi_aplikasi as va
        if not _re.fullmatch(r"\d{4}\.\d{2}\.\d{2}(\.\d+)?", va.VERSI) or \
                not va.urutan("2026.11.13.10") > va.urutan("2026.11.13.9") > va.urutan("2026.11.13"):
            raise RuntimeError(f"format VERSI salah: {va.VERSI}")
        if f"v{va.VERSI}" not in klien.get("/login/").get_data(as_text=True):
            raise RuntimeError("versi tidak tampil di halaman login")
        t = va.terbaru()
        return f"v{va.VERSI}; terbaru di GitHub: {t.get('versi') or t.get('pesan')}"

    @uji("Halaman", "/health")
    def _():
        r = klien.get("/health")
        if r.status_code != 200:
            raise RuntimeError(r.status_code)

    for url in ("/app/", "/studio/", "/pusat-kendali/", "/asisten/", "/kueri/", "/jejak-data/", "/kesehatan-kueri/"):
        @uji("Halaman", f"{url} meminta login")
        def _(url=url):
            r = klien.get(url)
            if r.status_code not in (302, 401, 403) or (r.status_code == 302 and "login" not in r.location):
                raise RuntimeError(f"status {r.status_code}")

    @uji("Halaman", "Kueri Visual & cangkang aplikasi tersaji")
    def _():
        for url in ("/kueri/static/kueri.js", "/app/static/app.js", "/app/static/bingkai.js", "/app/static/ai.js",
                    "/app/static/ekspor.js", "/app/static/vendor/html-to-image.js"):
            r = klien.get(url)
            if r.status_code != 200 or b"function" not in r.data:
                raise RuntimeError(f"{url}: status {r.status_code}")

    @uji("Halaman", "Menu tersusun menurut alur BI")
    def _():
        import sps_menu
        from superset.extensions import appbuilder
        sps_menu.susun(appbuilder)
        ada = [m.label for m in appbuilder.menu.menu if m.name in sps_menu.KATEGORI]
        if len(ada) != len(sps_menu.SUSUNAN):
            raise RuntimeError(f"kategori: {ada}")
        return " › ".join(ada)

    # ---- 7. Keamanan
    @uji("Keamanan", "Upload hanya diizinkan ke ALDx Engine")
    def _():
        from superset.db_engine_specs.clickhouse import ClickHouseConnectEngineSpec as CH
        from superset.models.core import Database
        if not CH.supports_file_upload:
            raise RuntimeError("tambalan upload belum terpasang")
        try:
            import pandas as pd
            from superset.sql.parse import Table
            CH.df_to_sql(Database(database_name="Sumber uji"), Table("x"), pd.DataFrame({"a": [1]}), {})
        except Exception as exc:  # noqa: BLE001
            if "ALDx Engine" in str(exc):
                return "ClickHouse lain ditolak"
            raise
        raise RuntimeError("upload ke ClickHouse lain TIDAK ditolak")

    @uji("Keamanan", "RLS sumber ikut di dataset ekstrak")
    def _():
        aturan = db.session.query(RowLevelSecurityFilter).all()
        salah = []
        for e in ekstrak.daftar():
            if not e["dataset_id"]:
                continue
            asal, baru = db.session.query(SqlaTable).get(e["dataset_asal_id"]), db.session.query(SqlaTable).get(e["dataset_id"])
            if asal is None or baru is None:
                continue
            kurang = [r.name for r in aturan if asal in r.tables and baru not in r.tables]
            if kurang:
                salah.append(f"{e['nama']}: {kurang}")
        if salah:
            raise RuntimeError("; ".join(salah))
        return "semua ekstrak sesuai"

    @uji("Keamanan", "Role Superadmin ada & dipegang akun admin instalasi")
    def _():
        import sps_superadmin
        role = sm.find_role(sps_superadmin.ROLE)
        if role is None:
            raise RuntimeError("role Superadmin belum dibuat (jalankan build-dashboards / upgrade)")
        nama = os.environ.get("ADMIN_USERNAME", "admin")
        u = sm.find_user(username=nama)
        if u is None or role not in u.roles:
            raise RuntimeError(f"akun '{nama}' belum Superadmin")
        if not sps_superadmin.adalah(u):
            raise RuntimeError("pemeriksaan adalah() salah")
        return f"'{nama}' Superadmin"

    # ---- 8. Tahap 2
    @uji("Tahap 2", "Batas data terhitung (auto, angka, tanpa batas)")
    def _():
        from sps_server import batas, penyimpanan
        atur = penyimpanan.nilai_semua()
        h = batas.hitung(atur)
        if len(h["daftar"]) != len(batas.KUNCI):
            raise RuntimeError("daftar batas tidak lengkap")
        if batas.berlaku({**atur, "impor.ukuran_mb": 0}, "impor.ukuran_mb") is not None:
            raise RuntimeError("0 harus berarti tanpa batas")
        try:
            list(batas.batasi_baris([[1, 2], [3]], 2, "Uji"))
            raise RuntimeError("batas baris tidak menghentikan data")
        except batas.MelebihiBatas:
            pass
        return f"impor {batas.berlaku(atur, 'impor.ukuran_mb') or 'tanpa batas'} MB"

    @uji("Tahap 2", "Ekspor Excel membuat berkas .xlsx")
    def _():
        from sps_app import ekspor
        isi = ekspor.buat_xlsx("Uji", ["a", "b"], [["x", "1.234,5"]]).getvalue()
        if isi[:2] != b"PK":
            raise RuntimeError("bukan berkas xlsx")
        if ekspor.angka("1.234,5") != 1234.5 or ekspor.angka("007") != "007":
            raise RuntimeError("konversi angka salah")
        return f"{len(isi):,} byte".replace(",", ".")

    @uji("Tahap 2", "Peran Asisten AI & alatnya lengkap")
    def _():
        from sps_ai import agen, peran
        for p in peran.PERAN:
            alat = [a["function"]["name"] for a in agen.alat_peran(p)]
            if alat != list(p.alat):
                raise RuntimeError(f"{p.perintah}: alat {alat}")
        h = peran.kontras("#FFFFFF", "#1E2A44")
        if not h["AA_teks_normal"]:
            raise RuntimeError("perhitungan kontras salah")
        return " ".join(p.perintah for p in peran.PERAN)

    @uji("Tahap 2", "Oracle: batas baris ROWNUM (Oracle 11g) & tipe NUMBER")
    def _():
        from superset.db_engine_specs.oracle import OracleEngineSpec
        from superset.sql.parse import LimitMethod, SQLScript
        skrip = SQLScript("SELECT a FROM genapp.t1 JOIN genapp.t2 ON t1.k = t2.k;", "oracle")
        skrip.statements[-1].set_limit_value(1000, LimitMethod.FORCE_LIMIT)
        sql = skrip.format()
        if "ROWNUM <= 1000" not in sql or "FETCH" in sql.upper():
            raise RuntimeError("batas Oracle masih FETCH FIRST (sps_dialek belum terpasang)")
        spec = OracleEngineSpec.get_column_spec("NUMBER")
        if spec is None or spec.generic_type.name != "NUMERIC":
            raise RuntimeError("NUMBER Oracle belum dikenali sebagai angka")
        return "ROWNUM, NUMBER = angka"

    @uji("Tahap 2", "Skema terpilih menyaring daftar skema")
    def _():
        import sps_skema

        class Db:
            extra = '{"sps_skema": ["GENAPP"]}'
        if sps_skema.batasi(Db(), {"genapp", "iku", "sys"}) != {"genapp"}:
            raise RuntimeError("penyaring skema salah")
        Db.extra = "{}"
        if len(sps_skema.batasi(Db(), {"a", "b"})) != 2:
            raise RuntimeError("tanpa pilihan harus semua skema")
        return "pilihan & tanpa pilihan"

    # ---- Tahap 3
    @uji("Tahap 3", "Berkas .ald/.aldx: enkripsi, sandi, tanda tangan")
    def _():
        from sps_berkas import sandi
        isi = b"PK-uji" * 100
        b1 = sandi.bungkus(isi, "ald")
        if isi in b1 or sandi.buka(b1)[1] != isi or not sandi.buka(b1)[2]:
            raise RuntimeError("kunci server gagal")
        b2 = sandi.bungkus(isi, "aldx", "sandi-uji-123")
        if sandi.buka(b2, "sandi-uji-123")[1] != isi:
            raise RuntimeError("kunci sandi gagal")
        for rusak, kata in ((b2, "salah-sandi-1"), (b1[:-40] + bytes([b1[-40] ^ 1]) + b1[-39:], None)):
            try:
                sandi.buka(rusak, kata)
            except sandi.GalatBerkas:
                continue
            raise RuntimeError("berkas salah sandi / diubah tidak ditolak")
        return "AES-256-GCM, scrypt, HMAC"

    @uji("Halaman", "Kesehatan kueri, ekspor PowerPoint & SSO (tanpa penyedia)")
    def _():
        import io
        import zipfile

        import sps_kesehatan
        import sps_pptx
        import sps_sso
        if sps_kesehatan.persentil([1, 2, 3, 4], 50) != 2.5 or sps_kesehatan.persentil([], 95) != 0:
            raise RuntimeError("persentil salah")
        r = sps_kesehatan.ringkas(30)
        if r["total"]["jalan"] and r["total"]["p95"] < r["total"]["p50"]:
            raise RuntimeError("p95 < median")
        png = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                            "1f15c4890000000d49444154789c6300010000050001"
                            "0d0a2db40000000049454e44ae426082")
        isi = sps_pptx.buat("Uji <&>", "filter", [{"judul": "Chart & \"satu\"", "gambar": png}])
        z = zipfile.ZipFile(io.BytesIO(isi))
        if z.namelist()[0] != "[Content_Types].xml" or "ppt/slides/slide2.xml" not in z.namelist() or b"&amp;" not in z.read("ppt/slides/slide1.xml"):
            raise RuntimeError("berkas pptx salah")
        try:
            sps_pptx.buat("x", "", [{"judul": "", "gambar": b"bukan gambar"}])
            raise RuntimeError("gambar palsu lolos")
        except sps_pptx.GambarSalah:
            pass
        s = sps_sso.Setelan("https://x/.well-known", "id", "rahasia", domain=("kantor.co.id",))
        ok = [sps_sso.email_dari_klaim({"email": "A@Kantor.co.id"}), sps_sso.email_dari_klaim({"preferred_username": "b@kantor.co.id"})]
        if ok != ["a@kantor.co.id", "b@kantor.co.id"] or sps_sso.domain_boleh("c@luar.com", s) or not sps_sso.domain_boleh(ok[0], s):
            raise RuntimeError(f"aturan email/domain SSO salah: {ok}")
        for klaim in ({"email": "x@kantor.co.id", "email_verified": False}, {"sub": "tanpa-email"}):
            try:
                sps_sso.email_dari_klaim(klaim)
                raise RuntimeError(f"klaim SSO tidak sah lolos: {klaim}")
            except sps_sso.SsoGagal:
                pass
        if not sps_sso.aktif():                                # tanpa pengaturan: /sso/masuk kembali ke login
            r2 = klien.get("/sso/masuk")
            if r2.status_code != 302 or "/login" not in r2.location:
                raise RuntimeError(f"/sso/masuk tanpa pengaturan: {r2.status_code}")
        return f"kueri chart 30 hari: {r['total']['jalan']}; pptx 2 slide; SSO {'aktif' if sps_sso.aktif() else 'mati'}"

    @uji("Tahap 3", "Filter global & tabel komentar/rating")
    def _():
        import json as _json
        import sps_filter_global
        from sps_ulasan import model

        class Dash:
            json_metadata = _json.dumps({"native_filter_configuration": [
                {"id": "NATIVE_FILTER-a", "type": "NATIVE_FILTER", "filterType": "filter_select",
                 "targets": [{"column": {"name": "nm_cabang"}}]}]})
        rison, berlaku, tidak = sps_filter_global.native_filters(Dash(), {"NM_CABANG": ["Bandung"], "tahun": [2025]})
        if berlaku != ["nm_cabang"] or tidak != ["tahun"] or "NATIVE_FILTER-a" not in (rison or ""):
            raise RuntimeError("filter global salah: " + str((rison, berlaku, tidak)))
        Dash.id, Dash.slug = 7, "penjualan"
        kec = sps_filter_global._dikecualikan
        if not (kec(Dash(), '["penjualan"]') and kec(Dash(), "[7]") and not kec(Dash(), '["lain"]') and not kec(Dash(), "rusak")):
            raise RuntimeError("pengecualian dashboard filter global salah")
        Dash.dashboard_title = "Tujuan"
        if not sps_filter_global.native_filters(Dash(), {"nm_cabang": ["Bandung"]})[0] or \
                sps_filter_global.native_filters(Dash(), {"kolom_lain": ["x"]})[0] is not None:
            raise RuntimeError("pencocokan dashboard tujuan drill-through salah")
        Dash.id = 987654                                    # tampilan tersimpan (bookmark): simpan, baca, timpa, hapus
        for filter_ in ({"nm_cabang": ["Bandung"]}, {"nm_cabang": ["Jakarta"]}):
            sps_filter_global.simpan_tampilan(Dash(), "uji__akun", "  Cabang   pilihan ", filter_)
        daftar = sps_filter_global.daftar_tampilan(Dash(), "uji__akun")
        if len(daftar) != 1 or daftar[0]["nama"] != "Cabang pilihan" or daftar[0]["filter"] != {"nm_cabang": ["Jakarta"]} \
                or not daftar[0]["native_filters"] or sps_filter_global.daftar_tampilan(Dash(), "akun_lain"):
            raise RuntimeError(f"tampilan tersimpan salah: {daftar}")
        sps_filter_global.hapus_tampilan("akun_lain", daftar[0]["id"])           # bukan pemilik: tidak terhapus
        if not sps_filter_global.daftar_tampilan(Dash(), "uji__akun"):
            raise RuntimeError("tampilan bisa dihapus akun lain")
        sps_filter_global.hapus_tampilan("uji__akun", daftar[0]["id"])
        try:
            sps_filter_global.simpan_tampilan(Dash(), "uji__akun", "kosong", {})
            raise RuntimeError("tampilan tanpa filter lolos")
        except ValueError:
            pass
        if sps_filter_global.daftar_tampilan(Dash(), "uji__akun"):
            raise RuntimeError("tampilan tidak terhapus")
        model.ringkasan("dashboard", 0)                     # membuat tabel sps_ulasan bila belum ada
        return f"native_filters & pengecualian ok, {model.jumlah_menunggu()} ulasan menunggu moderasi"

    @uji("Tahap 3", "HTTPS gateway: sertifikat otomatis & konfigurasi")
    def _():
        import tempfile
        from pathlib import Path as _P
        from sps_server import gateway, tls
        lama = (tls.SERTIFIKAT, tls.KUNCI)
        with tempfile.TemporaryDirectory() as d:
            tls.SERTIFIKAT, tls.KUNCI = _P(d) / "aldx.crt", _P(d) / "aldx.key"
            try:
                ket = tls.pastikan()
                if not tls.SERTIFIKAT.exists() or b"PRIVATE KEY" not in tls.KUNCI.read_bytes():
                    raise RuntimeError("sertifikat tidak dibuat")
            finally:
                tls.SERTIFIKAT, tls.KUNCI = lama
        atur = {"web.timeout_detik": 330, "upload.ukuran_mb": 25, "impor.ukuran_mb": 25}
        c = gateway.buat_conf(atur, [], https=True)
        if "listen 80 ssl" not in c or "error_page 497" not in c or "listen 8081" not in c:
            raise RuntimeError("konfigurasi HTTPS gateway tidak lengkap")
        if "ssl" in gateway.buat_conf(atur, [], https=False).split("listen 8081")[0]:
            raise RuntimeError("HTTP biasa tidak boleh memakai ssl")
        return ket.split(" (")[0]

    # ---- Keamanan tahap 1 (penguncian, audit, hak minimum, data impor)
    @uji("Keamanan", "Penguncian akun & jejak audit")
    def _():
        import sps_audit
        import sps_kunci
        from sps_server import penyimpanan
        maks = int(penyimpanan.nilai_semua().get("keamanan.login_maks_gagal", 5))
        if maks <= 0:
            return "penguncian dimatikan di Pengaturan (keamanan.login_maks_gagal = 0)"
        nama = "uji-kunci@aldx.invalid"
        try:
            for _i in range(maks):
                sps_kunci.gagal(nama, "uji")
            if sps_kunci.terkunci_sampai(nama) is None:
                raise RuntimeError(f"akun tidak terkunci setelah {maks} kali salah")
            sps_kunci.buka(nama, "uji")
            if sps_kunci.terkunci_sampai(nama) is not None:
                raise RuntimeError("kunci tidak terbuka")
            if not any(b["aksi"] == "Akun dikunci" for b in sps_audit.daftar(20, "login", nama)):
                raise RuntimeError("penguncian tidak tercatat di jejak audit")
        finally:
            sps_kunci.buka(nama, "uji")
        return f"terkunci setelah {maks} kali salah, tercatat di audit"

    @uji("Keamanan", "Hak minimum role bawaan & akses semua data")
    def _():
        from sps_server import izin
        gamma = sm.find_role("Gamma")
        bocor = sorted({pv.view_menu.name for pv in (gamma.permissions if gamma else [])
                        if sm._is_admin_only(pv) or sm._is_alpha_only(pv)})
        if bocor:
            raise RuntimeError("Gamma masih punya izin admin/analis: " + ", ".join(bocor[:6]) +
                               " (jalankan scripts\\build-dashboards.ps1)")
        semua = izin.peringatan_akses()
        if semua:                                            # peringatan, bukan galat: bisa disengaja
            return "PERINGATAN: non-Admin bisa melihat semua data: " + ", ".join(x["username"] for x in semua[:5])
        return "Gamma bersih; tidak ada non-Admin dengan akses semua data"

    @uji("Ketahanan", "Ekspor .aldx latar, batas berkas & status cadangan")
    def _():
        from sps_berkas import tugas
        from sps_server import monitor, penyimpanan
        tugas.pastikan_tabel()
        if tugas.ekspor_latar is None or tugas.ekspor_latar.name != "sps.berkas.ekspor":
            raise RuntimeError("tugas backgrounder sps.berkas.ekspor tidak terdaftar")
        mb = int(penyimpanan.nilai_semua().get("berkas.ukuran_mb") or 0)
        c = monitor.cadangan().get("cadangan")
        ket = f"cadangan terakhir {c['waktu']} ({c['hasil']})" if c else "belum ada cadangan (scripts\\jadwal-cadangan.ps1)"
        return f"backgrounder {'ada' if tugas.ada_worker() else 'tidak menjawab: ekspor langsung'}; berkas maks {mb} MB; {ket}"

    # ---- Hubungkan data
    @uji("Hubungkan data", "driver database & berkas terpasang")
    def _():
        from sps_koneksi import katalog
        kurang = [j.nama for j in katalog.KATALOG if not j.driver_ada() and not j.opsional]
        for modul in ("access_parser", "xlrd", "openpyxl", "duckdb"):
            if importlib.util.find_spec(modul) is None:
                kurang.append(modul)
        if kurang:
            raise RuntimeError("belum terpasang: " + ", ".join(kurang) + " (lihat docker/wheels/README.md)")
        opsional = [j.nama for j in katalog.KATALOG if j.opsional and not j.driver_ada()]
        ket = f"; opsional belum dipasang: {', '.join(opsional)}" if opsional else ""
        return f"{len(katalog.KATALOG)} jenis database + Access/Excel/CSV/SQLite/DuckDB/Parquet{ket}"

    # ---- Fitur 10 November 2026 (QA putaran 2)
    @uji("2026.11.10", "Role pendamping lengkap & tersimpan (Pengguna+Gamma, Superadmin+Admin)")
    def _():
        import sps_security
        kurang = []
        for u in sm.get_all_users():
            nama = {r.name for r in u.roles}
            if "Superadmin" in nama and sm.auth_role_admin not in nama:
                kurang.append(f"{u.username}: Superadmin tanpa Admin")
            if sps_security.ROLE_PENGGUNA in nama and not nama & {"Gamma", "Alpha", sm.auth_role_admin}:
                kurang.append(f"{u.username}: {sps_security.ROLE_PENGGUNA} tanpa Gamma")
        if kurang:
            raise RuntimeError("; ".join(kurang[:3]) + " (dilengkapi otomatis saat akun login berikutnya)")
        return f"{len(sm.get_all_users())} akun sesuai"

    @uji("2026.11.10", "Panduan di aplikasi: semua halaman menu ada & pencarian")
    def _():
        from sps_panduan import tampilan as P
        hilang = [h for _, isi in P.NAVIGASI for h, _ in isi if P._berkas(h.rstrip("/") + ("/" if h.endswith("/") else "")) is None]
        if hilang:
            raise RuntimeError("halaman tidak ada: " + ", ".join(hilang))
        isi = P._indeks_cari()
        if not any("ollama" in t.lower() for _, _, t in isi):
            raise RuntimeError("pencarian tidak menemukan 'ollama'")
        return f"{sum(len(i) for _, i in P.NAVIGASI)} halaman menu, {len(isi)} halaman terindeks"

    @uji("Dokumentasi", "Tautan & gambar relatif di semua dokumen tidak mati; setiap menu tercakup tutorial")
    def _():
        import re as _re
        from sps_panduan import tampilan as P
        mati, jumlah = [], 0
        for md in sorted(P.DOCS.rglob("*.md")):
            teks = _re.sub(r"`[^`\n]*`", "", _re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=_re.S))
            for t in _re.findall(r"!?\[[^\]]*\]\(([^)\s]+)", teks) + _re.findall(r'(?:src|href)="([^"]+)"', teks):
                if _re.match(r"(https?:|mailto:|#|\{)", t) or "releases" in t:
                    continue
                jumlah += 1
                tujuan = (md.parent / t.split("#")[0]).resolve()
                try:
                    tujuan.relative_to(P.DOCS.resolve())
                except ValueError:                       # menunjuk ke luar docs/ (README, docker/, ...): tidak ada di container
                    continue
                if t.split("#")[0] and not tujuan.exists():
                    mati.append(f"{md.relative_to(P.DOCS)} -> {t}")
        if mati:
            raise RuntimeError(f"{len(mati)} tautan mati: " + "; ".join(mati[:4]))
        peta = (P.DOCS / "33-peta-menu-per-level.md").read_text(encoding="utf-8")
        tanpa = [n for n in ("Hubungkan data", "Jejak data", "Studio Visual", "Daftar chart", "Langganan laporan", "Peringatan data",
                             "Sematkan ke web lain", "Auto chart & dashboard", "Kesehatan kueri", "Jejak audit", "Moderasi ulasan")
                 if f"**{n}**" not in peta]
        if tanpa:
            raise RuntimeError("peta menu tidak memuat: " + ", ".join(tanpa))
        return f"{jumlah} tautan/gambar diperiksa, semuanya ada; peta menu lengkap"

    @uji("2026.11.10", "Asisten AI: peta pengetahuan, konteks dashboard, kunci terenkripsi")
    def _():
        from sps_ai import kunci_api, status, pengaturan, wawasan
        with override_user(admin):
            from flask import g
            g.user = admin
            wawasan.lupakan(admin.id)
            peta = wawasan.ringkasan_katalog(admin.id)
            konteks = wawasan.konteks_halaman("/superset/dashboard/latihan/", dengan_data=True)
        if "DATASET" not in peta or "DASHBOARD" not in konteks:
            raise RuntimeError("peta / konteks dashboard kosong")
        kunci_api.simpan("AI_UJI_ASAP", "kunci-uji-12345678", "uji")
        ok = kunci_api.semua().get("AI_UJI_ASAP") == "kunci-uji-12345678"
        kunci_api.simpan("AI_UJI_ASAP", "", "uji")
        if not ok:
            raise RuntimeError("kunci terenkripsi tidak terbaca kembali")
        lokal = status.temukan(pengaturan.sumber_lokal())
        hidup = [s["nama"] for s in lokal if s["aktif"]]
        return f"peta {peta.count(chr(10) + '- [')} objek; lokal menyala: {', '.join(hidup) or 'tidak ada'}"

    _ = sps_latihan  # modul data latihan harus bisa dimuat


def cetak() -> int:
    lebar = max(len(n) for _, n, _, _ in HASIL)
    kelompok = None
    for k, n, ok, ket in HASIL:
        if k != kelompok:
            print(f"\n[{k}]")
            kelompok = k
        print(f"  {'LULUS' if ok else 'GAGAL'}  {n.ljust(lebar)}  {ket}")
    gagal = sum(1 for *_, ok, _ in HASIL if not ok)
    print(f"\n{len(HASIL) - gagal}/{len(HASIL)} lulus" + (f", {gagal} GAGAL" if gagal else ""))
    return 1 if gagal else 0


if __name__ == "__main__":
    from superset.app import create_app
    with create_app().app_context():
        jalankan_semua()
    sys.exit(cetak())
