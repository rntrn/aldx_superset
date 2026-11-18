"""Penerjemah niat: perintah UBAH yang umum dikenali TANPA model AI -> operasi ALDx Rencana (rencana.py).

Kenapa: model lokal kecil sering bingung memilih alat & mengisi argumen. Perintah pengelolaan yang
polanya jelas ("tambah filter cabang di dashboard tes1", "ubah chart X jadi batang") langsung dipahami
di sini: cepat, tidak bergantung model, tidak bisa gagal karena server model sibuk.
Nama yang ditangkap boleh tidak persis; rencana.py yang mencocokkan & bertanya balik bila ambigu.

    baca("dari dashboard tes1 buatkan filtrasi yang berlaku di semua chart")
      -> [{"op": "tambah_filter", "dashboard": "tes1", "kolom": ""}]
    baca("berapa penjualan bulan ini?") -> None   (bukan perintah ubah: diteruskan ke model AI)
"""

from __future__ import annotations

import re

_SETOP = (r"buat|bikin|tambah|pasang|kasih|beri|hapus|buang|hilangkan|copot|keluarkan|ganti|ubah|jadikan|"
          r"yang|untuk|agar|supaya|dengan|dan|jadi|menjadi|filter|filtrasi|ke|dari|di|pada|tolong|mohon")
_HENTI = rf"(?=\s+(?:{_SETOP})\w*\b|\s*[,.;!?]|\s*$)"
_KUTIP = "\"'“”‘’`"

_FILTER = r"(?:filter|filtrasi|penyaring|saringan|slicer)\w*"
P_DASHBOARD = re.compile(rf"\bdash(?:board|bor)\s+(?:bernama\s+|berjudul\s+)?(.+?){_HENTI}", re.I)
P_HAPUS_FILTER = re.compile(rf"\b(?:hapus|buang|hilangkan|copot|lepas)\w*\s+{_FILTER}\s*(.*?)"
                            r"(?=\s+(?:di|pada|dari)\s+dash|\s+dash(?:board|bor)\b|\s*[,.;!?]|\s*$)", re.I)
P_TAMBAH_FILTER = re.compile(rf"\b(?:tambah|buat|pasang|bikin|kasih|beri|sediakan|tampilkan)\w*\b.*?\b{_FILTER}\b"
                             rf"|\b{_FILTER}\s+(?:\w+\s+){{0,3}}(?:di|pada|untuk|ke)\s+dash", re.I)
P_KOLOM_FILTER = re.compile(rf"\b{_FILTER}\s+(?:berdasarkan\s+|per\s+|kolom\s+|untuk\s+kolom\s+|by\s+)?(.+?)"
                            r"(?=\s+(?:di|pada|ke|untuk|dari|yang|agar|supaya|biar|dash(?:board|bor)|sehingga)\b|\s*[,.;!?]|\s*$)", re.I)
P_BERDASAR = re.compile(r"\b(?:berdasarkan|per)\s+(?:kolom\s+)?(.+?)"
                        r"(?=\s+(?:di|pada|ke|untuk|dari|yang|agar|supaya|biar|dash(?:board|bor)|sehingga)\b|\s*[,.;!?]|\s*$)", re.I)
P_JUDUL = re.compile(r"\b(?:ganti|ubah|rubah|perbarui)\w*\s+(?:judul|nama)\s+(dash(?:board|bor)|chart|grafik|diagram)\s+"
                     r"(.*?)\s*(?:jadi|menjadi|ke|dengan)\s+(.+)$", re.I)
P_JENIS = re.compile(r"\b(?:ganti|ubah|rubah|jadikan|tukar)\w*\s+(?:chart|grafik|diagram|visual)\s+(.*?)\s*"
                     r"(?:jadi|menjadi|ke|sebagai|dengan)\s+(?:bentuk\s+|jenis\s+|tipe\s+)?(?:grafik\s+|chart\s+|diagram\s+)?(.+)$", re.I)
_JENIS_KATA = (r"batang|bar|kolom|garis|line|tren|pie|donat|donut|lingkaran|tabel pivot|pivot|tabel|table|angka|kpi|"
               r"area|treemap|peta panas|heatmap|corong|funnel|sebar|scatter|radar|sunburst|waterfall|awan kata|"
               r"sankey|gauge|box plot")
