"""Post-hoc evaluation after excluding train-matching test feature patterns.

No refitting, hyperparameter selection, split modification, or primary overwrite.
This conditional diagnostic cannot establish an independent capture evaluation.
"""
from pathlib import Path
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from run_explanation_robustness import group_differences, sensitivity, holm

RESULTS = Path("outputs/recent2025")
OUTPUT = Path("outputs/pattern_sensitivity_20261107")
CONTEXT_KEYS = ["dataset", "task", "model", "model_seed"]


def matching_patterns(train, test, features):
    """Exact raw predictor equality (including missing values), without labels/IDs.

    MultiIndex membership compares keys, avoiding a hash-only equality decision.
    """
    return np.asarray(pd.MultiIndex.from_frame(test[features]).isin(
        pd.MultiIndex.from_frame(train[features])))


def validate_contexts(primary, config):
    """Require each configured explanation context exactly once."""
    expected = {(d, t, m, s) for d in config["datasets"]
                for t in ("binary", "multiclass") for m in config["models"]
                for s in config["explanation_model_seeds"]}
    actual = set(primary[CONTEXT_KEYS].itertuples(index=False, name=None))
    if primary.duplicated(CONTEXT_KEYS).any() or actual != expected:
        raise ValueError("Primary context coverage is incomplete or duplicated")


def explanation_indices(frame, context, test):
    """Check context, integral row identity, connection and observed class."""
    for key in CONTEXT_KEYS:
        if set(frame[key]) != {getattr(context, key)}:
            raise ValueError(f"Explanation context identity disagrees: {key}")
    raw_indices = frame.source_test_index.to_numpy()
    if not np.isfinite(raw_indices).all() or not np.equal(raw_indices, np.floor(raw_indices)).all():
        raise ValueError("Explanation indices must be finite integers")
    if (raw_indices < 0).any() or (raw_indices >= len(test)).any():
        raise ValueError("Explanation index out of bounds")
    indices = raw_indices.astype(int)
    selected = test.iloc[indices]
    if not np.array_equal(selected.__group.astype(str).to_numpy(), frame.connection_group.astype(str).to_numpy()):
        raise ValueError("Explanation row-to-group identity disagrees with prepared data")
    labels = selected.Label.astype(str)
    if context.task == "binary":
        labels = labels.map(lambda value: "Normal" if value.lower() == "benign" else "Attack")
    if not np.array_equal(labels.to_numpy(), frame.actual_class.astype(str).to_numpy()):
        raise ValueError("Explanation observed class disagrees with prepared data")
    return indices


def validate_predictive_reference(result, primary):
    """The loaded seed-42 model must reproduce the frozen predictive metrics."""
    mask = np.ones(len(primary), dtype=bool)
    for key in ("dataset", "task", "model"):
        mask &= primary[key].eq(result[key]).to_numpy()
    mask &= primary.seed.eq(result["model_seed"]).to_numpy()
    reference = primary.loc[mask]
    if len(reference) != 1:
        raise ValueError("Frozen predictive reference is missing or duplicated")
    reference = reference.iloc[0]
    metrics = {"accuracy": "accuracy", "macro_f1_fixed_original_test_labels": "macro_f1_supported_classes",
               "macro_recall_fixed_original_test_labels": "balanced_accuracy"}
    if result["n_rows"] != reference.test_rows or any(
            not np.isclose(result[current], reference[frozen], rtol=0, atol=1e-12)
            for current, frozen in metrics.items()):
        raise ValueError("Saved model does not reproduce frozen predictive metrics")


