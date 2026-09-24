# Phase 6 Bilingual Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the final backend phase with a production-loaded bilingual knowledge base, compact local Arabic/English text-intent classifiers, and a passing 200-request TestClient acceptance gate.

**Architecture:** Keep one canonical bilingual knowledge graph, project responses into the explicitly selected language, and resolve submitted short text into canonical intent IDs before the unchanged CLIPS score path. Preserve the downloaded source checkpoints, fine-tune one compact classifier per language, export each to ONNX at no more than 50 MB, and load only the selected language session.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, CLIPSpy, pytest/TestClient, Hugging Face Transformers and PyTorch for offline training, ONNX and ONNX Runtime for production inference, pypdf/ReportLab/Poppler for the tracked PDF.

**Spec:** `docs/superpowers/specs/2026-08-24-phase6-bilingual-knowledge-design.md`

## Global Constraints

- Supported languages are exactly `ar` and `en`; the user selects one explicitly.
- User-facing prose returns only the selected language; official brand names may remain unchanged.
- Each final ONNX classifier file must be at most 52,428,800 bytes.
- Load only the requested language model and make no external inference call.
- Preserve source checkpoints unchanged and verify every copied file by SHA-256.
- Keep binary model weights out of Git history; commit manifests, configs, hashes, and reports.
- Keep CLIPS rule compilation and score arithmetic unchanged.
- The knowledge snapshot has four stages, exactly ten tool assignments per stage, no tool in more than three stages, and 20 questions at a 12/4/4 choice/short-text/Boolean ratio.
- The frozen holdout contains exactly 100 Arabic and 100 English TestClient requests and is never training, alias, or calibration data.
- Require at least 96 complete passes and intent Macro-F1 >= 0.90 independently for each language.
- Follow RED-GREEN-REFACTOR for every production behavior and commit each green increment atomically.
- Do not claim 90% accuracy until the frozen evaluator passes both languages.

---

### Task 1: Preserve and verify the downloaded checkpoints

**Files:**
- Modify: `.gitignore`
- Modify: `app/domain/models.py`
- Modify: `app/domain/__init__.py`
- Create: `app/text_intent/__init__.py`
- Create: `app/text_intent/artifacts.py`
- Create: `artifacts/models-manifest.json`
- Create: `scripts/copy_pretrained_models.py`
- Create: `tests/test_model_artifacts.py`
- Local-only: `artifacts/pretrained/en/*`
- Local-only: `artifacts/pretrained/ar/*`

**Interfaces:**
- Produces: `Language` with exactly `ar` and `en` before artifact code consumes it.
- Produces: `CheckpointSpec(language, vocab_size, required_files, file_hashes)`.
- Produces: `identify_checkpoint(source: Path) -> Language`.
- Produces: `copy_checkpoint(source: Path, destination: Path, spec: CheckpointSpec) -> list[Path]`.
- Preserves: the exact desktop source files without modification.

- [ ] **Step 1: Write failing checkpoint identity tests**

Create temporary source folders with `config.json` and a vocabulary file. Assert:

```python
def test_identify_checkpoint_uses_vocab_size_not_folder_name(tmp_path: Path) -> None:
    english = checkpoint_dir(tmp_path / "عربي", vocab_size=30_522)
    arabic = checkpoint_dir(tmp_path / "انكليزي", vocab_size=32_000)

    assert identify_checkpoint(english) is Language.ENGLISH
    assert identify_checkpoint(arabic) is Language.ARABIC


def test_identify_checkpoint_rejects_unknown_vocab_size(tmp_path: Path) -> None:
    source = checkpoint_dir(tmp_path / "unknown", vocab_size=1_024)
    with pytest.raises(ModelArtifactError, match="unsupported checkpoint"):
        identify_checkpoint(source)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_model_artifacts.py -v
```

Expected: collection fails because `app.text_intent.artifacts` does not exist.

- [ ] **Step 3: Add the minimal shared language enum**

Add and export:

```python
class Language(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"
```

Do not add localized display contracts until Task 2.

- [ ] **Step 4: Implement identity, allow-list copying, and hash verification**

Implement the public boundary:

```python
class ModelArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckpointSpec:
    language: Language
    vocab_size: int
    required_files: tuple[str, ...]
    file_hashes: Mapping[str, str]
```

Implement the functions with these bodies:

