# Hasil — CIRCL-E

Dokumen ini menyajikan hasil dan pembahasan sebagaimana laporan penelitian Big Data Challenge 2026 (bagian Hasil dan Pembahasan), diikuti diagnostik implementasi tambahan yang bukan temuan riset utama. Pendamping terstruktur hasil ekspor pipeline: `outputs/report/final_results.md` (Tahap 3) dan `CIRCL_E_STAGE2_EVIDENCE_FIRST_ARTIFACTS/report/stage2_semantic_report.md` (Tahap 2).

Tanggal analisis: 2026-09-26. Struktur upstream: 3.793 citra kanonik (dari 3.961 citra mentah), 16 klaster induk, 28 subklaster visual tervalidasi, 48 daun visual; keanggotaan numerik dan pemetaan semantik tidak berubah sejak pembekuan.

## Ketahanan struktur dan kontrol negatif

### Evaluasi estimasi foreground

Isolasi objek dilakukan melalui estimasi bounding box pada tiap citra. Hasilnya memotong area objek utama secara konsisten pada berbagai jenis perangkat dan kondisi latar belakang, sehingga variasi latar tidak menjadi dasar pembentukan klaster.

### Kontrol negatif latar belakang

Kontrol negatif menguji apakah struktur klaster dapat direproduksi hanya dari informasi latar: histogram konsep latar belakang direduksi menjadi 64 komponen utama, lalu dikelompokkan ulang dengan K-means pada jumlah kelompok yang sama dengan partisi acuan. Partisi berbasis latar hanya mencapai **ARI 0,096** terhadap partisi induk final — struktur induk tidak dapat direproduksi dari informasi latar semata. Pola serupa berlaku pada sebagian besar subkelompok visual tervalidasi, dengan satu pengecualian: klaster induk P09 (layar panel datar/televisi) mencapai ARI 0,486, menandakan struktur rincinya memiliki ketergantungan kuat pada konteks akuisisi.

### Degradasi visual terkendali

Enam degradasi visual terkendali pada 160 citra menghasilkan proporsi penugasan yang tetap **0,963–0,994** pada tingkat klaster induk dan **0,962–1,000** pada subklaster visual tervalidasi.

## Evaluasi struktur klaster

### Klaster induk

Dari *grid search* K-means (K∈{16,18,20}), HDBSCAN, dan Leiden-CPM pada tiga representasi global, hanya K-means yang lolos seluruh gerbang struktural: HDBSCAN gagal karena coverage hanya 0,660–0,676, sedangkan Leiden-CPM dan komponen *mutual-kNN* menghasilkan ratusan hingga ribuan komunitas mikro (jauh di luar rentang 10–25 klaster), bahkan dengan silhouette negatif pada beberapa konfigurasi. Dua kandidat yang lolos — K=16 pada representasi global *foreground* dan K=16 pada representasi dual — nyaris setara pada recall (0,704 vs 0,696) dan presisi kasus terburuk (0,892 vs 0,875); keduanya dipisahkan oleh skor kelebihan *nuisance* (0,396 vs 0,404), sehingga representasi *foreground* dengan **K-means K=16** ditetapkan sebagai klaster induk terpilih.

Klaster induk terpilih mencapai coverage 1,000, silhouette 0,478, dan stabilitas resampling ARI_g 0,954.

### Subklaster visual tervalidasi dan daun visual

Dari 16 klaster induk, dua struktur subklaster dikonstruksi secara independen. Subklaster visual tervalidasi dimulai dari 36 kandidat: 6 tereliminasi pada uji individual (resampling atau korespondensi lintas pandang) dan 2 klaster induk digugurkan aturan bifurkasi minimum, menyisakan **28 subklaster valid** — stabilitas partisi global tidak menjamin keandalan subklaster individual. Daun visual dibentuk tanpa uji kelangsungan individual agar variasi pose dan fisik tetap terjaga, menghasilkan **48 daun visual**.

