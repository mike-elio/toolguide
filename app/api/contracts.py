"""Request contracts owned by the HTTP API layer."""

from typing import Self

from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.domain.models import DomainId, DomainModel, Identifier, Language, StageId


ShortAnswerText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class SubmittedAnswer(DomainModel):
    question_id: Identifier
    option_ids: list[Identifier] | None = Field(default=None, min_length=1)
    text: ShortAnswerText | None = None

    @model_validator(mode="after")
    def validate_representation(self) -> Self:
        if (self.option_ids is None) == (self.text is None):
            raise ValueError("exactly one answer representation is required")
        if self.option_ids is not None and len(self.option_ids) != len(
            set(self.option_ids)
        ):
            raise ValueError("option ids must be unique")
        return self


class RecommendationRequest(DomainModel):
    language: Language
    answers: list[SubmittedAnswer] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_question_ids(self) -> Self:
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question ids must be unique")
        return self


SessionSeed = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class QuestionnaireRequest(DomainModel):
    language: Language
    stage: StageId
    domain: DomainId
    session_seed: SessionSeed
    asked_question_ids: list[Identifier] = Field(default_factory=list, max_length=10)
    answers: list[SubmittedAnswer] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_history_shape(self) -> Self:
        if len(self.asked_question_ids) != len(set(self.asked_question_ids)):
            raise ValueError("asked question ids must be unique")
        return self