```python
def identify_checkpoint(source: Path) -> Language:
    config = json.loads((source / "config.json").read_text(encoding="utf-8"))
    try:
        return {30_522: Language.ENGLISH, 32_000: Language.ARABIC}[
            int(config["vocab_size"])
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise ModelArtifactError(f"unsupported checkpoint: {source}") from error


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def copy_checkpoint(
    source: Path, destination: Path, spec: CheckpointSpec
) -> list[Path]:
    if identify_checkpoint(source) is not spec.language:
        raise ModelArtifactError(f"checkpoint language mismatch: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for filename in spec.required_files:
        source_file = source / filename
        expected_hash = spec.file_hashes[filename]
        if not source_file.is_file() or sha256_file(source_file) != expected_hash:
            raise ModelArtifactError(f"checkpoint hash mismatch: {filename}")
        destination_file = destination / filename
        temporary_file = destination / f".{filename}.copying"
        shutil.copyfile(source_file, temporary_file)
        if sha256_file(temporary_file) != expected_hash:
            temporary_file.unlink(missing_ok=True)
            raise ModelArtifactError(f"copied checkpoint hash mismatch: {filename}")
        temporary_file.replace(destination_file)
        copied.append(destination_file)
    return copied
```

Copy only the allow-listed files. Write to a temporary sibling file, verify its hash,
then atomically replace the destination. Reject missing, unexpected-hash, or wrong-model
inputs without leaving a partial destination.

- [ ] **Step 5: Add the committed manifest and local artifact exclusions**

Add these source entries to `artifacts/models-manifest.json`:

```json
{
  "sources": {
    "en": {
      "model_id": "prajjwal1/bert-mini",
      "license": "MIT",
      "vocab_size": 30522,
      "weight_file": "pytorch_model.bin",
      "files": {
        "config.json": "D32AC9FAF7E47097BEA0395FD2E0CC8AFC9CE038AD7FA41BDFFA37386972B524",
        "pytorch_model.bin": "F7902E759E678CF77852A40A710E79BB83ACB475C44C177773246D610818A5DB",
        "vocab.txt": "07ECED375CEC144D27C900241F3E339478DEC958F92FDDBC551F295C992038A3"
      }
    },
    "ar": {
      "model_id": "asafaya/bert-mini-arabic",
      "license": "MIT",
      "vocab_size": 32000,
      "weight_file": "model.safetensors",
      "files": {
        "config.json": "819CBFEC3FA53698CE51C2ABB64F3DC13418546834188454978EA47A939E1BC8",
        "model.safetensors": "CF1F64FDEA5DBC06F9EC67AF829075E5CE59FA08F1C935F90EB14FE4128B3763",
        "special_tokens_map.json": "303DF45A03609E4EAD04BC3DC1536D0AB19B5358DB685B6F3DA123D05EC200E3",
        "tokenizer_config.json": "359FDD360BE3DE14228B56E2CA9C6C940FF0B1A3DC88A5BF32BDEEB21EC7BE9C",
        "vocab.txt": "793ACD486C6B6621166CD1A061B5D70FD301F623B0E05FC834FE77BA444E02A0"
      }
    }
  }
}
```

Ignore `artifacts/pretrained/`, `artifacts/text-intent/**/*.onnx`, and copied binary
weights while retaining `artifacts/models-manifest.json` and final JSON configs.

- [ ] **Step 6: Implement and run the copy command**

The script accepts explicit source paths and defaults matching the verified desktop
locations:

```powershell
.venv\Scripts\python.exe scripts\copy_pretrained_models.py `
  --english-source "C:\Users\ST\Desktop\عربي" `
  --arabic-source "C:\Users\ST\Desktop\انكليزي" `
  --destination artifacts\pretrained
```

Expected: English and Arabic files are copied under their correct language codes and
the script prints verified SHA-256 values. Re-run it to prove idempotence.

- [ ] **Step 7: Verify and commit Task 1**

Run the focused tests, `git diff --check`, and `git status --short`. Confirm no binary
weight is staged, then commit:

```powershell
git add .gitignore app\domain app\text_intent artifacts\models-manifest.json scripts\copy_pretrained_models.py tests\test_model_artifacts.py
git commit -m "feat: preserve verified compact model sources"
```

---

### Task 2: Add bilingual domain and submitted-answer contracts

**Files:**
- Modify: `app/domain/models.py`
- Modify: `app/domain/__init__.py`
- Modify: `app/api/contracts.py`
- Modify: `app/api/routes.py`
- Modify: `app/recommendations/explanations.py`
- Modify: `app/recommendations/service.py`
- Modify: `tests/test_domain_models.py`
- Modify: `tests/test_api.py`
- Modify: test fixtures in `tests/test_knowledge.py`, `tests/test_expert_engine.py`, and `tests/test_recommendations.py`

**Interfaces:**
- Produces: `LocalizedText` and `TextIntent` using `Language` from Task 1.
- Produces: `LocalizedText.for_language(language: Language) -> str`.
- Produces: `SubmittedAnswer(question_id, option_ids=None, text=None)` with exactly one representation.
- Extends: `RecommendationRequest(language, answers)`.
- Preserves: canonical IDs, weights, URLs, dates, and existing CLIPS value bounds.

- [ ] **Step 1: Write failing localization and answer-union tests**

Add tests asserting:

```python
def test_localized_text_requires_both_languages() -> None:
    with pytest.raises(ValidationError):
        LocalizedText(ar="تحليل")


