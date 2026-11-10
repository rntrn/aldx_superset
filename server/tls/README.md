# server/tls/ — sertifikat HTTPS gateway

Dipakai bila HTTPS aktif (`SPS_HTTPS=1` di `.env`, atau centang **Pakai HTTPS** di installer).

| Berkas | Isi |
|---|---|
| `aldx.crt` | sertifikat (PEM) |
| `aldx.key` | kunci privat (PEM) — **jangan dibagikan / jangan di-commit** |

- **Belum punya sertifikat?** Biarkan folder ini kosong. `scripts\terapkan-server.ps1` membuat sertifikat
  sendiri (*self-signed*, berlaku 10 tahun) untuk nama komputer ini, `localhost`, dan nama di `SPS_HTTPS_NAMA`.
  Browser menampilkan peringatan sekali. Agar hilang di komputer pengguna: jalankan
  `scripts\percayai-sertifikat.ps1` di komputer itu (atau sebarkan `aldx.crt` lewat GPO kantor).
- **Punya sertifikat kantor?** Taruh di sini dengan nama di atas, lalu `scripts\terapkan-server.ps1`.
