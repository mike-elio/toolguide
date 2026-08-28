import re
import unicodedata

from app.domain.models import Language


_ARABIC_DIACRITICS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]"
)
_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str, language: Language) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    if language is Language.ARABIC:
        normalized = normalized.replace("ـ", "")
        normalized = _ARABIC_DIACRITICS.sub("", normalized)
    else:
        normalized = normalized.casefold()
    return _WHITESPACE.sub(" ", normalized).strip()