def test_localized_text_projects_only_the_requested_language() -> None:
    text = LocalizedText(ar="تحليل", en="Analysis")
    assert text.for_language(Language.ARABIC) == "تحليل"
    assert text.for_language(Language.ENGLISH) == "Analysis"


@pytest.mark.parametrize(
    "payload",
    [
        {"question_id": "q"},
        {"question_id": "q", "option_ids": ["yes"], "text": "yes"},
    ],
)
def test_submitted_answer_requires_exactly_one_representation(payload: dict) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        SubmittedAnswer.model_validate(payload)
```

Also assert short text is trimmed, limited to 500 characters, and duplicate option IDs
are rejected.

- [ ] **Step 2: Verify RED**

Run only the new tests. Expected: imports fail for the new contracts.

- [ ] **Step 3: Implement strict bilingual models**

Add `LocalizedText` and `TextIntent` alongside the existing `Language`:

```python
class LocalizedText(DomainModel):
    ar: NonEmptyText
    en: NonEmptyText

    def for_language(self, language: Language) -> str:
        return self.ar if language is Language.ARABIC else self.en


class TextIntent(DomainModel):
    id: Identifier
    label: LocalizedText
    value: float = Field(ge=-1.0, le=1.0, allow_inf_nan=False)
    aliases: dict[Language, list[NonEmptyText]]
```

Change knowledge display fields to `LocalizedText`. Add
`Question.text_intents: list[TextIntent]`. Enforce option/intents exclusivity and at
least two intents for short-text questions. Specifically change `Stage.name`,
`Tool.name`, `Tool.description`, `AnswerOption.label`, `Question.prompt`,
`EvaluationSource.name`, `EvaluationSource.publisher`, `RuleImpact.rationale`,
while keeping computed `Recommendation.tool_name` and `Recommendation.reason` as
already projected strings.

- [ ] **Step 4: Implement the HTTP-only submitted-answer contract**

Keep expert-engine `AnswerSelection` canonical and option-ID based. Add to the API:

```python
ShortAnswerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class SubmittedAnswer(DomainModel):
    question_id: Identifier
    option_ids: list[Identifier] | None = None
    text: ShortAnswerText | None = None

    @model_validator(mode="after")
    def validate_representation(self) -> Self:
        if (self.option_ids is None) == (self.text is None):
            raise ValueError("exactly one answer representation is required")
        return self
```

Add `language: Language` to `RecommendationRequest` and migrate test fixtures to
bilingual values without weakening strict validation. Pass the request language into
`RecommendationService.recommend`. Make `build_reason` accept `Language`, select the
localized rationale, and keep its existing bounded-string behavior. The service selects
the localized tool name and reason when constructing `RecommendationResult`, which
keeps the affected suite green before Task 3 changes response DTOs.

- [ ] **Step 5: Verify and commit Task 2**

Run domain, API-contract, knowledge, expert-engine, and recommendation tests. Commit
only when all affected tests pass:

```powershell
git commit -m "feat: define bilingual domain contracts"
```

---

### Task 3: Project API reads and recommendations into the selected language

**Files:**
- Create: `app/localization/__init__.py`
- Create: `app/localization/models.py`
- Create: `app/localization/projector.py`
- Modify: `app/api/routes.py`
- Modify: `app/recommendations/service.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_recommendations.py`

**Interfaces:**
- Produces: `StageResponse`, `QuestionResponse`, `AnswerOptionResponse`, `ToolResponse`, and localized recommendation response models.
- Produces: pure projection functions that accept a domain object and `Language`.
- Changes: localized GET routes require `language: Language` query input.
- Changes: recommendation output receives the request language and contains only projected strings.

- [ ] **Step 1: Write failing API-language tests**

Assert that `/api/stages` without `language` returns 422, `?language=ar` contains Arabic
without an `en` field, and `?language=en` contains English without an `ar` field. Add
the same assertions for questions, options, tools, names, descriptions, and reasons.

- [ ] **Step 2: Verify RED**

Run `pytest tests/test_api.py -k language -v`. Expected: current routes accept no
language and leak the internal shape.

- [ ] **Step 3: Implement pure response projection**

Use response-only models with plain string display fields. For a short-text question,
return `options=[]`; do not expose canonical text-intent IDs or aliases to clients.

```python
def project_stage(stage: Stage, language: Language) -> StageResponse:
    return StageResponse(id=stage.id, name=stage.name.for_language(language))


