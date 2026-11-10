# certs/ — sertifikat CA kantor (opsional)

Hanya perlu bila **Asisten AI memakai model API (cloud)** dan jaringan kantor
melakukan *SSL inspection* (error `CERTIFICATE_VERIFY_FAILED` di log).

1. Minta/ekspor sertifikat root CA kantor dalam format **PEM (Base-64)**,
   simpan di sini, contoh `certs\ca-kantor.pem`.
2. Di `.env`: `AI_CA_BUNDLE=/app/certs/ca-kantor.pem`
3. `docker compose up -d` (agar mount & .env terbaca ulang).

Folder ini di-mount ke container sebagai `/app/certs` (read-only).
Model lokal (Ollama di Windows) tidak membutuhkan ini.
