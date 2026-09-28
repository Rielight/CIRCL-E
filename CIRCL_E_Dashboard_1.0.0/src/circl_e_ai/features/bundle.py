"""Construct every frozen numerical representation required by runtime inference."""
from __future__ import annotations
from circl_e_ai.contracts.models import FeatureBundle
from circl_e_ai.input.image import load_rgb_image, image_sha256
from .dino import dino_forward
from .foreground import foreground_bbox_from_dino
from .cradio import extract_G_whole, extract_G_foreground
from .vlad import extract_L_whole, extract_L_foreground
from .preprocess import bbox_crop
from .concepts import base_concept_features, hires_foreground_concept_features
from .dense_patch import dense_grid16_from_highres_record
from .views import compose_named_views


def build_feature_bundle(image, release) -> FeatureBundle:
    """Pixel -> exact frozen feature bundle. No fitting, no cohort mutation."""
    im = load_rgb_image(image)
    digest = image_sha256(im)
    cfg = getattr(release.assets, "runtime_config", None) or {}

    # One whole-image DINO pass drives foreground proposal, L_whole and base concepts.
    whole_dino = dino_forward(
        im, release,
        short=int(cfg.get("dino_short", 512)),
        max_long=int(cfg.get("dino_max_long", 1024)),
    )
    bbox = foreground_bbox_from_dino(whole_dino["late"], whole_dino["cls"], whole_dino["grid"])

    G_whole = extract_G_whole(im, release)
    G_foreground = extract_G_foreground(im, bbox, release)
    L_whole = extract_L_whole(whole_dino, release)
    L_foreground, _ = extract_L_foreground(im, bbox, release)
    named = compose_named_views(G_whole, G_foreground, L_whole, L_foreground)

    base_concepts = base_concept_features(whole_dino, bbox, release)

    # Family ICA and patch atypicality share the exact same high-resolution foreground DINO pass.
    crop = bbox_crop(im, bbox, margin=float(cfg.get("foreground_margin", 0.04)))
    highres = dino_forward(
        crop, release,
        short=int(cfg.get("attr_short", 768)),
        max_long=int(cfg.get("attr_max_long", 1024)),
    )
    HFG_hires, _ = hires_foreground_concept_features(highres, release)
    dense = dense_grid16_from_highres_record(highres, release)

    return FeatureBundle(
        image_sha256=digest,
        foreground_bbox=bbox.tolist(),
        G_whole=G_whole,
        G_foreground=G_foreground,
        G_dual=named["G_dual"],
        L_whole=L_whole,
        L_foreground=L_foreground,
        L_dual=named["L_dual"],
        HSOFT=base_concepts["HSOFT"],
        HFG_hires=HFG_hires,
        dense_patch_g16=dense,
        named_views=named,
    )
