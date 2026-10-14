"""Repeat sensitivity and calibration audits for the recent-data models."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder

from src.xai_ids.benchmark import make_model, sha256
from src.xai_ids.extended_audit import _calibration_rows, _masking_baseline_rows, _lime_budget_rows


def run(config_path=Path("config_recent.yaml"), datasets=None):
    config = yaml.safe_load(config_path.read_text())
    datasets = datasets or config["datasets"]
    output = Path(config["output_dir"])
    destination = output / "extended"
    destination.mkdir(exist_ok=True)
    manifest_path = destination / "audit_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"config": config, "source_code": {}, "inputs": {}}
    if manifest["config"] != config:
        raise ValueError("Audit output belongs to another configuration")
    snapshots = destination / "source_snapshots"
    snapshots.mkdir(exist_ok=True)
    for path in (Path(__file__), Path("src/xai_ids/extended_audit.py"), Path("src/xai_ids/benchmark.py"), Path("src/xai_ids/transparency.py")):
        digest = sha256(path)
        if path.as_posix() in manifest["source_code"] and manifest["source_code"][path.as_posix()] != digest:
            raise ValueError("Audit source changed; use a new output directory")
        manifest["source_code"][path.as_posix()] = digest
        (snapshots / path.name).write_bytes(path.read_bytes())
    for dataset in datasets:
        for path in (Path("data/prepared") / dataset / "train.parquet", Path("data/prepared") / dataset / "test.parquet"):
            digest = sha256(path)
            if path.as_posix() in manifest["inputs"] and manifest["inputs"][path.as_posix()] != digest:
                raise ValueError("Audit input changed")
            manifest["inputs"][path.as_posix()] = digest
        train = pd.read_parquet(Path("data/prepared") / dataset / "train.parquet")
        test = pd.read_parquet(Path("data/prepared") / dataset / "test.parquet")
        for task in ("binary", "multiclass"):
            train_labels = np.where(train.Label.str.lower() == "benign", "Normal", "Attack") if task == "binary" else train.Label
            test_labels = np.where(test.Label.str.lower() == "benign", "Normal", "Attack") if task == "binary" else test.Label
            encoder = LabelEncoder().fit(train_labels)
            y_train, y_test = encoder.transform(train_labels), encoder.transform(test_labels)
            for model_name in ("random_forest", "xgboost"):
                name = f"{dataset}_{task}_{model_name}"
                checkpoint = destination / name
                checkpoint.mkdir(exist_ok=True)
                artifact_path = output / "models" / f"{name}.joblib"
                digest = sha256(artifact_path)
                if artifact_path.as_posix() in manifest["inputs"] and manifest["inputs"][artifact_path.as_posix()] != digest:
                    raise ValueError("Audit model changed")
                manifest["inputs"][artifact_path.as_posix()] = digest
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                if (checkpoint / "complete.json").exists():
                    continue
                print(f"[recent audit] {name}", flush=True)
                artifact = joblib.load(artifact_path)
                model, preprocessor, classes = artifact["model"], artifact["preprocessor"], artifact["classes"]
                x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
                if task == "binary":
                    bins, summary = _calibration_rows(dataset, model_name, model, x_test, y_test, classes)
                    pd.DataFrame(bins).to_csv(checkpoint / "calibration_bins.csv", index=False)
                    pd.DataFrame([summary]).to_csv(checkpoint / "calibration_summary.csv", index=False)
                alternative = make_model(model_name, config["models"], config["seed"], len(classes))
                if model_name == "random_forest":
                    alternative.set_params(class_weight=None)
                alternative.fit(x_train, y_train)
                balancing = [{"dataset": dataset, "task": task, "model": model_name, "seed": config["seed"],
                    "training_weighting": label, "macro_f1": f1_score(y_test, estimator.predict(x_test), average="macro", zero_division=0),
                    "macro_f1_supported_classes": f1_score(y_test, estimator.predict(x_test), labels=np.unique(y_test), average="macro", zero_division=0)}
                    for label, estimator in (("none", alternative), ("class_weighted", model))]
                pd.DataFrame(balancing).to_csv(checkpoint / "balancing_ablation.csv", index=False)
                masking = _masking_baseline_rows(dataset, task, model_name, model, x_train, x_test, y_test, preprocessor, config["seed"])
                pd.DataFrame(masking).to_csv(checkpoint / "masking_baseline_ablation.csv", index=False)
                budgets = _lime_budget_rows(dataset, task, model_name, model, x_train, x_test, y_test, preprocessor, classes, config["seed"])
                pd.DataFrame(budgets).to_csv(checkpoint / "lime_budget_ablation.csv", index=False)
                (checkpoint / "complete.json").write_text(json.dumps({"dataset": dataset, "task": task, "model": model_name}))
    for name in ("calibration_bins", "calibration_summary", "balancing_ablation", "masking_baseline_ablation", "lime_budget_ablation"):
        pd.concat([pd.read_csv(file) for file in sorted(destination.glob(f"*/{name}.csv"))], ignore_index=True).to_csv(destination / f"{name}.csv", index=False)
    print(f"[recent audits complete] {datasets}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config_recent.yaml"))
    parser.add_argument("--datasets", nargs="+")
    args = parser.parse_args()
    run(args.config, args.datasets)
