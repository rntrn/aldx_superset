# =============================================================================
#  Image Superset proyek SPS
#  Basis : image resmi apache/superset (versi diatur dari .env)
#  Tambah: semua paket di docker/wheels/paket.txt:
#          psycopg2 (metadata PostgreSQL), LDAP, ClickHouse (SPS Engine), Oracle,
#          serta driver wizard "Hubungkan data" (SQL Server, Snowflake, BigQuery,
#          Redshift, Databricks, Trino, Athena, DuckDB, SAP HANA, Vertica, Druid, Access)
#          Oracle Instant Client (opsional, dari docker/oracle/) - mode thick
#            untuk Oracle < 12.1. Lihat docker/oracle/README.md
#
#  Instalasi OFFLINE dari folder docker/wheels/ karena jaringan kantor
#  memblokir koneksi HTTPS dari dalam Docker ke pypi.org (SSL inspection).
#  Untuk driver lain: taruh file .whl di docker/wheels/ lalu tambahkan
#  namanya di docker/wheels/paket.txt.
#
#  Hemat ruang: berkas installer (.whl, zip Instant Client) TIDAK disalin ke
#  image, hanya "dipinjam" selama build (RUN --mount), sehingga tidak ikut
#  memakan storage.
# =============================================================================
ARG SUPERSET_VERSION=6.1.0
FROM apache/superset:${SUPERSET_VERSION}

USER root

# Pasang ke virtualenv bawaan image (/app/.venv) dengan uv (sudah ada di image resmi).
# Versi paket bawaan image (mis. requests) TIDAK diubah: wheels dipilih agar cocok dengannya.
# Bila gagal, pesan "Because ... was not found" menyebut paket yang kurang (docker/wheels/README.md).
RUN --mount=type=bind,source=wheels,target=/tmp/wheels \
    . /app/.venv/bin/activate && \
    sed 's/#.*//' /tmp/wheels/paket.txt | tr -s ' \t' '\n' | grep -v '^$' > /tmp/paket.txt && \
    uv pip install --no-cache --no-index --find-links /tmp/wheels -r /tmp/paket.txt

# Oracle Instant Client: hanya terpasang bila zip-nya ada di docker/oracle/.
RUN --mount=type=bind,source=oracle,target=/tmp/oracle \
    sh /tmp/oracle/install-instantclient.sh

USER superset
