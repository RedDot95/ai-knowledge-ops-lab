from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

TAXONOMY = ["financing", "earnings", "leadership_change", "other"]
ALLOWED_FIELDS = {"amount", "currency", "counterparty", "person", "role", "effective_date", "instrument", "event_date"}


def _safe_div(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def _macro_f1(truth: list[str], pred: list[str]) -> float:
    f1_values: list[float] = []
    for label in TAXONOMY:
        tp = sum(1 for t, p in zip(truth, pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(truth, pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(truth, pred) if t == label and p != label)
        precision = _safe_div(tp, tp + fp) or 0.0
        recall = _safe_div(tp, tp + fn) or 0.0
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        f1_values.append(f1)
    return sum(f1_values) / len(f1_values)


def evaluate_run(run_payload: dict[str, Any], truth_payload: dict[str, Any], split: str) -> dict[str, Any]:
    truth_records = [row for row in truth_payload.get("records", []) if row.get("split") == split]
    predictions = {
        record["source_id"]: record
        for record in run_payload.get("records", [])
        if not record.get("provenance", {}).get("mock") and not str(record.get("source_id", "")).startswith("mock-")
    }

    truth_labels: list[str] = []
    predicted_labels: list[str] = []
    missing_or_invalid = 0
    schema_valid_count = 0
    applicable_expected = 0
    applicable_valid = 0
    unsupported_extra_fields = 0
    critical_errors = 0
    needs_review_count = 0
    rejected_count = 0

    for truth in truth_records:
        source_id = truth["source_id"]
        truth_label = truth["event_type"]
        pred = predictions.get(source_id)
        truth_labels.append(truth_label)
        if not pred or pred.get("event_type") not in TAXONOMY:
            predicted_labels.append("other")
            missing_or_invalid += 1
            continue

        predicted_labels.append(pred["event_type"])

        issues = pred.get("validation_issues", [])
        if not issues:
            schema_valid_count += 1
        if pred.get("review_status") == "needs_review":
            needs_review_count += 1
        if pred.get("review_status") == "rejected":
            rejected_count += 1
            critical_errors += 1

        expected_fields = truth.get("expected_fields", [])
        observed_fields = {fact.get("field") for fact in pred.get("facts", []) if isinstance(fact, dict)}
        applicable_expected += len(expected_fields)
        applicable_valid += sum(1 for field in expected_fields if field in observed_fields)
        unsupported_extra_fields += sum(1 for field in observed_fields if field and field not in ALLOWED_FIELDS)

    total = len(truth_records)
    correct = sum(1 for t, p in zip(truth_labels, predicted_labels) if t == p)

    class_counts = Counter(truth_labels)

    return {
        "split": split,
        "total_records": total,
        "class_counts": {label: class_counts.get(label, 0) for label in TAXONOMY},
        "classification_accuracy": _safe_div(correct, total),
        "macro_f1_fixed_4_class": _macro_f1(truth_labels, predicted_labels) if total else None,
        "schema_valid_rate": _safe_div(schema_valid_count, total),
        "applicable_field_extraction_validity": _safe_div(applicable_valid, applicable_expected),
        "unsupported_extra_fields": unsupported_extra_fields,
        "critical_record_errors": critical_errors,
        "needs_review_rate": _safe_div(needs_review_count, total),
        "reject_rate": _safe_div(rejected_count, total),
        "missing_or_invalid_outputs": missing_or_invalid,
        "semantic_support_rate": None,
        "semantic_support_note": "Undefined until separately annotated atomic-claim support labels exist.",
        "timing_seconds": run_payload.get("timing_seconds"),
        "cost_estimate": "unknown",
        "ground_truth_status": truth_payload.get("ground_truth_status", "AI-assisted/unreviewed"),
        "excluded_mock_records": len(run_payload.get("records", [])) - len(predictions),
    }


def evaluate_command(run_dir: str | Path, truth_path: str | Path, split: str) -> dict[str, Any]:
    run_path = Path(run_dir) / "run.json"
    run_payload = json.loads(run_path.read_text(encoding="utf-8"))
    truth_payload = json.loads(Path(truth_path).read_text(encoding="utf-8"))
    result = evaluate_run(run_payload, truth_payload, split)
    (Path(run_dir) / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
