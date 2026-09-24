"""Strict build-time join for the separately maintained profile catalog."""
import json
from collections.abc import Callable
from pathlib import Path

from pydantic import TypeAdapter

from app.domain.base import DomainModel
from app.domain.models import Tool
from app.domain.tool_profiles import ToolProfile


class ProfileEntry(DomainModel):
    tool_id: str
    profile: ToolProfile


def merge_tool_profiles(
    tools: list[Tool],
    path: Path,
    fallback_factory: Callable[[Tool], ToolProfile] | None = None,
) -> list[Tool]:
    entries = TypeAdapter(list[ProfileEntry]).validate_python(
        json.loads(path.read_text(encoding="utf-8"))
    )
    profiles = {}
    for entry in entries:
        if entry.tool_id in profiles:
            raise ValueError(f"duplicate tool profile: {entry.tool_id}")
        profiles[entry.tool_id] = entry.profile
    expected = {tool.id for tool in tools}
    if unknown := set(profiles) - expected:
        raise ValueError(f"unknown tool profiles: {sorted(unknown)}")
    missing = expected - set(profiles)
    if missing and fallback_factory is None:
        raise ValueError(f"missing tool profiles: {sorted(missing)}")
    return [
        tool.model_copy(
            update={
                "profile": profiles.get(tool.id)
                or fallback_factory(tool)  # type: ignore[misc]
            }
        )
        for tool in tools
    ]
