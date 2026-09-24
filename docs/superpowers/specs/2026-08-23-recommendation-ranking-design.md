# Recommendation Ranking and Explanation Design

## Goal

Implement phase 4 of the backend plan: transform the raw, auditable output from the
CLIPSpy inference adapter into exactly three deterministic recommendations. Each
recommendation contains only the tool identifier, tool name, and a concise reason derived
from the rule impacts that actually contributed to that tool's score.

## Evidence Basis

- The backend plan defines the phase-4 formula as the sum of matching rule effects, then
  requires descending ranking, a stable tie-break, three results, and a concise reason from
  matched rules: `output/pdf/ai_expert_system_backend_plan_ar.pdf`.
- The CLIPS 6.4.2 Basic Programming Guide documents that equal-salience activations can be
  ordered arbitrarily and that rule correctness should not depend on agenda order. Final
  ranking therefore belongs outside the CLIPS agenda:
  <https://www.clipsrules.net/documentation/v642/bpg642.pdf>.
- The Python Sorting HOWTO documents key-based, stable sorting and multi-level sort keys.
  Phase 4 will use an explicit composite key instead of relying on input order:
  <https://docs.python.org/3/howto/sorting.html#sort-stability-and-complex-sorts>.
- Tintarev and Masthoff identify transparency, scrutability, trust, and effectiveness as
  goals for recommender-system explanations. Reasons in this phase will therefore be
  faithful to actual contributing rules rather than generated marketing prose:
  <https://doi.org/10.1007/s11257-011-9117-5>.

## Scope

This phase will:

1. Compose the existing `ClipspyAdapter` behind a recommendation service.
2. Rank every validated tool by raw score descending.
3. Resolve exact score ties by tool ID ascending.
4. Select exactly the first three ranked tools.
5. Build a concise reason from the strongest rule effects that actually contributed to
   each selected tool.
6. Return the existing strict `RecommendationResult` contract.
7. Reject a knowledge slice containing fewer than three tools.
8. Preserve deterministic output when tools, rules, answers, or CLIPS firing order change.
9. Update the existing Arabic backend-plan PDF with the implemented phase-4 decisions,
   verification evidence, and references.

This phase will not:

- expose recommendation HTTP endpoints;
- load JSON knowledge files;
- populate the production tool, question, rule, or benchmark catalog;
- normalize or combine benchmark metrics;
- use an LLM to generate recommendation prose;
- change the phase-3 raw inference result.

Those responsibilities remain in their later planned phases.

## Architecture

The new `app.recommendations` package owns ranking and explanation. Dependency direction
is one way:

```text
domain models
    -> expert-engine adapter
    -> recommendation service
    -> later FastAPI route
```

The expert engine remains unaware of ranking. The recommendation layer consumes
`InferenceResult`, domain tools, and sourced rules, then returns `RecommendationResult`.
It never receives or exposes a CLIPS environment.

## Public Python Interface

`app.recommendations.RecommendationService` will expose:

```python
def recommend(
    *,
    tools: Sequence[Tool],
    questions: Sequence[Question],
    rules: Sequence[Rule],
    answers: Sequence[AnswerSelection],
) -> RecommendationResult:
    ...
```

The default service uses the real `ClipspyAdapter`. Its constructor may accept an object
matching the narrow inference-engine protocol for composition, but the public result never
contains engine-specific objects or internal ranked records.

The package public boundary will export only the service and recommendation-specific error
types. Ranking helpers, explanation helpers, and the inference-engine protocol stay
internal.

## Ranking Policy

The adapter already calculates each raw tool score as:

```text
tool_score = sum(answer_value * question_importance * rule_weight)
```

The recommendation service will sort all tools with this composite key:

```python
(-tool_score, tool_id)
```

This makes the policy explicit:

1. higher raw score wins;
2. an exact score tie is resolved by the normalized, case-sensitive domain `tool_id` in
   ascending code-point order;
3. catalog order, dictionary order, rule order, and CLIPS agenda order have no effect.

The service will not round scores or collapse nearly equal scores. The domain contracts
already reject non-finite numbers, and the phase-3 adapter uses `math.fsum`. Introducing an
epsilon or display rounding rule here would silently change the scoring model without a
requirement or evidence basis.

Benchmarks will not break ties in this phase. Existing benchmarks can use different
metrics and units; combining them without an explicit normalization and missing-data policy
would create an undocumented second scoring system.

## Explanation Policy

Reasons must be faithful to executed rules and must be reproducible.

For each selected tool, the service will map every `ScoreEffect` back to the unique
`RuleImpact` identified by `(rule_id, tool_id)`. That impact already requires a rationale and
classified evidence sources.

Contributions are ordered by:

```text
absolute effect descending, rule ID ascending
```

The reason policy is:

