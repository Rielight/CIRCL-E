# CIRCL-E — Notebook Set & Dashboard

Repository ini memisahkan pipeline menjadi tiga tahap yang jelas:

1. **`01_CIRCL_E_Discovery.ipynb`** — numerical discovery berbasis citra.
2. **`02_CIRCL_E_Semantic_Mapping.ipynb`** — semantic mapping atas struktur Discovery yang telah dibekukan.
3. **`03_CIRCL_E_Post_Mapping.ipynb`** — evidence-informed ordinal circular-resource decision support.

## Status notebook (kondisi aktual repo ini)

### 01 — Discovery

Notebook 1 **tidak dihitung ulang dan output existing tidak dihapus**. Seluruh 65 code cell tersimpan dengan execution count dan output historisnya; metadata notebook mencatat `outputs_preserved: true` dan `execution_counts_preserved: true`. Output Notebook 1 adalah **record eksekusi yang otoritatif** dan tidak boleh dibersihkan. Dengan demikian hasil modelling yang mahal tetap tersedia sebagai executed record.

Catatan: jika suatu saat Notebook 1 dijalankan ulang, ia akan menulis ulang artefak handoff-nya (mis. `FINAL_DISCOVERY_HANDOFF.zip` dibangun kembali oleh cell di akhir notebook). Jangan mencampur output rerun baru dengan record historis tanpa keputusan eksplisit.

### 02 — Semantic Mapping

Notebook 2 memuat **output hasil eksekusi terakhir** (20 code cell dengan execution count dan output tersimpan; rerun dilakukan oleh pengguna pada environment proyek). Ratusan pasangan cell `review_*` / `assign_row(...)` lama telah diubah menjadi **registry keputusan semantik deklaratif** (`FAMILY_FACTOR_MAP` dan registri semantik lainnya). Seluruh label, semantic key, role, status, confidence, rationale, serta schema downstream dipertahankan.

Enam helper `review_*` yang tersisa hanyalah **penampil bukti visual yang opsional** (dijalankan hanya bila `CIRCLE_RENDER_REVIEW_EVIDENCE=1`); tidak ada keputusan semantik yang hidup hanya di helper tersebut — semua keputusan ada di registry.

Penyesuaian identifier untuk Discovery final telah diverifikasi secara statis pada sumber registry:

- family ICA P01 menggunakan `factor_id=2` (baris registry `parent_id=1, factor_id=2` pada `FAMILY_FACTOR_MAP`; identifier lama `factor_id=1` untuk P01 sudah tidak ada di registry). Gambar review `parent_01_ica_f01.jpg` di runtime adalah artefak kandidat lama.

Aktifkan montage review bila diperlukan:

```bash
export CIRCLE_RENDER_REVIEW_EVIDENCE=1
```

Gunakan render ringan untuk validasi figure path:

```bash
export CIRCLE_LIGHTWEIGHT_RENDER=1
```

### 03 — Post-Mapping

Notebook 3 memuat **output hasil eksekusi terakhir** (31 code cell dengan execution count dan output tersimpan). Dokumentasi diterjemahkan, helper dengan nama terlalu pendek diganti menjadi nama deskriptif, input handoff dibuat lebih portabel, dan validasi SHA ZIP dipisahkan dari validasi isi internal.

## Struktur repositori saat ini

