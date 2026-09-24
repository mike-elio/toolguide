from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.text_intent import AnswerResolutionService


@pytest.fixture
def client():
    return TestClient(create_app(answer_resolution_service=AnswerResolutionService()))


def payload(**overrides):
    result = dict(language="en", stage="analysis", domain="software",
                  session_seed="decision-support", asked_question_ids=[], answers=[])
    result.update(overrides)
    return result


def test_explicit_empty_constraints_preserve_questionnaire(client):
    response = client.post("/api/questionnaire/advance", json=payload(constraints={}))
    assert response.status_code == 200
    assert response.json()["status"] == "question"
    assert response.json()["eligible_count"] == 16
    assert response.json()["unknown_evidence_count"] == 0
    assert len(response.json()["knowledge_version"]) == 64


def test_strict_requirement_never_returns_unverified_tools(client):
    response = client.post("/api/questionnaire/advance", json=payload(
        constraints={"requires_offline": True, "requires_open_source": True}))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_match"
    assert body["recommendations"] == []
    assert body["eligible_count"] == 0
    assert len(body["excluded_tools"]) == 16
    assert body["unknown_evidence_count"] > 0
    assert isinstance(body["alternatives"], list)
    assert all(tool["failed_constraints"] or tool["unknown_constraints"]
               for tool in body["excluded_tools"])


def test_unknown_constraint_rejected(client):
    response = client.post("/api/questionnaire/advance", json=payload(
        constraints={"invented": True}))
    assert response.status_code == 422


def test_scenario_requires_same_path_and_knowledge(client):
    original = payload()
    version = client.post("/api/questionnaire/advance", json=original).json()["knowledge_version"]
    variant = deepcopy(original)
    variant["domain"] = "cybersecurity"
    response = client.post("/api/questionnaire/compare", json={
        "baseline": original, "variant": variant, "knowledge_version": version})
    assert response.status_code == 422
    response = client.post("/api/questionnaire/compare", json={
        "baseline": original, "variant": original, "knowledge_version": "0" * 64})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "KNOWLEDGE_VERSION_MISMATCH"


def test_scenario_is_repeatable_and_does_not_mutate_original(client):
    original = payload()
    original_outcome = client.post("/api/questionnaire/advance", json=original).json()
    variant = deepcopy(original)
    variant["constraints"] = {"requires_offline": True, "requires_open_source": True}
    body = dict(baseline=original, variant=variant,
                knowledge_version=original_outcome["knowledge_version"])
    first = client.post("/api/questionnaire/compare", json=body)
    second = client.post("/api/questionnaire/compare", json=body)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["baseline"] == original_outcome
    assert first.json()["variant"]["status"] == "no_match"
    assert first.json()["changes"] == []  # baseline is not a final result
    assert client.post("/api/questionnaire/advance", json=original).json() == original_outcome


def completed_request(client, **overrides):
    questions = [q for q in client.app.state.knowledge.questions
                 if q.stage.value == "analysis" and q.domain.value == "software"][:10]
    return payload(asked_question_ids=[q.id for q in questions], answers=[{
        "question_id": q.id, "option_ids": [(q.options or q.text_intents)[0].id],
    } for q in questions], **overrides)


def test_relaxing_requirement_reports_entrants_and_preserves_completed_ranking(client):
    baseline = completed_request(client, constraints={"requires_open_source": True})
    original = client.post("/api/questionnaire/advance", json=baseline).json()
    assert original["status"] == "no_match"
    variant = deepcopy(baseline)
    variant["constraints"] = {}
    expected = client.post("/api/questionnaire/advance", json=variant).json()
    response = client.post("/api/questionnaire/compare", json=dict(
        baseline=baseline, variant=variant, knowledge_version=original["knowledge_version"]))
    assert response.status_code == 200
    result = response.json()
    assert result["baseline"] == original
    assert result["variant"] == expected
    assert len(result["changes"]) == 3
    ranks = {tool["tool_id"]: i for i, tool in enumerate(expected["recommendations"], 1)}
    for change in result["changes"]:
        assert change["before_rank"] is None
        assert change["before_match"] is None
        assert change["after_rank"] == ranks[change["tool_id"]]


def test_changed_answer_uses_same_evaluator_and_invalid_option_is_rejected(client):
    baseline = completed_request(client)
    variant = deepcopy(baseline)
    qid = baseline["answers"][0]["question_id"]
    question = next(q for q in client.app.state.knowledge.questions if q.id == qid)
    variant["answers"][0]["option_ids"] = [(question.options or question.text_intents)[1].id]
    original = client.post("/api/questionnaire/advance", json=baseline).json()
    expected = client.post("/api/questionnaire/advance", json=variant).json()
    request = dict(baseline=baseline, variant=variant, knowledge_version=original["knowledge_version"])
    result = client.post("/api/questionnaire/compare", json=request)
    assert result.status_code == 200
    assert result.json()["variant"] == expected
    assert result.json()["baseline"] == original
    variant["answers"][0]["option_ids"] = ["not-an-option"]
    assert client.post("/api/questionnaire/compare", json=request).status_code == 422


def test_profile_projection_localizes_guides_and_retains_evidence(client):
    tool = client.app.state.knowledge.tools[0]
    for language in ("ar", "en"):
        result = client.get(f"/api/tools/{tool.id}?language={language}")
        assert result.status_code == 200
        profile = result.json()["profile"]
        assert profile["deployment"] == getattr(tool.profile.deployment, language)
        assert profile["starter_guide"]["steps"][0]["instruction"] == getattr(tool.profile.starter_guide.steps[0].instruction, language)
        assert profile["offline"]["value"] == tool.profile.offline.value
        assert profile["reviewed_at"] == str(tool.profile.reviewed_at)
        assert profile["operation_setups"]
        projected_setup = profile["operation_setups"][0]
        source_setup = tool.profile.operation_setups[0]
        assert projected_setup["name"] == getattr(source_setup.name, language)
        assert projected_setup["task"] == getattr(source_setup.task, language)
        assert projected_setup["runtime_network"] == source_setup.runtime_network.value
        assert projected_setup["evidence"][0]["status"] == source_setup.evidence[0].status.value


def test_completed_recommendations_reference_the_eligible_setup(client):
    request = completed_request(client)

    response = client.post("/api/questionnaire/advance", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert all(item["matching_setup_id"] for item in body["recommendations"])
    for item in body["recommendations"]:
        tool = client.get(f"/api/tools/{item['tool_id']}?language=en").json()
        setup_ids = {setup["id"] for setup in tool["profile"]["operation_setups"]}
        assert item["matching_setup_id"] in setup_ids
