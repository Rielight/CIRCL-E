# CIRCL-E Stage 2 — Semantic Mapping

## Metode
Keputusan semantik menggunakan struktur Discovery yang telah dibekukan. Registry memuat keputusan untuk broad parent, validated fine group, raw visual leaf, global/family ICA, dan patch atypicality. Evidence montage dapat dirender ulang secara opsional tanpa mengubah registry.

## Struktur Discovery yang dipertahankan
- canonical images: 3,793
- raw images: 3,961
- parents / fine groups / raw leaves: 16 / 28 / 48
- global / family ICA candidates: 16 / 24
- numerical memberships changed: **no**

## Batas operasional
- `unknown_mixed` tetap abstain
- `reliable_parent_only` tidak menerima fine semantics
- raw visual leaves bersifat deskriptif dan tidak menaikkan status operasional
- patch atypicality bukan probabilitas kerusakan
- PCA, t-SNE, hierarchy, dan similarity matrix hanya digunakan untuk komunikasi
