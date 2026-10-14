import unittest

import numpy as np
import pandas as pd

from src.xai_ids.recent_data import connection_groups, group_split


class RecentDataTests(unittest.TestCase):
    def test_bidirectional_connections_match_across_files_and_port_dtypes(self):
        frame = pd.DataFrame({"ip.src": ["10.0.0.1", "10.0.0.2"], "ip.dst": ["10.0.0.2", "10.0.0.1"],
            "tcp.srcport": [1000, 80.0], "tcp.dstport": [80, 1000.0],
            "udp.srcport": [np.nan, np.nan], "udp.dstport": [np.nan, np.nan], "ip.proto": [6, 6.0]})
        groups = connection_groups(frame)
        self.assertEqual(groups.iloc[0], groups.iloc[1])

    def test_group_split_keeps_connections_disjoint_and_records_singletons(self):
        rows = []
        for label in ("benign", "attack"):
            for group in range(12):
                for row in range(3):
                    rows.append({"Label": label, "__group": f"{label}/{group}", "__source_file": "sample", "__source_row": len(rows)})
        rows.append({"Label": "rare", "__group": "rare/one", "__source_file": "sample", "__source_row": len(rows)})
        train, test, audit = group_split(pd.DataFrame(rows))
        self.assertFalse(set(train["__group"]) & set(test["__group"]))
        self.assertEqual(set(test.Label), {"benign", "attack"})
        self.assertIn("rare", set(train.Label))
        self.assertEqual(audit["singleton_labels_training_only"], ["rare"])


if __name__ == "__main__":
    unittest.main()
