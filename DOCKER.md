# Docker workflow for artifact evaluation

The image contains the pinned LLoom Python environment, Lean 4.24.0, and a
built copy of the artifact's Lean project. Docker Compose bind-mounts the host
`llmgen-experiment/` directory at `/workspace/llmgen-experiment`.

This means generated Lean files, result JSON, logs, and resumable `.lloom`
sessions remain in the artifact directory after a container exits.

## Requirements

- Docker Engine or Docker Desktop with Compose v2
- About 20 GB of free disk space for the image and build cache
- Internet access while building the image
- An API key for any command that invokes an LLM

## Build and no-key validation

From the artifact root:

```bash
docker compose build lloom
docker compose run --rm lloom pipeline --print-graph
docker compose run --rm --entrypoint sh lloom -c 'lean --version && lake build'
docker compose run --rm lloom search --info
```

The pipeline smoke test should print:

```text
Pipeline stages: specgen -> codegen -> invgen -> verify
```

On Linux, build with your host UID and GID if they are not 1000, so generated
files remain editable outside Docker:

```bash
LLOOM_UID="$(id -u)" LLOOM_GID="$(id -g)" docker compose build lloom
```

## One-time semantic-search setup

The full pipeline uses LeanExplore plus the BGE embedding model. Download these
assets once with:

```bash
docker compose run --rm lloom setup
```

LeanExplore writes to `/home/lloom/.lean_explore`, while Hugging Face writes the
model to `/home/lloom/.cache/huggingface`. Compose persists the entire
`/home/lloom` directory in the named `lloom-home` volume, so later disposable
containers reuse both downloads.

You can verify persistence without invoking an LLM:

```bash
docker compose run --rm lloom search --info
docker compose run --rm lloom search "commutativity of addition" --limit 3 --no-verify
```

The initial setup downloads roughly 8.5 GB. For an entirely offline artifact,
the final release should also provide an exported pre-populated volume or bake
these assets into a separate image layer.

## Run the pipeline and persist its output

Export a provider key in the host shell; Compose forwards it without putting it
in the image:

```bash
export OPENAI_API_KEY="..."
```

Then run from the artifact root:

```bash
docker compose run --rm lloom pipeline \
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
| LeanExplore and embedding-model caches | `/home/lloom` | Named Docker volume |
| Model pricing | `leetproof/config/model_pricing.json` | Read-only host bind mount; no rebuild needed |
| API keys | Process environment | Not stored by this setup |
