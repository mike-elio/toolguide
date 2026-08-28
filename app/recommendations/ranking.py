from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import Tool
from app.expert_engine import InferenceResult, ScoreEffect
from app.recommendations.errors import (
    InsufficientToolsError,
    RecommendationConsistencyError,
)


@dataclass(frozen=True)
class RankedTool:
    tool: Tool
    score: float
    effects: tuple[ScoreEffect, ...]


def rank_tools(
    *, tools: Sequence[Tool], inference_result: InferenceResult
) -> tuple[RankedTool, ...]:
    if len(tools) < 3:
        raise InsufficientToolsError("recommendations require at least three tools")

    tools_by_id: dict[str, Tool] = {}
    for item in tools:
        if item.id in tools_by_id:
            raise RecommendationConsistencyError(f"duplicate tool id: {item.id}")
        tools_by_id[item.id] = item

    tool_ids = set(tools_by_id)
    if set(inference_result.tool_scores) != tool_ids:
        raise RecommendationConsistencyError(
            "inference score ids do not match the supplied tool ids"
        )

    effects_by_tool: defaultdict[str, list[ScoreEffect]] = defaultdict(list)
    for effect in inference_result.effects:
        if effect.tool_id not in tools_by_id:
            raise RecommendationConsistencyError(
                f"inference effect references unknown tool: {effect.tool_id}"
            )
        effects_by_tool[effect.tool_id].append(effect)

    ranked = [
        RankedTool(
            tool=item,
            score=inference_result.tool_scores[item.id],
            effects=tuple(
                sorted(
                    effects_by_tool[item.id],
                    key=lambda effect: (effect.rule_id, effect.value),
                )
            ),
        )
        for item in tools_by_id.values()
    ]
    ranked.sort(key=lambda item: (-item.score, item.tool.id))
    return tuple(ranked)
