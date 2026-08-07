## LeetProof

This directory contains two subdirectories.

- **leetproof** : This has the code for the tool.
- **llmgen-experiment**: This contains some extensions to Loom itself and the
  experiment results. See the final section for the results.

### llmgen-experiment

This directory contains some extensions to Loom itself
(`llmgen-experiment/Extensions/`) and the artefacts used to produce the paper's
results. See the final section for the complete run results.

### Running LeetProof

#### Using Provided Docker Tar

In order to load the provided `leetproof-ase2026-artifact.tar.gz`, please run the following command.

``` bash
gzip -dc leetproof-ase2026-artifact.tar.gz | docker load
```

This should take roughly 10-15 minutes since the tar file is quite big. 

Once you are done with this, you can directly move to the `"Smoke tests"` and
`"Reproducing the specification-PBT results"` section.

**NOTE**: In case you face any issues, you may try building the docker image
yourself following the instructions from section just below.

#### Docker setup

The recommended artifact-evaluation workflow uses Docker. It requires Docker
Engine or Docker Desktop with Compose v2, internet access for the initial
build, and approximately 30 GB of free space for the image and build cache.

From the repository root, build the complete environment with:

```bash
docker compose build leetproof
```

The image includes the LeetProof Python environment, Lean and Mathlib, the
built Lean project, semantic-search data, embedding model, and pinned Spec-PBT
benchmark inputs. No separate container setup command is required. Subsequent
builds reuse Docker's cached layers.

On Linux, pass your host UID and GID so generated files remain editable:

```bash
LEETPROOF_UID="$(id -u)" LEETPROOF_GID="$(id -g)" \
  docker compose build leetproof
```

Validate the image without an API key:

```bash
docker compose run --rm --entrypoint sh leetproof -c 'lean --version && lake build'
docker compose run --rm leetproof search --info
```

The host `llmgen-experiment/` directory is mounted inside the container. Specs,
implementations, proofs, logs, and sessions generated there remain available
on the host after the container exits or is removed. API keys are passed only
through the container environment and are not stored in the image.

#### Smoke tests

The repository includes cost-capped agent smoke tests for specification
generation, Velvet implementation generation, and standalone Lean synthesis.
After building the Docker image and exporting a provider key, run them from the
repository root:

```bash
export OPENAI_API_KEY="..."

./smoke-tests/run.py --problem single-number --workflow spec
./smoke-tests/run.py --problem single-number --workflow velvet
./smoke-tests/run.py --problem single-number --workflow lean
```

Bundled problems are `single-number`, `contains-duplicate`, and
`is-subsequence`. Generated `Spec.lean`, `Impl.lean`, and `LeanImpl.lean` files
are written under `llmgen-experiment/llmgen/SmokeTests/` on the host and remain
available after the container exits. See [smoke-tests/README.md](smoke-tests/README.md)
for costs, custom programs, dry runs, and all options.

**NOTE**: The default model is `gpt-5.2` (the one used for experiments in the
paper), but currently newer and more advanced GPT (and Claude) models are also
available. You may pass in `--provider <openai|anthropic> --model <model-name>`
flag to override the default one.

#### Reproducing the specification-PBT results

The pinned Verina/Clever workflow from the LeetProof repository is included in
this package. It downloads the exact historical benchmark revisions cited in
the feedback reports, converts their specifications, and supports a three-case
smoke test, the complete feedback-case set, or the full benchmark scan:

```bash
./specpbt.sh convert
./specpbt.sh run smoke
```

Generated Lean modules appear under
`llmgen-experiment/llmgen/ArtifactVerification/`, and JSON reports appear under
`specpbt-data/results/`; both remain available on the host after Docker exits.
This workflow does not invoke an LLM or require an API key. See
[specpbt/README.md](specpbt/README.md) for the pinned revisions, full runs,
and local execution.

#### Local setup (without Docker)

Run the setup script from the repository root:

```bash
bash setup.sh
```

This bootstraps the Python environment in `leetproof/`, builds the Lean project in `llmgen-experiment/`, and downloads the search/model assets used by the tool. No submodule initialization is required.

#### Prerequisites
Before running the tool, make sure the following are available:

