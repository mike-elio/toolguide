from datetime import date

import pytest

from app.domain.models import (
    AnswerOption,
    EvaluationSource,
    Language,
    LocalizedText,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    StageId,
    Tool,
)
from app.expert_engine import AnswerSelection, InferenceResult, ScoreEffect
from app.recommendations.errors import (
    InsufficientToolsError,
    RecommendationConsistencyError,
)
from app.recommendations.explanations import MAX_REASON_LENGTH, build_reason
from app.recommendations.ranking import RankedTool, rank_tools
from app.recommendations.service import RecommendationService


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(ar=ar or en, en=en)


def tool(tool_id: str) -> Tool:
    return Tool(
        id=tool_id,
        name=localized(f"Tool {tool_id}"),
        description=localized("A recommendation test tool."),
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


def source() -> EvaluationSource:
    return EvaluationSource(
        id="official-docs",
        name=localized("Official documentation"),
        publisher=localized("Example Foundation"),
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
                rationale=localized(rationale),
                sources=[source()],
            )
        ],
    )


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

    assert build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    ) == "Strong support."


def test_build_reason_replaces_generated_ids_with_readable_answer_context() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.7,
        effects=(ScoreEffect(tool_id="tool-a", rule_id="generic", value=0.7),),
    )
    rules = [
        sourced_rule(
            rule_id="generic",
            tool_id="tool-a",
            rationale="Official sources support Tool tool-a for yes workflows.",
        )
    ]

    reason = build_reason(
        ranked_tool=ranked_tool,
        rules=rules,
        questions=[question()],
        language=Language.ENGLISH,
    )

    assert reason == (
        'Tool tool-a fits your answer "Yes" to '
        '"Do you need this workflow capability?"; official sources in the '
        "knowledge base support this match."
    )
    assert "yes workflows" not in reason


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

    assert build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    ) == (
        "Strong workflow fit. Countervailing factor: Higher setup cost."
    )


def test_build_reason_is_transparent_when_no_rule_changed_the_score() -> None:
    ranked_tool = RankedTool(tool=tool("tool-a"), score=0.0, effects=())

    assert build_reason(
        ranked_tool=ranked_tool, rules=[], language=Language.ENGLISH
    ) == (
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

    assert build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    ) == (
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

    reason = build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    )

    assert len(reason) == MAX_REASON_LENGTH
    assert reason == long_rationale
    assert "Countervailing factor" not in reason


def test_build_reason_suppresses_only_the_strongest_duplicate_counterfactor() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.4,
        effects=(
            ScoreEffect(tool_id="tool-a", rule_id="positive", value=0.7),
            ScoreEffect(tool_id="tool-a", rule_id="duplicate-negative", value=-0.8),
            ScoreEffect(tool_id="tool-a", rule_id="distinct-negative", value=-0.2),
        ),
    )
    rules = [
        sourced_rule(
            rule_id="positive", tool_id="tool-a", rationale="Workflow fit."
        ),
        sourced_rule(
            rule_id="duplicate-negative",
            tool_id="tool-a",
            rationale="Workflow fit.",
        ),
        sourced_rule(
            rule_id="distinct-negative",
            tool_id="tool-a",
            rationale="Higher setup cost.",
        ),
    ]

    assert build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    ) == "Workflow fit."


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

    reason = build_reason(
        ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
    )

    assert len(reason) == MAX_REASON_LENGTH
    assert reason.endswith("…")


def test_build_reason_rejects_an_unmappable_effect() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.7,
        effects=(ScoreEffect(tool_id="tool-a", rule_id="missing", value=0.7),),
    )

    with pytest.raises(RecommendationConsistencyError, match="missing rule impact"):
        build_reason(
            ranked_tool=ranked_tool, rules=[], language=Language.ENGLISH
        )


def test_build_reason_rejects_an_effect_for_a_different_tool() -> None:
    ranked_tool = RankedTool(
        tool=tool("tool-a"),
        score=0.7,
        effects=(ScoreEffect(tool_id="tool-b", rule_id="positive", value=0.7),),
    )
    rules = [
        sourced_rule(
            rule_id="positive", tool_id="tool-b", rationale="Workflow fit."
        )
    ]

    with pytest.raises(RecommendationConsistencyError, match="missing rule impact"):
        build_reason(
            ranked_tool=ranked_tool, rules=rules, language=Language.ENGLISH
        )


def question() -> Question:
    return Question(
        id="analysis-q1",
        stage=StageId.ANALYSIS,
        prompt=localized("Do you need this workflow capability?"),
        type=QuestionType.SINGLE_CHOICE,
        importance=0.8,
        options=[
            AnswerOption(id="yes", label=localized("Yes"), value=1.0),
            AnswerOption(id="no", label=localized("No"), value=-1.0),
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
                rationale=localized(rationale),
                sources=[source()],
            )
        ],
    )


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
        language=Language.ENGLISH,
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
        language=Language.ENGLISH,
    )
    second = service.recommend(
        tools=list(reversed(tools)),
        questions=[question()],
        rules=list(reversed(rules)),
        answers=[AnswerSelection(question_id="analysis-q1", option_ids=["yes"])],
        language=Language.ENGLISH,
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
