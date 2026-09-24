# Phase 6 Bilingual Knowledge and Compact Text Classification Design

## Objective

Deliver the sixth and final backend phase as a production-loaded bilingual knowledge
base with reliable short-text interpretation. The user explicitly chooses Arabic or
English. The backend returns only the selected language, translates short answers to
canonical intent identifiers, and keeps CLIPS authoritative for recommendation scores.

Success requires a valid JSON knowledge base, exactly 10 tool assignments per stage,
the planned 60/20/20 question-type distribution, compact local model artifacts, and a
frozen 200-request TestClient acceptance suite that clears the accuracy gate separately
for Arabic and English.

## Approved Product Constraints

1. Supported languages are exactly `ar` and `en`.
2. The user selects the language; the backend does not auto-detect or auto-switch it.
3. User-facing prose is returned only in the selected language. Official product names
   remain unchanged when they have no translated brand name.
4. The final classifier artifact for each language must not exceed 50 MB.
5. Only the selected language model is loaded for a request.
6. No external AI or embedding service is called at inference time.
7. CLIPS remains responsible for rule firing and numerical tool scores.
8. The 200 acceptance cases are never training or calibration data.
9. Accuracy is evaluated and reported independently for each language.
10. The original downloaded checkpoints are copied and preserved unchanged.

## Verified Pretrained Checkpoints

The downloaded folder labels are reversed. Model identity is determined from the
checkpoint configuration and vocabulary:

| Runtime language | Desktop source | Evidence | Required source files |
|---|---|---|---|
| English (`en`) | `C:\Users\ST\Desktop\عربي` | `vocab_size=30522`, BERT English vocabulary | `config.json`, `pytorch_model.bin`, `vocab.txt` |
| Arabic (`ar`) | `C:\Users\ST\Desktop\انكليزي` | `vocab_size=32000`, Arabic vocabulary and masked-LM config | `config.json`, `model.safetensors`, `special_tokens_map.json`, `tokenizer_config.json`, `vocab.txt` |

Source-weight SHA-256 values:

```text
en/pytorch_model.bin  F7902E759E678CF77852A40A710E79BB83ACB475C44C177773246D610818A5DB
ar/model.safetensors  CF1F64FDEA5DBC06F9EC67AF829075E5CE59FA08F1C935F90EB14FE4128B3763
```

Copy the pristine files to `artifacts/pretrained/en` and
`artifacts/pretrained/ar`. Commit `artifacts/models-manifest.json`, containing source
URLs, language, license, filenames, sizes, and SHA-256 values. Ignore binary weight
files in Git so repository history does not grow by approximately 92 MB.

Fine-tuning writes separate artifacts under `artifacts/text-intent/en` and
`artifacts/text-intent/ar`; it never mutates the pristine copies.

## Domain Model

Introduce these strict concepts:

```python
class Language(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class LocalizedText(DomainModel):
    ar: NonEmptyText
    en: NonEmptyText


class TextIntent(DomainModel):
    id: Identifier
    label: LocalizedText
    value: float
    aliases: dict[Language, list[NonEmptyText]]
```

Stage names, tool names/descriptions, question prompts, answer labels, rationales, and
source display names use `LocalizedText`. Canonical identifiers, stage membership,
weights, URLs, dates, and benchmark values remain language-neutral.

A short-text question has at least two `TextIntent` values and no visible choice
options. A choice or Boolean question has at least two `AnswerOption` values and no
text intents. A rule's existing `answer_option_id` may reference either a visible
answer option or a short-text intent; the field is retained to avoid unnecessary CLIPS
schema churn.

## HTTP Contract

Localized read routes require an explicit query parameter:

```text
GET /api/stages?language=ar
GET /api/stages/{stage}/questions?language=en
GET /api/tools/{tool_id}?language=ar
```

They return language-projected response contracts rather than leaking both localized
strings. Missing or unsupported language is a `422 VALIDATION_ERROR`.

The recommendation request becomes:

```json
{
  "language": "ar",
  "answers": [
    {"question_id": "analysis-q1", "option_ids": ["yes"]},
    {"question_id": "analysis-q4", "text": "أحتاج مقارنة مصادر موثوقة"}
  ]
}
```

`AnswerSelection` accepts exactly one answer representation:

- `option_ids` for single-choice, multiple-choice, and Boolean questions;
- `text` for short-text questions.

