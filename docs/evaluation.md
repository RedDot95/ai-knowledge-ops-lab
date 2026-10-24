# Evaluation notes

- Development split: 15 real SEC 8-K documents from the frozen manifest.
- Ground truth file (`data/ground_truth.json`) is marked **AI-assisted/unreviewed** and is not owner-approved.
- Metrics are deterministic and computed from recorded outputs; missing or invalid predictions count as failures.
- Macro-F1 uses the fixed taxonomy: `financing`, `earnings`, `leadership_change`, `other`.
- Semantic-support score is **undefined** until separate atomic-claim support annotations are available.
- Synthetic fixtures (`data/robustness.json`) are robustness tests and are excluded from reported real-source metrics.
# Observed implementation failures and correction evidence

The initial Copilot commit `7b33d835079bd6bf829facdd6685cd5a2b56fc73` passed its original 17 tests but failed independent review. These are observed software defects, not observed LLM failures.

| Observed defect | Cause and correction | Verification |
|---|---|---|
| 15/15 frozen-source text hashes mismatched | Newline-based HTML extraction differed from the original space-normalized algorithm. Restore the exact extraction version without altering the manifest. | All 15 original raw documents reproduce frozen hashes; live `fetch-sec` returns 15 records, zero errors. |
| Missing answers received classification credit | Missing/invalid predictions were mapped to the legitimate `other` class. Use an invalid sentinel; rejected and duplicate predictions cannot score correct. | Empty predictions against an `other` truth now score zero; missing extraction slots remain in denominators. |
| Wrong-hash imports could become reviewable | Later warnings overwrote a hard rejection. Preserve raw envelopes and declared hashes; accumulate rejection monotonically; strictly validate types. | Regressions cover combined wrong hashes/warnings, null amounts, dictionary identifiers and malformed tags/currency. |
| Deterministically rejected entries could regain approval | Human routing replaced the only rejection flag. Bind reviews to the actual input/full output/revision and preserve hard rejection independently. | Regression verifies `request_changes` followed by `approve` cannot launder a hard rejection; changed input/summary/revision invalidates approval. |
| Replay attributed imported records to rules | Export assumed any nonempty run was rules. Derive attribution from actual processor. | Direct-import replay reports direct Recorded and rules Not run. |

The corrected local suite has 32 tests. It includes an actual subprocess test of persisted manual review and metadata. Ground truth remains AI-assisted/unreviewed. An exact-value extraction score is undefined until expected values are annotated; field presence is not extraction correctness. Critical-error measurements remain undefined without critical-error annotations. A schema check is not a semantic-support check.

Development rules processing and scoring were executed on all 15 downloaded sources. The baseline's classification is weak, and provisional labels require substantive source review (for example debt offerings and investor earnings presentations). Do not interpret this diagnostic scoring as a verified benchmark or tune on the future held-out set. A three-source in-session assistant demonstration was subsequently imported through the controlled path (see `manual-model-session.md`); no isolated B/C comparison or held-out tests have occurred. Public source records and quoted spans are not evidence of production readiness.

Run artifacts record input/prompt hashes, code revision, dirty state and runtime code-file hashes. A dirty revision is explicitly marked; file hashes identify the actual executed source rather than pretending that the base commit alone describes modified code. Timing covers local Python processing/import and excludes manual transfer or model generation. No model API cost is measured.

## Source review follow-up on 24 October 2026

[Review ledger and rationale](label-review-2026-10-24.md): all 15 frozen primary documents fetched again, zero retrieval errors and 15 matching text hashes. Two development classification labels were corrected after substantive source review. The 32-test regression suite passed after the data/documentation changes. This remains AI-assisted review with owner approval pending; historical replay metrics were not rewritten and no validated benchmark is claimed.
