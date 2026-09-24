# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the first runnable FastAPI backend increment with a health check, stable error envelope, CORS, and API tests.

**Architecture:** `app.main` creates the application and owns middleware and exception registration. The health router is separate from error handling so later API routers can use the same response contract. Empty domain, knowledge, and expert-engine packages establish the planned project boundaries without implementing later phases.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic, CLIPSpy, pytest, HTTPX.

**Spec:** `docs/superpowers/specs/2026-08-23-backend-foundation-design.md`

## Global Constraints

- Implement phase 1 only; do not add knowledge loading, inference, scoring, or recommendation endpoints.
- Serve all public routes beneath `/api`.
- Health success body is exactly `{"status":"ok"}`.
- Handled errors use the documented `error.code`, `error.message`, and `error.details` envelope.
- Default allowed frontend origin is `http://localhost:3000`; `FRONTEND_ORIGINS` overrides it with comma-separated origins.
- Use Python 3.12 and the dependencies specified in the design.

---

### Task 1: Scaffold the package and prove the health contract

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/api/__init__.py`
- Create: `app/api/health.py`
- Create: `app/main.py`
- Create: `app/domain/__init__.py`
- Create: `app/knowledge/__init__.py`
- Create: `app/expert_engine/__init__.py`
- Create: `tests/test_health.py`

**Interfaces:**
- Produces: `app.main.create_app() -> fastapi.FastAPI`
- Produces: `GET /api/health -> {"status": "ok"}`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_endpoint_returns_ok_status() -> None:
    response = TestClient(create_app()).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_health.py::test_health_endpoint_returns_ok_status -v`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# app/api/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# app/main.py
from fastapi import FastAPI
from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router, prefix="/api")
    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_health.py::test_health_endpoint_returns_ok_status -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app tests/test_health.py
git commit -m "feat: add FastAPI health endpoint"
```

### Task 2: Add CORS and the stable error envelope

**Files:**
- Create: `app/api/errors.py`
- Modify: `app/main.py`
- Modify: `tests/test_health.py`

**Interfaces:**
- Consumes: `app.main.create_app() -> FastAPI`
- Produces: all handled errors as `{"error": {"code": str, "message": str, "details": object | null}}`

- [ ] **Step 1: Write the failing tests**

```python
def test_unknown_api_route_returns_the_error_envelope() -> None:
    response = TestClient(create_app()).get("/api/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "HTTP_ERROR",
            "message": "Not Found",
            "details": None,
        }
    }


def test_cors_allows_the_default_frontend_origin() -> None:
    response = TestClient(create_app()).options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_health.py -v`

Expected: the new tests FAIL because the default FastAPI error body and no CORS middleware are present.

- [ ] **Step 3: Write minimal implementation**

```python
# app/api/errors.py
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": None}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Validation failed", "details": exc.errors()}},
    )
```

Register the handlers in `create_app()` and add `CORSMiddleware` with origins read from `FRONTEND_ORIGINS` or the default origin.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_health.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/errors.py app/main.py tests/test_health.py
git commit -m "feat: standardize API errors and CORS"
```

### Task 3: Verify the application can run

**Files:**
- No source changes.

**Interfaces:**
- Consumes: `app.main:app`
- Produces: a Uvicorn development server at `http://127.0.0.1:8000`.

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -v`

Expected: PASS with all phase-1 tests collected.

- [ ] **Step 2: Start the server and call health**

Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

Expected: `GET http://127.0.0.1:8000/api/health` responds with `{"status":"ok"}`.
