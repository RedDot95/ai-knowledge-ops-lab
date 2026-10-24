# Development label review — 24 October 2026

All 15 frozen SEC primary documents were fetched again with the existing adapter: 15 records, zero errors, and 15/15 canonical text hashes identical to `data/dev_manifest.json`. Raw filings stay in ignored `.local/` storage. The [review ledger](../data/dev_label_review_2026-10-24.json) records every source URL, exact input hash, prior label, source-checked label and reasoning.

ChatGPT Work performed this source review under owner direction. This is an additional AI-assisted review pass, not independent human validation. `ground_truth_status` remains `AI-assisted/unreviewed`, and owner approval remains pending. No held-out source was selected or inspected.

## Classification contract

Classify the substantive event in the frozen primary document, not merely its SEC item number or boilerplate. `financing` includes capital raising and disclosed credit/guarantee obligations; it excludes an acquisition merely stating a purchase price. `leadership_change` includes director departures and appointments as well as executive transitions. Earnings presentations explicitly reviewing financial results count as `earnings`; a segment-reporting change alone is `other`. Mixed filings use the main announced event, with secondary events noted in the ledger. These are explicit development conventions, not a universally validated taxonomy.

## Two source-supported corrections

| Source suffix | Before | After | Reason |
|---|---|---|---|
| JPMorgan 0001193125-26-426704 | other | financing | Primary body describes closing three public note offerings; Item 8.01 does not change the economic subject. |
| JPMorgan 0001628280-26-065616 | other | earnings | Primary body explicitly describes an investor presentation reviewing quarterly earnings. |

The remaining 13 classification labels were retained after primary-body review. The ledger explains potentially ambiguous cases: board non-reelection, litigation escrow, bylaw amendment, mixed earnings/dividend disclosure, acquisition agreement and contingent guaranties. Review decisions were based on source content, not on the rules processor's predictions.

## Extraction remains incomplete

The previous `expected_fields` are provisional and were preserved rather than silently certified. Several earnings primary documents only point to exhibits containing the results. Requiring an earnings amount from those primary-only inputs is unsupported. Visa's mixed filing contains a dividend amount, which must not be confused with earnings. JPMorgan contains several financial quantities; NVIDIA's contingent guarantee cap is not expenditure. The extraction contract must specify the quantity, period, unit, role and multi-value behavior before exact expected values can be approved.

No exact-value, critical-error or semantic-support metric is made valid by this classification review. Historical replay/evaluation artifacts are preserved unchanged and predate these corrections. Rerunning evaluation against the updated development labels produces a different diagnostic experiment; it is not a model-quality benchmark or evidence of improvement in the processor. No new API integration, model experiment or cost was introduced.

## Reproduce

```sh
python -m knowledge_ops fetch-sec --manifest data/dev_manifest.json --output .local/label-review-sources
python -m unittest discover -s tests -v
```

Compare each source's canonical text SHA-256 with the frozen manifest and review ledger. The ledger deliberately stores no full issuer text. Next: owner review of these conventions and labels, then bounded exact-value/semantic-support annotation with explicit exhibit scope.
