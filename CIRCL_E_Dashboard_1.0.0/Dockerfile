# CIRCL-E Dashboard 1.0.0 — GPU-capable local inference image.
#
# The large frozen backbone checkpoints are NOT baked into this image. They are
# mounted read-only at /models/dino and /models/cradio (see docker-compose.yml).
# Only the fitted/static release assets under runtime/release are included.
#
# The CUDA/PyTorch stack is pinned to the validated environment (torch 2.13.0,
# CUDA 13.0). If the tag below is unavailable on your mirror, use the official
# PyTorch runtime image that matches the same torch/CUDA pair.
FROM nvidia/cuda:13.0.0-cudnn9-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pinned runtime dependencies first so the layer caches across code edits.
COPY requirements.lock /app/requirements.lock
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /app/requirements.lock

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    CIRCL_RELEASE_DIR=/app/runtime/release \
    CIRCL_DINO_DIR=/models/dino \
    CIRCL_CRADIO_DIR=/models/cradio \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

# Application code.
COPY dashboard /app/dashboard
COPY src /app/src
COPY runtime/release /app/runtime/release
COPY scripts /app/scripts
COPY .streamlit /app/.streamlit
COPY VERSION RELEASE_MANIFEST.json /app/

# Non-root runtime user.
RUN useradd --create-home --uid 10001 circl \
    && chown -R circl:circl /app
USER circl

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD curl --fail --silent http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
