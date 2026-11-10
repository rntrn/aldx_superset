# server/ — berkas yang dikelola Pusat Kendali Server

| Berkas | Isi | Dibuat oleh |
|---|---|---|
| `gateway.conf` | Konfigurasi gateway nginx: daftar node web, timeout, ukuran upload | `scripts\terapkan-server.ps1` |

- **Jangan edit manual.** Ubah lewat halaman **Pusat Kendali Server**
  (`http://localhost:8088/pusat-kendali/`), lalu jalankan `scripts\terapkan-server.ps1`.
- Folder ini di-mount ke container sebagai `/app/server` (satu-satunya folder yang bisa ditulis container).
- Pengaturan server itu sendiri disimpan di database `sps_superset` (tabel `sps_server_atur`),
  jadi semua node membaca pengaturan yang sama.
