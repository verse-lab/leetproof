#!/usr/bin/env python3
"""Run a small, cost-capped LLoom artifact-evaluation workflow."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Problem:
    title: str
    output_name: str
    description: str
    specification: str | None = None


PROBLEMS = {
    "single-number": Problem(
        "Single Number",
        "SingleNumber",
        "llmgen/problems/136_single-number/problem.md",
        "llmgen/problems/136_single-number/Spec.lean",
    ),
    "contains-duplicate": Problem(
        "Contains Duplicate",
        "ContainsDuplicate",
        "llmgen/problems/217_contains-duplicate/problem.md",
        "llmgen/problems/217_contains-duplicate/Spec.lean",
    ),
    "is-subsequence": Problem(
        "Is Subsequence",
        "IsSubsequence",
        "llmgen/problems/392_is-subsequence/problem.md",
        "llmgen/problems/392_is-subsequence/Spec.lean",
    ),
}

WORKFLOWS = {
    "spec": "synthesize a fresh Lean specification from problem.md",
    "velvet": "synthesize Velvet from a generated or bundled Spec.lean",
    "lean": "synthesize Lean from a generated or bundled Spec.lean",
}


def build_parser() -> argparse.ArgumentParser:
    problem_lines = "\n".join(
        f"  {name:<20} {problem.title} ({problem.description})"
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
  ./smoke-tests/run.py --custom-program pair-sum --custom-title "Pair Sum" \\
    --custom-description llmgen/custom/pair-sum/problem.md \\
    --custom-output-name PairSum --workflow lean
""",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--problem", choices=PROBLEMS, help="bundled problem to run")
    selection.add_argument(
        "--custom-program",
        metavar="SLUG",
        help="custom program identifier; requires the other --custom-* details",
    )
    parser.add_argument("--custom-title", help="display title for a custom program")
    parser.add_argument(
        "--custom-description",
        help="custom problem.md path, relative to llmgen-experiment",
    )
    parser.add_argument(
        "--custom-output-name",
        help="directory name beneath llmgen/SmokeTests for a custom program",
    )
    parser.add_argument("--workflow", choices=WORKFLOWS, help="synthesis workflow")
    parser.add_argument(
        "--list-problems", action="store_true", help="list bundled problems and exit"
    )
    parser.add_argument(
        "--provider",
        choices=("openai", "anthropic"),
        default=os.environ.get("LEETPROOF_PROVIDER", "openai"),
        help="LLM provider (default: LEETPROOF_PROVIDER or openai)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LEETPROOF_MODEL"),
        help="model ID (default: LEETPROOF_MODEL, or gpt-5.2 for OpenAI)",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        help="maximum cost in US dollars (default: 1 for spec, 5 otherwise)",
    )
    parser.add_argument(
        "--spec-max-cost",
        type=float,
        default=1.0,
        help="custom program's preliminary specification cost cap (default: 1)",
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
        metavar="-- LEETPROOF_ARG ...",
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
    if input_file is None:
        raise ValueError("custom programs must generate a specification first")
    if workflow == "velvet":
        return input_file, f"{base}/Impl.lean"
    return input_file, f"{base}/LeanImpl.lean"


def validate_relative_path(
    parser: argparse.ArgumentParser, value: str, flag: str
) -> None:
    path = Path(value)
    if path.is_absolute():
        parser.error(f"{flag} must be relative to llmgen-experiment: {value}")
    if path.parts and path.parts[0] == "llmgen-experiment":
        parser.error(f"{flag} must not start with 'llmgen-experiment/': {value}")
    if ".." in path.parts:
        parser.error(f"{flag} must stay inside llmgen-experiment: {value}")


def custom_problem(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> Problem:
    required = {
        "--custom-title": args.custom_title,
        "--custom-description": args.custom_description,
        "--custom-output-name": args.custom_output_name,
    }
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        parser.error(f"--custom-program requires {', '.join(missing)}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.custom_program):
        parser.error("--custom-program must contain only letters, digits, '_' or '-'")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.custom_output_name):
        parser.error(
            "--custom-output-name must be one directory-safe name using letters, "
            "digits, '_' or '-'"
        )
    validate_relative_path(parser, args.custom_description, "--custom-description")
    return Problem(
        title=args.custom_title,
        output_name=args.custom_output_name,
        description=args.custom_description,
    )


def command_for_workflow(
    *,
    wrapper: Path,
    workflow: str,
    input_file: str,
    output_file: str,
    provider: str,
    model: str,
    max_cost: float,
    session_name: str | None = None,
) -> list[str]:
    common = [
        "--input-file",
        input_file,
        "--output-file",
        output_file,
        "--provider",
        provider,
        "--model",
        model,
        "--max-cost",
        f"{max_cost:g}",
    ]
    if workflow == "spec":
        return [str(wrapper), "pipeline", *common, "--end", "specgen"]
    if workflow == "velvet":
        return [str(wrapper), "pipeline", *common, "--start", "codegen"]
    assert session_name is not None
    return [
        str(wrapper),
        "lean-synth",
        *common,
        "--session-name",
        session_name,
    ]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_problems:
        for name, problem in PROBLEMS.items():
            print(f"{name}\t{problem.title}\t{problem.description}")
        return

    if not args.problem and not args.custom_program:
        parser.error(
            "--problem or --custom-program is required unless --list-problems is used"
        )
    if not args.workflow:
        parser.error("--workflow is required unless --list-problems is used")

    model = args.model
    if model is None and args.provider == "openai":
        model = "gpt-5.2"
    if not model:
        parser.error("--model or LEETPROOF_MODEL is required for Anthropic")
    max_cost = args.max_cost
    if max_cost is None:
        max_cost = 1.0 if args.workflow == "spec" else 5.0
    if max_cost <= 0:
        parser.error("--max-cost must be greater than zero")
    if args.spec_max_cost <= 0:
        parser.error("--spec-max-cost must be greater than zero")

    artifact_root = Path(__file__).resolve().parent.parent
    project_root = artifact_root / "llmgen-experiment"
    is_custom = args.custom_program is not None
    custom_details_supplied = any(
        (args.custom_title, args.custom_description, args.custom_output_name)
    )
    if not is_custom and custom_details_supplied:
        parser.error("--custom-* details require --custom-program")
    if is_custom and args.workflow != "spec" and args.input_file:
        parser.error(
            "--input-file cannot override the generated Spec.lean for a custom "
            "velvet or lean workflow"
        )
    problem_key = args.custom_program if is_custom else args.problem
    problem = custom_problem(parser, args) if is_custom else PROBLEMS[args.problem]
    if is_custom and args.workflow != "spec":
        generated_spec = f"llmgen/SmokeTests/{problem.output_name}/Spec.lean"
        mapped_input = generated_spec
        mapped_output = f"llmgen/SmokeTests/{problem.output_name}/"
        mapped_output += "Impl.lean" if args.workflow == "velvet" else "LeanImpl.lean"
    else:
        mapped_input, mapped_output = default_paths(
            problem, args.workflow, project_root
        )
    input_file = args.input_file or mapped_input
    output_file = args.output_file or mapped_output
    validate_relative_path(parser, input_file, "--input-file")
    validate_relative_path(parser, output_file, "--output-file")

    input_on_host = project_root / input_file
    if not is_custom or args.workflow == "spec":
        input_must_exist = input_on_host
    else:
        input_must_exist = project_root / problem.description
    if not input_must_exist.is_file():
        parser.error(f"input file does not exist: {input_must_exist}")
    if not args.dry_run:
        (project_root / output_file).parent.mkdir(parents=True, exist_ok=True)
        if is_custom and args.workflow != "spec":
            generated_spec = f"llmgen/SmokeTests/{problem.output_name}/Spec.lean"
            (project_root / generated_spec).parent.mkdir(parents=True, exist_ok=True)

    wrapper = artifact_root / "leetproof.sh"
    session_name = None
    if args.workflow == "lean":
        session_name = args.session_name or (
            f"artifact-lean-{problem_key}-"
            f"{datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
        )
    command = command_for_workflow(
        wrapper=wrapper,
        workflow=args.workflow,
        input_file=input_file,
        output_file=output_file,
        provider=args.provider,
        model=model,
        max_cost=max_cost,
        session_name=session_name,
    )

    forwarded = args.lloom_args
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    command.extend(forwarded)

    preliminary_spec_command = None
    if is_custom and args.workflow != "spec":
        spec_output = f"llmgen/SmokeTests/{problem.output_name}/Spec.lean"
        preliminary_spec_command = command_for_workflow(
            wrapper=wrapper,
            workflow="spec",
            input_file=problem.description,
            output_file=spec_output,
            provider=args.provider,
            model=model,
            max_cost=args.spec_max_cost,
        )
        preliminary_spec_command.extend(forwarded)

    if args.dry_run:
        if preliminary_spec_command is not None:
            print(shlex.join(preliminary_spec_command))
        print(shlex.join(command))
        return

    spec_source = None
    if args.workflow in ("velvet", "lean"):
        generated_spec = f"llmgen/SmokeTests/{problem.output_name}/Spec.lean"
        spec_source = "generated" if input_file == generated_spec else "bundled/custom"

    print("LLoom smoke-test configuration", flush=True)
    print(f"  Problem:   {problem_key} ({problem.title})", flush=True)
    print(f"  Workflow:  {args.workflow}", flush=True)
    print(f"  Provider:  {args.provider}", flush=True)
    print(f"  Model:     {model}", flush=True)
    print(f"  Max cost:  ${max_cost:g}", flush=True)
    print(f"  Input:     {input_file}", flush=True)
    if spec_source is not None:
        print(f"  Spec:      {spec_source}", flush=True)
    print(f"  Output:    {output_file}", flush=True)
    if preliminary_spec_command is not None:
        print("Starting preliminary specification generation...", flush=True)
        subprocess.run(preliminary_spec_command, check=True)
        if not input_on_host.is_file():
            parser.error(
                f"specification generation did not create expected file: {input_on_host}"
            )

    print("Starting LLoom...", flush=True)
    os.execv(str(wrapper), command)


if __name__ == "__main__":
    main()