def project_question(question: Question, language: Language) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        stage=question.stage,
        prompt=question.prompt.for_language(language),
        type=question.type,
        importance=question.importance,
        options=[
            AnswerOptionResponse(
                id=option.id,
                label=option.label.for_language(language),
                value=option.value,
            )
            for option in question.options
        ],
    )


def project_tool(tool: Tool, language: Language) -> ToolResponse:
    return ToolResponse(
        id=tool.id,
        name=tool.name.for_language(language),
        description=tool.description.for_language(language),
        stages=tool.stages,
    )


def project_result(
    result: RecommendationResult, language: Language
) -> RecommendationResponse:
    return RecommendationResponse(
        recommendations=[
            RecommendationItemResponse(
                tool_id=item.tool_id,
                tool_name=item.tool_name,
                reason=item.reason,
            )
            for item in result.recommendations
        ]
    )
```

- [ ] **Step 4: Require language on all localized routes**

Add `language: Language` to all three GET handlers and use
`request.language` for POST projection. Keep canonical IDs and deterministic ordering
identical in both languages.

- [ ] **Step 5: Verify OpenAPI and commit Task 3**

Assert OpenAPI documents the required language parameter and the bilingual POST field.
Run affected tests and commit:

```powershell
git commit -m "feat: expose explicitly selected response language"
```

---

### Task 4: Load and structurally audit canonical knowledge JSON

**Files:**
- Create: `app/knowledge/loader.py`
- Modify: `app/knowledge/__init__.py`
- Modify: `app/knowledge/models.py`
- Modify: `app/main.py`
- Create: `scripts/audit_phase6.py`
- Create: `tests/test_knowledge_loader.py`
- Modify: `tests/test_health.py`

**Interfaces:**
- Produces: `load_knowledge(path: Path) -> KnowledgeSnapshot`.
- Produces: `audit_knowledge(snapshot: KnowledgeSnapshot) -> KnowledgeAudit`.
- Produces: a package-relative `default_knowledge_path()` for Task 5 to activate after the production JSON exists.
- Fails: missing, malformed, or structurally invalid production JSON aborts application construction.

- [ ] **Step 1: Write failing loader tests**

Cover valid loading, missing file, malformed JSON, extra fields, dangling IDs, and
deterministic Pydantic error wrapping. Ensure error messages include the file path but
not the full source JSON.

- [ ] **Step 2: Write failing audit invariant tests**

The audit must reject every independent violation:

```python
assert audit.stage_assignment_counts == {
    StageId.ANALYSIS: 10,
    StageId.DESIGN: 10,
    StageId.IMPLEMENTATION: 10,
    StageId.TESTING: 10,
}
assert audit.question_type_counts == {
    "choice": 12,
    "short_text": 4,
    "boolean": 4,
}
```

Also reject a tool in four stages, a stage without exactly five questions, a missing
rule target, a source without `collected_at`, model-evaluation evidence with fewer than
three source IDs, and code-editor evidence with fewer than two source IDs.

- [ ] **Step 3: Verify RED**

Run `tests/test_knowledge_loader.py`. Expected: loader/audit imports fail.

- [ ] **Step 4: Implement loading and audit reports**

Use `Path.read_text(encoding="utf-8")`, `json.loads`, and
`KnowledgeSnapshot.model_validate`. Define safe `KnowledgeLoadError` and an immutable
audit result with exact counts and violations. The CLI prints JSON and returns exit 1
for any violation.

- [ ] **Step 5: Add the default-path helper without activating it**

Return a stable package-relative `data/knowledge/phase6.json` path, but keep
`create_app()` on its current explicit/empty behavior until Task 5 creates and audits
the file. Test the path deterministically without depending on the current directory.

- [ ] **Step 6: Verify and commit Task 4**

Run loader, health, and existing API tests. Commit:

```powershell
git commit -m "feat: load and audit phase-six knowledge JSON"
```

---

### Task 5: Build the sourced bilingual Phase 6 knowledge snapshot

**Files:**
- Create: `data/knowledge/phase6.json`
- Create: `docs/knowledge/phase6-source-ledger.md`
- Modify: `tests/test_knowledge_loader.py`
- Modify: `scripts/audit_phase6.py`

**Interfaces:**
- Consumes: the loader and audit contract from Task 4.
- Produces: the production snapshot loaded by `create_app()`.
- Produces: source-ledger rows mapping every claim family to primary URLs and collection date `2026-08-24`.

- [ ] **Step 1: Freeze the exact stage-tool assignment matrix**

Use these ten assignments per stage:

```text
analysis: ChatGPT, Claude, Gemini, Perplexity, NotebookLM, Elicit,
          Consensus, Scite, ResearchRabbit, Semantic Scholar
