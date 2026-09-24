"""One ranking pipeline for normal sessions and counterfactual scenarios."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import Question, Rule, Tool
from app.domain.tool_profiles import HardConstraints
from app.expert_engine import AnswerSelection, ClipspyAdapter, InferenceResult
from app.questionnaire.eligibility import EligibilityDecision, evaluate_eligibility
from app.recommendations.ranking import RankedTool, rank_tools


@dataclass(frozen=True)
class PoolEvaluation:
    ranked_eligible: tuple[RankedTool, ...]
    ranked_all: tuple[RankedTool, ...]
    inference: InferenceResult
    eligibility: tuple[EligibilityDecision, ...]


def evaluate_pool(*, tools: Sequence[Tool], questions: Sequence[Question],
                  rules: Sequence[Rule], answers: Sequence[AnswerSelection],
                  constraints: HardConstraints, engine: ClipspyAdapter) -> PoolEvaluation:
    # Keep the full pool in CLIPS: rules can reference an excluded tool.
    inference = engine.infer(tools=tools, questions=questions, rules=rules, answers=answers)
    eligibility = tuple(evaluate_eligibility(tool, constraints) for tool in tools)
    eligible_ids = {item.tool_id for item in eligibility if item.eligible}
    ranked = rank_tools(tools=tools, inference_result=inference)
    return PoolEvaluation(
        tuple(item for item in ranked if item.tool.id in eligible_ids),
        tuple(ranked),
        inference,
        eligibility,
    )
