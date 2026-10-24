# AI Knowledge Operations Lab

Applied AI research operations for turning real public company disclosures into structured, source-linked knowledge with deterministic quality controls.

> **Recorded pipeline results — no live model processing**

**Milestone M1: recorded, source-linked research pipeline.** A working Python CLI and static replay demonstrate ingestion, deterministic validation, auditable model-output import and review routing. A three-source in-session AI extraction is recorded. This is an evolving research project; isolated model experiments, reviewed labels and held-out evaluation remain open. See [milestone evidence and next steps](docs/milestone-m1.md).

## Start here

1. Read the [architecture](docs/architecture.md) and [evaluation limits](docs/evaluation.md).
2. Run the offline regression suite with Python 3.12+: `python -m unittest discover -s tests -v`. No third-party package or API key is needed.
3. Preview the committed replay: `python -m http.server 8000 --directory demo`, then open `http://localhost:8000`. Select the 15-source rules run or the separate three-source AI-assisted run. This serves recorded artifacts; it performs no model inference.
4. To reproduce processing from the frozen source manifest, follow the commands below and the [recorded response import instructions](docs/manual-model-session.md). This requires SEC network access; raw source text is intentionally excluded from git.

## Scope and current state

- Real source corpus: frozen 15-document SEC Form 8-K development manifest at `data/dev_manifest.json` (reused from commit `104cfef170f90c282cf9fe5a9d90a53ddee502fc`).
- Processor A (rules): implemented deterministic baseline.
- Processors B/C (direct/controlled): implemented as **auditable import** of model outputs only; a real three-source in-session assistant demonstration has been imported, with explicit method limitations.
- Ground truth: `data/ground_truth.json` remains **AI-assisted/unreviewed**. A [source-checked development review](docs/label-review-2026-10-24.md) reverified all 15 input hashes and corrected two classification labels; owner approval and exact-value/semantic annotations remain open.
- Synthetic robustness fixtures: `data/robustness.json` (10 cases), excluded from reported real-source metrics.

This repository is for research operations and does not provide investment advice.

## Rights and provenance limits

SEC access and issuer-document access are public, but this repository does **not** claim a blanket republication license for issuer-authored filing text. Raw filings and full extracted text stay local under ignored `.local/` paths. The repository stores source metadata, hashes, links, and derived records.

See `docs/data-sources.md` for provenance, sampling rule, and acquisition constraints.

## Commands

```bash
python -m unittest discover -s tests -v
python -m knowledge_ops fetch-sec --manifest data/dev_manifest.json --output .local/sources
python -m knowledge_ops run --input .local/sources/records.json --processor rules --output .local/rules-run
python -m knowledge_ops evaluate --run .local/rules-run --truth data/ground_truth.json --split dev
python -m knowledge_ops export --run .local/rules-run --output demo/replay.json
python -m knowledge_ops import --input .local/sources/records.json --responses .local/responses.json --processor direct --output .local/direct-run
python -m knowledge_ops import --input .local/sources/records.json --responses .local/responses.json --processor controlled --output .local/controlled-run
python -m knowledge_ops review --run .local/rules-run --decisions .local/decisions.json
```

## Architecture

- `knowledge_ops/sources.py`: SEC adapter with descriptive User-Agent, timeout, 1+ second pacing, local cache, and failure recording.
- `knowledge_ops/ingest.py`: strict input parsing and validation (duplicate keys/IDs, malformed types, invalid dates, >50KB text, hash mismatch).
- `knowledge_ops/processors.py`: deterministic rules baseline plus auditable model-output import and review routing.
- `knowledge_ops/evaluate.py`: deterministic scorecard (accuracy, fixed-four-class macro-F1, schema/extraction quality rates, critical errors, review rates).
- `knowledge_ops/export.py` + `demo/`: static replay output.

## Contribution attribution

- Owner supplied requirements and real-data direction.
- Assistant proposed architecture and data-prep flow.
- Copilot produced the initial MVP; ChatGPT Work performed independent review, reproduced defects, added regression tests and corrected the implementation. The failure analysis is in `docs/evaluation.md`.

No claim is made of owner code authorship, owner annotation approval, or production-readiness.

## Evidence and limits

On 21 October 2026, the corrected adapter fetched all 15 frozen real development filings with zero errors, and reproduced their recorded text hashes. The rules CLI processed all 15 and generated the committed replay. **32 automated tests passed again on 24 October 2026** at `0daed287426bda38785deaabc4e8d5f69473913f`, including regressions for false metric credit, malformed imports, stale approvals and frozen-source extraction. GitHub Actions run [39656453229](https://github.com/SFS-Labs/ai-knowledge-ops-lab/actions/runs/39656453229) passed on that same implementation commit. The historical live fetch was not repeated in the portfolio review; these are distinct verification events.

The rule baseline is deliberately simple and has weak event classification on these filings. Ground-truth labels are provisional and contain cases requiring further review; exact-value and semantic-support annotations are incomplete. Its diagnostic score is not a validated performance benchmark. Undefined quality measures remain undefined. The demo offers the actual 15-source rules replay and a separate three-source AI-assisted replay. See [the recorded session](docs/manual-model-session.md). Neither is a validated model benchmark.

For model imports, use an envelope containing `source_id`, the exact canonical `input_sha256`, `model`, `session_id`, timezone-aware `received_at`, and either `response_text` or `output`. Raw envelopes are retained. Mark test responses `mock: true`; source fixtures also carry mock provenance. API access is not configured by the import command.

For manual review, submit a JSON list with `record_id`, `reviewer`, timezone-aware `timestamp`, `decision` (`approve`, `reject`, `request_changes`), `rationale`, `source_hash` (the record's `input_sha256`), `output_hash` from `knowledge_ops.quality.review_output_hash`, and the run's `code_revision`. The CLI appends submitted decisions to `reviews.jsonl`; deterministic rejects cannot be approved. This local audit log is not tamper-proof storage or enterprise access control.