design:   Canva Magic Studio, Adobe Firefly, Figma AI, Midjourney,
          OpenAI Image Generation, Stable Diffusion, Uizard, Framer AI,
          Whimsical AI, Leonardo AI
implementation: GitHub Copilot, Cursor, Windsurf, Claude Code, OpenAI Codex,
                Amazon Q Developer, Gemini Code Assist, JetBrains AI Assistant,
                Replit Agent, Qodo
testing: GitHub Copilot, Cursor, Claude Code, OpenAI Codex, Qodo,
         Testim, mabl, Applitools, Snyk DeepCode, Diffblue Cover
```

Shared tools are canonical single records with multiple stages. No tool appears in
more than implementation and testing.

- [ ] **Step 2: Collect and record primary evidence**

For every tool, record its official product documentation and official repository when
available. For model-evaluation claims, record at least three independent sources from
official model cards, primary papers, or published benchmarks. For code-editor claims,
record at least two independent sources. Store exact URLs, publisher, source kind,
publication date when known, and `collected_at=2026-08-24`.

- [ ] **Step 3: Freeze the 20-question matrix**

Create five questions per stage in this order:

```text
analysis: primary goal (single), evidence needs (multiple), privacy (single),
          research need (short text), citations required (boolean)
design: output type (single), style controls (multiple), collaboration (single),
        asset need (short text), commercial use (boolean)
implementation: environment (single), languages (multiple), repository privacy (single),
                coding task (short text), IDE integration (boolean)
testing: scope (single), test types (multiple), execution target (single),
         defect/risk (short text), CI integration (boolean)
```

This yields 12 choice, four short-text, and four Boolean questions.

- [ ] **Step 4: Define the exact short-text intent labels**

Use four intents per short-text question:

```text
analysis-q4: evidence_synthesis, literature_discovery, citation_validation, document_grounded_review
design-q4: image_generation, ui_prototyping, brand_asset, diagramming
implementation-q4: code_generation, debugging, refactoring, repository_task
testing-q4: test_generation, visual_testing, security_testing, regression_automation
```

Give each intent Arabic/English labels, bounded values, initial exact aliases, and
sourced rule impacts. Alias strings used here cannot appear in calibration or frozen
acceptance data.

- [ ] **Step 5: Write the production JSON and run the audit**

Create rules for every choice option and text intent. Ensure at least three tools can
receive positive evidence for every valid response path. Run:

```powershell
.venv\Scripts\python.exe scripts\audit_phase6.py --knowledge data\knowledge\phase6.json
```

Expected: all exact counts and source requirements pass.

- [ ] **Step 6: Test default application reads in both languages**

After the JSON audit is green, change `create_app()` to load
`default_knowledge_path()` when no snapshot is injected. Replace tests that intentionally
need no data with `create_app(knowledge=KnowledgeSnapshot())`. Use TestClient against
`create_app()` and assert four stages, five questions per stage,
ten assigned tools per stage through the audited snapshot, and language-only display
text.

- [ ] **Step 7: Commit Task 5**

```powershell
git commit -m "feat: add sourced bilingual phase-six knowledge"
```

---

### Task 6: Resolve submitted answers and integrate short-text intents with CLIPS

**Files:**
- Create: `app/text_intent/contracts.py`
- Create: `app/text_intent/normalization.py`
- Create: `app/text_intent/aliases.py`
- Create: `app/text_intent/service.py`
- Modify: `app/text_intent/__init__.py`
- Modify: `app/expert_engine/validation.py`
- Modify: `app/recommendations/service.py`
- Modify: `app/api/dependencies.py`
- Modify: `app/api/routes.py`
- Create: `tests/test_text_intent.py`
- Modify: `tests/test_expert_engine.py`
- Modify: `tests/test_recommendations.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `IntentPrediction(question_id, intent_id, confidence, margin, source)`.
- Produces: `TextIntentClassifier.predict(language, question, text) -> IntentPrediction` protocol.
- Produces: `AnswerResolutionService.resolve(language, submitted_answers, questions) -> list[AnswerSelection]`.
- Changes: expert-engine option resolution accepts `Question.text_intents` as canonical answer values.
- Preserves: `ClipspyAdapter`, CLIPS templates, compiled rule syntax, and score formula.

- [ ] **Step 1: Write failing normalization tests**

Assert Arabic NFKC, diacritic removal, tatweel removal, and whitespace normalization.
Assert English NFKC, case folding, and whitespace normalization. Assert neither path
translates or transliterates product names.

- [ ] **Step 2: Write failing answer-resolution tests**

Cover choice passthrough, short-text alias resolution, classifier fallback, wrong
answer representation, classifier label for another question, uncertainty, duplicate
questions, and raw-text redaction from errors.

