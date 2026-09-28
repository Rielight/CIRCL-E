# Deployment — Dashboard CIRCL-E 1.0.0

## Isi checkout Git vs paket rilis

Checkout Git publik memuat kode sumber dan konfigurasi dashboard pada `CIRCL_E_Dashboard_1.0.0/`: aplikasi Streamlit (`dashboard/`), runtime kode (`src/`), skrip (`scripts/`), `requirements.lock`, `RELEASE_MANIFEST.json`, dan `SHA256SUMS`.

Direktori `CIRCL_E_Dashboard_1.0.0/runtime/release/` — aset runtime terpasang (*fitted/static artifacts*) yang dibutuhkan saat inferensi — sengaja tidak disertakan di Git (lihat `.gitignore`).

## Mengapa checkout Git tanpa aset runtime tidak dapat langsung dijalankan

`Dockerfile` menyalin direktori tersebut ke dalam image (`COPY runtime/release /app/runtime/release`) dan `docker-compose.yml` me-*mount* `./runtime/release` sebagai *read-only*. Tanpa `runtime/release/`, pembangunan image maupun `scripts/verify_runtime.py` akan gagal pada pemeriksaan tata letak bundle. Dengan demikian, checkout Git tanpa aset runtime bukan distribusi dashboard yang lengkap dan dapat dijalankan.

## Cara yang dimaksudkan: paket GitHub Release

Paket lengkap `CIRCL_E_Dashboard_1.0.0.zip` dimaksudkan didistribusikan sebagai aset GitHub Release (v1.0.0). Paket ini memuat seluruh isi `CIRCL_E_Dashboard_1.0.0/` termasuk `runtime/release/`, dengan checksum setiap berkas pada `SHA256SUMS`.

> Catatan: GitHub Release v1.0.0 belum terbit. Setelah rilis terbit, unduh paket tersebut dan gunakan sebagai distribusi dashboard lengkap; jangan menggantungkan diri pada clone Git polos.

## Langkah setelah paket diperoleh

1. Ekstrak `CIRCL_E_Dashboard_1.0.0.zip`.
2. Verifikasi tata letak bundle dan checksum: `python scripts/verify_runtime.py`.
3. Sediakan direktori *backbone* eksternal (DINOv3 dan C-RADIOv4) dan ikuti petunjuk pada `CIRCL_E_Dashboard_1.0.0/README.md` (Opsi Docker atau Python lokal).

Direktori *backbone* tidak termasuk dalam paket rilis dan tidak pernah dibundel; keduanya disediakan terpisah dan di-*mount* read-only.

## Catatan

- Isi `CIRCL_E_Dashboard_1.0.0/` di repo adalah bundel v1.0.0 yang checksum-nya terkunci pada `SHA256SUMS` (574 berkas); jangan mengubah isi direktori tersebut.
- Handoff ZIP antartahap analisis juga direncanakan didistribusikan sebagai aset GitHub Release, bukan Git (lihat [docs/reproducibility.md](reproducibility.md)).