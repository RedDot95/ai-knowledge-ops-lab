from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .ingest import MAX_TEXT_BYTES

USER_AGENT = "ai-knowledge-ops-lab/0.1 (+https://github.com/RedDot95/ai-knowledge-ops-lab)"


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "ix:header"}:
            self._skip_depth += 1
        elif tag in {'p', 'div', 'br', 'tr', 'td', 'h1', 'h2'} and not self._skip_depth:
            self._parts.append(' ')

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth and tag in {"script", "style", "ix:header"}:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(data)

    def text(self) -> str:
        return ' '.join(''.join(self._parts).split())


def html_to_text(raw_html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(raw_html)
    return parser.text()


@dataclass
class FetchResult:
    records: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class SecAdapter:
    def __init__(self, timeout_seconds: float = 25.0, min_interval_seconds: float = 1.05) -> None:
        self.timeout_seconds = timeout_seconds
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)

    def _download(self, url: str) -> bytes:
        self._throttle()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = response.read()
        finally:
            self._last_request_at = time.monotonic()
        return data

    def fetch(self, manifest_path: str | Path, output_dir: str | Path) -> FetchResult:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        output_base = Path(output_dir)
        raw_dir = output_base / "raw"
        text_dir = output_base / "text"
        raw_dir.mkdir(parents=True, exist_ok=True)
        text_dir.mkdir(parents=True, exist_ok=True)

        records: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for item in manifest.get("records", []):
            source_id = item["source_id"]
            raw_path = raw_dir / f"{source_id}.html"
            text_path = text_dir / f"{source_id}.txt"
            try:
                if text_path.exists():
                    text = text_path.read_text(encoding="utf-8")
                    observed_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if observed_sha == item.get("content_sha256"):
                        records.append(self._to_input_record(item, text, observed_sha))
                        continue

                raw_bytes = self._download(item["source_url"])
                raw_text = raw_bytes.decode("utf-8", errors="replace")
                text = html_to_text(raw_text)

                raw_path.write_bytes(raw_bytes)
                text_path.write_text(text, encoding="utf-8")

                observed_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if observed_sha != item.get("content_sha256"):
                    errors.append({"source_id": source_id, "error": "content_sha256_mismatch", "observed": observed_sha})
                    continue
                if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                    errors.append({"source_id": source_id, "error": "input_too_large"})
                    continue
                records.append(self._to_input_record(item, text, observed_sha))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                errors.append({"source_id": source_id, "error": "http_error", "detail": str(exc)})

        payload = {
            "schema_version": "input-records-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
            "errors": errors,
        }
        (output_base / "records.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return FetchResult(records=records, errors=errors)

    @staticmethod
    def _to_input_record(item: dict[str, Any], text: str, sha256: str) -> dict[str, Any]:
        return {
            "source_id": item["source_id"],
            "company_id": item["company_id"],
            "company_name": item["company_name"],
            "document_date": item["document_date"],
            "source_kind": item.get("source_kind", "sec_filing"),
            "provenance": {
                "accession_number": item.get("accession_number"),
                "primary_document": item.get("primary_document"),
                "retrieved_at": item.get("retrieved_at"),
                "submissions_url": item.get("submissions_url"),
                "submissions_sha256": item.get("submissions_sha256"),
                "rights_note": item.get("rights_note"),
                "extraction_version": item.get("extraction_version", "htmlparser-visible-v1"),
            },
            "source_url": item["source_url"],
            "text": text,
            "content_sha256": sha256,
        }
