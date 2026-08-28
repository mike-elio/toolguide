from typing import Literal, Protocol

from pydantic import Field

from app.domain.models import DomainModel, Identifier, Language, Question


class TextIntentError(Exception):
    """Base error for safe short-text resolution failures."""


class InvalidAnswerRepresentationError(TextIntentError):
    """Raised when the submitted representation does not match the question."""


class UncertainTextIntentError(TextIntentError):
    """Raised when short text cannot be mapped safely to a canonical intent."""


class ModelUnavailableError(TextIntentError):
    """Raised when a requested local classifier artifact is unavailable."""


class AliasConflictError(TextIntentError):
    """Raised when one normalized alias maps to multiple intents."""


class IntentPrediction(DomainModel):
    question_id: Identifier
    intent_id: Identifier
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    margin: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    source: Literal["alias", "model"]


class TextIntentClassifier(Protocol):
    def predict(
        self, language: Language, question: Question, text: str
    ) -> IntentPrediction:
        """Predict one canonical intent for a question-scoped short answer."""
