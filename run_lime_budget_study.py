"""Controlled post-hoc LIME budget study; primary experiment is read-only."""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import warnings

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from threadpoolctl import threadpool_limits

from src.xai_ids.benchmark import make_lime_explainer, stratified_indices

ROOT = Path(__file__).resolve().parent
PRIMARY = ROOT / "outputs/recent2025"
PROTOCOL = ROOT / "LIME_BUDGET_PROTOCOL_20261108.md"
K = (1, 3, 5, 10)
BUDGETS = (350, 3500)
METHODS = ("TreeSHAP_saved", "LIME_350", "LIME_3500")
CONTRASTS = (("TreeSHAP_saved", "LIME_3500"), ("LIME_3500", "LIME_350"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode()).digest()[:4], "little")


def holm(values):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("P values must be finite probabilities")
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1., np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1)))
    return adjusted


def deletion_rows(model, row, predicted, baseline, vector, method):
    if not np.isfinite(vector).all() or len(vector) != len(row):
        raise ValueError("Attribution vector has invalid shape or values")
    rank = np.argsort(-np.abs(vector))
    masked = np.tile(row, (len(K), 1))
    for j, k in enumerate(K):
        chosen = rank[:min(k, len(row))]
        masked[j, chosen] = baseline[chosen]
    probability = float(model.predict_proba(row.reshape(1, -1))[0, predicted])
    perturbed_probability = model.predict_proba(masked)[:, predicted]
    return [dict(method=method, k=k, probability_drop=probability-float(p))
            for k, p in zip(K, perturbed_probability)]


def group_endpoints(frame):
    required = {"method", "source_test_index", "connection_group", "k", "probability_drop"}
    if not required.issubset(frame):
        raise ValueError("Deletion measurements lack required columns")
    if frame.duplicated(["method", "source_test_index", "k"]).any():
        raise ValueError("Duplicate method/record/budget measurement")
    if set(frame.method) != set(METHODS):
        raise ValueError("All three methods must be present")
    if not np.isfinite(frame.probability_drop).all() or frame.connection_group.isna().any():
        raise ValueError("Nonfinite measurements or missing groups")
    if not frame.groupby("source_test_index").connection_group.nunique().eq(1).all():
        raise ValueError("Inconsistent record-to-group mapping")
    budgets = frame.groupby(["method", "source_test_index"]).k.agg(set)
    if not budgets.map(lambda value: value == set(K)).all():
        raise ValueError("Incomplete masking budgets")
    paired = frame.pivot(index=["connection_group", "source_test_index", "k"], columns="method", values="probability_drop")
    if paired.isna().any().any():
        raise ValueError("Unmatched diagnostic records")
    return paired.groupby(level=[0, 2]).mean().groupby(level=0).mean()


def summarize_contrast(values, seed, resamples=2000):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("At least two finite group differences required")
    positive, negative = int((values > 1e-12).sum()), int((values < -1e-12).sum())
    rng = np.random.default_rng(seed)
    boot = values[rng.integers(0, len(values), size=(resamples, len(values)))].mean(axis=1)
    low, high = np.quantile(boot, [.025, .975])
    return dict(n_groups=len(values), mean_difference=float(values.mean()),
                median_difference=float(np.median(values)), ci_low=float(low), ci_high=float(high),
                positive_groups=positive, negative_groups=negative, tied_groups=len(values)-positive-negative,
                sign_two_sided_p=float(binomtest(positive, positive+negative, .5).pvalue) if positive+negative else 1.)


def original_vectors(path, features):
    frame = pd.read_csv(path, float_precision="round_trip")
    if frame.duplicated(["source_test_index", "feature"]).any():
        raise ValueError("Duplicate saved attribution entries")
    if not np.isfinite(frame.attribution).all():
        raise ValueError("Nonfinite saved attributions")
    if not frame.groupby("source_test_index").feature.agg(set).map(lambda values: values == set(features)).all():
        raise ValueError("Saved attribution feature identity mismatch")
    identities = ["explanation_id", "actual_class", "predicted_class", "confidence"]
    if not frame.groupby("source_test_index")[identities].nunique().eq(1).all().all():
        raise ValueError("Saved record identity is inconsistent")
    meta = frame.drop_duplicates("source_test_index").sort_values("explanation_id")
    if len(meta) != 100 or meta.explanation_id.duplicated().any():
        raise ValueError("Exactly 100 unique original diagnostic records required")
    vectors = frame.pivot(index="source_test_index", columns="feature", values="attribution")[features]
    return meta, vectors


