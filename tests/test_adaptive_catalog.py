from collections import Counter
from pathlib import Path

from app.domain.models import DomainId, StageId
from app.knowledge import default_knowledge_path, load_knowledge
from scripts.build_adaptive_knowledge import (
    build_questions,
    main as build_adaptive_knowledge,
)


def test_builder_writes_a_loadable_gzip_catalog(tmp_path: Path) -> None:
    output = tmp_path / "adaptive.json.gz"

    exit_code = build_adaptive_knowledge(output)

    snapshot = load_knowledge(output)
    assert exit_code == 0
    assert output.read_bytes().startswith(b"\x1f\x8b")
    assert len(snapshot.tools) == 192
    assert len(snapshot.questions) == 672
    assert len(snapshot.rules) == 2016


def test_catalog_has_the_exact_stage_domain_matrix() -> None:
    snapshot = load_knowledge(default_knowledge_path())

    assert len(snapshot.tools) == 192
    assert len(snapshot.questions) == 672
    assert len(snapshot.rules) == 2016
    tool_cells = Counter((tool.stages[0], tool.domain) for tool in snapshot.tools)
    question_cells = Counter(
        (question.stage, question.domain) for question in snapshot.questions
    )
    expected_cells = {(stage, domain) for stage in StageId for domain in DomainId}
    assert set(tool_cells) == expected_cells
    assert set(question_cells) == expected_cells
    assert set(tool_cells.values()) == {16}
    assert set(question_cells.values()) == {56}


def test_catalog_tools_and_questions_have_reviewable_evidence() -> None:
    snapshot = load_knowledge(default_knowledge_path())

    assert all(tool.best_for is not None for tool in snapshot.tools)
    assert all(tool.limitations for tool in snapshot.tools)
    assert all(tool.source_url is not None for tool in snapshot.tools)
    assert all(tool.reviewed_at is not None for tool in snapshot.tools)
    assert all(question.dimension for question in snapshot.questions)
    assert all(question.sources for question in snapshot.questions)
    assert all(question.reviewed_at is not None for question in snapshot.questions)


def test_expanded_questions_use_axis_specific_primary_sources() -> None:
    expanded = [
        question
        for question in build_questions()
        if question.dimension.startswith("context_")
    ]

    assert len(expanded) == 4 * 3 * 42
    assert all(
        question.sources[0].kind.value
        in {"official_documentation", "vendor_documentation"}
        for question in expanded
    )
    assert all(
        question.sources[0].id
        not in {
            "iso-25010",
            "wcag-22",
            "nist-ssdf",
            "iso-25010-testing",
            "nist-ai-rmf",
            "nist-ai-playbook",
            "owasp-genai",
            "mitre-atlas",
            "nist-csf-20",
            "owasp-threat-modeling",
            "nist-ssdf-cyber",
            "owasp-wstg",
        }
        for question in expanded
    )


def test_every_answer_target_has_a_differentiating_same_pool_rule() -> None:
    snapshot = load_knowledge(default_knowledge_path())
    rules_by_target = {
        (rule.question_id, rule.answer_option_id): rule for rule in snapshot.rules
    }
    tools_by_id = {tool.id: tool for tool in snapshot.tools}

    for question in snapshot.questions:
        targets = [*question.options, *question.text_intents]
        for target in targets:
            rule = rules_by_target[(question.id, target.id)]
            assert len(rule.impacts) == 16
            assert any(impact.weight > 0 for impact in rule.impacts)
            assert any(impact.weight < 0 for impact in rule.impacts)
            for impact in rule.impacts:
                tool = tools_by_id[impact.tool_id]
                assert tool.stages == [question.stage]
                assert tool.domain is question.domain


def test_each_pool_has_question_order_variation_available() -> None:
    snapshot = load_knowledge(default_knowledge_path())
    dimensions = Counter(
        (question.stage, question.domain, question.dimension)
        for question in snapshot.questions
    )

    for stage in StageId:
        for domain in DomainId:
            pool_dimensions = {
                dimension
                for candidate_stage, candidate_domain, dimension in dimensions
                if candidate_stage is stage and candidate_domain is domain
            }
            assert len(pool_dimensions) >= 8
def test_preference_explanations_do_not_claim_unverified_capabilities():
    from scripts.build_adaptive_knowledge import build_rules

    rules = [rule for rule in build_rules() if rule.id.endswith("openness-open")]
    assert rules
    for rule in rules:
        for impact in rule.impacts:
            assert "preference" in impact.rationale.en
            assert "not proof" in impact.rationale.en
