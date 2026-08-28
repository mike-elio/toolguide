"""Typed dependencies backed by application state."""

from typing import Annotated, cast

from fastapi import Depends, Request

from app.knowledge import KnowledgeSnapshot
from app.questionnaire import QuestionnaireService
from app.recommendations import RecommendationService
from app.text_intent import AnswerResolutionService


def get_knowledge(request: Request) -> KnowledgeSnapshot:
    return cast(KnowledgeSnapshot, request.app.state.knowledge)


def get_recommendation_service(request: Request) -> RecommendationService:
    return cast(RecommendationService, request.app.state.recommendation_service)


def get_answer_resolution_service(request: Request) -> AnswerResolutionService:
    return cast(AnswerResolutionService, request.app.state.answer_resolution_service)


def get_questionnaire_service(request: Request) -> QuestionnaireService:
    return cast(QuestionnaireService, request.app.state.questionnaire_service)


KnowledgeDependency = Annotated[KnowledgeSnapshot, Depends(get_knowledge)]
RecommendationServiceDependency = Annotated[
    RecommendationService, Depends(get_recommendation_service)
]
AnswerResolutionServiceDependency = Annotated[
    AnswerResolutionService, Depends(get_answer_resolution_service)
]
QuestionnaireServiceDependency = Annotated[
    QuestionnaireService, Depends(get_questionnaire_service)
]
