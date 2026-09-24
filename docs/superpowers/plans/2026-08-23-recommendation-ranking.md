# Recommendation Ranking and Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert raw CLIPSpy scores into exactly three deterministic, faithfully explained tool recommendations and update the Arabic backend-plan PDF with the verified phase-4 behavior.

**Architecture:** A pure recommendation policy indexes raw effects, validates their consistency, ranks tools with the explicit key `(-score, tool_id)`, and derives bounded reasons from sourced rule impacts. A stateless service composes that policy with the existing real `ClipspyAdapter`; PDF generation remains a separate documentation concern and appends one idempotent Arabic implementation appendix to the tracked plan.

**Tech Stack:** Python 3.12, Pydantic 2, clipspy 1.0.6, pytest 8, ReportLab 4, pypdf 6, arabic-reshaper 3, python-bidi 0.6.

**Spec:** `docs/superpowers/specs/2026-08-23-recommendation-ranking-design.md`

## Global Constraints

- Keep ranking and explanation outside CLIPS; never depend on agenda order.
- Rank with `(-tool_score, tool_id)` and do not round or introduce an epsilon.
- Return exactly three unique `Recommendation` items through the existing `RecommendationResult` model.
- Derive matched reasons only from `RuleImpact.rationale` records associated with emitted `ScoreEffect` values.
- Represent negative and absent contributions transparently; never invent capabilities or benchmark claims.
- Do not use benchmarks until a separate normalization and missing-data policy exists.
- Add no runtime dependency; PDF tooling may be added only to the `dev` optional dependency group.
- Do not add JSON loading, production knowledge data, HTTP routes, or localization in this phase.
- Use the real `ClipspyAdapter` in integration tests; do not mock CLIPS.
- Keep the existing API error envelope and all phase-1 through phase-3 behavior unchanged.
- Update `output/pdf/ai_expert_system_backend_plan_ar.pdf` in place only after implementation verification.
- Before the first PDF authoring command, run the PDF artifact-operation marker exactly once.
- Render and visually inspect every final PDF page before completion.

---

### Task 1: Rank raw tool scores deterministically

**Files:**
- Create: `app/recommendations/errors.py`
- Create: `app/recommendations/ranking.py`
- Create: `tests/test_recommendations.py`

**Interfaces:**
- Consumes: `Sequence[Tool]`, `InferenceResult`
- Produces: internal `RankedTool(tool: Tool, score: float, effects: tuple[ScoreEffect, ...])`
- Produces: `rank_tools(tools, inference_result) -> tuple[RankedTool, ...]`
- Raises: `InsufficientToolsError`, `RecommendationConsistencyError`

- [ ] **Step 1: Write complete failing ranking tests**

Create `tests/test_recommendations.py`:

```python
import pytest

from app.domain.models import StageId, Tool
from app.expert_engine import InferenceResult, ScoreEffect
from app.recommendations.errors import (
    InsufficientToolsError,
    RecommendationConsistencyError,
)
from app.recommendations.ranking import rank_tools


def tool(tool_id: str) -> Tool:
    return Tool(
        id=tool_id,
        name=f"Tool {tool_id}",
        description="A recommendation test tool.",
        stages=[StageId.ANALYSIS],
    )


def test_rank_tools_selects_descending_scores_and_tool_id_ties() -> None:
    ranked = rank_tools(
        tools=[tool("tool-d"), tool("tool-c"), tool("tool-b"), tool("tool-a")],
        inference_result=InferenceResult(
            tool_scores={
                "tool-d": -0.2,
                "tool-c": 0.4,
                "tool-b": 0.8,
                "tool-a": 0.8,
            }
        ),
    )

    assert [(item.tool.id, item.score) for item in ranked] == [
        ("tool-a", 0.8),
        ("tool-b", 0.8),
        ("tool-c", 0.4),
        ("tool-d", -0.2),
    ]


def test_rank_tools_sorts_negative_scores_numerically() -> None:
    ranked = rank_tools(
        tools=[tool("tool-a"), tool("tool-b"), tool("tool-c")],
        inference_result=InferenceResult(
            tool_scores={"tool-a": -0.7, "tool-b": -0.1, "tool-c": -0.4}
        ),
    )

    assert [item.tool.id for item in ranked] == ["tool-b", "tool-c", "tool-a"]


def test_rank_tools_requires_at_least_three_tools() -> None:
    with pytest.raises(InsufficientToolsError, match="at least three"):
        rank_tools(
            tools=[tool("tool-a"), tool("tool-b")],
            inference_result=InferenceResult(
                tool_scores={"tool-a": 0.8, "tool-b": 0.4}
            ),
        )


def test_rank_tools_rejects_inconsistent_score_ids() -> None:
    with pytest.raises(RecommendationConsistencyError, match="score ids"):
        rank_tools(
            tools=[tool("tool-a"), tool("tool-b"), tool("tool-c")],
            inference_result=InferenceResult(
                tool_scores={"tool-a": 0.8, "tool-b": 0.4, "unknown": 0.2}
            ),
        )
```