def context(dataset, task, model_name, output, manifest):
    key = f"{dataset}_{task}_{model_name}_42"
    destination = output / "contexts" / key
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "complete.json").exists():
        saved = json.loads((destination / "complete.json").read_text())
        if saved["run_fingerprint"] != manifest["run_fingerprint"]:
            raise ValueError("Checkpoint belongs to a different frozen run")
        for filename, digest in saved["outputs"].items():
            if sha256(destination / filename) != digest:
                raise ValueError(f"Modified checkpoint: {destination / filename}")
        print(f"[resume] {key}", flush=True)
        return
    print(f"[start] {key}", flush=True)
    artifact = joblib.load(PRIMARY / "models" / f"{dataset}_{task}_{model_name}.joblib")
    model, preprocessor, classes = artifact["model"], artifact["preprocessor"], artifact["classes"]
    if artifact["dataset"] != dataset or artifact["task"] != task or artifact["seed"] != 42:
        raise ValueError("Saved model identity mismatch")
    if "n_jobs" in model.get_params():
        model.set_params(n_jobs=1)
    root = ROOT / "data/prepared" / dataset
    train, test = pd.read_parquet(root / "train.parquet"), pd.read_parquet(root / "test.parquet")
    x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
    features = list(preprocessor.feature_names)
    primary_context = PRIMARY / "contexts" / key
    meta, vectors = original_vectors(primary_context / "TreeSHAP_attributions.csv", features)
    lime_meta, _ = original_vectors(primary_context / "LIME_attributions.csv", features)
    if not meta[["source_test_index", "actual_class", "predicted_class"]].reset_index(drop=True).equals(
            lime_meta[["source_test_index", "actual_class", "predicted_class"]].reset_index(drop=True)):
        raise ValueError("Primary explainers have unmatched diagnostic identities")
    background_indices = stratified_indices(model.predict(x_train), min(5000, len(x_train)), 42)
    background = x_train[background_indices]
    np.save(destination / "background_indices.npy", background_indices)
    fit_rows, measurements, attributions = [], [], []
    for number, record in enumerate(meta.itertuples(index=False), start=1):
        index = int(record.source_test_index)
        if index < 0 or index >= len(test):
            raise ValueError("Saved diagnostic index out of range")
        row = x_test[index]
        probability = model.predict_proba(row.reshape(1, -1))[0]
        predicted = int(np.argmax(probability))
        expected_actual = ("Normal" if str(test.iloc[index].Label).lower() == "benign" else "Attack") if task == "binary" else str(test.iloc[index].Label)
        if classes[predicted] != record.predicted_class or expected_actual != record.actual_class:
            raise ValueError("Original diagnostic class/target does not match saved model/data")
        if not np.isclose(probability[predicted], record.confidence, rtol=1e-8, atol=1e-12):
            raise ValueError("Saved-model target probability changed")
        common = dict(dataset=dataset, task=task, model=model_name, model_seed=42,
                      source_test_index=index, explanation_id=int(record.explanation_id),
                      connection_group=str(test.iloc[index]["__group"]),
                      actual_class=record.actual_class, predicted_class=record.predicted_class)
        vector = vectors.loc[index].to_numpy(dtype=float)
        measurements.extend({**common, **measurement} for measurement in deletion_rows(
            model, row, predicted, np.asarray(preprocessor.baseline_), vector, "TreeSHAP_saved"))
        seed = stable_seed("lime-budget-20261108", dataset, task, model_name, index)
        for budget in BUDGETS:
            explainer = make_lime_explainer(background, preprocessor, classes, seed)
            explanation = explainer.explain_instance(row, model.predict_proba,
                labels=(predicted,), num_features=len(features), num_samples=budget)
            vector = np.zeros(len(features))
            for feature_index, weight in explanation.local_exp[predicted]:
                vector[int(feature_index)] = float(weight)
            surrogate = float(np.asarray(explanation.local_pred).ravel()[0])
            r2 = float(explanation.score)
            if not np.isfinite([surrogate, r2]).all():
                raise ValueError("Nonfinite LIME surrogate diagnostics")
            fit_rows.append({**common, "lime_samples": budget, "paired_seed": seed,
                "weighted_surrogate_r2": r2, "local_surrogate_prediction": surrogate,
                "target_probability": float(probability[predicted]),
                "absolute_local_prediction_error": abs(surrogate-float(probability[predicted]))})
            method = f"LIME_{budget}"
            measurements.extend({**common, **measurement} for measurement in deletion_rows(
                model, row, predicted, np.asarray(preprocessor.baseline_), vector, method))
            attributions.extend({**common, "lime_samples": budget, "paired_seed": seed,
                "feature": feature, "attribution": float(value)} for feature, value in zip(features, vector))
        if number % 10 == 0:
            print(f"[explain] {key}: {number}/100 records", flush=True)
    pd.DataFrame(fit_rows).to_csv(destination / "surrogate_fit.csv", index=False)
    pd.DataFrame(measurements).to_csv(destination / "deletion.csv", index=False)
    pd.DataFrame(attributions).to_csv(destination / "attributions.csv", index=False)
    endpoints = group_endpoints(pd.DataFrame(measurements))
    endpoints.to_csv(destination / "group_endpoints.csv")
    outputs = {p.name: sha256(p) for p in destination.iterdir() if p.is_file() and p.name != "complete.json"}
    (destination / "complete.json").write_text(json.dumps(dict(context=key,
        run_fingerprint=manifest["run_fingerprint"], records=100, groups=len(endpoints), outputs=outputs), indent=2), encoding="utf-8")
    print(f"[complete] {key}: {len(endpoints)} groups", flush=True)


