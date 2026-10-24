from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BANNER = "Recorded pipeline results — no live model processing"


def export_replay(run_payload: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    has_records = bool(run_payload.get("records"))
    replay = {
        "banner": BANNER,
        "generated_from_run": run_payload.get("run_id"),
        "code_revision": run_payload.get("code_revision"),
        "code_dirty": run_payload.get("code_dirty"),
        "code_files_sha256": run_payload.get("code_files_sha256"),
        "prompt_sha256": run_payload.get("prompt_sha256"),
        "timing_scope": run_payload.get("timing_scope"),
        "processor": run_payload.get("processor") if has_records else "Not run",
        "approaches": {
            name: 'Recorded' if has_records and run_payload.get('processor') == name else 'Not run'
            for name in ('rules', 'direct', 'controlled')
        },
        "records": [
            {
                "record_id": record.get("record_id"),
                "source_id": record.get("source_id"),
                "source_url": record.get("source_url"),
                "event_type": record.get("event_type"),
                "summary": record.get("summary"),
                "review_status": record.get("review_status"),
                "validation_issues": record.get("validation_issues", []),
                "facts": record.get("facts", []),
                "provenance": record.get("provenance", {}),
                "input_sha256": record.get('input_sha256'),
            }
            for record in run_payload.get("records", [])
        ],
    }
    Path(output_path).write_text(json.dumps(replay, indent=2, ensure_ascii=False), encoding="utf-8")
    return replay