- [ ] **Step 2: Run Task 1 tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -v
```

Expected: collection fails because `app.recommendations` does not exist.

- [ ] **Step 3: Implement recommendation errors**

Create `app/recommendations/errors.py`:

```python
class RecommendationError(Exception):
    """Base error for recommendation ranking and explanation."""


class InsufficientToolsError(RecommendationError):
    """Raised when fewer than three tools are available."""


class RecommendationConsistencyError(RecommendationError):
    """Raised when inference output cannot be reconciled with domain knowledge."""
```

- [ ] **Step 4: Implement the pure ranking policy**

Create `app/recommendations/ranking.py`:

```python
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import Tool
from app.expert_engine import InferenceResult, ScoreEffect
from app.recommendations.errors import (
    InsufficientToolsError,
    RecommendationConsistencyError,
)


@dataclass(frozen=True)
class RankedTool:
    tool: Tool
    score: float
    effects: tuple[ScoreEffect, ...]


def rank_tools(
    *, tools: Sequence[Tool], inference_result: InferenceResult
) -> tuple[RankedTool, ...]:
    if len(tools) < 3:
        raise InsufficientToolsError("recommendations require at least three tools")

    tools_by_id: dict[str, Tool] = {}
    for item in tools:
        if item.id in tools_by_id:
            raise RecommendationConsistencyError(f"duplicate tool id: {item.id}")
        tools_by_id[item.id] = item

    tool_ids = set(tools_by_id)
    if set(inference_result.tool_scores) != tool_ids:
        raise RecommendationConsistencyError(
            "inference score ids do not match the supplied tool ids"
        )

    effects_by_tool: defaultdict[str, list[ScoreEffect]] = defaultdict(list)
    for effect in inference_result.effects:
        if effect.tool_id not in tools_by_id:
            raise RecommendationConsistencyError(
                f"inference effect references unknown tool: {effect.tool_id}"
            )
        effects_by_tool[effect.tool_id].append(effect)

    ranked = [
        RankedTool(
            tool=item,
            score=inference_result.tool_scores[item.id],
            effects=tuple(
                sorted(
                    effects_by_tool[item.id],
                    key=lambda effect: (effect.rule_id, effect.value),
                )
            ),
        )
        for item in tools_by_id.values()
    ]
    ranked.sort(key=lambda item: (-item.score, item.tool.id))
    return tuple(ranked)
```

- [ ] **Step 5: Verify Task 1 GREEN and the existing suite**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -v
.venv\Scripts\python.exe -m pytest -q
```

Expected: all ranking tests and the complete suite pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add app/recommendations/errors.py app/recommendations/ranking.py tests/test_recommendations.py
git commit -m "feat: rank raw tool scores deterministically"
```

---

### Task 2: Build faithful bounded recommendation reasons

**Files:**
- Create: `app/recommendations/explanations.py`
- Modify: `tests/test_recommendations.py`

**Interfaces:**
- Consumes: `RankedTool`, `Sequence[Rule]`
- Produces: `build_reason(ranked_tool, rules) -> str`
- Raises: `RecommendationConsistencyError`

- [ ] **Step 1: Add complete failing explanation tests**

Append these imports and helpers to `tests/test_recommendations.py`:

```python
from datetime import date

from app.domain.models import EvaluationSource, Rule, RuleImpact, SourceKind
from app.recommendations.explanations import MAX_REASON_LENGTH, build_reason
from app.recommendations.ranking import RankedTool


def source() -> EvaluationSource:
    return EvaluationSource(
        id="official-docs",
        name="Official documentation",
        publisher="Example Foundation",
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://example.com/official-docs",
        published_at=date(2026, 8, 1),
        collected_at=date(2026, 8, 23),
    )


def sourced_rule(
    *,
    rule_id: str,
    tool_id: str,
    rationale: str,
) -> Rule:
    return Rule(
        id=rule_id,
        question_id="analysis-q1",
        answer_option_id="yes",
        impacts=[
            RuleImpact(
                tool_id=tool_id,
                weight=0.75,
                rationale=rationale,
                sources=[source()],
            )
        ],
    )
