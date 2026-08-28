from collections import Counter

from app.domain.models import DomainId, StageId
from app.knowledge import default_knowledge_path, load_knowledge


def test_catalog_has_the_exact_stage_domain_matrix() -> None:
    snapshot = load_knowledge(default_knowledge_path())

    assert len(snapshot.tools) == 48
    assert len(snapshot.questions) == 168
    tool_cells = Counter((tool.stages[0], tool.domain) for tool in snapshot.tools)
    question_cells = Counter(
        (question.stage, question.domain) for question in snapshot.questions
    )
    expected_cells = {(stage, domain) for stage in StageId for domain in DomainId}
    assert set(tool_cells) == expected_cells
    assert set(question_cells) == expected_cells
    assert set(tool_cells.values()) == {4}
    assert set(question_cells.values()) == {14}


def test_catalog_tools_and_questions_have_reviewable_evidence() -> None:
    snapshot = load_knowledge(default_knowledge_path())

    assert all(tool.best_for is not None for tool in snapshot.tools)
    assert all(tool.limitations for tool in snapshot.tools)
    assert all(tool.source_url is not None for tool in snapshot.tools)
    assert all(tool.reviewed_at is not None for tool in snapshot.tools)
    assert all(question.dimension for question in snapshot.questions)
    assert all(question.sources for question in snapshot.questions)
    assert all(question.reviewed_at is not None for question in snapshot.questions)


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
            assert len(rule.impacts) == 4
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
