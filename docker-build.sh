#!/bin/sh
set -eu

artifact_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "${artifact_root}"

case "${1:-}" in
    arm64|arm|aarch64)
        dockerfile=Dockerfile.arm64
        architecture=ARM64
        ;;
    x86_64|x86|amd64)
        dockerfile=Dockerfile.amd64
        architecture=AMD64
        ;;
    *)
        echo "Usage: $0 <arm64|amd64>" >&2
        echo "  arm64  builds the ARM64 image from Dockerfile.arm64" >&2
        echo "  amd64 builds the AMD64 image from Dockerfile.amd64" >&2
        exit 2
        ;;
esac

echo "Building the LeetProof ${architecture} artifact image (${dockerfile}) ..."
export LEETPROOF_DOCKERFILE="${dockerfile}"

# Match generated-file ownership to the reviewer automatically. Explicit
# environment values still take precedence when a different mapping is needed.
: "${LEETPROOF_UID:=$(id -u)}"
: "${LEETPROOF_GID:=$(id -g)}"
export LEETPROOF_UID LEETPROOF_GID

exec docker compose build leetproof
