#!/bin/sh
set -eu

specpbt_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "${specpbt_root}"

exec docker compose run --rm leetproof specpbt "$@"
