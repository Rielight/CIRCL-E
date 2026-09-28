"""Exact 16x16 foreground DINO descriptor branch used by local atypicality."""
from __future__ import annotations
import numpy as np
from .math import normalize_rows_l2
from .concepts import advanced_patch_descriptor


def dense_grid16_from_highres_record(highres_foreground_dino_record, release):
    import torch
    import torch.nn.functional as F
    D = advanced_patch_descriptor(
        highres_foreground_dino_record["mid"],
        highres_foreground_dino_record["late"],
        release,
    )
    gh, gw = highres_foreground_dino_record["grid"]
    T = torch.from_numpy(D.reshape(gh, gw, -1)).permute(2, 0, 1)[None]
    pooled = F.adaptive_avg_pool2d(T, (16, 16))[0].permute(1, 2, 0).reshape(-1, D.shape[1]).numpy()
    # The discovery source persists this grid through a C-order float16 memmap
    # (notebook cell 42: ``M[i] = normalize_rows_l2(...).astype(np.float16)`` is
    # assigned into ``open_memmap(..., shape=(N, 256, 128))``), so every row later
    # read back by the farthest-point prototype reducer (cell 43) is row-major.
    # ``.numpy()`` here is F-contiguous; keeping that layout changes the row-norm
    # reduction order inside ``normalize_rows_l2`` by ~1e-7 versus the source
    # memmap row, which flips genuine FPS near-ties. Force the source-compatible
    # C-order layout (values are bit-identical; only strides change).
    return np.ascontiguousarray(normalize_rows_l2(pooled)).astype(np.float32)


def extract_dense_grid16(image, bbox, release):
    """Convenience path when a shared high-res foreground DINO record is not already available."""
    from .preprocess import bbox_crop
    from .dino import dino_forward
    cfg = getattr(release.assets, "runtime_config", None) or {}
    crop = bbox_crop(image, bbox, margin=float(cfg.get("foreground_margin", 0.04)))
    rec = dino_forward(crop, release,
                       short=int(cfg.get("attr_short", 768)),
                       max_long=int(cfg.get("attr_max_long", 1024)))
    return dense_grid16_from_highres_record(rec, release)
