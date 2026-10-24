# Architecture

This deterministic MVP has five stages:

1. **Source retrieval (`fetch-sec`)**: consume the frozen `data/dev_manifest.json`, fetch SEC primary-document URLs at a minimum 1.05 second interval with a descriptive User-Agent, cache local raw/text files under `.local/sources`, and write validated pipeline inputs to `.local/sources/records.json`.
2. **Rule baseline (`run --processor rules`)**: classify each input into `financing|earnings|leadership_change|other`, extract deterministic facts/evidence spans, and assign review routing (`pending_review`, `needs_review`, `rejected`).
3. **Auditable import (`import --processor direct|controlled`)**: ingest real model outputs only, retain raw response metadata, enforce schema/evidence/hash checks, and route failures/review states deterministically.
4. **Evaluation (`evaluate`)**: compute fixed-four-class macro-F1, schema validity, extraction validity, unsupported fields, critical errors, review/reject rates, and missing-output failures; semantic support is explicitly undefined without atomic-claim labels.
5. **Static replay export (`export`)**: generate a JSON payload consumed by `demo/` with the banner "Recorded pipeline results — no live model processing".

No application model API calls are performed by this MVP.