```

Append the behavioral tests:

```python
def test_build_reason_uses_the_strongest_positive_rationale() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.9,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="weak", value=0.2),
            ScoreEffect(tool_id="tool-a", rule_id="strong", value=0.7),
        ),
    )
    rules = [
        sourced_rule(rule_id="weak", tool_id="tool-a", rationale="Weak support."),
        sourced_rule(rule_id="strong", tool_id="tool-a", rationale="Strong support."),
    ]

    assert build_reason(ranked_tool=ranked_tool, rules=rules) == "Strong support."


def test_build_reason_includes_the_strongest_negative_counterfactor() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.4,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="positive", value=0.7),
            ScoreEffect(tool_id="tool-a", rule_id="negative", value=-0.3),
        ),
    )
    rules = [
        sourced_rule(
            rule_id="positive", tool_id="tool-a", rationale="Strong workflow fit."
        ),
        sourced_rule(
            rule_id="negative", tool_id="tool-a", rationale="Higher setup cost."
        ),
    ]

    assert build_reason(ranked_tool=ranked_tool, rules=rules) == (
        "Strong workflow fit. Countervailing factor: Higher setup cost."
    )


def test_build_reason_is_transparent_when_no_rule_changed_the_score() -> None:
    ranked_tool = RankedTool(tool=tool("tool-a"), score=0.0, effects=())

    assert build_reason(ranked_tool=ranked_tool, rules=[]) == (
        "No matching rule changed this tool's score; it ranked by score and the "
        "deterministic tool-ID tie-break."
    )


def test_build_reason_reports_a_negative_only_match_honestly() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=-0.3,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="negative", value=-0.3),
        ),
    )
    rules = [
        sourced_rule(
            rule_id="negative", tool_id="tool-a", rationale="Higher setup cost."
        )
    ]

    assert build_reason(ranked_tool=ranked_tool, rules=rules) == (
        "Ranked comparatively despite a negative matched factor: Higher setup cost."
    )


def test_build_reason_deduplicates_the_counterfactor_rationale() -> None:
    long_rationale = "x" * 2_000
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.4,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="positive", value=0.7),
            ScoreEffect(tool_id="tool-a", rule_id="negative", value=-0.3),
        ),
    )
    rules = [
        sourced_rule(
            rule_id="positive", tool_id="tool-a", rationale=long_rationale
        ),
        sourced_rule(
            rule_id="negative", tool_id="tool-a", rationale=long_rationale
        ),
    ]

    reason = build_reason(ranked_tool=ranked_tool, rules=rules)

    assert len(reason) == MAX_REASON_LENGTH
    assert reason == long_rationale
    assert "Countervailing factor" not in reason


def test_build_reason_bounds_combined_output() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.4,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="positive", value=0.7),
            ScoreEffect(tool_id="tool-a", rule_id="negative", value=-0.3),
        ),
    )
    rules = [
        sourced_rule(
            rule_id="positive", tool_id="tool-a", rationale="x" * 2_000
        ),
        sourced_rule(
            rule_id="negative", tool_id="tool-a", rationale="Different factor."
        ),
    ]

    reason = build_reason(ranked_tool=ranked_tool, rules=rules)

    assert len(reason) == MAX_REASON_LENGTH
    assert reason.endswith("…")


def test_build_reason_rejects_an_unmappable_effect() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.7,
        effects=(ScoreEffect(tool_id="tool-a", rule_id="missing", value=0.7),),
    )

    with pytest.raises(RecommendationConsistencyError, match="missing rule impact"):
        build_reason(ranked_tool=ranked_tool, rules=[])
```

- [ ] **Step 2: Run explanation tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -v
```

Expected: collection fails because `app.recommendations.explanations` does not exist.

- [ ] **Step 3: Implement effect-to-impact resolution and bounded prose**

Create `app/recommendations/explanations.py`:

```python
from collections.abc import Sequence

from app.domain.models import Rule, RuleImpact
from app.recommendations.errors import RecommendationConsistencyError
from app.recommendations.ranking import RankedTool


MAX_REASON_LENGTH = 2_000
NO_EFFECT_REASON = (
    "No matching rule changed this tool's score; it ranked by score and the "
    "deterministic tool-ID tie-break."
)


def _bound_reason(reason: str) -> str:
    if len(reason) <= MAX_REASON_LENGTH:
        return reason
    return reason[: MAX_REASON_LENGTH - 1].rstrip() + "…"


def _impact_index(rules: Sequence[Rule]) -> dict[tuple[str, str], RuleImpact]:
    impacts: dict[tuple[str, str], RuleImpact] = {}
    for rule in rules:
        for impact in rule.impacts:
            key = (rule.id, impact.tool_id)
            if key in impacts:
                raise RecommendationConsistencyError(
                    f"duplicate rule impact mapping: {rule.id}/{impact.tool_id}"
                )
            impacts[key] = impact
    return impacts


def build_reason(*, ranked_tool: RankedTool, rules: Sequence[Rule]) -> str:
    if not ranked_tool.effects:
        return NO_EFFECT_REASON

    impacts = _impact_index(rules)
    contributions: list[tuple[float, str, str]] = []
    for effect in ranked_tool.effects:
        impact = impacts.get((effect.rule_id, ranked_tool.tool.id))
        if impact is None:
            raise RecommendationConsistencyError(
                f"missing rule impact for {effect.rule_id}/{ranked_tool.tool.id}"
            )
        contributions.append((effect.value, effect.rule_id, impact.rationale))

    positives = sorted(
        (item for item in contributions if item[0] > 0.0),
        key=lambda item: (-item[0], item[1]),
    )
    negatives = sorted(
        (item for item in contributions if item[0] < 0.0),
        key=lambda item: (item[0], item[1]),
    )

    primary = positives[0][2] if positives else None
    counter = next(
        (
            rationale
            for _, _, rationale in negatives
            if primary is None or rationale != primary
        ),
        None,
    )
    if primary is not None and counter is not None:
        return _bound_reason(f"{primary} Countervailing factor: {counter}")
    if primary is not None:
        return _bound_reason(primary)
    if counter is not None:
        return _bound_reason(
            f"Ranked comparatively despite a negative matched factor: {counter}"
        )
    return NO_EFFECT_REASON
```

- [ ] **Step 4: Verify Task 2 GREEN and mutate the critical branches mentally**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -v
```

Expected: all ranking and explanation tests pass. Confirm these mutations would fail at
least one test: choosing the weakest positive, hiding the negative counterfactor, returning
an invented no-effect reason, allowing an unmappable rule, or exceeding 2,000 characters.

- [ ] **Step 5: Commit Task 2**

```powershell
git add app/recommendations/explanations.py tests/test_recommendations.py
git commit -m "feat: explain recommendations from sourced effects"
```

---

### Task 3: Compose ranking with real CLIPSpy inference

**Files:**
- Create: `app/recommendations/service.py`
- Modify: `tests/test_recommendations.py`

**Interfaces:**
- Consumes: existing `ClipspyAdapter.infer(...) -> InferenceResult`
- Produces: `RecommendationService.recommend(...) -> RecommendationResult`
- Internal dependency seam: `InferenceEngine(Protocol)`

- [ ] **Step 1: Add full real-engine factories and a failing integration test**

Append these imports and helpers to `tests/test_recommendations.py`:

```python
from app.domain.models import AnswerOption, Question, QuestionType
from app.expert_engine import AnswerSelection
from app.recommendations.service import RecommendationService


def question() -> Question:
    return Question(
        id="analysis-q1",
        stage=StageId.ANALYSIS,
        prompt="Do you need this workflow capability?",
        type=QuestionType.SINGLE_CHOICE,
        importance=0.8,
        options=[
            AnswerOption(id="yes", label="Yes", value=1.0),
            AnswerOption(id="no", label="No", value=-1.0),
        ],
    )


def weighted_rule(
    *, rule_id: str, tool_id: str, weight: float, rationale: str
) -> Rule:
    return Rule(
        id=rule_id,
        question_id="analysis-q1",
        answer_option_id="yes",
        impacts=[
            RuleImpact(
                tool_id=tool_id,
                weight=weight,
                rationale=rationale,
                sources=[source()],
            )
        ],
    )
