"""Meaningful leakage/coverage regressions for the source-transfer supplement."""
import unittest
import numpy as np
import pandas as pd

from run_source_holdout import make_folds, partition, score_predictions


class SourceHoldoutTests(unittest.TestCase):
    def test_source_partition_purges_cross_source_groups(self):
        frame = pd.DataFrame({"__source_file":["a","a","b","b","c"],
            "__group":["shared","a","shared","b","c"],"Label":["benign"]*5})
        train,test,audit = partition(frame,["a"])
        self.assertEqual(set(train["__group"]),{"b","c"})
        self.assertEqual(audit["purged_train_rows"],1)
        self.assertFalse(set(train["__group"]) & set(test["__group"]))

    def test_gotham_source_bundles_cover_every_source_once(self):
        frame = pd.DataFrame({"__source_file":["attack-a","attack-b","benign-a","benign-b","benign-c"],
            "Label":["Flood","Scan","Benign","Benign","Benign"]})
        folds = make_folds(frame,"Gotham2025")
        self.assertEqual(len(folds),2)
        self.assertEqual(sorted(s for f in folds for s in f["test_sources"]),sorted(frame["__source_file"]))
        self.assertEqual(folds,make_folds(frame.sample(frac=1,random_state=4),"Gotham2025"))
        self.assertTrue(all(len(f["test_sources"])>=2 for f in folds))

    def test_unseen_class_is_preserved_in_primary_metric(self):
        metrics, rows, confusion = score_predictions(["A","A","B","NOVEL"],["A","A","B","A"],["A","B"])
        self.assertAlmostEqual(metrics["macro_f1_all_test_supported_labels"],.6)
        self.assertEqual(metrics["unseen_label_test_rows"],1)
        self.assertEqual(metrics["seen_label_test_rows"],3)
        self.assertEqual(metrics["macro_f1_seen_label_subset"],1)
        novel = next(r for r in rows if r["class"]=="NOVEL")
        self.assertEqual(novel["recall"],0)
        self.assertEqual(novel["test_support"],1)
        self.assertFalse(novel["seen_in_training"])
        self.assertEqual(sum(r["count"] for r in confusion),4)

    def test_invalid_prediction_vocabulary_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"outside trained vocabulary"):
            score_predictions(["NOVEL"],["NOVEL"],["A","B"])


if __name__ == "__main__":
    unittest.main()
