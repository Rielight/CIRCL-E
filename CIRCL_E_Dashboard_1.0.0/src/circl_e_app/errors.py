"""Clean, user-facing application errors.

These wrap low-level failures from the frozen runtime so the dashboard can show
an actionable message instead of a traceback. They never change inference
behavior or silently swallow scientific state.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all dashboard/application failures."""

    #: short machine-readable category used for presentation/tests
    category = "app_error"

    def __init__(self, message: str, *, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class ReleaseLoadError(AppError):
    """The frozen release or its bound backbone directories are unavailable."""

    category = "release_load_error"


class ImageValidationError(AppError):
    """The uploaded bytes are not a usable single image."""

    category = "image_validation_error"


class InferenceError(AppError):
    """The frozen inference path raised for a validated image."""

    category = "inference_error"


#: Substrings that indicate a CUDA/GPU device failure rather than a bad image.
_CUDA_MARKERS = (
    "cuda",
    "cudnn",
    "cublas",
    "no kernel image",
    "device-side assert",
    "out of memory",
    "nvidia",
)

_CUDA_HINT = (
    "The compute device failed (CUDA unavailable or out of memory). "
    "Switch 'Compute device' to cpu under Advanced settings and retry."
)


def cuda_guidance(detail: str | None) -> str | None:
    """Return actionable CPU-fallback guidance for CUDA/OOM failures, else None.

    Pure string matching on the low-level error; it never changes inference and
    never masks the underlying failure (the raw detail is still shown).
    """
    text = (detail or "").lower()
    if any(marker in text for marker in _CUDA_MARKERS):
        return _CUDA_HINT
    return None
