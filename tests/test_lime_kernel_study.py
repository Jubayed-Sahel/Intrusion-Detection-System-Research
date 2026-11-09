import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from run_lime_kernel_study import METHODS, SharedNeighborhood, audit_explanation, group_endpoints


class LimeKernelStudyTests(unittest.TestCase):
    def test_cache_shares_only_identical_neighborhoods(self):
        calls = []

        def predictor(rows):
            calls.append(len(rows))
            return np.tile([.25, .75], (len(rows), 1))

        rows = np.ones((3500, 2))
        cache = SharedNeighborhood(SimpleNamespace(predict_proba=predictor), rows[0], [.25, .75])
        result = cache(rows)
        result[0] = [.1, .9]  # Caller cannot mutate the cached classifier output.
        np.testing.assert_array_equal(cache(rows)[0], [.25, .75])
        self.assertEqual(calls, [3500])
        wrong = rows.copy()
        wrong[20, 0] = 0
        with self.assertRaisesRegex(ValueError, "changed the sampled neighborhood"):
            cache(wrong)

    def test_local_prediction_must_reconstruct_for_the_requested_class(self):
        explainer = SimpleNamespace(discretizer=object(), categorical_features=[0, 1],
            scaler=SimpleNamespace(mean_=np.zeros(2), scale_=np.ones(2)))
        exp = SimpleNamespace(local_exp={2: [(1, .3), (0, -.1)]}, intercept={2: .25},
            local_pred=np.array([.45]), score=.55)
        vector, intercept, predicted, r2, reconstructed = audit_explanation(explainer, exp, 2, 2)
        np.testing.assert_array_equal(vector, [-.1, .3])
        self.assertAlmostEqual(predicted, reconstructed)
        self.assertEqual((intercept, r2), (.25, .55))
        with self.assertRaisesRegex(ValueError, "requested classifier output"):
            audit_explanation(explainer, exp, 0, 2)
        exp.local_pred[0] = .7
        with self.assertRaises(AssertionError):
            audit_explanation(explainer, exp, 2, 2)

    def test_duplicate_or_incomplete_record_panels_fail(self):
        frame = pd.DataFrame([dict(method=method, source_test_index=i, k=k,
            connection_group="common" if i < 99 else "singleton", probability_drop=.1 if i < 99 else .9)
            for method in METHODS for i in range(100) for k in (1, 3, 5, 10)])
        grouped = group_endpoints(frame)
        self.assertAlmostEqual(grouped[METHODS[0]].mean(), .5)
        with self.assertRaisesRegex(ValueError, "Incomplete masking budgets"):
            group_endpoints(frame.iloc[:-1])
        with self.assertRaisesRegex(ValueError, "duplicated"):
            group_endpoints(pd.concat([frame, frame.iloc[:1]], ignore_index=True))


if __name__ == "__main__":
    unittest.main()
