# Lisensi Pihak Ketiga

ALDx dilisensikan dengan **Apache License 2.0** ([LICENSE](LICENSE), [NOTICE](NOTICE)): bebas dipakai,
diubah, dan dibagikan ulang, termasuk untuk keperluan komersial, asalkan berkas `LICENSE` dan `NOTICE`
ikut disertakan dan perubahan penting dicatat.

Berkas ini mencatat semua komponen pihak ketiga yang dipakai atau disertakan, beserta lisensinya.
Semua lisensi di bawah **sejalan** dengan Apache 2.0 untuk cara pakai ALDx (dipakai apa adanya, tidak diubah).

## 1. Disertakan di repo ini

| Komponen | Lokasi | Lisensi | Catatan |
|---|---|---|---|
| Apache ECharts 5.6.1 | `config/sps_studio/static/echarts.min.js` | Apache-2.0 (+ subkomponen BSD-3-Clause) | teks lengkap: `config/sps_studio/static/ECHARTS_LICENSE.txt` |
| html-to-image 1.11.11 | `config/sps_app/static/vendor/html-to-image.js` | MIT | pemberitahuan hak cipta ada di kepala berkas |
| Peta provinsi Indonesia | `config/sps_studio/static/indonesia.geojson` | Apache-2.0 | salinan dari peta negara Apache Superset 6.1.0 |
| Plus Jakarta Sans | `branding/fonts/` | SIL Open Font License 1.1 | teks lisensi: `branding/fonts/OFL-PlusJakartaSans.txt`; font tidak boleh dijual tersendiri |
| Paket Python (driver) | `docker/wheels/*.whl` | lihat tabel §2 | dipasang ke image saat build, tanpa internet |

Ikon antarmuka (`config/sps_app/static/ikon.js`), kode, dokumentasi, gambar, dan data latihan dibuat sendiri
dan ikut berlisensi Apache 2.0. Data latihan seluruhnya fiktif.

## 2. Paket Python di `docker/wheels/`

Setiap berkas `.whl` membawa teks lisensinya sendiri (folder `*.dist-info/` di dalam berkas).

| Paket | Versi | Lisensi |
|---|---|---|
| access_parser | 0.0.6 | Apache-2.0 |
| asn1crypto | 1.5.1 | MIT |
| backports.zstd | 1.8.0 | PSF-2.0 |
| boto3 | 1.43.121 | Apache-2.0 |
| botocore | 1.43.121 | Apache-2.0 |
| clickhouse-connect | 1.11.0 | Apache-2.0 |
| construct | 2.10.70 | MIT |
| databricks-sql-connector | 4.8.0 | Apache-2.0 |
| databricks-sqlalchemy | 1.0.5 | Apache-2.0 |
| duckdb | 1.5.6 | MIT |
| duckdb_engine | 0.17.0 | MIT |
| fsspec | 2026.9.0 | BSD-3-Clause |
| google-api-core | 2.30.3 | Apache-2.0 |
| google-cloud-bigquery | 3.46.2 | Apache-2.0 |
| google-cloud-core | 2.8.0 | Apache-2.0 |
| google-crc32c | 1.9.0 | Apache-2.0 |
| google-resumable-media | 2.11.0 | Apache-2.0 |
| googleapis-common-protos | 1.76.0 | Apache-2.0 |
| grpcio | 1.85.0 | Apache-2.0 |
| grpcio-status | 1.85.0 | Apache-2.0 |
| jmespath | 1.1.0 | MIT |
| ldap3 | 2.9.1 | LGPL-3.0 |
| lz4 | 4.4.5 | BSD |
| oauthlib | 4.0.0 | BSD-3-Clause |
| oracledb | 26.1.0 | UPL-1.0 OR Apache-2.0 |
| orjson | 3.13.0 | MPL-2.0 AND (Apache-2.0 OR MIT) |
| proto-plus | 1.29.0 | Apache-2.0 |
| protobuf | 7.36.2 | BSD-3-Clause |
| psycopg2-binary | 2.9.13 | LGPL-3.0 (dengan pengecualian) |
| PyAthena | 3.40.0 | MIT |
| pybreaker | 1.4.1 | BSD |
| pydruid | 0.6.9 | Apache-2.0 |
| pymssql | 2.4.6 | LGPL-2.1 |
| PyMySQL | 1.2.3 | MIT |
| s3transfer | 0.19.3 | Apache-2.0 |
| snowflake-connector-python | 4.8.0 | Apache-2.0 |
| snowflake-sqlalchemy | 1.11.1 | Apache-2.0 |
| sqlalchemy-bigquery | 1.17.3 | MIT |
| sqlalchemy-hana | 3.0.3 | Apache-2.0 |
| sqlalchemy-redshift | 0.8.14 | MIT |
| sqlalchemy-vertica-python | 0.6.3 | MIT |
| tenacity | 9.2.1 | Apache-2.0 |
| thrift | 0.25.0 | Apache-2.0 |
| tomlkit | 0.15.2 | MIT |
| trino | 0.340.0 | Apache-2.0 |
| tzlocal | 5.4.5 | MIT |
| vertica-python | 1.4.0 | Apache-2.0 |

