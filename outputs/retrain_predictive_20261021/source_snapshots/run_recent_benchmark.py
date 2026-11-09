"""Run the quantitative XAI protocol on traceable 2025 author datasets."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight

from src.xai_ids.benchmark import (TabularPreprocessor, evaluate_explainer, make_model,
    predictive_metrics, paired_bootstrap_comparisons, fidelity_control_tests, feature_ablation, sha256)


def holm(values):
    values = np.asarray(values)
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = running
    return adjusted


def group_comparisons(frame, seed):
    # Equal-weight connection-group mean deletion: the unit of inference is
    # an explained connection, not correlated packets/windows within it.
    keys = ["dataset", "task", "model", "explainer", "connection_group", "control", "k"]
    grouped = frame.groupby(keys, as_index=False).probability_drop.mean().rename(columns={"connection_group": "source_test_index"})
    paired = paired_bootstrap_comparisons(grouped, seed)
    controls = fidelity_control_tests(grouped, seed)
    for table in (paired, controls):
        table["inference_unit"] = "explained connection-group mean"
        table["insufficient_groups"] = table.n_pairs < 5
        table.loc[table.insufficient_groups, "wilcoxon_one_sided_p"] = 1.0
        table["holm_adjusted_p"] = holm(table.wilcoxon_one_sided_p)
    return paired, controls


def run(config_path: Path, only_datasets=None):
    config = yaml.safe_load(config_path.read_text())
    output = Path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    datasets = only_datasets or config["datasets"]
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "config": config, "environment": {"python": platform.python_version(),
            "packages": {line.split("==")[0]: importlib.metadata.version(line.split("==")[0]) for line in Path("requirements.txt").read_text().splitlines() if "==" in line}},
        "sources": {}, "source_code": {}}
    if manifest["config"] != config:
        raise ValueError("Output already belongs to another configuration")
    for path in (Path(__file__), Path("src/xai_ids/benchmark.py"), Path("src/xai_ids/recent_data.py")):
        old = manifest["source_code"].get(str(path))
        if old and old != sha256(path):
            raise ValueError("Source changed since run started; use a new output directory")
        manifest["source_code"][str(path)] = sha256(path)
        snapshot_dir = output / "source_snapshots"
        snapshot_dir.mkdir(exist_ok=True)
        (snapshot_dir / path.name).write_bytes(path.read_bytes())
    for dataset in datasets:
        root = Path("data/prepared") / dataset
        provenance = json.loads((root / "provenance.json").read_text())
        for name, expected in provenance["prepared_files"].items():
            if sha256(root / name) != expected["sha256"]:
                raise ValueError(f"Prepared input changed: {root / name}")
        manifest["sources"][dataset] = provenance
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        train, test = pd.read_parquet(root / "train.parquet"), pd.read_parquet(root / "test.parquet")
        features = provenance["features"]
        if set(train.__group) & set(test.__group):
            raise ValueError("Connection leakage")
        preprocessor = TabularPreprocessor(features).fit(train)
        x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
        for task in ("binary", "multiclass"):
            train_labels = np.where(train.Label.str.lower() == "benign", "Normal", "Attack") if task == "binary" else train.Label
            test_labels = np.where(test.Label.str.lower() == "benign", "Normal", "Attack") if task == "binary" else test.Label
            encoder = LabelEncoder().fit(train_labels)
            y_train, y_test = encoder.transform(train_labels), encoder.transform(test_labels)
            classes = encoder.classes_.tolist()
            for model_name in ("random_forest", "xgboost"):
                for seed in config["predictive_seeds"]:
                    checkpoint = output / "contexts" / f"{dataset}_{task}_{model_name}_{seed}"
                    checkpoint.mkdir(parents=True, exist_ok=True)
                    if (checkpoint / "complete.json").exists():
                        print(f"[resume] {checkpoint.name}", flush=True)
                        continue
                    print(f"[fit] {checkpoint.name}", flush=True)
                    model = make_model(model_name, config["models"], seed, len(classes))
                    weights = compute_sample_weight("balanced", y_train) if model_name == "xgboost" else None
                    started = time.perf_counter()
                    model.fit(x_train, y_train, sample_weight=weights)
                    probabilities = model.predict_proba(x_test)
                    metrics, class_metrics, confusion = predictive_metrics(y_test, probabilities.argmax(axis=1), probabilities, classes)
                    metrics["macro_f1_supported_classes"] = f1_score(y_test, probabilities.argmax(axis=1), labels=np.unique(y_test), average="macro", zero_division=0)
                    metrics["macro_f1_training_vocabulary"] = f1_score(y_test, probabilities.argmax(axis=1), labels=np.arange(len(classes)), average="macro", zero_division=0)
                    common = {"dataset": dataset, "task": task, "model": model_name, "seed": seed}
                    pd.DataFrame([{**common, **metrics, "training_seconds": time.perf_counter() - started,
                        "train_rows": len(train), "test_rows": len(test), "feature_count": len(features),
                        "test_classes_with_support": len(np.unique(y_test)), "training_classes": len(classes)}]).to_csv(checkpoint / "predictive_metrics.csv", index=False)
                    pd.DataFrame([{**common, **row} for row in class_metrics]).to_csv(checkpoint / "per_class_metrics.csv", index=False)
                    if seed == config["seed"]:
                        (output / "models").mkdir(exist_ok=True)
                        joblib.dump({"model": model, "preprocessor": preprocessor, "classes": classes,
                            "dataset": dataset, "task": task, "seed": seed}, output / "models" / f"{dataset}_{task}_{model_name}.joblib", compress=3)
                        pd.DataFrame([{**common, "actual_class": actual, "predicted_class": predicted,
                            "count": int(confusion[i,j])} for i, actual in enumerate(classes) for j, predicted in enumerate(classes)]).to_csv(checkpoint / "confusion_matrices.csv", index=False)
                        ranking = np.argsort(-model.feature_importances_)
                        pd.DataFrame(feature_ablation(dataset, task, model_name, config["models"], x_train, y_train,
                            x_test, y_test, features, ranking, config["evaluation"]["feature_ablation_k"], seed)).to_csv(checkpoint / "feature_ablation.csv", index=False)
                    if seed in config["explanation_model_seeds"]:
                        fidelity_rows, summaries = [], []
                        for explainer in ("TreeSHAP", "LIME"):
                            print(f"[explain] {checkpoint.name} {explainer}", flush=True)
                            attributions, fidelity, stability, summary = evaluate_explainer(dataset, task, model_name,
                                explainer, model, x_train, x_test, y_test, preprocessor, classes, config["evaluation"], config["seed"])
                            for row in fidelity:
                                row["connection_group"] = test.iloc[row["source_test_index"]]["__group"]
                                row["model_seed"] = seed
                            fidelity_rows.extend(fidelity)
                            summaries.append({**summary, "model_seed": seed})
                            pd.DataFrame(attributions).assign(model_seed=seed).to_csv(checkpoint / f"{explainer}_attributions.csv", index=False)
                            pd.DataFrame(stability).assign(model_seed=seed).to_csv(checkpoint / f"{explainer}_stability.csv", index=False)
                        fidelity_frame = pd.DataFrame(fidelity_rows)
                        fidelity_frame.to_csv(checkpoint / "fidelity.csv", index=False)
                        pd.DataFrame(summaries).to_csv(checkpoint / "explanation_summary.csv", index=False)
                        paired, controls = group_comparisons(fidelity_frame, seed)
                        paired.assign(model_seed=seed).to_csv(checkpoint / "paired_comparisons.csv", index=False)
                        controls.assign(model_seed=seed).to_csv(checkpoint / "fidelity_control_tests.csv", index=False)
                    (checkpoint / "complete.json").write_text(json.dumps(common), encoding="utf-8")
            baseline_rows = []
            majority = np.bincount(y_train).argmax()
            tree = DecisionTreeClassifier(max_depth=5, random_state=config["seed"]).fit(x_train, y_train)
            for name, predictions, probs in (("majority", np.full(len(y_test), majority), None), ("depth5_tree", tree.predict(x_test), tree.predict_proba(x_test))):
                if probs is None:
                    probs = np.zeros((len(y_test), len(classes))); probs[:, majority] = 1
                metrics, _, _ = predictive_metrics(y_test, predictions, probs, classes)
                metrics["macro_f1_supported_classes"] = f1_score(y_test, predictions, labels=np.unique(y_test), average="macro", zero_division=0)
                metrics["macro_f1_training_vocabulary"] = f1_score(y_test, predictions, labels=np.arange(len(classes)), average="macro", zero_division=0)
                baseline_rows.append({"dataset": dataset, "task": task, "model": name, **metrics})
            pd.DataFrame(baseline_rows).to_csv(output / f"baselines_{dataset}_{task}.csv", index=False)
    for name in ("predictive_metrics", "per_class_metrics", "confusion_matrices", "feature_ablation", "fidelity", "explanation_summary", "paired_comparisons", "fidelity_control_tests"):
        paths = sorted((output / "contexts").glob(f"*/{name}.csv"))
        if paths:
            table = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
            if "wilcoxon_one_sided_p" in table:
                table["holm_adjusted_p_all_contexts"] = holm(table.wilcoxon_one_sided_p)
            table.to_csv(output / f"{name}.csv", index=False)
    baselines = sorted(output.glob("baselines_*.csv"))
    pd.concat([pd.read_csv(path) for path in baselines], ignore_index=True).to_csv(output / "predictive_baselines.csv", index=False)
    print(f"[recent benchmark complete] {datasets}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config_recent.yaml"))
    parser.add_argument("--datasets", nargs="+")
    args = parser.parse_args()
    run(args.config, args.datasets)
