from __future__ import annotations

from enum import StrEnum

from pydantic import Field, HttpUrl

from app.domain.models import (
    AnswerOption,
    DomainModel,
    Identifier,
    NonEmptyText,
    Question,
)
from app.questionnaire.eligibility import EligibilityDecision, NoMatchAlternative


class QuestionnaireStatus(StrEnum):
    QUESTION = "question"
    CLARIFICATION = "clarification"
    COMPLETE = "complete"
    NO_MATCH = "no_match"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuestionnaireRecommendation(DomainModel):
    tool_id: Identifier
    tool_name: NonEmptyText
    match_percent: int = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    reasons: list[NonEmptyText] = Field(min_length=1, max_length=3)
    limitations: list[NonEmptyText] = Field(min_length=1, max_length=2)
    source_url: HttpUrl
    matching_setup_id: str | None = None


class QuestionnaireOutcome(DomainModel):
    status: QuestionnaireStatus
    answered_count: int = Field(ge=0, le=10)
    eligible_count: int = Field(default=0, ge=0)
    unknown_evidence_count: int = Field(default=0, ge=0)
    excluded_tools: list[EligibilityDecision] = Field(default_factory=list)
    alternatives: list[NoMatchAlternative] = Field(default_factory=list, max_length=3)
    knowledge_version: str = ""
    question: Question | None = None
    clarification_options: list[AnswerOption] = Field(default_factory=list)
    recommendations: list[QuestionnaireRecommendation] = Field(
        default_factory=list, max_length=3
    )


class QuestionnaireHistoryError(ValueError):
    """The submitted stateless history is inconsistent with its pool."""
