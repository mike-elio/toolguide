# Adaptive AI Tool Guide

[![CI](https://github.com/mike-elio/toolguide/actions/workflows/ci.yml/badge.svg)](https://github.com/mike-elio/toolguide/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An evidence-backed, bilingual tool recommendation system. It asks 6–10 adaptive questions, scopes the decision to a project stage and technical domain, and returns up to three eligible recommendations with comparison details, starter guides, and a what-if preview.

> **بالعربية:** دليل لاختيار الأدوات بالعربية والإنجليزية. حدّد المرحلة والمجال والشروط الإلزامية، ثم أجب عن أسئلة متكيّفة. قارن الأدوات المؤهلة، جرّب «ماذا لو؟» دون تغيير الأصل، وابدأ بخطوات عملية موثقة. إذا لم توجد أداة موثقة تحقق شروطك يظهر السبب بوضوح.

## Highlights

- 192 catalog tools across Analysis, Design, Implementation, and Testing.
- Three domains: Software, Artificial Intelligence, and Cybersecurity.
- 12 isolated stage/domain pools with 16 tools and 56 pre-authored questions each (672 questions total).
- Deterministic, stateless questionnaire sessions with a 6-question minimum and 10-question maximum.
- Explainable results with positive reasons, limitations, confidence, and official sources.
- Hard requirements for documented offline operation, a free plan, or open source; unknown evidence never satisfies a requirement.
- Side-by-side comparison and 192 bilingual, tool-specific starter guides.
- Setup-specific evidence separates online preparation from offline runtime and checks combined requirements against the same setup.
- What-if previews of previous answers and requirements, with explicit adoption or cancellation.
- Arabic and English interface with responsive and accessible native controls.
- Local-first short-text classification through curated aliases and optional Ollama fallback.
- No model training, runtime web search, database, or cloud API key required.

## How it works

1. Choose a project stage: Analysis, Design, Implementation, or Testing.
2. Choose a technical domain: Software, Artificial Intelligence, or Cybersecurity.
3. Optionally set hard requirements. These exclude tools; questionnaire preferences affect ranking.
4. Answer 6–10 questions when eligible tools exist. If none qualify, see the documented conflicts and unknowns immediately.
5. Receive one to three ranked tools, or a no-match result. Compare their costs, deployment, learning curve, integrations, and limitations; open a starter guide for each tool.
6. Preview changed requirements or earlier answers with **What if?**. The original remains unchanged until **Adopt scenario**. If the revised session needs another answer or clarification, adoption resumes the questionnaire.

Questionnaire sessions are stateless and deterministic. The browser sends the complete answer history with each request, and the server validates and scores that history before selecting the next question or returning recommendations.

Scenario requests use `POST /api/questionnaire/compare` with `baseline`, `variant`, and `knowledge_version`. Both sessions must preserve the language, stage, domain, seed, and question IDs. A changed catalog returns `409 KNOWLEDGE_VERSION_MISMATCH`; re-evaluate the original first. The older `POST /api/recommendations` contract still returns exactly three tools.

## Requirements

- Python 3.12 or newer
- Node.js 24 or newer, only for the JavaScript test suite
- [Ollama](https://ollama.com/) with `gemma3:1b` for unresolved free-text answers (optional)

Known short-text aliases work without Ollama. When an answer does not match a curated alias and Ollama is unavailable, the interface displays fixed clarification choices instead of a technical error.

## Quick start

### Windows PowerShell

```powershell
git clone https://github.com/mike-elio/toolguide.git
Set-Location toolguide
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
ollama pull gemma3:1b
uvicorn app.main:app --reload --env-file .env
```

### Linux or macOS

```bash
git clone https://github.com/mike-elio/toolguide.git
cd toolguide
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
ollama pull gemma3:1b
uvicorn app.main:app --reload --env-file .env
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Ollama can be skipped if you only want to explore the application and use predefined choices or known aliases.

## Configuration

Copy `.env.example` to `.env`, then change only the values you need:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `gemma3:1b` | Local model used for unresolved short-text intent classification |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Maximum wait for a local model response |
| `FRONTEND_ORIGINS` | Local ports `3000` | Comma-separated CORS origins for a separately hosted frontend |

Do not commit `.env`; it is intentionally ignored by Git.

## Verification commands

```bash
python -m pytest -q
node --test tests/*.test.cjs
python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json.gz
python -m compileall -q app scripts
```

Run the full 250-session API simulation:

```bash
python scripts/simulate_adaptive_questionnaire.py --sessions 250 --output output/research/adaptive-questionnaire-250-session-report.md
python scripts/simulate_decision_support.py
```

Regenerate the adaptive knowledge catalog:

```bash
python scripts/build_adaptive_knowledge.py
```

The generated `data/knowledge/adaptive.json.gz` catalog is committed because it is required at runtime. It contains ordinary UTF-8 JSON compressed with Gzip; the application loads it transparently without an additional dependency.

Comparison evidence and starter content are maintained in `data/knowledge/tool_profiles.json`. The builder requires exactly one valid profile for each catalog tool and merges it into the compressed runtime catalog. Known capability values require a source and review date; missing facts remain unknown.

### Browser checks

With the server running at `http://127.0.0.1:8000`:

```bash
npm ci
npx playwright install chromium
npm run test:e2e
```

The CI browser job runs the same journeys. `PLAYWRIGHT_CHANNEL=msedge` selects an installed Edge browser when desired. `TOOLGUIDE_URL` overrides the page URL. Browser screenshots are written under `tmp/decision-support/`.

## Architecture

```text
frontend/                 Vanilla JavaScript bilingual interface
app/api/                  FastAPI routes and request contracts
app/questionnaire/        Adaptive selection and stopping policy
app/expert_engine/        CLIPS-backed inference adapter
app/text_intent/          Alias resolution and optional Ollama classifier
app/knowledge/            Validated knowledge loading and audits
data/knowledge/           Runtime tool, question, and rule catalog
scripts/                  Catalog builder, audit, and simulation tools
tests/                    Python integration/unit and Node.js UI-state tests
```

The browser sends the complete stateless history to `POST /api/questionnaire/advance`. The server validates that history belongs to one stage/domain pool, resolves the submitted answer, runs signed rule inference, and either returns the next discriminating question or up to three eligible recommendations.

## Data and recommendation notes

- Questions and tool claims are pre-authored and source-backed; they are not generated at runtime.
- Ranking uses weighted preference scores with a stable ID tie-break. Match percentages normalize each tool's own contributions; they are not probabilities and need not descend with rank.
- Confidence describes the questionnaire's separation/stability heuristic, not scientific certainty. With fewer than four eligible tools it remains low because comparison evidence is limited.
- A documented free plan may exclude premium features or impose quotas; it does not guarantee an entire workflow at no cost. Local installation does not prove offline operation, and an open SDK does not prove the whole product is open source.
- Generated preference explanations are editorial comparisons. Hard capability requirements use the separately documented profile evidence.
- Catalog size does not establish recommendation quality. Many capability values remain undocumented, and documented offline setups have not all been independently tested under operating-system network isolation.
- What-if previews reuse the original questions; they do not claim to reproduce the adaptive question path that would have been chosen from scratch. Sessions are held in browser memory; changing language or restarting starts a new session.
- Official source links and review dates are stored with the catalog.
- Source scope and retrieval limitations are recorded in [`docs/research/2026-09-05-tool-profile-sources.md`](docs/research/2026-09-05-tool-profile-sources.md).
- The research rationale is available in [`output/research/adaptive-tool-guide-deep-research-ar.md`](output/research/adaptive-tool-guide-deep-research-ar.md).
- The latest pressure-test report is available in [`output/research/adaptive-questionnaire-250-session-report.md`](output/research/adaptive-questionnaire-250-session-report.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, tests, and pull-request expectations, and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community standards. Please report security issues according to [`SECURITY.md`](SECURITY.md), never through a public issue.

## License

Licensed under the [MIT License](LICENSE).
