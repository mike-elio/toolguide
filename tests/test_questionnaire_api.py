from fastapi.testclient import TestClient

from app.main import create_app
from app.text_intent import AnswerResolutionService


def request_payload(**overrides):
    payload = {
        "language": "en",
        "stage": "analysis",
        "domain": "software",
        "session_seed": "api-test",
        "asked_question_ids": [],
        "answers": [],
    }
    payload.update(overrides)
    return payload


def answer_payload(question):
    if question["type"] == "short_text":
        aliases = {
            "task_language": "Discover the landscape",
            "design_intent": "Explore visual directions",
            "implementation_intent": "Assist a developer",
            "testing_intent": "Prevent regressions",
        }
        dimension = question["id"].rsplit("-", 1)[-1]
        return {"question_id": question["id"], "text": aliases[dimension]}
    return {
        "question_id": question["id"],
        "option_ids": [question["options"][0]["id"]],
    }


def test_domains_are_localized_and_stably_ordered() -> None:
    response = TestClient(create_app()).get("/api/domains?language=ar")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "software",
        "artificial_intelligence",
        "cybersecurity",
    ]
    assert response.json()[0]["name"] == "البرمجيات"


def test_advance_starts_with_one_localized_pool_question() -> None:
    response = TestClient(create_app()).post(
        "/api/questionnaire/advance",
        json=request_payload(language="ar"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "question"
    assert body["answered_count"] == 0
    assert body["minimum_questions"] == 6
    assert body["maximum_questions"] == 10
    assert body["question"]["stage"] == "analysis"
    assert body["question"]["domain"] == "software"
    assert isinstance(body["question"]["prompt"], str)


def test_advance_completes_with_three_explainable_recommendations() -> None:
    client = TestClient(create_app())
    asked = []
    answers = []

    for _ in range(10):
        response = client.post(
            "/api/questionnaire/advance",
            json=request_payload(
                session_seed="complete-api",
                asked_question_ids=asked,
                answers=answers,
            ),
        )
        assert response.status_code == 200
        body = response.json()
        if body["status"] == "complete":
            break
        assert body["status"] == "question"
        question = body["question"]
        asked.append(question["id"])
        answers.append(answer_payload(question))
    else:
        raise AssertionError("questionnaire did not complete within ten answers")

    assert 6 <= body["answered_count"] <= 10
    assert len(body["recommendations"]) == 3
    assert len({item["tool_id"] for item in body["recommendations"]}) == 3
    assert all(item["reasons"] for item in body["recommendations"])
    assert all(item["limitations"] for item in body["recommendations"])
    assert all(item["source_url"].startswith("https://") for item in body["recommendations"])


def test_uncertain_short_text_returns_fixed_clarification_choices() -> None:
    question_id = "analysis-software-task_language"
    response = TestClient(
        create_app(answer_resolution_service=AnswerResolutionService())
    ).post(
        "/api/questionnaire/advance",
        json=request_payload(
            asked_question_ids=[question_id],
            answers=[
                {"question_id": question_id, "text": "unmapped private request"}
            ],
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification"
    assert body["question"]["id"] == question_id
    assert [item["id"] for item in body["clarification_options"]] == [
        "discover",
        "validate",
        "monitor",
    ]
    assert "unmapped private request" not in response.text


def test_cross_pool_history_returns_a_safe_validation_error() -> None:
    response = TestClient(create_app()).post(
        "/api/questionnaire/advance",
        json=request_payload(
            asked_question_ids=["testing-cybersecurity-target"],
            answers=[
                {
                    "question_id": "testing-cybersecurity-target",
                    "option_ids": ["code"],
                }
            ],
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "QUESTIONNAIRE_HISTORY_ERROR"
