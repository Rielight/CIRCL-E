# Metodologi — CIRCL-E

Dokumen ini menyajikan metodologi penelitian sebagaimana dilaporkan pada laporan Big Data Challenge 2026 (bagian Metodologi), diikuti perluasan implementasi teknis yang ditandai terpisah dan bukan bagian narasi riset. Versi terstruktur hasil ekspor pipeline tersedia pada `outputs/report/final_methodology.md` dan `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/report/stage2_semantic_report.md`.

## Dataset yang digunakan

Dataset utama Big Data Challenge 2026 memuat citra sampah dalam tiga kelas: *recyclable*, *electronic*, dan *organic*. Analisis dikhususkan untuk mengeksplorasi karakteristik visual dan pengelompokan citra limbah elektronik. Dataset ini memiliki 3.961 citra sampah elektronik, yang dikurasi menjadi 3.793 citra setelah duplikasi dideteksi dengan *dHash* dan *pHash*. Citra hasil kurasi menjadi unit analisis untuk ekstraksi representasi visual dan *clustering* secara *unsupervised*.

## Arsitektur model

Ekstraksi fitur menggunakan dua *backbone* ViT pralatih: C-RADIOv4-SO400M dan DINOv3-ViT-L/16. C-RADIO dilatih dengan *multi-teacher distillation* menggunakan SigLIP2, DINOv3, dan SAM3, yang masing-masing memberi supervisi pada representasi global dan spasial; representasi globalnya berdimensi 2048, tersusun atas dua *summary slots* berdimensi 1024 yang masing-masing disupervisi SigLIP2 dan DINOv3. DINOv3-ViT-L/16 memiliki 24 lapisan *transformer* dan menghasilkan fitur berdimensi 1024 untuk setiap token (satu token global dan token spasial sesuai resolusi citra).

Slot C-RADIO yang memperoleh supervisi distilasi dari DINOv3 dipertahankan sebagai representasi global karena keselarasan fiturnya dengan representasi lokal DINOv3, sedangkan token spasial DINOv3 menjadi representasi lokal untuk detail tekstur dan morfologi objek.

## Prapemrosesan (resizing)

Setiap citra di-*resize* proporsional dengan target sisi pendek 512 dan batas sisi panjang 1024; faktor skala yang lebih membatasi diterapkan pada kedua dimensi, lalu hasilnya dibulatkan ke kelipatan ukuran *patch* p=16. Jumlah token *patch* dengan demikian bergantung pada proporsi citra.

## Representasi semantik global (G)

Slot global C-RADIO yang disupervisi DINOv3 dinormalisasi ℓ2 dan direduksi dengan PCA (n=256) yang dilatih pada 80% citra *fit* untuk mencegah kebocoran informasi. Hasil proyeksi diterapkan pada seluruh citra dan dinormalisasi ulang menjadi vektor G berdimensi 256.

## Representasi morfologi lokal (L)

Token *patch* lapisan akhir DINOv3 direduksi PCA64, dikelompokkan ke 32 pusat dengan MiniBatch K-Means (pemetaan berdasarkan kemiripan kosinus tertinggi), lalu diagregasi mengikuti mekanisme VLAD (*Vector of Locally Aggregated Descriptors*): residual per pusat (32 vektor berukuran 64) dinormalisasi ℓ2 dan dikonkatenasi menjadi vektor 2048. Vektor ini dinormalisasi *power* (sign(v)·√|v|) dan ℓ2, kemudian direduksi PCA512 dengan *whitening* α=0,5 yang dilatih pada data *fit*, menghasilkan L berdimensi 512.

## Estimasi wilayah foreground

Peta spasial dibentuk dari kemiripan kosinus antara token global (token ke-0) dan token *patch* lapisan akhir DINOv3, dihaluskan dengan filter Gaussian (σ=0,8), dan di-*threshold* menggunakan Otsu 64-bin serta kuantil persentil ke-55 dan ke-65. Setiap masker kandidat dievaluasi melalui komponen terhubung dengan skor kelayakan yang mempertimbangkan rerata peta pada komponen, ukuran komponen, dan penalti proporsi keanggotaan pada batas citra; masker final dipilih lintas ambang menggunakan kombinasi skor geometris dan skor-Z. Bounding box ditentukan dari koordinat ekstrem komponen dan diperluas dengan margin 0,08.