def main():
    hashes, predictive, explanatory, coverage = {}, [], [], []
    def record(path):
        resolved = path.resolve()
        project_root = Path(__file__).resolve().parent
        key = resolved.relative_to(project_root).as_posix() if resolved.is_relative_to(project_root) else resolved.as_posix()
        hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    record(Path(__file__))
    record(Path("run_explanation_robustness.py"))
    record(RESULTS / "run_manifest.json")
    manifest = json.loads((RESULTS / "run_manifest.json").read_text())
    primary = pd.read_csv(RESULTS / "paired_comparisons.csv", float_precision="round_trip")
    record(RESULTS / "paired_comparisons.csv")
    validate_contexts(primary, manifest["config"])
    frozen_predictive = pd.read_csv(RESULTS / "predictive_metrics.csv", float_precision="round_trip")
    record(RESULTS / "predictive_metrics.csv")
    for dataset in manifest["config"]["datasets"]:
        directory = Path("data/prepared") / dataset
        for filename in ("train.parquet", "test.parquet", "provenance.json"):
            record(directory / filename)
        train, test = [pd.read_parquet(directory / f"{part}.parquet") for part in ("train", "test")]
        provenance = json.loads((directory / "provenance.json").read_text())
        features = provenance["features"]
        duplicate = matching_patterns(train, test, features)
        if int(duplicate.sum()) != provenance["test_feature_vectors_also_present_in_training"]:
            raise ValueError("Exact equality count disagrees with the frozen overlap audit")
        keep = ~duplicate
        coverage.append(dict(dataset=dataset, original_test_rows=len(test), excluded_test_rows=int(duplicate.sum()),
            retained_test_rows=int(keep.sum()), original_test_groups=test.__group.nunique(),
            retained_test_groups=test.loc[keep, "__group"].nunique()))
        for task in ("binary", "multiclass"):
            for model_name in manifest["config"]["models"]:
                path = RESULTS / "models" / f"{dataset}_{task}_{model_name}.joblib"
                record(path)
                artifact = joblib.load(path)
                if artifact["seed"] != 42:
                    raise ValueError("This diagnostic requires the saved seed-42 models")
                raw = test.Label.astype(str)
                if task == "binary":
                    raw = raw.map(lambda v: "Normal" if v.lower() == "benign" else "Attack")
                y = raw.map({label: i for i, label in enumerate(artifact["classes"])}).to_numpy()
                if pd.isna(y).any():
                    raise ValueError("Unrecognized evaluation label")
                pred = artifact["model"].predict(artifact["preprocessor"].transform(test))
                labels = sorted(np.unique(y))
                for name, mask in (("original", np.ones(len(test), dtype=bool)), ("no_train_matching_pattern", keep)):
                    missing = sorted(set(labels) - set(y[mask]))
                    result = dict(dataset=dataset, task=task, model=model_name, model_seed=42,
                        cohort=name, n_rows=int(mask.sum()), accuracy=accuracy_score(y[mask], pred[mask]),
                        macro_f1_fixed_original_test_labels=f1_score(y[mask], pred[mask], labels=labels,
                            average="macro", zero_division=0),
                        macro_recall_fixed_original_test_labels=recall_score(y[mask], pred[mask], labels=labels,
                            average="macro", zero_division=0),
                        labels_lost=";".join(artifact["classes"][i] for i in missing))
                    if name == "original":
                        validate_predictive_reference(result, frozen_predictive)
                    predictive.append(result)
        for context in primary[primary.dataset.eq(dataset)].itertuples(index=False):
            path = RESULTS / "contexts" / f"{dataset}_{context.task}_{context.model}_{context.model_seed}" / "fidelity.csv"
            record(path)
            frame = pd.read_csv(path, float_precision="round_trip")
            # A prepared test row index is the original benchmark's source_test_index.
            indices = explanation_indices(frame, context, test)
            original_values = group_differences(frame, manifest["config"]["evaluation"]["fidelity_k"])
            if len(original_values) != context.n_pairs or not np.isclose(original_values.mean(), context.mean_difference_shap_minus_lime, rtol=0, atol=1e-12):
                raise ValueError("Original explanation endpoint reproduction failed")
            retained = frame.loc[keep[indices]]
            values = group_differences(retained, manifest["config"]["evaluation"]["fidelity_k"])
            summary = sensitivity(values)
            explanatory.append(dict(dataset=dataset, task=context.task, model=context.model,
                model_seed=context.model_seed, original_groups=context.n_pairs,
                retained_diagnostic_records=retained.source_test_index.nunique(), **summary))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coverage).to_csv(OUTPUT / "coverage.csv", index=False)
    pd.DataFrame(predictive).to_csv(OUTPUT / "predictive.csv", index=False)
    table = pd.DataFrame(explanatory)
    if len(table) != 24:
        raise ValueError("Incomplete explanation family")
    table["sign_holm_p_24_contexts"] = holm(table.sign_two_sided_p)
    table.to_csv(OUTPUT / "explanatory.csv", index=False)
    summary = dict(contexts=len(table), positive_means=int(table.mean_difference.gt(0).sum()),
        positive_sign_test_holm=int(((table.sign_holm_p_24_contexts < .05) & (table.positive_groups > table.negative_groups)).sum()),
        single_group_reversals=int(table.single_group_can_reverse_mean.sum()),
        retained_group_range=[int(table.n_groups.min()), int(table.n_groups.max())])
    (OUTPUT / "manifest.json").write_text(json.dumps(dict(
        analysis="Exploratory conditional test-pattern exclusion; frozen primary unchanged",
        predictors="Exact raw prepared predictor equality; labels and audit fields excluded",
        seed_scope="Eight saved seed-42 predictive models; all 24 saved explanation contexts",
        inference="Separate post-hoc family of 24 two-sided sign tests, Holm adjusted; no new Wilcoxon or bootstrap claim",
        limitations="Post-selection diagnostic. Not a new split, retraining study, independent replication, or external validation. Groups may retain dependence; lost labels are reported, and predictive macro-F1 retains the original supported-label denominator.",
        summary=summary, sha256=hashes), indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
