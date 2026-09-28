"""CIRCL-E Dashboard — local inference application (single-process Streamlit).

Runtime architecture::

    Streamlit  ->  circl_e_app  ->  frozen circl_e_ai  ->  frozen DINO + C-RADIO

The app orchestrates only. It never re-implements scientific inference, never
mutates frozen assets, and never exposes model/threshold controls. Inference is
fully local: no network call and no runtime model download.

This module is intentionally thin; rendering lives in ``components``, session
state in ``state`` and styling in ``styles`` (all siblings in ``dashboard/``).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Import the sibling dashboard modules regardless of how the app is launched
# (``streamlit run dashboard/app.py`` or a headless AppTest).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import streamlit as st  # noqa: E402

import components as ui  # noqa: E402
import state as session_state  # noqa: E402
from styles import APP_SUBTITLE, APP_TITLE, CSS, DASHBOARD_VERSION, MODEL_RELEASE_NOTE  # noqa: E402

from circl_e_app import (  # noqa: E402
    AppError,
    InferenceError,
    InferenceService,
    backbone_paths_missing,
    effective_backbone_paths,
    inference_settings_key,
    input_source,
    manifest_fingerprint,
    read_example_bytes,
    result_key,
    select_example_images,
    sha256_bytes,
)
from circl_e_app.inference_service import SUPPORTED_EXTENSIONS  # noqa: E402

ROOT = _HERE.parent
UPLOAD_TYPES = sorted(SUPPORTED_EXTENSIONS)
EXAMPLE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

#: Developer controls are only rendered when explicitly enabled. The release UI
#: hides them and takes every setting from the environment.
SHOW_DEV_SETTINGS = os.getenv("CIRCLE_SHOW_DEV_SETTINGS", "0") == "1"


def _default_release_dir() -> str:
    """Release directory: explicit env var, else bundled ``runtime/release``.

    The source repository keeps its development release under
    ``runtime/release-dev``; the deployment bundle ships ``runtime/release``.
    """
    configured = os.getenv("CIRCL_RELEASE_DIR")
    if configured:
        return configured
    for name in ("release", "release-dev"):
        candidate = ROOT / "runtime" / name
        if (candidate / "manifest.json").is_file():
            return str(candidate)
    return str(ROOT / "runtime" / "release")


DEFAULT_RELEASE = _default_release_dir()
DEFAULT_ALLOW_UNVERIFIED = os.getenv("CIRCL_ALLOW_UNVERIFIED", "1") == "1"
DEFAULT_DEVICE = os.getenv("CIRCL_DEVICE", "auto")
SOURCE_ROOT = os.getenv("CIRCLE_SOURCE_ROOT")

st.set_page_config(page_title="CIRCL-E", page_icon="♻️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# A pending "New image" request is honored *before* any widget is instantiated.
# Streamlit forbids mutating a widget key after the widget exists in the same
# run, so the button only sets a flag and the purge happens on the next run.
if st.session_state.pop("_pending_new_image", False):
    session_state.purge_input()


# --------------------------------------------------------------------------- #
# Cached resources
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False, max_entries=2)
def get_service(
    release_dir: str,
    require_verified: bool,
    device: str | None,
    release_fingerprint: str | None,
) -> InferenceService:
    """Cache the service (and, transitively, the loaded frozen release).

    ``release_fingerprint`` participates in the cache key so an in-place release
    rebuild cannot keep serving the previously loaded assets.
    """
    return InferenceService(
        release_dir,
        require_verified=require_verified,
        device=device,
        strict_environment=False,
        release_fingerprint=release_fingerprint,
    )


def read_manifest(release_dir: str) -> dict | None:
    """Read the release manifest fresh on every rerun (tiny file; not cached)."""
    path = Path(release_dir) / "manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 - a corrupt manifest is reported as missing
        return None


@st.cache_data(show_spinner=False, max_entries=2)
def _example_candidates(source_root: str) -> list[str]:
    base = Path(source_root) / "data" / "competition" / "train" / "1_Electronic"
    if not base.is_dir():
        return []
    found = sorted(p for p in base.iterdir() if p.suffix.lower() in EXAMPLE_SUFFIXES)
    return [str(p) for p in select_example_images(found)]


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(
    f'<div class="ce-hero"><h1>{APP_TITLE}</h1>'
    f'<div class="ce-sub">{APP_SUBTITLE}</div></div>',
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Settings (developer panel hidden unless CIRCLE_SHOW_DEV_SETTINGS=1)
# --------------------------------------------------------------------------- #
if SHOW_DEV_SETTINGS:
    with st.expander("Advanced / developer settings", expanded=False):
        release_dir = st.text_input("Release directory", DEFAULT_RELEASE)
        allow_unverified = st.checkbox(
            "Allow unverified release",
            value=DEFAULT_ALLOW_UNVERIFIED,
            help=(
                "The research/decision-support release is not marked canonical. "
                "Disabling this enforces the canonical-release safety check and blocks "
                "inference until a verified release is configured."
            ),
        )
        device_options = ["auto", "cpu", "cuda"]
        device_index = device_options.index(DEFAULT_DEVICE) if DEFAULT_DEVICE in device_options else 0
        device = st.selectbox(
            "Compute device",
            device_options,
            index=device_index,
            help="'auto' uses CUDA when available, otherwise CPU.",
        )
else:
    release_dir = DEFAULT_RELEASE
    allow_unverified = DEFAULT_ALLOW_UNVERIFIED
    device = DEFAULT_DEVICE

manifest = read_manifest(release_dir)
backbones = (manifest or {}).get("backbones", {}) or {}
effective_backbones = effective_backbone_paths(backbones)
backbones_bound = bool(effective_backbones.get("dino_path") and effective_backbones.get("cradio_path"))
missing_backbone_paths = backbone_paths_missing(backbones) if backbones_bound else []
backbones_present = backbones_bound and not missing_backbone_paths
verified = bool((manifest or {}).get("verified"))
require_verified = (not verified) and (not allow_unverified)
release_ready = manifest is not None and backbones_present
device_arg = None if device == "auto" else device
manifest_fp = manifest_fingerprint(release_dir)

# A stored result must not survive a change to the settings that produced it
# (release directory, compute device, the unverified switch, or an in-place
# release rebuild at the same path).
settings_key = inference_settings_key(release_dir, require_verified, device_arg, manifest_fp)
service = get_service(str(Path(release_dir)), require_verified, device_arg, manifest_fp)
labels = service.display_labels()

if manifest is None:
    st.error("No model release is available at the configured location.")
elif not backbones_bound:
    st.error("The release does not bind the model directories; image inference cannot run.")
elif missing_backbone_paths:
    st.error("The model directories are missing: " + ", ".join(missing_backbone_paths))
elif require_verified:
    st.info("Inference is disabled until a verified model release is configured.")


# --------------------------------------------------------------------------- #
# Input workspace
# --------------------------------------------------------------------------- #
st.markdown("### Input")
col_input, col_preview = st.columns([1.05, 1], gap="large")

with col_input:
    uploaded = st.file_uploader(
        "Device image",
        type=UPLOAD_TYPES,
        key=session_state.UPLOAD_KEY,
        help="JPG, PNG or WEBP. The image is processed locally and is never uploaded anywhere.",
    )
    example_path: Path | None = None
    if SOURCE_ROOT:
        examples = [Path(p) for p in _example_candidates(SOURCE_ROOT)]
        if examples:
            names = [f"{p.stem} · {p.suffix.lstrip('.').upper()}" for p in examples]
            choice = st.selectbox(
                "Or use a demonstration image",
                options=list(range(len(examples) + 1)),
                format_func=lambda i: "(none)" if i == 0 else names[i - 1],
                key=session_state.EXAMPLE_KEY,
                disabled=uploaded is not None,
            )
            if choice > 0:
                example_path = examples[choice - 1]

data: bytes | None = None
filename: str | None = None
example_read_error: AppError | None = None
source = input_source(uploaded is not None, example_path is not None)
if source == "upload":
    data = uploaded.getvalue()
    filename = uploaded.name
elif source == "example":
    try:
        data = read_example_bytes(example_path)
        filename = example_path.name
    except AppError as exc:
        example_read_error = exc

current_sha = sha256_bytes(data) if data is not None else None
current_key = result_key(current_sha, settings_key)

# A result computed from different bytes, or under different inference-affecting
# settings, must never be shown for the current input.
if (
    session_state.displayed_view(current_key) is None
    and st.session_state.get("view_key") not in (None, current_key)
):
    session_state.purge_result()

has_result = (
    st.session_state.get("result") is not None
    and st.session_state.get("view_key") == current_key
)

preview_image = None
preview_info = None
preview_error: AppError | None = None

with col_preview:
    if example_read_error is not None:
        ui.show_error(example_read_error.message, example_read_error.detail)
    elif data is None:
        ui.placeholder()
    else:
        try:
            preview_image, preview_info = service.validate_image(data, filename)
        except AppError as exc:
            preview_error = exc
        if preview_image is None:
            ui.show_error(
                preview_error.message if preview_error else "The image could not be previewed.",
                preview_error.detail if preview_error else None,
            )
        elif has_result:
            # The image is shown in the Summary tab once a result exists; keep the
            # input column compact instead of duplicating it.
            size = (
                f"{preview_info.width}×{preview_info.height}"
                if preview_info and preview_info.width
                else "unknown size"
            )
            ui.muted(f"{filename or 'uploaded'} · {size} · preview shown in Summary")
        else:
            caption = filename or "uploaded"
            if preview_info is not None and preview_info.width and preview_info.height:
                caption = f"{caption} · {preview_info.width}×{preview_info.height}"
            st.image(preview_image, caption=caption, width="stretch")

with col_input:
    can_run = (
        data is not None
        and preview_error is None
        and release_ready
        and not require_verified
    )
    run = st.button("Run inference", type="primary", width="stretch", disabled=not can_run)
    new_image = st.button(
        "New image",
        width="stretch",
        disabled=current_sha is None and st.session_state.get("view_key") is None,
        help="Clears the result and the selected image.",
    )
    if manifest is not None and data is not None and not st.session_state.get("models_loaded"):
        st.caption("The first run loads the models and can take a while.")

if new_image:
    st.session_state["_pending_new_image"] = True
    st.rerun()

if run and can_run:
    with st.spinner("Running inference…"):
        try:
            result, view = service.infer_and_present(data, filename, labels=labels)
            if view["input"].get("byte_sha256") != current_sha:
                raise InferenceError("Result provenance does not match the selected image.")
            session_state.store_result(result=result, view=view, byte_sha=current_sha, key=current_key)
        except AppError as exc:
            session_state.store_error(exc.message, exc.detail)
        except Exception as exc:  # noqa: BLE001 - never crash the app
            session_state.store_error("Unexpected error while running inference.", str(exc))

error = st.session_state.get("error")
if error:
    ui.show_error(error.get("message", "Inference failed."), error.get("detail"))


# --------------------------------------------------------------------------- #
# Results (three levels: Summary / Evidence / Technical)
# --------------------------------------------------------------------------- #
view = session_state.displayed_view(current_key)
result = st.session_state.get("result") if view else None

if view:
    caption = filename or "uploaded"
    if preview_info is not None and preview_info.width and preview_info.height:
        caption = f"{caption} · {preview_info.width}×{preview_info.height}"

    summary_tab, evidence_tab, technical_tab = st.tabs(["Summary", "Evidence", "Technical"])
    with summary_tab:
        ui.render_summary(view, image=preview_image, image_caption=caption)
    with evidence_tab:
        ui.render_evidence(view)
    with technical_tab:
        ui.render_technical(view, result)


# --------------------------------------------------------------------------- #
# About (truthful product/release disclosure; no developer tooling narration)
# --------------------------------------------------------------------------- #
with st.expander("About", expanded=False):
    st.markdown("**CIRCL-E** — electronic-device identity and circular-economy evidence.")
    st.caption(
        "All inference runs locally on this machine. Images are not uploaded and no "
        "network call is made."
    )
    st.markdown(f"`Software version` {DASHBOARD_VERSION}")
    st.markdown(f"`Model release status` {MODEL_RELEASE_NOTE}")
    st.caption(
        "Outputs are decision-support evidence, not a certified verdict, a damage "
        "assessment or a hazard estimate."
    )
