from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok_status() -> None:
    response = TestClient(create_app()).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_cors_uses_configured_frontend_origins(monkeypatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://frontend.example,https://admin.example")

    response = TestClient(create_app()).options(
        "/api/health",
        headers={
            "Origin": "https://admin.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://admin.example"


def test_unexpected_error_does_not_expose_internal_details() -> None:
    app = create_app()

    @app.get("/api/test-error")
    def test_error() -> None:
        raise RuntimeError("sensitive internal detail")

    response = TestClient(app, raise_server_exceptions=False).get("/api/test-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": None,
        }
    }


def test_validation_error_uses_the_error_envelope() -> None:
    app = create_app()

    @app.get("/api/test-validation")
    def test_validation(count: int) -> dict[str, int]:
        return {"count": count}

    response = TestClient(app).get("/api/test-validation?count=not-a-number")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Validation failed"
    assert isinstance(body["error"]["details"], list)
