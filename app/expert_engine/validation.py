from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from app.domain.models import AnswerOption, Question, QuestionType, Rule, TextIntent, Tool
from app.expert_engine.errors import KnowledgeValidationError
from app.expert_engine.models import AnswerSelection


@dataclass(frozen=True)
class ResolvedAnswer:
    question: Question
    options: tuple[AnswerOption | TextIntent, ...]


@dataclass(frozen=True)
class InferenceContext:
    tools_by_id: dict[str, Tool]
    questions_by_id: dict[str, Question]
    rules: tuple[Rule, ...]
    answers: tuple[ResolvedAnswer, ...]


class _Identified(Protocol):
    id: str


IdentifiedItem = TypeVar("IdentifiedItem", bound=_Identified)


def _index_unique(
    items: Sequence[IdentifiedItem], item_kind: str
) -> dict[str, IdentifiedItem]:
    indexed: dict[str, IdentifiedItem] = {}
    for item in items:
        if item.id in indexed:
            raise KnowledgeValidationError(f"duplicate {item_kind} id: {item.id}")
        indexed[item.id] = item
    return indexed


def _validate_rules(
    rules: Sequence[Rule],
    questions_by_id: Mapping[str, Question],
    tools_by_id: Mapping[str, Tool],
) -> None:
    for rule in rules:
        question = questions_by_id.get(rule.question_id)
        if question is None:
            raise KnowledgeValidationError(
                f"rule {rule.id} references unknown question {rule.question_id}"
            )
        answer_ids = {option.id for option in question.options} | {
            intent.id for intent in question.text_intents
        }
        if rule.answer_option_id not in answer_ids:
            raise KnowledgeValidationError(
                f"rule {rule.id} references unknown answer option "
                f"{rule.answer_option_id} on question {question.id}"
            )
        for impact in rule.impacts:
            if impact.tool_id not in tools_by_id:
                raise KnowledgeValidationError(
                    f"rule {rule.id} references unknown tool {impact.tool_id}"
                )


def _resolve_answers(
    answers: Sequence[AnswerSelection],
    questions_by_id: Mapping[str, Question],
) -> tuple[ResolvedAnswer, ...]:
    answer_question_ids: set[str] = set()
    resolved_answers: list[ResolvedAnswer] = []
    for answer in answers:
        if answer.question_id in answer_question_ids:
            raise KnowledgeValidationError(
                f"duplicate answer for question: {answer.question_id}"
            )
        answer_question_ids.add(answer.question_id)

        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise KnowledgeValidationError(
                f"answer references unknown question {answer.question_id}"
            )
        if question.type in {
            QuestionType.SINGLE_CHOICE,
            QuestionType.SHORT_TEXT,
            QuestionType.BOOLEAN,
        } and len(answer.option_ids) != 1:
            raise KnowledgeValidationError(
                f"question {question.id} requires exactly one option"
            )

        available_answers = (
            question.text_intents
            if question.type is QuestionType.SHORT_TEXT
            else question.options
        )
        options_by_id = {option.id: option for option in available_answers}
        selected_options: list[AnswerOption | TextIntent] = []
        for option_id in answer.option_ids:
            option = options_by_id.get(option_id)
            if option is None:
                raise KnowledgeValidationError(
                    f"answer references unknown answer option {option_id} "
                    f"on question {question.id}"
                )
            selected_options.append(option)
        resolved_answers.append(
            ResolvedAnswer(question=question, options=tuple(selected_options))
        )
    return tuple(resolved_answers)


def validate_inference_input(
    *,
    tools: Sequence[Tool],
    questions: Sequence[Question],
    rules: Sequence[Rule],
    answers: Sequence[AnswerSelection],
) -> InferenceContext:
    tools_by_id = _index_unique(tools, "tool")
    questions_by_id = _index_unique(questions, "question")
    _index_unique(rules, "rule")
    _validate_rules(rules, questions_by_id, tools_by_id)
    resolved_answers = _resolve_answers(answers, questions_by_id)

    return InferenceContext(
        tools_by_id=tools_by_id,
        questions_by_id=questions_by_id,
        rules=tuple(rules),
        answers=resolved_answers,
    )
