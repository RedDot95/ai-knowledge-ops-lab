from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .ingest import hash_input_record
from .quality import validate_output_record

TAXONOMY = ["financing", "earnings", "leadership_change", "other"]


def _evidence(text: str, start: int, end: int) -> dict[str, Any]:
    return {"start": start, "end": end, "quote": text[start:end]}


def _find_first(pattern: str, text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    return re.search(pattern, text, flags)


def classify_event(text: str) -> list[str]:
    events: list[str] = []
    if re.search(r"\b(earnings|results|revenue|quarter)\b", text, re.IGNORECASE):
        events.append("earnings")
    if re.search(r"\b(notes|offering|financing|credit facility|debt)\b", text, re.IGNORECASE):
        events.append("financing")
    if re.search(r"\b(appointed|resigned|chief executive officer|chief financial officer|ceo|cfo)\b", text, re.IGNORECASE):
        events.append("leadership_change")
    if not events:
        events.append("other")
    return sorted(set(events))


def extract_facts(text: str, event_type: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    amount_match = _find_first(r"(USD|US\$|\$|EUR|€|GBP|£)\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if amount_match:
        currency = amount_match.group(1)
        normalized = {"US$": "USD", "$": "USD", "€": "EUR", "£": "GBP"}.get(currency, currency)
        amount = amount_match.group(2).replace(",", "")
        facts.append(
            {
                "field": "amount",
                "value": amount,
                "currency": normalized,
                "evidence": _evidence(text, amount_match.start(), amount_match.end()),
            }
        )

    if event_type == "leadership_change":
        person = _find_first(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", text)
        if person:
            facts.append({"field": "person", "value": person.group(1), "evidence": _evidence(text, person.start(1), person.end(1))})

    return facts


def _record_id(run_id: str, source_id: str, processor: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{source_id}:{processor}".encode("utf-8")).hexdigest()
    return f"rec-{digest[:16]}"


def _has_prompt_injection(text: str) -> bool:
    return bool(re.search(r"ignore previous instructions|system prompt|exfiltrate", text, re.IGNORECASE))


def run_rules(records: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for source in records:
        events = classify_event(source["text"])
        issues: list[str] = []
        review_status = "pending_review"
        event_type = events[0]
        if len(events) > 1:
            event_type = "other"
            issues.append("multi_event_ambiguity")
            review_status = "needs_review"

        facts = extract_facts(source["text"], event_type)
        if any(fact.get("field") == "amount" and not fact.get("currency") for fact in facts):
            issues.append("missing_currency")
            review_status = "needs_review"
        if _has_prompt_injection(source["text"]):
            issues.append("prompt_injection_indicator")
            review_status = "needs_review"

        record = {
            "record_id": _record_id(run_id, source["source_id"], "rules"),
            "source_id": source["source_id"],
            "input_sha256": hash_input_record(source),
            "processor": "rules",
            "run_id": run_id,
            "event_type": event_type,
            "facts": facts,
            "tags": [event_type],
            "summary": f"Rule baseline classified as {event_type}.",
            "validation_issues": issues,
            "review_status": review_status,
            "provenance": {"generated_at": datetime.now(timezone.utc).isoformat()},
        }
        extra_issues, critical = validate_output_record(record, source["text"])
        if extra_issues:
            record["validation_issues"].extend(extra_issues)
        if critical:
            record["review_status"] = "rejected"
        outputs.append(record)
    return outputs


def _parse_response_payload(response: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    parsed = response.get("output")
    if parsed is None and isinstance(response.get("response_text"), str):
        try:
            parsed = json.loads(response["response_text"])
        except json.JSONDecodeError:
            issues.append("invalid_llm_json")
            return None, issues
    if not isinstance(parsed, dict):
        issues.append("invalid_llm_json")
        return None, issues
    return parsed, issues


def import_model_outputs(
    source_records: list[dict[str, Any]],
    responses_payload: dict[str, Any],
    processor: str,
    run_id: str,
) -> list[dict[str, Any]]:
    if processor not in {"direct", "controlled"}:
        raise ValueError("processor must be direct or controlled")

    source_by_id = {record["source_id"]: record for record in source_records}
    outputs: list[dict[str, Any]] = []
    seen_response_ids: set[str] = set()

    responses = responses_payload.get("responses", responses_payload)
    if not isinstance(responses, list):
        raise ValueError("responses payload must be list or object with responses")

    for idx, response in enumerate(responses):
        if not isinstance(response, dict):
            continue
        source_id = response.get("source_id")
        issues: list[str] = []
        review_status = "pending_review"

        if not isinstance(source_id, str) or source_id not in source_by_id:
            issues.append("unknown_source")
            review_status = "rejected"

        if isinstance(source_id, str) and source_id in seen_response_ids:
            issues.append("duplicate_response")
            review_status = "needs_review"
        if isinstance(source_id, str):
            seen_response_ids.add(source_id)

        parsed, parse_issues = _parse_response_payload(response)
        issues.extend(parse_issues)
        if parse_issues:
            review_status = "rejected"

        source = source_by_id.get(source_id) if isinstance(source_id, str) else None
        if source:
            declared_hash = response.get("input_sha256")
            expected_hash = hash_input_record(source)
            if declared_hash != expected_hash:
                issues.append("source_hash_mismatch")
                review_status = "rejected"

        event_type = "other"
        facts: list[dict[str, Any]] = []
        tags: list[str] = []
        summary = ""

        if parsed:
            required_output_keys = {"event_type", "facts", "tags", "summary"}
            if not required_output_keys.issubset(parsed.keys()):
                issues.append("missing_event_fields")
                review_status = "needs_review"
            event_type = parsed.get("event_type", "other")
            facts = parsed.get("facts", []) if isinstance(parsed.get("facts"), list) else []
            tags = parsed.get("tags", []) if isinstance(parsed.get("tags"), list) else []
            summary = parsed.get("summary", "") if isinstance(parsed.get("summary"), str) else ""

            if event_type not in TAXONOMY:
                issues.append("invalid_event_type")
                review_status = "rejected"
            if not summary:
                issues.append("missing_event_fields")
                review_status = "needs_review"
            if _has_prompt_injection(summary):
                issues.append("prompt_injection_indicator")
                review_status = "needs_review"
            if len(tags) != len(set(tags)):
                issues.append("duplicate_tags")
                review_status = "needs_review"
            field_values: dict[str, set[str]] = {}
            for fact in facts:
                if isinstance(fact, dict) and isinstance(fact.get("field"), str) and isinstance(fact.get("value"), str):
                    field_values.setdefault(fact["field"], set()).add(fact["value"])
            if any(len(values) > 1 for values in field_values.values()):
                issues.append("contradictory_facts")
                review_status = "needs_review"

        source_text = source["text"] if source else ""
        output = {
            "record_id": _record_id(run_id, source_id or f"unknown-{idx}", processor),
            "source_id": source_id,
            "input_sha256": hash_input_record(source) if source else None,
            "processor": processor,
            "run_id": run_id,
            "event_type": event_type,
            "facts": facts,
            "tags": tags,
            "summary": summary,
            "validation_issues": issues,
            "review_status": review_status,
            "model_response": {
                "response_text": response.get("response_text"),
                "model": response.get("model"),
                "session_id": response.get("session_id"),
                "received_at": response.get("received_at"),
            },
        }
        extra_issues, critical = validate_output_record(output, source_text)
        output["validation_issues"].extend(extra_issues)
        if critical:
            output["review_status"] = "rejected"
        outputs.append(output)
    return outputs
