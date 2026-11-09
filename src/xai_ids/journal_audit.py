"""Read the verified journal follow-up and render its manuscript text."""
import json

import pandas as pd

from .benchmark import sha256


TITLE = "How Traffic Sources and Feature Masking Shape Explainable Intrusion Detection"


def manuscript_text(root):
    audit = root / "outputs/journal_audit_20261109"
    manifest = json.loads((audit / "manifest.json").read_text(encoding="utf-8"))
    dependencies = {
        root / "Q1_VALIDATION_PROTOCOL.md": manifest["protocol_sha256"],
        root / "run_journal_audit.py": manifest["runner_sha256"],
        root / "outputs/extended_validation_20261108/external/manifest.json":
            manifest["transfer_manifest_sha256"],
        **{audit / name: digest for name, digest in manifest["outputs"].items()},
    }
    for path, digest in dependencies.items():
        if sha256(path) != digest:
            raise ValueError(f"Journal audit checksum mismatch: {path}")
    metrics = pd.read_csv(audit / "metrics.csv")
    target = metrics[metrics.test.eq("OCPP")]
    rule = target[target.model.eq("protocol_majority")].iloc[0]
    pair = target[target.model.eq("pair_majority")].iloc[0]
    trees = target[target.feature_set.eq("transport")]
    rates = pd.read_csv(audit / "prevalence.csv")
    projected = rates[rates.test.eq("OCPP") & rates.prevalence.eq(0.01)]
    proj_rule = projected[projected.model.eq("protocol_majority")].iloc[0]
    proj_trees = projected[projected.feature_set.eq("transport")]
    protocols = pd.read_csv(audit / "protocol_counts.csv")
    tcp = protocols[protocols.split.eq("OCPP") & protocols.protocol.eq(6)].iloc[0]
    tcp_metrics = pd.read_csv(audit / "tcp_metrics.csv")
    tcp_trees = tcp_metrics[tcp_metrics.feature_set.eq("transport")]
    tcp_alerts = tcp_trees.false_alarms.unique()
    if len(tcp_alerts) != 1:
        raise ValueError("The TCP-only tree false-alarm counts differ")
    coverage = pd.read_csv(audit / "pair_coverage.csv")
    seen = coverage[coverage.test.eq("OCPP")].seen_pair.sum()
    abstract = (
        "Intrusion detectors and their explanations can look reliable when evaluation preserves traffic-source "
        "patterns or uses a single feature replacement rule. We audit Random Forest and XGBoost detectors with "
        "TreeSHAP and LIME on the official GeNIS and Gotham 2025 releases. On a frozen connection-group split, "
        "TreeSHAP produces greater target-probability drops in all 24 paired contexts under median/mode replacement "
        "after Holm adjustment. Retained-feature donor replacement substantially reduces the GeNIS gaps, with "
        "three of four intervals including zero. Uncapped, group-purged source tests cover 37,941,390 eligible "
        "records. In one GeNIS scenario, XGBoost misses 10,003 of 11,995 attacks. On an independent "
        f"EV-charging capture, a GeNIS-trained protocol-only rule reaches {rule.macro_f1:.3f} macro-F1, "
        f"compared with {trees.macro_f1.min():.3f} to {trees.macro_f1.max():.3f} for protocol-and-port trees. "
        f"On TCP alone, both trees flag {tcp_alerts[0]} of {tcp.benign} benign flows. "
        "A second external capture reproduces the high TCP false-alarm rate. "
        "The findings distinguish evidence about "
        "detector transfer from evidence about explanation fidelity under a specified replacement rule."
    )
    paragraphs = [
        "To test whether the reduced-feature transfer result required a tree ensemble, we ran two "
        "exploratory controls on the same source and external cohorts. A lookup assigns the training-majority "
        "binary label for the observed protocol or exact protocol and unordered port pair. Unseen pairs back "
        "off to protocol. Ties and unseen protocols predict benign. The rules use unweighted GeNIS training "
        "counts. The external capture was already inspected in the earlier study, so the comparison is retrospective.",
        f"On OCPP, the protocol-only and pair rules reach macro-F1 of {rule.macro_f1:.3f} and "
        f"{pair.macro_f1:.3f}, versus {trees.macro_f1.min():.3f} to {trees.macro_f1.max():.3f} for the "
        f"three-field trees. The protocol rule misses {rule.missed} of {rule.attacks:,} attacks and flags "
        f"{rule.false_alarms} of {rule.benign} benign flows. All {tcp.attacks:,} labeled OCPP attacks use TCP. "
        f"Exact pairs seen in GeNIS training cover only {seen} of {rule.test_rows:,} OCPP flows. "
        "This capture rewards protocol-label association and offers limited evidence that the trees transfer "
        "attack behavior. The control does not identify which features drive the original full models.",
        f"Restricting OCPP to TCP retains all {tcp.attacks:,} attacks and {tcp.benign} benign flows. "
        f"The protocol rule now flags all benign flows, and both three-field trees flag {tcp_alerts[0]} "
        f"of {tcp.benign}. Their TCP-only macro-F1 is "
        f"{tcp_trees.macro_f1.min():.3f} to {tcp_trees.macro_f1.max():.3f}. "
        "For this post-hoc diagnostic, the original source-only tree fits were rebuilt and required to "
        "match the saved full-capture error counts before their TCP-only results were reported.",
        f"Under a hypothetical 1 percent attack prevalence and fixed observed class-conditional rates, "
        f"positive predictive value is {proj_rule.ppv:.1%} for the protocol rule and "
        f"{proj_trees.ppv.min():.1%} to {proj_trees.ppv.max():.1%} for the three-field trees. "
        f"The corresponding expected false-alert counts per 10,000 records are "
        f"{proj_rule.false_alerts_per_10000:,.0f} and "
        f"{proj_trees.false_alerts_per_10000.min():,.0f} to {proj_trees.false_alerts_per_10000.max():,.0f}. "
        "These are base-rate sensitivity calculations [38]. They assume stable conditional rates and "
        "count record alerts, so they do not estimate production analyst workload.",
    ]
    return abstract, paragraphs
