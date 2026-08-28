from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import (
    AnswerOption,
    DomainId,
    Language,
    Question,
    QuestionType,
    Rule,
    StageId,
    Tool,
)
from app.expert_engine import AnswerSelection, ClipspyAdapter, InferenceResult
from app.knowledge import KnowledgeSnapshot
from app.questionnaire.models import (
    ConfidenceLevel,
    QuestionnaireHistoryError,
    QuestionnaireOutcome,
    QuestionnaireRecommendation,
    QuestionnaireStatus,
)
from app.questionnaire.selector import select_next_question
from app.recommendations.ranking import RankedTool, rank_tools
from app.text_intent import (
    AnswerResolutionService,
    ModelUnavailableError,
    UncertainTextIntentError,
)


MINIMUM_QUESTIONS = 6
MAXIMUM_QUESTIONS = 10
STOP_MARGIN = 0.18
HIGH_CONFIDENCE_MARGIN = 0.30


class QuestionnaireService:
    def __init__(self, engine: ClipspyAdapter | None = None) -> None:
        self._engine = engine or ClipspyAdapter()

    def advance(
        self,
        *,
        knowledge: KnowledgeSnapshot,
        resolver: AnswerResolutionService,
        language: Language,
        stage: StageId,
        domain: DomainId,
        session_seed: str,
        asked_question_ids: Sequence[str],
        submitted_answers: Sequence[object],
    ) -> QuestionnaireOutcome:
        tools, questions, rules = _pool(knowledge, stage, domain)
        _validate_history(questions, asked_question_ids, submitted_answers)
        resolved, clarification = _resolve_answers(
            resolver=resolver,
            language=language,
            questions=questions,
            submitted_answers=submitted_answers,
        )
        if clarification is not None:
            return QuestionnaireOutcome(
                status=QuestionnaireStatus.CLARIFICATION,
                answered_count=len(resolved),
                question=clarification,
                clarification_options=[
                    AnswerOption(id=intent.id, label=intent.label, value=intent.value)
                    for intent in clarification.text_intents
                ],
            )

        inference = self._engine.infer(
            tools=tools,
            questions=questions,
            rules=rules,
            answers=resolved,
        )
        ranked = rank_tools(tools=tools, inference_result=inference)
        answered_count = len(resolved)
        if answered_count >= MAXIMUM_QUESTIONS or (
            answered_count >= MINIMUM_QUESTIONS
            and _stable_and_separated(
                engine=self._engine,
                tools=tools,
                questions=questions,
                rules=rules,
                answers=resolved,
                ranked=ranked,
            )
        ):
            margin = _normalized_margin(ranked)
            confidence = _confidence(answered_count, margin)
            recommendations = _build_recommendations(
                ranked=ranked,
                inference=inference,
                questions=questions,
                rules=rules,
                answers=resolved,
                language=language,
                confidence=confidence,
            )
            return QuestionnaireOutcome(
                status=QuestionnaireStatus.COMPLETE,
                answered_count=answered_count,
                recommendations=recommendations,
            )

        question = select_next_question(
            questions=questions,
            rules=rules,
            tool_scores=inference.tool_scores,
            asked_question_ids=set(asked_question_ids),
            seed=session_seed,
        )
        return QuestionnaireOutcome(
            status=QuestionnaireStatus.QUESTION,
            answered_count=answered_count,
            question=question,
        )


def _pool(
    knowledge: KnowledgeSnapshot, stage: StageId, domain: DomainId
) -> tuple[list[Tool], list[Question], list[Rule]]:
    tools = [
        tool
        for tool in knowledge.tools
        if tool.stages == [stage] and tool.domain is domain
    ]
    questions = [
        question
        for question in knowledge.questions
        if question.stage is stage and question.domain is domain
    ]
    question_ids = {question.id for question in questions}
    rules = [rule for rule in knowledge.rules if rule.question_id in question_ids]
    if len(tools) != 4 or len(questions) < MAXIMUM_QUESTIONS:
        raise QuestionnaireHistoryError(
            f"incomplete questionnaire pool: {stage.value}/{domain.value}"
        )
    return tools, questions, rules


def _validate_history(
    questions: Sequence[Question],
    asked_question_ids: Sequence[str],
    submitted_answers: Sequence[object],
) -> None:
    if len(asked_question_ids) != len(set(asked_question_ids)):
        raise QuestionnaireHistoryError("asked question ids must be unique")
    if len(submitted_answers) != len(asked_question_ids):
        raise QuestionnaireHistoryError(
            "each asked question must have exactly one submitted answer"
        )
    pool_ids = {question.id for question in questions}
    if set(asked_question_ids) - pool_ids:
        raise QuestionnaireHistoryError("asked question does not belong to the pool")
    answer_ids = [getattr(answer, "question_id") for answer in submitted_answers]
    if answer_ids != list(asked_question_ids):
        raise QuestionnaireHistoryError(
            "submitted answer order must match asked question order"
        )


