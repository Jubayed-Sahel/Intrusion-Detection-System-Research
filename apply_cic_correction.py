"""Merge the scoped CIC correction while retaining historical evidence."""
import json
import shutil
from pathlib import Path

import pandas as pd

from src.xai_ids.benchmark import fidelity_control_tests, make_summary_plots, paired_bootstrap_comparisons, save_confusion_plot


def main():
    destination, source = Path("outputs"), Path("outputs/cic_multiclass_correction")
    backup = destination / "before_cic_feature_overlap_correction"
    backup.mkdir(exist_ok=False)
    for file in destination.glob("*.csv"):
        shutil.copy2(file, backup / file.name)
    shutil.copy2(destination / "run_manifest.json", backup / "run_manifest.json")
    shutil.copy2("output/pdf/xai_ids_ieee_paper.pdf", backup / "manuscript.pdf")
    for file in source.glob("*.csv"):
        if file.name in {"paired_comparisons.csv", "fidelity_control_tests.csv"}:
            continue
        replacement = pd.read_csv(file)
        assert set(replacement.dataset) == {"CIC-IDS2017"}
        assert set(replacement.task) == {"multiclass"}
        original = pd.read_csv(destination / file.name)
        keep = ~((original.dataset == "CIC-IDS2017") & (original.task == "multiclass"))
        pd.concat([original[keep], replacement], ignore_index=True).to_csv(destination / file.name, index=False)
    fidelity = pd.read_csv(destination / "fidelity.csv")
    paired_bootstrap_comparisons(fidelity, 42).to_csv(destination / "paired_comparisons.csv", index=False)
    fidelity_control_tests(fidelity, 42).to_csv(destination / "fidelity_control_tests.csv", index=False)
    manifest = json.loads((destination / "run_manifest.json").read_text())
    correction = json.loads((source / "run_manifest.json").read_text())
    manifest["datasets"]["CIC-IDS2017/multiclass"] = correction["datasets"]["CIC-IDS2017/multiclass"]
    manifest["corrections"] = [{"date": "2026-10-14", "context": "CIC-IDS2017/multiclass",
        "reason": "target-independent feature overlap in one test row",
        "source_manifest": str(source / "run_manifest.json"), "environment": correction["environment"],
        "latency_note": "correction and validation jobs may contend for CPU; new latency is descriptive"}]
    (destination / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for model in (source / "models").glob("*.joblib"):
        shutil.copy2(model, destination / "models" / model.name)
    confusion = pd.read_csv(destination / "confusion_matrices.csv")
    for (dataset, task, model), group in confusion.groupby(["dataset", "task", "model"]):
        classes = list(group.actual_class.unique())
        matrix = group.pivot(index="actual_class", columns="predicted_class", values="count").reindex(index=classes, columns=classes).to_numpy()
        safe = f"{dataset}_{task}_{model}".replace("-", "_")
        save_confusion_plot(matrix, classes, f"{dataset}: {task}, {model}", destination / "figures" / f"confusion_{safe}.png")
    make_summary_plots(destination)
    print("Merged corrected CIC multiclass evidence; historical files preserved.")


if __name__ == "__main__":
    main()
