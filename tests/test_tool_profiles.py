from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.tool_profiles import (
    CapabilityEvidence,
    EvidenceStatus,
    HardConstraints,
    NetworkRequirement,
    OperationSetup,
    SetupEvidence,
)
from app.knowledge.loader import load_knowledge, audit_knowledge, default_knowledge_path
from app.knowledge.profiles import merge_tool_profiles
from app.knowledge.models import KnowledgeSnapshot
from scripts.build_adaptive_knowledge import build_snapshot, build_tools, DEFAULT_PROFILES, main
import json
import gzip


@pytest.mark.parametrize("value", [True, False])
def test_known_capability_requires_both_source_and_review_date(value):
    for fields in ({}, {"source_url": "https://example.com/docs"}, {"reviewed_at": date(2026, 9, 5)}):
        with pytest.raises(ValidationError):
            CapabilityEvidence(value=value, **fields)
    assert CapabilityEvidence(value=value, source_url="https://example.com/docs", reviewed_at=date(2026, 9, 5)).value is value


def test_unknown_capability_and_default_constraints():
    assert CapabilityEvidence().value is None
    assert not any(HardConstraints().model_dump().values())


def test_operation_setup_rejects_offline_claim_when_runtime_needs_network():
    text = {"ar": "دليل", "en": "Evidence"}
    known = {
        "value": True,
        "source_url": "https://example.com/offline",
        "reviewed_at": "2026-09-06",
    }
    guide = {
        "prerequisites": [text],
        "steps": [
            {"instruction": text, "source_url": "https://example.com/offline"}
        ] * 3,
        "example": text,
        "expected_outcome": text,
        "reviewed_at": "2026-09-06",
    }

    with pytest.raises(ValidationError, match="runtime network"):
        OperationSetup.model_validate(
            {
                "id": "local-run",
                "name": text,
                "task": text,
                "stage": "implementation",
                "domain": "artificial_intelligence",
                "platform": text,
                "local_components": [text],
                "preparation_network": NetworkRequirement.REQUIRED,
                "runtime_network": NetworkRequirement.REQUIRED,
                "offline_features": [text],
                "online_only_features": [],
                "offline": known,
                "free_plan": known,
                "open_source": known,
                "evidence_status": EvidenceStatus.OFFICIAL_DOCUMENTATION,
                "evidence": [
                    SetupEvidence(
                        property="offline_runtime",
                        status=EvidenceStatus.OFFICIAL_DOCUMENTATION,
                        source_url="https://example.com/offline",
                        summary=text,
                        version_scope="1.x",
                        reviewed_at="2026-09-06",
                        limitations=text,
                    )
                ],
                "starter_guide": guide,
            }
        )


@pytest.mark.parametrize("mutation, message", [("duplicate", "duplicate"), ("unknown", "unknown"), ("missing", "missing")])
def test_profile_join_rejects_wrong_catalog_membership(tmp_path, mutation, message):
    entries = json.loads(DEFAULT_PROFILES.read_text(encoding="utf-8"))
    if mutation == "duplicate":
        entries.append(entries[0])
    elif mutation == "unknown":
        entries[0]["tool_id"] = "not-a-production-tool"
    else:
        entries.pop()
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        merge_tool_profiles(build_tools(), path)


def test_profiles_have_bilingual_tailored_guides_and_valid_references():
    snapshot = build_snapshot()
    assert len(snapshot.tools) == 192
    guides = []
    for tool in snapshot.tools:
        profile = tool.profile
        assert profile is not None
        guide = profile.starter_guide
        assert 3 <= len(guide.steps) <= 5
        assert guide.reviewed_at == profile.reviewed_at
        assert guide.prerequisites
        assert guide.example.ar != guide.example.en
        assert guide.expected_outcome.ar != guide.expected_outcome.en
        for step in guide.steps:
            assert step.source_url in profile.sources
            assert step.instruction.ar != step.instruction.en
        guides.append(tuple(step.instruction.en for step in guide.steps))
    assert len(set(guides)) == 192


def test_version_covers_profile_changes_and_ignores_json_order_and_gzip_metadata(tmp_path):
    snapshot = build_snapshot()
    payload = snapshot.model_dump(mode="json")
    left, right = tmp_path / "left.json.gz", tmp_path / "right.json.gz"
    left.write_bytes(gzip.compress(json.dumps(payload).encode(), mtime=1))
    right.write_bytes(gzip.compress(json.dumps(payload, sort_keys=True).encode(), mtime=2))
    assert load_knowledge(left).version == load_knowledge(right).version == snapshot.version
    payload["tools"][0]["profile"]["deployment"]["en"] += " Updated."
    assert KnowledgeSnapshot.model_validate(payload).version != snapshot.version


def test_rebuilding_is_reproducible_and_matches_production(tmp_path):
    first, second = tmp_path / "first.json.gz", tmp_path / "second.json.gz"
    main(first)
    main(second)
    assert first.read_bytes() == second.read_bytes()
    assert load_knowledge(first).version == load_knowledge(default_knowledge_path()).version
    assert audit_knowledge(load_knowledge(first)).passed


def test_production_audit_rejects_missing_profiles():
    snapshot = build_snapshot()
    snapshot.tools[0].profile = None
    assert any("profile" in violation for violation in audit_knowledge(snapshot).violations)


def test_profiles_reject_unlisted_sources_and_blank_translation():
    from app.domain.tool_profiles import ToolProfile
    profile = build_snapshot().tools[0].profile.model_dump(mode="json")
    profile["starter_guide"]["steps"][0]["source_url"] = "https://example.com/unreviewed"
    with pytest.raises(ValidationError, match="source"):
        ToolProfile.model_validate(profile)
    profile = build_snapshot().tools[0].profile.model_dump(mode="json")
    profile["deployment"]["ar"] = " "
    with pytest.raises(ValidationError):
        ToolProfile.model_validate(profile)
