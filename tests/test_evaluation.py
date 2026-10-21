from __future__ import annotations

import unittest

from knowledge_ops.evaluate import evaluate_run
from knowledge_ops.export import export_replay
import tempfile
from pathlib import Path


class ReviewRegressionTests(unittest.TestCase):
    def test_semantic_error_counted_on_rejected_record(self):
        truth={'records':[{'split':'dev','source_id':'s','event_type':'earnings','expected_values':{}}]}
        record={'source_id':'s','event_type':'earnings','facts':[],'review_status':'human_rejected','validation_issues':['wrong_amount']}
        self.assertEqual(evaluate_run({'records':[record]},truth,'dev')['critical_record_errors'],1)

    def test_missing_other_is_not_correct(self):
        truth = {'records': [{'split': 'dev', 'source_id': 's', 'event_type': 'other', 'expected_values': {'amount': '100'}}]}
        result = evaluate_run({'records': []}, truth, 'dev')
        self.assertEqual(result['classification_accuracy'], 0)
        self.assertEqual(result['macro_f1_fixed_4_class'], 0)
        self.assertEqual(result['applicable_field_extraction_validity'], 0)

    def test_rejected_or_wrong_values_cannot_score(self):
        truth = {'records': [{'split': 'dev', 'source_id': 's', 'event_type': 'earnings', 'expected_values': {'amount': '100'}}]}
        record = {'source_id': 's', 'event_type': 'earnings', 'facts': [{'field': 'amount', 'value': 'wrong'}], 'review_status': 'rejected', 'validation_issues': ['source_hash_mismatch']}
        result = evaluate_run({'records': [record]}, truth, 'dev')
        self.assertEqual(result['classification_accuracy'], 0)
        self.assertEqual(result['applicable_field_extraction_validity'], 0)

    def test_duplicate_predictions_not_silently_last_wins(self):
        r = {'source_id': 's', 'event_type': 'other', 'facts': [], 'review_status': 'pending_review', 'validation_issues': []}
        t = {'records': [{'split': 'dev', 'source_id': 's', 'event_type': 'other', 'expected_values': {}}]}
        self.assertEqual(evaluate_run({'records': [r, r]}, t, 'dev')['classification_accuracy'], 0)

    def test_replay_uses_actual_processor(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = export_replay({'processor': 'direct', 'run_id': 'r', 'records': [{'source_id': 's'}]}, Path(tmp)/'replay.json')
            self.assertEqual(r['approaches']['direct'], 'Recorded')
            self.assertEqual(r['approaches']['rules'], 'Not run')


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
