import unittest
import numpy as np
import pandas as pd
from run_explanation_robustness import group_differences, sensitivity, holm


class RobustnessTests(unittest.TestCase):
    def test_outlier_reverses_mean(self):
        result = sensitivity([10, -1, -1, -1])
        self.assertTrue(result["single_group_can_reverse_mean"])
        self.assertEqual(result["loo_mean_min"], -1)

    def test_ties_and_exact_sign_test(self):
        self.assertEqual(sensitivity([0, 1e-14])["sign_two_sided_p"], 1)
        self.assertAlmostEqual(sensitivity([1]*6)["sign_two_sided_p"], .03125)
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])

    def test_pairing_and_group_weight(self):
        rows = [dict(control="top", explainer=e, source_test_index=i,
                     connection_group=g, k=k, probability_drop=v if e == "TreeSHAP" else 0)
                for i, g, v in [(0, "a", 1), (1, "a", 1), (2, "b", -1)]
                for e in ["TreeSHAP", "LIME"] for k in [1, 3]]
        frame = pd.DataFrame(rows)
        self.assertEqual(group_differences(frame, [1, 3]).mean(), 0)
        with self.assertRaisesRegex(ValueError, "Incomplete|Unmatched"):
            group_differences(frame.iloc[1:], [1, 3])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            group_differences(pd.concat([frame, frame.iloc[:1]]), [1, 3])
