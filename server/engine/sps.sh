#!/bin/sh
# Perintah pemeliharaan ALDx Engine, dijalankan DI DALAM container engine oleh skrip PowerShell:
#   docker compose exec -T -e BERKAS engine sh /sps/sps.sh <perintah>
#
#   cadangkan   BACKUP DATABASE sps_engine -> /backups/$BERKAS   (folder backup\engine)
#   pulihkan    RESTORE DATABASE sps_engine dari /backups/$BERKAS (tabel yang ada diganti)
#   ukuran      ukuran tiap tabel setelah kompresi
#   ujipulih    uji cadangan /backups/$BERKAS: pulihkan ke database SEMENTARA sps_ujipulih, hitung baris, hapus lagi
set -eu
CH="clickhouse-client --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD"
DB="${CLICKHOUSE_DB:-sps_engine}"

case "$1" in
  cadangkan)
    $CH -q "BACKUP DATABASE $DB TO File('/backups/$BERKAS')" ;;
  pulihkan)
    $CH -q "DROP DATABASE IF EXISTS $DB SYNC"
    $CH -q "RESTORE DATABASE $DB FROM File('/backups/$BERKAS')" ;;
  ujipulih)
    UJI="sps_ujipulih"
    $CH -q "DROP DATABASE IF EXISTS $UJI SYNC"
    trap '$CH -q "DROP DATABASE IF EXISTS $UJI SYNC"' EXIT
    $CH -q "RESTORE DATABASE $DB AS $UJI FROM File('/backups/$BERKAS')"
    $CH -q "SELECT count() AS tabel, sum(total_rows) AS baris FROM system.tables WHERE database = '$UJI'
            FORMAT PrettyCompact"
    echo "UJI PULIH OK: /backups/$BERKAS" ;;
  ukuran)
    $CH -q "SELECT table, formatReadableSize(sum(bytes_on_disk)) AS ukuran, sum(rows) AS baris
            FROM system.parts WHERE active AND database = '$DB' GROUP BY table ORDER BY sum(bytes_on_disk) DESC
            FORMAT PrettyCompact" ;;
  *)
    echo "Perintah tidak dikenal: $1" >&2; exit 2 ;;
esac
