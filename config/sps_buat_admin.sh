#!/bin/sh
# Membuat akun admin pertama dari variabel .env (dipanggil scripts/init.ps1 & scripts/uji-ci.sh di dalam container).
#
# Berkas terpisah agar nilai berisi spasi atau karakter khusus (nama "Budi Santoso S", password "a b$c*")
# sampai utuh: tanda kutip di sini tidak diolah ulang oleh PowerShell Windows sebelum dikirim ke container.
# Akun yang sudah ada tidak diubah (Superset hanya memberi tahu "already exists").
set -eu
: "${ADMIN_USERNAME:?ADMIN_USERNAME kosong di .env}"
: "${ADMIN_PASSWORD:?ADMIN_PASSWORD kosong di .env}"
exec superset fab create-admin \
  --username "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD" \
  --email "${ADMIN_EMAIL:-$ADMIN_USERNAME}" \
  --firstname "${ADMIN_FIRSTNAME:-Admin}" \
  --lastname "${ADMIN_LASTNAME:--}"
