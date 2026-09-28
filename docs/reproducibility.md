# Reproducibility — CIRCL-E

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

Untuk menjalankan ulang dari Notebook 1, jalankan Notebook 1 terlebih dahulu untuk menghasilkan `CIRCL_E_Discovery_Handoff.zip`, kemudian lanjutkan ke urutan di atas.

## Nama handoff ZIP

| Tahap | Nama kanonik |
|-------|-------------|
| Discovery → Semantic Mapping | `CIRCL_E_Discovery_Handoff.zip` |
| Semantic Mapping → Post-Mapping | `CIRCL_E_Semantic_Mapping_Handoff.zip` |
| Post-Mapping final | `CIRCL_E_Post_Mapping_Handoff.zip` |

Untuk kompatibilitas, Notebook 2 masih dapat menemukan pola legacy `FINAL_DISCOVERY_HANDOFF*.zip`, dan Notebook 3 masih dapat menemukan pola legacy `CIRCL_E_STAGE2_SEMANTIC_HANDOFF*.zip`. Tidak perlu mengubah nama file di dalam handoff.

## File yang tidak di-track Git

File-file berikut sengaja tidak di-track Git dan direncanakan didistribusikan sebagai aset GitHub Release; setelah GitHub Release v1.0.0 diterbitkan, aset tersebut tersedia untuk diunduh (lihat [panduan deployment](deployment.md)):

- `CIRCL_E_Discovery_Handoff.zip`
- `CIRCL_E_Semantic_Mapping_Handoff.zip`
- `CIRCL_E_Post_Mapping_Handoff.zip`
- `CIRCL_E_Dashboard_1.0.0/runtime/release/` (tercakup dalam paket dashboard; lihat [panduan deployment](deployment.md))

`CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/` dan `outputs/` di-track langsung di repo.

### Direktori runtime lokal (tidak perlu diunduh)

`.circl_e_runtime/` bukan aset rilis dan tidak perlu diunduh: Notebook 2 membuatnya sendiri di root proyek (`PROJECT_ROOT/.circl_e_runtime/semantic_mapping`) sebagai direktori kerja saat dijalankan ulang.

## Environment variable

### Notebook 2

```bash
export CIRCLE_STAGE2_ROOT=/path/ke/root/repo
export CIRCLE_DISCOVERY_HANDOFF=/path/CIRCL_E_Discovery_Handoff.zip
```

### Notebook 3

```bash
export CIRCLE_STAGE2_HANDOFF=/path/CIRCL_E_Semantic_Mapping_Handoff.zip
```

### Review visual (opsional)

```bash
export CIRCLE_RENDER_REVIEW_EVIDENCE=1   # aktifkan montage review
export CIRCLE_LIGHTWEIGHT_RENDER=1       # render ringan untuk validasi figure path
```

### SHA strict mode (opsional)

```bash
export CIRCLE_STRICT_DISCOVERY_ZIP_SHA=1
export CIRCLE_STRICT_STAGE2_ZIP_SHA=1
```

## Menjalankan notebook

Notebook menggunakan `PROJECT_ROOT = Path.cwd()` (Notebook 2/3) atau pencarian root dari cwd (Notebook 1). Jalankan Jupyter dari root repo:

```bash
jupyter lab   # atau: jupyter notebook
```

## Kebijakan SHA-256

SHA ZIP dicatat untuk provenance, tetapi perubahan dokumentasi atau packaging dapat mengubah SHA tanpa mengubah substansi analisis:

- Notebook 2 memvalidasi internal Discovery freeze/fingerprint.
- Notebook 3 memvalidasi structure count dan hash file internal Stage-2 berdasarkan manifest.
- Whole-ZIP SHA mismatch adalah peringatan secara default, bukan penolakan isi yang lolos validasi internal.
- Untuk menjadikan whole-ZIP SHA pemeriksaan strict, gunakan `CIRCLE_STRICT_*` di atas.

SHA referensi yang tercatat saat penyusunan notebook:
- Discovery ZIP: `92941e821f208a83845da9026a7d4f38b1cd56d9e28935798a31152a47ac47ab`
- Stage-2 ZIP: `a2471014e1f04585fc07307f87b168536fe206aa3aa25b028937b4ff6abe682b`

## Field schema yang tidak boleh diubah

Field-field berikut digunakan sebagai kontrak downstream antar notebook dan tidak boleh diganti namanya:

- `raw_parent_id`, `validated_fine_group_id`, `raw_visual_leaf_id`
- `discovery_status` dan aturan abstention
- nama kolom pada CSV utama
- semantic key dan mapping fields
- RRP/WRO/CSO/TPC sebagai empat dimensi utama penelitian, IRP sebagai diagnostik tambahan pada implementasi Post-Mapping, serta route ID
- ordinal level semantics

## Status eksekusi notebook

- Notebook 1 menyimpan output historisnya (65 code cell dengan execution count tersimpan). Output ini adalah record eksekusi yang dijaga dan tidak boleh dibersihkan tanpa keputusan eksplisit.
- Notebook 2 dan 3 disertakan dengan output eksekusi terakhirnya. Rerun dilakukan oleh pengguna pada environment proyek.
- Dashboard bundle (`CIRCL_E_Dashboard_1.0.0/`) adalah artefak rilis terpisah; checksumnya tersimpan di `CIRCL_E_Dashboard_1.0.0/SHA256SUMS` (574 file).
