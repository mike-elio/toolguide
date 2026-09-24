# CLIPSpy Inference Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a sourced, isolated CLIPSpy inference layer that converts validated domain knowledge and selected answers into deterministic raw tool scores and fired-rule identifiers.

**Architecture:** Pydantic remains the auditable knowledge contract. A validation module resolves all cross-file references before a compiler creates a fresh CLIPS environment for one request; the adapter asserts typed facts, runs the agenda with a finite limit, extracts immutable score effects, and discards the environment.

**Tech Stack:** Python 3.12, Pydantic 2, clipspy 1.0.6, CLIPS 6.4 semantics, pytest 8.

**Spec:** `docs/superpowers/specs/2026-08-23-clipspy-inference-layer-design.md`

## Global Constraints

- Create one `clips.Environment` per inference call; never retain it on the adapter.
- Use real CLIPSpy environments in tests; do not mock CLIPS rule matching.
- Do not rank tools, break ties, create recommendation prose, load JSON, or add HTTP routes.
- Every `RuleImpact` requires a rationale and at least one classified evidence source.
- Treat official documentation and repositories as primary technical evidence; treat GitHub discussions and Reddit as supporting practitioner evidence only.
- Never derive a numeric rule weight from a community report alone.
- Do not depend on CLIPS agenda ordering for correctness or returned ordering.
- Reject dangling references and unsupported short-text scoring before creating an environment.
- Do not interpolate unchecked external identifiers into CLIPS constructs.
- Preserve the existing public error-envelope behavior and all phase-1/phase-2 tests.

---

### Task 1: Make rule effects auditable

**Files:**
- Modify: `app/domain/models.py`
- Modify: `tests/test_domain_models.py`

**Interfaces:**
- Produces: `SourceKind(StrEnum)`
- Produces: `EvaluationSource.publisher`, `kind`, and optional `published_at`
- Produces: `RuleImpact.rationale` and `sources`

- [ ] **Step 1: Update existing valid fixtures with explicit evidence**

Add a focused helper in `tests/test_domain_models.py`:

```python
def evaluation_source(source_id: str = "clips-guide") -> EvaluationSource:
    return EvaluationSource(
        id=source_id,
        name="CLIPS Basic Programming Guide",
        publisher="Secret Society Software",
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://www.clipsrules.net/documentation/v642/bpg642.pdf",
        published_at=date(2025, 1, 16),
        collected_at=date(2026, 8, 23),
    )
```

Update every existing `RuleImpact` fixture to include:

```python
rationale="The selected answer is supported by the cited capability evidence.",
sources=[evaluation_source()],
```

Update existing `EvaluationSource` fixtures with `publisher` and `kind`.

- [ ] **Step 2: Write failing provenance tests**

```python
def test_rule_impact_requires_a_rationale_and_source() -> None:
    payload = {"tool_id": "tool-a", "weight": 0.75}

    with pytest.raises(ValidationError):
        RuleImpact.model_validate(payload)


def test_rule_impact_rejects_duplicate_source_ids() -> None:
    source = evaluation_source()

    with pytest.raises(ValidationError, match="source ids must be unique"):
        RuleImpact(
            tool_id="tool-a",
            weight=0.75,
            rationale="Supported by the cited capability evidence.",
            sources=[source, source],
        )
```

