from pydantic import Field, HttpUrl

from app.domain.models import (
    DomainId,
    DomainModel,
    Identifier,
    NonEmptyText,
    QuestionType,
    StageId,
)
from app.questionnaire import ConfidenceLevel, QuestionnaireStatus


class StageResponse(DomainModel):
    id: StageId
    name: NonEmptyText


class DomainResponse(DomainModel):
    id: DomainId
    name: NonEmptyText


class AnswerOptionResponse(DomainModel):
    id: Identifier
    label: NonEmptyText
    value: float


class QuestionResponse(DomainModel):
    id: Identifier
    stage: StageId
    domain: DomainId | None = None
    prompt: NonEmptyText
    type: QuestionType
    importance: float
    options: list[AnswerOptionResponse] = Field(default_factory=list)


class ToolResponse(DomainModel):
    id: Identifier
    name: NonEmptyText
    description: NonEmptyText
    stages: list[StageId]


class RecommendationItemResponse(DomainModel):
    tool_id: Identifier
    tool_name: NonEmptyText
    reason: NonEmptyText


class RecommendationResponse(DomainModel):
    recommendations: list[RecommendationItemResponse] = Field(
        min_length=3, max_length=3
    )


class QuestionnaireRecommendationResponse(DomainModel):
    tool_id: Identifier
    tool_name: NonEmptyText
    match_percent: int
    confidence: ConfidenceLevel
    reasons: list[NonEmptyText]
    limitations: list[NonEmptyText]
    source_url: HttpUrl


class QuestionnaireResponse(DomainModel):
    status: QuestionnaireStatus
    answered_count: int
    minimum_questions: int = 6
    maximum_questions: int = 10
    question: QuestionResponse | None = None
    clarification_options: list[AnswerOptionResponse] = Field(default_factory=list)
    recommendations: list[QuestionnaireRecommendationResponse] = Field(
        default_factory=list, max_length=3
    )
