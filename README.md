# Adaptive AI Tool Guide

[![CI](https://github.com/mike-elio/toolguide/actions/workflows/ci.yml/badge.svg)](https://github.com/mike-elio/toolguide/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An evidence-backed, bilingual tool recommendation system. It asks 6–10 adaptive questions, scopes the decision to a project stage and technical domain, then returns three explainable recommendations.

> **بالعربية:** دليل ذكي لاختيار الأدوات يدعم العربية والإنجليزية. يختار المستخدم مرحلة المشروع ومجاله، ثم يجيب عن أسئلة متكيفة للحصول على ثلاث توصيات مع نسبة المطابقة، أسباب الاختيار، حالات عدم الملاءمة، والمصدر الرسمي.

## Highlights

- 48 curated tools across Analysis, Design, Implementation, and Testing.
- Three domains: Software, Artificial Intelligence, and Cybersecurity.
- 12 isolated stage/domain pools with 14 pre-authored questions each.
- Deterministic, stateless questionnaire sessions with a 6-question minimum and 10-question maximum.
- Explainable results with positive reasons, limitations, confidence, and official sources.
- Arabic and English interface with responsive and accessible native controls.
- Local-first short-text classification through curated aliases and optional Ollama fallback.
- No model training, runtime web search, database, or cloud API key required.

## How it works

1. Choose a project stage: Analysis, Design, Implementation, or Testing.
2. Choose a technical domain: Software, Artificial Intelligence, or Cybersecurity.
3. Answer 6–10 source-backed questions. Each answer determines which question is most useful next.
4. Receive three ranked tools with match scores, evidence-based reasons, limitations, and official sources.

Questionnaire sessions are stateless and deterministic. The browser sends the complete answer history with each request, and the server validates and scores that history before selecting the next question or returning recommendations.

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
python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json
python -m compileall -q app scripts
```

Run the full 250-session API simulation:

```bash
python scripts/simulate_adaptive_questionnaire.py --sessions 250 --output output/research/adaptive-questionnaire-250-session-report.md
```

Regenerate the adaptive knowledge catalog:

```bash
python scripts/build_adaptive_knowledge.py
```

The generated `data/knowledge/adaptive.json` file is committed because it is required at runtime.

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

The browser sends the complete stateless history to `POST /api/questionnaire/advance`. The server validates that history belongs to one stage/domain pool, resolves the submitted answer, runs signed rule inference, and either returns the next discriminating question or three ranked recommendations.

## Data and recommendation notes

- Questions and tool claims are pre-authored and source-backed; they are not generated at runtime.
- Match percentages are relative fit scores within the four eligible tools, not scientific probabilities.
- Official source links and review dates are stored with the catalog.
- The research rationale is available in [`output/research/adaptive-tool-guide-deep-research-ar.md`](output/research/adaptive-tool-guide-deep-research-ar.md).
- The latest pressure-test report is available in [`output/research/adaptive-questionnaire-250-session-report.md`](output/research/adaptive-questionnaire-250-session-report.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, tests, and pull-request expectations, and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community standards. Please report security issues according to [`SECURITY.md`](SECURITY.md), never through a public issue.

## License

Licensed under the [MIT License](LICENSE).