## Representasi foreground dan representasi dual

Citra dipotong pada bounding box (margin proporsional 0,04), di-*letterbox* ke kanvas persegi 512×512 berlatar abu-abu netral (127,127,127), lalu diproses dengan prosedur yang sama sehingga diperoleh representasi foreground global G_f dan lokal L_f. Representasi utuh dan foreground digabung menjadi representasi dual (G_dual, L_dual) yang dinormalisasi ℓ2 dengan faktor penyeimbang 1/√2 agar kontribusi kedua tampilan setara.

## Kamus konsep visual dan fitur akuisisi

Token *patch* dari dua kedalaman (lapisan 18 dan lapisan akhir) membentuk deskriptor gabungan yang dilatih menjadi kamus 512 konsep visual dengan MiniBatch K-Means pada sampel *patch* data *fit* (48 *patch* per citra). Setiap *patch* dipetakan ke konsep kamus berdasarkan kemiripan kosinus tertinggi. Frekuensi kemunculan konsep pada wilayah latar belakang membentuk histogram latar (512-dim) yang direduksi PCA menjadi 8 dimensi. Bersama statistik citra keabuan (rerata dan simpangan baku kecerahan, proporsi piksel gelap/terang, saturasi, kekuatan tepi, entropi histogram, *colorfulness*, dan variansi gradien sebagai proksi ketajaman) serta metadata akuisisi (dimensi citra, ukuran berkas, rasio aspek, proporsi *patch foreground*), vektor ini membentuk fitur akuisisi 21 dimensi. Fitur akuisisi tidak pernah menjadi masukan pembentukan klaster; ia dipakai untuk mengaudit korelasi hasil *clustering* dengan kondisi pengambilan gambar dan sebagai pembanding kontrol negatif.

## Pembentukan klaster induk

Klaster induk dicari pada representasi global (G, G_f, G_dual) melalui *grid search*: K-means (K∈{16,18,20}), HDBSCAN dengan tiga konfigurasi, dan Leiden-CPM pada graf *mutual cosine-kNN* (k=30, γ∈{0,04; 0,08; 0,12}), ditambah komponen terhubung graf *mutual-kNN* (k∈{5,10,20}) sebagai baseline. Setiap kandidat diulang pada tiga *seed* dan partisi representatif diambil dari *seed* medoid. Kandidat disaring melalui delapan repetisi pembagian referensi uji 80%–20% dengan gerbang kelayakan: coverage ≥0,95, ukuran klaster minimum ≥30, silhouette ≥0,26, median ARI resampling ≥0,84, serta prediksi KNN pada subset uji (Macro Recall ≥0,84, Recall Q10 ≥0,72, Precision Q10 ≥0,70). Partisi final dipilih yang meminimalkan skor kelebihan *nuisance* NE(π) — mengukur seberapa besar keanggotaan klaster dapat ditebak dari fitur akuisisi saja.

## Subkelompok di dalam klaster induk

Penemuan subtipe berjalan pada dua trayektori:

- **Raw visual** — memprioritaskan pemisahan beresolusi maksimal (K∈[2,8], K-means) pada kombinasi G dan L (rasio 35:65, 50:50, 65:35) serta G_dual dan L_dual (35:65), dengan menoleransi variasi wujud fisik. Syarat: coverage ≥88%, ARI_g ≥0,70 (median lima resampling 80%/20%), ARI_s ≥0,80 (tiga *seed*); kandidat dengan ARI dalam toleransi 0,05 dari nilai maksimum membentuk *frontier* yang dilanjutkan. Daun raw-visual bersifat deskriptif dan komplementer; kriteria pemilihan kandidat pada trayektori ini tidak sama dengan validasi kelangsungan per-subklaster yang diterapkan pada subklaster visual tervalidasi.
- **Visual tervalidasi** — dirancang menangkap identitas semantik yang konsisten terhadap variasi *nuisance*; pencarian pada G, G_f, G_dual, dan fusi G_dual dengan L_f (60:40, 75:25). Enam gerbang wajib: ARI_g ≥0,78, ARI_s ≥0,86, Macro Recall KNN ≥0,80, Recall Q10 ≥0,65, coverage ≥0,90, populasi minimum 15 citra per klaster. Kandidat dievaluasi pada tujuh metrik (maksimalkan ARI_g, performa prediktif KNN, median ARI lintas representasi, dukungan minimal dua representasi; minimalkan NE), kandidat tanpa keunggulan pada metrik apa pun dieliminasi, toleransi 0,04 dari ARI maksimum, dan model dengan jumlah subtipe terbanyak dipilih.

