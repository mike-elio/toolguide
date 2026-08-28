from datetime import date

import app.main as main_module
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.api.contracts import RecommendationRequest, SubmittedAnswer
from app.domain.models import (
    AnswerOption,
    EvaluationSource,
    Question,
    QuestionType,
    Rule,
    RuleImpact,
    SourceKind,
    Stage,
    StageId,
    Tool,
    Language,
    LocalizedText,
)
from app.expert_engine import AnswerSelection
from app.knowledge import KnowledgeSnapshot, default_knowledge_path, load_knowledge
from app.main import create_app
from app.recommendations import RecommendationService
from app.text_intent import AnswerResolutionService, IntentPrediction


def localized(en: str, ar: str | None = None) -> LocalizedText:
    return LocalizedText(ar=ar or en, en=en)


@pytest.mark.parametrize(
    "payload",
    [
        {"question_id": "q"},
        {"question_id": "q", "option_ids": ["yes"], "text": "yes"},
    ],
)
def test_submitted_answer_requires_exactly_one_representation(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        SubmittedAnswer.model_validate(payload)


def test_submitted_answer_trims_and_bounds_short_text() -> None:
    answer = SubmittedAnswer(question_id="q", text="  concise answer  ")

    assert answer.text == "concise answer"
    with pytest.raises(ValidationError):
        SubmittedAnswer(question_id="q", text="x" * 501)


def test_submitted_answer_rejects_duplicate_option_ids() -> None:
    with pytest.raises(ValidationError, match="option ids must be unique"):
        SubmittedAnswer(question_id="q", option_ids=["yes", "yes"])


def test_recommendation_request_requires_explicit_language() -> None:
    with pytest.raises(ValidationError):
        RecommendationRequest(
            answers=[SubmittedAnswer(question_id="q", option_ids=["yes"])]
        )

    request = RecommendationRequest(
        language=Language.ARABIC,
        answers=[SubmittedAnswer(question_id="q", option_ids=["yes"])],
    )
    assert request.language is Language.ARABIC


def read_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        stages=[
            Stage(id=StageId.DESIGN, name=localized("Design", "التصميم")),
            Stage(id=StageId.ANALYSIS, name=localized("Analysis", "التحليل")),
        ],
        tools=[
            Tool(
                id="tool-b",
                name=localized("Tool B", "الأداة ب"),
                description=localized("Second tool.", "الأداة الثانية."),
                stages=[StageId.DESIGN],
            ),
            Tool(
                id="tool-a",
                name=localized("Tool A", "الأداة أ"),
                description=localized("First tool.", "الأداة الأولى."),
                stages=[StageId.ANALYSIS],
            ),
        ],
        questions=[
            Question(
                id="analysis-q2",
                stage=StageId.ANALYSIS,
                prompt=localized("Second question?", "السؤال الثاني؟"),
                type=QuestionType.BOOLEAN,
                importance=0.5,
                options=[
                    AnswerOption(id="yes", label=localized("Yes", "نعم"), value=1.0),
                    AnswerOption(id="no", label=localized("No", "لا"), value=-1.0),
                ],
            ),
            Question(
                id="analysis-q1",
                stage=StageId.ANALYSIS,
                prompt=localized("First question?", "السؤال الأول؟"),
                type=QuestionType.BOOLEAN,
                importance=0.7,
                options=[
                    AnswerOption(id="yes", label=localized("Yes", "نعم"), value=1.0),
                    AnswerOption(id="no", label=localized("No", "لا"), value=-1.0),
                ],
            ),
        ],
    )


def recommendation_snapshot() -> KnowledgeSnapshot:
    source = EvaluationSource(
        id="source-api",
        name=localized("Official API evaluation", "تقييم API الرسمي"),
        publisher=localized("Example Foundation", "مؤسسة المثال"),
        kind=SourceKind.OFFICIAL_DOCUMENTATION,
        url="https://example.com/api-evaluation",
        collected_at=date(2026, 8, 24),
    )
    question = Question(
        id="analysis-q1",
        stage=StageId.ANALYSIS,
        prompt=localized("Does this fit the workflow?", "هل يناسب سير العمل؟"),
        type=QuestionType.BOOLEAN,
        importance=1.0,
        options=[
            AnswerOption(id="yes", label=localized("Yes"), value=1.0),
            AnswerOption(id="no", label=localized("No"), value=-1.0),
        ],
    )
    tools = [
        Tool(
            id=tool_id,
            name=localized(
                f"Tool {tool_id[-1].upper()}", f"الأداة {tool_id[-1].upper()}"
            ),
            description=localized(
                f"Candidate {tool_id}.", f"أداة مرشحة {tool_id}."
            ),
            stages=[StageId.ANALYSIS],
        )
        for tool_id in ["tool-d", "tool-c", "tool-b", "tool-a"]
    ]
    rationales = {
        "tool-a": (1.0, "Best documented workflow fit."),
        "tool-b": (0.75, "Strong documented workflow fit."),
        "tool-c": (0.5, "Moderate documented workflow fit."),
    }
    rules = [
        Rule(
            id=f"rule-{tool_id[-1]}",
            question_id=question.id,
            answer_option_id="yes",
            impacts=[
                RuleImpact(
                    tool_id=tool_id,
                    weight=weight,
                    rationale=localized(rationale, f"سبب موثق لـ {tool_id}."),
                    sources=[source],
                )
            ],
        )
        for tool_id, (weight, rationale) in rationales.items()
    ]
    return KnowledgeSnapshot(
        stages=[Stage(id=StageId.ANALYSIS, name=localized("Analysis"))],
        tools=tools,
        questions=[question],
        rules=rules,
    )


