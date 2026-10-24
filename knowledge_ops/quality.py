from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

TAXONOMY = {'financing', 'earnings', 'leadership_change', 'other'}
FIELDS = {'amount', 'currency', 'counterparty', 'person', 'role', 'effective_date', 'instrument', 'event_date'}


def validate_evidence(source_text: str, evidence: dict[str, Any]) -> list[str]:
    if not isinstance(evidence, dict):
        return ['evidence_not_object']
    start, end, quote = (evidence.get(k) for k in ('start', 'end', 'quote'))
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(source_text):
        return ['invalid_evidence_offsets']
    if not isinstance(quote, str) or source_text[start:end] != quote:
        return ['evidence_quote_mismatch']
    return []


def validate_output_record(record: dict[str, Any], source_text: str) -> tuple[list[str], bool]:
    issues = []
    critical = False
    for key, typ in {'record_id':str,'source_id':str,'processor':str,'run_id':str,'event_type':str,'facts':list,'tags':list,'summary':str,'validation_issues':list,'review_status':str}.items():
        if key not in record or not isinstance(record[key], typ):
            issues.append('invalid_' + key)
            critical = True
    if not isinstance(record.get('event_type'), str) or record['event_type'] not in TAXONOMY:
        issues.append('invalid_event_type')
        critical = True
    tags = record.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(t, str) or t not in TAXONOMY for t in tags):
        issues.append('invalid_tags')
        critical = True
    facts = record.get('facts', [])
    if not isinstance(facts, list):
        return issues + ['facts_not_list'], True
    for fact in facts:
        if not isinstance(fact, dict):
            issues.append('fact_not_object')
            critical = True
            continue
        field, value = fact.get('field'), fact.get('value')
        if not isinstance(field, str) or field not in FIELDS or not isinstance(value, str):
            issues.append('invalid_fact_field_or_value')
            critical = True
        if field == 'amount':
            if not isinstance(value, str) or not re.fullmatch(r'-?\d+(?:\.\d+)?', value):
                issues.append('invalid_amount_format')
                critical = True
            if not isinstance(fact.get('currency'), str) or fact.get('currency') not in {'USD','EUR','GBP'}:
                issues.append('missing_currency')
                if fact.get('currency') is not None and not isinstance(fact.get('currency'),str): critical = True
        evidence_issues = validate_evidence(source_text, fact.get('evidence'))
        issues.extend(evidence_issues)
        critical |= bool(evidence_issues)
    return issues, critical


def review_output_hash(record: dict[str, Any]) -> str:
    # Review decisions and mutable routing fields cannot recursively hash themselves.
    payload = {k:v for k,v in record.items() if k not in {'human_review','review_status','validation_issues','hard_rejected'}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode()).hexdigest()


def append_review_decisions(records: list[dict[str, Any]], decisions: list[dict[str, Any]], code_revision: str) -> list[dict[str, Any]]:
    index = {r['record_id']:r for r in records}
    for decision in decisions:
        record = index.get(decision.get('record_id'))
        if record is None:
            raise ValueError('review references unknown record')
        for key in ('reviewer','timestamp','decision','rationale','source_hash','output_hash','code_revision'):
            if not isinstance(decision.get(key), str) or not decision[key]:
                if key == 'code_revision':
                    continue
                raise ValueError('invalid review ' + key)
        dt = datetime.fromisoformat(decision['timestamp'].replace('Z', '+00:00'))
        if dt.tzinfo is None or decision['decision'] not in {'approve','reject','request_changes'}:
            raise ValueError('invalid review timestamp or decision')
        matches = (decision.get('source_hash') == record.get('input_sha256')
                   and decision.get('output_hash') == review_output_hash(record)
                   and decision.get('code_revision') == code_revision == record.get('code_revision'))
        if not matches:
            record.setdefault('validation_issues', []).append('stale_human_review')
            if record.get('review_status') != 'rejected':
                record['review_status'] = 'needs_review'
            continue
        record['hard_rejected'] = bool(record.get('hard_rejected') or record.get('review_status') == 'rejected')
        if record['hard_rejected'] and decision['decision'] == 'approve':
            raise ValueError('cannot approve deterministically rejected record')
        record.setdefault('human_review', []).append(dict(decision))
        if record['hard_rejected']:
            record['review_status'] = 'rejected'
            continue
        record['review_status'] = {'approve':'human_approved','reject':'human_rejected','request_changes':'needs_review'}[decision['decision']]
    return records
