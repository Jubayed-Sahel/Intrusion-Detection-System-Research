"""Run saved IDS models or a small, separate training/XAI smoke experiment."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def command(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check dependencies, tests, and recent artifacts first.")
    parser.add_argument("--smoke-train", action="store_true", help="Fit four small GeNIS models and evaluate SHAP/LIME; not a paper reproduction.")
    parser.add_argument("--dataset", choices=["GeNIS2025", "Gotham2025"], help="Restrict saved-model demonstrations to one dataset.")
    args = parser.parse_args()
    if args.smoke_train and args.dataset:
        parser.error("--dataset applies to the saved-model demo; smoke training uses GeNIS2025.")
    if args.check:
        command("-m", "pip", "check")
        command("-B", "-m", "unittest", "discover", "-s", "tests")
        command("-B", "verify_recent_benchmark.py")
    # A unique directory prevents reruns overwriting either paper evidence or demos.
    import tempfile
    (ROOT / "outputs" / "local_runs").mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_"),
                                     dir=ROOT / "outputs" / "local_runs"))
    if args.smoke_train:
        import yaml
        config = yaml.safe_load((ROOT / "config_recent.yaml").read_text())
        config.update(output_dir=destination.relative_to(ROOT).as_posix(),
                      datasets=["GeNIS2025"], predictive_seeds=[42], explanation_model_seeds=[42])
        config["models"]["random_forest"]["n_estimators"] = 20
        config["models"]["xgboost"]["n_estimators"] = 30
        config["evaluation"].update(explanation_samples=10, self_stability_samples=2, lime_repeat_seeds=2)
        config_path = destination / "config.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        print("Training four small GeNIS models with matched SHAP/LIME explanations. This is a smoke test, not publication evidence.", flush=True)
        command("run_recent_benchmark.py", "--config", config_path)
        print(f"Training and explanation outputs: {destination}")
        return
    from src.xai_ids.transparency import explain_alert
    import pandas as pd
    rows = []
    for dataset in ([args.dataset] if args.dataset else ["GeNIS2025", "Gotham2025"]):
        input_path = ROOT / "data" / "prepared" / dataset / "test.parquet"
        if not input_path.exists():
            raise FileNotFoundError(f"Prepared data missing: {input_path}. See README dataset preparation.")
        labels = pd.read_parquet(input_path, columns=["Label"]).Label
        attacks = labels.str.lower().ne("benign").to_numpy().nonzero()[0]
        if not len(attacks):
            raise ValueError(f"No labelled attack examples available in {dataset}")
        index = int(attacks[0])
        for task in ("binary", "multiclass"):
            for model in ("random_forest", "xgboost"):
                name = f"{dataset}_{task}_{model}"
                artifact = ROOT / "outputs" / "recent2025" / "models" / f"{name}.joblib"
                if not artifact.exists():
                    raise FileNotFoundError(f"Saved model missing: {artifact}. See README training instructions.")
                print(f"Explaining {name} ...", flush=True)
                markdown, structured = explain_alert(artifact, input_path, index, destination / name)
                report = json.loads(structured.read_text())
                rows.append(dict(dataset=dataset, task=task, model=model, row=index,
                                 actual_label=str(labels.iloc[index]), **report["alert"],
                                 evidence_tier=report["evidence_tier"], report=str(markdown)))
                print(f"  Prediction: {report['alert']['predicted_class']}; explanation: {report['evidence_tier']}", flush=True)
    (destination / "demo_summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nFinished {len(rows)} saved-model demonstrations. Reports: {destination}")
    print("These are selected test examples, not a new accuracy evaluation or live traffic monitoring.")


if __name__ == "__main__":
    main()
