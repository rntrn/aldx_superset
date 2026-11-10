#!/bin/sh
# Dijalankan DI DALAM container metadb-lama (MariaDB versi lama) oleh scripts\pindah-metadata.ps1:
#   docker compose --profile pindah exec -T -e BERKAS metadb-lama sh /sps/lama.sh impor
#
#   impor   muat cadangan MariaDB lama /backup/$BERKAS (.sql), lalu beri izin user superset
set -eu
case "$1" in
  impor)
    mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" < "/backup/$BERKAS"
    mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON *.* TO '$MARIADB_USER'@'%'; FLUSH PRIVILEGES;"
    echo "Cadangan $BERKAS dimuat." ;;
  *)
    echo "Perintah tidak dikenal: $1" >&2; exit 2 ;;
esac