P_JADIKAN = re.compile(rf"\bjadikan\s+(?:chart|grafik|diagram|visual)\s+(.+?)\s+(?:sebagai\s+)?(?:grafik\s+|chart\s+|diagram\s+)?"
                       rf"({_JENIS_KATA})\s*[.!]?$", re.I)
P_TAMBAH_CHART =re.compile(r"\b(?:tambah|masukkan|masukan|taruh|letakkan|pasang)\w*\s+(?:chart|grafik|diagram)\s+(.+?)\s+"
                            r"(?:ke|di|pada)\s+(?:dalam\s+)?dash(?:board|bor)\s*(.*)$", re.I)
P_BUANG_CHART = re.compile(r"\b(?:keluarkan|buang|hapus|copot|singkirkan|lepas)\w*\s+(?:chart|grafik|diagram)\s+(.+?)\s+"
                           r"dari\s+(?:dalam\s+)?dash(?:board|bor)\s*(.*)$", re.I)

_TANPA_KOLOM = re.compile(r"^(?:yang|untuk|di|pada|agar|supaya|biar|ini|itu|baru|global|umum|semua|"
                          r"bisa|berlaku|dashboard|nya|ya|dong|sekalian)\b", re.I)
_KATA_WAKTU = re.compile(r"\b(?:waktu|tanggal|periode|rentang waktu|range waktu)\b", re.I)


def _bersih(s: str | None) -> str:
    s = (s or "").strip().strip(_KUTIP).strip()
    s = re.sub(r"\s+(?:ya|dong|deh|sekalian|saja|aja|tolong)$", "", s, flags=re.I)
    s = re.sub(r"^(?:yang\s+)?(?:bernama|berjudul|namanya|judulnya)\s+", "", s, flags=re.I)
    return s.strip().strip(_KUTIP).strip(" .,:;!?")


def _nama_dashboard(teks: str) -> str:
    m = P_DASHBOARD.search(teks)
    return _bersih(m.group(1)) if m else ""


def _kolom_filter(teks: str) -> str:
    for p in (P_KOLOM_FILTER, P_BERDASAR):
        for m in p.finditer(teks):
            k = _bersih(m.group(1))
            if k and not _TANPA_KOLOM.match(k) and not re.match(r"^dash", k, re.I):
                return k
    return ""


def baca(teks: str) -> list[dict] | None:
    """Kalimat pengguna -> daftar operasi rencana, atau None bila bukan perintah ubah yang dikenali."""
    t = re.sub(r"^/[\w-]+\s*", "", str(teks or "")).strip()
    t = re.sub(r"^(?:tolong|mohon|coba|bisa|bisakah|minta)\s+", "", t, flags=re.I)
    if not t or len(t) > 300 or "?" in t[:-1]:
        return None

    m = P_JUDUL.search(t)
    if m:
        objek, nama, judul = m.group(1).lower(), _bersih(m.group(2)), _bersih(m.group(3))
        if objek.startswith("dash"):
            return [{"op": "ganti_judul_dashboard", "dashboard": nama, "judul": judul}]
        return [{"op": "ganti_judul_chart", "chart": nama, "judul": judul}]

    m = P_BUANG_CHART.search(t)
    if m:
        return [{"op": "buang_chart", "chart": _bersih(m.group(1)), "dashboard": _bersih(m.group(2))}]
    m = P_TAMBAH_CHART.search(t)
    if m:
        return [{"op": "tambah_chart", "chart": _bersih(m.group(1)), "dashboard": _bersih(m.group(2))}]

    m = P_JENIS.search(t) or P_JADIKAN.search(t)
    if m:
        return [{"op": "ubah_jenis_chart", "chart": _bersih(m.group(1)), "jenis": _bersih(m.group(2))}]

    m = P_HAPUS_FILTER.search(t)
    if m:
        return [{"op": "hapus_filter", "kolom": _bersih(m.group(1)), "dashboard": _nama_dashboard(t)}]

    if P_TAMBAH_FILTER.search(t):
        kolom = _kolom_filter(t)
        o = {"op": "tambah_filter", "dashboard": _nama_dashboard(t), "kolom": kolom}
        if re.search(r"\brentang\b|\brange\b|\bantara\b", t, re.I) and not _KATA_WAKTU.search(t):
            o.update(jenis="rentang", kolom=re.sub(r"^(?:rentang|range)\s+", "", kolom, flags=re.I))
        if _KATA_WAKTU.search(kolom or "") or (not kolom and _KATA_WAKTU.search(t)):
            o.update(kolom="waktu", jenis="waktu")
        return [o]
    return None
