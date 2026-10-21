# AI Knowledge Operations Lab

**Applied AI · Research Operations · Data Quality · LLM Evaluation**

This lab is being built to turn public company disclosures into structured, source-linked research knowledge with explicit quality checks and human review.

**Status: Planned — 15 real development disclosures retrieved.** No working application, application-model evaluation, passing application CI, deployed demo or recruiting-ready claim yet.

## Business task

A research team needs to identify company events, extract facts and their evidence, and route ambiguous or conflicting information for review. The intended workflow is: public disclosures → classification and extraction → deterministic checks → human review → recorded knowledge output. It does not provide investment advice.

## What exists now

- A bounded [implementation specification](https://github.com/RedDot95/ai-knowledge-ops-lab/issues/1).
- A real SEC EDGAR development-source manifest: 15 successfully retrieved Form 8-K documents from five companies, with accession numbers and verified raw/text hashes.
- A documented sampling procedure and separation of real source documents from future synthetic stress tests.

See [data provenance and access](docs/data-sources.md). This branch prepares data only; it does not implement the application.

## Planned comparison

| Approach | State |
|---|---|
| A: rule baseline | Not implemented |
| B: direct LLM extraction | Not run |
| C: controlled LLM extraction and validation | Not run |

The target evaluation uses 15 development documents, 20 procedurally held-out documents and 10 separate synthetic robustness cases. The held-out set has not been selected or tested. Metrics will only be published after actual execution; source retrieval is not model evaluation.

## Contribution and limits

Mathias Steinbach supplied the business requirements, career objectives and decision to use real public company disclosures. ChatGPT proposed architecture and prepared source acquisition. Copilot implementation is pending separate execution authorization. Owner technical review and annotation review have not yet occurred. No claim is made that Mathias independently wrote all code.

Public data access is separate from application-model access. SEC public data endpoints do not require an API key. No paid model API, secret, additional billing plan, automatic agent execution or merge is configured by this data-preparation branch. Target branch protections are not yet configured and are not inherited from another repository.
