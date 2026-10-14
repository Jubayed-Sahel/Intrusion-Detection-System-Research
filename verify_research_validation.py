"""Validate extended evidence structure without requiring a preferred outcome."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def verify(output: Path):
    protocol = json.loads((output / "protocol.json").read_text())
    snapshot = output / "benchmark_source_at_run_start.py"
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == protocol["benchmark_source_sha256"]
    fidelity = pd.read_csv(output / "fidelity.csv")
    summaries = pd.read_csv(output / "explanation_summary.csv")
    paired = pd.read_csv(output / "paired_comparisons.csv")
    controls = pd.read_csv(output / "fidelity_control_tests.csv")
    contexts = 8 * len(protocol["model_seeds"])
    assert len(summaries) == contexts * 2
    assert len(paired) == contexts
    assert len(controls) == contexts * 2
    assert set(fidelity.model_seed) == set(protocol["model_seeds"])
    keys = ["dataset", "task", "model", "model_seed"]
    assert fidelity.groupby(keys).ngroups == contexts
    for _, group in fidelity.groupby(keys):
        left = group[group.explainer == "TreeSHAP"].drop_duplicates("source_test_index").set_index("source_test_index")
        right = group[group.explainer == "LIME"].drop_duplicates("source_test_index").set_index("source_test_index")
        assert len(left) == protocol["explanation_samples"]
        assert set(left.index) == set(right.index)
        right = right.reindex(left.index)
        assert left.actual_class.equals(right.actual_class)
        assert left.predicted_class.equals(right.predicted_class)
        assert np.allclose(left.confidence, right.confidence)
        assert set(group.control) == {"top", "random", "bottom"}
        assert not group.duplicated(["explainer", "source_test_index", "control", "k"]).any()
    assert np.isfinite(fidelity.probability_drop).all()
    for frame in (paired, controls):
        assert (frame.ci_low <= frame.ci_high).all()
        assert frame.holm_adjusted_p_all_seeds.between(0, 1).all()
        assert (frame.holm_adjusted_p_all_seeds >= frame.wilcoxon_one_sided_p - 1e-12).all()
    print(f"Verified {contexts} model/seed contexts with {protocol['explanation_samples']} matched flows each.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/research_validation_corrected"))
    verify(parser.parse_args().output)