def _resolve_answers(
    *,
    resolver: AnswerResolutionService,
    language: Language,
    questions: Sequence[Question],
    submitted_answers: Sequence[object],
) -> tuple[list[AnswerSelection], Question | None]:
    questions_by_id = {question.id: question for question in questions}
    resolved: list[AnswerSelection] = []
    for submitted in submitted_answers:
        question = questions_by_id[getattr(submitted, "question_id")]
        option_ids = getattr(submitted, "option_ids")
        text = getattr(submitted, "text")
        if question.type is QuestionType.SHORT_TEXT and option_ids is not None:
            valid_intents = {intent.id for intent in question.text_intents}
            if len(option_ids) != 1 or option_ids[0] not in valid_intents:
                raise QuestionnaireHistoryError(
                    f"invalid clarification choice for question: {question.id}"
                )
            resolved.append(
                AnswerSelection(question_id=question.id, option_ids=option_ids)
            )
            continue
        try:
            resolved.extend(resolver.resolve(language, [submitted], [question]))
        except (ModelUnavailableError, UncertainTextIntentError):
            if question.type is not QuestionType.SHORT_TEXT or text is None:
                raise
            return resolved, question
    return resolved, None


def _normalized_margin(ranked: Sequence[RankedTool]) -> float:
    if len(ranked) < 4:
        return 0.0
    span = ranked[0].score - ranked[-1].score
    if span <= 0.0:
        return 0.0
    return max(0.0, (ranked[2].score - ranked[3].score) / span)


def _stable_and_separated(
    *,
    engine: ClipspyAdapter,
    tools: Sequence[Tool],
    questions: Sequence[Question],
    rules: Sequence[Rule],
    answers: Sequence[AnswerSelection],
    ranked: Sequence[RankedTool],
) -> bool:
    if len(answers) < MINIMUM_QUESTIONS:
        return False
    previous_inference = engine.infer(
        tools=tools,
        questions=questions,
        rules=rules,
        answers=answers[:-1],
    )
    previous = rank_tools(tools=tools, inference_result=previous_inference)
    current_ids = [item.tool.id for item in ranked[:3]]
    previous_ids = [item.tool.id for item in previous[:3]]
    return current_ids == previous_ids and _normalized_margin(ranked) >= STOP_MARGIN


def _confidence(answered_count: int, margin: float) -> ConfidenceLevel:
    if answered_count >= 8 and margin >= HIGH_CONFIDENCE_MARGIN:
        return ConfidenceLevel.HIGH
    if answered_count >= MINIMUM_QUESTIONS and margin >= STOP_MARGIN:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _selected_rules(
    rules: Sequence[Rule], answers: Sequence[AnswerSelection]
) -> list[Rule]:
    targets = {
        (answer.question_id, option_id)
        for answer in answers
        for option_id in answer.option_ids
    }
    return [
        rule
        for rule in rules
        if (rule.question_id, rule.answer_option_id) in targets
    ]


def _match_percent(
    ranked_tool: RankedTool,
    *,
    questions: Sequence[Question],
    selected_rules: Sequence[Rule],
) -> int:
    questions_by_id = {question.id: question for question in questions}
    capacity = 0.0
    for rule in selected_rules:
        impact = next(
            (item for item in rule.impacts if item.tool_id == ranked_tool.tool.id),
            None,
        )
        if impact is not None:
            capacity += questions_by_id[rule.question_id].importance * abs(impact.weight)
    if capacity <= 0.0:
        return 50
    normalized = max(-1.0, min(1.0, ranked_tool.score / capacity))
    return round(50.0 + 50.0 * normalized)


def _build_recommendations(
    *,
    ranked: Sequence[RankedTool],
    inference: InferenceResult,
    questions: Sequence[Question],
    rules: Sequence[Rule],
    answers: Sequence[AnswerSelection],
    language: Language,
    confidence: ConfidenceLevel,
) -> list[QuestionnaireRecommendation]:
    del inference
    selected = _selected_rules(rules, answers)
    rule_impacts = {
        (rule.id, impact.tool_id): impact
        for rule in selected
        for impact in rule.impacts
    }
    recommendations: list[QuestionnaireRecommendation] = []
    for ranked_tool in ranked[:3]:
        contributions = [
            (
                effect.value,
                rule_impacts[(effect.rule_id, ranked_tool.tool.id)]
                .rationale.for_language(language),
            )
            for effect in ranked_tool.effects
            if (effect.rule_id, ranked_tool.tool.id) in rule_impacts
        ]
        positives = _unique_text(
            text
            for value, text in sorted(contributions, key=lambda item: -item[0])
            if value > 0
        )[:3]
        negatives = _unique_text(
            text
            for value, text in sorted(contributions, key=lambda item: item[0])
            if value < 0
        )
        documented = [
            item.for_language(language) for item in ranked_tool.tool.limitations
        ]
        limitations = _unique_text([*negatives, *documented])[:2]
        if not positives:
            positives = [
                ranked_tool.tool.best_for.for_language(language)
                if ranked_tool.tool.best_for is not None
                else ranked_tool.tool.description.for_language(language)
            ]
        if not limitations:
            limitations = [
                "No documented limitation is available."
                if language is Language.ENGLISH
                else "لا يتوفر قيد موثق."
            ]
        recommendations.append(
            QuestionnaireRecommendation(
                tool_id=ranked_tool.tool.id,
                tool_name=ranked_tool.tool.name.for_language(language),
                match_percent=_match_percent(
                    ranked_tool, questions=questions, selected_rules=selected
                ),
                confidence=confidence,
                reasons=positives,
                limitations=limitations,
                source_url=ranked_tool.tool.source_url,
            )
        )
    recommendations.sort(
        key=lambda item: (-item.match_percent, item.tool_id)
    )
    return recommendations


def _unique_text(values) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


__all__ = ["QuestionnaireService"]