def test_explicit_empty_knowledge_exposes_an_empty_stage_list() -> None:
    response = TestClient(create_app(knowledge=KnowledgeSnapshot())).get(
        "/api/stages?language=en"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_default_app_loads_the_phase_six_knowledge_snapshot() -> None:
    client = TestClient(create_app())

    stages = client.get("/api/stages?language=en")
    questions = client.get("/api/stages/analysis/questions?language=en")

    assert stages.status_code == 200
    assert [stage["id"] for stage in stages.json()] == [
        "analysis",
        "design",
        "implementation",
        "testing",
    ]
    assert questions.status_code == 200
    assert len(questions.json()) == 42


def test_create_app_uses_the_default_runtime_answer_resolver(monkeypatch) -> None:
    resolver = AnswerResolutionService()
    monkeypatch.setattr(
        main_module,
        "build_default_answer_resolution_service",
        lambda: resolver,
    )

    application = main_module.create_app(knowledge=KnowledgeSnapshot())

    assert application.state.answer_resolution_service is resolver


def test_default_answer_resolver_uses_the_configured_ollama_classifier(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FixedOllamaClassifier:
        def __init__(self, *, model: str, base_url: str, timeout: float) -> None:
            captured.update(model=model, base_url=base_url, timeout=timeout)

        def predict(self, language, question, text) -> IntentPrediction:
            return IntentPrediction(
                question_id=question.id,
                intent_id="prototype",
                confidence=1.0,
                margin=1.0,
                source="model",
            )

    monkeypatch.setenv("OLLAMA_MODEL", "gemma3:1b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "12")
    monkeypatch.setattr(
        main_module,
        "OllamaTextIntentClassifier",
        FixedOllamaClassifier,
        raising=False,
    )
    main_module.build_default_answer_resolution_service.cache_clear()
    knowledge = load_knowledge(default_knowledge_path())
    question = next(
        item
        for item in knowledge.questions
        if item.id == "design-software-design_intent"
    )

    resolver = main_module.build_default_answer_resolution_service()
    resolved = resolver.resolve(
        Language.ENGLISH,
        [
            SubmittedAnswer(
                question_id="design-software-design_intent",
                text="an unseen design need",
            )
        ],
        [question],
    )

    assert resolved == [
        AnswerSelection(
            question_id="design-software-design_intent",
            option_ids=["prototype"],
        )
    ]
    assert captured == {
        "model": "gemma3:1b",
        "base_url": "http://127.0.0.1:11434",
        "timeout": 12.0,
    }
    main_module.build_default_answer_resolution_service.cache_clear()


def test_default_answer_resolver_allows_a_cold_ollama_start(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FixedOllamaClassifier:
        def __init__(self, *, model: str, base_url: str, timeout: float) -> None:
            captured.update(model=model, base_url=base_url, timeout=timeout)

    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr(
        main_module,
        "OllamaTextIntentClassifier",
        FixedOllamaClassifier,
    )
    main_module.build_default_answer_resolution_service.cache_clear()

    main_module.build_default_answer_resolution_service()

    assert captured["timeout"] == 60.0
    main_module.build_default_answer_resolution_service.cache_clear()


def test_stages_are_returned_in_deterministic_id_order() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/stages?language=en"
    )

    assert response.status_code == 200
    assert [stage["id"] for stage in response.json()] == ["analysis", "design"]


def test_questions_for_stage_are_returned_in_deterministic_id_order() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/stages/analysis/questions?language=en"
    )

    assert response.status_code == 200
    assert [question["id"] for question in response.json()] == [
        "analysis-q1",
        "analysis-q2",
    ]


def test_valid_but_unavailable_stage_returns_404_envelope() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/stages/testing/questions?language=en"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_invalid_stage_returns_validation_envelope() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/stages/unknown/questions?language=en"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_tool_endpoint_returns_the_requested_tool() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/tools/tool-a?language=en"
    )

    assert response.status_code == 200
    assert response.json()["id"] == "tool-a"


def test_missing_tool_returns_404_envelope() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(
        "/api/tools/missing-tool?language=en"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"


@pytest.mark.parametrize(
    "path",
    [
        "/api/stages",
        "/api/stages/analysis/questions",
        "/api/tools/tool-a",
    ],
)
def test_localized_read_routes_require_explicit_language(path: str) -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).get(path)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_localized_reads_return_only_the_selected_language() -> None:
    client = TestClient(create_app(knowledge=read_snapshot()))

    arabic_stage = client.get("/api/stages?language=ar").json()[0]
    english_question = client.get(
        "/api/stages/analysis/questions?language=en"
    ).json()[0]
    arabic_tool = client.get("/api/tools/tool-a?language=ar").json()

    assert arabic_stage["name"] == "التحليل"
    assert "ar" not in arabic_stage and "en" not in arabic_stage
    assert english_question["prompt"] == "First question?"
    assert english_question["options"][0]["label"] == "Yes"
    assert "text_intents" not in english_question
    assert arabic_tool["name"] == "الأداة أ"
    assert arabic_tool["description"] == "الأداة الأولى."


def test_recommendation_request_requires_at_least_one_answer() -> None:
    response = TestClient(create_app(knowledge=recommendation_snapshot())).post(
        "/api/recommendations", json={"language": "en", "answers": []}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_recommendation_request_rejects_duplicate_question_answers() -> None:
    answer = {"question_id": "analysis-q1", "option_ids": ["yes"]}
    response = TestClient(create_app(knowledge=recommendation_snapshot())).post(
        "/api/recommendations",
        json={"language": "en", "answers": [answer, answer]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_recommendations_use_the_real_clipspy_service() -> None:
    response = TestClient(create_app(knowledge=recommendation_snapshot())).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {"question_id": "analysis-q1", "option_ids": ["yes"]}
            ]
        },
    )

    assert response.status_code == 200
    assert [item["tool_id"] for item in response.json()["recommendations"]] == [
        "tool-a",
        "tool-b",
        "tool-c",
    ]
    assert response.json()["recommendations"][0]["reason"] == (
        "Best documented workflow fit."
    )


def test_recommendations_return_only_the_requested_language() -> None:
    response = TestClient(create_app(knowledge=recommendation_snapshot())).post(
        "/api/recommendations",
        json={
            "language": "ar",
            "answers": [
                {"question_id": "analysis-q1", "option_ids": ["yes"]}
            ],
        },
    )

    assert response.status_code == 200
    first = response.json()["recommendations"][0]
    assert first["tool_name"] == "الأداة A"
    assert first["reason"] == "سبب موثق لـ tool-a."
    assert "ar" not in first and "en" not in first


def test_short_text_alias_reaches_the_real_recommendation_path() -> None:
    response = TestClient(create_app()).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {
                    "question_id": "analysis-software-task_language",
                    "text": "Discover the landscape",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 3


def test_unseen_short_text_returns_safe_model_unavailable_without_echoing_text() -> None:
    raw_text = "an unseen private request"
    response = TestClient(
        create_app(answer_resolution_service=AnswerResolutionService())
    ).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {
                    "question_id": "analysis-software-task_language",
                    "text": raw_text,
                }
            ],
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert raw_text not in response.text


def test_wrong_question_representation_returns_a_stable_safe_error() -> None:
    raw_text = "private choice answer"
    response = TestClient(create_app()).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {"question_id": "analysis-software-outcome", "text": raw_text}
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ANSWER_REPRESENTATION"
    assert raw_text not in response.text


def test_recommendations_require_at_least_three_tools() -> None:
    response = TestClient(create_app(knowledge=read_snapshot())).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {"question_id": "analysis-q1", "option_ids": ["yes"]}
            ]
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_invalid_answer_reference_returns_422() -> None:
    response = TestClient(create_app(knowledge=recommendation_snapshot())).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {"question_id": "missing-question", "option_ids": ["yes"]}
            ]
        },
    )

    assert response.status_code == 422
    assert "missing-question" in response.json()["error"]["message"]


