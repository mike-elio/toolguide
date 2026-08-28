from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import DomainId, Language, QuestionType, StageId
from app.knowledge import default_knowledge_path, load_knowledge
from app.main import create_app
from app.text_intent import AnswerResolutionService


@dataclass(frozen=True)
class SimulationReport:
    session_count: int
    completed_sessions: int
    failed_sessions: int
    pool_count: int
    minimum_question_count: int
    maximum_question_count: int
    question_count_distribution: dict[int, int]
    result_tool_coverage: int
    result_tool_coverage_percent: float
    top_recommendation_diversity: dict[str, int]
    session_paths: tuple[tuple[str, ...], ...]
    session_recommendations: tuple[tuple[str, ...], ...]
    failures: tuple[str, ...]
    samples: tuple[str, ...]


def _stable_index(value: str, size: int) -> int:
    return int.from_bytes(
        hashlib.sha256(value.encode("utf-8")).digest()[:8], "big"
    ) % size


def _choose_answer(
    *,
    question_payload: dict[str, object],
    question,
    strategy: int,
    session_seed: str,
    target_tool_id: str,
    rules_by_question: dict[str, list],
    language: Language,
) -> dict[str, object]:
    if question.type is QuestionType.SHORT_TEXT:
        index = strategy % len(question.text_intents)
        intent = question.text_intents[index]
        return {
            "question_id": question.id,
            "text": intent.aliases[language][0],
        }

    options = question_payload.get("options") or []
    if not options:
        raise ValueError(f"choice question has no options: {question.id}")
    if strategy == 0:
        selected = options[0]
    elif strategy == 1:
        selected = options[-1]
    elif strategy == 2:
        selected = options[len(options) // 2]
    elif strategy == 3:
        candidate_rules = rules_by_question[question.id]
        best = max(
            candidate_rules,
            key=lambda rule: next(
                impact.weight
                for impact in rule.impacts
                if impact.tool_id == target_tool_id
            ),
        )
        selected = next(
            option for option in options if option["id"] == best.answer_option_id
        )
    else:
        selected = options[
            _stable_index(f"{session_seed}|{question.id}", len(options))
        ]
    return {"question_id": question.id, "option_ids": [selected["id"]]}


def run_simulation(
    *, session_count: int, seed_prefix: str = "simulation"
) -> SimulationReport:
    if session_count < 1:
        raise ValueError("session_count must be positive")
    snapshot = load_knowledge(default_knowledge_path())
    questions_by_id = {question.id: question for question in snapshot.questions}
    tools_by_id = {tool.id: tool for tool in snapshot.tools}
    rules_by_question: defaultdict[str, list] = defaultdict(list)
    for rule in snapshot.rules:
        rules_by_question[rule.question_id].append(rule)
    pool_tools = {
        (stage, domain): [
            tool
            for tool in snapshot.tools
            if tool.stages == [stage] and tool.domain is domain
        ]
        for stage in StageId
        for domain in DomainId
    }
    pools = list(product(StageId, DomainId))
    client = TestClient(
        create_app(answer_resolution_service=AnswerResolutionService())
    )

    failures: list[str] = []
    completed = 0
    question_counts: list[int] = []
    exercised_pools: set[str] = set()
    result_tools: set[str] = set()
    top_tools: defaultdict[str, set[str]] = defaultdict(set)
    paths: list[tuple[str, ...]] = []
    recommendations: list[tuple[str, ...]] = []
    samples: list[str] = []

    for session_index in range(session_count):
        stage, domain = pools[session_index % len(pools)]
        pool_key = f"{stage.value}/{domain.value}"
        exercised_pools.add(pool_key)
        language = Language.ARABIC if session_index % 2 else Language.ENGLISH
        strategy = session_index % 5
        session_seed = f"{seed_prefix}-{session_index}"
        target_tool = pool_tools[(stage, domain)][
            (session_index // len(pools)) % 4
        ]
        asked: list[str] = []
        answers: list[dict[str, object]] = []
        final_body: dict[str, object] | None = None
        session_failures: list[str] = []

        for _ in range(12):
            response = client.post(
                "/api/questionnaire/advance",
                json={
                    "language": language.value,
                    "stage": stage.value,
                    "domain": domain.value,
                    "session_seed": session_seed,
                    "asked_question_ids": asked,
                    "answers": answers,
                },
            )
            if response.status_code != 200:
                session_failures.append(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                break
            body = response.json()
            if body["status"] == "complete":
                final_body = body
                break
            if body["status"] == "clarification":
                if not answers or not asked:
                    session_failures.append("clarification without answer history")
                    break
                choice = body["clarification_options"][strategy % len(body["clarification_options"])]
                answers[-1] = {
                    "question_id": asked[-1],
                    "option_ids": [choice["id"]],
                }
                continue
            if body["status"] != "question":
                session_failures.append(f"unknown status: {body['status']}")
                break
            question_payload = body["question"]
            question_id = question_payload["id"]
            if question_id in asked:
                session_failures.append(f"duplicate question: {question_id}")
                break
            question = questions_by_id.get(question_id)
            if (
                question is None
                or question.stage is not stage
                or question.domain is not domain
            ):
                session_failures.append(f"cross-pool question: {question_id}")
                break
            asked.append(question_id)
            answers.append(
                _choose_answer(
                    question_payload=question_payload,
                    question=question,
                    strategy=strategy,
                    session_seed=session_seed,
                    target_tool_id=target_tool.id,
                    rules_by_question=rules_by_question,
                    language=language,
                )
            )

        if final_body is None:
            session_failures.append("session did not complete")
        else:
            items = final_body.get("recommendations") or []
            item_ids = [item["tool_id"] for item in items]
            percentages = [item["match_percent"] for item in items]
            if not 6 <= final_body["answered_count"] <= 10:
                session_failures.append(
                    f"question count out of range: {final_body['answered_count']}"
                )
            if final_body["answered_count"] != len(asked):
                session_failures.append("answered count does not match question path")
            if len(items) != 3 or len(set(item_ids)) != 3:
                session_failures.append("recommendations are not three unique tools")
            if percentages != sorted(percentages, reverse=True):
                session_failures.append("match percentages are not descending")
            for item in items:
                tool = tools_by_id.get(item["tool_id"])
                if tool is None or tool.stages != [stage] or tool.domain is not domain:
                    session_failures.append(
                        f"cross-pool recommendation: {item['tool_id']}"
                    )
                if not item.get("reasons"):
                    session_failures.append(f"missing reasons: {item['tool_id']}")
                if not item.get("limitations"):
                    session_failures.append(f"missing limitations: {item['tool_id']}")
                if not str(item.get("source_url", "")).startswith("https://"):
                    session_failures.append(f"missing source: {item['tool_id']}")

        if session_failures:
            failures.extend(
                f"session {session_index} ({pool_key}): {failure}"
                for failure in session_failures
            )
            continue

        completed += 1
        question_counts.append(len(asked))
        item_ids = [item["tool_id"] for item in final_body["recommendations"]]
        result_tools.update(item_ids)
        top_tools[pool_key].add(item_ids[0])
        paths.append(tuple(asked))
        recommendations.append(tuple(item_ids))
        if len(samples) < 12:
            first = final_body["recommendations"][0]
            samples.append(
                f"{pool_key} | {len(asked)} questions | {first['tool_name']} "
                f"({first['match_percent']}%, {first['confidence']})"
            )

    distribution = dict(sorted(Counter(question_counts).items()))
    return SimulationReport(
        session_count=session_count,
        completed_sessions=completed,
        failed_sessions=session_count - completed,
        pool_count=len(exercised_pools),
        minimum_question_count=min(question_counts, default=0),
        maximum_question_count=max(question_counts, default=0),
        question_count_distribution=distribution,
        result_tool_coverage=len(result_tools),
        result_tool_coverage_percent=round(100 * len(result_tools) / 48, 1),
        top_recommendation_diversity={
            key: len(values) for key, values in sorted(top_tools.items())
        },
        session_paths=tuple(paths),
        session_recommendations=tuple(recommendations),
        failures=tuple(failures),
        samples=tuple(samples),
    )


def render_markdown(report: SimulationReport) -> str:
    distribution = ", ".join(
        f"{count} questions: {sessions} sessions"
        for count, sessions in report.question_count_distribution.items()
    )
    lines = [
        "# Adaptive Questionnaire - 250 Session Simulation",
        "",
        "**Run type:** real FastAPI boundary with deterministic stateless sessions  ",
        f"**Requested sessions:** {report.session_count}  ",
        f"**Completed sessions:** {report.completed_sessions}  ",
        f"**Failed sessions:** {report.failed_sessions}",
        "",
        "## Acceptance metrics",
        "",
        f"- Stage/domain pools exercised: {report.pool_count}/12",
        f"- Question range observed: {report.minimum_question_count}-{report.maximum_question_count}",
        f"- Distribution: {distribution or 'none'}",
        f"- Catalog tools appearing in top-three results: {report.result_tool_coverage}/48 ({report.result_tool_coverage_percent}%)",
        "",
        "## Top-recommendation diversity by pool",
        "",
        "| Pool | Distinct top tools |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {pool} | {count} |"
        for pool, count in report.top_recommendation_diversity.items()
    )
    lines.extend(["", "## Representative outputs", ""])
    lines.extend(f"- {sample}" for sample in report.samples)
    lines.extend(["", "## Failures", ""])
    lines.extend(
        [f"- {failure}" for failure in report.failures]
        if report.failures
        else ["- None"]
    )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            (
                "PASS - every simulated session satisfied the structural output checks."
                if report.failed_sessions == 0
                else "FAIL - review the failures above before accepting the questionnaire."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=250)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/research/adaptive-questionnaire-250-session-report.md"),
    )
    parser.add_argument("--seed-prefix", default="simulation")
    args = parser.parse_args()
    report = run_simulation(
        session_count=args.sessions, seed_prefix=args.seed_prefix
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0 if report.failed_sessions == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
