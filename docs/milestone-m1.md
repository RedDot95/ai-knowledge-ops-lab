# M1 — Recorded research-operations pipeline

Review date: 24 October 2026. Implementation reviewed at immutable commit `0daed287426bda38785deaabc4e8d5f69473913f`; PR #3 contains the implementation and its historical correction trail. This milestone describes a bounded working intermediate state, not completion of the project.

## What a reviewer can inspect

| Capability | Implemented evidence | Boundary |
|---|---|---|
| Source provenance | 15-entry SEC development manifest; source URLs, extraction version and hashes | Full raw filings stay local; public availability is not a blanket republication licence |
| Input quality | Strict JSON keys/types, IDs, date/hash and text-size checks | No claim of validating every possible source feed |
| Processing | Deterministic rules baseline and direct/controlled response import | Import paths do not call an LLM API |
| Evidence validation | Exact quote offsets, canonical input hash, retained model envelopes | Matching a quote does not prove that a financial interpretation is correct |
| Human review | Input/output/revision binding and append-only local decision log | No enterprise identity/access control or tamper-proof storage |
| Evaluation | Missing/invalid/duplicate output handling; fixed-taxonomy scorecard | Labels unreviewed; exact-value and semantic-support annotation incomplete |
| Presentation | Separate committed 15-record rules and 3-record AI-assisted replays | Recorded outputs, not live inference or a model comparison |

## Verification

- Fresh local run: `python -m unittest discover -s tests -v` — **32 tests, OK**, 24 October 2026, Python 3.12.14.
- Existing CI on the same implementation SHA: [run 39656453229](https://github.com/RedDot95/ai-knowledge-ops-lab/actions/runs/39656453229), **success**. Documentation-only follow-up commits have their own CI history in PR #3.
- Existing 21 October evidence: 15 original texts reproduced frozen hashes; rules pipeline/scoring/export completed. The 24 October review reused that acquisition evidence rather than claiming a fresh live SEC fetch.
- The preserved AI envelopes contain three responses; replay contains nine facts with retained evidence spans. No human approval or semantic accuracy is inferred from schema validity.

## Attribution

Mathias Steinbach defined the problem, requirements and real-source direction. Copilot generated the initial implementation. ChatGPT Work reviewed and corrected code, added regression coverage and prepared the recorded AI extraction and documentation. Git commit author fields alone do not distinguish manually written code from AI-assisted changes. The owner has not independently approved the source annotations; the automation review is not a substitute for that annotation work.

## Next milestones

1. Review development labels and annotate exact values plus atomic-claim support.
2. Model legitimate multi-tranche events instead of flagging every repeated field as contradictory; preserve conservative review routing until verified.
3. Freeze an untouched holdout and run an isolated direct/controlled comparison with complete model provenance.
4. Add an optional model adapter only after cost and evaluation requirements are defined.

No production, client delivery, model-quality benchmark or completed enterprise deployment is claimed.
