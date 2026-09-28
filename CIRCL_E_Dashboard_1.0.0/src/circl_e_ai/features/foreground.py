"""Exact deterministic DINO-derived foreground proposal from the discovery notebook."""
from __future__ import annotations
import numpy as np
from scipy.ndimage import label as cc_label, gaussian_filter
from .math import normalize_rows_l2


def otsu_threshold(x, bins: int = 64) -> float:
    v = np.asarray(x, float).ravel()
    lo, hi = float(v.min()), float(v.max())
    if not np.isfinite(lo + hi) or hi <= lo + 1e-12:
        return float(np.median(v))
    hist, edges = np.histogram(v, bins=bins, range=(lo, hi))
    p = hist / max(hist.sum(), 1)
    cent = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)
    w1 = 1 - w0
    mu0 = np.cumsum(p * cent) / np.maximum(w0, 1e-12)
    mt = (p * cent).sum()
    mu1 = (mt - np.cumsum(p * cent)) / np.maximum(w1, 1e-12)
    score = w0 * w1 * (mu0 - mu1) ** 2
    return float(cent[int(np.nanargmax(score))])


def foreground_bbox_from_dino(late_patch_tokens, cls_vector, grid, pad: float = 0.08) -> np.ndarray:
    gh, gw = map(int, grid)
    p = normalize_rows_l2(late_patch_tokens)
    c = normalize_rows_l2(np.asarray(cls_vector).reshape(1, -1))[0]
    score = (p @ c).reshape(gh, gw)
    score = gaussian_filter(score, sigma=0.8)
    cand = []
    for t in [otsu_threshold(score), float(np.quantile(score, 0.55)), float(np.quantile(score, 0.65))]:
        mask = score >= t
        if mask.mean() < 0.04 or mask.mean() > 0.95:
            continue
        lab, nc = cc_label(mask)
        comps = []
        for k in range(1, nc + 1):
            m = lab == k
            if m.sum() < max(2, 0.01 * mask.size):
                continue
            border = np.r_[m[0], m[-1], m[:, 0], m[:, -1]].mean()
            val = float(score[m].mean() + 0.2 * np.log1p(m.sum()) - 0.25 * border)
            comps.append((val, m))
        if comps:
            mask = max(comps, key=lambda q: q[0])[1]
        ys, xs = np.where(mask)
        if not len(xs):
            continue
        x0, x1 = xs.min() / gw, (xs.max() + 1) / gw
        y0, y1 = ys.min() / gh, (ys.max() + 1) / gh
        area = (x1 - x0) * (y1 - y0)
        centrality = 1 - (abs((x0 + x1) / 2 - 0.5) + abs((y0 + y1) / 2 - 0.5)) / 2
        conf = float(np.clip((score[mask].mean() - score.mean()) / (score.std() + 1e-6), 0, 3) / 3)
        qual = conf + 0.25 * centrality - 0.15 * abs(area - 0.55)
        cand.append((qual, (x0, y0, x1, y1, conf, area)))
    if not cand:
        return np.array([0, 0, 1, 1, 0, 1], np.float32)
    _, (x0, y0, x1, y1, conf, area) = max(cand, key=lambda q: q[0])
    dx = (x1 - x0) * pad
    dy = (y1 - y0) * pad
    return np.array([
        max(0, x0 - dx), max(0, y0 - dy), min(1, x1 + dx), min(1, y1 + dy), conf, area
    ], np.float32)


def patch_mask_from_bbox(grid, bbox) -> np.ndarray:
    gh, gw = map(int, grid)
    yy = (np.arange(gh) + 0.5) / gh
    xx = (np.arange(gw) + 0.5) / gw
    X, Y = np.meshgrid(xx, yy)
    b = np.asarray(bbox, float)
    return ((X >= b[0]) & (X <= b[2]) & (Y >= b[1]) & (Y <= b[3])).ravel()
