# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ARG LLOOM_UID=1000
ARG LLOOM_GID=1000
ARG LEAN_TOOLCHAIN=leanprover/lean4:v4.24.0

ENV DEBIAN_FRONTEND=noninteractive \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/leetproof/.venv/bin:/opt/elan/bin:${PATH} \
    ELAN_HOME=/opt/elan \
    LLOOM_PROJECT_DIR=/workspace/llmgen-experiment

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        libgmp-dev \
        libssl-dev \
        pkg-config \
        unzip \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf \
        https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
        | sh -s -- -y --default-toolchain "${LEAN_TOOLCHAIN}"

WORKDIR /opt/leetproof

# Cache the expensive Python dependency layer independently from source edits.
COPY leetproof/pyproject.toml leetproof/uv.lock leetproof/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY leetproof/ /opt/leetproof/
RUN uv sync --frozen --no-dev

# Bake an exact, built copy of the artifact Lean project into the image. The
# reviewer-facing project is bind-mounted at runtime; the entrypoint seeds its
# ignored .lake directory from this copy on first use.
COPY llmgen-experiment/ /opt/llmgen-experiment/
WORKDIR /opt/llmgen-experiment
RUN lake exe cache get \
    && lake build

COPY docker/entrypoint.sh /usr/local/bin/lloom-entrypoint
RUN chmod 0755 /usr/local/bin/lloom-entrypoint \
    && groupadd --gid "${LLOOM_GID}" lloom \
    && useradd --uid "${LLOOM_UID}" --gid "${LLOOM_GID}" \
        --create-home --shell /bin/bash lloom \
    && mkdir -p /workspace/llmgen-experiment \
    && chown -R lloom:lloom /workspace /home/lloom

ENV HOME=/home/lloom
USER lloom
WORKDIR /workspace/llmgen-experiment

ENTRYPOINT ["lloom-entrypoint"]
CMD ["--help"]
