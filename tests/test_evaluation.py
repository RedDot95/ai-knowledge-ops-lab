from __future__ import annotations

import unittest

from knowledge_ops.evaluate import evaluate_run


class EvaluationTests(unittest.TestCase):
    def test_zero_claim_denominator_is_undefined_not_100(self) -> None:
        run_payload = {
            "records": [
                {
                    "source_id": "s-1",
                    "event_type": "other",
                    "facts": [],
                    "validation_issues": [],
                    "review_status": "pending_review",
                }
            ]
        }
        truth_payload = {
            "records": [{"split": "dev", "source_id": "s-1", "event_type": "other", "expected_fields": []}],
            "ground_truth_status": "AI-assisted/unreviewed",
        }
        result = evaluate_run(run_payload, truth_payload, "dev")
        self.assertIsNone(result["applicable_field_extraction_validity"])
        self.assertIsNone(result["semantic_support_rate"])

    def test_incomplete_predictions_count_as_failures(self) -> None:
        run_payload = {
            "records": [
                {
                    "source_id": "s-1",
                    "event_type": "earnings",
                    "facts": [],
                    "validation_issues": [],
                    "review_status": "pending_review",
                }
            ]
        }
        truth_payload = {
            "records": [
                {"split": "dev", "source_id": "s-1", "event_type": "earnings", "expected_fields": []},
                {"split": "dev", "source_id": "s-2", "event_type": "other", "expected_fields": []},
            ]
        }
        result = evaluate_run(run_payload, truth_payload, "dev")
        self.assertEqual(result["missing_or_invalid_outputs"], 1)

    def test_mock_records_are_excluded(self) -> None:
        run_payload = {
            "records": [
                {
                    "source_id": "mock-01",
                    "event_type": "other",
                    "facts": [],
                    "validation_issues": [],
                    "review_status": "pending_review",
                    "provenance": {"mock": True},
                }
            ]
        }
        truth_payload = {"records": [{"split": "dev", "source_id": "mock-01", "event_type": "other", "expected_fields": []}]}
        result = evaluate_run(run_payload, truth_payload, "dev")
        self.assertEqual(result["excluded_mock_records"], 1)
        self.assertEqual(result["missing_or_invalid_outputs"], 1)


if __name__ == "__main__":
    unittest.main()
