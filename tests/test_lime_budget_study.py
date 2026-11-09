import unittest
import numpy as np
import pandas as pd

from run_lime_budget_study import K, METHODS, deletion_rows, group_endpoints, holm, stable_seed, summarize_contrast


class DummyModel:
    def predict_proba(self, values):
        value = np.asarray(values).sum(axis=1) / 20
        return np.column_stack([1-value, value])


class LimeBudgetStudyTests(unittest.TestCase):
    def test_group_weighting_and_missing_pair_rejection(self):
        rows = [dict(method=method, source_test_index=i, connection_group=group, k=k,
                     probability_drop=value if method == "TreeSHAP_saved" else 0)
                for i, group, value in [(0, "a", 1), (1, "a", 1), (2, "b", -1)]
                for method in METHODS for k in K]
        frame = pd.DataFrame(rows)
        self.assertEqual(group_endpoints(frame).TreeSHAP_saved.mean(), 0)
        with self.assertRaisesRegex(ValueError, "Incomplete|Unmatched"):
            group_endpoints(frame.iloc[1:])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            group_endpoints(pd.concat([frame, frame.iloc[:1]]))

    def test_absolute_ranking_and_mask_budgets(self):
        result = deletion_rows(DummyModel(), np.asarray([1., 2., 3.]), 1, np.zeros(3),
                               np.asarray([.1, -.9, .2]), "test")
        self.assertEqual([row["k"] for row in result], list(K))
        self.assertAlmostEqual(result[0]["probability_drop"], .1)
        self.assertAlmostEqual(result[-1]["probability_drop"], .3)

    def test_two_sided_sign_test_ties_and_holm(self):
        self.assertAlmostEqual(summarize_contrast([1]*6, 42)["sign_two_sided_p"], .03125)
        self.assertEqual(summarize_contrast([0, 1e-14], 42)["sign_two_sided_p"], 1.)
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])
        self.assertEqual(stable_seed("d", "t", 1), stable_seed("d", "t", 1))
        self.assertNotEqual(stable_seed("d", "t", 1), stable_seed("d", "t", 2))
        with self.assertRaises(ValueError):
            summarize_contrast([1, np.nan], 42)


if __name__ == "__main__":
    unittest.main()
