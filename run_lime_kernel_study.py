"""Matched LIME width sensitivity. The primary and budget artifacts are read-only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import warnings

# Import the frozen helper first so its thread environment defaults take effect.
import run_lime_budget_study as budget
import joblib
from lime.lime_tabular import LimeTabularExplainer
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = budget.ROOT
BUDGET = ROOT / "outputs/lime_budget_20261108"
PROTOCOL = ROOT / "LIME_KERNEL_PROTOCOL_20261108.md"
WIDTHS = (.15, .35, .75)
METHODS = ("TreeSHAP_saved", *(f"LIME_3500_w{w:.2f}" for w in WIDTHS))
IDENTITIES = [(d, t, m) for d in ("GeNIS2025", "Gotham2025")
              for t in ("binary", "multiclass") for m in ("random_forest", "xgboost")]
RECORD_KEYS = ["source_test_index", "explanation_id", "connection_group", "actual_class", "predicted_class"]


def compare_values(actual, expected):
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-12)


class SharedNeighborhood:
    """Share classifier calls only after proving identical sampled model inputs."""
    def __init__(self, model, row, original_probability):
        self.model = model
        self.row = row
        self.original_probability = original_probability
        self.samples = None
        self.probabilities = None
        self.calls = 0

    def __call__(self, samples):
        if len(samples) != 3500 or not np.array_equal(samples[0], self.row):
            raise ValueError("LIME neighborhood has incorrect sample count or query row")
        if self.samples is None:
            self.samples = samples.copy()
            self.probabilities = self.model.predict_proba(samples)
            compare_values(self.probabilities[0], self.original_probability)
        elif not np.array_equal(samples, self.samples):
            raise ValueError("Changing kernel width also changed the sampled neighborhood")
        self.calls += 1
        return self.probabilities.copy()


def audit_explanation(explainer, explanation, predicted, n_features):
    """Verify the surrogate's target and query-point prediction independently."""
    if set(explanation.local_exp) != {predicted} or set(explanation.intercept) != {predicted}:
        raise ValueError("LIME did not fit exactly the requested classifier output column")
    if (explainer.discretizer is None or set(explainer.categorical_features) != set(range(n_features))
            or not np.array_equal(explainer.scaler.mean_, np.zeros(n_features))
            or not np.array_equal(explainer.scaler.scale_, np.ones(n_features))):
        raise ValueError("The fully discretized query representation is not all ones")
    coefficients = explanation.local_exp[predicted]
    if len(coefficients) != n_features or {int(i) for i, _ in coefficients} != set(range(n_features)):
        raise ValueError("LIME must return all prepared feature coefficients exactly once")
    vector = np.zeros(n_features)
    for feature, weight in coefficients:
        vector[int(feature)] = float(weight)
    intercept = float(explanation.intercept[predicted])
    local_pred = np.asarray(explanation.local_pred).ravel()
    if len(local_pred) != 1 or not np.isfinite([intercept, local_pred[0], explanation.score]).all() or not np.isfinite(vector).all():
        raise ValueError("Invalid local surrogate prediction or coefficient")
    reconstructed = float(intercept + vector.sum())
    compare_values(local_pred[0], reconstructed)
    return vector, intercept, float(local_pred[0]), float(explanation.score), reconstructed


def new_explainer(background, preprocessor, classes, seed, width):
    if width == .75:
        result = budget.make_lime_explainer(background, preprocessor, classes, seed)
    else:
        result = LimeTabularExplainer(background, feature_names=preprocessor.feature_names,
            class_names=classes, categorical_features=preprocessor.categorical_indices,
            categorical_names=preprocessor.categorical_names, discretize_continuous=True,
            mode="classification", random_state=seed, sample_around_instance=True,
            kernel_width=width * np.sqrt(background.shape[1]))
    compare_values(result.base.kernel_fn.keywords["kernel_width"], width * np.sqrt(background.shape[1]))
    return result


