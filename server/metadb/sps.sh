#!/bin/sh
# Perintah pemeliharaan metadb (PostgreSQL), dijalankan DI DALAM container metadb:
#   docker compose exec -T -e BERKAS metadb sh /sps/sps.sh <perintah>
#
#   cadangkan   dump database metadata -> /backup/$BERKAS   (format custom pg_dump, terkompresi)
#   pulihkan    ganti seluruh metadata dengan isi /backup/$BERKAS (.dump atau .sql)
#   kosongkan   hapus & buat ulang database metadata (dipakai ulang-coba pindah dari versi lama)
#   ukuran      tampilkan ukuran database metadata
#   ujipulih    uji cadangan /backup/$BERKAS: pulihkan ke database SEMENTARA, hitung isi pentingnya, lalu hapus.
#               Database aplikasi tidak disentuh; boleh dijalankan saat aplikasi menyala.
#
# Superset (web/worker/beat) HARUS dimatikan sebelum pulihkan/kosongkan.
set -eu
DB="$POSTGRES_DB"
U="$POSTGRES_USER"

buat_ulang() {
  psql -v ON_ERROR_STOP=1 -U "$U" -d postgres -q \
    -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE);" \
    -c "CREATE DATABASE \"$DB\" OWNER \"$U\" ENCODING 'UTF8';"
}

case "$1" in
  cadangkan)
    pg_dump -U "$U" -d "$DB" -Fc -Z 6 -f "/backup/$BERKAS"
    ls -lh "/backup/$BERKAS" ;;
  pulihkan)
    buat_ulang
    case "$BERKAS" in
      *.sql) psql -v ON_ERROR_STOP=1 -q -U "$U" -d "$DB" -f "/backup/$BERKAS" ;;
      *)     pg_restore -U "$U" -d "$DB" --no-owner --exit-on-error "/backup/$BERKAS" ;;
    esac
    echo "Dipulihkan dari /backup/$BERKAS" ;;
  kosongkan)
    buat_ulang
    echo "Database $DB dikosongkan." ;;
  ukuran)
    psql -U "$U" -d "$DB" -tAc "SELECT pg_size_pretty(pg_database_size('$DB'));" ;;
  ujipulih)
    UJI="sps_ujipulih"
    psql -v ON_ERROR_STOP=1 -U "$U" -d postgres -q -c "DROP DATABASE IF EXISTS \"$UJI\" WITH (FORCE);" \
         -c "CREATE DATABASE \"$UJI\" OWNER \"$U\";"
    trap 'psql -U "$U" -d postgres -q -c "DROP DATABASE IF EXISTS \"$UJI\" WITH (FORCE);"' EXIT
    case "$BERKAS" in
      *.sql) psql -v ON_ERROR_STOP=1 -q -U "$U" -d "$UJI" -f "/backup/$BERKAS" ;;
      *)     pg_restore -U "$U" -d "$UJI" --no-owner --exit-on-error "/backup/$BERKAS" ;;
    esac
    psql -U "$U" -d "$UJI" -tA -F ' ' -c "SELECT 'pengguna', count(*) FROM ab_user
      UNION ALL SELECT 'role', count(*) FROM ab_role
      UNION ALL SELECT 'koneksi', count(*) FROM dbs
      UNION ALL SELECT 'dataset', count(*) FROM tables
      UNION ALL SELECT 'chart', count(*) FROM slices
      UNION ALL SELECT 'dashboard', count(*) FROM dashboards;"
    echo "UJI PULIH OK: /backup/$BERKAS" ;;
  *)
    echo "Perintah tidak dikenal: $1" >&2; exit 2 ;;
esac
