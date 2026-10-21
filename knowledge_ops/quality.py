from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any


def validate_evidence(source_text: str, evidence: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(evidence, dict):
        return ["evidence_not_object"]
    start = evidence.get("start")
    end = evidence.get("end")
    quote = evidence.get("quote")
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
        return ["invalid_evidence_offsets"]
    if end > len(source_text):
        return ["invalid_evidence_offsets"]
    if not isinstance(quote, str):
        return ["evidence_quote_missing"]
    if source_text[start:end] != quote:
        issues.append("evidence_quote_mismatch")
    return issues


def validate_output_record(record: dict[str, Any], source_text: str) -> tuple[list[str], bool]:
    issues: list[str] = []
    critical = False
    for key in ["record_id", "source_id", "processor", "run_id", "event_type", "facts", "tags", "summary", "validation_issues", "review_status"]:
        if key not in record:
            issues.append(f"missing_{key}")
            critical = True

    if not isinstance(record.get("facts", []), list):
        issues.append("facts_not_list")
        critical = True
        return issues, critical

    for fact in record.get("facts", []):
        if not isinstance(fact, dict):
            issues.append("fact_not_object")
            critical = True
            continue
        field = fact.get("field")
        value = fact.get("value")
        evidence = fact.get("evidence")
        if not isinstance(field, str) or not isinstance(value, str):
            issues.append("invalid_fact_field_or_value")
            critical = True
        if field == "amount":
            if not value.replace(".", "", 1).isdigit():
                issues.append("invalid_amount_format")
            if not fact.get("currency"):
                issues.append("missing_currency")
        issues.extend(validate_evidence(source_text, evidence))
    if any(item in {"invalid_evidence_offsets", "evidence_quote_mismatch"} for item in issues):
        critical = True
    return issues, critical


def append_review_decisions(records: list[dict[str, Any]], decisions: list[dict[str, Any]], code_revision: str) -> list[dict[str, Any]]:
    index = {record["record_id"]: record for record in records}
    for decision in decisions:
        record_id = decision.get("record_id")
        if record_id not in index:
            continue
        record = index[record_id]
        try:
            datetime.fromisoformat(decision["timestamp"].replace("Z", "+00:00"))
        except Exception:
            continue
        source_hash = hashlib.sha256(record["source_id"].encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256(
            json.dumps({"event_type": record.get("event_type"), "facts": record.get("facts", [])}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if source_hash != decision.get("source_hash") or output_hash != decision.get("output_hash"):
            record.setdefault("validation_issues", []).append("stale_human_review")
            record["review_status"] = "needs_review"
            continue
        record.setdefault("human_review", []).append(
            {
                "reviewer": decision["reviewer"],
                "timestamp": decision["timestamp"],
                "decision": decision["decision"],
                "rationale": decision["rationale"],
                "source_hash": source_hash,
                "output_hash": output_hash,
                "code_revision": code_revision,
            }
        )
    return records
