from app.domain.models import DomainId, Language, Question, RecommendationResult, Stage, Tool
from app.localization.models import (
    AnswerOptionResponse,
    DomainResponse,
    QuestionResponse,
    QuestionnaireRecommendationResponse,
    QuestionnaireResponse,
    RecommendationItemResponse,
    RecommendationResponse,
    StageResponse,
    ToolResponse,
)
from app.questionnaire import QuestionnaireOutcome


def project_stage(stage: Stage, language: Language) -> StageResponse:
    return StageResponse(id=stage.id, name=stage.name.for_language(language))


def project_question(question: Question, language: Language) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        stage=question.stage,
        domain=question.domain,
        prompt=question.prompt.for_language(language),
        type=question.type,
        importance=question.importance,
        options=[
            AnswerOptionResponse(
                id=option.id,
                label=option.label.for_language(language),
                value=option.value,
            )
            for option in question.options
        ],
    )


def project_tool(tool: Tool, language: Language) -> ToolResponse:
    return ToolResponse(
        id=tool.id,
        name=tool.name.for_language(language),
        description=tool.description.for_language(language),
        stages=tool.stages,
    )


def project_result(
    result: RecommendationResult, language: Language
) -> RecommendationResponse:
    return RecommendationResponse(
        recommendations=[
            RecommendationItemResponse(
                tool_id=item.tool_id,
                tool_name=item.tool_name,
                reason=item.reason,
            )
            for item in result.recommendations
        ]
    )


DOMAIN_NAMES = {
    DomainId.SOFTWARE: {Language.ARABIC: "البرمجيات", Language.ENGLISH: "Software"},
    DomainId.ARTIFICIAL_INTELLIGENCE: {
        Language.ARABIC: "الذكاء الاصطناعي",
        Language.ENGLISH: "Artificial intelligence",
    },
    DomainId.CYBERSECURITY: {
        Language.ARABIC: "الأمن السيبراني",
        Language.ENGLISH: "Cybersecurity",
    },
}


def project_domain(domain: DomainId, language: Language) -> DomainResponse:
    return DomainResponse(id=domain, name=DOMAIN_NAMES[domain][language])


def project_questionnaire_outcome(
    outcome: QuestionnaireOutcome, language: Language
) -> QuestionnaireResponse:
    return QuestionnaireResponse(
        status=outcome.status,
        answered_count=outcome.answered_count,
        question=(
            project_question(outcome.question, language)
            if outcome.question is not None
            else None
        ),
        clarification_options=[
            AnswerOptionResponse(
                id=option.id,
                label=option.label.for_language(language),
                value=option.value,
            )
            for option in outcome.clarification_options
        ],
        recommendations=[
            QuestionnaireRecommendationResponse(
                tool_id=item.tool_id,
                tool_name=item.tool_name,
                match_percent=item.match_percent,
                confidence=item.confidence,
                reasons=item.reasons,
                limitations=item.limitations,
                source_url=item.source_url,
            )
            for item in outcome.recommendations
        ],
    )
