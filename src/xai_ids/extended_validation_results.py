"""Replay and summarize the uncapped and OCPP results for publication."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "outputs/extended_validation_20261108"
DOI = "10.21227/v1f0-9t13"


def checked(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for file, digest in manifest["outputs"].items():
        if hashlib.sha256((directory / file).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Result hash changed: {directory / file}")
    return manifest


def load_extended():
    coverage = []
    folds = []
    keys = ["dataset", "fold", "task", "model"]
    for dataset, n_sources in (("GeNIS2025", 8), ("Gotham2025", 65)):
        path = RESULTS / f"uncapped_{dataset}"
        manifest = checked(path)
        cover = pd.read_csv(path / "coverage.csv")
        scores = pd.read_csv(path / "metrics.csv")
        counts = pd.read_csv(path / "confusion.csv")
        if (manifest["contexts"], manifest["sources"], len(scores), len(cover)) != (32, n_sources, 32, n_sources):
            raise ValueError("Incomplete uncapped fold or source coverage")
        if cover.source.duplicated().any() or not cover.raw.eq(cover.unknown + cover.group_excluded + cover.eligible).all():
            raise ValueError("Uncapped source coverage does not reconcile")
        reference = scores.set_index(keys, verify_integrity=True)
        for context, frame in counts.groupby(keys):
            matrix = frame.pivot(index="actual", columns="predicted", values="count")
            if matrix.isna().any().any() or not matrix.index.equals(matrix.columns):
                raise ValueError("Incomplete confusion matrix")
            m = matrix.to_numpy()
            support = m.sum(axis=1)
            use = support > 0
            f1 = (2 * m.diagonal()[use] / (support + m.sum(axis=0))[use]).mean()
            row = reference.loc[context]
            eligible = cover.loc[cover.fold.eq(context[1]), "eligible"].sum()
            if m.sum() != row.test_rows or m.sum() != eligible or not np.isclose(row.macro_f1, f1, atol=1e-12, rtol=0):
                raise ValueError("Uncapped scores do not replay")
        if len(counts[keys].drop_duplicates()) != 32 or cover.eligible.sum() != manifest["eligible"]:
            raise ValueError("Incomplete uncapped confusion or row counts")
        coverage.append(cover)
        folds.append(scores)
    path = RESULTS / "external"
    manifest = checked(path)
    external = pd.read_csv(path / "metrics.csv")
    by_label = pd.read_csv(path / "per_label.csv")
    contexts = ["feature_set", "model", "test"]
    reference = external.set_index(contexts, verify_integrity=True)
    if len(reference) != 8 or len(by_label[contexts].drop_duplicates()) != 8 or manifest["rows"] != 4415:
        raise ValueError("Incomplete external test coverage")
    for context, group in by_label.groupby(contexts):
        label = "normal" if context[-1] == "OCPP" else "benign"
        normal = group.label.eq(label)
        errors = group.rows - group.correct
        row = reference.loc[context]
        if (row.test_rows, row.missed, row.false_alarms) != (group.rows.sum(), errors[~normal].sum(), errors[normal].sum()):
            raise ValueError("External per-class errors do not replay")
    return pd.concat(coverage), pd.concat(folds), external


def large_test_finding(coverage, folds):
    rows = coverage.groupby("dataset").eligible.sum()
    binary = folds[folds.task.eq("binary")].groupby("dataset").macro_f1.agg(["min", "max"])
    return (f"Uncapped scoring retains {rows['GeNIS2025']:,} GeNIS and {rows['Gotham2025']:,} Gotham records "
            f"after label and connection exclusions. Binary macro-F1 spans {binary.loc['GeNIS2025','min']:.3f}-{binary.loc['GeNIS2025','max']:.3f} "
            f"across GeNIS fold-model contexts and {binary.loc['Gotham2025','min']:.3f}-{binary.loc['Gotham2025','max']:.3f} across Gotham contexts.")