```

Append the real integration test:

```python
def test_recommendation_service_returns_top_three_from_real_clipspy() -> None:
    tools = [tool("tool-d"), tool("tool-c"), tool("tool-b"), tool("tool-a")]
    rules = [
        weighted_rule(
            rule_id="rule-a",
            tool_id="tool-a",
            weight=1.0,
            rationale="Best documented workflow fit.",
        ),
        weighted_rule(
            rule_id="rule-b",
            tool_id="tool-b",
            weight=0.75,
            rationale="Strong documented workflow fit.",
        ),
        weighted_rule(
            rule_id="rule-c",
            tool_id="tool-c",
            weight=0.5,
            rationale="Moderate documented workflow fit.",
        ),
    ]

    result = RecommendationService().recommend(
        tools=tools,
        questions=[question()],
        rules=rules,
        answers=[AnswerSelection(question_id="analysis-q1", option_ids=["yes"])],
    )

    assert [item.tool_id for item in result.recommendations] == [
        "tool-a",
        "tool-b",
        "tool-c",
    ]
    assert [item.reason for item in result.recommendations] == [
        "Best documented workflow fit.",
        "Strong documented workflow fit.",
        "Moderate documented workflow fit.",
    ]
```

- [ ] **Step 2: Run the integration test and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py::test_recommendation_service_returns_top_three_from_real_clipspy -v
```

Expected: collection fails because `app.recommendations.service` does not exist.

- [ ] **Step 3: Implement the narrow service boundary**

Create `app/recommendations/service.py`:

```python
from collections.abc import Sequence
from typing import Protocol

from app.domain.models import (
    Question,
    Recommendation,
    RecommendationResult,
    Rule,
    Tool,
)
from app.expert_engine import AnswerSelection, ClipspyAdapter, InferenceResult
from app.recommendations.explanations import build_reason
from app.recommendations.ranking import rank_tools


class InferenceEngine(Protocol):
    def infer(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
    ) -> InferenceResult:
        """Return deterministic raw inference output."""


class RecommendationService:
    def __init__(self, engine: InferenceEngine | None = None) -> None:
        self._engine = engine if engine is not None else ClipspyAdapter()

    def recommend(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
    ) -> RecommendationResult:
        inference_result = self._engine.infer(
            tools=tools,
            questions=questions,
            rules=rules,
            answers=answers,
        )
        top_three = rank_tools(
            tools=tools,
            inference_result=inference_result,
        )[:3]
        return RecommendationResult(
            recommendations=[
                Recommendation(
                    tool_id=ranked.tool.id,
                    tool_name=ranked.tool.name,
                    reason=build_reason(ranked_tool=ranked, rules=rules),
                )
                for ranked in top_three
            ]
        )
```

- [ ] **Step 4: Verify Task 3 GREEN and the complete recommendation module**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -v
.venv\Scripts\python.exe -m pytest -q
```

Expected: the real CLIPSpy integration and the complete backend suite pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add app/recommendations/service.py tests/test_recommendations.py
git commit -m "feat: compose deterministic recommendations"
```

---

### Task 4: Export and harden the recommendation boundary

**Files:**
- Create: `app/recommendations/__init__.py`
- Modify: `tests/test_recommendations.py`

**Interfaces:**
- Produces: stable imports for `RecommendationService`, `RecommendationError`,
  `InsufficientToolsError`, and `RecommendationConsistencyError`
- Keeps internal: `RankedTool`, `rank_tools`, `build_reason`, `InferenceEngine`

- [ ] **Step 1: Add failing determinism and public-boundary tests**

Append:

```python
def test_recommendations_are_identical_for_reordered_inputs() -> None:
    tools = [tool("tool-d"), tool("tool-c"), tool("tool-b"), tool("tool-a")]
    rules = [
        weighted_rule(
            rule_id="rule-a",
            tool_id="tool-a",
            weight=0.75,
            rationale="Documented A fit.",
        ),
        weighted_rule(
            rule_id="rule-b",
            tool_id="tool-b",
            weight=0.75,
            rationale="Documented B fit.",
        ),
        weighted_rule(
            rule_id="rule-c",
            tool_id="tool-c",
            weight=0.5,
            rationale="Documented C fit.",
        ),
    ]
    service = RecommendationService()

    first = service.recommend(
        tools=tools,
        questions=[question()],
        rules=rules,
        answers=[AnswerSelection(question_id="analysis-q1", option_ids=["yes"])],
    )
    second = service.recommend(
        tools=list(reversed(tools)),
        questions=[question()],
        rules=list(reversed(rules)),
        answers=[AnswerSelection(question_id="analysis-q1", option_ids=["yes"])],
    )

    assert first == second
    assert [item.tool_id for item in first.recommendations] == [
        "tool-a",
        "tool-b",
        "tool-c",
    ]


def test_recommendations_package_exports_only_the_public_boundary() -> None:
    from app import recommendations
    from app.recommendations import RecommendationService as PublicService

    assert PublicService is RecommendationService
    assert recommendations.__all__ == [
        "InsufficientToolsError",
        "RecommendationConsistencyError",
        "RecommendationError",
        "RecommendationService",
    ]
    assert "rank_tools" not in recommendations.__all__
    assert "build_reason" not in recommendations.__all__
```

