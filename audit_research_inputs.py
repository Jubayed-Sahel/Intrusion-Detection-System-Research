"""Audit feature overlap and class failures in the existing benchmark."""
import json
from pathlib import Path

import pandas as pd
import yaml

from src.xai_ids.benchmark import TabularPreprocessor, prepare_dataset, load_unsw


def main():
    config = yaml.safe_load(Path("config.yaml").read_text())
    destination = Path("outputs/research_validation")
    destination.mkdir(parents=True, exist_ok=True)
    overlap = []
    for dataset in ("CIC-IDS2017", "UNSW-NB15"):
        for task in ("binary", "multiclass"):
            train, test, _, _, _, metadata = prepare_dataset(dataset, task, config, 42)
            names = metadata["feature_names"]
            preprocessor = TabularPreprocessor(names).fit(train)
            raw_train = pd.util.hash_pandas_object(train[names], index=False)
            raw_test = pd.util.hash_pandas_object(test[names], index=False)
            encoded_train = pd.util.hash_pandas_object(pd.DataFrame(preprocessor.transform(train)), index=False)
            encoded_test = pd.util.hash_pandas_object(pd.DataFrame(preprocessor.transform(test)), index=False)
            overlap.append({"dataset": dataset, "task": task,
                            "raw_test_overlap_rows": int(raw_test.isin(raw_train).sum()),
                            "transformed_test_overlap_rows": int(encoded_test.isin(encoded_train).sum())})
    pd.DataFrame(overlap).to_csv(destination / "feature_overlap_audit.csv", index=False)
    print(pd.DataFrame(overlap).to_string(index=False), flush=True)
    per_class = pd.read_csv("outputs/per_class_metrics.csv")
    minority = per_class[(per_class.dataset == "UNSW-NB15") & (per_class.task == "multiclass")]
    grouped = minority.groupby(["model", "class"]).agg(
        recall_mean=("recall", "mean"), recall_min=("recall", "min"), recall_max=("recall", "max"),
        f1_mean=("f1", "mean"), support=("support", "first"), seeds=("seed", "nunique"))
    grouped.sort_values("recall_mean").to_csv(destination / "minority_class_audit.csv")
    confusion = pd.read_csv("outputs/confusion_matrices.csv")
    confusion = confusion[(confusion.dataset == "UNSW-NB15") & (confusion.task == "multiclass") & (confusion.actual_class != confusion.predicted_class)]
    errors = confusion.sort_values("count", ascending=False).groupby(["model", "actual_class"], sort=False).head(1)
    errors.to_csv(destination / "largest_class_confusions.csv", index=False)
    (destination / "input_audit.json").write_text(json.dumps({"feature_overlap": overlap,
        "method": "64-bit pandas row hashes, target columns excluded; hash-based screening",
        "minority_scope": "five committed predictive seeds; confusion destinations seed 42 only"}, indent=2))
    unsw = config["data"]["unsw_nb15"]
    clean_train, clean_test, _ = load_unsw(unsw)
    distributions, conflicts = [], []
    for partition, raw_path, clean_frame in (("train", unsw["train"], clean_train), ("test", unsw["test"], clean_test)):
        raw_frame = pd.read_parquet(raw_path)
        for attack in sorted(set(raw_frame.attack_cat)):
            original_count = int((raw_frame.attack_cat == attack).sum())
            retained_count = int((clean_frame.attack_cat == attack).sum())
            distributions.append({"partition": partition, "class": attack, "original_rows": original_count,
                                  "retained_rows": retained_count, "removed_fraction": 1 - retained_count / original_count})
        features = [name for name in clean_frame if name not in {"attack_cat", "label"}]
        hashes = pd.util.hash_pandas_object(clean_frame[features], index=False)
        for target in ("label", "attack_cat"):
            counts = clean_frame[target].groupby(hashes).nunique()
            conflicting_keys = counts[counts > 1].index
            conflicts.append({"partition": partition, "target": target,
                              "conflicting_feature_vectors": len(conflicting_keys),
                              "rows_in_conflicting_vectors": int(hashes.isin(conflicting_keys).sum())})
    pd.DataFrame(distributions).to_csv(destination / "unsw_cleaning_by_class.csv", index=False)
    pd.DataFrame(conflicts).to_csv(destination / "unsw_label_conflicts.csv", index=False)
    print(pd.DataFrame(conflicts).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
