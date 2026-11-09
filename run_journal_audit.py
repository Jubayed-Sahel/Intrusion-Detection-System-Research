"""Replay verified capture inputs and audit transport-only transfer baselines."""
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight

from run_extended_validation import OUT as EXTENDED, harmonize, scores, sha256, source
from src.xai_ids.benchmark import TabularPreprocessor, make_model

OUTPUT = Path("outputs/journal_audit_20261109")
PROTOCOL = Path("Q1_VALIDATION_PROTOCOL.md")
KEY = ["protocol", "port_low", "port_high"]


def keys(frame):
    return frame[KEY].fillna(-1)


def majority(train, attack):
    counts = train.assign(attack=attack).groupby(list(train.columns)).attack.agg(["sum", "size"])
    return counts["sum"] > counts["size"] / 2


def predictions(train, attack, test):
    protocol = majority(train[["protocol"]], attack)
    pairs = majority(train, attack)
    fallback = test.protocol.map(protocol).eq(True).to_numpy()
    matched = pairs.reindex(pd.MultiIndex.from_frame(test))
    seen = matched.notna().to_numpy()
    exact = np.where(seen, matched.eq(True), fallback)
    return fallback, exact, seen


def prevalence_projection(recall, false_positive_rate, prevalence):
    true_alerts = recall * prevalence
    false_alerts = false_positive_rate * (1 - prevalence)
    total = true_alerts + false_alerts
    return (true_alerts / total if total else None, 10_000 * false_alerts)


