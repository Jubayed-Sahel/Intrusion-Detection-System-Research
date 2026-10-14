import unittest

import numpy as np
import pandas as pd

from src.xai_ids.benchmark import (
    TabularPreprocessor,
    clean_unsw_partitions,
    predictive_metrics,
    bootstrap_mean_ci,
    nearest_neighbor_stability,
    safe_cosine,
)
from src.xai_ids.transparency import evidence_decision, local_deletion_evidence
from sklearn.ensemble import RandomForestClassifier


class BenchmarkUnitTests(unittest.TestCase):
    def test_batched_alert_controls_match_serial_predictions(self):
        rng = np.random.default_rng(7)
        features = rng.normal(size=(80, 5))
        labels = (features[:, 0] + features[:, 1] > 0).astype(int)
        model = RandomForestClassifier(n_estimators=8, max_depth=3, random_state=7, n_jobs=1).fit(features, labels)
        row, baseline = features[0], np.zeros(5)
        prediction = int(model.predict(row.reshape(1, -1))[0])
        attribution = np.array([5., 4., 3., 2., 1.])
        original = model.predict_proba(row.reshape(1, -1))[0, prediction]
        def serial_score(ranking):
            drops = []
            for k in (1, 3, 5, 10):
                masked = row.copy()
                selected = ranking[:min(k, len(row))]
                masked[selected] = baseline[selected]
                drops.append(original - model.predict_proba(masked.reshape(1, -1))[0, prediction])
            return np.mean(drops)
        top = serial_score(np.arange(5))
        bottom = serial_score(np.arange(5)[::-1])
        control_rng = np.random.default_rng(42)
        controls = np.array([serial_score(control_rng.permutation(5)) for _ in range(20)])
        result = local_deletion_evidence(model, row, attribution, prediction, baseline, [1, 3, 5, 10], 20, 42)
        self.assertAlmostEqual(result["top_deletion_score"], top)
        self.assertAlmostEqual(result["bottom_deletion_score"], bottom)
        self.assertAlmostEqual(result["random_mean_deletion_score"], controls.mean())
        expected_p = (1 + np.sum(controls >= top - 1e-12)) / 21
        self.assertEqual(result["local_empirical_one_sided_p"], expected_p)
        with self.assertRaises(ValueError):
            local_deletion_evidence(model, row, attribution, prediction, baseline, [1], 0, 42)

    def test_overlap_cleaning_excludes_conflicting_single_target_labels(self):
        train = pd.DataFrame({"feature": [1, 2], "Label": ["BENIGN", "AttackA"]})
        test = pd.DataFrame({"feature": [1, 3], "Label": ["AttackB", "AttackA"]})
        _, retained, audit = clean_unsw_partitions(train, test, "Label", "Label")
        self.assertEqual(retained.feature.tolist(), [3])
        self.assertEqual(retained.Label.tolist(), ["AttackA"])
        self.assertEqual(audit["cross_partition_feature_overlaps_removed_from_test"], 1)

    def test_unsw_cleaning_removes_duplicates_and_cross_partition_vectors(self):
        train = pd.DataFrame(
            {
                "feature_a": [1, 1, 2],
                "feature_b": ["x", "x", "y"],
                "label": [1, 1, 0],
                "attack_cat": ["Attack", "Attack", "Normal"],
            }
        )
        test = pd.DataFrame(
            {
                "feature_a": [1, 1, 3, 3],
                "feature_b": ["x", "x", "z", "z"],
                "label": [0, 0, 1, 1],
                "attack_cat": ["Normal", "Normal", "Attack", "Attack"],
            }
        )
        clean_train, clean_test, audit = clean_unsw_partitions(
            train, test, "label", "attack_cat"
        )
        self.assertEqual(len(clean_train), 2)
        self.assertEqual(len(clean_test), 1)
        self.assertEqual(audit["training_exact_duplicates_removed"], 1)
        self.assertEqual(audit["testing_exact_duplicates_removed"], 2)
        self.assertEqual(audit["cross_partition_feature_overlaps_removed_from_test"], 1)
        self.assertEqual(clean_test.iloc[0]["feature_a"], 3)

    def test_binary_security_metrics_use_named_attack_class(self):
        y_true = np.array([0, 0, 1, 1])  # classes are [Attack, Normal]
        y_pred = np.array([0, 1, 0, 1])
        probabilities = np.array([[0.9, 0.1], [0.4, 0.6], [0.7, 0.3], [0.1, 0.9]])
        metrics, _, _ = predictive_metrics(
            y_true, y_pred, probabilities, ["Attack", "Normal"]
        )
        self.assertAlmostEqual(metrics["false_positive_rate"], 0.5)
        self.assertAlmostEqual(metrics["false_negative_rate"], 0.5)
        self.assertGreater(metrics["pr_auc"], 0.8)

    def test_transparency_evidence_decision_is_conservative(self):
        self.assertEqual(
            evidence_decision(True, 0.2, 0.04)[0], "SUPPORTED_FOR_THIS_ALERT"
        )
        self.assertEqual(evidence_decision(True, 0.2, 0.06)[0], "REVIEW_REQUIRED")
        self.assertEqual(evidence_decision(False, 0.2, 0.01)[0], "UNSUPPORTED")

    def test_training_only_preprocessor_handles_unseen_category(self):
        train = pd.DataFrame({"numeric": [1.0, np.nan, 3.0], "category": ["a", "b", "a"]})
        test = pd.DataFrame({"numeric": [np.inf], "category": ["unseen"]})
        prep = TabularPreprocessor(["numeric", "category"]).fit(train)
        transformed = prep.transform(test)
        self.assertEqual(transformed.shape, (1, 2))
        self.assertEqual(transformed[0, 0], 2.0)
        self.assertEqual(transformed[0, 1], -1.0)

    def test_cosine_and_neighbor_stability_are_bounded(self):
        self.assertEqual(safe_cosine(np.zeros(2), np.zeros(2)), 1.0)
        x = np.array([[0.0, 0.0], [0.1, 0.0], [3.0, 3.0], [3.1, 3.0]])
        predicted = np.array([0, 0, 1, 1])
        attributions = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])
        rows = nearest_neighbor_stability(x, predicted, attributions)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(-1.0 <= row["cosine_similarity"] <= 1.0 for row in rows))
        self.assertTrue(all(0.0 <= row["top5_jaccard"] <= 1.0 for row in rows))

    def test_bootstrap_interval_contains_constant_mean(self):
        mean, low, high = bootstrap_mean_ci(np.ones(12) * 0.25, seed=42, repetitions=100)
        self.assertEqual(mean, 0.25)
        self.assertEqual(low, 0.25)
        self.assertEqual(high, 0.25)


if __name__ == "__main__":
    unittest.main()
