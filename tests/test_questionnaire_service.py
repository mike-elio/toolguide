from app.api.contracts import SubmittedAnswer
from app.domain.models import DomainId, Language, QuestionType, StageId
from app.knowledge import default_knowledge_path, load_knowledge
from app.questionnaire import QuestionnaireService, QuestionnaireStatus
from app.text_intent import AnswerResolutionService


def answer_for(question):
    if question.type is QuestionType.SHORT_TEXT:
        intent = question.text_intents[0]
        return SubmittedAnswer(
            question_id=question.id,
            text=intent.aliases[Language.ENGLISH][0],
        )
    return SubmittedAnswer(
        question_id=question.id,
        option_ids=[question.options[0].id],
    )


def advance(service, *, asked, answers, seed="service-test"):
    return service.advance(
        knowledge=load_knowledge(default_knowledge_path()),
        resolver=AnswerResolutionService(),
        language=Language.ENGLISH,
        stage=StageId.ANALYSIS,
        domain=DomainId.SOFTWARE,
        session_seed=seed,
        asked_question_ids=asked,
        submitted_answers=answers,
    )


def test_service_starts_with_one_pool_owned_question() -> None:
    outcome = advance(QuestionnaireService(), asked=[], answers=[])

    assert outcome.status is QuestionnaireStatus.QUESTION
    assert outcome.question is not None
    assert outcome.question.stage is StageId.ANALYSIS
    assert outcome.question.domain is DomainId.SOFTWARE
    assert outcome.answered_count == 0


def test_service_never_completes_before_six_or_continues_after_ten() -> None:
    service = QuestionnaireService()
    asked = []
    answers = []
    outcome = advance(service, asked=asked, answers=answers)

    while outcome.status is QuestionnaireStatus.QUESTION:
        assert outcome.question is not None
        asked.append(outcome.question.id)
        answers.append(answer_for(outcome.question))
        outcome = advance(service, asked=asked, answers=answers)
        if len(answers) < 6:
            assert outcome.status is QuestionnaireStatus.QUESTION
        if len(answers) == 10:
            break

    assert outcome.status is QuestionnaireStatus.COMPLETE
    assert 6 <= outcome.answered_count <= 10
    assert len(set(asked)) == len(asked)


def test_completed_service_result_is_explainable_and_pool_scoped() -> None:
    service = QuestionnaireService()
    asked = []
    answers = []
    outcome = advance(service, asked=asked, answers=answers, seed="explain")
    while outcome.status is QuestionnaireStatus.QUESTION:
        asked.append(outcome.question.id)
        answers.append(answer_for(outcome.question))
        outcome = advance(service, asked=asked, answers=answers, seed="explain")

    assert len(outcome.recommendations) == 3
    assert len({item.tool_id for item in outcome.recommendations}) == 3
    assert all(0 <= item.match_percent <= 100 for item in outcome.recommendations)
    assert all(item.reasons for item in outcome.recommendations)
    assert all(item.limitations for item in outcome.recommendations)
    assert all(str(item.source_url).startswith("https://") for item in outcome.recommendations)
    assert [item.match_percent for item in outcome.recommendations] == sorted(
        (item.match_percent for item in outcome.recommendations), reverse=True
    )


def test_unresolved_short_text_returns_fixed_clarification_choices() -> None:
    snapshot = load_knowledge(default_knowledge_path())
    question = next(
        item
        for item in snapshot.questions
        if item.stage is StageId.ANALYSIS
        and item.domain is DomainId.SOFTWARE
        and item.type is QuestionType.SHORT_TEXT
    )

    outcome = QuestionnaireService().advance(
        knowledge=snapshot,
        resolver=AnswerResolutionService(),
        language=Language.ENGLISH,
        stage=StageId.ANALYSIS,
        domain=DomainId.SOFTWARE,
        session_seed="clarify",
        asked_question_ids=[question.id],
        submitted_answers=[
            SubmittedAnswer(question_id=question.id, text="unmapped private need")
        ],
    )

    assert outcome.status is QuestionnaireStatus.CLARIFICATION
    assert outcome.question.id == question.id
    assert [option.id for option in outcome.clarification_options] == [
        intent.id for intent in question.text_intents
    ]
