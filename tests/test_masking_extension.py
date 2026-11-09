import unittest

import numpy as np
import pandas as pd

from run_masking_extension import (BUDGETS, feature_distances, group_differences,
                                   holm, masked_rows, nearest_donors, summarize,
                                   training_scale)


class MaskingExtensionTests(unittest.TestCase):
    def test_joint_donor_copy_preserves_retained_predictors(self):
        row = np.array([10., 20., 30.])
        donors = np.array([[1., 2., 3.], [4., 5., 6.]])
        masked = masked_rows(row, [0, 2], donors)
        np.testing.assert_array_equal(masked, [[1, 20, 3], [4, 20, 6]])
        np.testing.assert_array_equal(row, [10, 20, 30])

    def test_nearest_selection_ignores_removed_predictors(self):
        pool = np.array([[0., 1000.], [1., 0.], [2., -1000.]])
        distances = feature_distances(pool, np.array([0., 0.]), np.ones(2), [])
        indices, _ = nearest_donors(distances, [0], n=1)
        np.testing.assert_array_equal(indices, [0])
        pool[:, 1] = [0, 1000, 5000]
        changed = feature_distances(pool, np.array([0., 0.]), np.ones(2), [])
        np.testing.assert_array_equal(nearest_donors(changed, [0], n=1)[0], indices)
        with self.assertRaisesRegex(ValueError, "retained"):
            nearest_donors(distances, [], n=1)

    def test_categorical_mismatch_and_finite_training_scale(self):
        scale = training_scale(np.array([[0., 1.], [0., 3.], [0., 5.]]))
        np.testing.assert_array_equal(scale, [1., 2.])
        distances = feature_distances(np.array([[100., 3.], [0., 5.]]), np.array([0., 1.]), scale, [1])
        np.testing.assert_array_equal(distances, [[1, 1], [0, 1]])

    def test_equal_connection_weight_and_incomplete_pairing(self):
        rows = [dict(scheme="test", explainer=e, source_test_index=i, connection_group=g,
                     k=k, probability_drop=v if e == "TreeSHAP" else 0)
                for i, g, v in [(0, "a", 1), (1, "a", 1), (2, "b", -1)]
                for e in ["TreeSHAP", "LIME"] for k in BUDGETS]
        frame = pd.DataFrame(rows)
        self.assertEqual(group_differences(frame).mean(), 0)
        with self.assertRaisesRegex(ValueError, "Incomplete|Unmatched"):
            group_differences(frame.iloc[1:])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            group_differences(pd.concat([frame, frame.iloc[:1]]))

    def test_two_sided_sign_ties_and_holm(self):
        result = summarize([1., 1., 1., 1., 1., 1., 1e-14], 4)
        self.assertEqual(result["tied_groups"], 1)
        self.assertAlmostEqual(result["sign_two_sided_p"], .03125)
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])
        self.assertEqual(summarize([0., 0.], 4)["sign_two_sided_p"], 1.)
        with self.assertRaises(ValueError):
            summarize([np.nan, 1.], 4)


if __name__ == "__main__":
    unittest.main()
