"""Replay completed source-holdout results from CSVs, without models or raw data."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
KEYS = ["dataset", "fold", "task", "model"]
EXPECTED = {(d, f, t, m) for d in ("GeNIS2025", "Gotham2025")
            for f in range(1, 9) for t in ("binary", "multiclass")
            for m in ("random_forest", "xgboost")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    return pd.read_csv(path, float_precision="round_trip")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folds = json.loads((ROOT / "fold_assignments.json").read_text(encoding="utf-8"))
    assignments = {(row["dataset"], row["fold"]): set(row["test_sources"]) for row in folds}
    require(len(assignments) == 16 == len(folds), "Incorrect fold assignment count")
    aggregate = read_csv(ROOT / "predictive_metrics.csv").set_index(KEYS)
    explanations = read_csv(ROOT / "explanation_comparison.csv").set_index(KEYS)
    for table in (aggregate, explanations):
        require(table.index.is_unique and set(table.index) == EXPECTED, "Incomplete aggregate")
    manifest_hash = digest(ROOT / "run_manifest.json")
    key_cols = ["source_test_index", "k", "control", "connection_group"]
    max_delta_residual = max_probability_residual = 0.0
    tested_rows = {}
    file_count = 0
    for key in sorted(EXPECTED):
        dataset, fold, task, model = key
        name = f"{dataset}_fold{fold:02d}_{task}_{model}"
        context = ROOT / "contexts" / name
        for checkpoint in ("predictive", "explanation", "TreeSHAP", "LIME"):
            entry = json.loads((context / (checkpoint + "_complete.json")).read_text(encoding="utf-8"))
            require(entry["manifest_sha256"] == manifest_hash, f"Wrong manifest: {name}")
            for file, sha256 in entry["output_sha256"].items():
                require(digest(context / file) == sha256, f"Checksum mismatch: {name}/{file}")
                file_count += 1
        prediction = read_csv(context / "predictions.csv.gz")
        require(set(prediction["__source_file"]) == assignments[dataset, fold], f"Wrong sources: {name}")
        row_ids = set(zip(prediction["__source_file"], prediction["__source_row"]))
        previous = tested_rows.setdefault((dataset, task, model), set())
        require(len(row_ids) == len(prediction) and not previous.intersection(row_ids), f"Repeated test rows: {name}")
        previous.update(row_ids)
        columns = [c for c in prediction.columns if c.startswith("probability::")]
        labels = np.array([c.split("::", 1)[1] for c in columns])
        probabilities = prediction[columns].to_numpy()
        require(np.isfinite(probabilities).all() and (probabilities >= 0).all(), f"Invalid probabilities: {name}")
        max_probability_residual = max(max_probability_residual, float(np.max(np.abs(probabilities.sum(axis=1) - 1))))
        np.testing.assert_array_equal(labels[probabilities.argmax(axis=1)], prediction.predicted_class)
        actual = prediction.actual_class.to_numpy()
        predicted = prediction.predicted_class.to_numpy()
        unseen = ~np.isin(actual, labels)
        np.testing.assert_array_equal(~unseen, prediction.actual_seen_in_training)
        require(int(unseen.sum()) == aggregate.loc[key, "unseen_label_test_rows"], f"Wrong unseen support: {name}")
        f1 = [2 * np.count_nonzero((actual == c) & (predicted == c)) /
              (np.count_nonzero(actual == c) + np.count_nonzero(predicted == c)) for c in np.unique(actual)]
        np.testing.assert_allclose(np.mean(f1), aggregate.loc[key, "macro_f1_all_test_supported_labels"], rtol=0, atol=1e-12)
        left, right = [read_csv(context / (e + "_fidelity.csv")).set_index(key_cols).sort_index() for e in ("TreeSHAP", "LIME")]
        require(len(left) == len(right) == 600 and left.index.is_unique and left.index.equals(right.index), f"Unpaired explanation rows: {name}")
        require(set(left.index.get_level_values("k")) == {1, 3, 5, 10}, f"Missing masking budget: {name}")
        np.testing.assert_allclose(left.xs("random", level="control").probability_drop,
                                  right.xs("random", level="control").probability_drop,
                                  rtol=0, atol=1e-12)
        delta = left.xs("top", level="control").probability_drop - right.xs("top", level="control").probability_drop
        group_budget = delta.groupby(level=["connection_group", "k"]).mean().unstack("k")
        require(group_budget.notna().all().all(), f"Incomplete group budgets: {name}")
        group = group_budget.mean(axis=1)
        saved = read_csv(context / "paired_group_drops.csv").set_index("connection_group")
        np.testing.assert_allclose(group, saved.loc[group.index, "TreeSHAP_minus_LIME"], rtol=0, atol=1e-12)
        require(len(group) == explanations.loc[key, "explained_groups"], f"Wrong explanation group count: {name}")
        max_delta_residual = max(max_delta_residual, abs(group.mean() - explanations.loc[key, "TreeSHAP_minus_LIME"]))
    for (dataset, _, _), rows in tested_rows.items():
        require(len(rows) == (40000 if dataset == "GeNIS2025" else 133490), f"Incomplete row coverage: {dataset}")
    require(max_delta_residual <= 1e-12, "Explanation endpoint mismatch")
    require(max_probability_residual <= 1e-5, "Probability sum mismatch")
    result = {"predictive_contexts_replayed": 64, "explanation_contexts_replayed": 64,
              "checkpoint_files_hashed_including_repeated_references": file_count,
              "max_probability_sum_residual": max_probability_residual,
              "max_absolute_explanation_replay_residual": max_delta_residual,
              "no_raw_data_or_model_load": True, "no_pooled_significance_test": True,
              "summary_sha256": {name: digest(ROOT / name) for name in ("predictive_metrics.csv", "explanation_comparison.csv")}}
    (ROOT / "saved_results_replay.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