- `git`
- `curl`
- Python `3.13+`
- [`uv`](https://github.com/astral-sh/uv) for Python dependency management
- [`elan`](https://github.com/leanprover/elan) for managing the Lean toolchain

The bootstrap script at `setup.sh` installs or configures the expected Lean toolchain (`v4.24.0`), Python dependencies, and the Lean project assets used by LeetProof.

You will also need at least one LLM provider API key before running the pipeline:

```bash
export ANTHROPIC_API_KEY="your-key"
# or
export OPENAI_API_KEY="your-key"
```

#### Commands
From `llmgen-experiment/`, run commands with `./leetproof.sh`:

Keep generated files under `llmgen/`. This directory is already wired into the Lean project; writing specs or outputs outside `llmgen/` can cause import/build failures.

Pipeline usage from a natural-language problem statement:

```bash
bash ./leetproof.sh pipeline \
  --project . \
  --input-file sliding_window_maximum.txt \
  --output-file llmgen/SlidingWindowMaximum.lean \
  --provider <provider> \
  --model <model>
```

Generate only the specification first:

```bash
bash ./leetproof.sh pipeline \
  --project . \
  --end specgen \
  --input-file sliding_window_maximum.txt \
  --output-file llmgen/SlidingWindowMaximumSpec.lean \
  --provider <provider> \
  --model <model>
```

Later, continue from that generated specification:

```bash
bash ./leetproof.sh pipeline \
  --project . \
  --start codegen \
  --input-file llmgen/SlidingWindowMaximumSpec.lean \
  --output-file llmgen/SlidingWindowMaximum.lean \
  --provider <provider> \
  --model <model>
```

Standalone Lean synthesis and verification from an existing specification:

```bash
bash ./leetproof.sh lean-synth \
  --project . \
  --input-file llmgen/SlidingWindowMaximumSpec.lean \
  --output-file llmgen/SlidingWindowMaximumLeanImpl.lean \
  --session-name <session-name> \
  --provider <provider> \
  --model <model>
```

#### Cost limits and supported pricing

Append `--max-cost 5` to stop a run when its tracked provider cost reaches five
US dollars. Cost limits work only when the selected model matches an entry in
`leetproof/config/model_pricing.json` (dated model IDs are matched by prefix).

Pricing is configured for these model families:

- OpenAI: `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`,
  `gpt-5.4`, `gpt-5.2`, and `gpt-5.1`.
- Anthropic: `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`,
  `claude-opus-4-6`, `claude-opus-4-5`, `claude-sonnet-5`,
  `claude-sonnet-4-6`, `claude-sonnet-4-5`, and `claude-haiku-4-5`.

For any other model, token usage can still be reported, but `--max-cost` cannot
reliably calculate or enforce a dollar limit until its pricing is added.

## Paper Figures and Non-executable Data

This section includes non-executable materials, including Loom extensions and run
results.

### 1. SpecPBT results (`Table 1`)

The data for **Table 1: Specification issues discovered in published benchmark
sets for vericoding in Lean** is produced by SpecPBT checks on the Verina and
Clever benchmark suites, documenting under-specified specification findings.

Evidence and outputs:
`llmgen-experiment/verina_feedback.pdf`, `llmgen-experiment/clever_feedback.pdf`,
`llmgen-experiment/SpecPBTResult/Verina`, and
`llmgen-experiment/SpecPBTResult/Clever`.

### 2. Aristotle differential testing (`RQ1`)

For `RQ1`, we ran differential testing with `Aristotle` between:

- our generated Verina specifications, and
- the reference specifications in the Verina benchmark.

The corresponding artifact directory is
`llmgen-experiment/VerinaSpecEquivCheck/`, which contains the equivalence check
results and proof artifacts produced by `Aristotle`.

### 3. Benchmark (Section 6.1)

The benchmark used in Section 6.1 is a 50-problem LeetCode subset:

The set contains 50 problems, with a fixed split documented in
`llmgen-experiment/llmgen/problems/REPORT.md` (**15 development, 35 evaluation**).

Supporting benchmark files:

- `llmgen-experiment/llmgen/problems/` and `llmgen-experiment/llmgen/problems/REPORT.md`.
- `llmgen-experiment/problems-stats.json` (evaluation outcomes for the 50-item set).

### 4. Sections 6.2--6.4 run results

Complete results for Sections 6.2 through 6.4 are collected in `llmgen-experiment/llmgen`:

- `llmgen-experiment/llmgen/gpt_result/`: `gpt-5.2` run outputs.
- `llmgen-experiment/llmgen/opus_result/`: `opus4.6` run outputs.

### Feedback reports

- [Verina feedback report](llmgen-experiment/verina_feedback.pdf)
- [CLEVER feedback report](llmgen-experiment/clever_feedback.pdf)
