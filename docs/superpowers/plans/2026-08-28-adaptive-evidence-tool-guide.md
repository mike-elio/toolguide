# Adaptive Evidence-Backed Tool Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved adaptive 6-10 question flow, 48-tool sourced catalog, explainable results, and a verified 250-session simulation.

**Architecture:** Extend the validated knowledge model with domain and evidence metadata, then add a stateless questionnaire service that scopes the existing CLIPS inference engine to one four-tool pool. Expose one advance endpoint, migrate the vanilla JavaScript frontend to a one-question flow, and pressure-test the real HTTP boundary with 250 deterministic sessions.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, clipspy, pytest, vanilla JavaScript, Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-28-adaptive-evidence-tool-guide-design.md`

## Global Constraints

- Exactly 48 unique tools, 12 per stage, four per stage/domain cell.
- Exactly 168 pre-authored sourced questions, 14 per stage/domain pool.
- Runtime question generation is forbidden; Ollama classifies short text only.
- A completed session contains 6-10 unique questions.
- Low-confidence text classification returns fixed clarification choices, never a raw technical error.
- Preserve Arabic and English and keep legacy routes operational.
- Do not overwrite or discard unrelated existing working-tree changes.

---

### Task 1: Extend domain models and structural audit

**Files:**
- Modify: `app/domain/models.py`
- Modify: `app/knowledge/models.py`
- Modify: `app/knowledge/loader.py`
- Modify: `tests/test_domain_models.py`
- Modify: `tests/test_knowledge.py`
- Modify: `tests/test_knowledge_loader.py`

**Interfaces:**
- Produces: `DomainId`, enriched `Tool` and `Question`, signed `RuleImpact.weight`, and adaptive `KnowledgeAudit` cell counts.
- Consumes: existing `LocalizedText`, `StageId`, `EvaluationSource`, and `KnowledgeSnapshot` validation patterns.

- [ ] **Step 1: Write failing model tests**

```python
def test_tool_requires_adaptive_metadata() -> None:
    with pytest.raises(ValidationError):
        Tool(id="tool", name=localized("Tool"), description=localized("Desc"), stages=[StageId.ANALYSIS])

def test_signed_rule_impacts_accept_conflicts_but_not_zero() -> None:
    assert impact(weight=-0.5).weight == -0.5
    with pytest.raises(ValidationError):
        impact(weight=0.0)
```

- [ ] **Step 2: Run the focused tests and confirm they fail for missing fields and the positive-only bound**

Run: `pytest tests/test_domain_models.py tests/test_knowledge.py tests/test_knowledge_loader.py -q`

- [ ] **Step 3: Add the minimal models and cross-reference validation**

```python
class DomainId(StrEnum):
    SOFTWARE = "software"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    CYBERSECURITY = "cybersecurity"

class Tool(DomainModel):
    id: Identifier
    name: LocalizedText
    description: LocalizedText
    stages: list[StageId] = Field(min_length=1, max_length=1)
    domain: DomainId
    best_for: LocalizedText
    limitations: list[LocalizedText] = Field(min_length=1, max_length=4)
    source_url: HttpUrl
    reviewed_at: date
```

Add `domain`, `dimension`, `sources`, and `reviewed_at` to `Question`. Change `RuleImpact.weight` to `Field(ge=-1.0, le=1.0)` plus a validator rejecting zero. Validate rule impacts remain in the question's stage/domain pool.

- [ ] **Step 4: Replace fixed phase-six audit expectations with adaptive cell invariants and run the focused tests green**

Run: `pytest tests/test_domain_models.py tests/test_knowledge.py tests/test_knowledge_loader.py -q`

### Task 2: Build and audit the 48-tool/168-question catalog

**Files:**
- Create: `scripts/build_adaptive_knowledge.py`
- Create: `data/knowledge/adaptive.json`
- Modify: `app/knowledge/loader.py`
- Create: `tests/test_adaptive_catalog.py`
- Modify: `scripts/audit_phase6.py`

**Interfaces:**
- Produces: `build_snapshot() -> KnowledgeSnapshot` and canonical `data/knowledge/adaptive.json`.
- Consumes: enriched domain models from Task 1.

- [ ] **Step 1: Write failing catalog acceptance tests**

```python
def test_catalog_has_exact_stage_domain_matrix() -> None:
    snapshot = load_knowledge(default_knowledge_path())
    assert len(snapshot.tools) == 48
    assert len(snapshot.questions) == 168
    assert all(count == 4 for count in audit_knowledge(snapshot).stage_domain_tool_counts.values())
    assert all(count == 14 for count in audit_knowledge(snapshot).stage_domain_question_counts.values())
