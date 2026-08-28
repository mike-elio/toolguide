from collections.abc import Mapping, Sequence
import re
from types import MappingProxyType

from app.domain.models import Language, Question
from app.text_intent.contracts import AliasConflictError, IntentPrediction
from app.text_intent.normalization import normalize_text


AliasKey = tuple[Language, str, str]

_ENGLISH_STOP_WORDS = frozenset(
    {"a", "an", "and", "for", "of", "the", "this", "to", "with"}
)


def build_alias_index(questions: Sequence[Question]) -> Mapping[AliasKey, str]:
    index: dict[AliasKey, str] = {}
    for question in questions:
        for intent in question.text_intents:
            for language, aliases in intent.aliases.items():
                for alias in aliases:
                    key = (language, question.id, normalize_text(alias, language))
                    existing = index.get(key)
                    if existing is not None and existing != intent.id:
                        raise AliasConflictError(
                            f"conflicting aliases on question: {question.id}"
                        )
                    index[key] = intent.id
    return MappingProxyType(index)


def find_alias(
    index: Mapping[AliasKey, str],
    *,
    language: Language,
    question_id: str,
    text: str,
) -> IntentPrediction | None:
    intent_id = index.get(
        (language, question_id, normalize_text(text, language))
    )
    if intent_id is None:
        return None
    return IntentPrediction(
        question_id=question_id,
        intent_id=intent_id,
        confidence=1.0,
        margin=1.0,
        source="alias",
    )


def find_alias_term_match(
    question: Question,
    *,
    language: Language,
    text: str,
) -> IntentPrediction | None:
    if language is not Language.ENGLISH:
        return None

    submitted_terms = _english_terms(text)
    scored_intents: list[tuple[int, str]] = []
    for intent in question.text_intents:
        intent_terms: set[str] = set()
        for phrase in [intent.label.en, *intent.aliases[Language.ENGLISH]]:
            intent_terms.update(_english_terms(phrase))
        scored_intents.append((len(submitted_terms & intent_terms), intent.id))

    scored_intents.sort(reverse=True)
    best_score, best_intent_id = scored_intents[0]
    second_score = scored_intents[1][0]
    if best_score < 2 or best_score - second_score < 1:
        return None

    return IntentPrediction(
        question_id=question.id,
        intent_id=best_intent_id,
        confidence=best_score / (best_score + second_score),
        margin=(best_score - second_score) / best_score,
        source="alias",
    )


def _english_terms(value: str) -> set[str]:
    normalized = normalize_text(value, Language.ENGLISH)
    return {
        term
        for term in re.findall(r"[a-z0-9]+", normalized)
        if term not in _ENGLISH_STOP_WORDS
    }
