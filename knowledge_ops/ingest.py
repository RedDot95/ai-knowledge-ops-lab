from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

MAX_TEXT_BYTES = 50_000
REQUIRED_SOURCE_FIELDS = {
    "source_id": str,
    "company_id": str,
    "company_name": str,
    "document_date": str,
    "source_kind": str,
    "provenance": dict,
    "source_url": str,
    "text": str,
    "content_sha256": str,
}


class ValidationError(ValueError):
    pass


class DuplicateKeyError(ValidationError):
    pass


def _unique_object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate key: {key}")
        out[key] = value
    return out


def strict_load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object_pairs_hook)


def _validate_date(date_value: str) -> None:
    try:
        date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValidationError(f"invalid date: {date_value}") from exc


def _validate_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValidationError(f"invalid sha256 for {field_name}")


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_input_record(record: dict[str, Any]) -> str:
    payload = {key: record[key] for key in REQUIRED_SOURCE_FIELDS}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    company_id: str
    company_name: str
    document_date: str
    source_kind: str
    provenance: dict[str, Any]
    source_url: str
    text: str
    content_sha256: str

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "document_date": self.document_date,
            "source_kind": self.source_kind,
            "provenance": self.provenance,
            "source_url": self.source_url,
            "text": self.text,
            "content_sha256": self.content_sha256,
        }


def validate_source_record(record: dict[str, Any]) -> SourceRecord:
    unexpected = set(record.keys()) - set(REQUIRED_SOURCE_FIELDS.keys())
    missing = set(REQUIRED_SOURCE_FIELDS.keys()) - set(record.keys())
    if missing:
        raise ValidationError(f"missing fields: {sorted(missing)}")
    if unexpected:
        raise ValidationError(f"unexpected fields: {sorted(unexpected)}")
    for field_name, expected_type in REQUIRED_SOURCE_FIELDS.items():
        if not isinstance(record[field_name], expected_type):
            raise ValidationError(f"wrong type for {field_name}")

    _validate_date(record["document_date"])
    _validate_sha256(record["content_sha256"], "content_sha256")

    byte_len = _utf8_len(record["text"])
    if byte_len > MAX_TEXT_BYTES:
        raise ValidationError(f"text exceeds {MAX_TEXT_BYTES} bytes")

    observed = hash_text(record["text"])
    if observed != record["content_sha256"]:
        raise ValidationError("source-hash mismatch")

    return SourceRecord(**record)


def load_input_records(path: str | Path) -> list[dict[str, Any]]:
    payload = strict_load_json(path)
    if isinstance(payload, dict):
        records = payload.get("records")
    else:
        records = payload
    if not isinstance(records, list):
        raise ValidationError("records must be a list")

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for idx, raw_record in enumerate(records):
        if not isinstance(raw_record, dict):
            raise ValidationError(f"record[{idx}] must be object")
        record = validate_source_record(raw_record)
        if record.source_id in seen:
            raise ValidationError(f"duplicate source_id: {record.source_id}")
        seen.add(record.source_id)
        out.append(record.as_dict)
    return out
