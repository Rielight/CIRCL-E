# Hasil — CIRCL-E

Dokumen ini adalah pendamping naratif untuk `outputs/report/final_results.md`. Lihat file tersebut untuk versi terstruktur yang diekspor langsung dari pipeline.

Tanggal analisis: 2026-09-26.

## Struktur yang dibekukan

| Komponen | Nilai |
|----------|-------|
| Gambar kanonik | 3.793 |
| Raw images (sebelum canonicalization) | 3.961 |
| Parent group | 16 |
| Fine group tervalidasi | 28 |
| Raw visual leaf deskriptif | 48 |
| Keanggotaan numerik berubah | tidak |
| Mapping semantik berubah | tidak |

## Coverage profil ordinal

| Dimensi | Resolved | Total | Catatan |
|---------|----------|-------|---------|
| RRP | 2.918 | 3.793 | 454 unknown/mixed abstain pada semua dimensi utama |
| WRO | 642 | 3.793 | 545 gambar level komponen: WRO not-applicable (N/A) |
| CSO | 3.119 | 3.793 | |
| TPC | 3.119 | 3.793 | |
| IRP | semua gambar | 3.793 | Dimensi komparatif per parent group |

## 74/74 internal scientific/integrity checks

Notebook 3 menjalankan 74 pemeriksaan internal yang mencakup: konsistensi struktur, kebijakan abstention, aturan evidensi per dimensi, validitas level ordinal, source ablation recomputation, dan integritas registry. Semua 74 pemeriksaan lulus (`PASS`).

Ini adalah pemeriksaan internal ilmiah dan integritas — bukan benchmark eksternal, bukan skor akurasi prediktif, dan bukan sertifikasi produksi.

## Ketergantungan cakupan evidensi

### E001

Dalam source-ablation analysis, menghilangkan E001 — UNITAR SCYCLE *E-waste Statistics Guidelines* (2026, DOI [10.5281/zenodo.18328494](https://doi.org/10.5281/zenodo.18328494)) — membuat 2.113 dari 2.918 profil RRP yang sebelumnya resolved menjadi unresolved (72,4%).

E001 menyediakan product taxonomy (UNU-KEY v2) dan broad material context yang digunakan sebagai primary anchor pada sejumlah criterion RRP. Dari 19 criterion anchor yang terpengaruh E001: 7 tidak berubah, 2 menjadi lebih broad, 10 menjadi unsupported.

Hasil ini adalah ketergantungan terhadap cakupan evidensi — profil bergantung pada ketersediaan sumber tersebut untuk menentukan resource relevance. Ini bukan ukuran akurasi model.

### Sumber lain

E007 dan E008 masing-masing berkontribusi pada 293 dan 168 newly-unresolved RRP profiles jika dihilangkan. Sumber lain tidak menyebabkan newly-unresolved RRP profiles. Lihat `outputs/derived/source_ablation_results.csv` untuk detail per sumber.

## Interpretasi dimensi

- Assignment support adalah within-parent routing-strength diagnostic, bukan probabilitas.
- Model/evidence range adalah sensitivity range, bukan confidence interval.
- Route compatibility adalah ordinal affinity state — bukan rekomendasi treatment, bukan estimasi profitabilitas, bukan prediksi optimality.
- Ordinal level bukan ratio scale.

## Interpretasi rute

Setiap parent group memiliki kompatibilitas rute yang tercatat di `outputs/derived/parent_route_affinity_map.csv`. Rute yang tersedia: `reuse_refurbish`, `parts_harvest`, `bulk_material_recovery`, `specialist_pcb`, `battery_specialist`, `crt_specialist`, `sorting_dismantling`, `residual_treatment`.

Kompatibilitas rute naik atau turun berdasarkan transisi semantik yang tercatat di `outputs/derived/semantic_transition_registry.csv`. Perubahan pada rute tidak mengubah RRP/WRO/CSO/TPC secara bersamaan; dimensi-dimensi tersebut independen.

## Non-claims

Pipeline tidak menginferensikan:
- fungsionalitas perangkat
- berat material
- komposisi material yang tepat
- kimia baterai
- keberhasilan perbaikan
- yield pemulihan
- nilai pasar
- pembayaran recycler
- profitabilitas
- status hukum limbah
- klasifikasi bahaya
- rute penanganan optimal

Ordinal level bukan ratio scale. Route output bukan rekomendasi. 74/74 checks bukan skor akurasi prediktif.
