"""HTTP routes for knowledge-base reads."""

from fastapi import APIRouter, HTTPException, status

from app.api.contracts import QuestionnaireRequest, RecommendationRequest
from app.api.dependencies import (
    AnswerResolutionServiceDependency,
    KnowledgeDependency,
    QuestionnaireServiceDependency,
    RecommendationServiceDependency,
)
from app.api.errors import CodedHTTPException
from app.domain.models import DomainId, Language, StageId
from app.expert_engine import KnowledgeValidationError
from app.localization import (
    QuestionResponse,
    DomainResponse,
    RecommendationResponse,
    QuestionnaireResponse,
    StageResponse,
    ToolResponse,
    project_domain,
    project_question,
    project_questionnaire_outcome,
    project_result,
    project_stage,
    project_tool,
)
from app.recommendations import InsufficientToolsError
from app.questionnaire import QuestionnaireHistoryError
from app.text_intent import (
    InvalidAnswerRepresentationError,
    ModelUnavailableError,
    TextIntentError,
    UncertainTextIntentError,
)

router = APIRouter()


@router.get("/domains", response_model=list[DomainResponse])
def list_domains(language: Language) -> list[DomainResponse]:
    return [project_domain(domain, language) for domain in DomainId]


@router.post("/questionnaire/advance", response_model=QuestionnaireResponse)
def advance_questionnaire(
    request: QuestionnaireRequest,
    knowledge: KnowledgeDependency,
    questionnaire_service: QuestionnaireServiceDependency,
    answer_resolution_service: AnswerResolutionServiceDependency,
) -> QuestionnaireResponse:
    try:
        outcome = questionnaire_service.advance(
            knowledge=knowledge,
            resolver=answer_resolution_service,
            language=request.language,
            stage=request.stage,
            domain=request.domain,
            session_seed=request.session_seed,
            asked_question_ids=request.asked_question_ids,
            submitted_answers=request.answers,
        )
        return project_questionnaire_outcome(outcome, request.language)
    except QuestionnaireHistoryError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="QUESTIONNAIRE_HISTORY_ERROR",
            detail=str(error),
        ) from error
    except InvalidAnswerRepresentationError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_ANSWER_REPRESENTATION",
            detail=str(error),
        ) from error


@router.get("/stages", response_model=list[StageResponse])
def list_stages(
    knowledge: KnowledgeDependency, language: Language
) -> list[StageResponse]:
    return [
        project_stage(stage, language)
        for stage in sorted(knowledge.stages, key=lambda stage: stage.id.value)
    ]


@router.get("/stages/{stage}/questions", response_model=list[QuestionResponse])
def list_stage_questions(
    stage: StageId, knowledge: KnowledgeDependency, language: Language
) -> list[QuestionResponse]:
    if all(candidate.id != stage for candidate in knowledge.stages):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage not found: {stage.value}",
        )
    return [
        project_question(question, language)
        for question in sorted(
            (question for question in knowledge.questions if question.stage == stage),
            key=lambda question: question.id,
        )
    ]


@router.get("/tools/{tool_id}", response_model=ToolResponse)
def get_tool(
    tool_id: str, knowledge: KnowledgeDependency, language: Language
) -> ToolResponse:
    for tool in knowledge.tools:
        if tool.id == tool_id:
            return project_tool(tool, language)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tool not found: {tool_id}",
    )


@router.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(
    request: RecommendationRequest,
    knowledge: KnowledgeDependency,
    recommendation_service: RecommendationServiceDependency,
    answer_resolution_service: AnswerResolutionServiceDependency,
) -> RecommendationResponse:
    try:
        answers = answer_resolution_service.resolve(
            request.language,
            request.answers,
            knowledge.questions,
        )
        return project_result(
            recommendation_service.recommend(
                tools=knowledge.tools,
                questions=knowledge.questions,
                rules=knowledge.rules,
                answers=answers,
                language=request.language,
            ),
            request.language,
        )
    except InvalidAnswerRepresentationError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_ANSWER_REPRESENTATION",
            detail=str(error),
        ) from error
    except UncertainTextIntentError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="UNCERTAIN_TEXT_INTENT",
            detail=str(error),
        ) from error
    except ModelUnavailableError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="MODEL_UNAVAILABLE",
            detail=str(error),
        ) from error
    except TextIntentError as error:
        raise CodedHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="TEXT_INTENT_ERROR",
            detail=str(error),
        ) from error
    except InsufficientToolsError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except KnowledgeValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