- [ ] **Step 3: Verify RED**

Run `pytest tests/test_text_intent.py -v`. Expected: new modules are missing.

- [ ] **Step 4: Implement normalization and exact alias lookup**

Build an immutable index keyed by `(language, question_id, normalized_alias)`. Reject
duplicate aliases that map to different intents. Return source `alias` with confidence
and margin 1.0 for an exact match.

- [ ] **Step 5: Implement the injected classifier boundary and resolver**

The resolver validates submitted representation against the actual question type. It
uses aliases first, then the injected classifier, validates the returned label belongs
to the question, and produces canonical expert-engine `AnswerSelection` objects.

- [ ] **Step 6: Remove the short-text rejection through a failing engine test**

Replace `test_validate_inference_input_rejects_short_text_until_supported` with a test
that selects one canonical text intent and expects the matching CLIPS rule to fire.
Update `_resolve_answers` to index `question.text_intents` only for short-text questions.
Do not change `compiler.py` or CLIPS templates.

- [ ] **Step 7: Wire the route to resolution before recommendation**

Dependency-inject `AnswerResolutionService`. Convert submitted answers to canonical
answers in the POST handler, then call the existing recommendation service. Translate
known text errors to safe 422 responses and unavailable classifier artifacts to 503.

- [ ] **Step 8: Verify and commit Task 6**

Run focused text, engine, recommendation, and API tests, then the complete suite. Commit:

```powershell
git commit -m "feat: resolve bilingual short text into CLIPS intents"
```

---

### Task 7: Create leak-resistant training, calibration, and acceptance datasets

**Files:**
- Create: `data/text_intent/train.ar.jsonl`
- Create: `data/text_intent/train.en.jsonl`
- Create: `data/text_intent/calibration.ar.jsonl`
- Create: `data/text_intent/calibration.en.jsonl`
- Create: `data/text_intent/acceptance.ar.jsonl`
- Create: `data/text_intent/acceptance.en.jsonl`
- Create: `app/text_intent/datasets.py`
- Create: `tests/test_text_intent_data.py`
- Modify: `scripts/audit_phase6.py`

**Interfaces:**
- Produces: `TextIntentRow(id, language, question_id, intent_id, text, split, provenance, template_family)`.
- Produces: `load_text_intent_rows(path: Path) -> tuple[TextIntentRow, ...]`.
- Produces: `DatasetSplit` with `train`, `calibration`, and `acceptance` values.
- Produces: `audit_text_intent_splits(paths: Mapping[Language, Mapping[DatasetSplit, Path]], knowledge: KnowledgeSnapshot) -> DatasetAudit`.

- [ ] **Step 1: Write failing strict-row and split-audit tests**

Reject extra fields, invalid languages, unknown question/intent pairs, duplicate IDs,
duplicate normalized text across splits, and a `template_family` crossing splits.

- [ ] **Step 2: Verify RED and implement dataset validation**

Run the focused tests, implement line-numbered JSONL validation, then rerun them green.

- [ ] **Step 3: Author the training and calibration rows**

For each of the 16 `(question_id, intent_id)` labels and each language, author at least
20 training rows and five calibration rows. Training therefore has at least 320 rows
per language; calibration has at least 80 rows per language. Include affirmative,
negative-boundary, spelling, punctuation, and brand-name variants without copying
aliases or acceptance sentences.

- [ ] **Step 4: Freeze exactly 100 acceptance rows per language**

Allocate 25 rows to each short-text question. Within each group allocate intents as
7/6/6/6 and rotate the seven-row intent across questions. Every acceptance row also
stores the supporting choice answers and the expected ordered top-three tool IDs needed
for a complete TestClient request.

- [ ] **Step 5: Run leakage and distribution audits**

Require exact acceptance counts, complete intent coverage, no normalized or template
family overlap, and no acceptance text in knowledge aliases. Store the combined dataset
SHA-256 in the audit output.

- [ ] **Step 6: Commit Task 7**

```powershell
git commit -m "test: freeze bilingual text-intent datasets"
```

After this commit, acceptance files are immutable for the current model evaluation.

---

