"""Reproduce detection results and extend XAI without replacing paper evidence."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.utils.class_weight import compute_sample_weight

from src.xai_ids.benchmark import (
    TabularPreprocessor, evaluate_explainer, fidelity_control_tests,
    make_model, paired_bootstrap_comparisons, predictive_metrics,
    prepare_dataset, sha256,
)


def run(config_path: Path, output: Path, seeds: list[int], samples: int) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path("outputs/run_manifest.json").read_text(encoding="utf-8"))
    provenance = []
    for name, expected in manifest["files"].items():
        path = Path(name.replace("\\", "/"))
        actual = sha256(path)
        frame = pd.read_parquet(path)
        provenance.append({"path": str(path), "sha256": actual,
                           "matches_committed_hash": actual == expected["sha256"],
                           "rows": len(frame), "columns": list(frame.columns),
                           "provenance_status": "source conversion history undocumented"})
        if actual != expected["sha256"]:
            raise ValueError(f"Dataset hash mismatch: {path}")
    packages = {}
    for line in Path("requirements.txt").read_text().splitlines():
        if "==" in line:
            name, expected = line.split("==")
            actual = importlib.metadata.version(name)
            packages[name] = {"expected": expected, "installed": actual, "matches": actual == expected}
            if actual != expected:
                raise ValueError(f"Pinned dependency mismatch: {name}: {actual} != {expected}")
    protocol = {"model_seeds": seeds, "explanation_samples": samples,
                "dataset_split_seed": config["seed"], "explanation_sample_seed": config["seed"],
                "selection": "label-stratified with available error-case coverage; model-dependent",
                "python": platform.python_version(), "packages": packages, "files": provenance,
                "config": config,
                "benchmark_source_sha256": sha256(Path("src/xai_ids/benchmark.py")),
                "inference": "paired flow-level comparisons separately by model seed; no independent pooling across seeds",
                "limitations": ["not temporal or session-separated", "no analyst participants", "no live deployment"]}
    protocol_path = output / "protocol.json"
    if protocol_path.exists() and json.loads(protocol_path.read_text(encoding="utf-8")) != protocol:
        raise ValueError("Existing output has a different protocol; use a new output directory")
    # Preserve the source used by the run, including when project files change
    # while an experiment is computing. Never relabel old checkpoints.
    (output / "benchmark_source_at_run_start.py").write_bytes(Path("src/xai_ids/benchmark.py").read_bytes())
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    original = pd.read_csv("outputs/predictive_metrics.csv")
    comparisons, class_rows, fidelities, summaries, controls, paired = [], [], [], [], [], []
    evaluation = dict(config["evaluation"], explanation_samples=samples)
    for dataset in ("CIC-IDS2017", "UNSW-NB15"):
        for task in ("binary", "multiclass"):
            print(f"[prepare] {dataset}/{task}", flush=True)
            train, test, y_train, y_test, classes, metadata = prepare_dataset(dataset, task, config, config["seed"])
            preprocessor = TabularPreprocessor(metadata["feature_names"]).fit(train)
            x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
            for model_name in ("random_forest", "xgboost"):
                for model_seed in seeds:
                    common = {"dataset": dataset, "task": task, "model": model_name, "model_seed": model_seed}
                    checkpoint = output / f"{dataset}_{task}_{model_name}_{model_seed}".replace("-", "_")
                    checkpoint.mkdir(exist_ok=True)
                    if (checkpoint / "complete.json").exists():
                        print(f"[resume] {common}", flush=True)
                    else:
                        print(f"[fit] {common}", flush=True)
                        started = time.perf_counter()
                        model = make_model(model_name, config["models"], model_seed, len(classes))
                        weights = compute_sample_weight("balanced", y_train) if model_name == "xgboost" else None
                        model.fit(x_train, y_train, sample_weight=weights)
                        probabilities = model.predict_proba(x_test)
                        metrics, per_class, _ = predictive_metrics(y_test, probabilities.argmax(axis=1), probabilities, classes)
                        expected = original[(original.dataset == dataset) & (original.task == task) & (original.model == model_name) & (original.seed == model_seed)].iloc[0]
                        compare = [{**common, "metric": key, "recorded": float(expected[key]), "reproduced": float(value), "absolute_difference": abs(float(value) - float(expected[key]))} for key, value in metrics.items() if key in expected.index]
                        pd.DataFrame(compare).to_csv(checkpoint / "predictive_reproduction.csv", index=False)
                        pd.DataFrame([{**common, **row} for row in per_class]).to_csv(checkpoint / "per_class_metrics.csv", index=False)
                        local_fidelity, local_summaries = [], []
                        for explainer in ("TreeSHAP", "LIME"):
                            print(f"[explain] {common} {explainer} n={samples}", flush=True)
                            attrs, fidelity, stability, summary = evaluate_explainer(dataset, task, model_name, explainer, model, x_train, x_test, y_test, preprocessor, classes, evaluation, config["seed"])
                            pd.DataFrame([{**row, "model_seed": model_seed} for row in attrs]).to_csv(checkpoint / f"{explainer}_attributions.csv", index=False)
                            pd.DataFrame([{**row, "model_seed": model_seed} for row in stability]).to_csv(checkpoint / f"{explainer}_stability.csv", index=False)
                            local_fidelity.extend({**row, "model_seed": model_seed} for row in fidelity)
                            local_summaries.append({**summary, "model_seed": model_seed})
                        pd.DataFrame(local_fidelity).to_csv(checkpoint / "fidelity.csv", index=False)
                        pd.DataFrame(local_summaries).to_csv(checkpoint / "explanation_summary.csv", index=False)
                        (checkpoint / "complete.json").write_text(json.dumps({"elapsed_seconds": time.perf_counter() - started, "protocol_sha256": sha256(output / "protocol.json")}), encoding="utf-8")
                    saved = json.loads((checkpoint / "complete.json").read_text())
                    if saved["protocol_sha256"] != sha256(output / "protocol.json"):
                        raise ValueError("Checkpoint protocol differs; use a new output directory")
                    comparisons.append(pd.read_csv(checkpoint / "predictive_reproduction.csv"))
                    class_rows.append(pd.read_csv(checkpoint / "per_class_metrics.csv"))
                    fidelities.append(pd.read_csv(checkpoint / "fidelity.csv"))
                    summaries.append(pd.read_csv(checkpoint / "explanation_summary.csv"))
    fidelity = pd.concat(fidelities, ignore_index=True)
    # Correct tests over all eight contexts within each seed, then across seeds.
    for seed, frame in fidelity.groupby("model_seed"):
        paired.append(paired_bootstrap_comparisons(frame, config["seed"]).assign(model_seed=seed))
        controls.append(fidelity_control_tests(frame, config["seed"]).assign(model_seed=seed))
    for name, frames in (("predictive_reproduction", comparisons), ("per_class_metrics", class_rows), ("fidelity", fidelities), ("explanation_summary", summaries), ("paired_comparisons", paired), ("fidelity_control_tests", controls)):
        table = pd.concat(frames, ignore_index=True)
        if "wilcoxon_one_sided_p" in table:
            order = np.argsort(table.wilcoxon_one_sided_p.to_numpy())
            adjusted = np.empty(len(table)); running = 0.0
            for rank, index in enumerate(order):
                running = max(running, min(1.0, (len(table) - rank) * table.iloc[index].wilcoxon_one_sided_p))
                adjusted[index] = running
            table["holm_adjusted_p_all_seeds"] = adjusted
        table.to_csv(output / f"{name}.csv", index=False)
    print(f"[complete] {output.resolve()}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--output", type=Path, default=Path("outputs/research_validation"))
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 52, 62])
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()
    if args.samples < 2 or len(set(args.seeds)) != len(args.seeds):
        parser.error("Use at least two flows and distinct model seeds")
    run(args.config, args.output, args.seeds, args.samples)
