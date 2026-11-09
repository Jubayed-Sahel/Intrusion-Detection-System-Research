import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from run_pattern_sensitivity import (explanation_indices, matching_patterns,
                                     validate_contexts, validate_predictive_reference)


class PatternSensitivityTests(unittest.TestCase):
    def test_exact_pattern_membership_ignores_labels_and_preserves_missingness(self):
        train = pd.DataFrame({"number": [1., np.nan, 2.], "category": ["a", "b", None],
                              "Label": ["Benign", "Attack A", "Attack B"], "__group": ["x", "y", "z"]})
        test = pd.DataFrame({"number": [1., np.nan, 2., np.nan, 1.],
                             "category": ["a", "b", pd.NA, "c", "b"],
                             "Label": ["different"] * 5, "__group": ["other"] * 5})
        saved = test.copy(deep=True)
        np.testing.assert_array_equal(matching_patterns(train, test, ["number", "category"]),
                                      [True, True, True, False, False])
        pd.testing.assert_frame_equal(test, saved)
        # Raw predictor equality must not equate a string category with a numeric value.
        np.testing.assert_array_equal(matching_patterns(pd.DataFrame({"x": [1, 2]}),
                                                       pd.DataFrame({"x": ["1", "2"]}), ["x"]),
                                      [False, False])

    def test_context_count_cannot_hide_duplicate_or_wrong_seed(self):
        config = dict(datasets=["dataset"], models={"model": {}}, explanation_model_seeds=[42, 52])
        frame = pd.DataFrame([dict(dataset="dataset", task=task, model="model", model_seed=seed)
                              for task in ["binary", "multiclass"] for seed in [42, 52]])
        validate_contexts(frame, config)
        repeated = pd.concat([frame.iloc[:3], frame.iloc[:1]], ignore_index=True)
        self.assertEqual(len(repeated), len(frame))
        with self.assertRaisesRegex(ValueError, "coverage"):
            validate_contexts(repeated, config)
        wrong_seed = frame.copy()
        wrong_seed.loc[0, "model_seed"] = 99
        with self.assertRaisesRegex(ValueError, "coverage"):
            validate_contexts(wrong_seed, config)

    def test_explanation_row_identity_rejects_fractional_index_and_same_group_wrong_class(self):
        context = SimpleNamespace(dataset="dataset", task="binary", model="model", model_seed=42)
        test = pd.DataFrame({"Label": ["Benign", "Flood"], "__group": ["same", "same"]})
        frame = pd.DataFrame([dict(dataset="dataset", task="binary", model="model", model_seed=42,
                                   source_test_index=0, connection_group="same", actual_class="Normal")])
        np.testing.assert_array_equal(explanation_indices(frame, context, test), [0])
        for column, value, message in [("source_test_index", .5, "finite integers"),
                                       ("source_test_index", 1, "observed class"),
                                       ("source_test_index", -1, "out of bounds"),
                                       ("model_seed", 52, "context identity")]:
            broken = frame.astype({"source_test_index": float})
            broken.loc[0, column] = value
            with self.subTest(column=column, value=value), self.assertRaisesRegex(ValueError, message):
                explanation_indices(broken, context, test)

    def test_predictive_reference_detects_wrong_model_and_supported_label_metric(self):
        reference = pd.DataFrame([dict(dataset="dataset", task="multiclass", model="model", seed=42,
                                        test_rows=10, accuracy=.8, macro_f1_supported_classes=.6,
                                        balanced_accuracy=.7)])
        result = dict(dataset="dataset", task="multiclass", model="model", model_seed=42, n_rows=10,
                      accuracy=.8, macro_f1_fixed_original_test_labels=.6,
                      macro_recall_fixed_original_test_labels=.7)
        validate_predictive_reference(result, reference)
        for changes, message in [({"macro_f1_fixed_original_test_labels": .59}, "reproduce"),
                                 ({"n_rows": 9}, "reproduce"), ({"model_seed": 52}, "missing or duplicated")]:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                validate_predictive_reference({**result, **changes}, reference)


if __name__ == "__main__":
    unittest.main()
