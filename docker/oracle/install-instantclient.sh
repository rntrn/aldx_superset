#!/bin/sh
# =============================================================================
#  Pasang Oracle Instant Client (Linux x64) untuk mode THICK python-oracledb.
#  Dipanggil oleh docker/Dockerfile saat build. Tidak butuh internet KECUALI
#  untuk libaio (lihat langkah 2).
#
#  Dibutuhkan bila server Oracle < 12.1 (error DPY-3010 di mode thin).
#  Tanpa file zip di folder ini, skrip ini tidak melakukan apa-apa dan
#  Superset tetap memakai mode thin.
# =============================================================================
set -eu

SRC=/tmp/oracle
DEST=/opt/oracle
LIBDIR=/usr/lib/x86_64-linux-gnu

ZIP=$(ls "$SRC"/instantclient-basic*-linux.x64-*.zip 2>/dev/null | head -n 1 || true)
if [ -z "$ZIP" ]; then
    echo "[oracle] Instant Client tidak ada di docker/oracle/ -> mode thin saja."
    exit 0
fi
echo "[oracle] Memasang $(basename "$ZIP")"

# 1. Ekstrak zip (symlink seperti libclntsh.so ikut dipulihkan).
mkdir -p "$DEST"
/app/.venv/bin/python - "$ZIP" "$DEST" <<'PY'
import os, stat, sys, zipfile
zip_path, dest = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zip_path) as zf:
    for info in zf.infolist():
        target = os.path.join(dest, info.filename)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.lexists(target):
                os.remove(target)
            os.symlink(zf.read(info).decode(), target)
        else:
            zf.extract(info, dest)
            if mode:
                os.chmod(target, stat.S_IMODE(mode))
PY
CLIENT_DIR=$(ls -d "$DEST"/instantclient_* | head -n 1)
ln -sfn "$CLIENT_DIR" "$DEST/instantclient"
[ -e "$DEST/instantclient/libclntsh.so" ] || \
    ln -s "$(ls "$DEST"/instantclient/libclntsh.so.* | head -n 1)" "$DEST/instantclient/libclntsh.so"

# 2. libaio (wajib untuk Instant Client).
#    Utama: .deb lokal di docker/oracle/ (offline). Cadangan: apt (butuh jaringan).
if ls "$SRC"/libaio*.deb >/dev/null 2>&1; then
    dpkg -i "$SRC"/libaio*.deb
elif ! ls "$LIBDIR"/libaio.so.1* >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends libaio1t64 || \
        apt-get install -y --no-install-recommends libaio1
    rm -rf /var/lib/apt/lists/*
fi
# Debian trixie menamai berkasnya libaio.so.1t64; Instant Client mencari libaio.so.1.
[ -e "$LIBDIR/libaio.so.1" ] || ln -s "$LIBDIR/libaio.so.1t64" "$LIBDIR/libaio.so.1"

# 3. Daftarkan ke pencarian library sistem.
echo "$DEST/instantclient" > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig
echo "[oracle] Selesai: $CLIENT_DIR"
