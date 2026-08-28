from datetime import date

import clips
import pytest
from pydantic import ValidationError

from app.domain.models import (
    AnswerOption,
    EvaluationSource,
    Language,
    LocalizedText,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    StageId,
    TextIntent,
    Tool,
)
from app.expert_engine.clipspy_adapter import ClipspyAdapter, _run_to_completion
from app.expert_engine.errors import InferenceLimitError, KnowledgeValidationError
from app.expert_engine.models import AnswerSelection, InferenceResult, ScoreEffect
from app.expert_engine.validation import validate_inference_input


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(ar=ar or en, en=en)


def source() -> EvaluationSource:
    return EvaluationSource(
        id="official-docs",
        name=localized("Official documentation"),
        publisher=localized("Example Foundation"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://example.com/official-docs",
        published_at=date(2026, 8, 1),
        collected_at=date(2026, 8, 23),
    )


def tool(tool_id: str = "tool-a") -> Tool:
    return Tool(
        id=tool_id,
        name=localized(f"Tool {tool_id}"),
        description=localized("A tool used by inference tests."),
        stages=[StageId.ANALYSIS],
    )


def question(
    question_id: str = "analysis-q1",
    question_type: QuestionType = QuestionType.SINGLE_CHOICE,
) -> Question:
    return Question(
        id=question_id,
        stage=StageId.ANALYSIS,
        prompt=localized("Choose an answer."),
        type=question_type,
        importance=0.8,
        options=[
            AnswerOption(id="yes", label=localized("Yes"), value=1.0),
            AnswerOption(id="no", label=localized("No"), value=-1.0),
        ],
    )


def rule(
    rule_id: str = "analysis-q1-yes",
    question_id: str = "analysis-q1",
    answer_option_id: str = "yes",
    tool_id: str = "tool-a",
    weight: float = 0.75,
) -> Rule:
    return Rule(
        id=rule_id,
        question_id=question_id,
        answer_option_id=answer_option_id,
        impacts=[
            RuleImpact(
                tool_id=tool_id,
                weight=weight,
                rationale=localized("The cited source supports this rule impact."),
                sources=[source()],
            )
        ],
    )


def selection(
    question_id: str = "analysis-q1", option_ids: list[str] | None = None
) -> AnswerSelection:
    return AnswerSelection(question_id=question_id, option_ids=option_ids or ["yes"])


def validate(
    *,
    tools: list[Tool] | None = None,
    questions: list[Question] | None = None,
    rules: list[Rule] | None = None,
    answers: list[AnswerSelection] | None = None,
):
    return validate_inference_input(
        tools=tools or [tool()],
        questions=questions or [question()],
        rules=rules or [rule()],
        answers=answers or [selection()],
    )


def test_inference_contracts_reject_duplicate_and_non_finite_values() -> None:
    with pytest.raises(ValidationError, match="option ids must be unique"):
        AnswerSelection(question_id="analysis-q1", option_ids=["yes", "yes"])

    with pytest.raises(ValidationError):
        ScoreEffect(tool_id="tool-a", rule_id="rule-a", value=float("inf"))

    with pytest.raises(ValidationError):
        InferenceResult(tool_scores={"tool-a": float("nan")})


def test_validate_inference_input_resolves_a_complete_slice() -> None:
    context = validate()

    assert context.tools_by_id["tool-a"].name.en == "Tool tool-a"
    assert context.rules[0].id == "analysis-q1-yes"
    assert context.answers[0].question.id == "analysis-q1"
    assert context.answers[0].options[0].id == "yes"


@pytest.mark.parametrize("duplicate", ["tool", "question", "rule", "answer"])
def test_validate_inference_input_rejects_duplicate_ids(duplicate: str) -> None:
    kwargs = {}
    if duplicate == "tool":
        kwargs["tools"] = [tool(), tool()]
    elif duplicate == "question":
        kwargs["questions"] = [question(), question()]
    elif duplicate == "rule":
        kwargs["rules"] = [rule(), rule()]
    else:
        kwargs["answers"] = [selection(), selection()]

    with pytest.raises(KnowledgeValidationError, match=f"duplicate {duplicate}"):
        validate(**kwargs)


@pytest.mark.parametrize(
    ("invalid_rule", "message"),
    [
        (rule(question_id="missing-q"), "unknown question"),
        (rule(answer_option_id="missing-option"), "unknown answer option"),
        (rule(tool_id="missing-tool"), "unknown tool"),
    ],
)
def test_validate_inference_input_rejects_dangling_rule_references(
    invalid_rule: Rule, message: str
) -> None:
    with pytest.raises(KnowledgeValidationError, match=message):
        validate(rules=[invalid_rule])


@pytest.mark.parametrize(
    ("invalid_answer", "message"),
    [
        (selection(question_id="missing-q"), "unknown question"),
        (selection(option_ids=["missing-option"]), "unknown answer option"),
    ],
)
def test_validate_inference_input_rejects_dangling_answer_references(
    invalid_answer: AnswerSelection, message: str
) -> None:
    with pytest.raises(KnowledgeValidationError, match=message):
        validate(answers=[invalid_answer])


@pytest.mark.parametrize(
    "question_type", [QuestionType.SINGLE_CHOICE, QuestionType.BOOLEAN]
)
def test_validate_inference_input_requires_one_answer_for_scalar_questions(
    question_type: QuestionType,
) -> None:
    with pytest.raises(KnowledgeValidationError, match="exactly one option"):
        validate(
            questions=[question(question_type=question_type)],
            answers=[selection(option_ids=["yes", "no"])],
        )


def test_validate_inference_input_accepts_multiple_choice_answers() -> None:
    context = validate(
        questions=[question(question_type=QuestionType.MULTIPLE_CHOICE)],
        answers=[selection(option_ids=["yes", "no"])],
    )

    assert [option.id for option in context.answers[0].options] == ["yes", "no"]


def test_clipspy_adapter_accepts_a_canonical_short_text_intent() -> None:
    short_text = Question(
        id="analysis-q1",
        stage=StageId.ANALYSIS,
        prompt=localized("Describe the workflow."),
        type=QuestionType.SHORT_TEXT,
        importance=0.8,
        text_intents=[
            TextIntent(
                id="describe",
                label=localized("Describe"),
                value=1.0,
                aliases={
                    Language.ARABIC: ["صف"],
                    Language.ENGLISH: ["describe"],
                },
            ),
            TextIntent(
                id="compare",
                label=localized("Compare"),
                value=0.5,
                aliases={
                    Language.ARABIC: ["قارن"],
                    Language.ENGLISH: ["compare"],
                },
            ),
        ],
    )

    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[short_text],
        rules=[rule(answer_option_id="describe")],
        answers=[selection(option_ids=["describe"])],
    )

    assert result.tool_scores == pytest.approx({"tool-a": 0.6})
    assert result.fired_rule_ids == ["analysis-q1-yes"]


