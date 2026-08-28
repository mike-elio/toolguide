from fastapi.testclient import TestClient

from app.main import create_app


def test_frontend_assets_and_recommendation_flow_are_available() -> None:
    client = TestClient(create_app())

    page = client.get("/")
    assert page.status_code == 200
    assert "cdn.tailwindcss.com" not in page.text
    assert "/frontend/questionnaire-state.js" in page.text
    assert "/frontend/app.js" in page.text

    script = client.get("/frontend/app.js")
    assert script.status_code == 200
    assert "const apiBase" in script.text
    assert "fetch(`${apiBase}${path}`" in script.text

    stages = client.get("/api/stages?language=ar")
    assert stages.status_code == 200
    assert [stage["id"] for stage in stages.json()] == [
        "analysis",
        "design",
        "implementation",
        "testing",
    ]

    domains = client.get("/api/domains?language=ar")
    assert domains.status_code == 200
    assert len(domains.json()) == 3

    response = client.post(
        "/api/questionnaire/advance",
        json={
            "language": "ar",
            "stage": "analysis",
            "domain": "software",
            "session_seed": "frontend-integration",
            "asked_question_ids": [],
            "answers": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "question"
    assert response.json()["question"]["domain"] == "software"