- [ ] **Step 2: Run public-boundary test and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_recommendations.py::test_recommendations_package_exports_only_the_public_boundary -v
```

Expected: import or attribute failure because `app/recommendations/__init__.py` does not
exist.

- [ ] **Step 3: Export exactly the intended interface**

Create `app/recommendations/__init__.py`:

```python
from app.recommendations.errors import (
    InsufficientToolsError,
    RecommendationConsistencyError,
    RecommendationError,
)
from app.recommendations.service import RecommendationService

__all__ = [
    "InsufficientToolsError",
    "RecommendationConsistencyError",
    "RecommendationError",
    "RecommendationService",
]
```

- [ ] **Step 4: Run code verification and scope review**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app tests
.venv\Scripts\python.exe -m pip check
git diff --check
```

Generate every domain and recommendation schema, and require strict top-level models:

```powershell
.venv\Scripts\python.exe -c "from pydantic import BaseModel; from app.domain import models as d; classes=[value for value in vars(d).values() if isinstance(value,type) and issubclass(value,BaseModel) and value is not BaseModel]; schemas=[model.model_json_schema() for model in classes]; assert all(schema.get('additionalProperties') is False for schema in schemas); print(f'validated {len(schemas)} strict domain schemas')"
```

Inspect the complete branch diff. Confirm no HTTP route, JSON loader, benchmark ordering,
production rule data, dependency change, or CLIPS modification exists in Tasks 1-4.

- [ ] **Step 5: Commit Task 4**

```powershell
git add app/recommendations/__init__.py tests/test_recommendations.py
git commit -m "feat: expose recommendation service boundary"
```

---

### Task 5: Update and visually verify the Arabic plan PDF

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/update_backend_plan_pdf.py`
- Create: `tests/test_backend_plan_pdf.py`
- Modify: `output/pdf/ai_expert_system_backend_plan_ar.pdf`

**Interfaces:**
- Produces: `build_updated_pdf(source_path: Path, output_path: Path) -> None`
- Produces: an idempotent six-page PDF marked with `/Phase4Appendix = 1`
- Preserves: the first five source pages byte-semantically through pypdf page cloning

- [ ] **Step 1: Add reproducible PDF development dependencies**

Extend `[project.optional-dependencies].dev` in `pyproject.toml` with:

```toml
    "arabic-reshaper>=3.0,<4.0",
    "pypdf>=6.0,<7.0",
    "python-bidi>=0.6,<1.0",
    "reportlab>=4.4,<5.0",
```

Install the updated development extra:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Verify installed versions:

```powershell
.venv\Scripts\python.exe -c "from importlib.metadata import version; packages=('arabic-reshaper','python-bidi','pypdf','reportlab'); print({package: version(package) for package in packages})"
```

- [ ] **Step 2: Write a failing idempotent-PDF test**

Create `tests/test_backend_plan_pdf.py`:

```python
from pathlib import Path

from pypdf import PdfReader

from scripts.update_backend_plan_pdf import build_updated_pdf


SOURCE_PDF = Path("output/pdf/ai_expert_system_backend_plan_ar.pdf")


def test_build_updated_pdf_appends_one_idempotent_phase_four_page(tmp_path: Path) -> None:
    first_output = tmp_path / "first.pdf"
    second_output = tmp_path / "second.pdf"

    build_updated_pdf(SOURCE_PDF, first_output)
    build_updated_pdf(first_output, second_output)

    first = PdfReader(first_output)
    second = PdfReader(second_output)
    assert len(first.pages) == 6
    assert len(second.pages) == 6
    assert first.metadata.get("/Phase4Appendix") == "1"
    assert second.metadata.get("/Phase4Appendix") == "1"

    appendix_text = second.pages[-1].extract_text()
    assert "(-score, tool_id)" in appendix_text
    assert "RecommendationService" in appendix_text
    assert "pytest -q: PASS" in appendix_text
    assert "Benchmarks do not break ties" in appendix_text
```

- [ ] **Step 3: Run the PDF test and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_backend_plan_pdf.py -v
```

Expected: collection fails because `scripts/update_backend_plan_pdf.py` does not exist.

- [ ] **Step 4: Implement the idempotent Arabic appendix builder**

Create `scripts/update_backend_plan_pdf.py` with these constants and functions:

```python
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import arabic_reshaper
from bidi.algorithm import get_display
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = PROJECT_ROOT / "output" / "pdf" / "ai_expert_system_backend_plan_ar.pdf"
ARIAL = Path("C:/Windows/Fonts/arial.ttf")
ARIAL_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")
APPENDIX_MARKER = "/Phase4Appendix"


def _rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def _register_fonts() -> None:
    if not ARIAL.is_file() or not ARIAL_BOLD.is_file():
        raise FileNotFoundError("Arial Arabic fonts were not found in C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("PlanArabic", ARIAL))
    pdfmetrics.registerFont(TTFont("PlanArabicBold", ARIAL_BOLD))


def _draw_appendix(path: Path) -> None:
    _register_fonts()
    document = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    document.setFillColor(HexColor("#172033"))
    document.rect(0, 0, width, height, fill=1, stroke=0)
    document.setFillColor(HexColor("#67E8F9"))
    document.setFont("PlanArabicBold", 18)
    document.drawRightString(
        width - 48,
        height - 68,
        _rtl("ملحق تنفيذ المرحلة الرابعة - الترتيب والتفسير"),
    )

    arabic_lines = [
        "تم تنفيذ الترتيب خارج محرك CLIPS لضمان نتيجة مستقلة عن ترتيب الأجندة.",
        "تحسم الدرجة الأعلى الترتيب، ثم يحسم معرف الأداة التعادل تصاعديا.",
        "يبنى سبب الترشيح من تأثيرات القواعد التي اشتغلت فعليا ومصادرها الموثقة.",
        "يظهر أقوى عامل إيجابي وأقوى عامل سلبي ولا يتم اختلاق أي قدرة أو مقياس.",
        "لا تستخدم بيانات الاختبار المعياري لحسم التعادل قبل اعتماد سياسة تطبيع مستقلة.",
    ]
    document.setFont("PlanArabic", 12)
    document.setFillColor(HexColor("#E5EEF8"))
    y = height - 120
    for line in arabic_lines:
        document.drawRightString(width - 48, y, _rtl(line))
        y -= 31

    document.setFillColor(HexColor("#0F172A"))
    document.roundRect(48, 310, width - 96, 180, 12, fill=1, stroke=0)
    document.setFillColor(HexColor("#A7F3D0"))
    document.setFont("Courier", 10)
    technical_lines = [
        "ranking_key = (-score, tool_id)",
        "service = RecommendationService",
        "reasons = fired RuleImpact.rationale values only",
        "Benchmarks do not break ties",
        "pytest -q: PASS",
        "compileall + pip check + strict schemas: PASS",
    ]
    y = 458
    for line in technical_lines:
        document.drawString(64, y, line)
        y -= 24

    document.setFillColor(HexColor("#94A3B8"))
    document.setFont("Helvetica", 8)
    document.drawString(48, 78, "Sources: Python Sorting HOWTO | CLIPS 6.4.2 | Tintarev & Masthoff 2012")
    document.drawCentredString(width / 2, 34, "6")
    document.save()


def build_updated_pdf(source_path: Path, output_path: Path) -> None:
    reader = PdfReader(source_path)
    has_appendix = (reader.metadata or {}).get(APPENDIX_MARKER) == "1"
    base_page_count = len(reader.pages) - 1 if has_appendix else len(reader.pages)

    with TemporaryDirectory() as temporary_directory:
        appendix_path = Path(temporary_directory) / "phase4-appendix.pdf"
        _draw_appendix(appendix_path)
        appendix = PdfReader(appendix_path)

        writer = PdfWriter()
        for page in reader.pages[:base_page_count]:
            writer.add_page(page)
        writer.add_page(appendix.pages[0])
        metadata = {
            str(key): str(value)
            for key, value in (reader.metadata or {}).items()
            if value is not None
        }
        metadata[APPENDIX_MARKER] = "1"
        writer.add_metadata(metadata)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="wb", delete=False, dir=output_path.parent, suffix=".pdf"
        ) as temporary_output:
            writer.write(temporary_output)
            temporary_output_path = Path(temporary_output.name)
        temporary_output_path.replace(output_path)


if __name__ == "__main__":
    build_updated_pdf(DEFAULT_PDF, DEFAULT_PDF)
```

- [ ] **Step 5: Mark the PDF operation once, then verify the builder in temporary files**

The test below is the first command that authors any PDF during this task. Run the PDF
skill marker exactly once immediately before it:

```powershell
& 'C:\Users\ST\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'C:\Users\ST\.codex\plugins\cache\openai-primary-runtime\pdf\26.818.11542\skills\pdf\container_tools\mark_artifact_operation_started.mjs' --operation-kind edit --expected-output-count 1 --output-format pdf
```