| Struktur | Jml. | Coverage | Silhouette | ARI_g | ARI_g Q10 | Recall makro | Recall Q10 | Precision Q10 |
|---|---|---|---|---|---|---|---|---|
| Klaster induk | 16 | 1,000 | 0,478 | 0,954 | 0,905 | 0,965 | 0,948 | 0,921 |
| Subklaster visual tervalidasi | 28 | 0,653 | 0,457 | 0,981 | 0,928 | 0,966 | 0,891 | 0,937 |
| Daun visual | 48 | 1,000 | 0,202 | 0,961 | 0,912 | 0,915 | 0,748 | 0,886 |

Pola ketiganya konsisten dengan rancangannya: subklaster tervalidasi mencatat ARI_g tertinggi (0,981) berkat gerbang paling ketat, tetapi coverage-nya terbatas (0,653) akibat aturan bifurkasi; daun visual mencapai coverage penuh dengan silhouette dan recall Q10 terendah, sesuai sifatnya yang permisif terhadap variasi nonidentitas.

## Interpretasi semantik klaster induk

| ID | Label semantik | N | Status |
|---|---|---|---|
| P00 | Residu campuran/heterogen | 384 | mixed (Abstain) |
| P01 | Telepon pintar | 368 | accepted (Operational) |
| P02 | Papan sirkuit/komponen elektronik | 354 | accepted_broad_only |
| P03 | Mencit komputer | 304 | accepted (Operational) |
| P04 | Printer | 269 | accepted (Operational) |
| P05 | Papan ketik komputer | 263 | accepted (Operational) |
| P06 | Laptop | 252 | accepted (Operational) |
| P07 | Microwave | 235 | accepted (Operational) |
| P08 | Adegan tumpukan sampah elektronik | 232 | accepted (Operational) |
| P09 | Layar panel datar/televisi | 218 | accepted_broad_only |
| P10 | Baterai | 202 | accepted (Operational) |
| P11 | Mesin cuci bukaan depan | 195 | accepted (Operational) |
| P12 | Televisi CRT | 174 | accepted (Operational) |
| P13 | Perangkat audio | 142 | accepted_broad_only |
| P14 | Pemutar piringan hitam | 101 | accepted (Operational) |
| P15 | Mesin cuci bukaan atas | 100 | accepted (Operational) |

Sebanyak **12 dari 16 klaster induk berstatus operasional** dan dapat digunakan sebagai dasar penyusunan saran pengolahan. Tiga klaster (P02, P09, P13) berstatus *accepted_broad_only*: subtipe di dalamnya tidak dapat dijadikan dasar keputusan tanpa validasi lanjutan. P00 (residual, populasi terbesar) berstatus *mixed* dengan kelas penggunaan Abstain, sejalan dengan keandalan operasionalnya yang lemah. Visualisasi t-SNE menunjukkan sebagian besar klaster membentuk kelompok padat dan terpisah tegas; P00 tersebar di pusat ruang fitur, memvalidasi keputusan Abstain-nya.

Contoh peran semantik pada tingkat subkelompok (laporan, Tabel contoh anak struktur):

| ID | Induk | Label semantik | Peran | Status |
|---|---|---|---|---|
| F01 | P01 | Layar retak/pecah | condition | accepted |
| F02 | P02 | Papan PCB terisolasi | component_subtype | accepted |
| F10 | P06 | Konfigurasi laptop terbuka | configuration | accepted |
| F13 | P08 | Tumpukan e-waste skala objek | scene_context | accepted |
| F15 | P09 | Monitor konteks meja/ruangan | acquisition_style | nuisance_context |
| L01 | P00 | Subset residu mirip perangkat genggam | ambiguous | mixed |
| L47 | P15 | Daun tunggal (tanpa pemecahan) | device_family | accepted_broad_only |

