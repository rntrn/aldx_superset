# docker/oracle — Oracle Instant Client (mode thick)

Wajib bila server Oracle **di bawah 12.1** (error `DPY-3010` di Superset).

## Isi folder ini

| File | Wajib | Dari mana |
|---|---|---|
| `instantclient-basic-linux.x64-19.*.zip` | Ya | Unduh via browser (lihat bawah) |
| `libaio*.deb` | Hanya bila build gagal di langkah `apt-get` | packages.debian.org (lihat bawah) |
| `install-instantclient.sh` | — | Skrip pemasang (jangan diubah) |

## Mengunduh Instant Client

1. Buka https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
2. Bagian **Version 19.x** (sama dengan versi Windows di PC: 19.30) →
   **Basic Package (ZIP)**, nama file seperti `instantclient-basic-linux.x64-19.30.0.0.0dbru.zip`.
   - Harus **Linux x86-64**, bukan Windows.
   - Pilih **Basic**, bukan *Basic Light* (Light hanya mendukung sebagian character set).
3. Simpan di folder ini (`D:\superset\docker\oracle\`). Jangan diekstrak.

Versi 19 dipilih karena masih bisa terhubung ke Oracle 11.2, sedangkan 21/23 tidak.

## Bila build gagal saat memasang libaio

Jaringan kantor bisa saja memblokir `apt-get`. Unduh manual lewat browser:
- Debian trixie: https://packages.debian.org/trixie/amd64/libaio1t64/download
- Debian bookworm: https://packages.debian.org/bookworm/amd64/libaio1/download

Simpan file `.deb`-nya di folder ini, lalu build ulang.
