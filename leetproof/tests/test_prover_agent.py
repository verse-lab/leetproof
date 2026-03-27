import pytest

from agents.prover_agent import ProverAgent
from utils.lean.types import Goal, LakeBuildResult, LeanDiagnostic, Param
from utils.proof_types import (
    AttemptBudgetConfig,
    AttemptBudgetConfigBundle,
    AttemptBudgetMode,
    PantographParams,
    ProvingContext,
)


class FakePantograph:
    def __init__(self):
        self.calls: list[str] = []

    async def check_build(self, lean_code: str) -> LakeBuildResult:
        self.calls.append(lean_code)
        if "exact (foo_0 P Q hpost1 hpost1' hp hq)" in lean_code:
            return LakeBuildResult(
                typechecks=False,
                diagnostics=[
                    LeanDiagnostic(
                        severity="error",
                        message="Unknown identifier `hpost1'`",
                        line=1,
                        column=1,
                    )
                ],
            )
        return LakeBuildResult(typechecks=True, diagnostics=[])


@pytest.mark.asyncio
async def test_sanitize_extracted_goal_for_replay_drops_unknown_replay_param():
    goal = Goal(
        name="foo_0",
        params=[
            Param(name="P", ty="Prop"),
            Param(name="Q", ty="Prop"),
            Param(name="hpost1", ty="P ∧ Q"),
            Param(name="hpost1'", ty="P ∧ Q"),
            Param(name="hp", ty="P"),
            Param(name="hq", ty="Q"),
        ],
        final_goal="P",
    )
    assembled_sketch = """theorem foo (P Q : Prop) (hpost1 : P ∧ Q) : P := by
  have hpost1' : P ∧ Q := by
    exact hpost1
  rcases hpost1' with ⟨hp, hq⟩
  have h : P := by
    expose_names; sorry
  exact h
"""

    pantograph = FakePantograph()

    sanitized = await ProverAgent._sanitize_extracted_goal_for_replay(
        pantograph=pantograph,
        goal=goal,
        assembled_sketch=assembled_sketch,
    )

    assert [param.name for param in sanitized.params] == ["P", "Q", "hpost1", "hp", "hq"]
    assert any("exact (foo_0 P Q hpost1 hpost1' hp hq)" in call for call in pantograph.calls)
    assert any("exact (foo_0 P Q hpost1 hp hq)" in call for call in pantograph.calls)


class _DummyExtractor:
    def extract(self, content: str) -> str:
        return content


def _make_ctx(file_path: str, goal: Goal, *, pending_lemma_blocks: list[str]) -> ProvingContext:
    return ProvingContext(
        file_path=file_path,
        goal=goal,
        sections=["Proof"],
        pantograph=PantographParams(key=goal.name, project_path="."),
        automation_tactics=[],
        informal_reasoning="",
        context_extractor=_DummyExtractor(),
        attempt_budgets=AttemptBudgetConfigBundle(
            shallow=AttemptBudgetConfig(
                mode=AttemptBudgetMode.UP,
                base=1,
                slope=0,
                min_attempts=1,
                max_attempts=1,
            ),
            decomposition=AttemptBudgetConfig(
                mode=AttemptBudgetMode.DOWN,
                base=1,
                slope=0,
                min_attempts=1,
                max_attempts=1,
            ),
        ),
        pending_lemma_blocks=pending_lemma_blocks,
    )


def test_write_shutdown_snapshot_preserves_progress_and_is_idempotent(tmp_path):
    file_path = tmp_path / "progress.lean"
    file_path.write_text(
        """section Specs
lemma seed : True := by
  trivial
end Specs

section Proof
lemma child_done : True := by
  trivial
end Proof
"""
    )

    goal = Goal(
        name="main_goal",
        params=[Param(name="h", ty="True")],
        final_goal="True",
    )
    ctx = _make_ctx(
        str(file_path),
        goal,
        pending_lemma_blocks=[
            "lemma helper_progress : True := by\n  trivial",
        ],
    )

    prover = object.__new__(ProverAgent)
    prover._section = "Proof"

    prover.write_shutdown_snapshot(ctx)
    prover.write_shutdown_snapshot(ctx)

    content = file_path.read_text()
    assert "lemma child_done : True := by" in content
    assert content.count("lemma helper_progress : True := by") == 1
    assert content.count("theorem main_goal") == 1
    assert "sorry" in content
