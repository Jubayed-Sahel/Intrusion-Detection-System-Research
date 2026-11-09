import unittest

import pandas as pd

from run_journal_audit import KEY, predictions, prevalence_projection


class JournalAuditTests(unittest.TestCase):
    def test_pair_lookup_falls_back_and_ties_predict_benign(self):
        train = pd.DataFrame([("6", 1, 2), ("6", 1, 2), ("6", 3, 4), ("6", 4, 5)], columns=KEY)
        test = pd.DataFrame([("6", 1, 2), ("6", 5, 6), ("17", 1, 2)], columns=KEY)
        protocol, pair, seen = predictions(train, [True, False, True, True], test)
        self.assertEqual(protocol.tolist(), [True, True, False])
        self.assertEqual(pair.tolist(), [False, True, False])
        self.assertEqual(seen.tolist(), [True, False, False])

    def test_projection_uses_assumed_prevalence(self):
        precision, false_alerts = prevalence_projection(1.0, 0.25, 0.01)
        self.assertAlmostEqual(precision, 0.01 / 0.2575)
        self.assertAlmostEqual(false_alerts, 2475)