**LGPL** (`ldap3`, `psycopg2-binary`, `pymssql`): boleh dibagikan bersama aplikasi berlisensi lain selama
paketnya tidak diubah, teks lisensinya ikut (sudah ada di dalam `.whl`), dan pengguna bebas menggantinya
dengan versi lain. Ketiganya dipasang apa adanya sebagai paket terpisah, jadi syarat ini terpenuhi.
**MPL-2.0** (sebagian `orjson`): idem, berlaku per berkas yang diubah; tidak ada yang diubah.

## 3. Image Docker (diunduh saat instalasi, tidak disimpan di repo)

| Komponen | Image | Lisensi |
|---|---|---|
| Apache Superset 6.1.0 | `apache/superset` | Apache-2.0 |
| PostgreSQL 17 | `postgres` | PostgreSQL License (mirip MIT) |
| ClickHouse 25.8 | `clickhouse/clickhouse-server` | Apache-2.0 |
| nginx 1.28 | `nginx` | BSD-2-Clause |
| Redis 7.4 | `redis` | RSALv2 / SSPLv1 (*source-available*) |
| MariaDB 11.4 (hanya untuk pindah metadata versi lama) | `mariadb` | GPL-2.0 |

- **Redis 7.4**: boleh dipakai gratis sebagai cache di dalam aplikasi (cara ALDx memakainya). Yang dilarang
  hanyalah menjual Redis itu sendiri sebagai layanan terkelola. Bila menginginkan komponen yang sepenuhnya
  open source, pengganti setara adalah **Valkey** (BSD-3-Clause, protokol sama); belum dijadikan bawaan agar
  instalasi dan paket offline yang ada tidak berubah.
- **MariaDB (GPL-2.0)**: berjalan sebagai program terpisah di container sendiri dan hanya dihubungi lewat
  jaringan, jadi GPL tidak menular ke ALDx.
- Paket offline (`offline/aldx-images.tar.gz`) berisi image-image di atas tanpa diubah; lisensi masing-masing
  tetap berlaku dan teksnya ada di dalam image.

## 4. Tidak disertakan (diunduh sendiri oleh admin)

| Komponen | Lisensi | Alasan | Cara memasang |
|---|---|---|---|
| Oracle Instant Client | lisensi Oracle (Free Use Terms) | ukuran besar dan wajib dari sumber resmi Oracle; hanya perlu untuk Oracle < 12.1 | `docker/oracle/README.md` |
| SAP HANA driver `hdbcli` | SAP Developer License (proprietary) | lisensi SAP melarang dibagikan ulang | `docker/wheels/README.md` § SAP HANA |
| Logo perusahaan/instansi pengguna | merek milik pemiliknya | bukan milik proyek ini | taruh di `branding/` atau unggah di Pusat Kendali → Identitas ([09](docs/09-identitas-tema.md)) |

Berkas-berkas ini diabaikan git (`.gitignore`), jadi salinan lokal tetap ada saat repo diperbarui.

## 5. Layanan luar (opsional)

Asisten AI bisa disambungkan ke penyedia cloud (OpenAI, Anthropic, Google, xAI, DeepSeek) atau model lokal
(Ollama, LM Studio, Jan, llama.cpp). Tidak ada kode penyedia yang disertakan; pemakaian layanan tunduk pada
ketentuan masing-masing penyedia dan API key milik pengguna sendiri.

## 6. Merek dagang

"Apache", "Apache Superset", "Apache ECharts", dan logo bulu Apache adalah merek dagang The Apache Software
Foundation. ALDx boleh menyebut dirinya "berbasis Apache Superset", tetapi bukan produk resmi Apache dan tidak
memakai logo Apache. Nama produk lain yang disebut adalah milik pemiliknya masing-masing.

## Untuk pengembang: menambah komponen baru

1. Periksa lisensinya. Aman: Apache-2.0, MIT, BSD, ISC, PSF, UPL, PostgreSQL, OFL (font), LGPL/MPL (tanpa diubah).
   **Jangan disertakan**: proprietary/"developer license", GPL/AGPL di dalam kode Python/JS ALDx, atau yang tanpa lisensi.
2. Tambahkan satu baris di tabel yang sesuai di berkas ini.
3. Paket yang lisensinya melarang dibagikan: jadikan opsional (lihat `opsional=` di `config/sps_koneksi/katalog.py`)
   dan masukkan pola berkasnya ke `.gitignore`.
