import gzip
import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.models import DomainId, QuestionType, StageId
from app.knowledge.models import KnowledgeSnapshot


class KnowledgeLoadError(RuntimeError):
    """Safe boundary error for a knowledge file that cannot be loaded."""


class KnowledgeAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_assignment_counts: dict[StageId, int]
    stage_question_counts: dict[StageId, int]
    question_type_counts: dict[str, int]
    stage_domain_tool_counts: dict[str, int] = Field(default_factory=dict)
    stage_domain_question_counts: dict[str, int] = Field(default_factory=dict)
    violations: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.violations


def default_knowledge_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "knowledge"
        / "adaptive.json.gz"
    )


def load_knowledge(path: Path) -> KnowledgeSnapshot:
    path = Path(path)
    try:
        if path.suffix == ".gz":
            with gzip.open(path, mode="rt", encoding="utf-8") as compressed:
                contents = compressed.read()
        else:
            contents = path.read_text(encoding="utf-8")
    except OSError as error:
        raise KnowledgeLoadError(f"cannot read knowledge file: {path}") from error

    try:
        payload = json.loads(contents)
    except json.JSONDecodeError as error:
        raise KnowledgeLoadError(f"malformed JSON in knowledge file: {path}") from error

    try:
        return KnowledgeSnapshot.model_validate(payload)
    except ValidationError as error:
        raise KnowledgeLoadError(
            f"invalid knowledge in {path} ({error.error_count()} validation errors)"
        ) from error


