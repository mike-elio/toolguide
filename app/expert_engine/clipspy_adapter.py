import math
from collections import defaultdict
from collections.abc import Sequence

import clips

from app.domain.models import Question, Rule, Tool
from app.expert_engine.compiler import TEMPLATES, compile_rule
from app.expert_engine.errors import (
    InferenceBuildError,
    InferenceExecutionError,
    InferenceLimitError,
)
from app.expert_engine.models import AnswerSelection, InferenceResult, ScoreEffect
from app.expert_engine.validation import InferenceContext, validate_inference_input


class ClipspyAdapter:
    """Execute one isolated CLIPS environment for each inference request."""

    def infer(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
    ) -> InferenceResult:
        context = validate_inference_input(
            tools=tools,
            questions=questions,
            rules=rules,
            answers=answers,
        )
        environment = self._build_environment(context)
        self._assert_request_facts(environment, context)

        try:
            firing_count = _run_to_completion(environment, len(context.rules))
            return self._extract_result(environment, context, firing_count)
        except clips.CLIPSError as error:
            raise InferenceExecutionError("CLIPS inference execution failed") from error

    @staticmethod
    def _build_environment(context: InferenceContext) -> clips.Environment:
        environment = clips.Environment()
        try:
            for construct in TEMPLATES.strip().split("\n\n"):
                environment.build(construct)
            for rule in context.rules:
                environment.build(compile_rule(rule))
        except clips.CLIPSError as error:
            raise InferenceBuildError("CLIPS knowledge program build failed") from error
        return environment

    @staticmethod
    def _assert_request_facts(
        environment: clips.Environment, context: InferenceContext
    ) -> None:
        try:
            tool_template = environment.find_template("tool")
            for tool_id in context.tools_by_id:
                tool_template.assert_fact(**{"tool-id": tool_id})

            answer_template = environment.find_template("selected-answer")
            for answer in context.answers:
                for option in answer.options:
                    answer_template.assert_fact(
                        **{
                            "question-id": answer.question.id,
                            "option-id": option.id,
                            "value": option.value,
                            "importance": answer.question.importance,
                        }
                    )
        except clips.CLIPSError as error:
            raise InferenceExecutionError("CLIPS fact assertion failed") from error

    @staticmethod
    def _extract_result(
        environment: clips.Environment,
        context: InferenceContext,
        firing_count: int,
    ) -> InferenceResult:
        effects = sorted(
            (
                ScoreEffect(
                    tool_id=str(fact["tool-id"]),
                    rule_id=str(fact["rule-id"]),
                    value=float(fact["value"]),
                )
                for fact in environment.find_template("score-effect").facts()
            ),
            key=lambda effect: (effect.tool_id, effect.rule_id),
        )
        fired_rule_ids = sorted(
            {
                str(fact["rule-id"])
                for fact in environment.find_template("rule-fired").facts()
            }
        )
        effect_values_by_tool: defaultdict[str, list[float]] = defaultdict(list)
        for effect in effects:
            effect_values_by_tool[effect.tool_id].append(effect.value)
        tool_scores = {
            tool_id: math.fsum(effect_values_by_tool[tool_id])
            for tool_id in sorted(context.tools_by_id)
        }
        return InferenceResult(
            tool_scores=tool_scores,
            effects=effects,
            fired_rule_ids=fired_rule_ids,
            firing_count=firing_count,
        )


def _run_to_completion(
    environment: clips.Environment, firing_limit: int
) -> int:
    if firing_limit < 1:
        if next(environment.activations(), None) is not None:
            raise InferenceLimitError("CLIPS inference reached its firing limit")
        return 0

    firing_count = environment.run(firing_limit)
    if next(environment.activations(), None) is not None:
        raise InferenceLimitError("CLIPS inference reached its firing limit")
    return firing_count
