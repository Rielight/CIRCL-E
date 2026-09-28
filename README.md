# CIRCL-E

CIRCL-E menganalisis gambar e-waste melalui tiga tahap: menemukan pola visual yang berulang, memberi interpretasi semantik secara konservatif, lalu menerjemahkan bukti tersebut menjadi beberapa dimensi penilaian circular economy.

Hasil akhirnya bukan prediksi fungsi perangkat atau tingkat bahaya. CIRCL-E menghasilkan profil ordinal yang dapat ditelusuri ke keputusan semantik, literatur yang digunakan, atau aturan model yang terdokumentasi.

## Latar belakang

Pengelompokan dan penilaian e-waste dari foto memerlukan pendekatan yang sistematis dan dapat ditelusuri sumber evidensinya. Tahap Discovery tidak menggunakan label kelas per gambar sebagai input clustering. Tahap Semantic Mapping memberi interpretasi konservatif pada struktur yang dihasilkan; setiap keputusan dicatat beserta asal-usulnya. Tahap Post-Mapping memetakan interpretasi tersebut ke profil ordinal yang dapat dikuantifikasi ketergantungannya terhadap sumber tertentu.

## Pipeline tiga tahap

```text
[Tahap 1 — Discovery]         01_CIRCL_E_Discovery.ipynb
  Menyusun struktur visual dari 3.793 gambar kanonik (dari 3.961 raw images)
  menjadi 16 parent group dan 48 raw visual leaf; memvalidasi 28 fine group.
        ↓  CIRCL_E_Discovery_Handoff.zip
[Tahap 2 — Semantic Mapping]  02_CIRCL_E_Semantic_Mapping.ipynb
  Memberi label semantik pada struktur Tahap 1 melalui registry tertulis:
  label, peran, status operasional, confidence, dan rationale tiap struktur.
        ↓  CIRCL_E_Semantic_Mapping_Handoff.zip
[Tahap 3 — Post-Mapping]      03_CIRCL_E_Post_Mapping.ipynb
  Memetakan setiap gambar kanonik ke profil ordinal menggunakan 192 criterion
  anchor dan 128 route anchor.
        ↓  outputs/  (figures/, derived/, report/)
```

Setiap keputusan di registry mencatat asal-usulnya: `FROZEN_SEMANTIC` (semantik yang ditetapkan saat Tahap 2), `LITERATURE_SYNTHESIS` (dari literatur), atau `MODEL_RATIONALE` (aturan model yang eksplisit).

Gambar kanonik adalah unit citra setelah canonicalization/deduplication input; bukan centroid sintetis atau prototipe cluster.

## Dimensi output

Tahap 3 menghasilkan lima dimensi ordinal untuk setiap gambar:

- **RRP** (*Resource Recovery Potential*) — relevansi pemulihan material atau komponen, berdasarkan kriteria yang berbasis literatur.
- **WRO** (*Whole-device Reuse Opportunity*) — penilaian visual peluang reuse perangkat-utuh; mensyaratkan bukti integritas dan konfigurasi yang lebih ketat dari RRP.
- **CSO** (*Component Salvage Opportunity*) — relevansi pemulihan komponen individual.
- **TPC** (*Treatment Complexity/Priority*) — kompleksitas penanganan atau prioritas.
- **IRP** (*Relative Inspection/Resolution Priority*) — prioritas inspeksi relatif dalam satu parent group; dimensi komparatif, bukan hitungan tunggal.

Ditambah: kompatibilitas rute penanganan (ordinal affinity, bukan rekomendasi).

Semua nilai adalah ordinal. Tidak ada yang merupakan probabilitas, rasio, atau skor akurasi.

## Temuan utama

| Metrik | Nilai |
|--------|-------|
| Gambar kanonik | 3.793 |
| Parent group | 16 |
| Fine group tervalidasi | 28 |
| Raw visual leaf deskriptif | 48 |
| Abstention unknown/mixed | 454 |
| RRP resolved | 2.918 / 3.793 |
| WRO resolved | 642 / 3.793 |
| CSO / TPC resolved | 3.119 / 3.793 |
| Internal scientific/integrity checks | **74/74 passed** |

WRO yang lebih rendah dari CSO bukan anomali — ini disengaja. WRO beroperasi pada level perangkat-utuh dan mensyaratkan bukti visual konfigurasi yang eksplisit; komponen seperti PCB tidak diberi status reuse perangkat-utuh. Laptop dalam kondisi terbongkar, misalnya, dapat memiliki WRO rendah sekaligus CSO yang lebih tinggi karena komponennya terekspos.