def group_endpoints(frame):
    if set(frame.method) != set(METHODS) or frame.duplicated(["method", "source_test_index", "k"]).any():
        raise ValueError("Missing methods or duplicated deletion measurements")
    if not np.isfinite(frame.probability_drop).all() or frame.connection_group.isna().any():
        raise ValueError("Nonfinite deletion or missing connection")
    if not frame.groupby("source_test_index").connection_group.nunique().eq(1).all():
        raise ValueError("Record-to-connection mapping changed")
    if not frame.groupby(["method", "source_test_index"]).k.agg(set).map(lambda x: x == set(budget.K)).all():
        raise ValueError("Incomplete masking budgets")
    paired = frame.pivot(index=["connection_group", "source_test_index", "k"], columns="method", values="probability_drop")
    if paired.isna().any().any() or len(paired) != 400:
        raise ValueError("Expected a complete matched panel of 100 records and 4 budgets")
    return paired.groupby(level=[0, 2]).mean().groupby(level=0).mean()


def verified_files(directory, mapping):
    for file, expected in mapping.items():
        if budget.sha256(directory / file) != expected:
            raise ValueError(f"Artifact hash mismatch: {directory / file}")


def run_context(identity, out, fingerprint):
    dataset, task, model_name = identity
    key = f"{dataset}_{task}_{model_name}_42"
    destination = out / "contexts" / key
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / "complete.json"
    if marker.exists():
        checkpoint = json.loads(marker.read_text())
        if checkpoint["fingerprint"] != fingerprint:
            raise ValueError("Checkpoint belongs to a different kernel study")
        verified_files(destination, checkpoint["outputs"])
        print(f"[resume] {key}", flush=True)
        return
    print(f"[start] {key}", flush=True)
    original = BUDGET / "contexts" / key
    saved_fit = pd.read_csv(original / "surrogate_fit.csv", float_precision="round_trip")
    saved_fit = saved_fit[saved_fit.lime_samples.eq(3500)].set_index("source_test_index", drop=False)
    saved_attr = pd.read_csv(original / "attributions.csv", float_precision="round_trip")
    saved_attr = saved_attr[saved_attr.lime_samples.eq(3500)].pivot(index="source_test_index", columns="feature", values="attribution")
    saved_drops = pd.read_csv(original / "deletion.csv", float_precision="round_trip").set_index(["source_test_index", "method", "k"])
    artifact = joblib.load(budget.PRIMARY / "models" / f"{dataset}_{task}_{model_name}.joblib")
    if (artifact["dataset"], artifact["task"], artifact["seed"]) != (dataset, task, 42):
        raise ValueError("Saved classifier identity changed")
    model, preprocessor, classes = artifact["model"], artifact["preprocessor"], artifact["classes"]
    if "n_jobs" in model.get_params():
        model.set_params(n_jobs=1)
    prepared = ROOT / "data/prepared" / dataset
    train, test = pd.read_parquet(prepared / "train.parquet"), pd.read_parquet(prepared / "test.parquet")
    x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
    features = list(preprocessor.feature_names)
    meta, tree_vectors = budget.original_vectors(budget.PRIMARY / "contexts" / key / "TreeSHAP_attributions.csv", features)
    lime_meta, _ = budget.original_vectors(budget.PRIMARY / "contexts" / key / "LIME_attributions.csv", features)
    pair_keys = ["source_test_index", "explanation_id", "actual_class", "predicted_class"]
    if not meta[pair_keys].reset_index(drop=True).equals(lime_meta[pair_keys].reset_index(drop=True)):
        raise ValueError("Frozen primary explanation panel changed")
    if len(saved_fit) != 100 or set(saved_fit.index) != set(meta.source_test_index):
        raise ValueError("Frozen default-width diagnostic panel changed")
    if set(saved_attr.columns) != set(features) or set(saved_attr.index) != set(meta.source_test_index):
        raise ValueError("Frozen default-width attribution coverage changed")
    indices = budget.stratified_indices(model.predict(x_train), min(5000, len(x_train)), 42)
    if not np.array_equal(indices, np.load(original / "background_indices.npy", allow_pickle=False)):
        raise ValueError("Training background differs from the budget study")
    background = x_train[indices]
    baseline = np.asarray(preprocessor.baseline_)
    fit_rows, drop_rows, attrs = [], [], []
    for number, record in enumerate(meta.itertuples(index=False), 1):
        index = int(record.source_test_index)
        if not 0 <= index < len(test):
            raise ValueError("Saved test index out of range")
        row = x_test[index]
        probability = model.predict_proba(row.reshape(1, -1))[0]
        predicted = int(probability.argmax())
        truth = str(test.iloc[index].Label)
        actual = ("Normal" if truth.lower() == "benign" else "Attack") if task == "binary" else truth
        seed = budget.stable_seed("lime-budget-20261108", dataset, task, model_name, index)
        common = dict(dataset=dataset, task=task, model=model_name, model_seed=42,
            source_test_index=index, explanation_id=int(record.explanation_id),
            connection_group=str(test.iloc[index]["__group"]), actual_class=actual, predicted_class=classes[predicted])
        reference = saved_fit.loc[index]
        if (actual != record.actual_class or classes[predicted] != record.predicted_class
                or any(reference[k] != common[k] for k in RECORD_KEYS) or int(reference.paired_seed) != seed):
            raise ValueError("Saved record, target class or seed changed")
        compare_values(probability[predicted], [record.confidence, reference.target_probability])
        tree = budget.deletion_rows(model, row, predicted, baseline, tree_vectors.loc[index].to_numpy(float), "TreeSHAP_saved")
        for entry in tree:
            compare_values(entry["probability_drop"], saved_drops.loc[(index, "TreeSHAP_saved", entry["k"]), "probability_drop"])
        drop_rows.extend({**common, **entry} for entry in tree)
        neighborhood = SharedNeighborhood(model, row, probability)
        for width in WIDTHS:
            explainer = new_explainer(background, preprocessor, classes, seed, width)
            exp = explainer.explain_instance(row, neighborhood, labels=(predicted,), num_features=len(features), num_samples=3500)
            vector, intercept, surrogate, r2, reconstructed = audit_explanation(explainer, exp, predicted, len(features))
            method = f"LIME_3500_w{width:.2f}"
            fit = {**common, "method": method, "kernel_multiplier": width,
                "kernel_width": width * np.sqrt(len(features)), "lime_samples": 3500, "paired_seed": seed,
                "predicted_class_index": predicted, "weighted_surrogate_r2": r2,
                "local_intercept": intercept, "local_surrogate_prediction": surrogate,
                "reconstructed_local_prediction": reconstructed, "target_probability": float(probability[predicted]),
                "absolute_local_prediction_error": abs(surrogate-float(probability[predicted]))}
            drops = budget.deletion_rows(model, row, predicted, baseline, vector, method)
            if width == .75:
                compare_values(vector, saved_attr.loc[index, features].to_numpy(float))
                for field in ("weighted_surrogate_r2", "local_surrogate_prediction", "absolute_local_prediction_error"):
                    compare_values(fit[field], reference[field])
                for entry in drops:
                    compare_values(entry["probability_drop"], saved_drops.loc[(index, "LIME_3500", entry["k"]), "probability_drop"])
            fit_rows.append(fit)
            drop_rows.extend({**common, **entry} for entry in drops)
            attrs.extend({**common, "kernel_multiplier": width, "feature": feature, "attribution": float(value)}
                         for feature, value in zip(features, vector))
        if neighborhood.calls != 3:
            raise ValueError("Each record must use three matched classifier-neighborhood calls")
        if number % 20 == 0:
            print(f"[explain] {key}: {number}/100", flush=True)
    pd.DataFrame(fit_rows).to_csv(destination / "surrogate_fit.csv", index=False)
    pd.DataFrame(attrs).to_csv(destination / "attributions.csv", index=False)
    measurements = pd.DataFrame(drop_rows)
    measurements.to_csv(destination / "deletion.csv", index=False)
    groups = group_endpoints(measurements)
    groups.to_csv(destination / "group_endpoints.csv")
    files = {p.name: budget.sha256(p) for p in destination.glob("*.csv")}
    marker.write_text(json.dumps(dict(context=key, fingerprint=fingerprint, records=100, groups=len(groups),
        default_width_replay_records=100, equal_sample_neighborhoods=100, target_reconstruction_checks=300,
        outputs=files), indent=2), encoding="utf-8")
    print(f"[complete] {key}: {len(groups)} groups", flush=True)


