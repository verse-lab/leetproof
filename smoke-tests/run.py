#!/usr/bin/env python3
"""Run a small, cost-capped LLoom artifact-evaluation workflow."""

from __future__ import annotations

import argparse
import os
import shlex
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Problem:
    title: str
    directory: str
    output_name: str

    @property
    def description(self) -> str:
        return f"llmgen/problems/{self.directory}/problem.md"

    @property
    def specification(self) -> str:
        return f"llmgen/problems/{self.directory}/Spec.lean"


PROBLEMS = {
    "single-number": Problem("Single Number", "136_single-number", "SingleNumber"),
    "contains-duplicate": Problem(
        "Contains Duplicate", "217_contains-duplicate", "ContainsDuplicate"
    ),
    "is-subsequence": Problem(
        "Is Subsequence", "392_is-subsequence", "IsSubsequence"
    ),
}

WORKFLOWS = {
    "spec": "synthesize a fresh Lean specification from problem.md",
    "velvet": "synthesize Velvet from a generated or bundled Spec.lean",
    "lean": "synthesize Lean from a generated or bundled Spec.lean",
}


def build_parser() -> argparse.ArgumentParser:
    problem_lines = "\n".join(
        f"  {name:<20} {problem.title} ({problem.directory})"
        for name, problem in PROBLEMS.items()
    )
    workflow_lines = "\n".join(
        f"  {name:<20} {description}" for name, description in WORKFLOWS.items()
    )
    parser = argparse.ArgumentParser(
        description="Run one LLoom artifact smoke test through Docker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Problems:
{problem_lines}

Workflows:
{workflow_lines}

Examples:
  ./smoke-tests/run.py --problem single-number --workflow spec
  ./smoke-tests/run.py --problem single-number --workflow velvet
  ./smoke-tests/run.py --problem single-number --workflow lean
  ./smoke-tests/run.py --problem contains-duplicate --workflow spec --dry-run
  ./smoke-tests/run.py --problem is-subsequence --workflow velvet -- --recursion-limit 50
""",
    )
    parser.add_argument("--problem", choices=PROBLEMS, help="bundled problem to run")
    parser.add_argument("--workflow", choices=WORKFLOWS, help="synthesis workflow")
    parser.add_argument(
        "--list-problems", action="store_true", help="list bundled problems and exit"
    )
    parser.add_argument(
        "--provider",
        choices=("openai", "anthropic"),
        default=os.environ.get("LLOOM_PROVIDER", "openai"),
        help="LLM provider (default: LLOOM_PROVIDER or openai)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLOOM_MODEL"),
        help="model ID (default: LLOOM_MODEL, or gpt-5.4 for OpenAI)",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        help="maximum cost in US dollars (default: 1 for spec, 5 otherwise)",
    )
    parser.add_argument(
        "--input-file",
        help="override the mapped input path, relative to llmgen-experiment",
    )
    parser.add_argument(
        "--output-file",
        help="override the generated output path, relative to llmgen-experiment",
    )
    parser.add_argument(
        "--session-name", help="override the generated session name for Lean synthesis"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the command without running it"
    )
    parser.add_argument(
        "lloom_args",
        nargs=argparse.REMAINDER,
        metavar="-- LLOOM_ARG ...",
        help="additional arguments forwarded to LLoom after a -- separator",
    )
    return parser


def default_paths(
    problem: Problem, workflow: str, project_root: Path
) -> tuple[str, str]:
    base = f"llmgen/SmokeTests/{problem.output_name}"
    if workflow == "spec":
        return problem.description, f"{base}/Spec.lean"
    generated_spec = f"{base}/Spec.lean"
    input_file = (
        generated_spec
        if (project_root / generated_spec).is_file()
        else problem.specification
    )
    if workflow == "velvet":
        return input_file, f"{base}/Impl.lean"
    return input_file, f"{base}/LeanImpl.lean"


def validate_relative_path(parser: argparse.ArgumentParser, value: str, flag: str) -> None:
    path = Path(value)
    if path.is_absolute():
        parser.error(f"{flag} must be relative to llmgen-experiment: {value}")
    if path.parts and path.parts[0] == "llmgen-experiment":
        parser.error(f"{flag} must not start with 'llmgen-experiment/': {value}")
    if ".." in path.parts:
        parser.error(f"{flag} must stay inside llmgen-experiment: {value}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_problems:
        for name, problem in PROBLEMS.items():
            print(f"{name}\t{problem.title}\t{problem.directory}")
        return

    if not args.problem:
        parser.error("--problem is required unless --list-problems is used")
    if not args.workflow:
        parser.error("--workflow is required unless --list-problems is used")

    model = args.model
    if model is None and args.provider == "openai":
        model = "gpt-5.4"
    if not model:
        parser.error("--model or LLOOM_MODEL is required for Anthropic")
    max_cost = args.max_cost
    if max_cost is None:
        max_cost = 1.0 if args.workflow == "spec" else 5.0
    if max_cost <= 0:
        parser.error("--max-cost must be greater than zero")

    artifact_root = Path(__file__).resolve().parent.parent
    project_root = artifact_root / "llmgen-experiment"
    problem = PROBLEMS[args.problem]
    mapped_input, mapped_output = default_paths(
        problem, args.workflow, project_root
    )
    input_file = args.input_file or mapped_input
    output_file = args.output_file or mapped_output
    validate_relative_path(parser, input_file, "--input-file")
    validate_relative_path(parser, output_file, "--output-file")

    input_on_host = project_root / input_file
    if not input_on_host.is_file():
        parser.error(f"input file does not exist: {input_on_host}")
    if not args.dry_run:
        (project_root / output_file).parent.mkdir(parents=True, exist_ok=True)

    wrapper = artifact_root / "leetproof.sh"
    common = [
        "--input-file",
        input_file,
        "--output-file",
        output_file,
        "--provider",
        args.provider,
        "--model",
        model,
        "--max-cost",
        f"{max_cost:g}",
    ]

    if args.workflow == "spec":
        command = [str(wrapper), "pipeline", *common, "--end", "specgen"]
    elif args.workflow == "velvet":
        command = [str(wrapper), "pipeline", *common, "--start", "codegen"]
    else:
        session_name = args.session_name or (
            f"artifact-lean-{args.problem}-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
        )
        command = [
            str(wrapper),
            "lean-synth",
            *common,
            "--session-name",
            session_name,
        ]

    forwarded = args.lloom_args
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    command.extend(forwarded)

    if args.dry_run:
        print(shlex.join(command))
        return

    spec_source = None
    if args.workflow in ("velvet", "lean"):
        generated_spec = f"llmgen/SmokeTests/{problem.output_name}/Spec.lean"
        spec_source = "generated" if input_file == generated_spec else "bundled/custom"

    print("LLoom smoke-test configuration", flush=True)
    print(f"  Problem:   {args.problem} ({problem.title})", flush=True)
    print(f"  Workflow:  {args.workflow}", flush=True)
    print(f"  Provider:  {args.provider}", flush=True)
    print(f"  Model:     {model}", flush=True)
    print(f"  Max cost:  ${max_cost:g}", flush=True)
    print(f"  Input:     {input_file}", flush=True)
    if spec_source is not None:
        print(f"  Spec:      {spec_source}", flush=True)
    print(f"  Output:    {output_file}", flush=True)
    print("Starting LLoom...", flush=True)

    os.execv(str(wrapper), command)


if __name__ == "__main__":
    main()
