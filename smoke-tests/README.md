# Agent smoke tests

`run.py` provides three synthesis workflows over three bundled problems from
`llmgen/problems/`. Run `--help` to see every problem, workflow, option, and
example:

```bash
./smoke-tests/run.py --help
```

After building the image and completing the one-time setup, export a provider
key and select a problem and workflow:

```bash
export OPENAI_API_KEY="..."

./smoke-tests/run.py --problem single-number --workflow spec
./smoke-tests/run.py --problem single-number --workflow velvet
./smoke-tests/run.py --problem single-number --workflow lean
```

Available problems are `single-number`, `contains-duplicate`, and
`is-subsequence`. Every run defaults to OpenAI GPT-5.4. Specification
synthesis is capped at $1 by default; Velvet and Lean synthesis are capped at
$5. Outputs are written beneath:

```text
llmgen-experiment/llmgen/SmokeTests/
```

The `spec` workflow reads the selected `problem.md` and writes a fresh
`Spec.lean`. The `velvet` and `lean` workflows choose their input
in this order:

1. An explicit `--input-file`, when supplied.
2. The fresh `llmgen/SmokeTests/<Problem>/Spec.lean`, when it already exists.
3. The problem's bundled `llmgen/problems/<problem>/Spec.lean` as a fallback.

This makes `spec` followed by `velvet` or `lean` a natural chained workflow,
while keeping every synthesis workflow independently runnable.

## Output convention

Default outputs are relative to `llmgen-experiment/` and follow this layout:

```text
llmgen/SmokeTests/<Problem>/<File>
```

| Workflow | Primary file |
|---|---|
| `spec` | `Spec.lean` |
| `velvet` | `Impl.lean` |
| `lean` | `LeanImpl.lean` |

For example, Single Number produces:

```text
llmgen/SmokeTests/SingleNumber/Spec.lean
llmgen/SmokeTests/SingleNumber/Impl.lean
llmgen/SmokeTests/SingleNumber/LeanImpl.lean
```

These paths are inside the Docker bind mount, so the files appear directly in
the host artifact directory and survive container removal. A custom
`--output-file` must also be relative to `llmgen-experiment/`; the launcher
creates its parent directory before starting LLoom.

Use `--provider`, `--model`, `--max-cost`, `--input-file`, and `--output-file`
to override defaults. For example, `--max-cost 1` sets a one-dollar cap for
any workflow. Arguments after `--` are forwarded to LLoom:

```bash
./smoke-tests/run.py \
  --problem contains-duplicate \
  --workflow velvet \
  --provider anthropic \
  --model claude-sonnet-4-6

./smoke-tests/run.py \
  --problem is-subsequence \
  --workflow velvet \
  -- --recursion-limit 50
```

Inspect a resolved command without running an agent:

```bash
./smoke-tests/run.py --problem is-subsequence --workflow lean --dry-run
```
