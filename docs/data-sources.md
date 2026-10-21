# Real company disclosures: provenance and access

## Source

SEC EDGAR public submissions metadata and the referenced issuer-submitted Form 8-K primary documents. Official access documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces . Public data endpoints require no authentication or API key. This does not mean an application LLM API is included.

## Development sampling

Fixed issuers: Microsoft (CIK 789019), Apple (320193), JPMorgan Chase (19617), Visa (1403161), NVIDIA (1045810). For each, select the three most recent Form 8-K filings dated on or before 2026-10-20 from the recent submissions response. Preserve failed selections without choosing easier replacements. Selection uses dates and form, not model success or desired event labels. Resulting class imbalance will be reported. A Form 8-K is not itself a classification label for earnings.

`data/dev_manifest.json` records the actual selected accession numbers, metadata response hash, canonical primary-document URL, retrieval status, raw document and extracted-text hashes, retrieval time and size. A future adapter must consume the frozen accession numbers rather than silently refreshing the sample. Source content may change or become inaccessible; hashes detect differences but do not guarantee availability.

## Retrieval and text preparation

Source acquisition is performed in ChatGPT Work with Python standard-library HTTP access, a descriptive User-Agent naming this public project, at most one new request per 1.05 seconds, 25-second request timeout and no automatic retries. Raw HTML and metadata responses remain local under ignored `.local/sources/`.

The initial extraction uses HTMLParser, omits script/style/inline-XBRL header contents and collapses whitespace. This is a preliminary text view, not a claim of perfect visible-text extraction. Tables, document headers and exhibit references may need dedicated treatment. Text spans in later records must refer to the precise recorded extraction version and hash. Inputs over the planned 50,000-byte limit are flagged rather than silently truncated. A primary 8-K can reference an earnings exhibit without containing all the underlying financial figures; missing exhibit information must not be invented.

## Rights and privacy

Issuer-authored material is not assumed to be public domain merely because it is accessible through EDGAR. Full HTML and extracted prose are excluded from git. The public repository contains source metadata, hashes and subsequently factual derived results; only minimal necessary evidence snippets should be considered for a public replay, with source links and a source-specific publication review. No blanket license over issuer documents is asserted. Retrieval records are not a formal legal opinion or compliance certification.

No user attachments, private gateway content, banking/medical details or credentials are part of this corpus. Future external model calls would process public disclosure content only and require an approved model-access path.

## Evaluation boundaries

These 15 source documents are development material. SEC `items` metadata can aid provisional annotation but is not a substitute for source review and must not become leaked labels in model input. Ground truth, semantic-support annotations and owner review are not yet completed. No accuracy, cost saving, production-readiness or model-improvement result follows from successful source acquisition. No held-out documents have been selected or evaluated. Synthetic adversarial cases will be separately labeled and scored.

## Observed acquisition result — 21 October 2026

15 of 15 selected primary documents were downloaded successfully, three per issuer, with no substituted records or retrieval errors. Integrity checks recomputed all 15 raw-document and all 15 extracted-text SHA256 hashes, verified unique source IDs, five issuer IDs, the date cutoff and the 50,000-byte input limit. These are source-integrity checks, not application tests or model evaluation. Original documents remain local and ignored.