Dalam source-ablation analysis, menghilangkan E001 — UNITAR SCYCLE *E-waste Statistics Guidelines* (2026, DOI: [10.5281/zenodo.18328494](https://doi.org/10.5281/zenodo.18328494)) — membuat 2.113 dari 2.918 profil RRP yang sebelumnya resolved menjadi unresolved (72,4%). Hasil ini menunjukkan ketergantungan pada cakupan evidensi, bukan akurasi model. Penjelasan lengkap di [docs/results.md](docs/results.md).

## Contoh: bagaimana bukti visual mengubah profil

Empat contoh berikut diambil langsung dari `outputs/derived/semantic_transition_registry.csv`. Semua penilaian didasarkan pada tampilan visual, bukan klaim tentang apakah perangkat berfungsi atau layak diperbaiki.

| Apa yang terlihat | Apa yang berubah di profil | Catatan interpretasi |
|-------------------|---------------------------|----------------------|
| Smartphone dengan layar retak | WRO turun (integritas visual perangkat-utuh rendah); kompatibilitas parts harvest naik | Keretakan layar adalah bukti kondisi visual — bukan bukti kerusakan permanen atau prediksi nilai komponen |
| Laptop dalam kondisi terbongkar | WRO turun (konfigurasi tidak utuh); CSO naik (komponen terekspos); kompleksitas pemilahan naik | Nilai CSO yang lebih tinggi mencerminkan aksesibilitas visual komponen, bukan kepastian bahwa komponen dapat dipulihkan |
| IC/prosesor lepas | Spesifisitas feed RRP naik; spesifisitas komponen CSO naik; kompatibilitas rute specialist e-scrap naik | Berdasarkan synthesis literatur; bukan pengukuran komposisi material |
| Display yang terlihat aktif/menyala | WRO naik (presentasi visual positif) | Tampilan aktif adalah bukti presentasi visual — **bukan probabilitas bahwa perangkat berfungsi** |

## Arsitektur pipeline

![Arsitektur CIRCL-E](outputs/figures/01_evidence_to_profile_architecture.png)

## Contoh profil CIRCL-E

![Contoh profil CIRCL-E](outputs/figures/07_representative_profile_cards.png)

## Dashboard inferensi lokal

`CIRCL_E_Dashboard_1.0.0/` menyediakan aplikasi Streamlit untuk inferensi pada gambar baru. Inferensi sepenuhnya lokal; tidak memerlukan akses internet saat berjalan. Backbone DINOv3 dan C-RADIOv4 harus tersedia di direktori lokal — tidak disertakan dalam paket.

Lihat [CIRCL_E_Dashboard_1.0.0/README.md](CIRCL_E_Dashboard_1.0.0/README.md) untuk petunjuk instalasi lengkap (Docker atau Python lokal).

## Struktur repositori

```text
CIRCL-E/
├── 01_CIRCL_E_Discovery.ipynb
├── 02_CIRCL_E_Semantic_Mapping.ipynb
├── 03_CIRCL_E_Post_Mapping.ipynb
├── CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/   # artefak Tahap 2 (di-track Git)
├── CIRCL_E_Dashboard_1.0.0/                   # source + bundle dashboard
├── outputs/                                   # hasil Tahap 3 (di-track Git)
│   ├── derived/    # CSV: profil, registry transisi, ablasi sumber, validasi
│   ├── figures/    # 7 figure ilmiah
│   └── report/     # final_results.md, final_methodology.md
└── docs/
    ├── reproducibility.md
    ├── methodology.md
    └── results.md
```

Runtime dashboard dan ZIP handoff tidak disimpan dalam Git. Artefak tersebut didistribusikan melalui GitHub Releases.

## Dokumentasi teknis

| Dokumen | Isi |
|---------|-----|
| [docs/reproducibility.md](docs/reproducibility.md) | Handoff ZIP, kebijakan SHA-256, environment variable, urutan eksekusi, nama legacy ZIP, field schema yang tidak boleh diubah |
| [docs/methodology.md](docs/methodology.md) | Lima dimensi ordinal, criterion/route anchor, kebijakan interpretasi semantik, sensitivity & source ablation, aturan abstention, identitas dan peran E001 |
| [docs/results.md](docs/results.md) | Tabel hasil lengkap, ketergantungan cakupan evidensi, interpretasi rute, 74/74 internal integrity checks, non-claims |

## Batasan

Output pipeline adalah profil ordinal berbasis penilaian visual. Pipeline tidak menginferensikan: fungsionalitas perangkat, berat material, komposisi material, kimia baterai, keberhasilan perbaikan, yield pemulihan, nilai pasar, pembayaran recycler, profitabilitas, status hukum limbah, klasifikasi bahaya, atau rute penanganan optimal.
