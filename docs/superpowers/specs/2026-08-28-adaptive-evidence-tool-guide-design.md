# Adaptive Evidence-Backed Tool Guide Design

**Status:** Approved by the user on 2026-08-28
**Research:** `output/research/adaptive-tool-guide-deep-research-ar.md`

## Goal

Replace the fixed five-question stage flow with an evidence-backed adaptive questionnaire that explicitly selects one of three domains, asks 6-10 sourced questions, and returns three explainable recommendations from a 48-tool catalog.

## User flow

1. Select one of four stages: analysis, design, implementation, or testing.
2. Select one domain: software, artificial intelligence, or cybersecurity.
3. Answer one question at a time. The next question is selected from a pre-authored sourced bank based on the answers already given.
4. Stop after at least six questions when ranking confidence is sufficient, or after ten questions unconditionally.
5. Show three recommendation cards containing match percentage, confidence, answer-derived reasons, documented limitations, and primary evidence link.

## Fixed requirements

- The catalog contains exactly 48 unique tools: 12 per stage and four per stage/domain cell.
- The bank starts with 168 pre-authored questions: 14 per stage/domain pool.
- Runtime question generation is forbidden. Ollama may classify short text only.
- A session asks between six and ten unique questions.
- Questions and rules include reviewed evidence. Capability claims use official documentation, standards, or official repositories. Community evidence is labelled anecdotal and is used only for practical limitations.
- Arabic and English are supported.
- A low-confidence short-text classification never exposes a technical error. It returns a fixed clarification choice owned by the question.
- The API is stateless: the client submits the selected stage/domain, a stable session seed, asked question IDs, and accumulated answers on every advance request.
- Legacy read and recommendation routes remain available while the frontend moves to the adaptive route.

## Data model

### Domain

`DomainId` has three values: `software`, `artificial_intelligence`, and `cybersecurity`.

### Tool additions

Each tool has one stage/domain cell, localized `best_for`, one or more localized `limitations`, a primary official `source_url`, and `reviewed_at`. The existing localized name and description remain.

### Question additions

Each question has a domain, decision dimension, at least one evidence source, and `reviewed_at`. Choice options are pre-authored. Short-text questions own fixed intents and those intent labels become clarification choices when classification is uncertain.

### Signed rule impacts

Rule impact weights range from -1.0 to 1.0, excluding zero. This lets one answer support suitable tools and penalize unsuitable tools. Every rule affects at least one candidate in the same stage/domain cell and cannot reference a tool outside that cell.

## Adaptive selection

Candidate tools are the four tools in the selected stage/domain cell. For every advance:

1. Resolve submitted answers to canonical option IDs.
2. Infer current scores with the existing isolated CLIPS adapter, scoped to the pool.
3. Rank candidates by score and deterministic tool ID tie-break.
4. Identify the closest-scoring candidate pair.
5. Score each unanswered question by the maximum signed impact separation it can create for that pair, multiplied by question importance.
6. Apply a content-balancing penalty to dimensions already asked.
7. Use a stable hash of session seed and question ID to select among the top three near-equal questions.

The first question uses importance, uncovered dimension value, and the same seeded tie-break because no answer scores exist yet.

## Stop rule

- Never stop before six answers.
- After six answers, recompute the top-three order for the full answer prefix and the previous prefix.
- Stop when the top three are stable and the normalized third-versus-fourth margin is at least 0.18.
- Otherwise continue until ten answers, then stop regardless of margin.

## Result scoring and explanations

Match percentage is a bounded suitability score, not a probability. For each tool, normalize its signed score against the maximum absolute score the answered questions could have contributed to that tool. Neutral is 50%, strong positive evidence approaches 100%, and strong conflict approaches 0%.

Confidence is:

- `high` after at least eight answers with a normalized third/fourth margin of at least 0.30;
- `medium` after six answers with a margin of at least 0.18;
- `low` otherwise, including forced completion at ten questions.

Each card contains:

- three strongest positive answer-derived rationales, deduplicated;
- up to two strongest negative answer-derived rationales or documented tool limitations;
- the tool's primary official source URL;
- `match_percent` and localized confidence label.

## API contract

### `GET /api/domains?language=ar|en`

Returns the three localized domains in stable order.

### `POST /api/questionnaire/advance`

Request:

```json
{
  "language": "ar",
  "stage": "implementation",
  "domain": "software",
  "session_seed": "user-visible-stable-seed",
  "asked_question_ids": ["implementation-software-environment"],
  "answers": [
    {
      "question_id": "implementation-software-environment",
      "option_ids": ["ide"]
    }
  ]
}
```

While active, the response contains `status: "question"`, one localized question, `answered_count`, `minimum_questions: 6`, and `maximum_questions: 10`.

At completion, the response contains `status: "complete"` and exactly three detailed recommendations.

For an uncertain short-text answer, the response contains `status: "clarification"`, the same question ID, and fixed intent choices. The client replaces the free-text field with those choices and resubmits without losing prior answers.

## Frontend

- Domain selection is added after stage selection and remains part of step one.
- Only one question card is rendered at a time.
- The progress text shows answered count and the 6-10 range rather than pretending the final question count is known.
- Back/restart clears questionnaire state safely.
- All controls use native buttons/inputs, visible focus, associated labels, status regions, and keyboard operation.
- Results retain the current dark/orange visual language while adding compact percentage, confidence, reason, limitation, and evidence rows.

## Data audit

The knowledge audit must verify:

- exactly four stages, three domains, and 48 unique tools;
- exactly four tools in every stage/domain cell;
- exactly 14 questions in every stage/domain pool;
- every question has evidence and every answer target has a rule;
- every rule stays inside its stage/domain cell;
- every tool has a limitation, official URL, and review date;
- no missing or duplicate IDs, empty branches, or zero-impact answers.

## 250-session acceptance simulation

The simulation runs exactly 250 complete questionnaire sessions through the real FastAPI boundary using stable seeds and several answer strategies. It must verify:

- no HTTP failures or raw classifier errors;
- every session asks 6-10 unique questions from the selected pool;
- every completed response contains three unique tools from the selected stage/domain cell;
- match percentages are 0-100 and ordered non-increasingly;
- every result has confidence, an answer-derived reason, a limitation, and an official source URL;
- all 12 stage/domain pools are exercised;
- across the 250 sessions, at least 80% of catalog tools appear in a top-three result and each pool produces at least two distinct top recommendations;
- identical seed and answers produce identical question paths and results;
- different seeds can change question order without changing data validity.

The simulation writes `output/research/adaptive-questionnaire-250-session-report.md` with totals, failure counts, pool coverage, recommendation diversity, question-count distribution, and representative result samples. Any failed invariant becomes a regression test before its fix.

## Non-goals

- No model training or fine-tuning.
- No runtime web search.
- No runtime generation of questions, options, facts, or product claims.
- No database-backed server session in this iteration.
- No removal of the existing Ollama classifier or legacy recommendation endpoint.
