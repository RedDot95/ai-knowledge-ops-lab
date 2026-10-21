from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .evaluate import evaluate_command
from .export import export_replay
from .ingest import load_input_records, strict_load_json
from .processors import import_model_outputs, run_rules
from .sources import SecAdapter


def _run_id(processor: str) -> str:
    return f"{processor}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _write_run(output_dir: Path, run_payload: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.json").write_text(json.dumps(run_payload, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_fetch_sec(args: argparse.Namespace) -> int:
    adapter = SecAdapter()
    result = adapter.fetch(args.manifest, args.output)
    print(json.dumps({"records": len(result.records), "errors": len(result.errors)}))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    start = time.perf_counter()
    records = load_input_records(args.input)
    if args.processor != "rules":
        raise SystemExit("Only rules processor is supported for run")
    run_id = _run_id("rules")
    outputs = run_rules(records, run_id)
    elapsed = time.perf_counter() - start

    source_by_id = {record["source_id"]: record for record in records}
    for output in outputs:
        source = source_by_id.get(output["source_id"], {})
        output["source_url"] = source.get("source_url")
        output.setdefault("provenance", {}).update({"source_kind": source.get("source_kind")})

    run_payload = {
        "run_id": run_id,
        "processor": "rules",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timing_seconds": elapsed,
        "records": outputs,
    }
    _write_run(Path(args.output), run_payload)
    print(json.dumps({"run_id": run_id, "records": len(outputs), "timing_seconds": elapsed}))
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    start = time.perf_counter()
    records = load_input_records(args.input)
    responses = strict_load_json(args.responses)
    run_id = _run_id(args.processor)
    outputs = import_model_outputs(records, responses, args.processor, run_id)
    elapsed = time.perf_counter() - start

    source_by_id = {record["source_id"]: record for record in records}
    for output in outputs:
        source = source_by_id.get(output.get("source_id"), {})
        output["source_url"] = source.get("source_url")
        output.setdefault("provenance", {}).update({"source_kind": source.get("source_kind")})

    run_payload = {
        "run_id": run_id,
        "processor": args.processor,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timing_seconds": elapsed,
        "records": outputs,
    }
    _write_run(Path(args.output), run_payload)
    print(json.dumps({"run_id": run_id, "records": len(outputs), "timing_seconds": elapsed}))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    result = evaluate_command(args.run, args.truth, args.split)
    print(json.dumps(result, indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    run_payload = json.loads((Path(args.run) / "run.json").read_text(encoding="utf-8"))
    export_replay(run_payload, args.output)
    print(json.dumps({"output": args.output, "records": len(run_payload.get("records", []))}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="knowledge_ops")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch-sec")
    fetch.add_argument("--manifest", required=True)
    fetch.add_argument("--output", required=True)
    fetch.set_defaults(func=cmd_fetch_sec)

    run = sub.add_parser("run")
    run.add_argument("--input", required=True)
    run.add_argument("--processor", required=True)
    run.add_argument("--output", required=True)
    run.set_defaults(func=cmd_run)

    imp = sub.add_parser("import")
    imp.add_argument("--input", required=True)
    imp.add_argument("--responses", required=True)
    imp.add_argument("--processor", required=True)
    imp.add_argument("--output", required=True)
    imp.set_defaults(func=cmd_import)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--run", required=True)
    evaluate.add_argument("--truth", required=True)
    evaluate.add_argument("--split", required=True)
    evaluate.set_defaults(func=cmd_evaluate)

    export = sub.add_parser("export")
    export.add_argument("--run", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
