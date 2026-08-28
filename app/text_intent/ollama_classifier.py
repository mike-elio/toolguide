"""Ollama-backed short-text intent classification."""

from collections.abc import Callable, Mapping
import json
from urllib.request import Request, urlopen

from app.domain.models import Language, Question
from app.text_intent.contracts import (
    IntentPrediction,
    ModelUnavailableError,
    UncertainTextIntentError,
)

_Transport = Callable[[str, dict[str, object], float], object]
_MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 60.0


class OllamaTextIntentClassifier:
    def __init__(
        self,
        *,
        model: str = "gemma3:1b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
        transport: _Transport | None = None,
    ) -> None:
        self._model = model
        self._chat_url = f"{base_url.rstrip('/')}/api/chat"
        self._timeout = timeout
        self._transport = transport or _post_json

    def predict(
        self, language: Language, question: Question, text: str
    ) -> IntentPrediction:
        intent_ids = [intent.id for intent in question.text_intents]
        # Ollama accepts a JSON Schema in `format`; temperature 0 improves
        # deterministic structured output.
        # Source: https://docs.ollama.com/capabilities/structured-outputs
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": _classification_prompt(language, question),
                },
                {"role": "user", "content": text},
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "intent_id": {"type": "string", "enum": intent_ids}
                },
                "required": ["intent_id"],
                "additionalProperties": False,
            },
            "options": {"temperature": 0, "seed": 42, "num_predict": 32},
        }
        try:
            response = self._transport(self._chat_url, payload, self._timeout)
            intent_id = _response_intent_id(response)
        except UncertainTextIntentError:
            raise
        except Exception as error:
            raise ModelUnavailableError(
                "Ollama text-intent model is unavailable"
            ) from error

        if intent_id not in intent_ids:
            raise UncertainTextIntentError(
                f"short text could not be resolved for question: {question.id}"
            )
        return IntentPrediction(
            question_id=question.id,
            intent_id=intent_id,
            confidence=1.0,
            margin=1.0,
            source="model",
        )


def _classification_prompt(language: Language, question: Question) -> str:
    intent_lines: list[str] = []
    for intent in question.text_intents:
        phrases = dict.fromkeys(
            [intent.label.for_language(language), *intent.aliases[language]]
        )
        intent_lines.append(f"- {intent.id}: {'; '.join(phrases)}")
    return "\n".join(
        [
            "You are a deterministic bilingual intent classifier.",
            "Classify the user's request; do not perform it.",
            "Choose exactly one intent_id from this question-scoped list:",
            *intent_lines,
            "Return only JSON matching the supplied schema.",
        ]
    )


def _response_intent_id(response: object) -> str:
    if not isinstance(response, Mapping):
        raise ValueError("invalid Ollama response")
    if response.get("done") is not True:
        raise ValueError("incomplete Ollama response")
    message = response.get("message")
    if not isinstance(message, Mapping) or message.get("role") != "assistant":
        raise ValueError("invalid Ollama response message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("invalid Ollama response content")
    decoded = json.loads(content)
    if (
        not isinstance(decoded, Mapping)
        or set(decoded) != {"intent_id"}
        or not isinstance(decoded.get("intent_id"), str)
    ):
        raise ValueError("invalid Ollama intent response")
    return decoded["intent_id"]


def _post_json(url: str, payload: dict[str, object], timeout: float) -> object:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw_response = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(raw_response) > _MAX_RESPONSE_BYTES:
        raise ValueError("Ollama response is too large")
    return json.loads(raw_response)


__all__ = ["DEFAULT_OLLAMA_TIMEOUT_SECONDS", "OllamaTextIntentClassifier"]