Setiap subkelompok pada model akhir divalidasi delapan kali resampling (20% data disembunyikan) dengan pencocokan Hungarian berbasis Jaccard; subkelompok bertahan bila median kestabilan ≥0,70, kuantil ke-10 ≥0,45, recall pengenalan kembali ≥0,80, dan didukung minimal dua representasi fitur independen. Suatu klaster induk hanya mengekspos lapisan rinci bila sedikitnya dua subkelompok lolos seluruh kriteria (aturan bifurkasi minimum).

## Faktor atribut berbasis residual (ICA)

Histogram konsep lunak pada wilayah *foreground* dibentuk dengan *softmax* bertemperatur 0,07 atas tiga konsep teratas tiap *patch*. Residu log-rasio terhadap k tetangga terdekat pada ruang G_dual menghasilkan matriks residual per citra: nilai positif menandai konsep yang menonjol dibanding tetangga, nilai negatif menandai konsep yang lebih lemah.

Faktor kontinu global diekstraksi dengan FastICA (k∈{10,20,40}, rank∈{8,12,16,24}, tiga *seed* per konfigurasi, *unit-variance whitening*); konfigurasi dipilih dari kandidat dengan galat rekonstruksi *held-out* tidak lebih dari 12% di atas terbaik, dengan rank terkecil dan stabilitas tertinggi. Tiap faktor diuji lima repetisi *bootstrap* (median kesamaan ≥0,78, kuantil ke-10 ≥0,55) dan disaring agar komplementer terhadap struktur klaster: η²<0,55 terhadap subkelompok visual tervalidasi, R²<0,45 terhadap fitur akuisisi, penolakan bila lebih dari 80% contoh skor tertinggi berasal dari satu klaster induk, dan pemangkasan redundansi pada |ρ|≥0,90.

Prosedur yang sama dijalankan terpisah per klaster induk berskala minimal 100 citra (k=20, rank∈{2,3,4,5,6}, toleransi galat 15%) untuk memperoleh faktor *family-local*. Karena setiap model dipelajari independen di dalam klaster induknya, skor faktor antarklaster induk tidak diinterpretasikan pada skala yang sama.

## Interpretasi semantik

Setelah struktur numerik dibekukan, interpretasi semantik dilakukan secara manual pada tiga tingkatan klaster berdasarkan citra representatif dan metrik pendukung. Skor dari Regresi Logistik berbasis *cosine similarity* digunakan untuk membantu peninjauan, bukan sebagai probabilitas semantik yang terkalibrasi. Klaster yang didominasi bias pemotretan diberi status terpisah dari atribut objek, dan struktur dengan pola visual ambigu dibiarkan tanpa label. Makna tiap komponen ICA diinterpretasikan dari kontras visual antarkutub nilai ekstrem; komponen yang redundan terhadap label klaster atau sekadar merefleksikan variasi pengambilan gambar dikesampingkan.

## Empat dimensi saran pengolahan

Label semantik dipadukan dengan bukti literatur dan lembaga terkait pengelolaan limbah elektronik untuk membentuk empat dimensi pendukung keputusan pada skala diskret 1–4: RRP (potensi pemulihan sumber daya), WRO (peluang penggunaan kembali perangkat utuh), CSO (peluang penyelamatan komponen), dan TPC (kompleksitas atau kebutuhan penanganan khusus). Sebuah dimensi dapat tidak menghasilkan nilai bila bukti yang tersedia belum mencukupi.

