import gzip
import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.models import (
    AnswerOption,
    Benchmark,
    EvaluationSource,
    Language,
    LocalizedText,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    Stage,
    StageId,
    TextIntent,
    Tool,
)
from app.knowledge import KnowledgeSnapshot
from app.knowledge.loader import (
    KnowledgeLoadError,
    audit_knowledge,
    default_knowledge_path,
    load_knowledge,
)


def localized(value: str) -> LocalizedText:
    return LocalizedText(ar=value, en=value)


def source(source_id: str) -> EvaluationSource:
    return EvaluationSource(
        id=source_id,
        name=localized(source_id),
        publisher=localized("publisher"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url=f"https://example.com/{source_id}",
        collected_at=date(2026, 8, 24),
    )


def audit_snapshot() -> KnowledgeSnapshot:
    stages = [Stage(id=stage, name=localized(stage.value)) for stage in StageId]
    tools = [
        Tool(
            id=f"{stage.value}-tool-{index}",
            name=localized(f"{stage.value} tool {index}"),
            description=localized("description"),
            stages=[stage],
        )
        for stage in StageId
        for index in range(10)
    ]
    questions: list[Question] = []
    rules: list[Rule] = []
    rule_index = 0
    for stage in StageId:
        question_types = [
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.SINGLE_CHOICE,
            QuestionType.SHORT_TEXT,
            QuestionType.BOOLEAN,
        ]
        for question_index, question_type in enumerate(question_types, start=1):
            question_id = f"{stage.value}-q{question_index}"
            if question_type is QuestionType.SHORT_TEXT:
                intents = [
                    TextIntent(
                        id=f"intent-{intent_index}",
                        label=localized(f"intent {intent_index}"),
                        value=1.0 if intent_index == 1 else 0.5,
                        aliases={
                            Language.ARABIC: [f"ar-{stage.value}-{intent_index}"],
                            Language.ENGLISH: [f"en-{stage.value}-{intent_index}"],
                        },
                    )
                    for intent_index in (1, 2)
                ]
                question = Question(
                    id=question_id,
                    stage=stage,
                    prompt=localized(question_id),
                    type=question_type,
                    importance=0.8,
                    text_intents=intents,
                )
                targets = [intent.id for intent in intents]
            else:
                options = [
                    AnswerOption(id="yes", label=localized("yes"), value=1.0),
                    AnswerOption(id="no", label=localized("no"), value=0.3),
                ]
                question = Question(
                    id=question_id,
                    stage=stage,
                    prompt=localized(question_id),
                    type=question_type,
                    importance=0.8,
                    options=options,
                )
                targets = [option.id for option in options]
            questions.append(question)
            for target in targets:
                evidence = [source("source-1")]
                if stage is StageId.IMPLEMENTATION:
                    evidence.append(source("source-2"))
                rules.append(
                    Rule(
                        id=f"rule-{rule_index}",
                        question_id=question_id,
                        answer_option_id=target,
                        impacts=[
                            RuleImpact(
                                tool_id=f"{stage.value}-tool-{(rule_index + offset) % 10}",
                                weight=0.5,
                                rationale=localized("documented fit"),
                                sources=evidence,
                            )
                            for offset in range(3)
                        ],
                    )
                )
                rule_index += 1
    benchmark_sources = [source(f"benchmark-source-{index}") for index in range(3)]
    return KnowledgeSnapshot(
        stages=stages,
        tools=tools,
        questions=questions,
        rules=rules,
        benchmarks=[
            Benchmark(
                id="model-evaluation",
                tool_id="analysis-tool-0",
                metric="macro-f1",
                value=0.9,
                sources=benchmark_sources,
            )
        ],
    )


def test_load_knowledge_reads_a_valid_utf8_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.json"
    path.write_text(
        json.dumps(audit_snapshot().model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    loaded = load_knowledge(path)

    assert loaded == audit_snapshot()


def test_load_knowledge_reads_a_valid_gzip_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.json.gz"
    with gzip.open(path, mode="wt", encoding="utf-8") as compressed:
        json.dump(
            audit_snapshot().model_dump(mode="json"),
            compressed,
            ensure_ascii=False,
        )

    loaded = load_knowledge(path)

    assert loaded == audit_snapshot()


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("{", "malformed JSON"),
        ('{"unexpected": true}', "invalid knowledge"),
        (
            '{"stages": [], "tools": [], "questions": [{"id": "q"}]}',
            "invalid knowledge",
        ),
    ],
)
def test_load_knowledge_wraps_invalid_content_without_echoing_it(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "private.json"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(KnowledgeLoadError, match=message) as caught:
        load_knowledge(path)

    assert str(path) in str(caught.value)
    assert contents not in str(caught.value)


def test_load_knowledge_reports_a_missing_path(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(KnowledgeLoadError, match="cannot read") as caught:
        load_knowledge(path)

    assert str(path) in str(caught.value)


def test_default_knowledge_path_is_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    path = default_knowledge_path()

    assert path.name == "adaptive.json.gz"
    assert path.parts[-3:] == ("data", "knowledge", "adaptive.json.gz")


def test_audit_knowledge_reports_exact_phase_six_counts() -> None:
    audit = audit_knowledge(audit_snapshot())

    assert audit.passed
    assert audit.stage_assignment_counts == {
        StageId.ANALYSIS: 10,
        StageId.DESIGN: 10,
        StageId.IMPLEMENTATION: 10,
        StageId.TESTING: 10,
    }
    assert audit.question_type_counts == {
        "choice": 12,
        "short_text": 4,
        "boolean": 4,
    }


def test_bundled_phase_six_knowledge_passes_the_structural_audit() -> None:
    audit = audit_knowledge(load_knowledge(default_knowledge_path()))

    assert audit.passed
    assert len(load_knowledge(default_knowledge_path()).tools) == 48
    assert set(audit.stage_domain_tool_counts.values()) == {4}
    assert set(audit.stage_domain_question_counts.values()) == {14}


def test_audit_knowledge_reports_independent_invariant_violations() -> None:
    snapshot = audit_snapshot()
    missing_rule = snapshot.model_copy(update={"rules": snapshot.rules[1:]})
    weak_benchmark = snapshot.model_copy(
        update={
            "benchmarks": [
                snapshot.benchmarks[0].model_copy(
                    update={"sources": [source("only-source")]}
                )
            ]
        }
    )
    implementation_rule = next(
        rule for rule in snapshot.rules if rule.question_id.startswith("implementation")
    )
    weak_impact = implementation_rule.impacts[0].model_copy(
        update={"sources": [source("only-source")]}
    )
    weak_rule = implementation_rule.model_copy(update={"impacts": [weak_impact]})
    weak_editor = snapshot.model_copy(
        update={
            "rules": [
                weak_rule if rule.id == weak_rule.id else rule
                for rule in snapshot.rules
            ]
        }
    )

    assert any("rule target" in item for item in audit_knowledge(missing_rule).violations)
    assert any(
        "model-evaluation" in item
        for item in audit_knowledge(weak_benchmark).violations
    )
    assert any("code-editor" in item for item in audit_knowledge(weak_editor).violations)


def test_audit_knowledge_requires_each_stage_mix_and_three_positive_impacts() -> None:
    snapshot = audit_snapshot()
    analysis_short = next(
        question
        for question in snapshot.questions
        if question.id == "analysis-q4"
    )
    design_boolean = next(
        question
        for question in snapshot.questions
        if question.id == "design-q5"
    )
    wrong_mix = snapshot.model_copy(
        update={
            "questions": [
                question.model_copy(update={"type": QuestionType.BOOLEAN})
                if question.id == analysis_short.id
                else question.model_copy(update={"type": QuestionType.SHORT_TEXT})
                if question.id == design_boolean.id
                else question
                for question in snapshot.questions
            ]
        }
    )
    sparse_rule = snapshot.rules[0].model_copy(
        update={"impacts": snapshot.rules[0].impacts[:2]}
    )
    sparse_snapshot = snapshot.model_copy(
        update={"rules": [sparse_rule, *snapshot.rules[1:]]}
    )

    assert any("question mix" in item for item in audit_knowledge(wrong_mix).violations)
    assert any(
        "three positive impacts" in item
        for item in audit_knowledge(sparse_snapshot).violations
    )


def test_audit_knowledge_rejects_invalid_constructed_stage_and_source_shapes() -> None:
    snapshot = audit_snapshot()
    four_stage_tool = snapshot.tools[0].model_copy(
        update={"stages": list(StageId)}
    )
    invalid_tool_snapshot = snapshot.model_copy(
        update={"tools": [four_stage_tool, *snapshot.tools[1:]]}
    )
    source_without_date = EvaluationSource.model_construct(
        id="missing-date",
        name=localized("missing date"),
        publisher=localized("publisher"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://example.com/missing-date",
        published_at=None,
    )
    invalid_impact = snapshot.rules[0].impacts[0].model_copy(
        update={"sources": [source_without_date]}
    )
    invalid_rule = snapshot.rules[0].model_copy(update={"impacts": [invalid_impact]})
    invalid_source_snapshot = snapshot.model_copy(
        update={"rules": [invalid_rule, *snapshot.rules[1:]]}
    )

    assert any(
        "four stages" in item
        for item in audit_knowledge(invalid_tool_snapshot).violations
    )
    assert any(
        "collected_at" in item
        for item in audit_knowledge(invalid_source_snapshot).violations
    )


def test_audit_cli_result_uses_a_nonzero_code_for_violations(tmp_path: Path) -> None:
    from scripts.audit_phase6 import run_audit

    path = tmp_path / "knowledge.json"
    path.write_text(
        json.dumps(KnowledgeSnapshot().model_dump(mode="json")),
        encoding="utf-8",
    )

    payload, exit_code = run_audit(path)

    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["violations"]


def test_adaptive_audit_skips_legacy_training_dataset_requirements() -> None:
    from scripts.audit_phase6 import run_audit

    payload, exit_code = run_audit(default_knowledge_path())

    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["datasets"] == {
        "passed": True,
        "skipped": True,
        "reason": "adaptive questionnaire uses curated aliases without training",
    }
