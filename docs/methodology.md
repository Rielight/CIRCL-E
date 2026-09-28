# Metodologi — CIRCL-E

Dokumen ini adalah pendamping naratif untuk `outputs/report/final_methodology.md` dan `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/report/stage2_semantic_report.md`. Lihat file-file tersebut untuk versi terstruktur yang diekspor langsung dari pipeline.

## Ringkasan pipeline

CIRCL-E berjalan dalam tiga tahap. Setiap tahap menghasilkan handoff yang digunakan tahap berikutnya.

**Tahap 1 — Discovery** menyusun struktur visual dari gambar e-waste tanpa menggunakan label kelas per gambar sebagai input clustering. Hasilnya adalah kelompok visual (parent, fine, raw visual leaf) dengan keanggotaan numerik yang dijaga konsistensinya sebagai dasar tahap berikutnya.

**Tahap 2 — Semantic Mapping** memberi interpretasi semantik pada struktur numerik dari Tahap 1 melalui registry tertulis. Setiap struktur diberi label, peran, status operasional, confidence, semantic key, dan rationale. Keputusan dicatat secara eksplisit; tidak ada keputusan semantik yang hidup di luar registry.

**Tahap 3 — Post-Mapping** memetakan interpretasi semantik ke profil ordinal menggunakan criterion anchor dan route anchor. Setiap anchor mencatat asal-usulnya dan — jika berbasis literatur — mencatat sumber pada level klaim.

## Lima dimensi ordinal

### RRP — Resource Recovery Potential

Relevansi pemulihan material atau komponen. Membutuhkan resource-relevance evidence; profil RRP tetap unresolved jika criterion evidensi tidak tersedia. Kondisi visual (seperti keretakan) tidak dapat memodifikasi RRP.

### WRO — Whole-device Reuse Opportunity

Peluang reuse perangkat-utuh berdasarkan penilaian visual integritas dan konfigurasi. Parent level komponen (seperti PCB) tidak diberi status WRO secara artifisial. WRO mensyaratkan reviewed image-state integrity/configuration evidence yang terpisah dari class reuse anchor.

### CSO — Component Salvage Opportunity

Relevansi pemulihan komponen individual. Dapat lebih tinggi dari WRO pada item yang terbongkar karena aksesibilitas komponen meningkat secara visual.

### TPC — Treatment Complexity/Priority

Kompleksitas penanganan atau prioritas relatif. Dibentuk dari faktor morfologi dan presentasi visual.

### IRP — Relative Inspection/Resolution Priority

Prioritas inspeksi relatif dalam satu parent group. Dibentuk dari operational assignment state, ambiguitas semantik/evidensi, dan within-parent visual atypicality/inventory cues. Ini adalah dimensi komparatif — tidak diukur sebagai hitungan resolved tunggal di seluruh dataset.

Semua dimensi adalah ordinal. Nilai bukan probabilitas, rasio, confidence interval, atau skor akurasi.

## Kategori asal-usul keputusan

| Kategori | Artinya |
|----------|---------|
| `FROZEN_SEMANTIC` | Keputusan ditetapkan saat Tahap 2; tidak bergantung pada sumber eksternal |
| `LITERATURE_SYNTHESIS` | Didukung oleh satu atau lebih sumber literatur yang tercatat di `outputs/derived/external_source_registry.csv` |
| `MODEL_RATIONALE` | Aturan model yang eksplisit dan terdokumentasi; tidak memerlukan sumber eksternal |

## Criterion anchor dan route anchor

Tahap 3 menggunakan:
- **192 criterion anchor** (75 di antaranya berbasis literatur). Setiap anchor berbasis literatur memiliki dependency sumber pada level klaim dan telah di-review secara manual.
- **128 route anchor** (9 di antaranya berbasis literatur).

Sumber broad-context tidak dapat menggantikan product/process-specific source yang diwajibkan secara diam-diam. Setiap criterion dan route anchor berbasis literatur memiliki `support_review_status: MANUALLY_REVIEWED_*` di registry.

## Source ablation dan sensitivity

Claim-aware source ablation membedakan anchor yang:
- tetap sama (*unchanged*);
- menjadi lebih broad (*broadened*);
- turun ke explicit model rationale (*downgraded*);
- menjadi unsupported (*unsupported*).

Hasil ablation tersimpan di `outputs/derived/source_ablation_results.csv`. Sensitivity analysis menggunakan shared parent/criterion evidence states dan shared uncertain semantic rules.

## E001 — identitas dan peran

**E001** adalah:

> UNITAR SCYCLE, *E-waste Statistics: Guidelines on Classifications, Reporting and Indicators, Third Edition*, publikasi 2026-02-12, DOI [10.5281/zenodo.18328494](https://doi.org/10.5281/zenodo.18328494).

Cakupan: UNU-KEY v2 product descriptions, average weights, EU6-PV material composition. Klaim yang didukung: product taxonomy dan broad/product material context — bukan item assay per gambar.

E001 digunakan sebagai primary anchor pada sejumlah criterion RRP. Dalam source-ablation analysis, menghilangkan E001 membuat 2.113 dari 2.918 profil RRP yang sebelumnya resolved menjadi unresolved (72,4%). Ini adalah ketergantungan terhadap cakupan evidensi: E001 menyediakan product taxonomy yang diperlukan untuk menentukan resource relevance. Hasil ablation bukan ukuran akurasi model.

## Aturan abstention operasional

- `unknown_mixed`: abstain pada semua dimensi utama; tetap memiliki IRP.
- `reliable_parent_only`: tidak menerima fine semantics.
- Raw visual leaf bersifat deskriptif dan tidak menaikkan status operasional gambar.
- Patch atypicality adalah identity-relative, bukan probabilitas kerusakan.
- Nuisance fine group (seperti acquisition-style splits untuk display) tidak memiliki efek pada dimensi utama.

## Registry machine-readable

| File | Isi |
|------|-----|
| `outputs/derived/semantic_transition_registry.csv` | Semua transisi semantik dari fine/raw leaf ke criterion dan rute |
| `outputs/derived/parent_route_affinity_map.csv` | Kompatibilitas rute per parent beserta asal-usul anchor |
| `outputs/derived/external_source_registry.csv` | Semua sumber eksternal dengan locator dan verification status |
| `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/mapping/semantic_structure_map.csv` | Label, peran, status tiap struktur Discovery |
