"""Validate and summarize the GeNIS training-size experiment."""
import json
from pathlib import PureWindowsPath

import numpy as np
import pandas as pd

from .benchmark import sha256


def load_training_scale(root):
    directory = root / "outputs/training_scale"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["inputs"].items():
        runner = PureWindowsPath(name)
        if runner.is_absolute() and runner.name == "run_training_scale.py":
            name = runner.name
        if sha256(root / name) != digest:
            raise ValueError(f"Training-size input checksum differs: {name}")
    path = directory / "metrics.csv"
    if sha256(path) != manifest["metrics_sha256"]:
        raise ValueError("Training-size metrics checksum differs")
    metrics = pd.read_csv(path, float_precision="round_trip")
    keys = ["fold", "model", "train_rows"]
    expected = {(fold, model, size) for fold in range(1, 9)
                for model in ("random_forest", "xgboost") for size in (10_000, 40_000, 160_000)}
    if len(metrics) != manifest["contexts"] or metrics.duplicated(keys).any() or (
        set(metrics[keys].itertuples(index=False, name=None)) != expected
    ):
        raise ValueError("Incomplete training-size model coverage")
    for fold, table in metrics.groupby("fold"):
        checkpoint = json.loads((directory / f"fold_{fold}.json").read_text(encoding="utf-8"))
        if checkpoint["signature"] != {k: manifest[k] for k in ("archive_sha256", "members", "inputs")}:
            raise ValueError(f"Training-size fold signature differs: {fold}")
        pd.testing.assert_frame_equal(table.reset_index(drop=True), pd.DataFrame(checkpoint["rows"]),
                                      check_like=True)
    fixed = metrics.groupby("fold")[["test_rows", "attacks", "benign", "pool_rows"]].nunique()
    if not fixed.eq(1).all().all():
        raise ValueError("Training-size comparisons require identical test and pool coverage")
    source = pd.read_csv(root / "outputs/extended_validation_20261108/uncapped_GeNIS2025/coverage.csv")
    expected_rows = source.set_index("fold")["raw"]
    if (metrics.fold.map(expected_rows) != metrics.test_rows).any():
        raise ValueError("Training-size test cohorts must cover complete author files")
    if (metrics.test_rows != metrics.attacks + metrics.benign).any() or (
        (metrics.missed < 0) | (metrics.false_alarms < 0) |
        (metrics.missed > metrics.attacks) | (metrics.false_alarms > metrics.benign)
    ).any():
        raise ValueError("Invalid training-size confusion counts")
    tp, tn = metrics.attacks - metrics.missed, metrics.benign - metrics.false_alarms
    errors = metrics.missed + metrics.false_alarms
    np.testing.assert_allclose(metrics.macro_f1, tp / (2 * tp + errors) + tn / (2 * tn + errors),
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(metrics.attack_recall, tp / metrics.attacks, rtol=0, atol=1e-12)
    np.testing.assert_allclose(metrics.fpr, metrics.false_alarms / metrics.benign, rtol=0, atol=1e-12)
    return metrics


def manuscript_text(root):
    metrics = load_training_scale(root)
    totals = metrics.drop_duplicates("fold").test_rows.sum()
    details = []
    for name, model in metrics.groupby("model"):
        label = {"random_forest": "Random Forest", "xgboost": "XGBoost"}[name]
        paired = model.pivot(index="fold", columns="train_rows", values="macro_f1")
        delta = paired[160_000] - paired[10_000]
        means = ", ".join(f"{n:.3f}" for n in paired.mean())
        details.append(
            f"{label} equal-scenario mean macro-F1 is {means} at 10,000, 40,000, and 160,000 rows. "
            f"The largest cohort improves over the smallest in {delta.gt(1e-12).sum()}/8 scenarios "
            f"and declines in {delta.lt(-1e-12).sum()}/8 "
            f"(paired change {delta.min():+.3f} to {delta.max():+.3f})."
        )
    scenario = metrics[metrics.fold.eq(4) & metrics.model.eq("xgboost")].sort_values("train_rows")
    misses = [int(n) for n in scenario.missed]
    benign_train = [int(n) for n in scenario.train_rows - scenario.train_attacks]
    attacks = int(scenario.attacks.iloc[0])
    return [
        "We tested binary detector sensitivity to training size in the eight GeNIS source holdouts. "
        "Uniform nested training samples of 10,000, 40,000, and 160,000 rows per fold come from the other "
        "seven files after excluding every row whose FlowID appears anywhere in the held-out file. "
        "Raw class mix is preserved in expectation, and the original model weighting, settings, and seed 42 "
        "are fixed. Preprocessing is fitted separately on each training prefix. Within each fold, all sizes "
        f"score exactly the same complete source file. Together these files contain {totals:,} test rows.",
        " ".join(details),
        f"In GeNIS scenario 4, XGBoost misses {misses[0]:,}, {misses[1]:,}, and {misses[2]:,} of "
        f"{attacks:,} attacks as training size increases. The corresponding training cohorts contain "
        f"only {benign_train[0]}, {benign_train[1]}, and {benign_train[2]} benign rows. "
        "This is a post-hoc, descriptive GeNIS analysis "
        "with overlapping training pools and one nested draw per scenario. Larger samples can add coverage "
        "of different connections and attack categories. This experiment addresses binary detection "
        "under scenario separation within one testbed."
    ]