```text
CIRCL-E/
├── 01_CIRCL_E_Discovery.ipynb
├── 02_CIRCL_E_Semantic_Mapping.ipynb
├── 03_CIRCL_E_Post_Mapping.ipynb
├── README.md
├── CIRCL_E_Discovery_Handoff.zip          # handoff antar-tahap (di disk; TIDAK di-track Git — aset GitHub Release)
├── CIRCL_E_Semantic_Mapping_Handoff.zip   # handoff antar-tahap (di disk; TIDAK di-track Git — aset GitHub Release)
├── CIRCL_E_Post_Mapping_Handoff.zip       # handoff final (di disk; TIDAK di-track Git — aset GitHub Release)
├── CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/   # bukti/evidence stage-2 (payload Semantic_Mapping_Handoff.zip; di-track)
├── CIRCL_E_Dashboard_1.0.0/               # dashboard bundle (sumber + runtime/release)
│   ├── Dockerfile, docker-compose.yml, pyproject.toml, requirements.lock
│   ├── VERSION, RELEASE_MANIFEST.json, SHA256SUMS
│   ├── dashboard/  scripts/  src/  .streamlit/
│   └── runtime/release/                   # data runtime ilmiah (checksum terverifikasi; TIDAK di-track Git — aset Release)
├── outputs/                               # hasil Notebook 3: derived/, figures/, report/ (di-track)
└── .circl_e_runtime/                      # area kerja runtime Notebook 2 (frozen handoff; TIDAK di-track Git)
```

> **Catatan checkout:** berkas ZIP dan data runtime (`*.zip`, `CIRCL_E_Dashboard_1.0.0/runtime/`, `.circl_e_runtime/`) sengaja **tidak di-track Git** (lihat `.gitignore`). Checkout sumber dari GitHub tidak memuatnya; unduh sebagai **aset GitHub Release** (atau gunakan `CIRCL_E_Dashboard_1.0.0.zip`) dan letakkan di lokasi yang sesuai sebelum menjalankan notebook/dashboard. `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/` dan `outputs/` di-track langsung di repo.

Folder `inputs/` **tidak ada** di repo ini; handoff ZIP berada di root. Semua notebook tetap mendukung pencarian di `inputs/` bila Anda menyusun ulang folder secara manual.

## Nama handoff ZIP

Nama yang direkomendasikan untuk progression antar notebook:

| Tahap | Nama ZIP |
|---|---|
| Discovery → Semantic Mapping | `CIRCL_E_Discovery_Handoff.zip` |
| Semantic Mapping → Post-Mapping | `CIRCL_E_Semantic_Mapping_Handoff.zip` |
| Post-Mapping final | `CIRCL_E_Post_Mapping_Handoff.zip` |

Untuk kompatibilitas, Notebook 2 masih dapat menemukan pola legacy `FINAL_DISCOVERY_HANDOFF*.zip`, dan Notebook 3 masih dapat menemukan pola legacy `CIRCL_E_STAGE2_SEMANTIC_HANDOFF*.zip`.

Tidak perlu mengubah nama file **di dalam** handoff. Nama kolom CSV, numerical IDs, semantic keys, serta internal folder `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/` dipertahankan karena digunakan sebagai kontrak downstream.

## Menjalankan notebook

Notebook menggunakan `PROJECT_ROOT = Path.cwd()` (Notebook 2/3) atau pencarian root dari cwd (Notebook 1), sehingga **jalankan Jupyter dari root repo ini**. Untuk kontrol eksplisit:

```bash
export CIRCLE_STAGE2_ROOT=/path/ke/root/repo        # Notebook 2
export CIRCLE_DISCOVERY_HANDOFF=/path/CIRCL_E_Discovery_Handoff.zip
export CIRCLE_STAGE2_HANDOFF=/path/CIRCL_E_Semantic_Mapping_Handoff.zip
```

Notebook juga mendukung environment variable untuk memilih handoff secara eksplisit:

```bash
export CIRCLE_DISCOVERY_HANDOFF=/path/to/discovery_handoff.zip
export CIRCLE_STAGE2_HANDOFF=/path/to/semantic_mapping_handoff.zip
```

## Kebijakan SHA-256

SHA ZIP dicatat untuk provenance, tetapi perubahan dokumentasi/manifest/packaging dapat mengubah SHA tanpa mengubah substansi analisis. Karena itu:

