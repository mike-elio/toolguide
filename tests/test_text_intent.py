from collections.abc import Sequence

import pytest

from app.api.contracts import SubmittedAnswer
from app.domain.models import (
    Language,
    LocalizedText,
    Question,
    QuestionType,
    TextIntent,
)
from app.expert_engine import AnswerSelection
from app.knowledge import default_knowledge_path, load_knowledge
from app.text_intent.contracts import IntentPrediction
from app.text_intent.normalization import normalize_text
from app.text_intent.service import (
    AnswerResolutionService,
    InvalidAnswerRepresentationError,
    TextIntentClassifier,
    UncertainTextIntentError,
)


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(en=en, ar=ar or en)


def short_question() -> Question:
    return Question(
        id="analysis-q4",
        stage="analysis",
        prompt=localized("Describe the research need", "صف الحاجة البحثية"),
        type=QuestionType.SHORT_TEXT,
        importance=0.8,
        text_intents=[
            TextIntent(
                id="synthesis",
                label=localized("Synthesis", "توليف"),
                value=1.0,
                aliases={
                    Language.ENGLISH: ["compare trusted sources"],
                    Language.ARABIC: ["مقارنة مصادر موثوقة"],
                },
            ),
            TextIntent(
                id="discovery",
                label=localized("Discovery", "اكتشاف"),
                value=0.7,
                aliases={
                    Language.ENGLISH: ["find related papers"],
                    Language.ARABIC: ["العثور على أبحاث مرتبطة"],
                },
            ),
        ],
    )


class FixedClassifier(TextIntentClassifier):
    def __init__(self, prediction: IntentPrediction | Exception) -> None:
        self.prediction = prediction
        self.calls: list[tuple[Language, str, str]] = []

    def predict(
        self, language: Language, question: Question, text: str
    ) -> IntentPrediction:
        self.calls.append((language, question.id, text))
        if isinstance(self.prediction, Exception):
            raise self.prediction
        return self.prediction


@pytest.mark.parametrize(
    ("language", "raw", "expected"),
    [
        (Language.ENGLISH, "  STRASSE\u212A  ", "strassek"),
        (Language.ARABIC, "  مُـقَارَنَة   مَصَادِر  ", "مقارنة مصادر"),
    ],
)
def test_normalize_text_is_language_specific_and_deterministic(
    language: Language, raw: str, expected: str
) -> None:
    assert normalize_text(raw, language) == expected


def test_alias_resolution_precedes_classifier_fallback() -> None:
    classifier = FixedClassifier(AssertionError("classifier must not run"))
    resolver = AnswerResolutionService(classifier)

    resolved = resolver.resolve(
        Language.ARABIC,
        [SubmittedAnswer(question_id="analysis-q4", text="مُـقَارَنَة مصادر موثوقة")],
        [short_question()],
    )

    assert resolved == [
        AnswerSelection(question_id="analysis-q4", option_ids=["synthesis"])
    ]
    assert classifier.calls == []


def test_clear_english_alias_terms_resolve_before_classifier_fallback() -> None:
    classifier = FixedClassifier(AssertionError("classifier must not run"))
    resolver = AnswerResolutionService(classifier)
    knowledge = load_knowledge(default_knowledge_path())
    question = next(
        question
        for question in knowledge.questions
        if question.id == "design-software-design_intent"
    )

    resolved = resolver.resolve(
        Language.ENGLISH,
        [
            SubmittedAnswer(
                question_id="design-software-design_intent",
                text=(
                    "I want to create a prototype of a modern application interface "
                    "with a clear and customizable user experience."
                ),
            )
        ],
        [question],
    )

    assert resolved == [
        AnswerSelection(
            question_id="design-software-design_intent",
            option_ids=["prototype"],
        )
    ]
    assert classifier.calls == []


def test_classifier_fallback_returns_only_a_question_owned_intent() -> None:
    classifier = FixedClassifier(
        IntentPrediction(
            question_id="analysis-q4",
            intent_id="discovery",
            confidence=0.97,
            margin=0.63,
            source="model",
        )
    )
    resolver = AnswerResolutionService(classifier)

    resolved = resolver.resolve(
        Language.ENGLISH,
        [SubmittedAnswer(question_id="analysis-q4", text="locate adjacent studies")],
        [short_question()],
    )

    assert resolved[0].option_ids == ["discovery"]
    assert classifier.calls == [
        (Language.ENGLISH, "analysis-q4", "locate adjacent studies")
    ]


@pytest.mark.parametrize(
    "prediction",
    [
        IntentPrediction(
            question_id="other-question",
            intent_id="discovery",
            confidence=0.99,
            margin=0.8,
            source="model",
        ),
        IntentPrediction(
            question_id="analysis-q4",
            intent_id="foreign-intent",
            confidence=0.99,
            margin=0.8,
            source="model",
        ),
    ],
)
def test_classifier_labels_cannot_escape_the_submitted_question(
    prediction: IntentPrediction,
) -> None:
    resolver = AnswerResolutionService(FixedClassifier(prediction))

    with pytest.raises(UncertainTextIntentError, match="could not be resolved"):
        resolver.resolve(
            Language.ENGLISH,
            [SubmittedAnswer(question_id="analysis-q4", text="private raw text")],
            [short_question()],
        )


def test_resolution_rejects_the_wrong_answer_representation_without_raw_text() -> None:
    resolver = AnswerResolutionService(
        FixedClassifier(AssertionError("classifier must not run"))
    )

    with pytest.raises(InvalidAnswerRepresentationError) as caught:
        resolver.resolve(
            Language.ENGLISH,
            [SubmittedAnswer(question_id="analysis-q4", option_ids=["synthesis"])],
            [short_question()],
        )

    assert "synthesis" not in str(caught.value)
