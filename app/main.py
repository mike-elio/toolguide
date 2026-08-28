import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import (
    http_exception_handler,
    internal_exception_handler,
    validation_exception_handler,
)
from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.knowledge import KnowledgeSnapshot, default_knowledge_path, load_knowledge
from app.questionnaire import QuestionnaireService
from app.recommendations import RecommendationService
from app.text_intent import (
    AnswerResolutionService,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    OllamaTextIntentClassifier,
)


@lru_cache(maxsize=1)
def build_default_answer_resolution_service() -> AnswerResolutionService:
    classifier = OllamaTextIntentClassifier(
        model=os.getenv("OLLAMA_MODEL", "gemma3:1b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        timeout=float(
            os.getenv(
                "OLLAMA_TIMEOUT_SECONDS",
                str(DEFAULT_OLLAMA_TIMEOUT_SECONDS),
            )
        ),
    )
    return AnswerResolutionService(classifier)


def frontend_origins() -> list[str]:
    configured_origins = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


def create_app(
    *,
    knowledge: KnowledgeSnapshot | None = None,
    recommendation_service: RecommendationService | None = None,
    answer_resolution_service: AnswerResolutionService | None = None,
    questionnaire_service: QuestionnaireService | None = None,
) -> FastAPI:
    app = FastAPI(title="AI Expert System Backend")
    app.state.knowledge = (
        knowledge
        if knowledge is not None
        else load_knowledge(default_knowledge_path())
    )
    app.state.recommendation_service = (
        recommendation_service
        if recommendation_service is not None
        else RecommendationService()
    )
    app.state.answer_resolution_service = (
        answer_resolution_service
        if answer_resolution_service is not None
        else build_default_answer_resolution_service()
    )
    app.state.questionnaire_service = questionnaire_service or QuestionnaireService()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, internal_exception_handler)
    app.include_router(health_router, prefix="/api")
    app.include_router(api_router, prefix="/api")
    frontend_directory = Path(__file__).resolve().parents[1] / "frontend"
    if frontend_directory.is_dir():
        @app.get("/", include_in_schema=False)
        def serve_frontend() -> FileResponse:
            return FileResponse(frontend_directory / "index.html")

        app.mount(
            "/frontend",
            StaticFiles(directory=frontend_directory),
            name="frontend",
        )
    return app


app = create_app()
