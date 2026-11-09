"""Verify and summarize the second external capture."""
import json
from pathlib import PureWindowsPath

import numpy as np
import pandas as pd

from .benchmark import sha256


def load_independent_tcp(root):
    directory = root / "outputs/independent_tcp"
    manifest = json.loads((directory / "manifest.json").read_text())
    inputs = {}
    for name, digest in manifest["input_hashes"].items():
        runner = PureWindowsPath(name)
        if runner.is_absolute() and runner.name == "run_independent_tcp.py":
            name = runner.name
        inputs[root / name] = digest
    for path, expected in {
        **inputs,
        **{directory / name: digest for name, digest in manifest["outputs"].items()},
    }.items():
        if sha256(path) != expected:
            raise ValueError(f"Independent capture audit checksum differs: {path}")
    metrics = pd.read_csv(directory / "metrics.csv")
    coverage = pd.read_csv(directory / "coverage.csv")
    keys = ["subset", "feature_set", "model"]
    variants = {("lookup", "protocol_majority"),
                *((spec, model) for spec in ("transport", "transport_volume")
                  for model in ("random_forest", "xgboost"))}
    subsets = {"all", "TCP"}
    if manifest["mixed_port_pair_rows"]:
        subsets.add("TCP_mixed_port_pair")
    expected = {(subset, spec, model) for subset in subsets for spec, model in variants}
    if metrics.duplicated(keys).any() or set(metrics[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Independent capture model coverage differs")
    for name, table in (("all", coverage), ("TCP", coverage[coverage.protocol.eq(6)])):
        counts = metrics[metrics.subset.eq(name)]
        normal = table.loc[table.label.eq("Normal"), "rows"].sum()
        if not (counts.benign.eq(normal) & counts.attacks.eq(table.rows.sum() - normal)).all():
            raise ValueError(f"Independent capture label counts differ: {name}")
    if (coverage.rows.sum() != manifest["raw_rows"] or
        not metrics[metrics.subset.eq("TCP_mixed_port_pair")].test_rows.eq(manifest["mixed_port_pair_rows"]).all() or
        not metrics.test_rows.eq(metrics.attacks + metrics.benign).all()):
        raise ValueError("Independent capture row totals differ")
    if ((metrics.missed < 0) | (metrics.missed > metrics.attacks) |
        (metrics.false_alarms < 0) | (metrics.false_alarms > metrics.benign)).any():
        raise ValueError("Independent capture confusion counts are out of bounds")
    tp, tn = metrics.attacks - metrics.missed, metrics.benign - metrics.false_alarms
    errors = metrics.missed + metrics.false_alarms
    np.testing.assert_allclose(metrics.macro_f1, tp / (2 * tp + errors) + tn / (2 * tn + errors))
    np.testing.assert_allclose(metrics.fpr, metrics.false_alarms / metrics.benign)
    np.testing.assert_allclose(metrics.attack_recall, tp / metrics.attacks)
    return metrics, coverage, manifest


def manuscript_text(root):
    metrics, coverage, manifest = load_independent_tcp(root)
    tcp = metrics[metrics.subset.eq("TCP")].set_index(["feature_set", "model"])
    rf = tcp.loc["transport", "random_forest"]
    xgb = tcp.loc["transport", "xgboost"]
    rule = tcp.loc["lookup", "protocol_majority"]
    matched = metrics[(metrics.subset.eq("TCP_mixed_port_pair")) & metrics.feature_set.eq("transport")]
    if len(matched):
        row = matched.iloc[0]
        alarm_range = (f"{matched.false_alarms.min():,}" if matched.false_alarms.nunique() == 1
                       else f"{matched.false_alarms.min():,} to {matched.false_alarms.max():,}")
        port_sentence = (
            f"Exact unordered TCP port pairs carrying both labels cover {row.test_rows:,} flows "
            f"({row.attacks:,} attack and {row.benign:,} benign). The transport trees flag "
            f"{alarm_range} of those benign flows."
        )
    else:
        port_sentence = "No exact unordered TCP port pair carries both labels in the release."
    web = coverage.loc[coverage.protocol.eq(6) & coverage.label.eq("Web_Attack"), "rows"].sum()
    return [
        "We added an independent protocol-matched evaluation using the provider's PDMFC v1 capture "
        "[39], exported from pfSense traffic with CICFlowMeter. We verify the complete CSV against the "
        "publisher checksum and use its populated lowercase annotation field. Models, weighting, "
        "preprocessing and decisions are carried over from the GeNIS-only transfer configuration. "
        "The rebuilt fits reproduce the saved OCPP full-capture and TCP confusion counts before "
        "PDMFC scoring. The primary diagnostic includes all TCP flows in the release.",
        f"The TCP cohort contains {rf.attacks:,} attack and {rf.benign:,} benign flows. Random Forest "
        f"and XGBoost with protocol and ports raise {rf.false_alarms:,} and {xgb.false_alarms:,} false "
        f"alarms ({rf.fpr:.1%} and {xgb.fpr:.1%}) and miss {rf.missed:,} and {xgb.missed:,} attacks, "
        f"respectively. The protocol-only control flags {rule.false_alarms:,} benign flows and misses "
        f"{rule.missed:,} attacks. {port_sentence}",
        f"PDMFC contributes one separately collected file with {manifest['raw_rows']:,} flows. "
        f"The provider labels {web:,} of its TCP attacks as Web Attack. "
        "The provider labels and error rates are descriptive of this release. Protocol matching "
        "does not control endpoints, traffic mix or capture conditions, and repeated flows within "
        "the capture are not independent replications."
    ]