def audit_knowledge(snapshot: KnowledgeSnapshot) -> KnowledgeAudit:
    violations: list[str] = []
    adaptive = bool(snapshot.tools) and bool(snapshot.questions) and all(
        tool.domain is not None for tool in snapshot.tools
    ) and all(question.domain is not None for question in snapshot.questions)
    stage_assignment_counts = {stage: 0 for stage in StageId}
    for tool in snapshot.tools:
        if len(tool.stages) > 3:
            violations.append(f"tool appears in four stages: {tool.id}")
        for stage in tool.stages:
            stage_assignment_counts[stage] += 1
    expected_stage_tools = 12 if adaptive else 10
    for stage, count in stage_assignment_counts.items():
        if count != expected_stage_tools:
            violations.append(
                "stage assignment count must be "
                f"{expected_stage_tools}: {stage.value} has {count}"
            )

    stage_question_counter = Counter(question.stage for question in snapshot.questions)
    stage_question_counts = {
        stage: stage_question_counter.get(stage, 0) for stage in StageId
    }
    expected_stage_questions = 42 if adaptive else 5
    for stage, count in stage_question_counts.items():
        if count != expected_stage_questions:
            violations.append(
                "stage question count must be "
                f"{expected_stage_questions}: {stage.value} has {count}"
            )

    if not adaptive:
        for stage in StageId:
            stage_types = Counter(
                question.type
                for question in snapshot.questions
                if question.stage is stage
            )
            stage_mix = {
                "choice": sum(
                    stage_types[kind]
                    for kind in (
                        QuestionType.SINGLE_CHOICE,
                        QuestionType.MULTIPLE_CHOICE,
                    )
                ),
                "short_text": stage_types[QuestionType.SHORT_TEXT],
                "boolean": stage_types[QuestionType.BOOLEAN],
            }
            if stage_mix != {"choice": 3, "short_text": 1, "boolean": 1}:
                violations.append(
                    f"stage question mix must be 3/1/1: {stage.value} has {stage_mix}"
                )

    question_type_counts = {"choice": 0, "short_text": 0, "boolean": 0}
    for question in snapshot.questions:
        if question.type is QuestionType.SHORT_TEXT:
            question_type_counts["short_text"] += 1
        elif question.type is QuestionType.BOOLEAN:
            question_type_counts["boolean"] += 1
        else:
            question_type_counts["choice"] += 1
    expected_types = (
        {"choice": 156, "short_text": 12, "boolean": 0}
        if adaptive
        else {"choice": 12, "short_text": 4, "boolean": 4}
    )
    if question_type_counts != expected_types:
        violations.append(
            f"question type counts must be {expected_types}: got {question_type_counts}"
        )

    expected_rule_targets = {
        (question.id, target_id)
        for question in snapshot.questions
        for target_id in [
            *(option.id for option in question.options),
            *(intent.id for intent in question.text_intents),
        ]
    }
    actual_rule_targets = {
        (rule.question_id, rule.answer_option_id) for rule in snapshot.rules
    }
    for question_id, target_id in sorted(expected_rule_targets - actual_rule_targets):
        violations.append(f"missing rule target: {question_id}/{target_id}")

    questions_by_id = {question.id: question for question in snapshot.questions}
    for rule in snapshot.rules:
        question = questions_by_id.get(rule.question_id)
        if question is None:
            continue
        target_values = {
            item.id: item.value for item in [*question.options, *question.text_intents]
        }
        target_value = target_values.get(rule.answer_option_id)
        if adaptive:
            if len(rule.impacts) != 4:
                violations.append(f"adaptive rule requires four impacts: {rule.id}")
            if not any(impact.weight > 0 for impact in rule.impacts) or not any(
                impact.weight < 0 for impact in rule.impacts
            ):
                violations.append(
                    f"adaptive rule must differentiate positive and negative: {rule.id}"
                )
        elif target_value is not None and (
            target_value <= 0 or len(rule.impacts) < 3
        ):
            violations.append(
                f"rule target requires three positive impacts: {rule.id}"
            )

    tools_by_id = {tool.id: tool for tool in snapshot.tools}
    for rule in snapshot.rules:
        for impact in rule.impacts:
            for evidence in impact.sources:
                if getattr(evidence, "collected_at", None) is None:
                    violations.append(
                        f"source missing collected_at: {rule.id}/{evidence.id}"
                    )
            tool = tools_by_id.get(impact.tool_id)
            source_ids = {evidence.id for evidence in impact.sources}
            if (
                not adaptive
                and
                tool is not None
                and StageId.IMPLEMENTATION in tool.stages
                and len(source_ids) < 2
            ):
                violations.append(
                    f"code-editor evidence requires two sources: {rule.id}/{tool.id}"
                )

    for benchmark in snapshot.benchmarks:
        for evidence in benchmark.sources:
            if getattr(evidence, "collected_at", None) is None:
                violations.append(
                    f"source missing collected_at: {benchmark.id}/{evidence.id}"
                )
        if len({evidence.id for evidence in benchmark.sources}) < 3:
            violations.append(
                f"model-evaluation evidence requires three sources: {benchmark.id}"
            )

    stage_domain_tool_counts: dict[str, int] = {}
    stage_domain_question_counts: dict[str, int] = {}
    if adaptive:
        tool_cells = Counter(
            (tool.stages[0], tool.domain) for tool in snapshot.tools
        )
        question_cells = Counter(
            (question.stage, question.domain) for question in snapshot.questions
        )
        for stage in StageId:
            for domain in DomainId:
                key = f"{stage.value}/{domain.value}"
                tool_count = tool_cells[(stage, domain)]
                question_count = question_cells[(stage, domain)]
                stage_domain_tool_counts[key] = tool_count
                stage_domain_question_counts[key] = question_count
                if tool_count != 4:
                    violations.append(
                        f"stage/domain tool count must be 4: {key} has {tool_count}"
                    )
                if question_count != 14:
                    violations.append(
                        "stage/domain question count must be 14: "
                        f"{key} has {question_count}"
                    )
        for tool in snapshot.tools:
            if (
                tool.best_for is None
                or not tool.limitations
                or tool.source_url is None
                or tool.reviewed_at is None
            ):
                violations.append(f"adaptive tool metadata is incomplete: {tool.id}")
        for question in snapshot.questions:
            if (
                question.dimension is None
                or not question.sources
                or question.reviewed_at is None
            ):
                violations.append(
                    f"adaptive question evidence is incomplete: {question.id}"
                )

    return KnowledgeAudit(
        stage_assignment_counts=stage_assignment_counts,
        stage_question_counts=stage_question_counts,
        question_type_counts=question_type_counts,
        stage_domain_tool_counts=stage_domain_tool_counts,
        stage_domain_question_counts=stage_domain_question_counts,
        violations=tuple(violations),
    )
