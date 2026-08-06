#!/usr/bin/env python3
"""Pinned, end-to-end reproduction workflow for the specification-PBT artifact.

The benchmark revisions are the exact revisions cited in the feedback reports.
The script deliberately keeps cloned benchmarks and generated Lean files out of
the tracked source tree: benchmark checkouts go in ``specpbt-data/`` and Lean
modules go in the supplied Velvet/Loom project.

Examples (from the repository root)::

    ./specpbt.sh convert
    ./specpbt.sh run smoke
    ./specpbt.sh run full
    ./specpbt.sh run all
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path(
    os.environ.get("LEETPROOF_SPECPBT_DATA_DIR", REPO_ROOT / "specpbt-data")
).expanduser().resolve()
DEFAULT_LEAN_PROJECT = Path(
    os.environ.get("LEETPROOF_PROJECT_DIR", REPO_ROOT / "llmgen-experiment")
).expanduser().resolve()

# Local runs use the uv project under leetproof/. Docker installs the same
# package at /opt/leetproof, which is already importable.
LEETPROOF_ROOT = REPO_ROOT / "leetproof"
if LEETPROOF_ROOT.is_dir():
    sys.path.insert(0, str(LEETPROOF_ROOT))

BENCHMARKS = {
    "verina": {
        "url": "https://github.com/sunblaze-ucb/verina.git",
        # Revision cited in the packaged Verina feedback report.
        "commit": "643ed3cab89f37a243720640206de3b178730534",
    },
    "clever": {
        "url": "https://github.com/trishullab/clever.git",
        # Revision cited in the packaged Clever feedback report.
        "commit": "603e318da2a633cf3aea3a6b2c43cc3fd0187fb7",
    },
}

# Every issue listed in the two feedback reports.  Three Verina issues were
# diagnosed as incorrect specifications rather than via a uniqueness witness;
# we still run them in ``full`` so the artifact records their checker outcome.
VERINA_FEEDBACK_IDS = (
    "verina_advanced_8", "verina_advanced_10", "verina_advanced_12",
    "verina_advanced_13", "verina_advanced_47", "verina_advanced_71",
    "verina_basic_22", "verina_basic_34", "verina_basic_37",
    "verina_basic_46", "verina_basic_77", "verina_basic_79",
    "verina_basic_84", "verina_basic_95", "verina_basic_97",
    "verina_basic_103",
)
CLEVER_FEEDBACK_IDS = (
    "7", "9", "24", "27", "29", "30", "44", "49", "68", "69",
    "79", "84", "88", "89", "94", "96", "156", "161",
)

# Covers both bug modes: an underspecified spec (Verina #8 / Clever #7) and
# a concrete implementation result violating an otherwise strong spec (Clever
# #9).
SMOKE_CASES = (("verina", "verina_advanced_8"), ("clever", "7"), ("clever", "9"))


@dataclass
class RunResult:
    dataset: str
    problem_id: str
    status: str
    seconds: float
    detail: str


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _verina_checkout(lean_project: Path) -> Path:
    return lean_project / ".lloom" / "benchmarks" / "verina"


def download_benchmarks(lean_project: Path) -> None:
    """Clone and detach Verina at the report-cited commit for local runs."""
    for name in ("verina",):
        info = BENCHMARKS[name]
        checkout = _verina_checkout(lean_project)
        if not checkout.exists():
            checkout.parent.mkdir(parents=True, exist_ok=True)
            _run(["git", "clone", info["url"], str(checkout)])
        if not (checkout / ".git").exists():
            raise RuntimeError(f"{checkout} exists but is not a Git checkout")

        # Fetch before checking out so an existing partial/shallow clone also
        # becomes able to resolve the historical commit.
        _run(["git", "-C", str(checkout), "fetch", "--tags", "origin"])
        _run(["git", "-C", str(checkout), "checkout", "--detach", info["commit"]])
        actual = _git_output(checkout, "rev-parse", "HEAD")
        if actual != info["commit"]:
            raise RuntimeError(f"{name}: wanted {info['commit']}, got {actual}")
        print(f"{name}: {actual}", flush=True)


def verify_benchmarks(lean_project: Path) -> None:
    for name in ("verina",):
        info = BENCHMARKS[name]
        checkout = _verina_checkout(lean_project)
        if not (checkout / ".git").exists():
            raise RuntimeError(
                f"Missing {name} checkout at {checkout}: rebuild the Docker image "
                "or run `download` for a local checkout"
            )
        actual = _git_output(checkout, "rev-parse", "HEAD")
        if actual != info["commit"]:
            raise RuntimeError(
                f"{name} checkout is {actual}; expected pinned revision {info['commit']}. "
                "Run `download` to repair it."
            )


def _install_clever_helpers(source: Path, lean_project: Path) -> None:
    """Install the tiny, versioned compatibility adaptation for Clever helpers.

    The benchmark's helper file was written for its original Lean toolchain.
    The additions below are the minimal changes used in the original experiment
    to compile it with the Velvet experiment project.  It is written under the
    artifact namespace, leaving users' ``Extensions/CleverAllImports.lean``
    untouched.
    """
    content = source.read_text(encoding="utf-8")
    imports = "import Mathlib\nimport Mathlib.Algebra.Polynomial.Basic\nimport Std.Data.HashMap"
    replacement = (
        "import Mathlib.Tactic\nimport Mathlib.Algebra.Polynomial.Basic\n"
        "import Batteries.Data.String.Lemmas\nimport Std.Data.HashMap\n"
        "import Init.Data.String.Basic"
    )
    if imports not in content:
        raise RuntimeError("Unexpected Clever AllImports.lean header at pinned revision")
    content = content.replace(imports, replacement, 1)

    needle = "have h_temp : paren_string.length > 0 := by linarith\n    assumption"
    pieces = content.split(needle)
    if len(pieces) != 4:
        raise RuntimeError("Unexpected Clever helper layout; expected three compatibility sites")
    first = needle.replace("    assumption", "    simp [String.length]\n    assumption")
    third = needle.replace("    assumption", "    simp [String.length] at *\n    grind")
    content = pieces[0] + first + pieces[1] + first + pieces[2] + third + pieces[3]

    destination = lean_project / "llmgen" / "ArtifactSupport" / "CleverAllImports.lean"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def _require_lean_project(lean_project: Path) -> None:
    if not (lean_project / "lakefile.toml").is_file() and not (lean_project / "lakefile.lean").is_file():
        raise RuntimeError(
            f"{lean_project} is not a Lean project. Ensure the packaged llmgen-experiment project is present "
            "or pass --lean-project PATH."
        )


def _clear_generated_specs(spec_root: Path) -> None:
    # This directory is solely owned by the artifact workflow.  Re-creating it
    # makes conversion deterministic without touching any user-generated specs.
    if spec_root.exists():
        shutil.rmtree(spec_root)
    spec_root.mkdir(parents=True)


def convert_benchmarks(lean_project: Path) -> None:
    """Convert every pinned Verina and Clever spec into the PBT input format."""
    verify_benchmarks(lean_project)
    _require_lean_project(lean_project)

    # The existing Verina loader stores and discovers its checkout relative to
    # the Lean project. Docker's entrypoint uses the same working directory.
    os.chdir(lean_project)

    from clever_bench.benchmark import Benchmark
    from evals.clever_to_lean import build_lean_file as build_clever
    from evals.verina_to_lean import build_lean_file as build_verina, load_verina_problem

    spec_root = lean_project / "llmgen" / "ArtifactSpecs"
    _clear_generated_specs(spec_root)
    verina_dir = _verina_checkout(lean_project)

    verina_dest = spec_root / "Verina"
    verina_dest.mkdir()
    verina_ids = sorted(
        p.name for p in (verina_dir / "datasets" / "verina").glob("verina_*") if p.is_dir()
    )
    for problem_id in verina_ids:
        data = load_verina_problem(problem_id)
        (verina_dest / f"{problem_id}.lean").write_text(build_verina(data), encoding="utf-8")

    clever_dest = spec_root / "Clever"
    clever_dest.mkdir()
    clever_benchmark = Benchmark()
    _install_clever_helpers(Path(clever_benchmark.helper_definition_file), lean_project)
    clever_benchmark.load_all()
    clever_problems = sorted(clever_benchmark.problems, key=lambda problem: problem.problem_id)
    for problem in clever_problems:
        problem_id = problem.problem_id
        (clever_dest / f"problem_{problem_id}.lean").write_text(
            build_clever(problem, clever_import="llmgen.ArtifactSupport.CleverAllImports"),
            encoding="utf-8",
        )

    manifest = {
        "verina_commit": BENCHMARKS["verina"]["commit"],
        "clever_commit": BENCHMARKS["clever"]["commit"],
        "verina_specs": len(verina_ids),
        "clever_specs": len(clever_problems),
    }
    (spec_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


def _spec_file(lean_project: Path, dataset: str, problem_id: str) -> Path:
    base = lean_project / "llmgen" / "ArtifactSpecs"
    if dataset == "verina":
        return base / "Verina" / f"{problem_id}.lean"
    return base / "Clever" / f"problem_{problem_id}.lean"


def _selected_cases(kind: str, lean_project: Path) -> Iterable[tuple[str, str]]:
    if kind == "smoke":
        return SMOKE_CASES
    if kind == "full":
        return (
            *(("verina", pid) for pid in VERINA_FEEDBACK_IDS),
            *(("clever", pid) for pid in CLEVER_FEEDBACK_IDS),
        )
    if kind == "all":
        verina = (("verina", p.stem) for p in sorted((lean_project / "llmgen" / "ArtifactSpecs" / "Verina").glob("*.lean")))
        clever = (("clever", p.stem.removeprefix("problem_")) for p in sorted((lean_project / "llmgen" / "ArtifactSpecs" / "Clever").glob("problem_*.lean")))
        return (*verina, *clever)
    raise ValueError(f"Unknown run kind: {kind}")


def run_checks(kind: str, data_dir: Path, lean_project: Path) -> list[RunResult]:
    """Run PBT over smoke, feedback cases, or the complete converted benchmark."""
    _require_lean_project(lean_project)
    spec_root = lean_project / "llmgen" / "ArtifactSpecs"
    if not spec_root.is_dir():
        raise RuntimeError("Converted specs are missing: run `convert` first")

    from utils.spec_bug_finder import generate_and_check

    verification_root = lean_project / "llmgen" / "ArtifactVerification" / kind
    verification_root.mkdir(parents=True, exist_ok=True)
    results: list[RunResult] = []
    cases = tuple(_selected_cases(kind, lean_project))
    print(f"Running {len(cases)} {kind} case(s)", flush=True)
    for index, (dataset, problem_id) in enumerate(cases, 1):
        source = _spec_file(lean_project, dataset, problem_id)
        if not source.is_file():
            results.append(RunResult(dataset, problem_id, "missing_spec", 0.0, str(source)))
            continue
        output = verification_root / f"{dataset}_{problem_id}.lean"
        print(f"[{index}/{len(cases)}] {dataset}/{problem_id}", flush=True)
        started = time.monotonic()
        try:
            status, detail = generate_and_check(str(source), str(output), str(lean_project))
        except Exception as exc:  # Keep a full-test report even if one case crashes.
            status, detail = "error", f"{type(exc).__name__}: {exc}"
        elapsed = time.monotonic() - started
        results.append(RunResult(dataset, problem_id, status, elapsed, detail))
        print(f"  => {status} ({elapsed:.1f}s)", flush=True)

    results_dir = data_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    report = results_dir / f"{kind}.json"
    report.write_text(json.dumps([asdict(result) for result in results], indent=2) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print(f"Wrote {report}", flush=True)
    print(json.dumps(counts, indent=2), flush=True)
    return results


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=_path, default=DEFAULT_DATA_DIR,
                        help="Directory for machine-readable JSON reports")
    parser.add_argument("--lean-project", type=_path, default=DEFAULT_LEAN_PROJECT,
                        help="Velvet/Loom Lean project used to compile generated specs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("download", help="clone and pin Verina for local execution")
    subparsers.add_parser("convert", help="convert all pinned benchmark specs")
    run_parser = subparsers.add_parser("run", help="run property-based specification checks")
    run_parser.add_argument("kind", choices=("smoke", "full", "all"))
    args = parser.parse_args()

    if args.command == "download":
        download_benchmarks(args.lean_project)
    elif args.command == "convert":
        convert_benchmarks(args.lean_project)
    else:
        run_checks(args.kind, args.data_dir, args.lean_project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