- referensi Discovery ZIP saat penyusunan notebook ini: `92941e821f208a83845da9026a7d4f38b1cd56d9e28935798a31152a47ac47ab`;
- referensi Stage-2 ZIP lama: `a2471014e1f04585fc07307f87b168536fe206aa3aa25b028937b4ff6abe682b`;
- Notebook 2 tetap memvalidasi internal Discovery freeze/fingerprint;
- Notebook 3 tetap memvalidasi structure count dan hash file internal Stage-2 berdasarkan manifest;
- whole-ZIP SHA mismatch menjadi peringatan secara default, bukan alasan untuk menolak isi yang lolos validasi internal.

Untuk menjadikan whole-ZIP SHA sebagai pemeriksaan strict:

```bash
export CIRCLE_STRICT_DISCOVERY_ZIP_SHA=1
export CIRCLE_STRICT_STAGE2_ZIP_SHA=1
```

## Dashboard bundle (CIRCL_E_Dashboard_1.0.0)

Bundle dashboard berisi aplikasi Streamlit (`dashboard/`), paket inferensi (`src/circl_e_ai`, `src/circl_e_app`), dan data runtime ilmiah (`runtime/release/`). Bundle ini adalah artefak rilis yang **checksum-nya terverifikasi penuh**: `SHA256SUMS` mencakup 574 file dan seluruhnya cocok (`sha256sum -c SHA256SUMS` → 574/574 OK pada waktu audit). Karena itu:

- jangan mengedit file apa pun di dalam bundle tanpa rencana regenerasi manifest (buat ulang `RELEASE_MANIFEST.json` + `SHA256SUMS`, lalu `sha256sum -c SHA256SUMS` harus lulus);
- `runtime/release/` dan `.circl_e_runtime/` sengaja tidak di-track Git (ukuran ~160MB+); distribusikan sebagai aset GitHub Release;
- `CIRCL_E_Dashboard_1.0.0.zip` adalah arsip distribusi bersih (tanpa `__pycache__`) dan juga menjadi aset Release.

Menjalankan dashboard lokal:

```bash
cd CIRCL_E_Dashboard_1.0.0
./scripts/run_local.sh          # verifikasi runtime lalu streamlit run dashboard/app.py
```

Docker:

```bash
cd CIRCL_E_Dashboard_1.0.0
cp .env.example .env            # isi CIRCL_DINO_HOST_DIR dan CIRCL_CRADIO_HOST_DIR (wajib)
docker compose up --build
```

## Urutan eksekusi

Jika modelling Discovery tidak perlu dihitung ulang, gunakan handoff yang sudah tersedia dan mulai dari Notebook 2:

```text
CIRCL_E_Discovery_Handoff.zip
        ↓
02_CIRCL_E_Semantic_Mapping.ipynb
        ↓
CIRCL_E_Semantic_Mapping_Handoff.zip
        ↓
03_CIRCL_E_Post_Mapping.ipynb
        ↓
CIRCL_E_Post_Mapping_Handoff.zip
```

## Kontrak yang dipertahankan

Cleanup tidak dimaksudkan untuk mengubah scientific meaning pipeline. Beberapa kontrak penting yang dipertahankan:

- `raw_parent_id`, `validated_fine_group_id`, `raw_visual_leaf_id`;
- `discovery_status` dan aturan abstention;
- nama kolom pada CSV utama;
- semantic key dan mapping fields;
- RRP/WRO/CSO/TPC/IRP dan route IDs;
- raw visual leaf tetap deskriptif;
- ICA tetap continuous factor, bukan class;
- patch atypicality tetap identity-relative dan bukan damage probability;
- ordinal level bukan probabilitas atau ratio scale.

## Catatan reproducibility

Notebook 1 mempertahankan environment/model assumptions dari pipeline modelling asli. Notebook 2 dan 3 hanya membutuhkan handoff stage sebelumnya beserta scientific Python stack yang sudah digunakan proyek ini. Notebook 2 dan 3 disertakan **dengan output eksekusi terakhirnya** sebagai bukti; rerun dilakukan oleh pengguna pada environment proyek (jalankan dari root repo). Tidak ada notebook dalam paket ini yang dieksekusi selama proses audit; audit dilakukan sepenuhnya statis (tanpa menjalankan notebook, skrip, atau program apa pun).
