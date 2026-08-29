import argparse
import json
from pathlib import Path

from app.knowledge import (
    KnowledgeLoadError,
    audit_knowledge,
    default_knowledge_path,
    load_knowledge,
)
from app.text_intent.datasets import (
    audit_text_intent_splits,
    default_dataset_paths,
)


def run_audit(knowledge_path: Path) -> tuple[dict[str, object], int]:
    try:
        knowledge = load_knowledge(knowledge_path)
        audit = audit_knowledge(knowledge)
    except KnowledgeLoadError as error:
        return {"passed": False, "error": str(error)}, 1

    payload: dict[str, object] = audit.model_dump(mode="json")
    payload["passed"] = audit.passed
    if any(question.domain is not None for question in knowledge.questions):
        payload["datasets"] = {
            "passed": True,
            "skipped": True,
            "reason": "adaptive questionnaire uses curated aliases without training",
        }
        return payload, 0 if audit.passed else 1
    dataset_audit = audit_text_intent_splits(default_dataset_paths(), knowledge)
    dataset_payload = dataset_audit.model_dump(mode="json")
    dataset_payload["passed"] = dataset_audit.passed
    payload["datasets"] = dataset_payload
    return payload, 0 if audit.passed and dataset_audit.passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 6 knowledge data")
    parser.add_argument(
        "--knowledge",
        type=Path,
        default=default_knowledge_path(),
        help="Path to the canonical knowledge JSON or .json.gz catalog",
    )
    args = parser.parse_args()
    payload, exit_code = run_audit(args.knowledge)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
