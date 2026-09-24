# CLIPSpy Inference Layer Design

## Goal

Implement phase 3 of the backend plan: translate validated domain data into CLIPS facts
and rules, execute inference in an isolated environment, and return raw per-tool score
effects together with the identifiers of the rules that fired.

## Evidence Basis

The implementation targets the installed `clipspy` 1.0.6 package.

- The official CLIPSpy 1.0.6 API describes `Environment` as an independent CLIPS
  engine with its own data structures and exposes construct building, template fact
  assertion, agenda execution, and fact iteration through that environment:
  <https://clipspy.readthedocs.io/en/latest/clips.html>.
- The CLIPS 6.4.2 Basic Programming Guide defines `deftemplate` as the named-field
  representation for facts, defines rules as LHS conditions followed by RHS actions,
  and documents the rule execution cycle. It also warns that equal-priority rule order
  can be arbitrary and must not be used for correctness:
  <https://www.clipsrules.net/documentation/v642/bpg642.pdf>.
- NASA describes CLIPS as a forward-chaining, rule-based language designed for expert
  system delivery and integration with external systems:
  <https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19880006986.pdf>.
- NASA's TARGET work documents generating CLIPS production rules from an intermediate
  knowledge representation and highlights verification and validation of generated
  rules:
  <https://ntrs.nasa.gov/citations/19930016401>.

These sources justify a narrow adapter: Pydantic models remain the auditable
intermediate representation, while generated CLIPS constructs are an execution detail.

## Scope

This phase will:

1. Extend each rule impact with an auditable rationale and evidence sources.
2. Accept validated tools, questions, rules, and selected answers.
3. Validate references across those collections before invoking CLIPS.
4. Create a fresh `clips.Environment` for every inference call.
5. Define typed templates for tools, selected answers, score effects, and fired rules.
6. Generate one CLIPS production rule for each domain rule.
7. Run the agenda with a finite firing limit.
8. Extract deterministic raw tool scores and unique fired domain-rule identifiers.

This phase will not rank tools, break score ties, produce recommendation prose, load JSON
files, or expose HTTP endpoints. Those belong to later phases.

Short-text questions do not currently have answer options, while the phase-2 `Rule`
contract references an `answer_option_id`. Therefore this phase explicitly rejects a
short-text answer sent to inference instead of silently inventing a scoring policy. A
later knowledge-design phase must define an auditable normalization policy before such
answers can affect scores.

## Public Python Interface

`app.expert_engine.models` will define strict Pydantic contracts:

- `AnswerSelection(question_id, option_ids)` represents one or more selected options.
- `ScoreEffect(tool_id, rule_id, value)` represents an immutable rule contribution.
- `InferenceResult(tool_scores, effects, fired_rule_ids, firing_count)` represents raw
  inference output. It contains no ranking or recommendation reason.

`app.expert_engine.clipspy_adapter.ClipspyAdapter.infer(...)` will accept sequences of
`Tool`, `Question`, `Rule`, and `AnswerSelection`, and return `InferenceResult`.

The adapter will be stateless. It will not expose a CLIPS environment or CLIPS-specific
objects to the rest of the application.

## CLIPS Representation

The adapter will build these templates:

```clips
(deftemplate tool
  (slot tool-id (type STRING)))

(deftemplate selected-answer
  (slot question-id (type STRING))
  (slot option-id (type STRING))
  (slot answer-value (type FLOAT))
  (slot importance (type FLOAT)))

(deftemplate score-effect
  (slot tool-id (type STRING))
  (slot rule-id (type STRING))
  (slot value (type FLOAT)))

(deftemplate rule-fired
  (slot rule-id (type STRING)))
```

Each domain rule will match one `selected-answer` fact by question and option. Its RHS
will assert one `score-effect` fact per impacted tool using:

```text
answer_value * question_importance * rule_weight
```

It will also assert a `rule-fired` fact containing the original domain rule ID. Effects
are immutable; rules never modify facts that appear on their own LHS, which prevents
self-reactivation loops in the generated rule set.

Python will sum the emitted effects by tool to produce raw totals. This extraction is
part of the adapter boundary, not phase-4 ranking logic.

## Translation Safety

Knowledge files are external input even after structural Pydantic validation.

- Tools, answers, and results will be inserted with template `assert_fact`, not
  interpolated into `assert_string` expressions.
- CLIPS rule names will be stable hashes of domain rule IDs, so external identifiers
  cannot alter CLIPS syntax.
- Domain identifiers embedded as CLIPS string literals will be escaped by one focused
  encoder and covered with adversarial tests.
- Numeric operands come only from bounded Pydantic fields.
- Duplicate collection IDs and dangling references are rejected before an environment
  is created.
- CLIPS exceptions are wrapped in an adapter-specific error without returning generated
  CLIPS source to an API consumer.

## Cross-Reference Validation

Before compilation, the adapter will require:

- unique tool, question, and rule IDs;
- every rule question to exist;
- every rule answer option to belong to its referenced question;
- every impacted tool to exist;
- every answer question and option to exist;
- exactly one selection for single-choice and boolean questions;
- at least one unique selection for multiple-choice questions;
- no answer for a short-text question until a normalization contract exists.

