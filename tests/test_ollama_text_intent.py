import json

import pytest

from app.domain.models import Language, LocalizedText, Question, QuestionType, TextIntent
from app.text_intent import ModelUnavailableError, UncertainTextIntentError
from app.text_intent.ollama_classifier import OllamaTextIntentClassifier


def localized(en: str, ar: str) -> LocalizedText:
    return LocalizedText(en=en, ar=ar)


def design_question() -> Question:
    return Question(
        id="design-q4",
        stage="design",
        prompt=localized(
            "Describe the required design asset.",
            "صف أصل التصميم المطلوب.",
        ),
        type=QuestionType.SHORT_TEXT,
        importance=0.85,
        text_intents=[
            TextIntent(
                id="image_generation",
                label=localized("Image generation", "توليد الصور"),
                value=1.0,
                aliases={
                    Language.ENGLISH: ["generate an image"],
                    Language.ARABIC: ["توليد صورة"],
                },
            ),
            TextIntent(
                id="ui_prototyping",
                label=localized("UI prototyping", "نمذجة واجهة"),
                value=0.9,
                aliases={
                    Language.ENGLISH: ["prototype a ui"],
                    Language.ARABIC: ["نموذج واجهة"],
                },
            ),
        ],
    )


def test_ollama_classifier_default_timeout_allows_a_cold_model_start() -> None:
    captured: dict[str, float] = {}

    def transport(url: str, payload: dict[str, object], timeout: float) -> object:
        captured["timeout"] = timeout
        return {
            "model": "gemma3:1b",
            "message": {
                "role": "assistant",
                "content": json.dumps({"intent_id": "ui_prototyping"}),
            },
            "done": True,
            "done_reason": "stop",
        }

    classifier = OllamaTextIntentClassifier(transport=transport)
    classifier.predict(
        Language.ENGLISH,
        design_question(),
        "Build a clickable mobile app mockup.",
    )

    assert captured["timeout"] == 60.0


def test_ollama_classifier_sends_all_question_intents_in_a_json_schema() -> None:
    captured: dict[str, object] = {}

    def transport(url: str, payload: dict[str, object], timeout: float) -> object:
        captured.update(url=url, payload=payload, timeout=timeout)
        return {
            "model": "gemma3:1b",
            "message": {
                "role": "assistant",
                "content": json.dumps({"intent_id": "ui_prototyping"}),
            },
            "done": True,
            "done_reason": "stop",
        }

    classifier = OllamaTextIntentClassifier(
        model="gemma3:1b",
        base_url="http://127.0.0.1:11434",
        timeout=12.0,
        transport=transport,
    )

    prediction = classifier.predict(
        Language.ENGLISH,
        design_question(),
        "I need a prototype of a modern application interface.",
    )

    assert prediction.question_id == "design-q4"
    assert prediction.intent_id == "ui_prototyping"
    assert prediction.source == "model"
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["timeout"] == 12.0
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gemma3:1b"
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0, "seed": 42, "num_predict": 32}
    assert payload["format"] == {
        "type": "object",
        "properties": {
            "intent_id": {
                "type": "string",
                "enum": ["image_generation", "ui_prototyping"],
            }
        },
        "required": ["intent_id"],
        "additionalProperties": False,
    }
    messages = payload["messages"]
    assert isinstance(messages, list)
    assert "image_generation" in messages[0]["content"]
    assert "ui_prototyping" in messages[0]["content"]
    assert messages[1] == {
        "role": "user",
        "content": "I need a prototype of a modern application interface.",
    }


def test_ollama_classifier_rejects_an_unknown_intent_without_echoing_text() -> None:
    raw_text = "private design request"

    def transport(url: str, payload: dict[str, object], timeout: float) -> object:
        return {
            "model": "gemma3:1b",
            "message": {
                "role": "assistant",
                "content": json.dumps({"intent_id": "foreign_intent"}),
            },
            "done": True,
            "done_reason": "stop",
        }

    classifier = OllamaTextIntentClassifier(transport=transport)

    with pytest.raises(UncertainTextIntentError) as caught:
        classifier.predict(Language.ENGLISH, design_question(), raw_text)

    assert raw_text not in str(caught.value)


def test_ollama_classifier_maps_transport_failures_to_a_safe_error() -> None:
    raw_text = "private design request"

    def transport(url: str, payload: dict[str, object], timeout: float) -> object:
        raise OSError("private network details")

    classifier = OllamaTextIntentClassifier(transport=transport)

    with pytest.raises(ModelUnavailableError) as caught:
        classifier.predict(Language.ENGLISH, design_question(), raw_text)

    assert str(caught.value) == "Ollama text-intent model is unavailable"
    assert raw_text not in str(caught.value)
    assert "private network details" not in str(caught.value)


@pytest.mark.parametrize(
    "response",
    [
        {
            "model": "gemma3:1b",
            "message": {
                "role": "assistant",
                "content": json.dumps({"intent_id": "ui_prototyping"}),
            },
            "done": False,
        },
        {
            "model": "gemma3:1b",
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {"intent_id": "ui_prototyping", "unexpected": "value"}
                ),
            },
            "done": True,
            "done_reason": "stop",
        },
    ],
)
def test_ollama_classifier_rejects_incomplete_or_extra_model_output(
    response: object,
) -> None:
    def transport(url: str, payload: dict[str, object], timeout: float) -> object:
        return response

    classifier = OllamaTextIntentClassifier(transport=transport)

    with pytest.raises(ModelUnavailableError, match="unavailable"):
        classifier.predict(
            Language.ENGLISH,
            design_question(),
            "prototype an application interface",
        )