### Task 8: Fine-tune compact classifiers and export <=50 MB ONNX artifacts

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/train_text_intent.py`
- Create: `app/text_intent/training.py`
- Create: `tests/test_text_intent_training.py`
- Local-only: `artifacts/text-intent/ar/model.onnx`
- Local-only: `artifacts/text-intent/en/model.onnx`
- Create: `artifacts/text-intent/ar/runtime.json`
- Create: `artifacts/text-intent/en/runtime.json`
- Modify: `artifacts/models-manifest.json`

**Interfaces:**
- Produces: deterministic label maps sorted by `<question_id>::<intent_id>`.
- Produces: `TrainingConfig(seed=1729, max_length=128, epochs, learning_rate, batch_size)`.
- Produces: ONNX input names `input_ids`, `attention_mask`, and `token_type_ids`; output `logits`.
- Produces: per-language `runtime.json` with labels, thresholds, margins, hashes, and source metadata.

- [ ] **Step 1: Add isolated ML dependency groups**

Keep ONNX Runtime and tokenizer support in production dependencies. Put PyTorch,
Transformers, ONNX export, and evaluation dependencies in an `ml` optional group so
production does not install PyTorch. Install and run `pip check` before training.

- [ ] **Step 2: Write failing deterministic preprocessing tests**

Assert stable label ordering, question-prompt/text pairing, fixed seeds, max length 128,
and dataset hashes included in output metadata. Test that exporting a file larger than
52,428,800 bytes raises `ModelSizeError`.

- [ ] **Step 3: Verify RED and implement training utilities**

Implement pure preprocessing/config functions first. Keep device selection explicit
and print CPU/CUDA choice. Do not download a model from the internet; require the
verified `artifacts/pretrained/<language>` source. Because the compact English config
does not declare `model_type`, instantiate both sources explicitly with `BertConfig`,
`BertTokenizer`, and `BertForSequenceClassification`; do not use `AutoModel` discovery.

- [ ] **Step 4: Fine-tune English and Arabic separately**

Run full-encoder sequence-classification fine-tuning with seed 1729. Select epochs and
learning rate only from training/calibration results. Save the best calibration
Macro-F1 checkpoint; never inspect acceptance labels during tuning.

- [ ] **Step 5: Calibrate confidence and margin thresholds**

For each language, choose thresholds from calibration predictions to maximize coverage
subject to precision >= 0.96. Store probability and top-one/top-two margin thresholds
in `runtime.json`.

- [ ] **Step 6: Export and validate ONNX candidates**

Export with dynamic batch and sequence axes. Compare ONNX logits to PyTorch logits on
at least 32 calibration samples with maximum absolute difference <= 0.001. Require each
model file <= 52,428,800 bytes. If a model exceeds the limit, produce a dynamic INT8
candidate and keep it only after parity and frozen acceptance evaluation.

- [ ] **Step 7: Record final artifact hashes without staging binaries**

Update the manifest with ONNX SHA-256, byte size, dataset hash, runtime-config hash,
training seed, and dependency versions. Confirm `git status` does not show `.onnx`.

- [ ] **Step 8: Commit Task 8 metadata and training code**

```powershell
git commit -m "feat: train compact bilingual intent classifiers"
```

---

### Task 9: Add lazy ONNX production inference

**Files:**
- Create: `app/text_intent/onnx.py`
- Modify: `app/text_intent/service.py`
- Modify: `app/text_intent/__init__.py`
- Modify: `app/api/dependencies.py`
- Modify: `app/main.py`
- Create: `tests/test_onnx_text_intent.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `OnnxTextIntentClassifier(model_root: Path)`.
- Produces: one cached session per language, created only on first use.
- Consumes: tokenizer files, `model.onnx`, and `runtime.json` under the selected language.
- Raises: safe `ModelUnavailableError`, `ModelIntegrityError`, or `UncertainTextIntentError`.

- [ ] **Step 1: Write failing lazy-loading and language-isolation tests**

With injected fake session factories, assert construction loads no model, the first
Arabic call loads only Arabic, repeated Arabic calls reuse one session, and the first
English call then loads exactly one English session.

- [ ] **Step 2: Write failing integrity and uncertainty tests**

Reject missing files, hash mismatch, unknown output label, label for another question,
probability below threshold, and margin below threshold. Assert errors never contain
submitted text.

- [ ] **Step 3: Verify RED and implement ONNX session holders**

Protect cache creation with a lock, but perform prediction without a global request
lock. Tokenize prompt/text with max length 128 and return softmax probability and
top-one/top-two margin from logits.

- [ ] **Step 4: Wire the production default and dependency injection**

`create_app()` creates the classifier boundary without opening model files. Tests may
inject a fake classifier or resolver. A model-dependent request returns 503 only when
its selected artifact is missing; choice-only requests do not load a model.

- [ ] **Step 5: Run real local smoke tests**

Run one unseen Arabic and one unseen English calibration example through the actual
ONNX sessions, then through `POST /api/recommendations`. Record model load time and
warm-request time without claiming the final accuracy gate.

- [ ] **Step 6: Verify and commit Task 9**

```powershell
git commit -m "feat: run selected-language intent inference locally"
```

---

### Task 10: Execute the frozen 200-request gate and publish the report

