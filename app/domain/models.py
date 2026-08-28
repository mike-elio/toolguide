from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)


Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000),
]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Language(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class LocalizedText(DomainModel):
    ar: NonEmptyText
    en: NonEmptyText

    def for_language(self, language: Language) -> str:
        return self.ar if language is Language.ARABIC else self.en


class StageId(StrEnum):
    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"


class DomainId(StrEnum):
    SOFTWARE = "software"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    CYBERSECURITY = "cybersecurity"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_TEXT = "short_text"
    BOOLEAN = "boolean"


class SourceKind(StrEnum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    OFFICIAL_REPOSITORY = "official_repository"
    PRIMARY_RESEARCH = "primary_research"
    PEER_REVIEWED_RESEARCH = "peer_reviewed_research"
    PUBLISHED_BENCHMARK = "published_benchmark"
    VENDOR_DOCUMENTATION = "vendor_documentation"
    PRACTITIONER_REPORT = "practitioner_report"


class Stage(DomainModel):
    id: StageId
    name: LocalizedText


class Tool(DomainModel):
    id: Identifier
    name: LocalizedText
    description: LocalizedText
    stages: list[StageId] = Field(min_length=1, max_length=3)
    domain: DomainId | None = None
    best_for: LocalizedText | None = None
    limitations: list[LocalizedText] = Field(default_factory=list, max_length=4)
    source_url: HttpUrl | None = None
    reviewed_at: date | None = None

    @model_validator(mode="after")
    def validate_unique_stages(self) -> Self:
        if len(self.stages) != len(set(self.stages)):
            raise ValueError("stages must be unique")
        return self


class AnswerOption(DomainModel):
    id: Identifier
    label: LocalizedText
    value: float = Field(ge=-1.0, le=1.0, allow_inf_nan=False)


class TextIntent(DomainModel):
    id: Identifier
    label: LocalizedText
    value: float = Field(ge=-1.0, le=1.0, allow_inf_nan=False)
    aliases: dict[Language, list[NonEmptyText]]


class Question(DomainModel):
    id: Identifier
    stage: StageId
    domain: DomainId | None = None
    dimension: Identifier | None = None
    prompt: LocalizedText
    type: QuestionType
    importance: float = Field(gt=0.0, le=1.0, allow_inf_nan=False)
    options: list[AnswerOption] = Field(default_factory=list)
    text_intents: list[TextIntent] = Field(default_factory=list)
    sources: list[EvaluationSource] = Field(default_factory=list)
    reviewed_at: date | None = None

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option ids must be unique")
        intent_ids = [intent.id for intent in self.text_intents]
        if len(intent_ids) != len(set(intent_ids)):
            raise ValueError("text intent ids must be unique")

        choice_types = {
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.BOOLEAN,
        }
        if self.type in choice_types and len(self.options) < 2:
            raise ValueError("choice questions require at least two options")
        if self.type in choice_types and self.text_intents:
            raise ValueError("choice questions must not define text intents")
        if self.type is QuestionType.SHORT_TEXT and self.options:
            raise ValueError("short-text questions must not define options")
        if self.type is QuestionType.SHORT_TEXT and len(self.text_intents) < 2:
            raise ValueError("short-text questions require at least two text intents")
        return self


class EvaluationSource(DomainModel):
    id: Identifier
    name: LocalizedText
    publisher: LocalizedText
    kind: SourceKind
    url: HttpUrl
    published_at: date | None = None
    collected_at: date


class RuleImpact(DomainModel):
    tool_id: Identifier
    weight: float = Field(ge=-1.0, le=1.0, allow_inf_nan=False)
    rationale: LocalizedText
    sources: list[EvaluationSource] = Field(min_length=1)

    @field_validator("weight")
    @classmethod
    def validate_nonzero_weight(cls, value: float) -> float:
        if value == 0.0:
            raise ValueError("rule impact weight must not be zero")
        return value

    @model_validator(mode="after")
    def validate_unique_sources(self) -> Self:
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")
        return self


class Rule(DomainModel):
    id: Identifier
    question_id: Identifier
    answer_option_id: Identifier
    impacts: list[RuleImpact] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_tool_impacts(self) -> Self:
        tool_ids = [impact.tool_id for impact in self.impacts]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("tool impacts must be unique")
        return self


class Benchmark(DomainModel):
    id: Identifier
    tool_id: Identifier
    metric: Identifier
    value: float = Field(allow_inf_nan=False)
    unit: Identifier | None = None
    sources: list[EvaluationSource] = Field(min_length=1)


class Recommendation(DomainModel):
    tool_id: Identifier
    tool_name: NonEmptyText
    reason: NonEmptyText


class RecommendationResult(DomainModel):
    recommendations: list[Recommendation] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_unique_tools(self) -> Self:
        tool_ids = [recommendation.tool_id for recommendation in self.recommendations]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("recommended tools must be unique")
        return self
