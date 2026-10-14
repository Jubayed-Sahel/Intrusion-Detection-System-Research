import io
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from run_recent_benchmark import group_comparisons, holm
from src.xai_ids.recent_paper import manuscript_identity
from src.xai_ids.transparency import _benchmark_context
from verify_recent_benchmark import _contexts, _inference_matches, read_source_csv, source_basename
from scipy.stats import wilcoxon


class RecentIntegrityTests(unittest.TestCase):
    def test_inference_checks_allow_numerical_error_but_keep_group_counts_exact(self):
        expected = pd.DataFrame({"n_pairs": [42], "ci_low": [.1], "wilcoxon_one_sided_p": [.001],
                                 "inference_unit": ["explained connection-group mean"], "insufficient_groups": [False]})
        actual = expected.copy()
        actual["ci_low"] = np.nextafter(actual.ci_low, np.inf)
        _inference_matches(actual, expected, ["n_pairs", "ci_low", "wilcoxon_one_sided_p"])
        actual["n_pairs"] = 43
        with self.assertRaisesRegex(AssertionError, "n_pairs"):
            _inference_matches(actual, expected, ["n_pairs", "ci_low", "wilcoxon_one_sided_p"])

    def test_checkpoint_csv_parsing_preserves_near_ties_for_signed_rank_test(self):
        values = np.tile(np.array([.3, -.30000000000000004, .2, .2, .1, .1]), 10)
        csv = pd.DataFrame({"difference": values}).to_csv(index=False)
        reconstructed = read_source_csv(io.StringIO(csv)).difference.to_numpy()
        np.testing.assert_array_equal(values, reconstructed)
        original_p = wilcoxon(values, alternative="greater").pvalue
        reconstructed_p = wilcoxon(reconstructed, alternative="greater").pvalue
        self.assertEqual(original_p, reconstructed_p)
        # The standard parser merges the oppositely signed near-ties and
        # changes their ranks. Do not recompute inference from that aggregate.
        rounded = pd.read_csv(io.StringIO(csv)).difference.to_numpy()
        self.assertNotEqual(original_p, wilcoxon(rounded, alternative="greater").pvalue)

    def test_windows_source_snapshot_names_are_portable_to_linux_ci(self):
        self.assertEqual(source_basename(r"C:\Users\User\Desktop\498R\run_recent_benchmark.py"), "run_recent_benchmark.py")
        self.assertEqual(source_basename("src/xai_ids/recent_data.py"), "recent_data.py")

    def test_connection_duplication_cannot_change_inferential_weight(self):
        rows = []
        for connection, difference in enumerate([0.8, -0.4, 0.1, 0.2, -0.3, 0.2]):
            for explainer, score in (("TreeSHAP", difference), ("LIME", 0.0)):
                for control in ("top", "random", "bottom"):
                    for k in (1, 3):
                        rows.append({"dataset": "synthetic", "task": "binary", "model": "example",
                                     "explainer": explainer, "connection_group": f"group-{connection}",
                                     "source_test_index": connection, "control": control, "k": k,
                                     "probability_drop": score if control == "top" else 0.0})
        original = pd.DataFrame(rows)
        # Overrepresent one connection by 20 packets. Its inferential weight
        # must remain identical to each of the five other connections.
        duplicated = pd.concat([original] + [original[original.connection_group.eq("group-0")]] * 19)
        pairs, controls = group_comparisons(original, 42)
        repeated_pairs, repeated_controls = group_comparisons(duplicated, 42)
        pd.testing.assert_frame_equal(pairs, repeated_pairs)
        pd.testing.assert_frame_equal(controls, repeated_controls)
        self.assertEqual(pairs.n_pairs.iloc[0], 6)
        self.assertAlmostEqual(pairs.mean_difference_shap_minus_lime.iloc[0], 0.1)

    def test_global_holm_adjustment_uses_whole_family(self):
        np.testing.assert_allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_context_coverage_rejects_duplicate_replacing_missing_context(self):
        frame = pd.DataFrame({"seed": [42, 42]})
        with self.assertRaisesRegex(AssertionError, "Duplicate contexts"):
            _contexts(frame, ["seed"], [(42,), (52,)])

    def test_alert_gate_selects_model_seed_and_full_family_adjustment(self):
        common = {"dataset": "Gotham2025", "task": "binary", "model": "random_forest", "explainer": "TreeSHAP"}
        controls = pd.DataFrame([
            {**common, "model_seed": 52, "holm_adjusted_p": .001, "holm_adjusted_p_all_contexts": .001,
             "ci_low": .1, "ci_high": .3, "mean_lift_top_minus_random": .2, "n_pairs": 90,
             "inference_unit": "explained connection-group mean"},
            {**common, "model_seed": 42, "holm_adjusted_p": .001, "holm_adjusted_p_all_contexts": .2,
             "ci_low": .05, "ci_high": .15, "mean_lift_top_minus_random": .1, "n_pairs": 30,
             "inference_unit": "explained connection-group mean"},
        ])
        summaries = pd.DataFrame([
            {**common, "model_seed": seed, "stability_cosine_mean": .7, "stability_jaccard_mean": .6,
             "latency_median_ms": seed, "latency_p95_ms": seed + 1, "n_explanations": 100}
            for seed in (52, 42)
        ])
        with patch("src.xai_ids.transparency.pd.read_csv", side_effect=[controls, summaries]), patch.object(Path, "exists", return_value=False):
            context = _benchmark_context(Path("example-results"), "Gotham2025", "binary", "random_forest", 42)
        self.assertFalse(context["global_random_control_passed"])
        self.assertEqual(context["global_holm_adjusted_p"], .2)
        self.assertEqual(context["validation_inference_group_count"], 30)
        self.assertEqual(context["median_explanation_latency_ms"], 42)

    def test_recent_manuscript_reads_metadata_and_withholds_names_during_anonymous_review(self):
        identity = manuscript_identity()
        self.assertIn("TreeSHAP", identity["title"])
        self.assertIn("2025 Benchmarks", identity["title"])
        self.assertTrue(identity["anonymous"])
        self.assertIn("Anonymous research draft", identity["author_line"])
        self.assertNotIn("Jubayed", identity["author_line"])
        self.assertIn("venue not selected", identity["footer"])


if __name__ == "__main__":
    unittest.main()
