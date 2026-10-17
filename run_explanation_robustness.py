"""Post-hoc sign and influence sensitivity; never changes frozen primary results."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest


def holm(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1, np.maximum.accumulate(
        values[order] * np.arange(len(values), 0, -1)))
    return adjusted


def group_differences(frame, budgets):
    top = frame[frame.control.eq("top")].copy()
    keys = ["explainer", "source_test_index", "k"]
    if top.duplicated(keys).any():
        raise ValueError("Duplicate explanation/record/budget observations")
    if not np.isfinite(top.probability_drop).all():
        raise ValueError("Nonfinite deletion values")
    if set(top.explainer) != {"TreeSHAP", "LIME"}:
        raise ValueError("Both explainers are required")
    groups = top.groupby("source_test_index").connection_group.nunique()
    if not groups.eq(1).all() or top.connection_group.isna().any():
        raise ValueError("Each record must belong to exactly one connection")
    counts = top.groupby(["explainer", "source_test_index"]).k.agg(set)
    if not counts.map(lambda values: values == set(budgets)).all():
        raise ValueError("Incomplete masking budgets")
    paired = top.pivot(index=["connection_group", "source_test_index", "k"],
                       columns="explainer", values="probability_drop")
    if paired.isna().any().any():
        raise ValueError("Unmatched explanation records")
    # Match the primary endpoint: mean packets within connection/budget,
    # then mean budgets, then equal weight for each connection.
    differences = paired.TreeSHAP - paired.LIME
    return differences.groupby(level=[0, 2]).mean().groupby(level=0).mean()


def sensitivity(values, tolerance=1e-12):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("At least two finite connection differences required")
    positive = int((values > tolerance).sum())
    negative = int((values < -tolerance).sum())
    nonzero = positive + negative
    leave_one_out = (values.sum() - values) / (len(values) - 1)
    return dict(n_groups=len(values), mean_difference=float(values.mean()),
                median_difference=float(np.median(values)), positive_groups=positive,
                negative_groups=negative, tied_groups=len(values)-nonzero,
                sign_two_sided_p=float(binomtest(positive, nonzero, .5).pvalue) if nonzero else 1.,
                loo_mean_min=float(leave_one_out.min()),
                loo_mean_max=float(leave_one_out.max()),
                single_group_can_reverse_mean=bool(
                    (values.mean() > 0 and leave_one_out.min() <= 0) or
                    (values.mean() < 0 and leave_one_out.max() >= 0)))


def run(results, output):
    manifest = json.loads((results / "run_manifest.json").read_text())
    primary = pd.read_csv(results / "paired_comparisons.csv", float_precision="round_trip")
    keys = ["dataset", "task", "model", "model_seed"]
    expected = {(d, t, m, s) for d in manifest["config"]["datasets"]
                for t in ("binary", "multiclass") for m in manifest["config"]["models"]
                for s in manifest["config"]["explanation_model_seeds"]}
    if primary.duplicated(keys).any() or set(primary[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Primary context coverage is incomplete or duplicated")
    sources = {}
    rows = []
    def record(path):
        # Keep audit keys portable when run from Windows or Linux checkouts.
        resolved = path.resolve()
        project_root = Path(__file__).resolve().parent
        key = resolved.relative_to(project_root).as_posix() if resolved.is_relative_to(project_root) else resolved.as_posix()
        sources[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    record(results / "run_manifest.json")
    record(results / "paired_comparisons.csv")
    record(Path(__file__))
    for row in primary.itertuples(index=False):
        path = results / "contexts" / f"{row.dataset}_{row.task}_{row.model}_{row.model_seed}" / "fidelity.csv"
        record(path)
        frame = pd.read_csv(path, float_precision="round_trip")
        for key in keys:
            if set(frame[key]) != {getattr(row, key)}:
                raise ValueError(f"Context identity mismatch: {path}: {key}")
        values = group_differences(frame, manifest["config"]["evaluation"]["fidelity_k"])
        result = sensitivity(values)
        if len(values) != row.n_pairs or not np.isclose(result["mean_difference"], row.mean_difference_shap_minus_lime, rtol=0, atol=1e-12):
            raise ValueError(f"Primary endpoint reproduction failed: {path}")
        rows.append({**{key: getattr(row, key) for key in keys}, **result})
    table = pd.DataFrame(rows)
    table["sign_holm_p_24_contexts"] = holm(table.sign_two_sided_p)
    output.mkdir(parents=True, exist_ok=True)
    table.to_csv(output / "sensitivity.csv", index=False)
    summary = dict(contexts=len(table), positive_means=int(table.mean_difference.gt(0).sum()),
                   positive_sign_test_holm=int(((table.sign_holm_p_24_contexts < .05) & (table.positive_groups > table.negative_groups)).sum()),
                   negative_sign_test_holm=int(((table.sign_holm_p_24_contexts < .05) & (table.negative_groups > table.positive_groups)).sum()),
                   single_group_reversals=int(table.single_group_can_reverse_mean.sum()))
    (output / "manifest.json").write_text(json.dumps(dict(
        analysis="Post-hoc sensitivity, separate from the primary confirmatory families",
        tie_tolerance=1e-12, sign_null="Equal positive/negative probability conditional on non-tied explained groups",
        caveats="Sign test targets direction frequency, not mean magnitude. Groups may retain dependence. Seeds share data; no pooling or external generalization. Leave-one-out is descriptive, not a confidence interval.",
        summary=summary, sha256=sources), indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("outputs/recent2025"))
    parser.add_argument("--output", type=Path, default=Path("outputs/explanation_robustness"))
    args = parser.parse_args()
    run(args.results, args.output)
