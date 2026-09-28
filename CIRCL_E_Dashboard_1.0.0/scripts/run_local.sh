#!/usr/bin/env bash
# Launch the CIRCL-E dashboard locally (no Docker, no API key).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export CIRCL_RELEASE_DIR="${CIRCL_RELEASE_DIR:-$ROOT/runtime/release}"
export CIRCL_ALLOW_UNVERIFIED="${CIRCL_ALLOW_UNVERIFIED:-1}"

echo "CIRCL-E Dashboard 1.0.0"
echo "  release : $CIRCL_RELEASE_DIR"
echo "  dino    : ${CIRCL_DINO_DIR:-<unset>}"
echo "  cradio  : ${CIRCL_CRADIO_DIR:-<unset>}"
echo

# Fail fast with an actionable message before Streamlit loads multi-GB weights.
if ! python "$ROOT/scripts/verify_runtime.py"; then
    echo "Runtime verification failed. Fix the issues above, then retry." >&2
    exit 1
fi

exec streamlit run "$ROOT/dashboard/app.py" "$@"
