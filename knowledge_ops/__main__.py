from __future__ import annotations

import argparse
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .evaluate import evaluate_command
from .export import export_replay
from .ingest import load_input_records, strict_load_json
from .processors import import_model_outputs, run_rules
from .sources import SecAdapter
from .quality import append_review_decisions


def _provenance(records, processor):
    try:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git','status','--porcelain'],text=True))
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = 'unknown', True
    prompts = {}
    for name in ('direct-v1.txt','controlled-v1.txt'):
        path = Path(__file__).resolve().parent.parent/'prompts'/name
        prompts[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    from .ingest import hash_input_record
    code_files = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).resolve().parent.glob('*.py')}
    return {'code_revision':revision,'code_dirty':dirty,'code_files_sha256':code_files,'prompt_sha256':prompts,
            'expected_source_ids':[r['source_id'] for r in records],
            'input_hashes':{r['source_id']:hash_input_record(r) for r in records},
            'timing_scope':'local processing/import only; excludes model inference and manual transfer',
            'variable_cost':'unknown; no application model calls made by this command'}


def _run_id(processor: str) -> str:
    return f"{processor}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _write_run(output_dir: Path, run_payload: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run.json").write_text(json.dumps(run_payload, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_fetch_sec(args: argparse.Namespace) -> int:
    adapter = SecAdapter()
    result = adapter.fetch(args.manifest, args.output)
    print(json.dumps({"records": len(result.records), "errors": len(result.errors)}))
    return 1 if result.errors else 0


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
    run_payload.update(_provenance(records, 'rules'))
    for record in outputs:
        record['code_revision'] = run_payload['code_revision']
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
    run_payload.update(_provenance(records, args.processor))
    for record in outputs:
        record['code_revision'] = run_payload['code_revision']
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


def cmd_review(args):
    run_dir = Path(args.run)
    payload = strict_load_json(run_dir/'run.json')
    decisions = strict_load_json(args.decisions)
    if not isinstance(decisions, list):
        raise ValueError('decisions must be a list')
    # Validate on a copy so malformed decisions cannot partly mutate the saved run.
    import copy
    updated = append_review_decisions(copy.deepcopy(payload['records']), decisions, payload.get('code_revision','unknown'))
    with (run_dir/'reviews.jsonl').open('a',encoding='utf-8') as log:
        for decision in decisions:
            log.write(json.dumps({'submitted_decision':decision,'logged_at':datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+'\n')
    payload['records'] = updated
    _write_run(run_dir,payload)
    print(json.dumps({'submitted_decisions':len(decisions),'log':'reviews.jsonl'}))
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

    review = sub.add_parser('review')
    review.add_argument('--run',required=True)
    review.add_argument('--decisions',required=True)
    review.set_defaults(func=cmd_review)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
