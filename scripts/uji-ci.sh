#!/usr/bin/env bash
# Menyalakan ALDx dari nol di Linux lalu menjalankan SEMUA uji: uji otomatis (sps_uji.py) + uji tampilan (tests/e2e).
#
# Dipakai GitHub Actions (.github/workflows/uji.yml) pada setiap pull request, dan bisa dijalankan pengembang di
# mesin Linux/WSL KOSONG (nama container & volume ALDx tetap: jangan jalankan di komputer yang sudah terpasang ALDx).
#
#   bash scripts/uji-ci.sh             # bangun image, pasang, data latihan, uji
#   UJI_LEWATI_BANGUN=1 bash ...       # image sps-superset:<versi> sudah ada
#
# Hasil: kode keluar 0 = semua lulus. Tangkapan layar uji tampilan di tests/e2e/hasil/.
set -euo pipefail
cd "$(dirname "$0")/.."

acak() { head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32; }
atur() {   # atur KUNCI NILAI di .env (ganti baris yang ada / tambah)
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
tunggu_sehat() {   # tunggu_sehat <container> <detik>
  for _ in $(seq 1 "$2"); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$1" 2>/dev/null)" = "healthy" ] && return 0
    sleep 1
  done
  echo "::error::$1 tidak sehat dalam $2 detik"; docker logs --tail 80 "$1" || true; return 1
}

echo "==> .env uji (rahasia acak, tidak disimpan)"
cp .env.example .env
SANDI="Uji$(acak | head -c 12)#1"
atur SUPERSET_SECRET_KEY "$(acak)$(acak)"
atur REDIS_PASSWORD "$(acak)"; atur METADB_PASSWORD "$(acak)"; atur ENGINE_PASSWORD "$(acak)"
atur METADB_JENIS postgres; atur NODE_NAMA ci; atur ADMIN_PASSWORD "$SANDI"
VERSI_SS=$(grep -E '^SUPERSET_VERSION=' .env | cut -d= -f2 | tr -d '\r')

if [ -z "${UJI_LEWATI_BANGUN:-}" ]; then
  echo "==> Membangun image sps-superset:$VERSI_SS"
  docker compose build superset
fi

echo "==> Menyalakan metadb, engine, redis"
docker compose up -d metadb engine redis
tunggu_sehat sps_metadb 120; tunggu_sehat sps_engine 180; tunggu_sehat sps_redis 60

echo "==> Metadata, admin, role"
docker compose run --rm superset superset db upgrade
docker compose run --rm superset sh /app/pythonpath/sps_buat_admin.sh
docker compose run --rm superset superset init

echo "==> Menyalakan semua layanan"
docker compose up -d
tunggu_sehat sps_superset 300

echo "==> Dashboard, menu, ALDx Engine & data latihan (seperti installer)"
docker compose exec -T superset python /app/pythonpath/sps_build_dashboards.py
docker compose exec -T superset python /app/pythonpath/sps_latihan.py

echo "==> Uji otomatis (sps_uji.py)"
docker compose exec -T superset python /app/pythonpath/sps_uji.py | tee tests/e2e/uji-otomatis.txt
grep -qE '^[0-9]+/[0-9]+ lulus$' tests/e2e/uji-otomatis.txt || { echo "::error::sps_uji.py tidak selesai"; exit 1; }
lulus=$(grep -oE '^[0-9]+/[0-9]+' tests/e2e/uji-otomatis.txt | tail -1)
[ "${lulus%/*}" = "${lulus#*/}" ] || { echo "::error::uji otomatis $lulus"; grep GAGAL tests/e2e/uji-otomatis.txt || true; exit 1; }

echo "==> Uji tampilan (Playwright)"
ALDX_URL="http://localhost:$(grep -E '^SUPERSET_PORT=' .env | cut -d= -f2 | tr -d '\r')" ALDX_USER=admin ALDX_PASSWORD="$SANDI" \
  python3 tests/e2e/uji_tampilan.py
