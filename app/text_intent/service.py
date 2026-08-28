from collections.abc import Sequence

from app.domain.models import Language, Question, QuestionType
from app.expert_engine import AnswerSelection
from app.text_intent.aliases import (
    build_alias_index,
    find_alias,
    find_alias_term_match,
)
from app.text_intent.contracts import (
    InvalidAnswerRepresentationError,
    IntentPrediction,
    ModelUnavailableError,
    TextIntentClassifier,
    TextIntentError,
    UncertainTextIntentError,
)


class UnavailableTextIntentClassifier:
    def predict(
        self, language: Language, question: Question, text: str
    ) -> IntentPrediction:
        raise ModelUnavailableError(
            f"text-intent model unavailable for language: {language.value}"
        )


class AnswerResolutionService:
    def __init__(self, classifier: TextIntentClassifier | None = None) -> None:
        self._classifier = classifier or UnavailableTextIntentClassifier()

    def resolve(
        self,
        language: Language,
        submitted_answers: Sequence[object],
        questions: Sequence[Question],
    ) -> list[AnswerSelection]:
        questions_by_id = {question.id: question for question in questions}
        if len(questions_by_id) != len(questions):
            raise TextIntentError("duplicate question ids")
        alias_index = build_alias_index(questions)
        seen_questions: set[str] = set()
        resolved: list[AnswerSelection] = []
        for answer in submitted_answers:
            question_id = getattr(answer, "question_id")
            option_ids = getattr(answer, "option_ids")
            answer_text = getattr(answer, "text")
            if question_id in seen_questions:
                raise TextIntentError(f"duplicate answer for question: {question_id}")
            seen_questions.add(question_id)
            question = questions_by_id.get(question_id)
            if question is None:
                raise TextIntentError(f"answer references unknown question: {question_id}")

            if question.type is not QuestionType.SHORT_TEXT:
                if option_ids is None or answer_text is not None:
                    raise InvalidAnswerRepresentationError(
                        f"question requires option ids: {question.id}"
                    )
                resolved.append(
                    AnswerSelection(question_id=question.id, option_ids=option_ids)
                )
                continue

            if answer_text is None or option_ids is not None:
                raise InvalidAnswerRepresentationError(
                    f"question requires short text: {question.id}"
                )
            prediction = find_alias(
                alias_index,
                language=language,
                question_id=question.id,
                text=answer_text,
            )
            if prediction is None:
                prediction = find_alias_term_match(
                    question,
                    language=language,
                    text=answer_text,
                )
            if prediction is None:
                prediction = self._classifier.predict(language, question, answer_text)
            intent_ids = {intent.id for intent in question.text_intents}
            if (
                prediction.question_id != question.id
                or prediction.intent_id not in intent_ids
            ):
                raise UncertainTextIntentError(
                    f"short text could not be resolved for question: {question.id}"
                )
            resolved.append(
                AnswerSelection(
                    question_id=question.id,
                    option_ids=[prediction.intent_id],
                )
            )
        return resolved


__all__ = [
    "AnswerResolutionService",
    "InvalidAnswerRepresentationError",
    "ModelUnavailableError",
    "TextIntentClassifier",
    "TextIntentError",
    "UncertainTextIntentError",
    "UnavailableTextIntentClassifier",
]
