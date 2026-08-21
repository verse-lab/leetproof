#!/bin/sh
set -eu

artifact_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "${artifact_root}"

case "${1:-}" in
    arm64|arm|aarch64)
        architecture=arm64
        archives="leetproof-ase2026-artifact-arm64.tar.gz"
        ;;
    x86_64|x86|amd64)
        architecture=amd64
        archives="leetproof-ase2026-artifact-amd64.tar.gz"
        ;;
    *)
        echo "Usage: $0 <arm64|amd64>" >&2
        exit 2
        ;;
esac

for archive in ${archives}; do
    if [ -f "${archive}" ]; then
        echo "Loading the LeetProof ${architecture} image from ${archive} ..."
        gzip -dc "${archive}" | docker load
        exit 0
    fi
done

echo "No ${architecture} image archive was found; building it from source instead."
exec ./docker-build.sh "${architecture}"
