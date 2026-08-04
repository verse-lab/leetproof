#!/bin/sh
set -eu

artifact_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "${artifact_root}"

exec docker compose run --rm lloom "$@"