def test_clipspy_adapter_executes_a_matching_rule() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[selection()],
    )

    assert result.tool_scores == pytest.approx({"tool-a": 0.6})
    assert [(effect.tool_id, effect.rule_id) for effect in result.effects] == [
        ("tool-a", "analysis-q1-yes")
    ]
    assert result.effects[0].value == pytest.approx(0.6)
    assert result.fired_rule_ids == ["analysis-q1-yes"]
    assert result.firing_count == 1


def test_clipspy_adapter_returns_zero_when_no_rule_matches() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[selection(option_ids=["no"])],
    )

    assert result.tool_scores == {"tool-a": 0.0}
    assert result.effects == []
    assert result.fired_rule_ids == []
    assert result.firing_count == 0


def test_clipspy_adapter_preserves_negative_score_effects() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(answer_option_id="no", weight=0.5)],
        answers=[selection(option_ids=["no"])],
    )

    assert result.tool_scores == pytest.approx({"tool-a": -0.4})
    assert result.effects[0].value == pytest.approx(-0.4)


def test_clipspy_adapter_reuse_does_not_leak_request_facts() -> None:
    adapter = ClipspyAdapter()

    first = adapter.infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[selection(option_ids=["yes"])],
    )
    second = adapter.infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[selection(option_ids=["no"])],
    )

    assert first.firing_count == 1
    assert second == InferenceResult(tool_scores={"tool-a": 0.0})


