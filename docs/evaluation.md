# Evaluation notes

- Development split: 15 real SEC 8-K documents from the frozen manifest.
- Ground truth file (`data/ground_truth.json`) is marked **AI-assisted/unreviewed** and is not owner-approved.
- Metrics are deterministic and computed from recorded outputs; missing or invalid predictions count as failures.
- Macro-F1 uses the fixed taxonomy: `financing`, `earnings`, `leadership_change`, `other`.
- Semantic-support score is **undefined** until separate atomic-claim support annotations are available.
- Synthetic fixtures (`data/robustness.json`) are robustness tests and are excluded from reported real-source metrics.