Profil dibentuk secara hierarkis: nilai acuan tiap kriteria pada tingkat klaster induk ditentukan dari bukti eksternal, kemudian informasi yang lebih spesifik dari subkelompok visual tervalidasi, daun visual, dan faktor kontinu ICA hanya digunakan bila peran semantiknya relevan terhadap kriteria tertentu. Contoh pada klaster induk telepon pintar: WRO beracuan 4 (tinggi) berdasarkan literatur; pada penyempurnaan berbasis kondisi visual, 263 citra tanpa kerusakan layar berat memperoleh level 3 dan 89 citra dengan layar retak/pecah memperoleh level 1.

---

## Perluasan implementasi teknis

Bagian ini mendokumentasikan lapisan implementasi di repositori. Bagian ini bukan narasi riset pada laporan dan tidak mengubah hasil riset di atas.

### Tiga notebook eksekusi

- `01_CIRCL_E_Discovery.ipynb` — ekstraksi representasi dan pembentukan struktur klaster; menghasilkan handoff `CIRCL_E_Discovery_Handoff.zip`.
- `02_CIRCL_E_Semantic_Mapping.ipynb` — interpretasi semantik atas struktur yang dibekukan; menghasilkan artefak `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/` dan handoff `CIRCL_E_Semantic_Mapping_Handoff.zip`.
- `03_CIRCL_E_Post_Mapping.ipynb` — pembentukan profil ordinal dan validasi; menghasilkan `outputs/`.

### IRP — diagnostik implementasi tambahan

**IRP** (*Relative Inspection/Resolution Priority*) adalah diagnostik implementasi tingkat inspeksi/resolusi tambahan yang diperkenalkan pada implementasi Post-Mapping saat ini: prioritas inspeksi relatif di dalam satu klaster induk, dibentuk dari status penugasan operasional, ambiguitas semantik/bukti, dan keatipikalitas visual *within-parent*. IRP bersifat komparatif, bukan dimensi riset kelima, dan tidak dilaporkan sebagai hasil utama. Dimensi saran pengolahan hasil riset adalah empat: RRP, WRO, CSO, TPC.

### Acuan kriteria dan acuan rute

Tahap Post-Mapping menggunakan 192 acuan kriteria (75 berbasis literatur) dan 128 acuan rute (9 berbasis literatur). Setiap acuan berbasis literatur mencatat dependensi sumber pada level klaim. Kategori asal-usul keputusan: `FROZEN_SEMANTIC` (ditetapkan saat Tahap 2), `LITERATURE_SYNTHESIS` (didukung sumber tercatat), dan `MODEL_RATIONALE` (aturan model eksplisit). Registri terkait:

- `outputs/derived/semantic_transition_registry.csv` — transisi semantik dari subkelompok ke kriteria dan rute
- `outputs/derived/parent_route_affinity_map.csv` — kompatibilitas rute per klaster induk
- `outputs/derived/external_source_registry.csv` — sumber eksternal dengan locator
- `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/mapping/semantic_structure_map.csv` — label, peran, dan status tiap struktur Discovery

### Analisis penghilangan sumber

Penghilangan satu sumber literatur mengklasifikasikan dampaknya pada tiap acuan: *unchanged*, *broadened*, *downgraded* ke rationale model, atau *unsupported*. Hasil per sumber tersimpan di `outputs/derived/source_ablation_results.csv`; kasus utama (E001) dibahas di [docs/results.md](results.md).

### Aturan abstention operasional

- `unknown_mixed`: abstain pada semua dimensi utama.
- `reliable_parent_only`: tidak menerima semantik tingkat subkelompok.
- Daun visual bersifat deskriptif dan tidak menaikkan status operasional gambar.
- Keatipikalitas *patch* bersifat *identity-relative*, bukan probabilitas kerusakan.
- Subkelompok dengan pola akuisisi (mis. *acquisition-style* pada layar) tidak berefek pada dimensi utama.

### Kontrak antartahap

Nama field berikut adalah kontrak downstream antar notebook dan tidak boleh diganti: `raw_parent_id`, `validated_fine_group_id`, `raw_visual_leaf_id`, `discovery_status` beserta aturan abstention, nama kolom CSV utama, semantic key dan mapping fields, RRP/WRO/CSO/TPC sebagai empat dimensi utama penelitian, serta IRP sebagai diagnostik tambahan pada implementasi Post-Mapping, beserta route ID, serta semantik level ordinal. Detail lingkungan eksekusi ada di [docs/reproducibility.md](reproducibility.md).
