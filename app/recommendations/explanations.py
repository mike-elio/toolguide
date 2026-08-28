from collections.abc import Sequence

from app.domain.models import Language, Question, Rule, RuleImpact
from app.recommendations.errors import RecommendationConsistencyError
from app.recommendations.ranking import RankedTool


MAX_REASON_LENGTH = 2_000
NO_EFFECT_REASONS = {
    Language.ARABIC: (
        "لم تغيّر أي قاعدة مطابقة درجة هذه الأداة؛ جرى ترتيبها حسب الدرجة ثم "
        "معرّف الأداة عند التعادل."
    ),
    Language.ENGLISH: (
        "No matching rule changed this tool's score; it ranked by score and the "
        "deterministic tool-ID tie-break."
    ),
}


def _bound_reason(reason: str) -> str:
    if len(reason) <= MAX_REASON_LENGTH:
        return reason
    return reason[: MAX_REASON_LENGTH - 1].rstrip() + "…"


def _impact_index(
    rules: Sequence[Rule],
) -> dict[tuple[str, str], tuple[Rule, RuleImpact]]:
    impacts: dict[tuple[str, str], tuple[Rule, RuleImpact]] = {}
    for rule in rules:
        for impact in rule.impacts:
            key = (rule.id, impact.tool_id)
            if key in impacts:
                raise RecommendationConsistencyError(
                    f"duplicate rule impact mapping: {rule.id}/{impact.tool_id}"
                )
            impacts[key] = (rule, impact)
    return impacts


def _readable_rationale(
    *,
    rationale: str,
    rule: Rule,
    questions: dict[str, Question],
    ranked_tool: RankedTool,
    language: Language,
) -> str:
    generated = (
        rationale.startswith("Official sources support ")
        if language is Language.ENGLISH
        else rationale.startswith("تدعم المصادر الرسمية استخدام ")
    )
    if not generated:
        return rationale

    question = questions.get(rule.question_id)
    if question is None:
        return rationale
    answers = [*question.options, *question.text_intents]
    answer = next(
        (item for item in answers if item.id == rule.answer_option_id),
        None,
    )
    if answer is None:
        return rationale

    tool_name = ranked_tool.tool.name.for_language(language)
    answer_label = answer.label.for_language(language)
    prompt = question.prompt.for_language(language)
    if language is Language.ARABIC:
        return (
            f"تلائم أداة {tool_name} إجابتك «{answer_label}» عن «{prompt}»؛ "
            "وتدعم المصادر الرسمية في قاعدة المعرفة هذا التطابق."
        )
    return (
        f'{tool_name} fits your answer "{answer_label}" to "{prompt}"; '
        "official sources in the knowledge base support this match."
    )


def build_reason(
    *,
    ranked_tool: RankedTool,
    rules: Sequence[Rule],
    language: Language,
    questions: Sequence[Question] = (),
) -> str:
    if not ranked_tool.effects:
        return NO_EFFECT_REASONS[language]

    impacts = _impact_index(rules)
    questions_by_id = {question.id: question for question in questions}
    contributions: list[tuple[float, str, str]] = []
    for effect in ranked_tool.effects:
        if effect.tool_id != ranked_tool.tool.id:
            raise RecommendationConsistencyError(
                f"missing rule impact for {effect.rule_id}/{effect.tool_id}"
            )
        rule_impact = impacts.get((effect.rule_id, effect.tool_id))
        if rule_impact is None:
            raise RecommendationConsistencyError(
                f"missing rule impact for {effect.rule_id}/{effect.tool_id}"
            )
        rule, impact = rule_impact
        rationale = _readable_rationale(
            rationale=impact.rationale.for_language(language),
            rule=rule,
            questions=questions_by_id,
            ranked_tool=ranked_tool,
            language=language,
        )
        contributions.append(
            (effect.value, effect.rule_id, rationale)
        )

    positives = sorted(
        (item for item in contributions if item[0] > 0.0),
        key=lambda item: (-item[0], item[1]),
    )
    negatives = sorted(
        (item for item in contributions if item[0] < 0.0),
        key=lambda item: (item[0], item[1]),
    )

    primary = positives[0][2] if positives else None
    strongest_negative = negatives[0][2] if negatives else None
    counter = None if strongest_negative == primary else strongest_negative
    if primary is not None and counter is not None:
        separator = (
            " عامل معاكس: "
            if language is Language.ARABIC
            else " Countervailing factor: "
        )
        return _bound_reason(f"{primary}{separator}{counter}")
    if primary is not None:
        return _bound_reason(primary)
    if counter is not None:
        prefix = (
            "جاء ترتيبها نسبيًا رغم وجود عامل سلبي مطابق: "
            if language is Language.ARABIC
            else "Ranked comparatively despite a negative matched factor: "
        )
        return _bound_reason(f"{prefix}{counter}")
    return NO_EFFECT_REASONS[language]
