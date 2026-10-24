# Recorded AI-assisted extraction

On 21 October 2026, the ongoing ChatGPT Work assistant read three actual source texts from the frozen SEC development corpus and authored classifications, summaries and extraction drafts. This used the current conversation, without a model API, API key or additional Copilot assignment. `data/manual_model_outputs.json` preserves the drafts and import envelopes. Python located the exact quoted spans in the source texts to add offsets; it did not generate the semantic extraction.

The documents were selected as three small, interpretable examples, not a random sample or held-out evaluation. The assistant had full project context. Its exact model snapshot, generation settings, token usage and generation time are unavailable. The local session identifier is an audit label, not a provider-issued execution ID. The committed prompts were not executed in isolation. Routing through `controlled` identifies the validator/import path, not evidence of a controlled model experiment.

## Actual observed results

Import run `controlled-20261021T184753Z` processed three records with nine extracted facts. All three satisfied the deterministic schema and all nine evidence quotes matched their source offsets. Raw response envelopes were retained. Two records were `pending_review`; the JPMorgan record was `needs_review`. None received human approval. These observations do not measure semantic support, classification accuracy or production reliability.

| Source | AI-assisted interpretation | Observed limitation |
|---|---|---|
| Microsoft, 29 July 2026 | Earnings announcement; event date extracted | Primary filing refers to an exhibit; no operating figures fabricated from the reference. |
| Microsoft, 2 June 2026 | Reid Hoffman not seeking reelection; name, role and notification date extracted | Notification date is not an exact departure date. |
| JPMorgan, 20 October 2026 | Financing; three note amounts, event date and instrument extracted | Multiple legitimate tranches trigger `contradictory_facts`; dollar symbols without explicit ISO currency trigger `missing_currency`. Review remains required. |

The contradiction flag is an observed false positive of the current single-field heuristic. A future schema could group amounts by tranche and link related evidence; that change has not been implemented or verified. The conservative currency warning remains visible rather than silently assuming USD. The session does not establish improved model performance or constitute three independent LLM failure cases.

## Reproduce import and validation

After fetching the frozen sources using the README command, construct the same subset and import the preserved responses:

```bash
python - <<'PY'
import json
from pathlib import Path
sources = json.loads(Path('.local/sources/records.json').read_text())['records']
responses = json.loads(Path('data/manual_model_outputs.json').read_text())
ids = {r['source_id'] for r in responses['responses']}
subset = [r for r in sources if r['source_id'] in ids]
assert len(subset) == 3
Path('.local/manual-source-subset.json').write_text(json.dumps(subset))
PY
python -m knowledge_ops import --input .local/manual-source-subset.json --responses data/manual_model_outputs.json --processor controlled --output .local/manual-reproduced
python -m knowledge_ops export --run .local/manual-reproduced --output .local/manual-reproduced-replay.json
```

This reproduces deterministic processing of recorded model responses, not model generation. Fresh run identifiers, timing and code provenance will differ. The public `demo/manual-replay.json` preserves the original execution metadata, including its dirty working snapshot and runtime file hashes. Full source texts remain local. No model cost or generation latency is claimed; Python import timing excludes inference and manual transfer.
