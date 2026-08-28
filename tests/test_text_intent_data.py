import json
from pathlib import Path

import pytest

from app.domain.models import Language
from app.knowledge import default_knowledge_path, load_knowledge
from app.text_intent.datasets import (
    DatasetLoadError,
    DatasetSplit,
    audit_text_intent_splits,
    default_dataset_paths,
    load_text_intent_rows,
)


def legacy_knowledge_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "knowledge" / "phase6.json"


def row(
    *,
    row_id: str,
    split: DatasetSplit,
    text: str,
    family: str,
    question_id: str = "analysis-q4",
    intent_id: str = "evidence_synthesis",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": row_id,
        "language": "en",
        "question_id": question_id,
        "intent_id": intent_id,
        "text": text,
        "split": split.value,
        "provenance": "authored",
        "template_family": family,
    }
    if split is DatasetSplit.ACCEPTANCE:
        payload["supporting_answers"] = [
            {"question_id": "analysis-q1", "option_ids": ["depth"]}
        ]
        payload["expected_tool_ids"] = ["chatgpt", "claude", "gemini"]
    return payload


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in rows),
        encoding="utf-8",
    )


def test_load_text_intent_rows_is_strict_and_reports_the_line(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    valid = row(
        row_id="train-1",
        split=DatasetSplit.TRAIN,
        text="combine reliable findings",
        family="train-synthesis",
    )
    invalid = {**valid, "id": "train-2", "unexpected": True}
    write_rows(path, [valid, invalid])

    with pytest.raises(DatasetLoadError, match=r"rows.jsonl:2") as caught:
        load_text_intent_rows(path)

    assert "combine reliable findings" not in str(caught.value)


def test_dataset_audit_detects_cross_split_text_and_template_leakage(
    tmp_path: Path,
) -> None:
    train = tmp_path / "train.jsonl"
    calibration = tmp_path / "calibration.jsonl"
    acceptance = tmp_path / "acceptance.jsonl"
    write_rows(
        train,
        [
            row(
                row_id="duplicate-id",
                split=DatasetSplit.TRAIN,
                text="Combine reliable findings",
                family="shared-family",
            )
        ],
    )
    write_rows(
        calibration,
        [
            row(
                row_id="duplicate-id",
                split=DatasetSplit.CALIBRATION,
                text="combine   reliable findings",
                family="shared-family",
            )
        ],
    )
    write_rows(
        acceptance,
        [
            row(
                row_id="acceptance-1",
                split=DatasetSplit.ACCEPTANCE,
                text="synthesize evidence",
                family="acceptance-family",
            )
        ],
    )
    paths = {
        Language.ENGLISH: {
            DatasetSplit.TRAIN: train,
            DatasetSplit.CALIBRATION: calibration,
            DatasetSplit.ACCEPTANCE: acceptance,
        }
    }

    audit = audit_text_intent_splits(paths, load_knowledge(legacy_knowledge_path()))

    assert any("duplicate row id" in item for item in audit.violations)
    assert any("normalized text crosses splits" in item for item in audit.violations)
    assert any("template family crosses splits" in item for item in audit.violations)
    assert any("acceptance text duplicates an alias" in item for item in audit.violations)


def test_dataset_audit_rejects_unknown_question_and_intent_pairs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "train.jsonl"
    write_rows(
        path,
        [
            row(
                row_id="unknown-1",
                split=DatasetSplit.TRAIN,
                text="unknown label",
                family="unknown-family",
                question_id="missing-question",
                intent_id="missing-intent",
            )
        ],
    )

    audit = audit_text_intent_splits(
        {Language.ENGLISH: {DatasetSplit.TRAIN: path}},
        load_knowledge(legacy_knowledge_path()),
    )

    assert any("unknown question/intent" in item for item in audit.violations)


def test_bundled_text_intent_splits_pass_the_frozen_distribution_audit() -> None:
    audit = audit_text_intent_splits(
        default_dataset_paths(), load_knowledge(legacy_knowledge_path())
    )

    assert audit.passed
    assert audit.counts["en"] == {
        "train": 320,
        "calibration": 80,
        "acceptance": 100,
    }
    assert audit.counts["ar"] == {
        "train": 320,
        "calibration": 80,
        "acceptance": 100,
    }
    assert len(audit.dataset_sha256) == 64


def test_phase_six_audit_command_includes_the_frozen_datasets() -> None:
    from scripts.audit_phase6 import run_audit

    payload, exit_code = run_audit(legacy_knowledge_path())

    assert exit_code == 0
    assert payload["datasets"]["passed"] is True
    assert payload["datasets"]["counts"]["en"]["acceptance"] == 100
