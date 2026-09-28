"""Frozen DINO VLAD encoder and output projection."""
from __future__ import annotations
import numpy as np
from .math import normalize_rows_l2, apply_npz_transform
from .preprocess import bbox_crop
from .dino import dino_forward


def vlad_raw(late_patches, release):
    p = apply_npz_transform(late_patches, release.assets.transforms["vlad_patch_pca64"])
    centers = normalize_rows_l2(release.assets.transforms["vlad32_centers"])
    assign = np.argmax(p @ centers.T, axis=1)
    V = np.zeros_like(centers, np.float32)
    for c in range(len(centers)):
        m = assign == c
        if np.any(m):
            r = (p[m] - centers[c]).sum(0)
            nr = np.linalg.norm(r)
            V[c] = r / nr if nr > 1e-12 else r
    v = V.reshape(-1)
    v = np.sign(v) * np.sqrt(np.abs(v) + 1e-12)
    return normalize_rows_l2(v.reshape(1, -1))


def vlad_encode_final_patches(late_patches, release):
    return apply_npz_transform(vlad_raw(late_patches, release), release.assets.transforms["vlad32_pca512_alpha05"])


def extract_L_whole(dino_record, release):
    return vlad_encode_final_patches(dino_record["late"], release)


def extract_L_foreground(image, bbox, release):
    cfg = getattr(release.assets, "runtime_config", None) or {}
    crop = bbox_crop(image, bbox, margin=float(cfg.get("foreground_margin", 0.04)))
    rec = dino_forward(crop, release,
                       short=int(cfg.get("dino_short", 512)),
                       max_long=int(cfg.get("dino_max_long", 1024)))
    return vlad_encode_final_patches(rec["late"], release), rec