Supplying both, neither, or the wrong representation returns `422`. Short text is
trimmed, must be 1-500 characters, and is not returned in errors. Uncertain or
language-mismatched text returns a safe `422` with a stable public error code. Arabic
answers may contain official Latin-script product names.

`RecommendationResult` contains only selected-language tool names and reasons.

## Knowledge JSON

Store one canonical bilingual snapshot in versioned JSON under `data/knowledge`.
Load and validate it at application startup. `create_app()` loads the bundled snapshot
by default; tests may inject an explicit snapshot. Invalid production knowledge fails
startup instead of serving partial recommendations.

The initial snapshot contains:

- four stages: analysis, design, implementation, and testing;
- exactly 10 tool assignments for each stage;
- each tool assigned to one, two, or three stages, never four;
- 20 questions total, five per stage;
- 12 choice questions, four short-text questions, and four Boolean questions;
- exactly one short-text and one Boolean question per stage;
- rules for every selectable option and every short-text intent;
- source URL and `collected_at` for every evidence item;
- at least three independent sources for model-evaluation claims;
- at least two independent sources for code-editor claims.

All source links must be primary vendor documentation, official repositories, primary
research, or published benchmarks. IDs and ordering are deterministic. A validation
command audits counts, ratios, stage assignments, references, sources, and dates so
knowledge can be revised without changing Python code.

## Text Classification Pipeline

Use one classifier per language with labels in the form
`<question_id>::<intent_id>`. The model input combines the selected-language question
prompt and the user's answer, separated by the tokenizer separator token. This prevents
the same phrase from being interpreted outside its question context.

Processing order:

```text
explicit language + question + text
  -> length and representation validation
  -> Unicode normalization
  -> exact normalized alias lookup
  -> selected-language ONNX classifier
  -> calibrated confidence and margin checks
  -> canonical TextIntent
  -> ResolvedAnswer
  -> ordinary selected-answer CLIPS fact
```

Arabic normalization uses Unicode NFKC, removes tatweel and optional diacritics, and
normalizes whitespace. It does not transliterate or translate. English normalization
uses Unicode NFKC, case folding, and whitespace normalization.

Exact aliases are versioned training assets. The classifier handles unseen paraphrases.
Confidence thresholds are calibrated separately per language on calibration data. A
prediction is accepted only when both its probability threshold and top-one/top-two
margin pass. Rejection is safer than silently firing an unrelated rule.

The training command fine-tunes the two four-layer BERT checkpoints, fixes random
seeds, records dependency versions and dataset hashes, and exports ONNX artifacts.
The classifier head adds negligible source size. The exporter fails when an artifact
exceeds 50 MB. Optional dynamic INT8 quantization is accepted only when it passes the
same frozen accuracy gates as the unquantized candidate.

Runtime uses ONNX Runtime and a tokenizer, not PyTorch. Sessions are created lazily,
cached by language, and dependency-injectable so ordinary unit tests do not require
model files.

## Training, Calibration, and Acceptance Data

Maintain three non-overlapping datasets per language:

1. training data for parameter updates;
2. calibration data for confidence and margin thresholds;
3. frozen acceptance data for final evaluation only.

Every row stores language, question ID, canonical intent ID, text, split, provenance,
and a stable row ID. Duplicate normalized text cannot cross splits. Template families,
not only exact strings, are isolated to one split to reduce leakage.

The frozen acceptance set has 100 Arabic and 100 English cases. Each language balances
the four short-text questions and their intents and includes natural paraphrases,
negation, punctuation, spelling variation, and official technical names. Code-switched
sentences are excluded except official brand names because the product promises one
selected language at a time.

## TestClient Acceptance Gate

Each frozen case is a complete `POST /api/recommendations` request through the real
application, real knowledge loader, selected-language classifier, CLIPS engine, ranker,
and localized response. It records the expected canonical intent and expected ordered
tool IDs. A case passes only when the request succeeds, the internal audited intent is
correct, and the ordered final recommendation IDs match.

Results are grouped independently:

| Language | Requests | Minimum complete passes | Intent Macro-F1 |
|---|---:|---:|---:|
| Arabic | 100 | 96 | >= 0.90 |
| English | 100 | 96 | >= 0.90 |