Peran *condition* dan *configuration* langsung relevan untuk keputusan penanganan, sedangkan peran *acquisition_style* berstatus *nuisance_context* — F15 ditandai sebagai sinyal akuisisi murni dan tidak dipromosikan menjadi taksonomi. Temuan ini menunjukkan bahwa sistem dapat memisahkan sebagian variasi kondisi pemotretan dari variasi identitas objek.

## Atribut visual kontinu (ICA)

Pada tingkat global, hanya **3 dari 16 komponen independen** yang diterima sebagai atribut kontinu tambahan; sisanya tersaring karena redundansi terhadap klaster (4), variasi akuisisi (4), dan pola visual tidak konsisten (5). Salah satu atribut yang diterima adalah sumbu *Object integrity/presentation organization*, dari presentasi objek terbongkar/tidak beraturan hingga objek utuh tersaji tunggal — menandakan sebagian besar variasi visual global telah terwakili struktur klaster.

Pada tingkat *family-local*, **13 dari 24 kombinasi klaster induk/komponen** diterima. Pembatasan ruang evaluasi pada masing-masing klaster induk mengurangi pengaruh variasi identitas antarkelas, sehingga komponen lebih efektif menangkap variasi yang spesifik — misalnya sumbu *Laptop integrity/dismantling state* pada klaster laptop, dari presentasi terbongkar/tumpukan skrap hingga laptop utuh tunggal.

## Empat dimensi saran pengolahan

Label semantik dipadukan dengan bukti literatur dan lembaga terkait pengelolaan limbah elektronik membentuk empat dimensi pendukung keputusan pada skala diskret 1–4: **RRP** (potensi pemulihan sumber daya), **WRO** (peluang penggunaan kembali perangkat utuh), **CSO** (peluang penyelamatan komponen), dan **TPC** (kompleksitas/kebutuhan penanganan khusus). Profil dibentuk hierarkis: nilai acuan tingkat klaster induk dari bukti eksternal, disempurnakan oleh subkelompok visual tervalidasi, daun visual, dan faktor ICA bila peran semantiknya relevan.

Contoh klaster telepon pintar (P01): WRO memperoleh nilai acuan 4 (tinggi) berdasarkan literatur. Pada penyempurnaan berbasis kondisi visual, 263 citra tanpa kerusakan layar berat memperoleh WRO level 3, sedangkan 89 citra dengan layar retak/pecah memperoleh level 1. Angka ini menunjukkan bahwa kondisi fisik yang terlihat dapat menyempurnakan peluang penggunaan kembali — bukan klaim fungsi maupun kelayakan perbaikan.

---

## Diagnostik implementasi tambahan

Bagian ini mendokumentasikan hasil implementasi Post-Mapping saat ini. Bagian ini bukan temuan riset utama pada laporan dan diberi tempat terpisah agar tidak tertukar dengan hasil riset di atas.

### Cakupan profil ordinal

| Dimensi | Terisi | Total | Catatan |
|---------|-------|-------|---------|
| RRP | 2.918 | 3.793 | 454 citra berstatus unknown/mixed; sebagian kasus lain tetap tidak memperoleh nilai karena bukti khusus untuk dimensi tersebut belum mencukupi |
| WRO | 642 | 3.793 | 545 gambar level komponen tidak berlaku (*not-applicable*), dihitung terpisah dari kasus yang tidak memperoleh nilai karena bukti belum mencukupi |
| CSO | 3.119 | 3.793 | 454 citra unknown/mixed abstain; sebagian kasus lain tetap tidak memperoleh nilai karena bukti khusus dimensi ini belum mencukupi |
| TPC | 3.119 | 3.793 | 454 citra unknown/mixed abstain; sebagian kasus lain tetap tidak memperoleh nilai karena bukti khusus dimensi ini belum mencukupi |

