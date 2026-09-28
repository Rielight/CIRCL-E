"""DINO 512-concept representations used by the frozen ICA branches."""
from __future__ import annotations
import numpy as np
from .math import normalize_rows_l2, apply_npz_transform_raw
from .foreground import patch_mask_from_bbox


def advanced_patch_descriptor(mid, late, release):
    midz = normalize_rows_l2(apply_npz_transform_raw(mid, release.assets.transforms["concept_mid_pca64"]))
    latez = normalize_rows_l2(apply_npz_transform_raw(late, release.assets.transforms["concept_late_pca64"]))
    return normalize_rows_l2(np.c_[midz / np.sqrt(2), latez / np.sqrt(2)])


def soft_histogram(sim, k: int = 512, temperature: float = 0.07):
    if len(sim) == 0:
        return np.zeros(k, np.float32)
    top = np.argpartition(sim, -3, axis=1)[:, -3:]
    ss = np.take_along_axis(sim, top, axis=1)
    ww = np.exp((ss - ss.max(1, keepdims=True)) / float(temperature))
    ww /= np.maximum(ww.sum(1, keepdims=True), 1e-12)
    h = np.zeros(k, np.float32)
    for rr in range(len(top)):
        np.add.at(h, top[rr], ww[rr])
    return h / max(float(h.sum()), 1e-12)


def base_concept_features(dino_record, foreground_bbox, release) -> dict:
    """Build source-compatible HFG/HBG/HSOFT on the whole-image DINO grid."""
    desc = advanced_patch_descriptor(dino_record["mid"], dino_record["late"], release)
    centers = normalize_rows_l2(release.assets.transforms["concept512_centers"])
    sim = desc @ centers.T
    assign = np.argmax(sim, axis=1)
    fg = patch_mask_from_bbox(dino_record["grid"], foreground_bbox)
    if fg.sum() < max(4, 0.05 * len(fg)):
        fg[:] = True
    bg = ~fg
    hfg = np.bincount(assign[fg], minlength=len(centers)).astype(np.float32)
    hfg /= max(float(hfg.sum()), 1.0)
    hbg = np.bincount(assign[bg], minlength=len(centers)).astype(np.float32) if bg.any() else np.zeros(len(centers), np.float32)
    hbg /= max(float(hbg.sum()), 1.0) if hbg.sum() else 1.0
    hsoft = soft_histogram(sim[fg], k=len(centers))
    return {"HFG": hfg, "HBG": hbg, "HSOFT": hsoft, "descriptor": desc, "assignment": assign, "fg_mask": fg}


def hires_foreground_concept_features(highres_foreground_dino_record, release):
    """Exact family-ICA concept path: high-res foreground descriptor -> top-3 soft 512 histogram."""
    desc = advanced_patch_descriptor(
        highres_foreground_dino_record["mid"],
        highres_foreground_dino_record["late"],
        release,
    )
    centers = normalize_rows_l2(release.assets.transforms["concept512_centers"])
    return soft_histogram(desc @ centers.T, k=len(centers)), desc
