"""Thin local application layer around the frozen :mod:`circl_e_ai` runtime.

This package never performs scientific inference itself. It only:

* loads a frozen release once and caches it;
* validates/sanitizes uploaded image bytes safely;
* calls the existing production ``circl_e_ai.pipeline.infer.infer_image`` path;
* converts the returned ``InferenceResult`` into a stable presentation model.

No fitting, retraining, recalibration or mutation of frozen assets happens here.
"""
from .errors import (
    AppError,
    ImageValidationError,
    InferenceError,
    ReleaseLoadError,
    cuda_guidance,
)
from .inference_service import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_EXTENSIONS,
    InferenceService,
    InputInfo,
    ReleaseInfo,
)
from .labels import DIMENSION_ORDER, load_display_labels
from .presentation import (
    DISPLAY_NA,
    best_available_identity,
    display_value,
    format_percentile,
    prepare_display_result,
    to_json_safe,
)
from .ui_helpers import (
    RESULT_STATE_KEYS,
    backbone_env_overrides,
    backbone_paths_missing,
    drop_empty_columns,
    effective_backbone_paths,
    humanize_token,
    inference_settings_key,
    input_source,
    manifest_fingerprint,
    read_example_bytes,
    result_is_stale,
    result_key,
    select_example_images,
    sha256_bytes,
)

__all__ = [
    "AppError",
    "ImageValidationError",
    "InferenceError",
    "ReleaseLoadError",
    "cuda_guidance",
    "InferenceService",
    "InputInfo",
    "ReleaseInfo",
    "MAX_UPLOAD_BYTES",
    "SUPPORTED_EXTENSIONS",
    "DIMENSION_ORDER",
    "load_display_labels",
    "DISPLAY_NA",
    "best_available_identity",
    "display_value",
    "format_percentile",
    "prepare_display_result",
    "to_json_safe",
    "backbone_env_overrides",
    "backbone_paths_missing",
    "drop_empty_columns",
    "effective_backbone_paths",
    "humanize_token",
    "inference_settings_key",
    "input_source",
    "manifest_fingerprint",
    "read_example_bytes",
    "result_is_stale",
    "result_key",
    "RESULT_STATE_KEYS",
    "select_example_images",
    "sha256_bytes",
]