Then run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_backend_plan_pdf.py -v
```

Expected: the test passes twice against temporary outputs, both with exactly six pages and
one appendix marker.

- [ ] **Step 6: Run final code verification before recording PASS in the PDF**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app tests scripts
.venv\Scripts\python.exe -m pip check
git diff --check
```

Expected: all tests pass, compilation exits 0, dependency validation reports no broken
requirements, and the diff check is clean. Only after this evidence is fresh may the
appendix contain the two `PASS` lines.

- [ ] **Step 7: Update the tracked PDF without repeating the marker**

The artifact operation was marked exactly once in Step 5. Do not run the marker again.
Run:

```powershell
.venv\Scripts\python.exe scripts\update_backend_plan_pdf.py
```

Expected: the tracked PDF now contains six pages and metadata
`/Phase4Appendix = 1`.

- [ ] **Step 8: Render and visually inspect all final pages**

Create `tmp/pdfs/phase4` and render with the bundled Poppler binary:

```powershell
New-Item -ItemType Directory -Force -Path tmp\pdfs\phase4
& 'C:\Users\ST\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\override\pdftoppm.cmd' -png -r 144 output\pdf\ai_expert_system_backend_plan_ar.pdf tmp\pdfs\phase4\page
```

Open all six generated PNG files with the local image viewer. Require:

- readable Arabic shaping and right-to-left order;
- no clipped or overlapping text;
- intact original five pages;
- legible technical block and sources on page 6;
- consistent A4 dimensions, margins, colors, and page numbering.

If any defect exists, patch the builder, rerun it, rerender all pages, and repeat the visual
inspection. After a clean inspection, remove only `tmp/pdfs/phase4`.

- [ ] **Step 9: Reopen and structurally verify the final PDF**

Run:

```powershell
.venv\Scripts\python.exe -c "from pypdf import PdfReader; p='output/pdf/ai_expert_system_backend_plan_ar.pdf'; r=PdfReader(p); assert len(r.pages)==6; assert r.metadata.get('/Phase4Appendix')=='1'; text=r.pages[-1].extract_text(); assert '(-score, tool_id)' in text and 'RecommendationService' in text and 'pytest -q: PASS' in text; print('verified 6-page phase-4 PDF')"
```

Expected: `verified 6-page phase-4 PDF`.

- [ ] **Step 10: Commit Task 5**

```powershell
git add pyproject.toml scripts/update_backend_plan_pdf.py tests/test_backend_plan_pdf.py output/pdf/ai_expert_system_backend_plan_ar.pdf
git commit -m "docs: record verified phase-four behavior"
```

---

### Task 6: Final review and branch verification

**Files:**
- Review: every file changed from the phase-4 base commit

**Interfaces:**
- Preserves all public interfaces defined by Tasks 1-5
- Produces no new feature surface

- [ ] **Step 1: Review tests first, then implementation across five axes**

Review correctness, readability, architecture, security, and performance. Confirm:

- every realistic ranking mutation is caught by a test;
- no source collection order affects output;
- explanations map only to emitted effects and sourced impacts;
- no unbounded text or non-finite score can enter a recommendation;
- ranking remains `O(T log T)` and effect indexing is linear;
- PDF generation is idempotent and never deletes the original five pages;
- no dead code or unintended public symbol remains.

- [ ] **Step 2: Inspect graph impact and coverage**

Use the codebase-memory graph to search and trace `RecommendationService.recommend`,
`rank_tools`, and `build_reason` in both call directions. Run `check_index_coverage` for:

```text
app/recommendations/__init__.py
app/recommendations/errors.py
app/recommendations/ranking.py
app/recommendations/explanations.py
app/recommendations/service.py
tests/test_recommendations.py
scripts/update_backend_plan_pdf.py
tests/test_backend_plan_pdf.py
```

Read exact source for any stale, partial, skipped, or unknown coverage before relying on
graph findings.

- [ ] **Step 3: Run fresh completion verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app tests scripts
.venv\Scripts\python.exe -m pip check
git diff --check
git status --short --branch
```

Re-run the six-page structural PDF check from Task 5. Require a clean worktree after all
planned commits.

- [ ] **Step 4: Finish the development branch**

Use `superpowers:finishing-a-development-branch`. Present the local merge, push/PR, and
keep-as-is choices. Do not merge, push, remove the worktree, or delete the branch without
the user's explicit choice.
