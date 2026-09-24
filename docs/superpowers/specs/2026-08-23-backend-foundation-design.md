# Backend Foundation Design

## Goal

Establish the first runnable backend increment for the AI-tool selection expert system: a FastAPI service that exposes a health check and a stable error contract.

## Scope

This document implements phase 1 of the approved backend plan only. It does not load the knowledge base, run CLIPS rules, score tools, or expose recommendation endpoints.

## Architecture

`app.main` owns application creation and cross-cutting middleware. `app.api.health` owns the health route. `app.api.errors` owns the public error response model and exception handlers. The future domain, knowledge, and expert-engine folders are created now to make the planned boundaries explicit, but contain no behavior in this phase.

The service is served by Uvicorn and mounted under the `/api` prefix. The browser boundary is protected with CORS: configured origins may make cross-origin requests and local development is permitted by default.

## HTTP Contract

### `GET /api/health`

Returns HTTP 200 with the exact JSON body:

```json
{"status":"ok"}
```

### Errors

All handled HTTP errors and request-validation errors use the following envelope:

```json
{
  "error": {
    "code": "HTTP_ERROR",
    "message": "Human-readable explanation",
    "details": null
  }
}
```

Validation errors use `VALIDATION_ERROR` and include FastAPI validation details. Unexpected exceptions use `INTERNAL_ERROR`, return HTTP 500, and do not expose internal exception text.

## Configuration

`FRONTEND_ORIGINS` is an optional comma-separated list of allowed origins. When absent, the development origin `http://localhost:3000` is permitted. Credentials are not allowed, so wildcard origins are never required.

## Tooling

- Python 3.12
- FastAPI and Uvicorn
- Pydantic
- CLIPSpy (installed for the later expert-engine phase but unused here)
- pytest and HTTPX for API tests

## Acceptance Criteria

1. The package structure contains `api`, `domain`, `knowledge`, `expert_engine`, and `tests` boundaries.
2. The health endpoint returns the documented 200 response.
3. An unknown API route returns the documented error envelope.
4. Request-validation errors are registered to use the documented validation error envelope; the first input-taking route in phase 5 will exercise this contract end to end.
5. CORS permits the configured development frontend origin.
6. Tests exercise the API through FastAPI's `TestClient`.
