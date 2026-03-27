## LeetProof

This directory contains two subdirectories.

- **leetproof** : This has the code for the tool.
- **llmgen-experiment**: This has the artefact of all the results submitted as part of the paper.

### Running LeetProof

#### Setup

#### Prerequisites
Before running the tool, make sure the following are available:

- `git`
- `curl`
- Python `3.13+`
- [`uv`](https://github.com/astral-sh/uv) for Python dependency management
- [`elan`](https://github.com/leanprover/elan) for managing the Lean toolchain

The bootstrap script at [`leetproof/setup.sh`](/Users/dipesh/github.com/verse-lab/artefact/leetproof/setup.sh) installs or configures the expected Lean toolchain (`v4.24.0`), Python dependencies, and the Lean project assets used by LeetProof.

Run:

```bash
cd leetproof
bash setup.sh
```

You will also need at least one LLM provider API key before running the pipeline:

```bash
export ANTHROPIC_API_KEY="your-key"
# or
export OPENAI_API_KEY="your-key"
```
