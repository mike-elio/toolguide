import pytest

from app.api.contracts import SubmittedAnswer
from app.domain.models import DomainId, Language, LocalizedText, StageId, Tool
from app.domain.tool_profiles import (
    CapabilityEvidence,
    EvidenceStatus,
    HardConstraints,
    NetworkRequirement,
    OperationSetup,
    SetupEvidence,
    ToolProfile,
)
from app.expert_engine import AnswerSelection, ClipspyAdapter
from app.knowledge import default_knowledge_path, load_knowledge
from app.questionnaire import QuestionnaireService
from app.questionnaire.eligibility import evaluate_eligibility, find_minimal_alternatives
from app.recommendations.ranking import rank_tools
from app.text_intent import AnswerResolutionService


def profile(value):
    text = {"ar": "مثال موثق", "en": "Documented example"}
    evidence = dict(value=value, source_url="https://example.com/", reviewed_at="2026-09-05")
    return ToolProfile.model_validate(dict(
        offline=evidence, free_plan=evidence, open_source=evidence,
        deployment=text, pricing_summary=text, learning_curve=text, integrations=[],
        sources=["https://example.com/"], reviewed_at="2026-09-05",
        starter_guide=dict(prerequisites=[], steps=[dict(instruction=text,
            source_url="https://example.com/")] * 3, example=text,
        expected_outcome=text, reviewed_at="2026-09-05")))


def setup(setup_id, *, offline, free, open_source, preparation_network):
    text = {"ar": "مثال موثق", "en": "Documented example"}
    source_url = f"https://example.com/{setup_id}"
    def capability(value):
        return dict(value=value, source_url=source_url, reviewed_at="2026-09-06")
    return OperationSetup.model_validate(dict(
        id=setup_id, name=text, task=text, stage="analysis", domain="software",
        platform=text, local_components=[text],
        preparation_network=preparation_network,
        runtime_network=(NetworkRequirement.NOT_REQUIRED if offline
                         else NetworkRequirement.REQUIRED),
        offline_features=[text] if offline else [], online_only_features=[],
        offline=capability(offline), free_plan=capability(free),
        open_source=capability(open_source),
        evidence_status=EvidenceStatus.OFFICIAL_DOCUMENTATION,
        evidence=[SetupEvidence(property="runtime", status="official_documentation",
                                source_url=source_url, summary=text, version_scope="1.x",
                                reviewed_at="2026-09-06", limitations=text)],
        starter_guide=dict(prerequisites=[text], steps=[dict(instruction=text,
            source_url=source_url)] * 3, example=text, expected_outcome=text,
            reviewed_at="2026-09-06")))


def tool_with_setups(*setups, tool_id="sample"):
    tool = Tool(id=tool_id, name=LocalizedText(ar=f"مثال {tool_id}", en=f"Example {tool_id}"),
                description=LocalizedText(ar="وصف", en="Description"),
                stages=[StageId.ANALYSIS], domain=DomainId.SOFTWARE)
    base = profile(None).model_dump(mode="python")
    base["operation_setups"] = list(setups)
    base["sources"] = list(dict.fromkeys([
        *base["sources"],
        *(claim.source_url for item in setups for claim in item.evidence),
    ]))
    tool.profile = ToolProfile.model_validate(base)
    return tool


def test_no_match_alternatives_use_one_documented_setup_and_minimum_changes():
    one_change = tool_with_setups(
        setup("local-paid", offline=True, free=False, open_source=True,
              preparation_network=NetworkRequirement.NOT_REQUIRED),
        tool_id="one-change",
    )
    two_changes = tool_with_setups(
        setup("online-paid", offline=False, free=False, open_source=True,
              preparation_network=NetworkRequirement.NOT_REQUIRED),
        tool_id="two-changes",
    )
    undocumented = tool_with_setups(
        setup("unknown", offline=None, free=True, open_source=True,
              preparation_network=NetworkRequirement.UNKNOWN),
        tool_id="undocumented",
    )

    alternatives = find_minimal_alternatives(
        [two_changes, undocumented, one_change],
        HardConstraints(requires_offline=True, requires_free_plan=True),
    )

    assert [(item.tool_id, item.setup_id, item.changed_constraints) for item in alternatives] == [
        ("one-change", "local-paid", ["requires_free_plan"])
    ]


def test_unknown_is_not_false_and_neither_satisfies_requirement():
    tool = Tool(id="sample", name=LocalizedText(ar="مثال", en="Example"),
                description=LocalizedText(ar="وصف", en="Description"),
                stages=[StageId.ANALYSIS])
    assert evaluate_eligibility(tool, HardConstraints()).eligible
    result = evaluate_eligibility(tool, HardConstraints(requires_offline=True))
    assert not result.eligible
    assert result.unknown_constraints == ["requires_offline"]
    tool.profile = profile(False)
    result = evaluate_eligibility(tool, HardConstraints(requires_offline=True))
    assert result.failed_constraints == ["requires_offline"]
    assert result.unknown_constraints == []
    tool.profile = profile(True)
    assert evaluate_eligibility(tool, HardConstraints(requires_offline=True)).eligible


