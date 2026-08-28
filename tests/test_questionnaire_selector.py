from collections import Counter

from app.domain.models import DomainId, StageId
from app.knowledge import default_knowledge_path, load_knowledge
from app.questionnaire.selector import select_next_question


def pool():
    snapshot = load_knowledge(default_knowledge_path())
    tools = [
        tool
        for tool in snapshot.tools
        if tool.stages == [StageId.ANALYSIS] and tool.domain is DomainId.SOFTWARE
    ]
    questions = [
        question
        for question in snapshot.questions
        if question.stage is StageId.ANALYSIS
        and question.domain is DomainId.SOFTWARE
    ]
    rules = [
        rule
        for rule in snapshot.rules
        if any(question.id == rule.question_id for question in questions)
    ]
    return tools, questions, rules


def test_selector_is_deterministic_and_never_repeats_a_question() -> None:
    tools, questions, rules = pool()
    scores = {tool.id: 0.0 for tool in tools}

    first = select_next_question(
        questions=questions,
        rules=rules,
        tool_scores=scores,
        asked_question_ids=set(),
        seed="stable-session",
    )
    repeated = select_next_question(
        questions=questions,
        rules=rules,
        tool_scores=scores,
        asked_question_ids=set(),
        seed="stable-session",
    )
    second = select_next_question(
        questions=questions,
        rules=rules,
        tool_scores=scores,
        asked_question_ids={first.id},
        seed="stable-session",
    )

    assert first.id == repeated.id
    assert second.id != first.id


def test_selector_uses_the_seed_to_vary_near_equal_question_order() -> None:
    tools, questions, rules = pool()
    scores = {tool.id: 0.0 for tool in tools}

    selected = {
        select_next_question(
            questions=questions,
            rules=rules,
            tool_scores=scores,
            asked_question_ids=set(),
            seed=f"seed-{index}",
        ).id
        for index in range(20)
    }

    assert len(selected) >= 3


def test_selector_changes_focus_when_the_closest_tool_pair_changes() -> None:
    tools, questions, rules = pool()
    ids = [tool.id for tool in tools]
    first_scores = {ids[0]: 1.0, ids[1]: 0.95, ids[2]: -0.2, ids[3]: -1.0}
    second_scores = {ids[0]: 1.0, ids[1]: -0.2, ids[2]: 0.4, ids[3]: 0.39}

    first_questions = Counter(
        select_next_question(
            questions=questions,
            rules=rules,
            tool_scores=first_scores,
            asked_question_ids=set(),
            seed=f"focus-{index}",
        ).id
        for index in range(20)
    )
    second_questions = Counter(
        select_next_question(
            questions=questions,
            rules=rules,
            tool_scores=second_scores,
            asked_question_ids=set(),
            seed=f"focus-{index}",
        ).id
        for index in range(20)
    )

    assert first_questions != second_questions
