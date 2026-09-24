# Phase 5 HTTP API Design

## Objective

Expose the already implemented domain and recommendation engine through a typed,
deterministic FastAPI boundary. The frontend must be able to list stages, fetch
questions for one stage, inspect a tool, and submit answers for exactly three
recommendations without coupling HTTP handlers to the phase-six JSON loader.

Success means the four planned endpoints are present in OpenAPI, use the existing
error envelope, validate all client input at the HTTP boundary, and execute the real
`RecommendationService` when a validated knowledge snapshot is injected.

## Approved Assumptions

1. Phase five implements API contracts and orchestration only. JSON loading and the
   production knowledge base remain phase-six work.
2. `create_app()` may accept optional injected knowledge and recommendation service
   objects while remaining callable without arguments.
3. The default application starts with an empty knowledge snapshot. Read endpoints
   return empty collections where appropriate, and recommendation requests return
   HTTP 503 until at least three tools are available.
4. JSON field names remain `snake_case`, matching the existing strict Pydantic
   contracts. No alias layer is introduced.
5. Collection responses are ordered deterministically by stable domain identifiers.
6. The existing error envelope remains the only HTTP error shape.

## Tech Stack

- Python 3.12+
- FastAPI 0.141.1 installed, constrained by `fastapi>=0.115,<1.0`
- Pydantic 2.13.4 installed, constrained by `pydantic>=2.0,<3.0`
- CLIPSpy 1.x through the existing `RecommendationService`
- pytest 8.x and FastAPI `TestClient`

Official framework patterns:

- Routers and `include_router`: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Pydantic request bodies: https://fastapi.tiangolo.com/tutorial/body/
- Typed response models: https://fastapi.tiangolo.com/tutorial/response-model/
- Dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- HTTP errors and custom handlers: https://fastapi.tiangolo.com/tutorial/handling-errors/
- TestClient integration testing: https://fastapi.tiangolo.com/tutorial/testing/

## HTTP Contract

### `GET /api/stages`

- Response: `200` with `list[Stage]` sorted by `Stage.id`.
- The empty knowledge snapshot returns `[]`.

### `GET /api/stages/{stage}/questions`

- Path parameter: strict `StageId` enum.
- Response: `200` with `list[Question]` sorted by `Question.id`.
- A valid enum value absent from the loaded stage catalog returns `404`.
- An invalid enum value is rejected by FastAPI as `422`.

### `GET /api/tools/{tool_id}`

- Response: `200` with the matching `Tool`.
- A missing identifier returns `404`.

### `POST /api/recommendations`

- Request body: `RecommendationRequest` with `answers: list[AnswerSelection]` and
  at least one answer.
- Response: `200` with the existing `RecommendationResult` containing exactly three
  unique tools.
- The handler passes all snapshot tools, questions, and rules to the existing
  `RecommendationService`; it does not reproduce inference, ranking, or explanation
  logic.
- Fewer than three loaded tools returns `503` with a safe message.
- Invalid request structure returns `422` through the existing validation handler.
- Invalid answer selections reported by `KnowledgeValidationError` return `422`
  without exposing stack traces.
- Unexpected recommendation consistency or engine failures use the existing safe
  `500` envelope.

All failures retain this existing response shape:

```json
{
  "error": {
    "code": "HTTP_ERROR",
    "message": "Safe client-facing message",
    "details": null
  }
}
```

## Architecture and Data Flow

`KnowledgeSnapshot` is a strict Pydantic data carrier with stages, tools, questions,
rules, and benchmarks. It performs local uniqueness and reference validation so the
API never observes ambiguous IDs. It does not read files.

`create_app(knowledge=None, recommendation_service=None)` stores the selected snapshot
and service on application state. A documented FastAPI dependency retrieves each
value per request. The API router contains only HTTP translation and lookup logic:

