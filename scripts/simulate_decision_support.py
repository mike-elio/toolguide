"""Exercise hard constraints against every real stage/domain pool."""

import argparse
from collections import Counter
from itertools import product
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import DomainId, StageId
from app.knowledge import default_knowledge_path, load_knowledge
from app.main import create_app
from app.text_intent import AnswerResolutionService


def run_constraint_simulation() -> dict:
    knowledge = load_knowledge(default_knowledge_path())
    client = TestClient(create_app(knowledge=knowledge, answer_resolution_service=AnswerResolutionService()))
    capabilities = {"requires_offline": "offline", "requires_free_plan": "free_plan",
                    "requires_open_source": "open_source"}
    configurations = [{key: True} for key in capabilities] + [dict.fromkeys(capabilities, True)]
    questions = {q.id: q for q in knowledge.questions}
    failures, sessions = [], []
    for stage, domain, constraints in product(StageId, DomainId, configurations):
        pool = [tool for tool in knowledge.tools if tool.stages == [stage] and tool.domain is domain]
        # Independent expected eligibility from evidence, not the production filter.
        expected = {tool.id for tool in pool if tool.profile and all(
            getattr(tool.profile, capabilities[key]).value is True for key in constraints)}
        body = dict(language="ar", stage=stage.value, domain=domain.value,
                    session_seed=f"constraint-{stage}-{domain}", asked_question_ids=[],
                    answers=[], constraints=constraints)
        label = f"{stage.value}/{domain.value}: {','.join(constraints)}"
        result = None
        for _ in range(11):
            response = client.post("/api/questionnaire/advance", json=body)
            if response.status_code != 200:
                failures.append(f"{label}: HTTP {response.status_code}")
                break
            result = response.json()
            if result["status"] in {"complete", "no_match"}:
                break
            question = questions[result["question"]["id"]]
            body["asked_question_ids"].append(question.id)
            body["answers"].append(dict(question_id=question.id,
                option_ids=[(question.options or question.text_intents)[0].id]))
        if result is None:
            continue
        recommended = {item["tool_id"] for item in result["recommendations"]}
        if result["eligible_count"] != len(expected) or not recommended <= expected:
            failures.append(f"{label}: unverified or incorrect eligibility")
        if len(recommended) != min(3, len(expected)):
            failures.append(f"{label}: wrong recommendation count")
        if expected and (result["status"] != "complete" or not 6 <= result["answered_count"] <= 10):
            failures.append(f"{label}: incomplete questionnaire")
        if not expected and result["status"] != "no_match":
            failures.append(f"{label}: missing no-match result")
        sessions.append(dict(pool=f"{stage.value}/{domain.value}", constraints=constraints,
                             count=len(recommended), status=result["status"],
                             answers=result["answered_count"]))
    return dict(version=knowledge.version, sessions=sessions, failures=failures)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/research/decision-support-constraint-report.md"))
    args = parser.parse_args()
    report = run_constraint_simulation()
    distribution = Counter(session["count"] for session in report["sessions"])
    lines = ["# Decision support constraint simulation", "",
             f"Knowledge version: `{report['version']}`", "",
             f"Sessions: {len(report['sessions'])} (12 pools × 4 constraint configurations)",
             f"Failures: {len(report['failures'])}", "",
             "Each result was checked against the catalog's explicit capability evidence.",
             "Unknown capabilities never satisfy a hard requirement.", "",
             "| Recommendations returned | Sessions |", "|---|---:|"]
    lines += [f"| {count} | {distribution[count]} |" for count in range(4)]
    lines += ["", "## Failures", ""] + (report["failures"] or ["None."])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(report['sessions'])} sessions; {len(report['failures'])} failures; {args.output}")
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
