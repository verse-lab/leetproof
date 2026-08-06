# Docker workflow for artifact evaluation

The image contains the pinned LeetProof Python environment, Lean 4.24.0, a built
copy of the artifact's Lean project, and the semantic-search assets used by
LeetProof (LeanExplore and the BGE embedding model). Docker Compose bind-mounts
the host `llmgen-experiment/` directory at `/workspace/llmgen-experiment`.

This means generated Lean files, result JSON, logs, and resumable `.lloom`
sessions remain in the artifact directory after a container exits.

## Requirements

- Docker Engine or Docker Desktop with Compose v2
- About 30 GB of free disk space for the image and build cache
- Internet access while building the image
- An API key for any command that invokes an LLM

## Build and no-key validation

From the artifact root:

```bash
docker compose build leetproof
docker compose run --rm --entrypoint sh leetproof -c 'lean --version && lake build'
docker compose run --rm leetproof search --info
docker compose run --rm leetproof search "commutativity of addition" --limit 3 --no-verify
```

On Linux, build with your host UID and GID if they are not 1000, so generated
files remain editable outside Docker:

```bash
LLOOM_UID="$(id -u)" LLOOM_GID="$(id -g)" docker compose build leetproof
```

## Cached heavyweight build layers

The Docker build performs all time-consuming setup ahead of time:

- Python dependencies are cached from `leetproof/uv.lock`.
- LeanExplore data and the BGE embedding model are downloaded into a dedicated
  image layer keyed by the Python dependency files and `leetproof/cli.py`.
- Lean/Mathlib packages and their binary cache are downloaded in a layer keyed
  only by `lean-toolchain`, `lakefile.toml`, and `lake-manifest.json`.
- The artifact's Lean sources are copied and built only after those dependency
  layers.

LeetProof/search setup and the Lean project are independent multi-stage build
branches. Changes to Python source therefore do not invalidate the Mathlib
download, and changes to Lean source do not invalidate the LeanExplore/model
download. Docker may build the two branches concurrently.

Consequently, normal edits to LeetProof or Lean source files do not repeat the
large downloads. Changing a lockfile or manifest intentionally invalidates the
corresponding layer. A clean first build downloads roughly 8.5 GB of search
assets in addition to the Lean dependencies, so it can take a while; subsequent
builds reuse Docker's layer cache.

The resulting image is self-contained for Lean builds and semantic search; no
runtime `lloom-agent setup` step or persistent home volume is required. You can
verify this without invoking an LLM:

```bash
docker compose run --rm leetproof search --info
docker compose run --rm leetproof search "commutativity of addition" --limit 3 --no-verify
```

## Run the pipeline and persist its output

Export a provider key in the host shell; Compose forwards it without putting it
in the image:

```bash
export OPENAI_API_KEY="..."
```

Then run from the artifact root:

```bash
docker compose run --rm leetproof pipeline \
  --input-file sliding_window_maximum.txt \
  --output-file llmgen/SmokeTests/SlidingWindowMaximum/Spec.lean \
  --end specgen \
  --provider openai \
  --model YOUR_MODEL \
  --max-cost 5
```

The output is written on the host at:

```text
llmgen-experiment/llmgen/SmokeTests/SlidingWindowMaximum/Spec.lean
```

Input and output paths are relative to `llmgen-experiment/`. Do not prefix a
relative path with `llmgen-experiment/`, since that would create a nested path.

For three ready-to-run, cost-capped agent examples, see
[`smoke-tests/`](smoke-tests/README.md).

## Persistence summary

| Data | Location | Persistence |
|---|---|---|
| Generated specifications and programs | `llmgen-experiment/llmgen/` | Host bind mount |
| Sessions, DBOS database, and logs | `llmgen-experiment/.lloom/` | Host bind mount |
| Lean build products | `llmgen-experiment/.lake/` | Host bind mount, seeded from image |
| LeanExplore and embedding-model caches | `/home/lloom` | Image layers |
| Model pricing | `leetproof/config/model_pricing.json` | Read-only host bind mount; no rebuild needed |
| API keys | Process environment | Not stored by this setup |
