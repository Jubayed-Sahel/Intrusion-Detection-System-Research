import unittest

from run_extended_validation import scores
from src.xai_ids.extended_validation_results import load_extended


class ExtendedValidationTests(unittest.TestCase):
    def test_unsupported_training_class_still_counts_in_test_macro_f1(self):
        result = scores([[9, 0], [1, 0]], ["known", "new"])
        self.assertAlmostEqual(result["macro_f1"], 9 / 19)

    def test_complete_results_replay_and_scope(self):
        coverage, folds, external = load_extended()
        self.assertEqual(len(folds), 64)
        self.assertEqual(coverage.eligible.sum(), 37_941_390)
        self.assertTrue(external[external.test.eq("OCPP")].test_rows.eq(4415).all())
