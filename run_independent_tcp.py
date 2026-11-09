"""Replay fixed GeNIS transfer models on an independent provider capture."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight

from run_extended_validation import OUT as EXTENDED, harmonize, scores, source
from run_journal_audit import KEY, OUTPUT as JOURNAL, keys, predictions
from src.xai_ids.benchmark import TabularPreprocessor, make_model, sha256


FILE = Path("data/official/16943481/labeled_cicflow_genelen.csv")
PROVIDER_MD5 = "a409f9e5f840d13dbe0b62a740ddb662"
URL = "https://zenodo.org/records/16943481"
OUT = Path("outputs/independent_tcp")
PROTOCOL = Path("INDEPENDENT_TCP_PROTOCOL.md")
CONFIG = Path("config_recent.yaml")
FEATURES = ["Protocol", "Src Port", "Dst Port", "Flow Duration", "Total Fwd Packet", "Total Bwd packets"]


def measure(truth, pred, mask):
    return scores(confusion_matrix(truth[mask], pred[mask], labels=[True, False]),
                  ["Attack", "Normal"])


def run():
    previous = EXTENDED / "external"
    manifest = json.loads((previous / "manifest.json").read_text())
    journal = json.loads((JOURNAL / "manifest.json").read_text())
    archive = Path("data/official/14887131/Balanced_OCPP16_TCP-IP_Layer.zip")
    train_path = Path("data/prepared/GeNIS2025/train.parquet")
    source.load_primary("GeNIS2025")
    for path, digest in {
        train_path: manifest["geNIS_prepared"][train_path.name],
        archive: manifest["archive_sha256"],
        previous / "metrics.csv": manifest["outputs"]["metrics.csv"],
        JOURNAL / "tcp_metrics.csv": journal["outputs"]["tcp_metrics.csv"],
        previous / "manifest.json": journal["transfer_manifest_sha256"],
    }.items():
        if sha256(path) != digest:
            raise ValueError(f"Historical transfer input changed: {path}")

    raw_train = pd.read_parquet(train_path)
    train = harmonize(raw_train, False)
    attack = raw_train.Label.str.lower().ne("benign").to_numpy()
    y = (~attack).astype(int)
    config = yaml.safe_load(CONFIG.read_text())["models"]
    fitted = {}
    for spec, columns in (("transport", KEY), ("transport_volume", list(train.columns))):
        pre = TabularPreprocessor(columns).fit(train)
        x = pre.transform(train)
        for name in ("random_forest", "xgboost"):
            model = make_model(name, config, 42, 2)
            model.set_params(n_jobs=4)
            weight = compute_sample_weight("balanced", y) if name == "xgboost" else None
            model.fit(x, y, sample_weight=weight)
            fitted[spec, name] = pre, model

    with zipfile.ZipFile(archive) as zipped:
        ocpp = pd.concat([pd.read_csv(zipped.open(name)) for name in manifest["members"]], ignore_index=True)
    ocpp_x = harmonize(ocpp, True)
    ocpp_y = ocpp.Label.ne("normal").to_numpy()
    previous_full = pd.read_csv(previous / "metrics.csv").query("test == 'OCPP'")
    previous_tcp = pd.read_csv(JOURNAL / "tcp_metrics.csv")
    for (spec, name), (pre, model) in fitted.items():
        pred = model.predict(pre.transform(ocpp_x)) == 0
        for reference, mask in ((previous_full, np.ones(len(ocpp), dtype=bool)),
                                (previous_tcp, ocpp_x.protocol.eq("6").to_numpy())):
            row = reference.query("feature_set == @spec and model == @name").iloc[0]
            actual = measure(ocpp_y, pred, mask)
            if any(actual[key] != row[key] for key in ("attacks", "benign", "missed", "false_alarms")):
                raise ValueError(f"Historical confusion counts did not replay: {spec}/{name}")

    with FILE.open("rb") as stream:
        digest = hashlib.file_digest(stream, "md5").hexdigest()
    if digest != PROVIDER_MD5:
        raise ValueError("PDMFC CSV does not match provider checksum")
    target = pd.read_csv(FILE, usecols=[*FEATURES, "Label", "label", "Timestamp"])
    labels = target.label.astype("string").str.strip()
    if labels.isna().any() or labels.eq("").any() or "Normal" not in set(labels):
        raise ValueError("Missing provider labels or benign support")
    truth = labels.ne("Normal").to_numpy(dtype=bool)
    x = harmonize(target, True)
    tcp = x.protocol.eq("6").to_numpy()
    if np.unique(truth[tcp]).size != 2:
        raise ValueError("Both target classes must occur on TCP")
    tcp_pairs = x.loc[tcp, KEY].dropna().assign(attack=truth[x.loc[tcp, KEY].dropna().index])
    mixed = tcp_pairs.groupby(KEY).attack.transform("nunique").eq(2)
    matched = x.index.isin(tcp_pairs.index[mixed])
    masks = {"all": np.ones(len(x), dtype=bool), "TCP": tcp}
    if matched.any():
        masks["TCP_mixed_port_pair"] = matched

    baseline, _, _ = predictions(keys(train), attack, keys(x))
    variants = {("lookup", "protocol_majority"): baseline}
    for (spec, name), (pre, model) in fitted.items():
        variants[spec, name] = model.predict(pre.transform(x)) == 0
    rows = [
        dict(subset=subset, feature_set=spec, model=name, **measure(truth, pred, mask))
        for subset, mask in masks.items()
        for (spec, name), pred in variants.items()
    ]
    coverage = (pd.DataFrame({"protocol": target.Protocol, "label": labels})
                .value_counts().rename("rows").reset_index())
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "metrics.csv", index=False)
    coverage.to_csv(OUT / "coverage.csv", index=False)
    paths = [Path(__file__), PROTOCOL, CONFIG, previous / "manifest.json", JOURNAL / "manifest.json",
             Path("run_extended_validation.py"), Path("run_journal_audit.py"),
             Path("src/xai_ids/benchmark.py")]
    timestamps = pd.to_datetime(target.Timestamp, format="mixed", errors="raise")
    result = dict(provider=URL, csv_sha256=sha256(FILE), provider_md5=digest,
                  input_hashes={p.as_posix(): sha256(p) for p in paths},
                  historical_model_counts_replayed=8, raw_rows=len(x),
                  mixed_port_pair_rows=int(matched.sum()),
                  original_label_values=target.Label.value_counts(dropna=False).to_dict(),
                  first_capture_timestamp=str(timestamps.min()), last_capture_timestamp=str(timestamps.max()),
                  outputs={p: sha256(OUT / p) for p in ("metrics.csv", "coverage.csv")})
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    run()
