"""ALDx App — cangkang aplikasi (/app/): satu rumah untuk seluruh pekerjaan BI.

Yang dilihat pengguna:
    sidebar     Beranda · Data · Kueri · Visual · Dashboard · Story · Asisten AI · Kelola
                (urutan = urutan membuat laporan; di ponsel menjadi bilah tab bawah)
    bilah atas  judul halaman, Cari & perintah (Ctrl+K), Bantuan (?), bahasa, akun
    isi         Beranda dibangun sendiri; halaman lain (Superset & halaman ALDx) tampil di bingkai
                yang menyatu, tanpa navbar ganda

Cara kerja singkat:
    - Alamat halaman Superset/ALDx yang dibuka langsung di tab browser diarahkan ke
      /app/?p=<alamat>, jadi pengguna selalu berada di cangkang yang sama (tampilan.alihkan_ke_app).
    - Halaman di dalam bingkai mendapat bingkai.js (sembunyikan navbar lama, teruskan pintasan
      keyboard, laporkan judul & alamat ke cangkang, terjemahkan halaman ALDx).
    - Hak akses: daftar menu diambil dari /api/v1/menu/ (izin Superset + sps_menu), jadi item yang
      tidak boleh dibuka tidak tampil.

Struktur:
    tampilan.py         blueprint /app, pengalihan, penyisipan bingkai.js
    halaman.html        kerangka HTML cangkang
    static/app.css      design system (token, komponen, animasi, responsif)
    static/ikon.js      ikon SVG garis
    static/i18n.js      bahasa id/en/ja: t(), penerjemah DOM (dipakai cangkang & halaman ALDx)
    static/app.js       navigasi, bingkai, palet perintah, pintasan, bantuan
    static/beranda.js   halaman Beranda
    static/bingkai.js   skrip di dalam bingkai
    static/bahasa/*.json  kamus terjemahan (kunci = teks Indonesia)
    static/bantuan/*.json isi panel Bantuan per halaman (id, en, ja)
"""


def daftarkan(app) -> None:
    """FLASK_APP_MUTATOR: blueprint /app + pengalihan halaman ke cangkang."""
    from sps_app import tampilan
    tampilan.daftarkan(app)