Rejections, timeouts, unexpected errors, wrong intents, and wrong rankings are failures.
The evaluator writes a JSON report with per-language counts, confusion matrices,
Macro-F1, latency percentiles, model hashes, data hash, and Wilson lower bound. It
exits nonzero unless both languages pass every gate.

The accuracy claim is limited to this frozen distribution. Production examples cannot
be added to the acceptance set retroactively; a model update requires a new untouched
holdout.

## Error Handling and Safety

- Validate all JSON with strict Pydantic contracts and reject extra fields.
- Cap short text at 500 characters before tokenization.
- Never include raw user text in error messages or default logs.
- Never let model output name a tool or weight directly.
- Reject classifier labels that do not belong to the submitted question.
- Validate model and dataset hashes before evaluation.
- Fail startup for missing or corrupt production knowledge.
- Return safe `422` errors for invalid/uncertain text and safe `503` when required
  model artifacts are unavailable.
- Preserve the existing safe `500` envelope for unexpected failures.

## Project Boundaries

Planned new modules have one responsibility each:

```text
app/localization/                 language projection and localized response models
app/knowledge/loader.py           validated JSON loading only
app/text_intent/contracts.py      classifier boundary and prediction records
app/text_intent/normalization.py  deterministic language-specific normalization
app/text_intent/aliases.py        exact alias lookup
app/text_intent/onnx.py           lazy selected-language ONNX sessions
app/text_intent/service.py        alias/model orchestration and threshold checks
data/knowledge/                   canonical bilingual knowledge JSON
data/text_intent/                 train, calibration, and frozen acceptance JSONL
artifacts/models-manifest.json    checkpoint and final-artifact integrity metadata
scripts/copy_pretrained_models.py verified local copy command
scripts/train_text_intent.py      deterministic fine-tuning and ONNX export
scripts/audit_phase6.py           knowledge, artifact, and acceptance audit
tests/test_phase6_acceptance.py   exactly 200 real TestClient cases
```

Existing CLIPS compilation and score formulas remain unchanged. Short-text resolution
happens before `ClipspyAdapter` validates and asserts selected-answer facts.

## Incremental Delivery

1. Preserve and verify the two source checkpoints; add the artifact manifest.
2. Add language/localization and answer-union contracts with compatibility tests.
3. Add and audit the bilingual JSON loader and initial knowledge snapshot.
4. Add deterministic alias resolution and CLIPS short-text intent integration.
5. Build non-overlapping training/calibration/acceptance datasets.
6. Fine-tune and export the two <=50 MB ONNX classifiers.
7. Integrate lazy runtime inference and calibrated rejection.
8. Run the 200 TestClient cases, publish the machine-readable evaluation report, and
   correct data/model issues without touching the frozen holdout.
9. Run all regression, compilation, dependency, integrity, and PDF checks.
10. Append one verified Phase 6 page to the backend-plan PDF, preserving pages 1-7.

Each increment follows RED-GREEN-REFACTOR, runs focused tests plus affected regressions,
and ends in an atomic commit. No increment claims success without fresh verification.

## PDF Update

Extend the idempotent backend-plan builder to produce exactly eight pages. Preserve
the first five original pages and the verified Phase 4 and Phase 5 appendices. Add a
Phase 6 page containing the implemented language contract, knowledge counts, model
names and final sizes, source hashes, 200-case results, accuracy/Macro-F1 per language,
and the exact verification commands. Add metadata marker `/Phase6Knowledge = 1`.

The PDF records only measured results; it must not claim 90% until the frozen evaluator
passes both language gates.

## Verification

Required fresh commands at completion:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest tests\test_phase6_acceptance.py -v
.venv\Scripts\python.exe -m compileall -q app tests scripts
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\audit_phase6.py
git diff --check
```

Refresh the codebase-memory index after implementation, trace the recommendation path
in both directions, and check coverage for every changed Python path. Read exact source
for any stale, skipped, partial, excluded, or unknown range before making claims.

## Explicitly Out of Scope

- automatic language detection or translation;
- generative answers or chat;
- cloud model inference;
- authentication, user accounts, persistence, or analytics;
- frontend implementation;
- more than Arabic and English;
- changing CLIPS score arithmetic;
- claiming accuracy outside the frozen project distribution.

## Open Questions

None. The user selected the compact two-model approach, explicit language choice,
local inference, careful staged implementation, and the 200-case acceptance target.
