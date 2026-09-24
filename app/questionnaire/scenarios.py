"""Compare outcomes without storing or mutating either session."""

from app.domain.models import DomainModel, Identifier
from app.questionnaire.models import QuestionnaireOutcome, QuestionnaireStatus


class ScenarioChange(DomainModel):
    tool_id: Identifier
    before_rank: int | None = None
    after_rank: int | None = None
    before_match: int | None = None
    after_match: int | None = None


def compare_outcomes(baseline: QuestionnaireOutcome,
                     variant: QuestionnaireOutcome) -> list[ScenarioChange]:
    final = {QuestionnaireStatus.COMPLETE, QuestionnaireStatus.NO_MATCH}
    if baseline.status not in final or variant.status not in final:
        return []
    before = {tool.tool_id: (rank, tool.match_percent)
              for rank, tool in enumerate(baseline.recommendations, 1)}
    after = {tool.tool_id: (rank, tool.match_percent)
             for rank, tool in enumerate(variant.recommendations, 1)}
    return [ScenarioChange(tool_id=tool_id,
                           before_rank=before.get(tool_id, (None, None))[0],
                           before_match=before.get(tool_id, (None, None))[1],
                           after_rank=after.get(tool_id, (None, None))[0],
                           after_match=after.get(tool_id, (None, None))[1])
            for tool_id in sorted(before.keys() | after.keys())]
