class RecommendationError(Exception):
    """Base error for recommendation ranking and explanation."""


class InsufficientToolsError(RecommendationError):
    """Raised when fewer than three tools are available."""


class RecommendationConsistencyError(RecommendationError):
    """Raised when inference output cannot be reconciled with domain knowledge."""
