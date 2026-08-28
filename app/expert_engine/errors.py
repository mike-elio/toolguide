class ExpertEngineError(Exception):
    """Base error for the expert-engine boundary."""


class KnowledgeValidationError(ExpertEngineError):
    """Raised when domain knowledge or answers are internally inconsistent."""


class InferenceBuildError(ExpertEngineError):
    """Raised when CLIPS cannot build the generated knowledge program."""


class InferenceExecutionError(ExpertEngineError):
    """Raised when CLIPS fails while executing an inference request."""


class InferenceLimitError(InferenceExecutionError):
    """Raised when inference reaches its firing limit before completion."""