1. Use the strongest unique positive rationale as the primary reason.
2. If a negative effect also contributed, append the strongest unique negative rationale as
   a countervailing factor so the explanation does not hide material evidence.
3. If only negative effects exist, state transparently that the tool ranked comparatively
   despite the strongest negative matched factor.
4. If no rule affected the tool, state that no rule changed its score and that its position
   came from the deterministic ranking policy.
5. Never invent a capability, benchmark claim, or rationale that is absent from the rules.
6. Bound the final reason to the existing `NonEmptyText` maximum while preserving the full
   rationale and sources in the underlying rule data.

The human-readable fallback text is backend-owned English in this phase. Localization is an
API/frontend concern and is not silently mixed into the ranking engine.

## Validation and Error Model

The existing expert-engine validation remains the authority for duplicate identifiers,
dangling references, unsupported questions, and invalid answers.

The recommendation layer adds:

- `RecommendationError`: base error for this boundary;
- `InsufficientToolsError`: fewer than three validated tools are available;
- `RecommendationConsistencyError`: an inference effect cannot be mapped back to its
  originating rule impact.

The consistency error is defensive. With the default real adapter it indicates a programming
or integration defect, not normal user input. Phase 5 will map these errors to the existing
API error envelope.

## Determinism, Safety, and Performance

- The service is stateless and creates no shared mutable request state.
- It relies on the phase-3 adapter's fresh environment per request.
- Every ordering operation has an explicit secondary key.
- Reasons are assembled only from Pydantic-validated text and are returned as data; they are
  never interpreted as source code or templates.
- The complete ranking is `O(T log T)` for `T` tools. Effect indexing and explanation are
  linear in the number of emitted effects.
- A knowledge slice must contain at least three tools because the existing public result
  contract requires exactly three recommendations.

## Incremental Implementation

### Slice 1: Pure ranking contract

Add recommendation errors and a pure ranking function that consumes validated tools plus an
`InferenceResult`. Prove descending scores, deterministic tool-ID ties, negative values, and
the three-tool boundary.

### Slice 2: Faithful reasons

Map score effects to sourced rule impacts and build deterministic positive, negative, and
no-effect explanations. Prove duplicate rationale handling and the output-length boundary.

### Slice 3: Service composition

Compose the real `ClipspyAdapter` and the pure ranking/explanation policy behind
`RecommendationService.recommend`. Prove the end-to-end Python flow with real CLIPS rules.

### Slice 4: Public boundary and regression verification

Export only the intended package interface, verify reordered inputs produce identical
recommendations, and run the complete backend suite and schema checks.

### Slice 5: Plan PDF update and visual verification

Update `output/pdf/ai_expert_system_backend_plan_ar.pdf` in place so the phase-4 section
records the implemented ranking key, benchmark exclusion, explanation policy, and final
verification evidence. Render every updated page to PNG, visually inspect Arabic shaping,
alignment, clipping, tables, page numbering, and source legibility, then reopen the PDF and
confirm its page count and extractable text. Git history remains the recovery path for the
original PDF.

## Testing Strategy

Tests will exercise real Pydantic models and real CLIPSpy inference. Mocks are unnecessary
for the default path.

Required cases:

1. Three highest scores are returned in descending order.
2. Exact ties are resolved by tool ID, regardless of input order.
3. Negative scores sort correctly.
4. Fewer than three tools fail before a result is constructed.
5. A positive matched effect returns its sourced impact rationale.
6. A positive and negative contribution produce a faithful bounded explanation.
7. A zero-effect tool receives the transparent fallback reason.
8. Duplicate rationales do not create duplicate prose.
9. An unmappable effect raises a consistency error.
10. Reordered tools and rules yield an identical result.
11. A real selected answer passes through CLIPSpy and produces the expected top three.
12. All phase-1 through phase-3 tests continue to pass.
13. The updated backend-plan PDF renders without clipping, overlap, broken Arabic glyphs,
    or unreadable references.

## Acceptance Criteria

1. The public service always returns exactly three unique recommendations for a valid
   knowledge slice containing at least three tools.
2. Results are sorted by raw score descending and exact ties by tool ID ascending.
3. Results never depend on source collection order or CLIPS agenda order.
4. Every matched explanation is traceable to a fired rule impact and its evidence sources.
5. Negative and absent evidence are represented honestly rather than hidden or invented.
6. Benchmarks do not affect ordering before a separate normalization policy exists.
7. The public result remains the existing `RecommendationResult` shape: tool ID, tool name,
   and reason only.
8. No new runtime dependency is added.
9. The complete backend test suite, Python compilation, dependency check, and strict schema
   generation pass.
10. The existing Arabic backend-plan PDF documents the final phase-4 behavior and passes
    full visual and structural verification before delivery.
