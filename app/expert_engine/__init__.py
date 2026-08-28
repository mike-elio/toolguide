"""CLIPSpy expert-engine integration boundary."""

from app.expert_engine.clipspy_adapter import ClipspyAdapter
from app.expert_engine.errors import (
    ExpertEngineError,
    InferenceBuildError,
    InferenceExecutionError,
    InferenceLimitError,
    KnowledgeValidationError,
)
from app.expert_engine.models import AnswerSelection, InferenceResult, ScoreEffect

__all__ = [
    "AnswerSelection",
    "ClipspyAdapter",
    "ExpertEngineError",
    "InferenceBuildError",
    "InferenceExecutionError",
    "InferenceLimitError",
    "InferenceResult",
    "KnowledgeValidationError",
    "ScoreEffect",
]