```

Add assertions for unique tool IDs, rule target coverage, sources, review dates, limitations, signed answer differentiation, and same-pool rule impacts.

- [ ] **Step 2: Run the catalog tests and confirm they fail against the current 35-tool snapshot**

Run: `pytest tests/test_adaptive_catalog.py -q`

- [ ] **Step 3: Author the catalog builder with the approved 48 tools and 12 sourced question pools**

```python
TOOL_POOLS: dict[tuple[StageId, DomainId], tuple[ToolSpec, ...]] = {...}
QUESTION_POOLS: dict[tuple[StageId, DomainId], tuple[QuestionSpec, ...]] = {...}

def build_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        stages=build_stages(),
        tools=build_tools(TOOL_POOLS),
        questions=build_questions(QUESTION_POOLS),
        rules=build_rules(TOOL_POOLS, QUESTION_POOLS),
    )
```

Every `QuestionSpec` contains literal Arabic and English prompts/options, source metadata, dimension, importance, and explicit preference ordering for all four tools. The builder performs mechanical serialization only; it does not call an LLM or the network.

- [ ] **Step 4: Generate the canonical JSON and run the structural audit**

Run: `python scripts/build_adaptive_knowledge.py`

Run: `python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json`

- [ ] **Step 5: Run catalog and legacy loader tests green**

Run: `pytest tests/test_adaptive_catalog.py tests/test_knowledge_loader.py -q`

### Task 3: Implement adaptive selection and stopping with TDD

**Files:**
- Create: `app/questionnaire/__init__.py`
- Create: `app/questionnaire/models.py`
- Create: `app/questionnaire/selector.py`
- Create: `app/questionnaire/service.py`
- Create: `tests/test_questionnaire_selector.py`
- Create: `tests/test_questionnaire_service.py`

**Interfaces:**
- Produces: `QuestionnaireService.advance(request, knowledge, resolver) -> QuestionnaireOutcome`.
- Consumes: `RecommendationService`, `AnswerResolutionService`, `ClipspyAdapter`, `KnowledgeSnapshot`.

- [ ] **Step 1: Write failing tests for pool scoping, seeded variation, answer-dependent selection, and 6-10 stopping**

```python
def test_next_question_changes_when_the_closest_candidate_pair_changes() -> None:
    first = selector.select(pool=pool, answers=answers_favoring_a, asked_ids=asked, seed="same")
    second = selector.select(pool=pool, answers=answers_favoring_d, asked_ids=asked, seed="same")
    assert first.id != second.id

def test_service_never_completes_before_six_or_continues_after_ten() -> None:
    assert advance(answer_count=5).status == "question"
    assert advance(answer_count=10).status == "complete"
```

- [ ] **Step 2: Run focused tests and confirm failures because the questionnaire package does not exist**

Run: `pytest tests/test_questionnaire_selector.py tests/test_questionnaire_service.py -q`

- [ ] **Step 3: Implement the smallest deterministic selector**

```python
def select_next_question(*, questions, rules, ranked_tools, asked_ids, dimension_counts, seed):
    closest = closest_scoring_pair(ranked_tools)
    eligible = [q for q in questions if q.id not in asked_ids]
    return max(eligible, key=lambda q: selection_key(q, closest, rules, dimension_counts, seed))
```

Use a SHA-256 stable tie key, not Python's randomized `hash()`.

- [ ] **Step 4: Implement stop stability, normalization, detailed explanations, and fixed clarification outcome**

The service resolves only pool-owned answers, recomputes prefix rankings, applies the 0.18/0.30 margins from the spec, and converts `UncertainTextIntentError` into a clarification outcome whose options are the question-owned intents.

- [ ] **Step 5: Run selector/service tests and the existing recommendation tests green**

Run: `pytest tests/test_questionnaire_selector.py tests/test_questionnaire_service.py tests/test_recommendations.py -q`

### Task 4: Add localized adaptive API contracts

**Files:**
- Modify: `app/api/contracts.py`
- Modify: `app/api/dependencies.py`
- Modify: `app/api/routes.py`
- Modify: `app/localization/models.py`
- Modify: `app/localization/projector.py`
- Modify: `app/localization/__init__.py`
- Modify: `app/main.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `GET /api/domains` and `POST /api/questionnaire/advance`.
- Consumes: `QuestionnaireService.advance` from Task 3.

- [ ] **Step 1: Write failing HTTP contract tests for initial question, next question, clarification, completion, localization, and invalid cross-pool history**

```python
def test_advance_starts_a_localized_pool() -> None:
    response = client.post("/api/questionnaire/advance", json={
        "language": "ar", "stage": "analysis", "domain": "software",
        "session_seed": "case-1", "asked_question_ids": [], "answers": []
    })
    assert response.status_code == 200
    assert response.json()["status"] == "question"
    assert response.json()["question"]["domain"] == "software"
```

- [ ] **Step 2: Run API tests and confirm 404/missing-schema failures**

Run: `pytest tests/test_api.py -q`

- [ ] **Step 3: Add strict request/response models and route wiring**

