# Smoke-test outputs

Generated smoke-test files use one directory per problem. The canonical
filenames identify the synthesis output:

```text
llmgen/SmokeTests/<Problem>/Spec.lean
llmgen/SmokeTests/<Problem>/Impl.lean
llmgen/SmokeTests/<Problem>/LeanImpl.lean
```

The top-level Docker wrapper writes these relative paths into the host's
`llmgen-experiment/` directory, so the files remain after the container exits.
Specification synthesis is capped at one US dollar by default; Velvet and
Lean synthesis are capped at five US dollars by default. The launcher prints
the resolved configuration before starting LLoom.
