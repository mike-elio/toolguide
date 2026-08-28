# Contributing

Thank you for improving the Adaptive AI Tool Guide.

By participating, you agree to follow the project [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

1. Create and activate a Python 3.12+ virtual environment.
2. Install development dependencies with `pip install -e ".[dev]"`.
3. Copy `.env.example` to `.env` if local configuration is needed, and start Uvicorn with `--env-file .env`.
4. Optionally install Ollama and pull the model configured by `OLLAMA_MODEL`.

## Before opening a pull request

Run every project check:

```bash
python -m pytest -q
node --test tests/*.test.cjs
python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json
python -m compileall -q app scripts
git diff --check
```

If the questionnaire behavior or catalog changes, also run the 250-session simulation and commit the updated Markdown report.

## Change guidelines

- Keep commits focused and use descriptive messages such as `feat:`, `fix:`, `test:`, `docs:`, or `chore:`.
- Add or update tests for behavior changes and bug fixes.
- Keep questions, product claims, limitations, and recommendation evidence source-backed.
- Do not add runtime-generated questions or require model training.
- Do not commit `.env`, credentials, model binaries, virtual environments, caches, or build output.
- Regenerate `data/knowledge/adaptive.json` through `scripts/build_adaptive_knowledge.py`; do not hand-edit the generated catalog.
- Preserve Arabic and English coverage for user-visible content.

## Pull requests

Explain the user-facing change, verification commands, catalog or evidence changes, and any known limitations. Keep unrelated refactoring in a separate pull request.

Use the repository's issue forms for reproducible bug reports and focused feature proposals. Security vulnerabilities must follow [SECURITY.md](SECURITY.md) and must not be posted publicly.