Validation failures will identify the offending domain ID and stop before inference.

## Isolation and Determinism

Every call creates, builds, runs, reads, and discards its own environment. This matches
the CLIPSpy environment isolation contract and prevents facts from one user request from
appearing in another.

Generated rules have no inter-rule dependency, so correctness does not depend on agenda
ordering. Returned score effects will be sorted by `(tool_id, rule_id)`, fired rule IDs
will be sorted, and score dictionaries will be emitted in sorted tool-ID order.

The firing limit will equal the number of generated domain rules. If activations remain
after the limit, the adapter will raise an inference-limit error rather than return a
partial result.

## Error Model

- `KnowledgeValidationError`: duplicate IDs, dangling references, invalid selections,
  or unsupported short-text scoring.
- `InferenceBuildError`: CLIPS rejected a generated construct.
- `InferenceExecutionError`: CLIPS failed while facts were asserted or inference ran.
- `InferenceLimitError`: the agenda still contains activations after the safe limit.

These errors remain internal in phase 3. Phase 5 will map them to the existing stable API
error envelope.

## Evidence Policy for Rule Conditions

The condition side of a rule is the question and answer option it matches. The conclusion
side is each tool impact and its weight. The conclusion must not be based on an uncited
opinion.

`EvaluationSource` will be extended with:

- `kind`: official documentation, official source repository, primary research,
  peer-reviewed research, published benchmark, vendor documentation, or practitioner
  report;
- `publisher`: the organization or venue responsible for the source;
- `published_at`: the source publication date when available;
- the existing `url` and `collected_at` fields for retrieval and freshness auditing.

Each `RuleImpact` will require:

- `rationale`: a concise statement connecting the matched answer to the affected tool;
- `sources`: at least one `EvaluationSource` supporting that relationship and weight.

Source selection follows this order:

1. official specifications, product documentation, and original dataset documentation;
2. peer-reviewed or original academic research;
3. benchmarks with published methodology and reproducible data;
4. vendor documentation only for a capability the vendor directly claims, explicitly
   marked as vendor evidence.

GitHub and Reddit are used under the following evidence rules:

- An official GitHub repository's source code, release notes, tests, and maintainer-owned
  documentation may serve as primary technical evidence for observable product behavior.
- GitHub issues and discussions are supporting evidence. A maintainer response is stronger
  than an unverified user report, but neither replaces released documentation or a
  reproducible test.
- Reddit posts and comments are practitioner reports. They can reveal workflow friction,
  recurring failure modes, adoption constraints, and terminology worth investigating.
- A Reddit report must be linked by permalink and recorded with its date and relevant
  context. Deleted, unverifiable, affiliate, or obviously promotional content is excluded.
- Community reports never establish a capability, benchmark result, or numeric weight on
  their own. Material claims must be triangulated with an authoritative source, a
  reproducible repository artifact, published research, or a benchmark methodology.
- Repeated community evidence must come from independent reports; multiple comments in one
  thread count as one discussion context, not independent confirmation.

Affiliate pages, uncited comparison articles, search snippets, and AI-generated summaries
are not admissible evidence. A source may support a capability or measured result, but the
rule rationale must state the inference made from that evidence. The system will not claim
that a source directly endorses a generated weight when the weight is an engineering
normalization.

Phase 3 enforces and preserves this provenance but does not author the real tool-selection
conditions. The full, sourced rule set is populated in the knowledge-base phase, where the
project plan also requires multiple sources per tool category. This separation keeps the
inference engine generic while making it impossible to load an uncited production rule
impact.

## Incremental Implementation

### Slice 1: Contracts and reference validation

Extend source and rule-impact provenance, add inference input/output contracts, and
validate a complete, internally consistent knowledge slice without creating a CLIPS
environment.

### Slice 2: Translation and one-rule inference

Build templates, assert typed facts, compile one rule, run it, and return its score effect
and fired rule ID.

### Slice 3: Multiple rules, determinism, and isolation

Support multiple tools and rules, negative answer values, deterministic aggregation,
sequential-request isolation, and the firing guard.

### Slice 4: Hardening and regression verification

Test hostile identifiers, dangling references, unsupported question types, CLIPS build
errors, and the complete backend test suite.

## Acceptance Criteria

1. A matching selected answer fires the corresponding generated rule.
2. The emitted effect equals `answer_value * importance * rule_weight`.
3. Non-matching rules do not contribute a score or appear in fired IDs.
4. Multiple effects for one tool produce the expected raw total without ranking.
5. Negative answer values produce negative effects.
6. Repeated calls cannot observe each other's facts or fired rules.
7. Results are deterministic regardless of CLIPS agenda order.
8. Invalid references and selections fail before CLIPS execution.
9. External identifiers cannot inject or corrupt generated CLIPS constructs.
10. Every rule impact has a rationale and at least one classified evidence source.
11. All phase-1 and phase-2 tests continue to pass.
