## Summary

Describe the user-visible change and why it is needed.

## Verification

- [ ] `python -m pytest -q`
- [ ] `node --test tests/*.test.cjs`
- [ ] `python scripts/audit_phase6.py --knowledge data/knowledge/adaptive.json.gz`
- [ ] `python -m compileall -q app scripts`
- [ ] Manual browser verification completed when the interface changed

## Knowledge and evidence

- [ ] No catalog, question, rule, or source changes
- [ ] Catalog changes were regenerated with `scripts/build_adaptive_knowledge.py`
- [ ] New product claims and limitations include reviewable sources
- [ ] The 250-session report was refreshed when questionnaire behavior changed

## Risk and rollback

List known limitations, compatibility concerns, and the commit or change that can be reverted if needed.