- [ ] **Step 3: Run the domain-model tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests\test_domain_models.py -v`

Expected: collection or validation failures because `SourceKind`, source metadata, and rule-impact provenance do not exist.

- [ ] **Step 4: Implement the evidence contract**

Add to `app/domain/models.py`:

```python
class SourceKind(StrEnum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    OFFICIAL_REPOSITORY = "official_repository"
    PRIMARY_RESEARCH = "primary_research"
    PEER_REVIEWED_RESEARCH = "peer_reviewed_research"
    PUBLISHED_BENCHMARK = "published_benchmark"
    VENDOR_DOCUMENTATION = "vendor_documentation"
    PRACTITIONER_REPORT = "practitioner_report"


class EvaluationSource(DomainModel):
    id: Identifier
    name: NonEmptyText
    publisher: NonEmptyText
    kind: SourceKind
    url: HttpUrl
    published_at: date | None = None
    collected_at: date


class RuleImpact(DomainModel):
    tool_id: Identifier
    weight: float = Field(gt=0.0, le=1.0, allow_inf_nan=False)
    rationale: NonEmptyText
    sources: list[EvaluationSource] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_sources(self) -> Self:
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")
        return self
```

Move `EvaluationSource` above `RuleImpact` so the runtime annotation resolves without a
forward-reference string. Keep `Benchmark.sources` typed as `list[EvaluationSource]`.

- [ ] **Step 5: Verify Task 1 GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests\test_domain_models.py -v`

Expected: all domain-model tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add app/domain/models.py tests/test_domain_models.py
git commit -m "feat: require evidence for rule impacts"
```

---

### Task 2: Define inference contracts and validate references

**Files:**
- Create: `app/expert_engine/errors.py`
- Create: `app/expert_engine/models.py`
- Create: `app/expert_engine/validation.py`
- Create: `tests/test_expert_engine.py`

**Interfaces:**
- Consumes: `Tool`, `Question`, `QuestionType`, `Rule`
- Produces: `AnswerSelection(question_id: str, option_ids: list[str])`
- Produces: `ScoreEffect(tool_id: str, rule_id: str, value: float)`
- Produces: `InferenceResult(tool_scores, effects, fired_rule_ids, firing_count)`
- Produces: `validate_inference_input(...) -> InferenceContext`
- Raises: `KnowledgeValidationError`

- [ ] **Step 1: Write failing contract and reference tests**

Create `tests/test_expert_engine.py` with factories for one tool, one two-option question,
one sourced rule, and one answer. Add these tests:

```python
def source() -> EvaluationSource:
    return EvaluationSource(
        id="clips-guide",
        name="CLIPS Basic Programming Guide",
        publisher="Secret Society Software",
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://www.clipsrules.net/documentation/v642/bpg642.pdf",
        published_at=date(2025, 1, 16),
        collected_at=date(2026, 8, 23),
    )


def tool(tool_id: str = "tool-a") -> Tool:
    return Tool(
        id=tool_id,
        name="Tool A",
        description="Analyzes requirements.",
        stages=[StageId.ANALYSIS],
    )


def question(
    question_id: str = "q1",
    question_type: QuestionType = QuestionType.SINGLE_CHOICE,
) -> Question:
    return Question(
        id=question_id,
        stage=StageId.ANALYSIS,
        prompt="Do you need requirements analysis?",
        type=question_type,
        importance=0.8,
        options=[
            AnswerOption(id="yes", label="Yes", value=1.0),
            AnswerOption(id="no", label="No", value=-1.0),
        ],
    )


def rule(
    *,
    question_id: str = "q1",
    option_id: str = "yes",
    tool_id: str = "tool-a",
    weight: float = 0.75,
) -> Rule:
    return Rule(
        id=f"rule-{question_id}-{option_id}",
        question_id=question_id,
        answer_option_id=option_id,
        impacts=[
            RuleImpact(
                tool_id=tool_id,
                weight=weight,
                rationale="Supported by the cited capability evidence.",
                sources=[source()],
            )
        ],
    )


def test_validation_resolves_a_complete_inference_input() -> None:
    context = validate_inference_input(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[AnswerSelection(question_id="q1", option_ids=["yes"])],
    )

    assert context.tools_by_id["tool-a"].name == "Tool A"
    assert context.questions_by_id["q1"].importance == 0.8
    assert context.resolved_answers[0].value == 1.0


def test_validation_rejects_a_rule_with_an_unknown_question() -> None:
    with pytest.raises(KnowledgeValidationError, match="unknown question"):
        validate_inference_input(
            [tool()],
            [question()],
            [rule(question_id="missing")],
            [AnswerSelection(question_id="q1", option_ids=["yes"])],
        )


def test_validation_rejects_a_rule_with_an_unknown_option() -> None:
    with pytest.raises(KnowledgeValidationError, match="unknown option"):
        validate_inference_input(
            [tool()],
            [question()],
            [rule(option_id="missing")],
            [AnswerSelection(question_id="q1", option_ids=["yes"])],
        )


def test_validation_rejects_an_impact_with_an_unknown_tool() -> None:
    with pytest.raises(KnowledgeValidationError, match="unknown tool"):
        validate_inference_input(
            [tool()],
            [question()],
            [rule(tool_id="missing")],
            [AnswerSelection(question_id="q1", option_ids=["yes"])],
        )


def test_validation_rejects_an_answer_with_an_unknown_question() -> None:
    with pytest.raises(KnowledgeValidationError, match="unknown question"):
        validate_inference_input(
            [tool()],
            [question()],
            [rule()],
            [AnswerSelection(question_id="missing", option_ids=["yes"])],
        )


def test_validation_rejects_an_answer_with_an_unknown_option() -> None:
    with pytest.raises(KnowledgeValidationError, match="unknown option"):
        validate_inference_input(
            [tool()],
            [question()],
            [rule()],
            [AnswerSelection(question_id="q1", option_ids=["missing"])],
        )
```

Add the duplicate-ID and selection-cardinality tests explicitly:

```python
def test_validation_rejects_duplicate_collection_ids() -> None:
    answer = AnswerSelection(question_id="q1", option_ids=["yes"])

    with pytest.raises(KnowledgeValidationError, match="duplicate tool"):
        validate_inference_input([tool(), tool()], [question()], [rule()], [answer])
    with pytest.raises(KnowledgeValidationError, match="duplicate question"):
        validate_inference_input([tool()], [question(), question()], [rule()], [answer])
    with pytest.raises(KnowledgeValidationError, match="duplicate rule"):
        validate_inference_input([tool()], [question()], [rule(), rule()], [answer])
    with pytest.raises(KnowledgeValidationError, match="duplicate answer"):
        validate_inference_input([tool()], [question()], [rule()], [answer, answer])


def test_answer_selection_rejects_duplicate_options() -> None:
    with pytest.raises(ValidationError, match="option ids must be unique"):
        AnswerSelection(question_id="q1", option_ids=["yes", "yes"])


@pytest.mark.parametrize(
    "question_type",
    [QuestionType.SINGLE_CHOICE, QuestionType.BOOLEAN],
)
def test_validation_rejects_multiple_options_for_single_value_questions(
    question_type: QuestionType,
) -> None:
    selected_question = question(question_type=question_type)

    with pytest.raises(KnowledgeValidationError, match="exactly one option"):
        validate_inference_input(
            [tool()],
            [selected_question],
            [rule()],
            [AnswerSelection(question_id="q1", option_ids=["yes", "no"])],
        )


def test_validation_rejects_short_text_scoring() -> None:
    text_question = Question(
        id="q1",
        stage=StageId.ANALYSIS,
        prompt="Describe the workflow.",
        type=QuestionType.SHORT_TEXT,
        importance=0.8,
    )

    with pytest.raises(KnowledgeValidationError, match="short-text"):
        validate_inference_input(
            [tool()],
            [text_question],
            [],
            [AnswerSelection(question_id="q1", option_ids=["text-answer"])],
        )
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py -v`

Expected: import failure because the expert-engine contracts and validator do not exist.

- [ ] **Step 3: Implement strict inference models and errors**

In `app/expert_engine/errors.py`:

```python
class ExpertEngineError(RuntimeError):
    """Base error for the expert-engine boundary."""


class KnowledgeValidationError(ExpertEngineError):
    """The knowledge slice contains inconsistent references."""


class InferenceBuildError(ExpertEngineError):
    """CLIPS rejected a generated construct."""


class InferenceExecutionError(ExpertEngineError):
    """CLIPS failed while asserting facts or running inference."""


class InferenceLimitError(ExpertEngineError):
    """The CLIPS agenda did not drain within the firing limit."""
```

In `app/expert_engine/models.py`, implement:

```python
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class AnswerSelection(DomainModel):
    question_id: Identifier
    option_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_options(self) -> Self:
        if len(self.option_ids) != len(set(self.option_ids)):
            raise ValueError("option ids must be unique")
        return self


class ScoreEffect(DomainModel):
    tool_id: Identifier
    rule_id: Identifier
    value: FiniteFloat


class InferenceResult(DomainModel):
    tool_scores: dict[Identifier, FiniteFloat]
    effects: list[ScoreEffect]
    fired_rule_ids: list[Identifier]
    firing_count: int = Field(ge=0)
```

- [ ] **Step 4: Implement reference resolution**

In `app/expert_engine/validation.py`, define immutable internal records:

```python
@dataclass(frozen=True)
class ResolvedAnswer:
    question_id: str
    option_id: str
    value: float
    importance: float


@dataclass(frozen=True)
class InferenceContext:
    tools_by_id: dict[str, Tool]
    questions_by_id: dict[str, Question]
    rules: tuple[Rule, ...]
    resolved_answers: tuple[ResolvedAnswer, ...]
```

Implement `_index_unique` and `validate_inference_input` with this control flow:

```python
def _index_unique(items, *, kind: str) -> dict[str, object]:
    indexed = {}
    for item in items:
        if item.id in indexed:
            raise KnowledgeValidationError(f"duplicate {kind} id: {item.id}")
        indexed[item.id] = item
    return indexed


def validate_inference_input(
    tools: Sequence[Tool],
    questions: Sequence[Question],
    rules: Sequence[Rule],
    answers: Sequence[AnswerSelection],
) -> InferenceContext:
    tools_by_id = _index_unique(tools, kind="tool")
    questions_by_id = _index_unique(questions, kind="question")
    rules_by_id = _index_unique(rules, kind="rule")

    for rule_item in rules_by_id.values():
        selected_question = questions_by_id.get(rule_item.question_id)
        if selected_question is None:
            raise KnowledgeValidationError(
                f"rule {rule_item.id} references unknown question {rule_item.question_id}"
            )
        option_ids = {option.id for option in selected_question.options}
        if rule_item.answer_option_id not in option_ids:
            raise KnowledgeValidationError(
                f"rule {rule_item.id} references unknown option "
                f"{rule_item.answer_option_id}"
            )
        for impact in rule_item.impacts:
            if impact.tool_id not in tools_by_id:
                raise KnowledgeValidationError(
                    f"rule {rule_item.id} references unknown tool {impact.tool_id}"
                )

    answers_by_question = {}
    resolved_answers = []
    for answer in answers:
        if answer.question_id in answers_by_question:
            raise KnowledgeValidationError(
                f"duplicate answer for question {answer.question_id}"
            )
        answers_by_question[answer.question_id] = answer
        selected_question = questions_by_id.get(answer.question_id)
        if selected_question is None:
            raise KnowledgeValidationError(
                f"answer references unknown question {answer.question_id}"
            )
        if selected_question.type is QuestionType.SHORT_TEXT:
            raise KnowledgeValidationError(
                f"short-text scoring is unsupported for question {answer.question_id}"
            )
        if selected_question.type in {
            QuestionType.SINGLE_CHOICE,
            QuestionType.BOOLEAN,
        } and len(answer.option_ids) != 1:
            raise KnowledgeValidationError(
                f"question {answer.question_id} requires exactly one option"
            )
        options_by_id = {option.id: option for option in selected_question.options}
        for option_id in answer.option_ids:
            option = options_by_id.get(option_id)
            if option is None:
                raise KnowledgeValidationError(
                    f"answer references unknown option {option_id}"
                )
            resolved_answers.append(
                ResolvedAnswer(
                    question_id=answer.question_id,
                    option_id=option.id,
                    value=option.value,
                    importance=selected_question.importance,
                )
            )

    return InferenceContext(
        tools_by_id=tools_by_id,
        questions_by_id=questions_by_id,
        rules=tuple(rules_by_id.values()),
        resolved_answers=tuple(resolved_answers),
    )
```

- [ ] **Step 5: Verify Task 2 GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py -v`

Expected: all contract and validation tests pass without importing `clips`.

- [ ] **Step 6: Commit Task 2**

```powershell
git add app/expert_engine/errors.py app/expert_engine/models.py app/expert_engine/validation.py tests/test_expert_engine.py
git commit -m "feat: validate expert-engine inference inputs"
```

---

### Task 3: Compile and execute one real CLIPS rule

**Files:**
- Create: `app/expert_engine/compiler.py`
- Create: `app/expert_engine/clipspy_adapter.py`
- Modify: `tests/test_expert_engine.py`

**Interfaces:**
- Consumes: `InferenceContext`
- Produces: `compile_environment(context: InferenceContext) -> clips.Environment`
- Produces: `ClipspyAdapter.infer(...) -> InferenceResult`

- [ ] **Step 1: Write the failing real-engine test**

```python
def test_matching_answer_fires_rule_and_emits_raw_score() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(weight=0.75)],
        answers=[AnswerSelection(question_id="q1", option_ids=["yes"])],
    )

    assert result.firing_count == 1
    assert result.fired_rule_ids == ["rule-q1-yes"]
    assert [(effect.tool_id, effect.rule_id) for effect in result.effects] == [
        ("tool-a", "rule-q1-yes")
    ]
    assert result.effects[0].value == pytest.approx(0.6)
    assert result.tool_scores["tool-a"] == pytest.approx(0.6)
```

The expected value is the hand-derived literal `1.0 * 0.8 * 0.75 = 0.6`.

- [ ] **Step 2: Run the test and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py::test_matching_answer_fires_rule_and_emits_raw_score -v`

Expected: import failure because the compiler and adapter do not exist.

- [ ] **Step 3: Implement templates and rule compilation**

In `app/expert_engine/compiler.py`, define the templates and safe encoders:

```python
TEMPLATE_CONSTRUCTS = (
    "(deftemplate tool (slot tool-id (type STRING)))",
    """(deftemplate selected-answer
      (slot question-id (type STRING))
      (slot option-id (type STRING))
      (slot answer-value (type FLOAT))
      (slot importance (type FLOAT)))""",
    """(deftemplate score-effect
      (slot tool-id (type STRING))
      (slot rule-id (type STRING))
      (slot value (type FLOAT)))""",
    "(deftemplate rule-fired (slot rule-id (type STRING)))",
)


def clips_rule_name(rule_id: str) -> str:
    digest = hashlib.sha256(rule_id.encode("utf-8")).hexdigest()
    return f"domain_rule_{digest}"


def clips_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'
```

Compile each rule with:

```python
def compile_rule(rule: Rule) -> str:
    actions = [
        "(assert (score-effect "
        f"(tool-id {clips_string(impact.tool_id)}) "
        f"(rule-id {clips_string(rule.id)}) "
        f"(value (* ?answer-value ?importance {impact.weight!r}))))"
        for impact in rule.impacts
    ]
    actions.append(
        f"(assert (rule-fired (rule-id {clips_string(rule.id)})))"
    )
    return "\n".join(
        [
            f"(defrule {clips_rule_name(rule.id)}",
            "  (selected-answer",
            f"    (question-id {clips_string(rule.question_id)})",
            f"    (option-id {clips_string(rule.answer_option_id)})",
            "    (answer-value ?answer-value)",
            "    (importance ?importance))",
            "  =>",
            *(f"  {action}" for action in actions),
            ")",
        ]
    )


def compile_environment(context: InferenceContext) -> clips.Environment:
    environment = clips.Environment()
    try:
        for construct in TEMPLATE_CONSTRUCTS:
            environment.build(construct)
        for rule in context.rules:
            environment.build(compile_rule(rule))
    except clips.CLIPSError as exc:
        raise InferenceBuildError("CLIPS rejected a generated construct") from exc
    return environment
```

This wrapper must not embed generated CLIPS source in the public error message.

- [ ] **Step 4: Implement minimal adapter execution**

In `app/expert_engine/clipspy_adapter.py`, implement the minimal adapter:

```python
class ClipspyAdapter:
    def infer(
        self,
        *,
        tools: Sequence[Tool],
        questions: Sequence[Question],
        rules: Sequence[Rule],
        answers: Sequence[AnswerSelection],
    ) -> InferenceResult:
        context = validate_inference_input(tools, questions, rules, answers)
        environment = compile_environment(context)
        try:
            tool_template = environment.find_template("tool")
            for tool_id in sorted(context.tools_by_id):
                tool_template.assert_fact(**{"tool-id": tool_id})

            answer_template = environment.find_template("selected-answer")
            for answer in context.resolved_answers:
                answer_template.assert_fact(
                    **{
                        "question-id": answer.question_id,
                        "option-id": answer.option_id,
                        "answer-value": answer.value,
                        "importance": answer.importance,
                    }
                )

            firing_count = (
                environment.run(limit=len(context.rules)) if context.rules else 0
            )
            effects = [
                ScoreEffect(
                    tool_id=str(fact["tool-id"]),
                    rule_id=str(fact["rule-id"]),
                    value=float(fact["value"]),
                )
                for fact in environment.find_template("score-effect").facts()
            ]
            fired_rule_ids = {
                str(fact["rule-id"])
                for fact in environment.find_template("rule-fired").facts()
            }
        except clips.CLIPSError as exc:
            raise InferenceExecutionError("CLIPS inference failed") from exc

        effects.sort(key=lambda effect: (effect.tool_id, effect.rule_id))
        tool_scores = {}
        for tool_id in sorted(context.tools_by_id):
            tool_scores[tool_id] = math.fsum(
                effect.value for effect in effects if effect.tool_id == tool_id
            )
        return InferenceResult(
            tool_scores=tool_scores,
            effects=effects,
            fired_rule_ids=sorted(fired_rule_ids),
            firing_count=firing_count,
        )
```

- [ ] **Step 5: Verify Task 3 GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py::test_matching_answer_fires_rule_and_emits_raw_score -v`

Expected: PASS using the installed clipspy 1.0.6 native engine.

- [ ] **Step 6: Commit Task 3**

```powershell
git add app/expert_engine/compiler.py app/expert_engine/clipspy_adapter.py tests/test_expert_engine.py
git commit -m "feat: execute sourced rules with CLIPSpy"
```

---

### Task 4: Prove non-matches, determinism, isolation, and firing limits

**Files:**
- Modify: `app/expert_engine/compiler.py`
- Modify: `app/expert_engine/clipspy_adapter.py`
- Modify: `tests/test_expert_engine.py`

**Interfaces:**
- Produces: `_run_to_completion(environment, firing_limit) -> int`
- Preserves: `ClipspyAdapter.infer(...) -> InferenceResult`

- [ ] **Step 1: Write failing behavioral tests**

Add tests that prove:

```python
def test_non_matching_rule_returns_zero_score_and_no_fired_rule() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(option_id="yes")],
        answers=[AnswerSelection(question_id="q1", option_ids=["no"])],
    )
    assert result.tool_scores == {"tool-a": 0.0}
    assert result.effects == []
    assert result.fired_rule_ids == []
    assert result.firing_count == 0


def test_negative_answer_value_produces_a_negative_effect() -> None:
    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(option_id="no", weight=0.5)],
        answers=[AnswerSelection(question_id="q1", option_ids=["no"])],
    )
    assert result.tool_scores["tool-a"] == pytest.approx(-0.4)


def test_reusing_adapter_does_not_leak_facts_between_calls() -> None:
    adapter = ClipspyAdapter()
    first = adapter.infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(option_id="yes")],
        answers=[AnswerSelection(question_id="q1", option_ids=["yes"])],
    )
    second = adapter.infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule(option_id="yes")],
        answers=[AnswerSelection(question_id="q1", option_ids=["no"])],
    )

    assert first.fired_rule_ids == ["rule-q1-yes"]
    assert second.fired_rule_ids == []
    assert second.tool_scores == {"tool-a": 0.0}
```

Add a multi-tool/multi-rule test whose inputs are deliberately reversed:

```python
def test_results_are_deterministic_for_multiple_tools_and_rules() -> None:
    rules = [
        rule(tool_id="tool-b", weight=0.5),
        Rule(
            id="rule-q1-yes-a",
            question_id="q1",
            answer_option_id="yes",
            impacts=[
                RuleImpact(
                    tool_id="tool-a",
                    weight=0.75,
                    rationale="Supported by evidence.",
                    sources=[source()],
                )
            ],
        ),
    ]
    result = ClipspyAdapter().infer(
        tools=[tool("tool-b"), tool("tool-a")],
        questions=[question()],
        rules=rules,
        answers=[AnswerSelection(question_id="q1", option_ids=["yes"])],
    )

    assert list(result.tool_scores) == ["tool-a", "tool-b"]
    assert result.fired_rule_ids == ["rule-q1-yes", "rule-q1-yes-a"]
    assert [(effect.tool_id, effect.rule_id) for effect in result.effects] == [
        ("tool-a", "rule-q1-yes-a"),
        ("tool-b", "rule-q1-yes"),
    ]
```

Add an adversarial identifier test containing quotes and backslashes:

```python
def test_external_identifiers_cannot_inject_clips_constructs() -> None:
    hostile_id = 'q1\\" ) (defrule injected => (assert (rule-fired (rule-id "bad")))) ;'
    hostile_question = question(question_id=hostile_id)
    hostile_rule = rule(question_id=hostile_id)

    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[hostile_question],
        rules=[hostile_rule],
        answers=[AnswerSelection(question_id=hostile_id, option_ids=["yes"])],
    )

    assert result.fired_rule_ids == [f"rule-{hostile_id}-yes"]
    assert result.firing_count == 1
```

- [ ] **Step 2: Write a real firing-limit test**

Build a real standalone CLIPS environment with a self-reactivating rule:

```python
def test_run_to_completion_rejects_an_undrained_agenda() -> None:
    environment = clips.Environment()
    environment.build("(deftemplate counter (slot value (type INTEGER)))")
    environment.build(
        """(defrule increment-forever
        ?counter <- (counter (value ?value))
        =>
        (modify ?counter (value (+ ?value 1))))"""
    )
    environment.find_template("counter").assert_fact(value=0)

    with pytest.raises(InferenceLimitError, match="firing limit"):
        _run_to_completion(environment, 1)
```

This tests the guard with CLIPS behavior rather than a mock.

- [ ] **Step 3: Run the new tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py -v`

Expected: failures for missing deterministic multi-effect handling, firing-limit helper,
or isolation behavior not yet implemented.

- [ ] **Step 4: Implement the minimum hardening needed**

Extract `_run_to_completion` so it:

```python
firing_count = environment.run(limit=firing_limit)
if next(environment.activations(), None) is not None:
    raise InferenceLimitError("CLIPS agenda exceeded the firing limit")
return firing_count
```

Handle the zero-rule case without calling `run(limit=0)`. Keep environment creation inside
`infer`, ensure aggregation starts from a fresh dictionary each call, and sort all output
collections before constructing `InferenceResult`.

- [ ] **Step 5: Verify Task 4 GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py -v`

Expected: all expert-engine tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add app/expert_engine/compiler.py app/expert_engine/clipspy_adapter.py tests/test_expert_engine.py
git commit -m "test: harden CLIPSpy inference isolation"
```

---

### Task 5: Export the boundary and verify the complete backend

**Files:**
- Modify: `app/expert_engine/__init__.py`
- Modify: `tests/test_expert_engine.py`

**Interfaces:**
- Produces: stable imports from `app.expert_engine` for `AnswerSelection`,
  `ClipspyAdapter`, `InferenceResult`, and expert-engine error classes.

- [ ] **Step 1: Write a failing public-import test**

```python
def test_expert_engine_exposes_only_the_python_boundary() -> None:
    from app.expert_engine import AnswerSelection, ClipspyAdapter, InferenceResult

    result = ClipspyAdapter().infer(
        tools=[tool()],
        questions=[question()],
        rules=[rule()],
        answers=[AnswerSelection(question_id="q1", option_ids=["yes"])],
    )

    assert isinstance(result, InferenceResult)
```

- [ ] **Step 2: Run the import test and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests\test_expert_engine.py::test_expert_engine_exposes_only_the_python_boundary -v`

Expected: import failure because `app.expert_engine.__init__` has not exported the boundary.

- [ ] **Step 3: Export the intended Python API**

Import the adapter, models, and error classes in `app/expert_engine/__init__.py` and define
this explicit boundary:

```python
from app.expert_engine.clipspy_adapter import ClipspyAdapter
from app.expert_engine.errors import (
    ExpertEngineError,
    InferenceBuildError,
    InferenceExecutionError,
    InferenceLimitError,
    KnowledgeValidationError,
)
from app.expert_engine.models import AnswerSelection, InferenceResult, ScoreEffect

__all__ = [
    "AnswerSelection",
    "ClipspyAdapter",
    "ExpertEngineError",
    "InferenceBuildError",
    "InferenceExecutionError",
    "InferenceLimitError",
    "InferenceResult",
    "KnowledgeValidationError",
    "ScoreEffect",
]
```

Do not export `clips.Environment`, compiler helpers, or native CLIPS objects.

- [ ] **Step 4: Run complete verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -v
.venv\Scripts\python.exe -m compileall -q app
```

Then generate JSON schemas for `EvaluationSource`, `RuleImpact`, `AnswerSelection`, and
`InferenceResult`; assert each top-level schema has `additionalProperties: false`.

Run:

```powershell
.venv\Scripts\python.exe -c "from app.domain.models import EvaluationSource, RuleImpact; from app.expert_engine import AnswerSelection, InferenceResult; models=(EvaluationSource, RuleImpact, AnswerSelection, InferenceResult); assert all(model.model_json_schema().get('additionalProperties') is False for model in models); print('4 strict schemas verified')"
```

Expected: all tests pass, compilation exits 0, and all four schemas remain strict.

- [ ] **Step 5: Review scope and security**

Inspect `git diff --check`, confirm no generated CLIPS source or source documents are logged,
confirm no dependency changed, and confirm no JSON loader, ranking, API route, or production
knowledge rules were added.

- [ ] **Step 6: Commit Task 5**

```powershell
git add app/expert_engine/__init__.py tests/test_expert_engine.py
git commit -m "feat: expose expert-engine boundary"
```
