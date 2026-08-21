# LeetProof

This directory contains two subdirectories.

- **leetproof** : This has the code for the tool.
    - `./leetproof/prompts/` has all the prompts used for the agents.
    - `./leetproof/agents/` has the agent code for various agent we presented in the paper.
- **llmgen-experiment**: This contains some extensions to Loom itself and the
  experiment results. See the final section for the results.

## llmgen-experiment

This directory contains some extensions to Loom itself
(`llmgen-experiment/Extensions/`) and the artefacts used to produce the paper's
results. See the final section for the complete run results.

## Running LeetProof

### Load the Docker image

Use Docker Engine or Docker Desktop with Compose v2. From the repository root,
load the archive matching your machine:

```sh
# On ARM64 (for example, Apple Silicon or ARM Linux):
gzip -dc leetproof-ase2026-artifact-arm64.tar.gz | docker load

# On AMD64 (x86_64; for example, Intel or AMD Linux):
gzip -dc leetproof-ase2026-artifact-amd64.tar.gz | docker load
```

Docker-related operations may require root permission. If you get a
`permission denied` error, consider prefixing the Docker command with `sudo`.
For example:

```sh
gzip -dc leetproof-ase2026-artifact-amd64.tar.gz | sudo docker load
```

Both archives load the image tag
`leetproof-ase2026-artifact:latest`. All commands after this point are exactly
the same on ARM64 and AMD64. Loading an archive can take roughly 10--15
minutes.

If you need to build the Docker image locally from source instead:

```sh
./docker-build.sh arm64   # On ARM64 (e.g. Apple Silicon, ARM Linux)
./docker-build.sh amd64   # On AMD64 / x86_64 (e.g. Intel/AMD Linux)
```

#### Storage requirements

At least 60 GB of free disk space is recommended.

The image includes the LeetProof Python environment, Lean and Mathlib, the
built Lean project, semantic-search data, embedding model, and pinned Spec-PBT
benchmark inputs. No separate container setup command is required.

Validate the image without an API key:

```bash
# Build the project baked into the image, using its prebuilt Mathlib cache.
docker compose run --rm --entrypoint sh leetproof \
  -c 'cd /opt/llmgen-experiment && lean --version && lake build'

docker compose run --rm leetproof search --info
```

The `lake build` command deliberately uses `/opt/llmgen-experiment`, which is
the fully built project stored in the image. Do not run this validation from
the bind-mounted `/workspace/llmgen-experiment` before its cache has been
initialized, because that can trigger a fresh Mathlib build.

The host `llmgen-experiment/` directory is mounted inside the container. Specs,
implementations, proofs, logs, and sessions generated there remain available
on the host after the container exits or is removed. API keys are passed only
through the container environment and are not stored in the image.

#### Smoke tests

The repository includes cost-capped agent smoke tests for specification
generation, Velvet implementation generation, and standalone Lean synthesis.
After loading the Docker image and exporting a provider key, run them from the
repository root (one by one after completion):

```bash
export OPENAI_API_KEY="..."

./smoke-tests/run.py --problem single-number --workflow spec
./smoke-tests/run.py --problem single-number --workflow velvet
./smoke-tests/run.py --problem single-number --workflow lean
```

The `sudo` command removes most user environment variables. If Docker requires
root permission, explicitly pass the API key to the smoke-test command:

```bash
sudo env OPENAI_API_KEY="$OPENAI_API_KEY" \
  ./smoke-tests/run.py --problem single-number --workflow spec
```

Bundled problems for smoke tests are `single-number`, `contains-duplicate`, and
`is-subsequence`. The programs are choosen at random from from what we used for
our experiments for the paper. Generated `Spec.lean`, `Impl.lean`, and
`LeanImpl.lean` files are written under `llmgen-experiment/llmgen/SmokeTests/`
on the host and remain available after the container exits. You can verify 
whether they were proven fully or partially by checking the file: if it has 
sorry or some commented out error, then partially proven else it would be 
fully proven. In case of any other form of termination, you can see the error 
messages printed in the terminal.

See [smoke-tests/README.md](smoke-tests/README.md) for costs, **custom programs**, dry
runs, and all options.

It is important to understand that the time for each command to run may vary due
to the non-deterministic nature of agentic setups. Generally, it should take
less than half an hour. There are various factors that affect the time: LLM's
own reasoning time, the output produced may end up timing out Lean sometimes or
generating too many verification conditions for velvet, etc.


**NOTE**: The default model is `gpt-5.2` (the one used for experiments in the
paper), but currently newer and more advanced GPT (and Claude) models are also
available. You may pass in `--provider <openai|anthropic> --model <model-name>`
flag to override the default one. Using a newer model is recommended as they'll 
generally be faster and more intelligent.

#### Reproducing full results from paper

*It may take days for the entire pipeline to run for all the programs part of
our problem set and quite a lot of tokens(and money)*

You can use the custom flag from the smoke tests script and use appropriate
paths to run any problem from the problem set (which is at
`llmgen-experiment/llmgen/problems/` directory). However, due to the
non-deterministic nature of LLMs, reproducability of the results is not
guaranteed.

#### Reproducing the specification-PBT results

The pinned Verina/Clever workflow from the LeetProof repository is included in
this package. It downloads the exact historical benchmark revisions cited in
the feedback reports, converts their specifications, and supports a three-case
smoke test, the complete feedback-case set, or the full benchmark scan:

```bash
./specpbt.sh convert
./specpbt.sh run smoke
```

The smoke test is expected to print findings such as
`[SPECIFICATION BUG FOUND]`. This indicates that Spec-PBT found one of the
intended counterexamples; it is not a workflow failure.

Generated Lean modules appear under
`llmgen-experiment/llmgen/ArtifactVerification/`, and JSON reports appear under
`specpbt-data/results/`; both remain available on the host after Docker exits.
This workflow does not invoke an LLM or require an API key. See
[specpbt/README.md](specpbt/README.md) for the pinned revisions, full runs,
and local execution.



### Local setup (without Docker)

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

### Cost limits and supported pricing

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
- `gpt-stats.json` (evaluation outcomes for the 50-item set for GPT 5.2).
- `opus-stats.json` (evaluation outcomes for the 25-item set for Opus 4.6).

### 4. Sections 6.2--6.4 run results

Complete results for Sections 6.2 through 6.4 are collected in `llmgen-experiment/llmgen`:

- `llmgen-experiment/llmgen/gpt_result/`: `gpt-5.2` run outputs.
- `llmgen-experiment/llmgen/opus_result/`: `opus4.6` run outputs.

### Feedback reports

- [Verina feedback report](llmgen-experiment/verina_feedback.pdf)
- [CLEVER feedback report](llmgen-experiment/clever_feedback.pdf)
