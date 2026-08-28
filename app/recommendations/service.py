from collections.abc import Sequence
from typing import Protocol

from app.domain.models import (
    Language,
    Question,
    Recommendation,
    RecommendationResult,
    Rule,
    Tool,
)
from app.expert_engine import AnswerSelection, ClipspyAdapter, InferenceResult
from app.recommendations.explanations import build_reason
from app.recommendations.ranking import rank_tools


class InferenceEngine(Protocol):
    def infer(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
    ) -> InferenceResult:
        """Return deterministic raw inference output."""


class RecommendationService:
    def __init__(self, engine: InferenceEngine | None = None) -> None:
        self._engine = engine if engine is not None else ClipspyAdapter()

    def recommend(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
        language: Language,
    ) -> RecommendationResult:
        inference_result = self._engine.infer(
            tools=tools,
            questions=questions,
            rules=rules,
            answers=answers,
        )
        top_three = rank_tools(
            tools=tools,
            inference_result=inference_result,
        )[:3]
        return RecommendationResult(
            recommendations=[
                Recommendation(
                    tool_id=ranked.tool.id,
                    tool_name=ranked.tool.name.for_language(language),
                    reason=build_reason(
                        ranked_tool=ranked,
                        rules=rules,
                        questions=questions,
                        language=language,
                    ),
                )
                for ranked in top_three
            ]
        )
