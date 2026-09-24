"""Dependency-free shared vocabulary for domain models and tool profiles."""
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)
]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Language(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class LocalizedText(DomainModel):
    ar: NonEmptyText
    en: NonEmptyText

    def for_language(self, language: Language) -> str:
        return self.ar if language is Language.ARABIC else self.en
