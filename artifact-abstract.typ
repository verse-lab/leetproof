#set page(margin: (x: 1.7cm, y: 1.5cm))
#set text(size: 9.5pt)
#set par(justify: true, leading: 0.55em)
#show heading.where(level: 1): set text(size: 15pt, weight: "bold")
#show heading.where(level: 2): set text(size: 10.5pt, weight: "bold")
#show raw: set text(size: 8.5pt)

= Artifact Abstract

== Paper title

_Certified Program Synthesis with a Multi-modal Verifier_

== Link to the accepted paper. The paper should be made available so the reviewers can access it.

The accepted paper is available as a reviewer-accessible PDF at
#link("https://verse-lab.org/papers/leetproof-ase26.pdf")[verse-lab.org/papers/leetproof-ase26.pdf].
The paper's ASE 2026 program page is
#link("https://conf.researchr.org/details/ase-2026/ase-2026-research-track/263/Certified-Program-Synthesis-with-a-Multi-modal-Verifier")[available here].

== Purpose: a brief description of what the artifact does.

This artifact contains LeetProof, the implementation and evaluation materials
for a multi-agent pipeline that synthesizes formally verified programs from
natural-language programming problems. It supports specification generation,
imperative program and proof generation through Velvet, and functional Lean
program and proof generation. The package includes the prompts and agent code,
a 50-problem benchmark, generated implementations and proofs, experiment
outcomes used in the paper, and a deterministic property-based-testing (PBT)
workflow for checking specifications from the pinned Verina and Clever
benchmarks. It provides small smoke tests as well as instructions for inspecting
the submitted results and running larger experiments.

== Badge: A list of badge(s) the authors are applying for, as well as the reasons why the authors believe that the artifact deserves that badge(s).

- *Artifacts Available.* The source, data, results, documentation, and packaged
  Docker image are publicly distributed under the Apache-2.0 license. The
  archival Zenodo record supplied with the ASE submission gives the evaluated
  snapshot a persistent DOI; the public source repository provides ongoing
  access and development history.
- *Artifacts Reusable* (and therefore *Artifacts Functional*). The submitted
  Docker image captures the Python, Lean 4.24.0, Mathlib, semantic-search, and
  benchmark dependencies. The artifact is documented and structured into tool,
  benchmark, results, and smoke-test components. Reviewers can validate the
  installation without an LLM key, exercise each of the three synthesis
  workflows on bundled or custom inputs, reproduce the specification-PBT
  checks, and inspect machine-readable and proof-level evidence. These features
  support both verification of the paper's claims and reuse on new programs.

== Technology skills assumed by the reviewer evaluating the artifact and hardware requirements.

Reviewers need only basic command-line and Docker familiarity; knowledge of
Python, Lean, or Velvet is useful for inspecting or extending the implementation
but is not required for the guided tests. The recommended route requires a
64-bit machine capable of running Linux containers (ARM64 or x86_64/AMD64), Docker Engine or Docker
Desktop with Compose, and approximately 60 GB of free disk space. Internet
access is needed when building rather than loading the supplied image and when
calling an LLM. No GPU or unusual peripheral is required. Synthesis tests require
an OpenAI or Anthropic account, API key, network access, and incur provider
charges; the deterministic specification-PBT test requires none of these.

== Provenance: where the artifact can be obtained.

The immutable evaluation snapshot and its DOI are provided by the Zenodo record
linked in the ASE submission. The evaluated package includes prebuilt Docker image
archives for both ARM64 (`leetproof-ase2026-artifact-arm64.tar.gz`) and AMD64
(`leetproof-ase2026-artifact-amd64.tar.gz`), alongside the source tree. The repository records the exact Lean
toolchain and dependency revisions in `lean-toolchain`, `lake-manifest.json`,
and `uv.lock`.

== Instructions

*Tools.* Use a POSIX shell plus Docker with Compose (or anything docker compatible 
like podman, orbstack, etc.). Linux, macOS, and Windows hosts may be used as long as 
they can run Linux containers. No GPU is needed. The prebuilt image is recommended 
because loading it takes approximately 10--15 minutes and avoids a lengthy dependency 
build. From the unpacked artifact root:

```sh
# On ARM64 (e.g. Apple Silicon, ARM Linux):
gzip -dc leetproof-ase2026-artifact-arm64.tar.gz | docker load

# On AMD64 / x86_64 (e.g. Intel/AMD Linux):
gzip -dc leetproof-ase2026-artifact-amd64.tar.gz | docker load

# Validation without an API key:
docker compose run --rm --entrypoint sh leetproof \
  -c 'cd /opt/llmgen-experiment && lean --version && lake build'
docker compose run --rm leetproof search --info
```

These commands validate the supplied environment without an API key. Detailed
expected behavior, troubleshooting, local installation, and full reproduction
instructions are in `README.md`.

*Quick executable tests.* For the deterministic specification test, run:

```sh
./specpbt.sh convert
./specpbt.sh run smoke
```

For an agent smoke test, first export `OPENAI_API_KEY` (or select Anthropic with
the documented flags), then run one workflow, for example:

```sh
export OPENAI_API_KEY="..."
./smoke-tests/run.py --problem single-number --workflow spec
./smoke-tests/run.py --problem single-number --workflow velvet
./smoke-tests/run.py --problem single-number --workflow lean
```

The `spec`, `velvet`, and `lean` workflows respectively test specification
generation, imperative synthesis with proof, and functional Lean synthesis with
proof. Agent runs are nondeterministic, normally take up to about 30 minutes
each, and have documented cost caps. Full pipeline reruns can take days and
substantial LLM expenditure; they are not required for the getting-started
check. The included results allow those claims to be evaluated without rerunning
every LLM call.

*Additional Information.* `llmgen-experiment/llmgen/problems/` contains one
directory per programming problem; each directory contains the natural-language
problem statement (`problem.md`) and the Lean specification (`Spec.lean`)
generated by our pipeline from that statement. `problems/REPORT.md` defines the
fixed 50-problem split (15 development and 35 evaluation problems). The generated
programs and proof artifacts are stored separately by model under
`llmgen-experiment/llmgen/gpt_result/` and
`llmgen-experiment/llmgen/opus_result/`. Within each problem directory, files
such as `Impl.lean`, `LeanImpl.lean`, `ImplAristotleProof.lean`, and
`LeanImplAristotleProof.lean` record the imperative or functional outputs and
their proof artifacts when produced. `gpt-stats.json` maps each problem identifier to fields
such as specification type-check status, generated-code type-check status,
invariant quality, proof status, and Velvet end-to-end verdict for GPT 5.2 experiments 
from the paper. `opus-stats.json` provides the corresponding summary for the
Claude Opus 4.6 experiments. The Verina and
Clever specification-PBT workflow uses pinned upstream revisions, converts each
case to a Lean module under `llmgen/ArtifactSpecs/`, writes verification modules
under `llmgen/ArtifactVerification/`, and emits JSON reports under
`specpbt-data/results/`. These data support inspecting individual derivations,
recomputing paper summaries, checking reported specification defects, and using
LeetProof or the PBT checker on new inputs. All text, Lean, JSON, and PDF evidence
uses standard formats and requires no proprietary viewer.
