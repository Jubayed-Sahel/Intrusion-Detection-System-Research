"""Summarize the completed official-source study without pooling seeds."""
import argparse
import json
from pathlib import Path

import pandas as pd


def main(root=Path("outputs/recent2025")):
    manifest = json.loads((root / "run_manifest.json").read_text())
    predictive = pd.read_csv(root / "predictive_metrics.csv")
    paired = pd.read_csv(root / "paired_comparisons.csv")
    controls = pd.read_csv(root / "fidelity_control_tests.csv")
    assert len(predictive) == 40 and len(paired) == 24 and len(controls) == 48
    metrics = predictive.groupby(["dataset", "task", "model"])["macro_f1_supported_classes"].agg(["mean", "std"]).reset_index()
    metrics.to_csv(root / "predictive_summary.csv", index=False)
    sources = {}
    for dataset, source in manifest["sources"].items():
        sources[dataset] = {"author_record": source["author_record"],
            "source_rows": sum(source["source_label_counts"].values()),
            "supervised_excluded_label_counts": source["supervised_excluded_label_counts"],
            "sampled_rows": sum(source["sampled_label_counts"].values()),
            "source_date_range_utc": source["source_date_range_utc"],
            "feature_count": len(source["features"]), **source["split_audit"]}
    comparison = {"contexts": len(paired),
        "positive_mean_difference": int((paired.mean_difference_shap_minus_lime > 0).sum()),
        "directional_holm_significant": int(((paired.holm_adjusted_p_all_contexts < .05) & (paired.mean_difference_shap_minus_lime > 0)).sum()),
        "bootstrap_interval_above_zero": int((paired.ci_low > 0).sum()),
        "explained_groups_min": int(paired.n_pairs.min()), "explained_groups_max": int(paired.n_pairs.max())}
    control_summary = {}
    for explainer, table in controls.groupby("explainer"):
        control_summary[explainer] = {"contexts": len(table),
            "strict_supported_contexts": int(((table.holm_adjusted_p_all_contexts < .05) & (table.ci_low > 0)).sum())}
    summary = {"source_scope": "Official author CSV derivatives; historical unknown-provenance parquet inputs are not primary evidence.",
        "sources": sources, "predictive_fits": len(predictive),
        "predictive_score": "Macro-F1 averaged over the fixed labels with actual held-out support; five seeds on one frozen split.",
        "paired_group_inference": comparison, "random_controls": control_summary,
        "inference_scope": "Equal-weight explained connection-group means on diagnostic class-capped held-out cohorts; Holm families 24 paired and 48 controls, no pooling repeated seeds.",
        "completed_extended_contexts": len(list((root / "extended").glob("*/complete.json")))}
    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"fits": len(predictive), "paired_contexts": len(paired), "controls": control_summary}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/recent2025"))
    main(parser.parse_args().output)
