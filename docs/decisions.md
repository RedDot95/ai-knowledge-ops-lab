# Decisions

1. Reused frozen source manifest from commit `104cfef170f90c282cf9fe5a9d90a53ddee502fc` (no resampling).
2. Kept raw SEC documents and full extracted text in ignored local paths (`.local/`) and committed only metadata/derived records.
3. Implemented only deterministic processing plus model-output import; no live model inference.
4. Enforced strict input validation (duplicate keys/IDs, malformed types, date format, >50KB text, hash mismatch).
5. Routed high-risk records to `needs_review` or `rejected` based on deterministic rules.