def test_clipspy_adapter_output_is_deterministic_for_reordered_inputs() -> None:
    tools = [tool("tool-b"), tool("tool-a")]
    rules = [
        rule(rule_id="rule-b", tool_id="tool-b", weight=0.25),
        rule(rule_id="rule-a", tool_id="tool-a", weight=0.75),
    ]
    adapter = ClipspyAdapter()

    first = adapter.infer(
        tools=tools,
        questions=[question()],
        rules=rules,
        answers=[selection()],
    )
    second = adapter.infer(
        tools=list(reversed(tools)),
        questions=[question()],
        rules=list(reversed(rules)),
        answers=[selection()],
    )

    assert first == second
    assert list(first.tool_scores) == ["tool-a", "tool-b"]
    assert [(effect.tool_id, effect.rule_id) for effect in first.effects] == [
        ("tool-a", "rule-a"),
        ("tool-b", "rule-b"),
    ]
    assert first.fired_rule_ids == ["rule-a", "rule-b"]


def test_clipspy_adapter_treats_hostile_identifiers_as_data() -> None:
    hostile_tool_id = 'tool-"quoted\\path'
    hostile_question_id = 'question-"quoted\\path'
    hostile_option_id = 'option-"quoted\\path'
    hostile_rule_id = 'rule-"quoted\\path'
    hostile_question = Question(
        id=hostile_question_id,
        stage=StageId.ANALYSIS,
        prompt=localized("Choose an answer."),
        type=QuestionType.SINGLE_CHOICE,
        importance=0.8,
        options=[
            AnswerOption(id=hostile_option_id, label=localized("Yes"), value=1.0),
            AnswerOption(id="no", label=localized("No"), value=-1.0),
        ],
    )

    result = ClipspyAdapter().infer(
        tools=[tool(hostile_tool_id)],
        questions=[hostile_question],
        rules=[
            rule(
                rule_id=hostile_rule_id,
                question_id=hostile_question_id,
                answer_option_id=hostile_option_id,
                tool_id=hostile_tool_id,
            )
        ],
        answers=[selection(hostile_question_id, [hostile_option_id])],
    )

    assert result.tool_scores == pytest.approx({hostile_tool_id: 0.6})
    assert result.fired_rule_ids == [hostile_rule_id]


def test_clipspy_adapter_handles_an_empty_rule_set() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[],
        answers=[selection()],
    )

    assert result == InferenceResult(tool_scores={"tool-a": 0.0})


def test_run_to_completion_rejects_a_self_reactivating_rule() -> None:
    environment = clips.Environment()
    environment.build("(deftemplate tick (slot value (type INTEGER)))")
    environment.build(
        "(defrule loop "
        "?tick <- (tick (value ?value)) "
        "=> "
        "(retract ?tick) "
        "(assert (tick (value (+ ?value 1)))))"
    )
    environment.find_template("tick").assert_fact(value=0)

    with pytest.raises(InferenceLimitError, match="firing limit"):
        _run_to_completion(environment, firing_limit=3)


def test_public_expert_engine_boundary_runs_real_inference() -> None:
    from app import expert_engine
    from app.expert_engine import (
        AnswerSelection as PublicAnswerSelection,
        ClipspyAdapter as PublicClipspyAdapter,
        InferenceResult as PublicInferenceResult,
    )

    result = PublicClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[PublicAnswerSelection(question_id="analysis-q1", option_ids=["yes"])],
    )

    assert isinstance(result, PublicInferenceResult)
    assert result.tool_scores == pytest.approx({"tool-a": 0.6})
    assert "compile_rule" not in expert_engine.__all__
    assert "clips" not in expert_engine.__all__
