from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from knowledge_ops.sources import SecAdapter, html_to_text


class FrozenExtractionRegression(unittest.TestCase):
    def test_original_extraction_whitespace_contract(self):
        self.assertEqual(html_to_text('<html><p>Amount <b>USD</b> 10</p><p>Next</p></html>'), 'Amount USD 10 Next')


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SourcesTests(unittest.TestCase):
    def test_http_error_recorded(self) -> None:
        manifest = {
            "records": [
                {
                    "source_id": "s-1",
                    "company_id": "CIK1",
                    "company_name": "Example",
                    "document_date": "2026-10-20",
                    "source_kind": "sec_filing",
                    "source_url": "https://example.test/1",
                    "content_sha256": "0" * 64,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            adapter = SecAdapter()
            with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
                result = adapter.fetch(manifest_path, Path(tmp) / "out")
            self.assertEqual(len(result.errors), 1)
            self.assertEqual(result.errors[0]["error"], "http_error")

    def test_cache_used_without_network(self) -> None:
        text = "Revenue USD 100"
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        manifest = {
            "records": [
                {
                    "source_id": "s-1",
                    "company_id": "CIK1",
                    "company_name": "Example",
                    "document_date": "2026-10-20",
                    "source_kind": "sec_filing",
                    "source_url": "https://example.test/1",
                    "content_sha256": sha,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            (out / "text").mkdir(parents=True)
            (out / "text" / "s-1.txt").write_text(text, encoding="utf-8")
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            adapter = SecAdapter()
            with patch("urllib.request.urlopen") as mocked:
                result = adapter.fetch(manifest_path, out)
            mocked.assert_not_called()
            self.assertEqual(len(result.records), 1)
            self.assertEqual(result.records[0]["source_id"], "s-1")

    def test_fetch_timeout_recorded_deterministically(self) -> None:
        html = b"<html><body>Revenue USD 100</body></html>"
        text = "Revenue USD 100"
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        manifest = {
            "records": [
                {
                    "source_id": "s-1",
                    "company_id": "CIK1",
                    "company_name": "Example",
                    "document_date": "2026-10-20",
                    "source_kind": "sec_filing",
                    "source_url": "https://example.test/1",
                    "content_sha256": sha,
                },
                {
                    "source_id": "s-2",
                    "company_id": "CIK2",
                    "company_name": "Example 2",
                    "document_date": "2026-10-20",
                    "source_kind": "sec_filing",
                    "source_url": "https://example.test/2",
                    "content_sha256": sha,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            def fake_urlopen(request, timeout=0):
                if request.full_url.endswith("/2"):
                    raise TimeoutError("timeout")
                return _FakeResponse(html)

            adapter = SecAdapter(min_interval_seconds=0)
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = adapter.fetch(manifest_path, Path(tmp) / "out")

            self.assertEqual(len(result.records), 1)
            self.assertEqual(len(result.errors), 1)
            self.assertEqual(result.errors[0]["source_id"], "s-2")


if __name__ == "__main__":
    unittest.main()
