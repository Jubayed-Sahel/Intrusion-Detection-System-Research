"""Small isolated offline timing pilot for the complete alert-report CLI path."""
import json
import platform
import time
from pathlib import Path

import pandas as pd
import yaml

from src.xai_ids.benchmark import prepare_dataset, stratified_indices
from src.xai_ids.transparency import explain_alert


def main():
    config = yaml.safe_load(Path("config.yaml").read_text())
    output = Path("outputs/research_validation_corrected/operational_pilot")
    output.mkdir(parents=True, exist_ok=True)
    inputs = Path("tmp/operational_pilot")
    inputs.mkdir(parents=True, exist_ok=True)
    rows = []
    for dataset in ("CIC-IDS2017", "UNSW-NB15"):
        for task in ("binary", "multiclass"):
            _, test, _, y_test, _, _ = prepare_dataset(dataset, task, config, 42)
            indices = stratified_indices(y_test, 3, 42)
            input_path = inputs / f"{dataset}_{task}.csv"
            test.iloc[indices].to_csv(input_path, index=False)
            for model in ("random_forest", "xgboost"):
                safe = f"{dataset}_{task}_{model}".replace("-", "_")
                artifact = Path("outputs/models") / f"{safe}.joblib"
                print(f"[pipeline pilot] {safe}", flush=True)
                for index, source_index in enumerate(indices):
                    report_base = output / f"{safe}_{index}"
                    start = time.perf_counter()
                    _, report_path = explain_alert(artifact, input_path, index, report_base, random_trials=200)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    report = json.loads(report_path.read_text())
                    rows.append({"dataset": dataset, "task": task, "model": model,
                                 "source_test_index": int(source_index), "elapsed_ms": elapsed_ms,
                                 "evidence_tier": report["evidence_tier"], "random_trials": 200})
                    # Preserve each observation even if a later configuration fails.
                    pd.DataFrame(rows).to_csv(output / "observations.csv", index=False)
    result = pd.DataFrame(rows)
    result.groupby(["dataset", "task", "model"]).elapsed_ms.agg(["count", "median", "min", "max"]).to_csv(output / "timing_summary.csv")
    (output / "protocol.json").write_text(json.dumps({"mode": "sequential offline CLI-style invocations; artifact and input read on every call; OS cache not flushed",
        "scope": "model load, CSV load, preprocessing, prediction, SHAP, 200 local random controls, context read, JSON/Markdown serialization",
        "samples_per_configuration": 3, "host": platform.platform(),
        "local_controls": "batched predictions, 200 permutations, conservative 1e-12 near-tie tolerance",
        "excluded": ["network ingestion", "queueing", "concurrency", "live traffic", "drift"],
        "interpretation": "small pilot; do not estimate tail percentiles or sustained throughput"}, indent=2))
    print(f"[pilot complete] {output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
