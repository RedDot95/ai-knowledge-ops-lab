from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from copy import deepcopy
from typing import Any

from .ingest import hash_input_record, _unique_object_pairs_hook
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
    if re.search(r"\b(appointed|resigned|not to stand for re-election|transition from his role)\b", text, re.IGNORECASE):
        events.append("leadership_change")
    if not events:
        events.append("other")
    return sorted(set(events))


def extract_facts(text: str, event_type: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    # The filing cover page contains par-values unrelated to the event.
    body = re.search(r"(?i)\bItem\s+[12578]\.\d{2}\b", text)
    offset = body.start() if body else 0
    search_text = text[offset:]
    amount_match = _find_first(r"(USD|US\$|\$|EUR|€|GBP|£)\s*([0-9][0-9,]*(?:\.[0-9]+)?)(?:\s*(thousand|million|billion))?", search_text)
    if amount_match:
        currency = amount_match.group(1)
        normalized = {"US$": "USD", "$": None, "€": "EUR", "£": "GBP"}.get(currency, currency)
        amount = format(Decimal(amount_match.group(2).replace(",", "")) * {None:1,"thousand":1000,"million":1000000,"billion":1000000000}[amount_match.group(3).lower() if amount_match.group(3) else None], "f")
        facts.append(
            {
                "field": "amount",
                "value": amount,
                "currency": normalized,
                "evidence": _evidence(text, offset + amount_match.start(), offset + amount_match.end()),
            }
        )

    if event_type == "leadership_change":
        person = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", search_text)
        if person:
            facts.append({"field": "person", "value": person.group(1), "evidence": _evidence(text, offset + person.start(1), offset + person.end(1))})

    return facts


def _record_id(run_id: str, source_id: str, processor: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{source_id}:{processor}".encode("utf-8")).hexdigest()
    return f"rec-{digest[:16]}"


def _has_prompt_injection(text: str) -> bool:
    return bool(re.search(r"ignore previous instructions|system prompt|exfiltrate", text, re.IGNORECASE))


def run_rules(records: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    seen_hashes = set()
    for source in records:
        events = classify_event(source["text"])
        issues: list[str] = []
        review_status = "pending_review"
        if source["content_sha256"] in seen_hashes:
            issues.append("duplicate_content")
            review_status = "needs_review"
        seen_hashes.add(source["content_sha256"])
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
            "provenance": {"generated_at": datetime.now(timezone.utc).isoformat(), "mock": bool(source.get("provenance", {}).get("mock"))},
        }
        extra_issues, critical = validate_output_record(record, source["text"])
        if extra_issues:
            record["validation_issues"].extend(extra_issues)
        record["schema_valid"] = not critical
        if critical:
            record["review_status"] = "rejected"
        outputs.append(record)
    return outputs


def _parse_response_payload(response: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    parsed = response.get("output")
    if parsed is None and isinstance(response.get("response_text"), str):
        try:
            parsed = json.loads(response["response_text"], object_pairs_hook=_unique_object_pairs_hook)
        except (json.JSONDecodeError, ValueError):
            issues.append("invalid_llm_json")
            return None, issues
    if not isinstance(parsed, dict):
        issues.append("invalid_llm_json")
        return None, issues
    return parsed, issues


def import_model_outputs(source_records, responses_payload, processor, run_id):
    if processor not in {"direct", "controlled"}:
        raise ValueError("processor must be direct or controlled")
    responses = responses_payload.get("responses") if isinstance(responses_payload, dict) else responses_payload
    if not isinstance(responses, list):
        raise ValueError("responses must be a list")
    source_by_id = {s["source_id"]:s for s in source_records}
    outputs = []
    seen = set()
    for idx, raw in enumerate(responses):
        response = raw if isinstance(raw, dict) else {}
        sid = response.get("source_id")
        source = source_by_id.get(sid) if isinstance(sid, str) else None
        issues = []
        hard = False
        if source is None:
            issues.append("unknown_source")
            hard = True
        if isinstance(sid, str):
            if sid in seen:
                issues.append("duplicate_response")
                for prior in outputs:
                    if prior["source_id"] == sid:
                        prior["validation_issues"].append("duplicate_response")
                        if prior["review_status"] != "rejected": prior["review_status"] = "needs_review"
            seen.add(sid)
        parsed, parse_issues = _parse_response_payload(response)
        issues.extend(parse_issues)
        hard |= bool(parse_issues)
        if source and response.get("input_sha256") != hash_input_record(source):
            issues.append("source_hash_mismatch")
            hard = True
        metadata_ok = all(isinstance(response.get(k), str) and response[k] for k in ("model", "session_id", "received_at"))
        if metadata_ok:
            try:
                metadata_ok = datetime.fromisoformat(response['received_at'].replace('Z','+00:00')).tzinfo is not None
            except ValueError:
                metadata_ok = False
        if not metadata_ok:
            issues.append("missing_model_provenance")
            hard = True
        parsed = parsed or {}
        if not {"event_type","facts","tags","summary"}.issubset(parsed):
            issues.append("missing_event_fields")
            hard = True
        event_type = parsed.get("event_type", "other")
        facts, tags, summary = parsed.get("facts", []), parsed.get("tags", []), parsed.get("summary", "")
        if not summary:
            issues.append("missing_event_fields")
        if isinstance(summary, str) and _has_prompt_injection(summary):
            issues.append("prompt_injection_indicator")
        if isinstance(tags, list) and all(isinstance(t,str) for t in tags) and len(tags) != len(set(tags)):
            issues.append("duplicate_tags")
        field_values = {}
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, dict) and isinstance(fact.get('field'),str) and isinstance(fact.get('value'),str):
                    field_values.setdefault(fact['field'],set()).add(fact['value'])
        if any(len(v)>1 for v in field_values.values()):
            issues.append('contradictory_facts')
        if source and _has_prompt_injection(source['text']):
            issues.append('prompt_injection_indicator')
        out = {'record_id':_record_id(run_id, sid if isinstance(sid,str) else f'unknown-{idx}', processor),
               'source_id':sid if isinstance(sid,str) else f'invalid-{idx}', 'input_sha256':response.get('input_sha256'), 'processor':processor, 'run_id':run_id,
               'event_type':event_type, 'facts':facts, 'tags':tags, 'summary':summary,
               'validation_issues':issues, 'review_status':'pending_review',
               'provenance':{'mock':bool(response.get('mock') or (source and source.get('provenance',{}).get('mock')))},
               'model_response':{'raw_envelope':deepcopy(raw), 'response_text':response.get('response_text'),
                                 'model':response.get('model'), 'session_id':response.get('session_id'), 'received_at':response.get('received_at')}}
        extra, critical = validate_output_record(out, source['text'] if source else '')
        out['validation_issues'] = list(dict.fromkeys(issues + extra))
        out['schema_valid'] = not critical and not parse_issues
        out['hard_rejected'] = bool(hard or critical)
        out['review_status'] = 'rejected' if hard or critical else ('needs_review' if out['validation_issues'] else 'pending_review')
        outputs.append(out)
    for sid, source in source_by_id.items():
        if sid not in seen:
            outputs.append({'record_id':_record_id(run_id,sid,processor),'source_id':sid,'input_sha256':hash_input_record(source),
                            'processor':processor,'run_id':run_id,'event_type':'other','facts':[],'tags':[],'summary':'',
                            'validation_issues':['missing_response'],'review_status':'rejected','provenance':{'mock':bool(source.get('provenance',{}).get('mock'))},'model_response':{'raw_envelope':None}})
    return outputs
