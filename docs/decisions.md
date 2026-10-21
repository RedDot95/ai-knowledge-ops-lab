# Decisions

1. Reused frozen source manifest from commit `104cfef170f90c282cf9fe5a9d90a53ddee502fc` (no resampling).
2. Kept raw SEC documents and full extracted text in ignored local paths (`.local/`) and committed only metadata/derived records.
3. Implemented only deterministic processing plus model-output import; no automated inference service. A later in-session assistant demonstration is documented separately.
4. Enforced strict input validation (duplicate keys/IDs, malformed types, date format, >50KB text, hash mismatch).
5. Routed high-risk records to `needs_review` or `rejected` based on deterministic rules.
# Review decisions — 21 October 2026

- Owner: specified the business requirements, real-data direction and authorized one bounded Copilot implementation run.
- Copilot: generated the initial implementation on an isolated Draft PR.
- ChatGPT Work: independently reproduced failures after the original 17 tests passed; corrected them locally and added regression coverage. No second Copilot assignment was started. The attempted in-flight steering message was not delivered by GitHub.
- Assistant review decision: keep model imports explicit and require provenance; never count coding-agent execution as application-model inference.
- Assistant review decision: retain the frozen 15-source selection; repair extraction rather than rewriting expected hashes to fit broken output.
- Assistant review decision: publish actual deterministic replay and a clearly separated in-session AI demonstration; leave incomplete extraction/support metrics undefined and keep all LLM/holdout performance claims open.
- Owner technical review, annotation review, target protection activation, Pages deployment and exact-HEAD merge remain open. These assistant decisions are not presented as owner expertise or independent human approval.

- Work continuation: use the already running assistant for three real-source extraction examples, avoiding a new API dependency. Preserve original drafts and raw envelopes; identify manual transfer and unavailable model settings. This is a demonstration, not an independently evaluated B/C experiment.
- Observed schema limitation: multiple legitimate note amounts trigger the single-field contradiction heuristic. Keep the warning and review requirement visible; defer a tranche-aware schema change until separately specified and tested.
