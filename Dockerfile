# syntax=docker/dockerfile:1.7
#
# Folge Accessibility Pipeline -- Docker image
#
# Build:  docker build -t folge-cli .
# Run:    docker run --rm folge-cli --help
#
# ------------------------------------------------------------------------
# WHY THE IMAGE IS LAID OUT THIS WAY (read this before changing paths)
# ------------------------------------------------------------------------
# folge-cli resolves its own "project root" as the folder three levels
# above src/folge_cli/config.py (PROJECT_ROOT = Path(__file__).resolve()
# .parent.parent.parent). Several things depend on that:
#   - Pandoc's --css/--lua-filter arguments are built from that root, so
#     templates/, *.lua, and fonts/ (referenced by templates/folge.css)
#     have to actually live there on disk.
#   - `ensure_directories()` in pipeline.py unconditionally creates and
#     reads <PROJECT_ROOT>/images -- it is not configurable via a CLI
#     flag.
#   - The `folge-cli pipeline` subcommand shells back out to itself via
#     `uv run python -m folge_cli.<stage>` for each pipeline stage, so
#     `uv` has to be on PATH and runnable *inside the container at
#     runtime*, not just at image-build time.
#
# In other words: this only works correctly as an *editable* install
# (so __file__ points at real files, not somewhere inside
# site-packages) with the full source tree kept together at a stable
# path. That's exactly what `uv sync` gives you by default for a local
# project, so we lean on that rather than building/installing a wheel.
#
# Practical upshot for docker-compose.yml: mount your guide.json,
# images/, and output/ *into /app* (the same place the app itself
# lives), not into some separate /data directory -- see the compose
# file for the volume examples.
# ------------------------------------------------------------------------

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.11.7

# uv's own distroless image, used to grab the static binary for both stages.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ==========================================================================
# Stage 1: builder -- resolve/install Python deps + editable-install the
# project itself into /app/.venv
# ==========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# WeasyPrint's cffi bindings need Cairo/Pango/GDK-Pixbuf/libffi present;
# build-essential covers the rare wheel that isn't available prebuilt for
# this platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
        libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install locked third-party deps first, as their own layer -- this only
# invalidates when pyproject.toml / uv.lock actually change, so editing
# application code doesn't force a full dependency reinstall.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Now bring in the rest of the project (src/, templates/, fonts/, the
# lua filters, config.yaml, ...) and finish the editable install of
# folge-cli itself.
COPY . .
RUN uv sync --frozen

# ==========================================================================
# Stage 2: runtime -- slim image with only what's needed to actually run
# ==========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG PANDOC_VERSION=3.10.1

LABEL org.opencontainers.image.title="folge-cli" \
      org.opencontainers.image.description="Folge Vision accessibility publishing pipeline" \
      org.opencontainers.image.source="https://github.com/mrhunsaker/Folge_Accessibility"

# Runtime system deps:
#  - libcairo2/libpango*/libgdk-pixbuf*/libffi/shared-mime-info: WeasyPrint,
#    invoked by pandoc as an external --pdf-engine.
#  - poppler-utils: gives `folge-cli validate-pdf` access to `pdfinfo` for
#    extra tagged-PDF checks (optional but cheap to include).
#  - curl/xz-utils/ca-certificates: only needed transiently below to fetch
#    and unpack Pandoc's official release tarball; removed again after.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
        libffi-dev shared-mime-info \
        poppler-utils \
        curl xz-utils ca-certificates \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) PANDOC_ARCH=amd64 ;; \
         arm64) PANDOC_ARCH=arm64 ;; \
         *) echo "Unsupported architecture for pandoc: $ARCH" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /tmp/pandoc.tar.gz \
         "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${PANDOC_ARCH}.tar.gz" \
    && tar -xzf /tmp/pandoc.tar.gz -C /usr/local --strip-components=1 \
         "pandoc-${PANDOC_VERSION}/bin/pandoc" \
    && rm -f /tmp/pandoc.tar.gz \
    && apt-get purge -y --auto-remove curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

# `folge-cli pipeline` shells back out to `uv run python -m folge_cli.<stage>`
# for each of its own stages (see the note at the top of this file), so uv
# has to be present at runtime too, not just during the build.
COPY --from=uv /uv /uvx /usr/local/bin/

RUN groupadd --gid 1000 folge \
    && useradd --uid 1000 --gid folge --create-home --shell /bin/bash folge

WORKDIR /app
COPY --from=builder --chown=folge:folge /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_NO_SYNC=1 \
    UV_OFFLINE=1

# Pre-create the directories folge-cli expects at its install root so that
# bind-mounting into them (see docker-compose.yml) doesn't require the
# container to create them as root on first run.
RUN mkdir -p /app/images /app/output /app/schemas \
    && chown -R folge:folge /app/images /app/output /app/schemas

USER folge

# `docker run folge-cli pipeline guide.json output` now behaves exactly
# like `uv run folge-cli pipeline guide.json output` from source -- no
# "uv run" needed on the outside either.
ENTRYPOINT ["folge-cli"]
CMD ["--help"]
