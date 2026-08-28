import math
from typing import Self

from pydantic import Field, model_validator

from app.domain.models import DomainModel, Identifier


class AnswerSelection(DomainModel):
    question_id: Identifier
    option_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_option_ids(self) -> Self:
        if len(self.option_ids) != len(set(self.option_ids)):
            raise ValueError("option ids must be unique")
        return self


class ScoreEffect(DomainModel):
    tool_id: Identifier
    rule_id: Identifier
    value: float = Field(allow_inf_nan=False)


class InferenceResult(DomainModel):
    tool_scores: dict[Identifier, float] = Field(default_factory=dict)
    effects: list[ScoreEffect] = Field(default_factory=list)
    fired_rule_ids: list[Identifier] = Field(default_factory=list)
    firing_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_finite_scores_and_unique_rules(self) -> Self:
        if not all(math.isfinite(score) for score in self.tool_scores.values()):
            raise ValueError("tool scores must be finite")
        if len(self.fired_rule_ids) != len(set(self.fired_rule_ids)):
            raise ValueError("fired rule ids must be unique")
        return self