```python
@router.post("/questionnaire/advance", response_model=QuestionnaireResponse)
def advance_questionnaire(request: QuestionnaireRequest, ...):
    return project_questionnaire_outcome(service.advance(...), request.language)
```

Map validation, inconsistent history, and unavailable classifier failures to safe coded envelopes without echoing private text.

- [ ] **Step 4: Run API and OpenAPI tests green**

Run: `pytest tests/test_api.py -q`

### Task 5: Convert the frontend to one-question adaptive flow

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Create: `frontend/questionnaire-state.js`
- Create: `tests/frontend_questionnaire.test.cjs`
- Modify: `tests/test_frontend_integration.py`

**Interfaces:**
- Produces: accessible stage/domain selection, one-question form, progress, clarification, and enriched results UI.
- Consumes: adaptive API from Task 4.

- [ ] **Step 1: Write failing Node tests for state transitions and safe request payloads**

```javascript
test('answering advances one question without dropping history', () => {
  const next = state.answer({ question_id: 'q1', option_ids: ['a'] });
  assert.deepEqual(next.askedQuestionIds, ['q1']);
  assert.deepEqual(next.answers, [{ question_id: 'q1', option_ids: ['a'] }]);
});
```

- [ ] **Step 2: Run Node and frontend integration tests and confirm the new behavior is absent**

Run: `node --test tests/frontend_questionnaire.test.cjs tests/frontend_api_error.test.cjs tests/frontend_localization.test.cjs`

Run: `pytest tests/test_frontend_integration.py -q`

- [ ] **Step 3: Add the minimal state helper and domain selection UI**

The helper owns stage, domain, seed, asked IDs, and answers. The DOM layer renders one API-provided question and submits one answer at a time.

- [ ] **Step 4: Add clarification and result cards with match, confidence, reasons, limitations, and evidence**

Use native form controls, `aria-live` status, visible focus, and the existing orange/dark tokens. Do not add a new UI framework.

- [ ] **Step 5: Run frontend tests and the integration test green**

Run: `node --test tests/frontend_questionnaire.test.cjs tests/frontend_api_error.test.cjs tests/frontend_localization.test.cjs`

Run: `pytest tests/test_frontend_integration.py -q`

### Task 6: Run and harden a 250-session HTTP simulation

**Files:**
- Create: `scripts/simulate_adaptive_questionnaire.py`
- Create: `tests/test_adaptive_simulation.py`
- Create: `output/research/adaptive-questionnaire-250-session-report.md`

**Interfaces:**
- Produces: `run_simulation(session_count=250) -> SimulationReport` and Markdown report.
- Consumes: real `create_app()` through `fastapi.testclient.TestClient`.

- [ ] **Step 1: Write a failing smoke test for the simulation invariants**

```python
def test_twenty_four_session_smoke_simulation_has_no_failures() -> None:
    report = run_simulation(session_count=24)
    assert report.failed_sessions == 0
    assert report.pool_count == 12
    assert report.min_questions >= 6
    assert report.max_questions <= 10
```

- [ ] **Step 2: Run the smoke test and confirm failure because the simulation module is absent**

Run: `pytest tests/test_adaptive_simulation.py -q`

- [ ] **Step 3: Implement deterministic answer strategies and invariant collection**

Strategies rotate through first, last, balanced, tool-targeted, and seeded option selection. Short-text questions use owned aliases so the real resolver is exercised without network-dependent Ollama calls.

- [ ] **Step 4: Run 250 sessions and inspect the report for coverage and recommendation diversity**

Run: `python scripts/simulate_adaptive_questionnaire.py --sessions 250 --output output/research/adaptive-questionnaire-250-session-report.md`

Expected: 250 completed, zero failures, all 12 pools, 6-10 questions, at least 80% catalog tool result coverage, and at least two distinct top tools per pool.

- [ ] **Step 5: For every failed invariant, add a focused failing regression test before fixing production code**

Run the focused test red, apply the minimal fix, then run it green. Repeat until the 250-session report contains zero failed invariants.

### Task 7: Full regression and requirement verification

**Files:**
- Modify only if a verification failure receives a reproducing test first.

**Interfaces:**
- Consumes all previous task outputs.
- Produces final verification evidence.

- [ ] **Step 1: Run the structural audit**

Run: `python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json`

- [ ] **Step 2: Run all Python tests**

Run: `pytest -q`

- [ ] **Step 3: Run all frontend tests**

Run: `node --test tests/*.test.cjs`

- [ ] **Step 4: Re-run the 250-session simulation after the last code change**

Run: `python scripts/simulate_adaptive_questionnaire.py --sessions 250 --output output/research/adaptive-questionnaire-250-session-report.md`

- [ ] **Step 5: Review the final diff and report scope, untouched areas, and any remaining concerns**

Run: `git diff --check`

Run: `git status --short`
