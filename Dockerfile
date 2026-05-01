# syntax=docker/dockerfile:1.7
#
# evalkit — multi-stage build.
#
# Stage 1 (builder) compiles wheels into a venv. Stage 2 copies the venv
# into a minimal runtime image. The final image is ~150 MB and contains
# Python, the evalkit package + CLI, and all production deps.
#
# Build:   docker build -t evalkit .
# Run:     docker run --rm -v ${PWD}/runs:/app/runs evalkit
#
# See README "Running with Docker" for the docker compose flow.

# -----------------------------------------------------------------------------
# Builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps. We keep this layer cached as long as no system deps change.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create a venv that the runtime stage will pick up wholesale.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies first so layer caches when only source changes.
# We copy ONLY the project metadata, not the source, for this step.
COPY pyproject.toml ./
COPY README.md LICENSE ./

RUN pip install --upgrade pip wheel

# Touch a placeholder package so pip can resolve the project metadata
# without needing the real source yet. This caches the dep layer; iterative
# builds reinstall only the package itself when source changes.
RUN mkdir -p evalkit && touch evalkit/__init__.py
# Production deps + the `fast` (orjson) extra, plus a minimal slice of the
# dev extras needed to run `docker run evalkit tests` without a second image.
RUN pip install ".[fast]" pytest pytest-asyncio respx hypothesis \
    && pip uninstall -y evalkit

# Now copy real source and install the package itself (non-editable, so the
# venv is portable across stages without needing /build to exist).
COPY evalkit/ ./evalkit/
COPY scripts/ ./scripts/
RUN pip install --no-deps .

# -----------------------------------------------------------------------------
# Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    EVALKIT_IN_DOCKER=1

# Non-root user — never run an interactive image as root.
RUN groupadd --system --gid 1000 evalkit \
    && useradd  --system --uid 1000 --gid evalkit --create-home evalkit

# Pull the venv (with evalkit installed in editable mode) from the builder.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy the rest of the project so the editable install resolves and so
# examples / tests are runnable from inside the container.
COPY --chown=evalkit:evalkit pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY --chown=evalkit:evalkit evalkit/ ./evalkit/
COPY --chown=evalkit:evalkit scripts/ ./scripts/
COPY --chown=evalkit:evalkit tests/ ./tests/
COPY --chown=evalkit:evalkit examples/ ./examples/
COPY --chown=evalkit:evalkit docker-entrypoint.sh /usr/local/bin/docker-entrypoint
RUN chmod +x /usr/local/bin/docker-entrypoint

# /app/runs is the canonical artifact directory — mount a host volume here
# to retrieve reports and dashboards on the host.
RUN mkdir -p /app/runs && chown -R evalkit:evalkit /app

USER evalkit

ENTRYPOINT ["docker-entrypoint"]
CMD ["demo"]