def run():
    previous = EXTENDED / "external"
    manifest = json.loads((previous / "manifest.json").read_text())
    archive = Path("data/official/14887131/Balanced_OCPP16_TCP-IP_Layer.zip")
    source.load_primary("GeNIS2025")
    for name, digest in manifest["geNIS_prepared"].items():
        if sha256(Path("data/prepared/GeNIS2025") / name) != digest:
            raise ValueError(f"Prepared data differ from the transfer study: {name}")
    metrics = previous / "metrics.csv"
    if sha256(metrics) != manifest["outputs"][metrics.name] or sha256(archive) != manifest["archive_sha256"]:
        raise ValueError("Transfer metrics or archive differ from the verified inputs")
    train, test = (pd.read_parquet(Path("data/prepared/GeNIS2025") / name)
                   for name in ("train.parquet", "test.parquet"))
    train_keys = keys(harmonize(train, False))
    train_attack = train.Label.str.lower().ne("benign").to_numpy()
    with zipfile.ZipFile(archive) as zipped:
        target = pd.concat([pd.read_csv(zipped.open(name)) for name in manifest["members"]],
                           ignore_index=True)
    if target.Label.value_counts().to_dict() != manifest["labels"]:
        raise ValueError("External label support differs from the transfer study")

    results, coverage, protocol_counts = [], [], []
    for proto in sorted(train_keys.protocol.unique()):
        mask = train_keys.protocol.eq(proto).to_numpy()
        protocol_counts.append(dict(split="GeNIS train", protocol=proto,
                                    attacks=int(train_attack[mask].sum()),
                                    benign=int((~train_attack[mask]).sum())))
    for name, frame, benign in (("GeNIS", test, "benign"), ("OCPP", target, "normal")):
        labels = frame.Label.str.lower().to_numpy()
        truth = labels != benign
        test_keys = keys(harmonize(frame, name == "OCPP"))
        protocol, pair, seen = predictions(train_keys, train_attack, test_keys)
        for proto in sorted(test_keys.protocol.unique()):
            mask = test_keys.protocol.eq(proto).to_numpy()
            protocol_counts.append(dict(split=name, protocol=proto, attacks=int(truth[mask].sum()),
                                        benign=int((~truth[mask]).sum())))
        for model, pred in (("protocol_majority", protocol), ("pair_majority", pair)):
            matrix = confusion_matrix(truth, pred, labels=[True, False])
            results.append(dict(test=name, model=model, **scores(matrix, ["Attack", "Normal"])))
        for label in sorted(set(labels)):
            mask = labels == label
            coverage.append(dict(test=name, label=label, rows=int(mask.sum()),
                                 seen_pair=int(seen[mask].sum()),
                                 pair_errors=int((pair[mask] != truth[mask]).sum())))

    all_metrics = pd.concat([
        pd.DataFrame(results).assign(feature_set="lookup"),
        pd.read_csv(metrics),
    ], ignore_index=True)
    train_features = harmonize(train, False)
    target_features = harmonize(target, True)
    truth = target.Label.str.lower().ne("normal").to_numpy()
    tcp = target_features.protocol.eq("6").to_numpy()
    protocol, pair, _ = predictions(train_keys, train_attack, keys(target_features))
    tcp_results = []
    for model, pred in (("protocol_majority", protocol), ("pair_majority", pair)):
        matrix = confusion_matrix(truth[tcp], pred[tcp], labels=[True, False])
        tcp_results.append(dict(model=model, feature_set="lookup", **scores(matrix, ["Attack", "Normal"])))
    config = yaml.safe_load(Path("config_recent.yaml").read_text())["models"]
    for spec, features in (("transport", KEY), ("transport_volume", list(train_features.columns))):
        pre = TabularPreprocessor(features).fit(train_features)
        x_train, x_target = pre.transform(train_features), pre.transform(target_features)
        y = (~train_attack).astype(int)
        for name in ("random_forest", "xgboost"):
            model = make_model(name, config, 42, 2)
            model.set_params(n_jobs=4)
            weight = compute_sample_weight("balanced", y) if name == "xgboost" else None
            model.fit(x_train, y, sample_weight=weight)
            pred = model.predict(x_target) == 0
            reference = all_metrics.query("test == 'OCPP' and feature_set == @spec and model == @name").iloc[0]
            if ((truth & ~pred).sum(), (~truth & pred).sum()) != (reference.missed, reference.false_alarms):
                raise ValueError(f"Rebuilt model did not match original confusion counts: {spec}/{name}")
            matrix = confusion_matrix(truth[tcp], pred[tcp], labels=[True, False])
            tcp_results.append(dict(model=name, feature_set=spec, **scores(matrix, ["Attack", "Normal"])))
    for row in all_metrics.itertuples():
        if (row.attacks + row.benign != row.test_rows or
            not np.isclose(row.attack_recall, 1 - row.missed / row.attacks) or
            not np.isclose(row.fpr, row.false_alarms / row.benign)):
            raise ValueError("Confusion totals or rates do not reconcile")
    scenarios = []
    for row in all_metrics.itertuples():
        for p in (0.001, 0.01, 0.05):
            ppv, alerts = prevalence_projection(row.attack_recall, row.fpr, p)
            scenarios.append(dict(test=row.test, model=row.model, feature_set=row.feature_set,
                                  prevalence=p, ppv=ppv, false_alerts_per_10000=alerts))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tables = {"metrics.csv": all_metrics, "pair_coverage.csv": pd.DataFrame(coverage),
              "prevalence.csv": pd.DataFrame(scenarios),
              "tcp_metrics.csv": pd.DataFrame(tcp_results),
              "protocol_counts.csv": pd.DataFrame(protocol_counts)}
    for name, table in tables.items():
        table.to_csv(OUTPUT / name, index=False)
    (OUTPUT / "manifest.json").write_text(json.dumps({
        "protocol_sha256": sha256(PROTOCOL), "runner_sha256": sha256(Path(__file__)),
        "transfer_manifest_sha256": sha256(previous / "manifest.json"),
        "outputs": {name: sha256(OUTPUT / name) for name in tables},
    }, indent=2), encoding="utf-8")
    print(all_metrics.to_string(index=False))


if __name__ == "__main__":
    run()