def run(output):
    if not PROTOCOL.is_file():
        raise FileNotFoundError("The frozen protocol must exist before computation")
    output.mkdir(parents=True, exist_ok=True)
    paths = [Path(__file__).resolve(), PROTOCOL, ROOT / "src/xai_ids/benchmark.py", PRIMARY / "run_manifest.json"]
    identities = [(d, t, m) for d in ("GeNIS2025", "Gotham2025")
                  for t in ("binary", "multiclass") for m in ("random_forest", "xgboost")]
    for dataset in ("GeNIS2025", "Gotham2025"):
        paths.extend(ROOT / "data/prepared" / dataset / name for name in ("train.parquet", "test.parquet", "provenance.json"))
    for d, t, m in identities:
        paths.append(PRIMARY / "models" / f"{d}_{t}_{m}.joblib")
        paths.extend(PRIMARY / "contexts" / f"{d}_{t}_{m}_42" / name for name in ("TreeSHAP_attributions.csv", "LIME_attributions.csv"))
    inputs = {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}
    frozen = dict(protocol="LIME_BUDGET_PROTOCOL_20261108.md", contexts=8, diagnostic_records_per_context=100,
                  budgets=list(BUDGETS), masking_budgets=list(K), tests=16, inputs=inputs,
                  environment={"python": platform.python_version(), "packages": {name: importlib.metadata.version(name)
                      for name in ("numpy", "pandas", "scipy", "scikit-learn", "lime", "xgboost", "shap")}})
    fingerprint = hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["run_fingerprint"] != fingerprint:
            raise ValueError("Run inputs/source/environment changed; choose a new output directory")
    else:
        from datetime import datetime, timezone
        manifest = {**frozen, "run_fingerprint": fingerprint, "started_utc": datetime.now(timezone.utc).isoformat(), "status": "running"}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        snapshot = output / "source_snapshots"
        snapshot.mkdir(exist_ok=True)
        for p in (Path(__file__).resolve(), PROTOCOL):
            (snapshot / p.name).write_bytes(p.read_bytes())
    with threadpool_limits(limits=1):
        for identity in identities:
            context(*identity, output, manifest)
    rows, fit_frames, deletion_frames = [], [], []
    for d, t, m in identities:
        destination = output / "contexts" / f"{d}_{t}_{m}_42"
        measurements = pd.read_csv(destination / "deletion.csv", float_precision="round_trip")
        endpoints = group_endpoints(measurements)
        common = dict(dataset=d, task=t, model=m, model_seed=42)
        for left, right in CONTRASTS:
            rows.append({**common, "left": left, "right": right,
                **summarize_contrast(endpoints[left]-endpoints[right], stable_seed(d, t, m, left, right))})
        fit_frames.append(pd.read_csv(destination / "surrogate_fit.csv", float_precision="round_trip"))
        deletion_frames.append(measurements)
    contrasts = pd.DataFrame(rows)
    if len(contrasts) != 16:
        raise ValueError("The declared 16-contrast family is incomplete")
    contrasts["sign_holm_p_16_contrasts"] = holm(contrasts.sign_two_sided_p)
    contrasts.to_csv(output / "contrasts.csv", index=False)
    fit = pd.concat(fit_frames, ignore_index=True)
    fit.to_csv(output / "surrogate_fit.csv", index=False)
    fit.groupby(["dataset", "task", "model", "lime_samples"])[["weighted_surrogate_r2", "absolute_local_prediction_error"]].agg(["mean", "median", "std"]).to_csv(output / "surrogate_summary.csv")
    pd.concat(deletion_frames, ignore_index=True).to_csv(output / "deletion.csv", index=False)
    for path, digest in inputs.items():
        if sha256(ROOT / path) != digest:
            raise ValueError(f"Input changed during computation: {path}")
    manifest["status"] = "complete"
    from datetime import datetime, timezone
    manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["summary"] = dict(contexts=8, controlled_lime_explanations=len(fit), contrasts=16,
        shap_minus_lime3500_positive=int(((contrasts.left == "TreeSHAP_saved") & (contrasts.mean_difference > 0)).sum()),
        shap_minus_lime3500_significant_positive=int(((contrasts.left == "TreeSHAP_saved") & (contrasts.mean_difference > 0) & (contrasts.sign_holm_p_16_contrasts < .05)).sum()),
        lime3500_minus_350_positive=int(((contrasts.left == "LIME_3500") & (contrasts.mean_difference > 0)).sum()),
        lime3500_minus_350_significant_positive=int(((contrasts.left == "LIME_3500") & (contrasts.mean_difference > 0) & (contrasts.sign_holm_p_16_contrasts < .05)).sum()))
    manifest["aggregate_outputs"] = {p.name: sha256(p) for p in output.glob("*.csv")}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/lime_budget_20261108")
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        run(args.output.resolve())