**Files:**
- Create: `tests/test_phase6_acceptance.py`
- Create: `app/text_intent/evaluation.py`
- Create: `artifacts/evaluation/phase6-acceptance.json`
- Modify: `scripts/audit_phase6.py`

**Interfaces:**
- Produces: exactly 200 parameterized TestClient cases.
- Produces: per-language accuracy, complete-pass count, Macro-F1, confusion matrix, latency percentiles, Wilson lower bound, and hashes.
- Exits nonzero unless both languages meet every gate.

- [ ] **Step 1: Write the evaluator metric tests**

Use small fixed confusion matrices to verify accuracy, Macro-F1, and Wilson bounds.
Assert 96/100 has lower bound >= 0.90 and 95/100 does not.

- [ ] **Step 2: Verify RED and implement metrics**

Run the focused tests. Implement metrics without rounding during gate decisions; round
only report display values.

- [ ] **Step 3: Implement exactly 200 real TestClient cases**

Load the frozen acceptance JSONL, assert 100 rows per language before creating the
parameter list, and submit every case to `create_app()` with real knowledge, resolver,
ONNX classifier, CLIPS, ranking, and localization. Count rejection, non-200, intent
mismatch, or ordered recommendation mismatch as failure. Wrap the real classifier in
a test-only `AuditingClassifier` decorator that records the prediction returned during
the request; compare that recorded canonical intent without exposing it in the HTTP
response.

- [ ] **Step 4: Run the immutable gate**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_phase6_acceptance.py -v
```

Require Arabic complete passes >= 96, English complete passes >= 96, and intent
Macro-F1 >= 0.90 for both. Do not edit acceptance rows after observing results. Fix
training data, aliases that are not acceptance strings, thresholds, or model training,
then retrain and rerun when a gate fails.

- [ ] **Step 5: Write and validate the evaluation report**

Store the exact model, runtime-config, knowledge, and dataset hashes plus all metrics
and latency percentiles. `scripts/audit_phase6.py` independently recomputes and verifies
the report against local artifacts.

- [ ] **Step 6: Commit Task 10**

```powershell
git commit -m "test: verify 200 bilingual recommendation cases"
```

---

### Task 11: Update the backend plan PDF and complete project verification

**Files:**
- Modify: `scripts/update_backend_plan_pdf.py`
- Modify: `tests/test_backend_plan_pdf.py`
- Modify: `output/pdf/ai_expert_system_backend_plan_ar.pdf`
- Review: every path changed since commit `883bdb8`

**Interfaces:**
- Produces: exactly eight PDF pages.
- Preserves: original pages 1-5 and Phase 4/5 appendices.
- Adds: metadata `/Phase6Knowledge = 1` and a measured Phase 6 appendix.

- [ ] **Step 1: Write the failing Phase 6 PDF test**

Assert an idempotent rebuild has exactly eight pages and markers for Phase 4, Phase 5,
and Phase 6. Assert final-page extracted text contains `ar`, `en`, both final model byte
sizes, `200`, both complete-pass counts, both Macro-F1 values, and `pytest -q: PASS`.

- [ ] **Step 2: Verify RED**

Run `pytest tests/test_backend_plan_pdf.py -v`. Expected: seven pages and no Phase 6
marker.

- [ ] **Step 3: Extend the idempotent PDF builder**

Read measured values from `artifacts/evaluation/phase6-acceptance.json`; never hard-code
passing metrics. Rebuild from the first five pages plus three generated appendices so
running twice remains eight pages.

- [ ] **Step 4: Run structural and visual PDF verification**

Run the PDF test, rebuild the tracked artifact, render all eight pages with bundled
Poppler, and inspect Arabic shaping, margins, clipping, overlap, footers, and page
numbers. Verify all three metadata markers with pypdf.

- [ ] **Step 5: Run one fresh complete verification**

Run exactly:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest tests\test_phase6_acceptance.py -v
.venv\Scripts\python.exe -m compileall -q app tests scripts
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\audit_phase6.py
git diff --check
git status --short --branch
```

Read every exit code and failure count before making any completion claim.

- [ ] **Step 6: Refresh and verify the code graph**

Force a full repository re-index after the large update. Search and trace the request
path from `create_recommendations` through answer resolution, selected-language ONNX
prediction, recommendation service, CLIPS, ranking, and projection. Run
`check_index_coverage` over every changed Python path and read direct source for every
stale, skipped, partial, excluded, or unknown range.

- [ ] **Step 7: Review the final diff and commit Task 11**

Review tests before production files, scan staged changes for secrets and binary model
weights, and commit only the verified PDF/code changes:

```powershell
git commit -m "docs: record verified bilingual phase six"
```

Report the exact commits, final model sizes/hashes, Arabic and English metrics, total
test count, PDF path, and any claim limitation. Do not report the project complete if
either language gate or any regression command fails.
