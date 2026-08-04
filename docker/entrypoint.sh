#!/bin/sh
set -eu

project_dir="${LLOOM_PROJECT_DIR:-/workspace/llmgen-experiment}"
image_project_dir="/opt/llmgen-experiment"

if [ ! -f "${project_dir}/lakefile.toml" ] && [ ! -f "${project_dir}/lakefile.lean" ]; then
    echo "error: ${project_dir} is not a Lean project" >&2
    echo "Mount the artifact's llmgen-experiment directory at ${project_dir}." >&2
    exit 2
fi

# Build products are deliberately omitted from the archive. Seed them from the
# exact project built into the image, avoiding a network download on first run.
if [ ! -d "${project_dir}/.lake/packages" ]; then
    echo "Initialising the Lean build cache in ${project_dir} ..."
    mkdir -p "${project_dir}/.lake"
    cp -R "${image_project_dir}/.lake/." "${project_dir}/.lake/"
fi

cd "${project_dir}"

if [ "$#" -eq 0 ]; then
    set -- --help
fi

# LLoom resolves relative inputs, outputs, logs, and sessions after changing to
# --project. Inject the mounted project so all those files persist on the host.
case "$1" in
    pipeline)
        shift
        set -- pipeline --project "${project_dir}" "$@"
        ;;
    -*)
        set -- --project "${project_dir}" "$@"
        ;;
esac

exec lloom-agent "$@"