def test_unexpected_recommendation_failure_stays_private() -> None:
    class ExplodingRecommendationService(RecommendationService):
        def recommend(self, **kwargs: object) -> object:
            raise RuntimeError("private service details")

    response = TestClient(
        create_app(
            knowledge=recommendation_snapshot(),
            recommendation_service=ExplodingRecommendationService(),
        ),
        raise_server_exceptions=False,
    ).post(
        "/api/recommendations",
        json={
            "language": "en",
            "answers": [
                {"question_id": "analysis-q1", "option_ids": ["yes"]}
            ]
        },
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private service details" not in response.text


def test_openapi_documents_localized_routes_and_contracts() -> None:
    schema = create_app().openapi()

    assert {
        "/api/stages",
        "/api/stages/{stage}/questions",
        "/api/tools/{tool_id}",
        "/api/recommendations",
    }.issubset(schema["paths"])

    recommendation_operation = schema["paths"]["/api/recommendations"]["post"]
    request_schema = recommendation_operation["requestBody"]["content"][
        "application/json"
    ]["schema"]
    response_schema = recommendation_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert request_schema["$ref"].endswith("/RecommendationRequest")
    assert response_schema["$ref"].endswith("/RecommendationResponse")
    request_contract = schema["components"]["schemas"]["RecommendationRequest"]
    assert "language" in request_contract["required"]

    for path in [
        "/api/stages",
        "/api/stages/{stage}/questions",
        "/api/tools/{tool_id}",
    ]:
        language_parameter = next(
            parameter
            for parameter in schema["paths"][path]["get"]["parameters"]
            if parameter["name"] == "language"
        )
        assert language_parameter["required"] is True
