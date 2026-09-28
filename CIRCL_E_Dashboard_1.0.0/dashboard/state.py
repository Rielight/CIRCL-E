"""Session-state helpers for the dashboard state machine.

The UI moves through ``EMPTY -> READY -> RUNNING -> SUCCESS | ERROR``. A stored
result is bound to the exact input bytes *and* to the inference-affecting
settings that produced it; whenever either changes the stored result is purged
before anything is rendered. These helpers keep that logic in one place and
testable without a browser.

``streamlit`` is imported lazily so the pure helpers can be unit-tested directly.
"""
from __future__ import annotations

from typing import Any, MutableMapping

from circl_e_app import RESULT_STATE_KEYS

#: Widget keys owned by the input workspace. ``purge_result`` never touches them;
#: ``purge_input`` additionally resets the selected image.
UPLOAD_KEY = "image_upload"
EXAMPLE_KEY = "example_choice"


def _session(session: MutableMapping[str, Any] | None) -> MutableMapping[str, Any]:
    if session is not None:
        return session
    import streamlit as st

    return st.session_state


def purge_result(session: MutableMapping[str, Any] | None = None) -> None:
    """Drop the displayed result (never the selected image or settings)."""
    store = _session(session)
    for key in RESULT_STATE_KEYS:
        store.pop(key, None)


def purge_input(session: MutableMapping[str, Any] | None = None) -> None:
    """Drop the result *and* the selected image (used by "New image")."""
    store = _session(session)
    purge_result(store)
    store.pop(UPLOAD_KEY, None)
    store.pop(EXAMPLE_KEY, None)


def store_result(
    *,
    result: Any,
    view: dict[str, Any],
    byte_sha: str,
    key: str | None,
    session: MutableMapping[str, Any] | None = None,
) -> None:
    """Persist a successful result together with its staleness key."""
    store = _session(session)
    store.update({
        "result": result,
        "view": view,
        "view_sha": byte_sha,
        "view_key": key,
        "models_loaded": True,
    })
    store.pop("error", None)


def store_error(
    message: str,
    detail: str | None,
    *,
    session: MutableMapping[str, Any] | None = None,
) -> None:
    """Persist a clean error and drop any stale successful result."""
    store = _session(session)
    purge_result(store)
    store["error"] = {"message": message, "detail": detail}


def displayed_view(
    current_key: str | None,
    *,
    session: MutableMapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the stored view only when it matches the current input/settings."""
    store = _session(session)
    view = store.get("view")
    if view and store.get("view_key") == current_key:
        return view
    return None