def test_constraints_must_be_satisfied_by_one_operation_setup():
    tool = tool_with_setups(
        setup("offline-paid", offline=True, free=False, open_source=True,
              preparation_network=NetworkRequirement.REQUIRED),
        setup("online-free", offline=False, free=True, open_source=True,
              preparation_network=NetworkRequirement.NOT_REQUIRED),
    )

    result = evaluate_eligibility(
        tool,
        HardConstraints(requires_offline=True, requires_free_plan=True,
                        requires_open_source=True, allows_online_preparation=True),
    )

    assert not result.eligible
    assert result.matching_setup_id is None


def test_online_preparation_is_an_explicit_offline_constraint():
    tool = tool_with_setups(
        setup("predownloaded", offline=True, free=True, open_source=True,
              preparation_network=NetworkRequirement.REQUIRED)
    )

    without_preparation = evaluate_eligibility(
        tool, HardConstraints(requires_offline=True, requires_free_plan=True)
    )
    with_preparation = evaluate_eligibility(
        tool, HardConstraints(requires_offline=True, requires_free_plan=True,
                              allows_online_preparation=True)
    )

    assert not without_preparation.eligible
    assert "allows_online_preparation" in without_preparation.failed_constraints
    assert with_preparation.eligible
    assert with_preparation.matching_setup_id == "predownloaded"


def test_setup_from_another_domain_cannot_qualify_or_be_an_alternative():
    foreign = setup("foreign", offline=True, free=False, open_source=True,
                    preparation_network=NetworkRequirement.NOT_REQUIRED)
    foreign.domain = "cybersecurity"
    tool = tool_with_setups(foreign)
    constraints = HardConstraints(requires_offline=True, requires_free_plan=True)
    result = evaluate_eligibility(tool, constraints)
    assert not result.eligible
    assert result.matching_setup_id is None
    assert find_minimal_alternatives([tool], constraints) == []


def test_setup_from_another_stage_cannot_qualify():
    foreign = setup("foreign", offline=True, free=True, open_source=True,
                    preparation_network=NetworkRequirement.NOT_REQUIRED)
    foreign.stage = "testing"
    result = evaluate_eligibility(tool_with_setups(foreign), HardConstraints(requires_offline=True))
    assert not result.eligible


@pytest.mark.parametrize("eligible_count", range(5))
def test_filtered_pool_uses_full_rules_and_finishes_with_only_eligible_tools(eligible_count):
    knowledge = load_knowledge(default_knowledge_path()).model_copy(deep=True)
    tools = [tool for tool in knowledge.tools if tool.stages == [StageId.ANALYSIS]
             and tool.domain is DomainId.SOFTWARE]
    for index, tool in enumerate(tools):
        tool.profile = profile(index < eligible_count)
    eligible_ids = {tool.id for tool in tools[:eligible_count]}
    questions = [q for q in knowledge.questions if q.stage is StageId.ANALYSIS
                 and q.domain is DomainId.SOFTWARE]
    service = QuestionnaireService()
    asked, answers = [], []
    for _ in range(11):
        result = service.advance(knowledge=knowledge, resolver=AnswerResolutionService(),
            language=Language.ENGLISH, stage=StageId.ANALYSIS, domain=DomainId.SOFTWARE,
            session_seed="eligibility", asked_question_ids=asked, submitted_answers=answers,
            constraints=HardConstraints(requires_offline=True))
        if result.status.value in ("complete", "no_match"):
            break
        q = result.question
        asked.append(q.id)
        if q.text_intents:
            answers.append(SubmittedAnswer(question_id=q.id, option_ids=[q.text_intents[0].id]))
        else:
            answers.append(SubmittedAnswer(question_id=q.id, option_ids=[q.options[0].id]))
    assert result.eligible_count == eligible_count
    assert len(result.recommendations) == min(3, eligible_count)
    assert {item.tool_id for item in result.recommendations} <= eligible_ids
    if eligible_count:
        assert 6 <= result.answered_count <= 10
        rules = [rule for rule in knowledge.rules if rule.question_id in {q.id for q in questions}]
        inference = ClipspyAdapter().infer(tools=tools, questions=questions, rules=rules,
            answers=[AnswerSelection(question_id=a.question_id, option_ids=a.option_ids) for a in answers])
        expected = [item.tool.id for item in rank_tools(tools=tools, inference_result=inference)
                    if item.tool.id in eligible_ids][:3]
        assert [item.tool_id for item in result.recommendations] == expected
        if eligible_count < 4:
            assert all(item.confidence.value == "low" for item in result.recommendations)
    else:
        assert result.status.value == "no_match"


def test_source_version_changes_when_profile_changes():
    knowledge = load_knowledge(default_knowledge_path()).model_copy(deep=True)
    original = knowledge.version
    knowledge.tools[0].profile = profile(True)
    assert knowledge.version != original
