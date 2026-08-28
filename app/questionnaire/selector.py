from __future__ import annotations

import hashlib
import itertools
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence, Set

from app.domain.models import Question, Rule
from app.questionnaire.models import QuestionnaireHistoryError


def _closest_pair(tool_scores: Mapping[str, float]) -> tuple[str, str] | None:
    if len(tool_scores) < 2:
        return None
    return min(
        itertools.combinations(sorted(tool_scores), 2),
        key=lambda pair: (abs(tool_scores[pair[0]] - tool_scores[pair[1]]), pair),
    )


def _question_discrimination(
    question: Question,
    rules: Sequence[Rule],
    tool_scores: Mapping[str, float],
) -> float:
    question_rules = [rule for rule in rules if rule.question_id == question.id]
    if not question_rules:
        return 0.0
    all_equal = len({round(score, 12) for score in tool_scores.values()}) <= 1
    closest = _closest_pair(tool_scores)
    separations: list[float] = []
    for rule in question_rules:
        weights = {impact.tool_id: impact.weight for impact in rule.impacts}
        if all_equal:
            values = list(weights.values())
            if values:
                separations.append(max(values) - min(values))
        elif closest is not None:
            separations.append(
                abs(weights.get(closest[0], 0.0) - weights.get(closest[1], 0.0))
            )
    return question.importance * max(separations, default=0.0)


def _seed_index(seed: str, asked_question_ids: Set[str], size: int) -> int:
    material = f"{seed}|{'|'.join(sorted(asked_question_ids))}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % size


def select_next_question(
    *,
    questions: Sequence[Question],
    rules: Sequence[Rule],
    tool_scores: Mapping[str, float],
    asked_question_ids: Set[str],
    seed: str,
) -> Question:
    questions_by_id = {question.id: question for question in questions}
    unknown = set(asked_question_ids) - set(questions_by_id)
    if unknown:
        raise QuestionnaireHistoryError(
            f"asked questions do not belong to the selected pool: {sorted(unknown)}"
        )
    eligible = [
        question for question in questions if question.id not in asked_question_ids
    ]
    if not eligible:
        raise QuestionnaireHistoryError("selected pool has no unanswered questions")

    dimension_counts = Counter(
        questions_by_id[question_id].dimension for question_id in asked_question_ids
    )
    ranked: list[tuple[float, str, Question]] = []
    for question in eligible:
        discrimination = _question_discrimination(question, rules, tool_scores)
        balance = 1.0 / (1.0 + 0.4 * dimension_counts[question.dimension])
        ranked.append((discrimination * balance, question.id, question))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    top = ranked[: min(3, len(ranked))]
    return top[_seed_index(seed, asked_question_ids, len(top))][2]


__all__ = ["select_next_question"]