```text
HTTP request
  -> FastAPI/Pydantic boundary validation
  -> injected KnowledgeSnapshot
  -> RecommendationService for POST only
  -> typed Pydantic response
  -> existing error envelope on failure
```

The default snapshot is empty and safe. Phase six will build and inject a populated
snapshot from JSON without changing any phase-five endpoint signature.

## Project Structure

```text
app/api/contracts.py       HTTP-only request contracts
app/api/dependencies.py    request access to injected app state
app/api/routes.py          the four phase-five path operations
app/knowledge/models.py    validated KnowledgeSnapshot data carrier
app/main.py                application assembly and router inclusion
tests/test_api.py          HTTP contract, OpenAPI, errors, and real CLIPSpy flow
tests/test_knowledge.py    snapshot invariants
scripts/update_backend_plan_pdf.py
tests/test_backend_plan_pdf.py
output/pdf/ai_expert_system_backend_plan_ar.pdf
```

## Code Style

Use explicit return types and FastAPI's `Annotated[..., Depends(...)]` pattern:

```python
@router.get("/stages", response_model=list[Stage])
def list_stages(
    knowledge: Annotated[KnowledgeSnapshot, Depends(get_knowledge)],
) -> list[Stage]:
    return sorted(knowledge.stages, key=lambda stage: stage.id)
```

Handlers remain synchronous because all current collaborators are in-memory and
synchronous. Route functions contain no CLIPS constructs and no filesystem access.

## Testing Strategy

Development follows RED-GREEN-REFACTOR in four increments:

1. Snapshot invariants and safe defaults.
2. Stage/question/tool read endpoints and error responses.
3. Recommendation request validation and a real CLIPSpy end-to-end response.
4. OpenAPI contract, default empty-knowledge behavior, and the updated PDF.

Tests use `TestClient(create_app(...))` with a small in-memory snapshot. The
recommendation success test uses the real `RecommendationService` and CLIPSpy adapter,
not a mock. Each increment runs its focused tests before the complete suite.

Commands:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app tests scripts
.venv\Scripts\python.exe -m pip check
git diff --check
```

## PDF Update

The existing backend-plan updater becomes the single idempotent document builder. It
preserves the five original pages and phase-four appendix, then adds one phase-five
API appendix as page seven. Metadata must contain both `/Phase4Appendix = 1` and
`/Phase5Api = 1`. Rebuilding the output must remain exactly seven pages.

The phase-five page records the implemented routes, dependency-injected snapshot,
typed boundary, actual verification result, and the official FastAPI sources above.
It must not claim that the phase-six JSON loader or production knowledge base exists.

## Boundaries

### Always

- Keep public response schemas explicit and strict.
- Preserve deterministic collection ordering.
- Use the existing error envelope for every failure.
- Test route behavior before implementation and run the real recommendation stack.
- Keep framework decisions traceable to official FastAPI documentation.

### Ask First

- Add or upgrade dependencies.
- Change any existing domain model field or error-envelope field.
- Pull JSON loading or production knowledge content into phase five.
- Add authentication, persistence, API versioning, or pagination.

### Never

- Hard-code sample knowledge into the production application.
- Duplicate CLIPS, ranking, or explanation logic in an HTTP handler.
- Expose internal exception details.
- Claim benchmark normalization or benchmark tie-breaking.
- Delete or replace the five original PDF pages.

## Success Criteria

- All four phase-five endpoints exist under `/api` and appear in OpenAPI.
- Request and response bodies use the documented Pydantic schemas.
- Read endpoints are deterministic and return documented 404/422 behavior.
- The default application is safe with no knowledge loaded.
- Injected knowledge produces three real deterministic recommendations through CLIPS.
- Existing health, CORS, error, domain, engine, and recommendation tests still pass.
- The PDF has seven clean pages and both phase metadata markers.
- The code graph indexes every new Python symbol with no skipped or partial files.

## Open Questions

None. Authentication, pagination, the JSON loader, and production knowledge content
are explicitly deferred to later phases.
