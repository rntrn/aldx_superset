# docker/wheels

Paket Python (file `.whl`) yang dipasang ke image **tanpa internet**.

Alasan: jaringan kantor memeriksa koneksi HTTPS (SSL inspection), sehingga
`pip`/`uv` di dalam Docker gagal dengan `invalid peer certificate: UnknownIssuer`.

- Daftar paket yang dipasang: [`paket.txt`](paket.txt) (satu nama per baris, beserta kegunaannya).
- Folder ini berisi paket tersebut **beserta dependensi yang belum ada di image** (47 file, ±63 MB).
  Diuji pada lingkungan yang sama persis dengan image `apache/superset:6.1.0`
  (Python 3.10 + versi terkunci di `requirements/base.txt` Superset 6.1.0, mis. `requests 2.32.4`):
  terpasang tanpa internet, `uv pip check` bersih, semua driver bisa di-import.

### Cara menguji ulang (pengembang, setelah mengganti versi Superset atau menambah driver)

```
curl -LO https://raw.githubusercontent.com/apache/superset/<versi>/requirements/base.txt
uv venv -p 3.10 img && uv pip install --python img/bin/python -r base.txt (tanpa baris "-e")
uv pip freeze --python img/bin/python > beku.txt
uv pip compile paket.txt -c beku.txt --python-version 3.10 -o hasil.txt   # pilih versi yang cocok
# unduh .whl untuk paket di hasil.txt yang versinya berbeda dari beku.txt, lalu:
uv pip install --python img/bin/python --no-index --find-links . -r paket.txt && uv pip check
```

| Kelompok | Paket | Kegunaan |
|---|---|---|
| Wajib | `psycopg2-binary` | metadata Superset (PostgreSQL) + sumber PostgreSQL/Redshift |
| Wajib | `ldap3`, `pyasn1` | login LDAP / Active Directory |
| Wajib | `clickhouse-connect`, `lz4` | ALDx Engine + sumber ClickHouse |
| Wajib | `oracledb` | sumber Oracle |
| Wajib | `pymysql` | sumber MySQL/MariaDB + pindah metadata versi lama |
| Wizard | `pymssql`, `snowflake-sqlalchemy`, `sqlalchemy-bigquery`, `sqlalchemy-redshift`, `databricks-*`, `trino`, `pyathena`, `duckdb-engine`, `sqlalchemy-vertica-python`, `pydruid` | sumber data pada wizard "Hubungkan data" |
| Impor | `access-parser`, `xlrd` | impor Microsoft Access (.mdb/.accdb) & Excel lama (.xls) |
| Opsional | `sqlalchemy-hana` + `hdbcli` | SAP HANA, hanya bila `hdbcli` ditaruh sendiri (di bawah) |

Teradata tidak disertakan (driver 127 MB). Tambahkan sendiri bila perlu (langkah di bawah).

## SAP HANA (opsional)

Driver resmi SAP (`hdbcli`) berlisensi **SAP Developer License** (proprietary), jadi tidak boleh ikut dibagikan
di repo ini. `sqlalchemy-hana` (Apache-2.0) sudah ada di folder ini dan otomatis dipasang begitu `hdbcli` tersedia:

1. Unduh dari https://pypi.org/project/hdbcli/#files berkas `hdbcli-<versi>-cp310-abi3-manylinux2014_x86_64.whl`
   (teruji: 2.30.27). Dengan mengunduhnya Anda menyetujui lisensi SAP.
2. Simpan di folder ini (berkas `hdbcli-*.whl` diabaikan git, jadi tetap ada saat repo diperbarui).
3. `scripts\init.ps1` (atau `docker compose build`). Kartu **SAP HANA** di wizard aktif.

Tanpa langkah ini semua fitur lain berjalan normal; kartu SAP HANA tampil nonaktif dengan petunjuk di atas.

## Menambah driver baru

1. Di komputer yang punya internet & Python 3.10:
   ```
   pip download --only-binary=:all: --python-version 3.10 --platform manylinux2014_x86_64 -d . <nama-paket>
   ```
   atau unduh lewat browser dari https://pypi.org (menu *Download files*): pilih
   `py3-none-any.whl` atau `cp310-...-manylinux...x86_64.whl`. Sertakan dependensinya.
2. Simpan semua `.whl` di folder ini.
3. Tambahkan nama paketnya di `paket.txt`.
4. `docker compose build` — bila ada dependensi yang kurang, build gagal dengan pesan
   `Because <paket> was not found ...`; unduh paket itu lalu ulangi.
