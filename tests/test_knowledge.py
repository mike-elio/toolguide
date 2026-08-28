from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.models import (
    AnswerOption,
    Benchmark,
    DomainId,
    EvaluationSource,
    LocalizedText,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    Stage,
    StageId,
    Tool,
)
from app.knowledge import KnowledgeSnapshot


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(ar=ar or en, en=en)


def evaluation_source() -> EvaluationSource:
    return EvaluationSource(
        id="source-1",
        name=localized("Official evaluation"),
        publisher=localized("Example Foundation"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://example.com/evaluation",
        collected_at=date(2026, 8, 24),
    )


def valid_snapshot() -> KnowledgeSnapshot:
    source = evaluation_source()
    return KnowledgeSnapshot(
        stages=[Stage(id=StageId.ANALYSIS, name=localized("Analysis"))],
        tools=[
            Tool(
                id="tool-a",
                name=localized("Tool A"),
                description=localized("A tool used by knowledge snapshot tests."),
                stages=[StageId.ANALYSIS],
            )
        ],
        questions=[
            Question(
                id="analysis-q1",
                stage=StageId.ANALYSIS,
                prompt=localized("Does the project need structured analysis?"),
                type=QuestionType.SINGLE_CHOICE,
                importance=0.8,
                options=[
                    AnswerOption(id="yes", label=localized("Yes"), value=1.0),
                    AnswerOption(id="no", label=localized("No"), value=-1.0),
                ],
            )
        ],
        rules=[
            Rule(
                id="rule-a",
                question_id="analysis-q1",
                answer_option_id="yes",
                impacts=[
                    RuleImpact(
                        tool_id="tool-a",
                        weight=0.75,
                        rationale=localized("Documented analysis fit."),
                        sources=[source],
                    )
                ],
            )
        ],
        benchmarks=[
            Benchmark(
                id="benchmark-a",
                tool_id="tool-a",
                metric="quality",
                value=0.9,
                sources=[source],
            )
        ],
    )


def test_empty_knowledge_snapshot_is_safe() -> None:
    snapshot = KnowledgeSnapshot()

    assert snapshot.stages == []
    assert snapshot.tools == []
    assert snapshot.questions == []
    assert snapshot.rules == []
    assert snapshot.benchmarks == []


def test_snapshot_accepts_a_referenced_knowledge_slice() -> None:
    snapshot = valid_snapshot()

    assert snapshot.rules[0].question_id == snapshot.questions[0].id
    assert snapshot.rules[0].impacts[0].tool_id == snapshot.tools[0].id


@pytest.mark.parametrize(
    "field",
    ["stages", "tools", "questions", "rules", "benchmarks"],
)
def test_snapshot_rejects_duplicate_ids(field: str) -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload[field].append(payload[field][0].copy())

    with pytest.raises(ValidationError, match=r"ids must be unique"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_stage_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["questions"][0]["stage"] = "testing"

    with pytest.raises(ValidationError, match="question references unknown stage"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_tool_stage_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["tools"][0]["stages"] = ["testing"]

    with pytest.raises(ValidationError, match="tool references unknown stage"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_question_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["rules"][0]["question_id"] = "missing-question"

    with pytest.raises(ValidationError, match="rule references unknown question"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_answer_option_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["rules"][0]["answer_option_id"] = "missing-option"

    with pytest.raises(ValidationError, match="rule references unknown answer option"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_tool_impact_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["rules"][0]["impacts"][0]["tool_id"] = "missing-tool"

    with pytest.raises(ValidationError, match="rule impact references unknown tool"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_rule_impacts_outside_the_question_pool() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["tools"][0].update(
        {
            "domain": DomainId.CYBERSECURITY.value,
            "best_for": localized("Security analysis").model_dump(mode="json"),
            "limitations": [localized("Requires security data").model_dump(mode="json")],
            "source_url": "https://example.com/tool-a",
            "reviewed_at": "2026-08-28",
        }
    )
    payload["questions"][0].update(
        {
            "domain": DomainId.SOFTWARE.value,
            "dimension": "scope",
            "sources": [evaluation_source().model_dump(mode="json")],
            "reviewed_at": "2026-08-28",
        }
    )

    with pytest.raises(ValidationError, match="crosses a stage/domain pool"):
        KnowledgeSnapshot.model_validate(payload)


def test_snapshot_rejects_unknown_benchmark_tool_reference() -> None:
    payload = valid_snapshot().model_dump(mode="json")
    payload["benchmarks"][0]["tool_id"] = "missing-tool"

    with pytest.raises(ValidationError, match="benchmark references unknown tool"):
        KnowledgeSnapshot.model_validate(payload)
