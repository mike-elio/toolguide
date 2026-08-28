from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.models import (
    AnswerOption,
    Benchmark,
    DomainId,
    EvaluationSource,
    Language,
    LocalizedText,
    Question,
    QuestionType,
    Recommendation,
    RecommendationResult,
    Rule,
    RuleImpact,
    SourceKind,
    Stage,
    StageId,
    TextIntent,
    Tool,
)


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(ar=ar or en, en=en)


def evaluation_source(source_id: str = "official-docs") -> EvaluationSource:
    return EvaluationSource(
        id=source_id,
        name=localized("Official documentation"),
        publisher=localized("Example Foundation"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url=f"https://example.com/sources/{source_id}",
        published_at=date(2026, 8, 1),
        collected_at=date(2026, 8, 23),
    )


def rule_impact(tool_id: str = "tool-a", weight: float = 0.75) -> RuleImpact:
    return RuleImpact(
        tool_id=tool_id,
        weight=weight,
        rationale=localized("The cited source supports this rule impact."),
        sources=[evaluation_source()],
    )


def test_localized_text_requires_both_languages() -> None:
    with pytest.raises(ValidationError):
        LocalizedText(ar="تحليل")


def test_localized_text_projects_only_the_requested_language() -> None:
    text = LocalizedText(ar="تحليل", en="Analysis")

    assert text.for_language(Language.ARABIC) == "تحليل"
    assert text.for_language(Language.ENGLISH) == "Analysis"


def test_short_text_question_requires_at_least_two_text_intents() -> None:
    with pytest.raises(ValidationError, match="at least two text intents"):
        Question(
            id="analysis-q4",
            stage=StageId.ANALYSIS,
            prompt=LocalizedText(ar="صف المهمة", en="Describe the task"),
            type=QuestionType.SHORT_TEXT,
            importance=0.8,
            text_intents=[
                TextIntent(
                    id="research",
                    label=LocalizedText(ar="بحث", en="Research"),
                    value=1.0,
                    aliases={
                        Language.ARABIC: ["بحث"],
                        Language.ENGLISH: ["research"],
                    },
                )
            ],
        )


def test_domain_contracts_accept_a_complete_knowledge_slice() -> None:
    stage = Stage(id=StageId.ANALYSIS, name=localized("Analysis", "تحليل"))
    tool = Tool(
        id="tool-a",
        name=localized("Tool A"),
        description=localized("Analyzes requirements."),
        stages=[StageId.ANALYSIS],
    )
    option = AnswerOption(id="yes", label=localized("Yes"), value=1.0)
    question = Question(
        id="analysis-q1",
        stage=StageId.ANALYSIS,
        prompt=localized("Do you need requirements analysis?"),
        type=QuestionType.SINGLE_CHOICE,
        importance=0.8,
        options=[
            option,
            AnswerOption(id="no", label=localized("No"), value=-1.0),
        ],
    )
    rule = Rule(
        id="analysis-q1-yes",
        question_id=question.id,
        answer_option_id=option.id,
        impacts=[rule_impact(tool.id)],
    )
    source = EvaluationSource(
        id="vendor-evaluation",
        name=localized("Vendor evaluation"),
        publisher=localized("Tool A"),
        kind=SourceKind.VENDOR_DOCUMENTATION,
        url="https://example.com/evaluations/tool-a",
        published_at=None,
        collected_at=date(2026, 8, 23),
    )
    benchmark = Benchmark(
        id="tool-a-quality",
        tool_id=tool.id,
        metric="quality",
        value=91.5,
        unit="percent",
        sources=[source],
    )
    result = RecommendationResult(
        recommendations=[
            Recommendation(tool_id="tool-a", tool_name="Tool A", reason="Best fit."),
            Recommendation(tool_id="tool-b", tool_name="Tool B", reason="Fast setup."),
            Recommendation(tool_id="tool-c", tool_name="Tool C", reason="Strong tests."),
        ]
    )

    assert stage.model_dump(mode="json") == {
        "id": "analysis",
        "name": {"ar": "تحليل", "en": "Analysis"},
    }
    assert question.options[0].value == 1.0
    assert rule.impacts[0].tool_id == tool.id
    assert benchmark.sources[0].collected_at == date(2026, 8, 23)
    assert [item.tool_id for item in result.recommendations] == [
        "tool-a",
        "tool-b",
        "tool-c",
    ]


def test_domain_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Stage.model_validate(
            {
                "id": "analysis",
                "name": {"ar": "تحليل", "en": "Analysis"},
                "unexpected": True,
            }
        )


def test_tool_rejects_duplicate_stages() -> None:
    with pytest.raises(ValidationError, match="stages must be unique"):
        Tool(
            id="tool-a",
            name=localized("Tool A"),
            description=localized("Analyzes requirements."),
            stages=[StageId.ANALYSIS, StageId.ANALYSIS],
        )


def test_adaptive_tool_metadata_is_strict_and_localized() -> None:
    tool = Tool(
        id="tool-a",
        name=localized("Tool A"),
        description=localized("Analyzes requirements."),
        stages=[StageId.ANALYSIS],
        domain=DomainId.SOFTWARE,
        best_for=localized("Repository analysis."),
        limitations=[localized("Requires cloud access.")],
        source_url="https://example.com/tool-a",
        reviewed_at=date(2026, 8, 28),
    )

    assert tool.domain is DomainId.SOFTWARE
    assert tool.best_for.for_language(Language.ENGLISH) == "Repository analysis."
    assert tool.limitations[0].for_language(Language.ENGLISH) == (
        "Requires cloud access."
    )


def test_adaptive_question_carries_decision_evidence() -> None:
    question = Question(
        id="analysis-software-scope",
        stage=StageId.ANALYSIS,
        domain=DomainId.SOFTWARE,
        dimension="scope",
        prompt=localized("What scope must be analyzed?"),
        type=QuestionType.SINGLE_CHOICE,
        importance=0.8,
        options=[
            AnswerOption(id="repository", label=localized("Repository"), value=1.0),
            AnswerOption(id="web", label=localized("Web"), value=1.0),
        ],
        sources=[evaluation_source()],
        reviewed_at=date(2026, 8, 28),
    )

    assert question.domain is DomainId.SOFTWARE
    assert question.dimension == "scope"
    assert question.sources[0].id == "official-docs"


def test_signed_rule_impacts_accept_conflicts_but_reject_zero() -> None:
    assert rule_impact(weight=-0.5).weight == -0.5
    with pytest.raises(ValidationError):
        rule_impact(weight=0.0)


@pytest.mark.parametrize(
    "question_type",
    [
        QuestionType.SINGLE_CHOICE,
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.BOOLEAN,
    ],
)
def test_choice_question_requires_at_least_two_options(
    question_type: QuestionType,
) -> None:
    with pytest.raises(ValidationError, match="at least two options"):
        Question(
            id="analysis-q1",
            stage=StageId.ANALYSIS,
            prompt=localized("Choose a workflow."),
            type=question_type,
            importance=0.8,
            options=[
                AnswerOption(id="one", label=localized("One"), value=1.0)
            ],
        )


def test_short_text_question_rejects_options() -> None:
    with pytest.raises(ValidationError, match="must not define options"):
        Question(
            id="analysis-q2",
            stage=StageId.ANALYSIS,
            prompt=localized("Describe the workflow."),
            type=QuestionType.SHORT_TEXT,
            importance=0.8,
            options=[
                AnswerOption(id="one", label=localized("One"), value=1.0)
            ],
        )


def test_question_rejects_duplicate_option_ids() -> None:
    with pytest.raises(ValidationError, match="option ids must be unique"):
        Question(
            id="analysis-q1",
            stage=StageId.ANALYSIS,
            prompt=localized("Choose a workflow."),
            type=QuestionType.SINGLE_CHOICE,
            importance=0.8,
            options=[
                AnswerOption(id="same", label=localized("One"), value=1.0),
                AnswerOption(id="same", label=localized("Two"), value=-1.0),
            ],
        )


def test_rule_rejects_duplicate_tool_impacts() -> None:
    with pytest.raises(ValidationError, match="tool impacts must be unique"):
        Rule(
            id="analysis-q1-yes",
            question_id="analysis-q1",
            answer_option_id="yes",
            impacts=[
                rule_impact(weight=0.5),
                rule_impact(weight=0.8),
            ],
        )


def test_rule_impact_requires_a_rationale_and_source() -> None:
    with pytest.raises(ValidationError):
        RuleImpact(tool_id="tool-a", weight=0.75)


def test_rule_impact_rejects_duplicate_source_ids() -> None:
    with pytest.raises(ValidationError, match="source ids must be unique"):
        RuleImpact(
            tool_id="tool-a",
            weight=0.75,
            rationale=localized("The cited sources support this rule impact."),
            sources=[evaluation_source(), evaluation_source()],
        )


def test_recommendation_result_rejects_duplicate_tools() -> None:
    with pytest.raises(ValidationError, match="recommended tools must be unique"):
        RecommendationResult(
            recommendations=[
                Recommendation(tool_id="tool-a", tool_name="Tool A", reason="Best fit."),
                Recommendation(tool_id="tool-a", tool_name="Tool A", reason="Fast setup."),
                Recommendation(tool_id="tool-c", tool_name="Tool C", reason="Strong tests."),
            ]
        )


@pytest.mark.parametrize(
    "invalid_model",
    [
        lambda: AnswerOption(id="yes", label=localized("Yes"), value=1.1),
        lambda: Question(
            id="analysis-q1",
            stage=StageId.ANALYSIS,
            prompt=localized("Choose a workflow."),
            type=QuestionType.SINGLE_CHOICE,
            importance=0.0,
            options=[
                AnswerOption(id="one", label=localized("One"), value=1.0),
                AnswerOption(id="two", label=localized("Two"), value=-1.0),
            ],
        ),
        lambda: rule_impact(weight=0.0),
    ],
    ids=["answer-value", "question-importance", "rule-weight"],
)
def test_scoring_factors_are_bounded(invalid_model) -> None:
    with pytest.raises(ValidationError):
        invalid_model()


@pytest.mark.parametrize(
    "invalid_model",
    [
        lambda: Tool(
            id="tool-a",
            name=localized("Tool A"),
            description=localized("Analyzes requirements."),
            stages=[],
        ),
        lambda: Tool(
            id="tool-a",
            name=localized("Tool A"),
            description=localized("Analyzes requirements."),
            stages=[
                StageId.ANALYSIS,
                StageId.DESIGN,
                StageId.IMPLEMENTATION,
                StageId.TESTING,
            ],
        ),
        lambda: Rule(
            id="analysis-q1-yes",
            question_id="analysis-q1",
            answer_option_id="yes",
            impacts=[],
        ),
        lambda: Benchmark(
            id="tool-a-quality",
            tool_id="tool-a",
            metric="quality",
            value=91.5,
            sources=[],
        ),
        lambda: RecommendationResult(
            recommendations=[
                Recommendation(tool_id="tool-a", tool_name="Tool A", reason="Best fit."),
                Recommendation(tool_id="tool-b", tool_name="Tool B", reason="Fast setup."),
            ]
        ),
    ],
    ids=[
        "tool-needs-a-stage",
        "tool-has-at-most-three-stages",
        "rule-needs-an-impact",
        "benchmark-needs-a-source",
        "result-needs-three-recommendations",
    ],
)
def test_contract_collections_enforce_their_size(invalid_model) -> None:
    with pytest.raises(ValidationError):
        invalid_model()


def test_identifier_rejects_a_blank_value() -> None:
    with pytest.raises(ValidationError):
        Tool(
            id="   ",
            name=localized("Tool A"),
            description=localized("Analyzes requirements."),
            stages=[StageId.ANALYSIS],
        )


def test_text_rejects_a_blank_value() -> None:
    with pytest.raises(ValidationError):
        Stage(id=StageId.ANALYSIS, name=localized("   "))


def test_benchmark_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError):
        Benchmark(
            id="tool-a-quality",
            tool_id="tool-a",
            metric="quality",
            value=float("inf"),
            sources=[
                EvaluationSource(
                    id="vendor-evaluation",
                    name=localized("Vendor evaluation"),
                    publisher=localized("Tool A"),
                    kind=SourceKind.VENDOR_DOCUMENTATION,
                    url="https://example.com/evaluations/tool-a",
                    published_at=None,
                    collected_at=date(2026, 8, 23),
                )
            ],
        )