def run(out):
    original = json.loads((BUDGET / "manifest.json").read_text())
    if original["status"] != "complete":
        raise ValueError("The controlled budget study must be complete")
    environment = {"python": platform.python_version(), "packages": {name: importlib.metadata.version(name)
        for name in original["environment"]["packages"]}}
    if environment != original["environment"]:
        raise ValueError("Replay requires the frozen budget-study environment")
    verified_files(ROOT, original["inputs"])
    verified_files(BUDGET, original["aggregate_outputs"])
    paths = [Path(__file__).resolve(), PROTOCOL, BUDGET / "manifest.json"]
    for identity in IDENTITIES:
        directory = BUDGET / "contexts" / ("_".join(identity) + "_42")
        done = json.loads((directory / "complete.json").read_text())
        if done["run_fingerprint"] != original["run_fingerprint"]:
            raise ValueError("Budget checkpoint fingerprint mismatch")
        verified_files(directory, done["outputs"])
        paths.extend([directory / "complete.json", *(directory / file for file in done["outputs"])])
    inputs = {**original["inputs"], **{p.relative_to(ROOT).as_posix(): budget.sha256(p) for p in paths}}
    config = dict(protocol=PROTOCOL.name, environment=environment, inputs=inputs,
        contexts=8, records_per_context=100, width_multipliers=list(WIDTHS), lime_samples=3500,
        masking_budgets=list(budget.K), new_contrasts=16, prediction_workers=1)
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    file = out / "manifest.json"
    if file.exists():
        manifest = json.loads(file.read_text())
        if manifest["fingerprint"] != fingerprint:
            raise ValueError("Kernel study inputs or source changed; use a new output directory")
        if manifest["status"] == "complete":
            verified_files(out, manifest["aggregate_outputs"])
    else:
        manifest = {**config, "fingerprint": fingerprint, "status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
        file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        snapshots = out / "source_snapshots"
        snapshots.mkdir(exist_ok=True)
        for p in (Path(__file__), PROTOCOL):
            (snapshots / p.name).write_bytes(p.read_bytes())
    with threadpool_limits(limits=1):
        for identity in IDENTITIES:
            run_context(identity, out, fingerprint)
    fit_frames, drop_frames, effect_rows = [], [], []
    for d, t, m in IDENTITIES:
        path = out / "contexts" / f"{d}_{t}_{m}_42"
        drops = pd.read_csv(path / "deletion.csv", float_precision="round_trip")
        endpoints = group_endpoints(drops)
        for width in WIDTHS:
            right = f"LIME_3500_w{width:.2f}"
            effect_rows.append(dict(dataset=d, task=t, model=m, model_seed=42, kernel_multiplier=width,
                contrast=f"TreeSHAP_saved minus {right}", in_new_holm_family=width != .75,
                **budget.summarize_contrast(endpoints["TreeSHAP_saved"]-endpoints[right],
                    budget.stable_seed("lime-kernel-20261108", d, t, m, width))))
        fit_frames.append(pd.read_csv(path / "surrogate_fit.csv", float_precision="round_trip"))
        drop_frames.append(drops)
    effects = pd.DataFrame(effect_rows)
    new = effects.in_new_holm_family
    if len(effects) != 24 or int(new.sum()) != 16:
        raise ValueError("Incomplete declared width grid or Holm family")
    effects.loc[new, "sign_holm_p_16_new_contrasts"] = budget.holm(effects.loc[new, "sign_two_sided_p"])
    effects.to_csv(out / "contrasts.csv", index=False)
    fit = pd.concat(fit_frames, ignore_index=True)
    fit.to_csv(out / "surrogate_fit.csv", index=False)
    summary = fit.groupby(["dataset", "task", "model", "kernel_multiplier"], as_index=False).agg(
        n_records=("source_test_index", "size"), mean_weighted_r2=("weighted_surrogate_r2", "mean"),
        mean_absolute_point_error=("absolute_local_prediction_error", "mean"),
        median_absolute_point_error=("absolute_local_prediction_error", "median"))
    summary.to_csv(out / "surrogate_summary.csv", index=False)
    pd.concat(drop_frames, ignore_index=True).to_csv(out / "deletion.csv", index=False)
    verified_files(ROOT, inputs)
    manifest.update(status="complete", completed_utc=datetime.now(timezone.utc).isoformat(),
        summary=dict(fit_records=len(fit), default_width_replayed=800, new_lime_explanations=1600,
            new_contrasts=16, all_widths=24, sign_tests_favor_shap=int(((effects.sign_holm_p_16_new_contrasts < .05)
                & (effects.positive_groups > effects.negative_groups)).sum()),
            sign_tests_favor_lime=int(((effects.sign_holm_p_16_new_contrasts < .05)
                & (effects.negative_groups > effects.positive_groups)).sum())),
        aggregate_outputs={p.name: budget.sha256(p) for p in out.glob("*.csv")})
    file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/lime_kernel_20261108")
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        run(args.output.resolve())