WRO yang lebih rendah daripada CSO bukan anomali: WRO menilai perangkat secara utuh dan menuntut bukti visual konfigurasi yang masih lengkap, sehingga komponen seperti PCB tidak diberi status penggunaan kembali sebagai perangkat utuh. Laptop yang terbongkar dapat memiliki WRO rendah sekaligus CSO lebih tinggi karena komponennya terlihat jelas.

### IRP — diagnostik inspeksi tambahan

**IRP** (*Relative Inspection/Resolution Priority*) adalah diagnostik implementasi tingkat inspeksi/resolusi tambahan yang diperkenalkan pada implementasi Post-Mapping saat ini: prioritas inspeksi relatif di dalam satu klaster induk, dibentuk dari status penugasan operasional, ambiguitas semantik/bukti, dan keatipikalitas visual *within-parent*. IRP bersifat komparatif — bukan hitungan tunggal lintas dataset — dan bukan dimensi riset kelima; aturannya tercatat di `outputs/derived/irp_rule_registry.csv`.

### Analisis penghilangan sumber

Menghilangkan E001 — UNITAR SCYCLE, *E-waste Statistics: Guidelines on Classifications, Reporting and Indicators, Third Edition* (2026, DOI [10.5281/zenodo.18328494](https://doi.org/10.5281/zenodo.18328494)) — membuat 2.113 dari 2.918 profil RRP yang sebelumnya terisi menjadi tidak terisi (72,4%). Dari 19 acuan kriteria yang terpengaruh E001: 7 tidak berubah, 2 menjadi lebih luas, 10 menjadi tanpa dukungan. Hasil ini menunjukkan ketergantungan pada cakupan bukti literatur — E001 menyediakan taksonomi produk (UNU-KEY v2) yang diperlukan untuk menentukan relevansi pemulihan sumber daya — bukan ukuran akurasi model.

Sumber lain: E007 dan E008 masing-masing berkontribusi pada 293 dan 168 profil RRP yang menjadi tidak terisi bila dihilangkan; sumber lainnya tidak menyebabkan profil RRP baru yang tidak terisi. Detail per sumber ada di `outputs/derived/source_ablation_results.csv`.

### Pemeriksaan internal

Notebook 3 menjalankan 74 pemeriksaan internal yang mencakup konsistensi struktur, kebijakan abstention, aturan bukti per dimensi, validitas level ordinal, rekompilasi analisis penghilangan sumber, dan integritas registri; seluruhnya **74/74 lulus**. Ini adalah pemeriksaan internal implementasi — bukan benchmark eksternal, bukan skor akurasi prediktif, dan bukan sertifikasi produksi.

### Kompatibilitas rute

Setiap klaster induk memiliki kompatibilitas rute yang tercatat di `outputs/derived/parent_route_affinity_map.csv`. Rute yang tersedia: `reuse_refurbish`, `parts_harvest`, `bulk_material_recovery`, `specialist_pcb`, `battery_specialist`, `crt_specialist`, `sorting_dismantling`, `residual_treatment`. Kompatibilitas rute naik atau turun mengikuti transisi semantik yang tercatat di `outputs/derived/semantic_transition_registry.csv`; perubahan rute tidak mengubah RRP/WRO/CSO/TPC secara bersamaan. Nilai rute menunjukkan kecenderungan kompatibilitas, bukan rekomendasi penanganan yang optimal.

## Batasan interpretasi

- Profil ordinal tidak menginferensikan fungsionalitas perangkat, berat material, komposisi material yang tepat, kimia baterai, keberhasilan perbaikan, *yield* pemulihan, nilai pasar, pembayaran *recycler*, profitabilitas, status hukum limbah, klasifikasi bahaya, maupun rute penanganan optimal.
- Level ordinal bukan skala rasio.
- Nilai rute adalah status kompatibilitas, bukan rekomendasi.
- Rentang model/bukti adalah rentang sensitivitas, bukan interval kepercayaan.
- Dukungan penugasan bersifat diagnostik kekuatan perutean *within-parent*, bukan probabilitas.