import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

from app.domain.models import DomainModel, Identifier, Language
from app.expert_engine import AnswerSelection
from app.knowledge import KnowledgeSnapshot
from app.text_intent.normalization import normalize_text


DatasetText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class DatasetSplit(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    ACCEPTANCE = "acceptance"


class DatasetLoadError(RuntimeError):
    """Safe error for invalid JSONL text-intent data."""


class TextIntentRow(DomainModel):
    id: Identifier
    language: Language
    question_id: Identifier
    intent_id: Identifier
    text: DatasetText
    split: DatasetSplit
    provenance: DatasetText
    template_family: Identifier
    supporting_answers: list[AnswerSelection] | None = None
    expected_tool_ids: list[Identifier] | None = None

    @model_validator(mode="after")
    def validate_acceptance_fields(self) -> Self:
        if self.split is DatasetSplit.ACCEPTANCE:
            if not self.supporting_answers or not self.expected_tool_ids:
                raise ValueError("acceptance rows require complete request expectations")
            if len(self.expected_tool_ids) != 3:
                raise ValueError("acceptance rows require exactly three expected tools")
            if len(self.expected_tool_ids) != len(set(self.expected_tool_ids)):
                raise ValueError("expected tool ids must be unique")
        elif self.supporting_answers is not None or self.expected_tool_ids is not None:
            raise ValueError("only acceptance rows may define request expectations")
        return self


class DatasetAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    counts: dict[str, dict[str, int]]
    dataset_sha256: str
    violations: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.violations


DatasetPaths = Mapping[Language, Mapping[DatasetSplit, Path]]


def default_dataset_paths() -> dict[Language, dict[DatasetSplit, Path]]:
    root = Path(__file__).resolve().parents[2] / "data" / "text_intent"
    return {
        language: {
            split: root / f"{split.value}.{language.value}.jsonl"
            for split in DatasetSplit
        }
        for language in Language
    }


def load_text_intent_rows(path: Path) -> tuple[TextIntentRow, ...]:
    path = Path(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DatasetLoadError(f"cannot read dataset file: {path}") from error
    rows: list[TextIntentRow] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            rows.append(TextIntentRow.model_validate(payload))
        except (json.JSONDecodeError, ValidationError) as error:
            raise DatasetLoadError(
                f"invalid dataset row at {path}:{line_number}"
            ) from error
    return tuple(rows)


def _dataset_hash(paths: DatasetPaths) -> str:
    digest = hashlib.sha256()
    for language in sorted(paths, key=lambda item: item.value):
        for split in sorted(paths[language], key=lambda item: item.value):
            path = paths[language][split]
            digest.update(language.value.encode("ascii"))
            digest.update(split.value.encode("ascii"))
            try:
                digest.update(path.read_bytes())
            except OSError:
                digest.update(b"<missing>")
    return digest.hexdigest().upper()


def audit_text_intent_splits(
    paths: DatasetPaths, knowledge: KnowledgeSnapshot
) -> DatasetAudit:
    violations: list[str] = []
    counts = {
        language.value: {split.value: 0 for split in DatasetSplit}
        for language in Language
    }
    rows: list[TextIntentRow] = []
    for language, split_paths in paths.items():
        for split, path in split_paths.items():
            try:
                loaded = load_text_intent_rows(path)
            except DatasetLoadError as error:
                violations.append(str(error))
                continue
            counts[language.value][split.value] += len(loaded)
            for item in loaded:
                if item.language is not language or item.split is not split:
                    violations.append(f"dataset path identity mismatch: {item.id}")
                rows.append(item)

    row_ids = Counter(item.id for item in rows)
    for row_id, count in sorted(row_ids.items()):
        if count > 1:
            violations.append(f"duplicate row id: {row_id}")

    intents_by_question = {
        question.id: {intent.id for intent in question.text_intents}
        for question in knowledge.questions
        if question.text_intents
    }
    for item in rows:
        if item.intent_id not in intents_by_question.get(item.question_id, set()):
            violations.append(
                f"unknown question/intent pair: {item.question_id}/{item.intent_id}"
            )

    text_splits: defaultdict[tuple[Language, str], set[DatasetSplit]] = defaultdict(set)
    family_splits: defaultdict[tuple[Language, str], set[DatasetSplit]] = defaultdict(set)
    for item in rows:
        text_splits[(item.language, normalize_text(item.text, item.language))].add(
            item.split
        )
        family_splits[(item.language, item.template_family)].add(item.split)
    for (language, normalized), splits in text_splits.items():
        if len(splits) > 1:
            violations.append(
                f"normalized text crosses splits: {language.value}/{normalized[:32]}"
            )
    for (language, family), splits in family_splits.items():
        if len(splits) > 1:
            violations.append(
                f"template family crosses splits: {language.value}/{family}"
            )

    aliases = {
        (language, question.id, normalize_text(alias, language))
        for question in knowledge.questions
        for intent in question.text_intents
        for language, values in intent.aliases.items()
        for alias in values
    }
    for item in rows:
        if item.split is DatasetSplit.ACCEPTANCE and (
            item.language,
            item.question_id,
            normalize_text(item.text, item.language),
        ) in aliases:
            violations.append(f"acceptance text duplicates an alias: {item.id}")

    expected_counts = {"train": 320, "calibration": 80, "acceptance": 100}
    for language in Language:
        if counts[language.value] != expected_counts:
            violations.append(
                f"dataset counts invalid for {language.value}: {counts[language.value]}"
            )

    label_counts: defaultdict[tuple[Language, DatasetSplit, str, str], int] = defaultdict(int)
    for item in rows:
        label_counts[(item.language, item.split, item.question_id, item.intent_id)] += 1
    for language in Language:
        for question_id, intent_ids in intents_by_question.items():
            for intent_id in intent_ids:
                if label_counts[(language, DatasetSplit.TRAIN, question_id, intent_id)] < 20:
                    violations.append(
                        f"training label has fewer than 20 rows: {language.value}/{question_id}/{intent_id}"
                    )
                if label_counts[(language, DatasetSplit.CALIBRATION, question_id, intent_id)] < 5:
                    violations.append(
                        f"calibration label has fewer than 5 rows: {language.value}/{question_id}/{intent_id}"
                    )

            acceptance_counts = sorted(
                label_counts[
                    (language, DatasetSplit.ACCEPTANCE, question_id, intent_id)
                ]
                for intent_id in intent_ids
            )
            if acceptance_counts != [6, 6, 6, 7]:
                violations.append(
                    f"acceptance intent distribution invalid: {language.value}/{question_id}/{acceptance_counts}"
                )

    return DatasetAudit(
        counts=counts,
        dataset_sha256=_dataset_hash(paths),
        violations=tuple(violations),
    )
