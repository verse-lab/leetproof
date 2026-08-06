# Verina/Clever specification-PBT artifact

This directory provides the reproducible workflow for the specification bugs
reported in `llmgen-experiment/verina_feedback.pdf` and
`llmgen-experiment/clever_feedback.pdf`. It uses the historical benchmark
revisions cited in those reports, rather than current branches where some
specifications may already have been fixed.

| Benchmark | Pinned revision |
|---|---|
| Verina | `643ed3cab89f37a243720640206de3b178730534` |
| Clever v1.4.0 | `603e318da2a633cf3aea3a6b2c43cc3fd0187fb7` |

## Prepare the pinned inputs

Build the image once, then convert both pinned benchmarks:

```sh
docker compose build leetproof
./specpbt.sh convert
```

The Docker build checks out Verina in a cached image layer and installs Clever
directly from the pinned Git revision through the LeetProof uv lockfile. Thus
Clever keeps its standard `Benchmark()` package-data loader. `convert` verifies
the Verina checkout before generating 189 Verina and 161 Clever PBT-ready Lean files beneath
`llmgen-experiment/llmgen/ArtifactSpecs/`.

Clever's historical helper definitions are adapted under the separate
`llmgen.ArtifactSupport` namespace. Existing files under `Extensions/` and the
submitted results under `SpecPBTResult/` are not overwritten.

## Smoke test

The smoke test covers both supported bug modes: underspecified Verina
`verina_advanced_8` and Clever `7` specifications, plus Clever `9`, where PBT
executes the supplied implementation and finds an output that violates its
postcondition.

```sh
./specpbt.sh run smoke
```

Generated Lean verification modules are written beneath
`llmgen-experiment/llmgen/ArtifactVerification/smoke/`. The machine-readable
report is written to `specpbt-data/results/smoke.json`. Both locations are
bind-mounted, so the results remain on the host after the container exits.

## Full feedback-case test

This checks every issue in the feedback reports: 16 Verina cases and 18 Clever
cases. It records the exact checker status for underspecified, incorrect, and
unsatisfiable specifications. For each non-stub implementation, it also tests
whether the implementation output satisfies the postcondition.

```sh
./specpbt.sh run full
```

The report is `specpbt-data/results/full.json`.

## Full benchmark scan

To scan all 189 Verina and 161 Clever specifications:

```sh
./specpbt.sh run all
```

This can take roughly one day as a serial run, depending on hardware and Lean
cache state. The report is `specpbt-data/results/all.json`.

## Local execution

Docker is the recommended artifact-evaluation path. With the local LeetProof
environment and Lean project already prepared, the equivalent commands are:

```sh
uv run --project leetproof python specpbt/workflow.py download
uv run --project leetproof python specpbt/workflow.py convert
uv run --project leetproof python specpbt/workflow.py run smoke
```

The explicit `download` step prepares Verina under the Lean project's existing
`.lloom/benchmarks/verina` location for local execution. The pinned Clever
package is installed by `uv`, and Docker already contains both.

All commands accept `--data-dir PATH` and `--lean-project PATH` before the
subcommand when a non-default layout is needed.
