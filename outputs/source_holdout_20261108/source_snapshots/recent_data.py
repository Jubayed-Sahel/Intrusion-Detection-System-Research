"""Deterministic, documented preparation of two author-published 2025 datasets."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from .benchmark import sha256


GENIS_EXCLUDE = {
    "FlowID", "Rank", "StartTime", "LastTime", "IdleTime", "Seq", "SrcAddr", "DstAddr",
    "SrcMac", "DstMac", "SrcOui", "DstOui", "sCo", "dCo", "sAS", "dAS", "iAS", "sIpId", "dIpId",
    "sMpls", "dMpls", "AutoId", "Inode", "Offset", "Ssaddr", "Sdaddr", "srcUdata", "dstUdata",
    "sVlan", "dVlan", "sVid", "dVid", "sVpri", "dVpri", "SRange", "ERange", "SrcTCPBase", "DstTCPBase",
    "BinaryLabel", "CategoryLabel", "SubCategoryLabel",
}
GENIS_CATEGORICAL = {"Proto", "Flgs", "sDSb", "dDSb", "Cause", "Dir", "State", "TcpOpt"}
GOTHAM_EXCLUDE = {"frame.time", "eth.src", "eth.dst", "ip.src", "ip.dst", "ip.checksum", "tcp.checksum", "tcp.options", "label"}
GOTHAM_CATEGORICAL = {"frame.protocols"}


def connection_groups(frame: pd.DataFrame) -> pd.Series:
    """Use bidirectional transport endpoint tuples across all device files."""
    source_port = pd.to_numeric(frame["tcp.srcport"].fillna(frame["udp.srcport"]), errors="coerce").fillna(-1).astype("int64").astype(str)
    destination_port = pd.to_numeric(frame["tcp.dstport"].fillna(frame["udp.dstport"]), errors="coerce").fillna(-1).astype("int64").astype(str)
    left = frame["ip.src"].fillna("").astype(str) + ":" + source_port
    right = frame["ip.dst"].fillna("").astype(str) + ":" + destination_port
    low = left.where(left <= right, right)
    high = right.where(left <= right, left)
    protocol = pd.to_numeric(frame["ip.proto"], errors="coerce").fillna(-1).astype("int64").astype(str)
    return low + "|" + high + "|" + protocol


def group_split(frame: pd.DataFrame, seed=42, test_size=0.2):
    """Freeze the first label-covered group split, before any model fitting.

    Classes confined to one group cannot appear on both sides. Their groups
    stay in training and their absence from test is explicitly recorded.
    """
    counts = frame.groupby("Label")["__group"].nunique()
    singleton_labels = counts[counts < 2].index.tolist()
    forced_groups = set(frame.loc[frame.Label.isin(singleton_labels), "__group"])
    eligible = frame.loc[~frame.__group.isin(forced_groups)]
    eligible_labels = set(eligible.Label)
    if len(eligible_labels) < 2:
        raise ValueError("Insufficient independent groups for evaluation")
    for candidate, (train_indices, test_indices) in enumerate(GroupShuffleSplit(n_splits=200, test_size=test_size, random_state=seed).split(eligible, groups=eligible.__group)):
        train = pd.concat([eligible.iloc[train_indices], frame.loc[frame.__group.isin(forced_groups)]])
        test = eligible.iloc[test_indices]
        if set(test.Label) <= set(train.Label) and set(test.Label) >= eligible_labels:
            train, test = train.sort_values(["__source_file", "__source_row"]), test.sort_values(["__source_file", "__source_row"])
            assert not set(train.__group) & set(test.__group)
            return train.reset_index(drop=True), test.reset_index(drop=True), {
                "split": "connection-group holdout; first label-covered GroupShuffleSplit candidate",
                "seed": seed, "candidate": candidate, "requested_test_group_fraction": test_size,
                "singleton_labels_training_only": singleton_labels,
                "test_labels": sorted(set(test.Label)), "training_labels": sorted(set(train.Label)),
                "training_groups": train.__group.nunique(), "testing_groups": test.__group.nunique(),
                "train_rows": len(train), "test_rows": len(test), "overlapping_groups": 0,
            }
    raise ValueError("No label-covered group split found; do not replace with a leaky row split")


def _hex_numeric(series):
    return series.map(lambda value: int(value, 16) if isinstance(value, str) and value.startswith("0x") else value)


def prepare(name: str, cap: int = 10000, seed: int = 42):
    preparation_source = Path(__file__).read_bytes()
    rng = np.random.default_rng(seed)
    reservoirs, label_counts, source_files = {}, Counter(), []
    date_min, date_max = None, None
    # An unspecified source label does not establish either benign traffic
    # or a confirmed attack. Retain its raw count and omit it from supervision.
    supervised_excluded_labels = {"Unknown"} if name == "Gotham2025" else set()
    if name == "GeNIS2025":
        source_root = Path("data/official/14919237")
        archive = zipfile.ZipFile(source_root / "3-scenarios.zip")
        members = sorted(member for member in archive.namelist() if "/scenarios-5-sec/" in member and member.endswith(".csv"))
        inputs = [(member, lambda member=member: archive.open(member)) for member in members]
        excludes, categorical = GENIS_EXCLUDE, GENIS_CATEGORICAL
    elif name == "Gotham2025":
        source_root = Path("data/official/14502760")
        acquisition = json.loads((source_root / "acquisition.json").read_text())
        members = sorted(file["filename"] for file in acquisition["files"] if file["filename"].endswith(".csv"))
        if len(members) != 78:
            raise ValueError(f"All 78 author CSV files are required, found {len(members)}")
        inputs = [(member, lambda member=member: (source_root / member).open("rb")) for member in members]
        excludes, categorical = GOTHAM_EXCLUDE, GOTHAM_CATEGORICAL
    else:
        raise ValueError(name)
    feature_names = None
    for filename, opener in inputs:
        print(f"[prepare source] {name}: {filename}", flush=True)
        source_digest = __import__("hashlib").sha256()
        # Fully verify the member while parsing through a separate stream.
        with opener() as stream:
            while block := stream.read(1024 * 1024):
                source_digest.update(block)
        offset = 0
        with opener() as stream:
            for chunk in pd.read_csv(stream, chunksize=50000, low_memory=False):
                if feature_names is None:
                    feature_names = [column for column in chunk if column not in excludes]
                labels = chunk["CategoryLabel" if name == "GeNIS2025" else "label"].astype(str).str.strip()
                if labels.isin(["", "nan"]).any():
                    raise ValueError("Missing source labels")
                label_counts.update(labels.tolist())
                if name == "GeNIS2025":
                    # Scenarios can reuse intermediate flow material. Group
                    # the provider's canonical flow identifier globally,
                    # rather than treating a new filename as independence.
                    groups = chunk.FlowID.astype(str)
                else:
                    groups = connection_groups(chunk)
                    timestamps = pd.to_datetime(chunk["frame.time"], format="%b %d, %Y %H:%M:%S.%f GMT", utc=True, errors="coerce")
                    if timestamps.isna().any():
                        raise ValueError("Unparsed Gotham timestamp")
                    start, end = timestamps.min().isoformat(), timestamps.max().isoformat()
                    date_min = min(date_min, start) if date_min else start
                    date_max = max(date_max, end) if date_max else end
                selected = chunk[feature_names].copy()
                for column in feature_names:
                    if column not in categorical:
                        values = _hex_numeric(selected[column]) if name == "Gotham2025" else selected[column]
                        selected[column] = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
                    else:
                        selected[column] = selected[column].astype("string")
                selected["Label"] = labels
                selected["__group"] = groups
                selected["__source_file"] = filename
                selected["__source_row"] = np.arange(offset, offset + len(chunk))
                selected["__sample_key"] = rng.random(len(chunk))
                offset += len(chunk)
                selected = selected.loc[~labels.isin(supervised_excluded_labels)]
                for label, group in selected.groupby("Label", sort=True):
                    previous = reservoirs.get(label)
                    combined = pd.concat([previous, group], ignore_index=True) if previous is not None else group
                    reservoirs[label] = combined.nsmallest(cap, "__sample_key")
        source_files.append({"member": filename, "parsed_rows": offset, "sha256": source_digest.hexdigest()})
    frame = pd.concat(reservoirs.values(), ignore_index=True).drop(columns="__sample_key")
    train, test, split_audit = group_split(frame, seed)
    # Drop constants using training data alone; no feature selection based on labels.
    constants = [column for column in feature_names if train[column].nunique(dropna=False) <= 1]
    features = [column for column in feature_names if column not in constants]
    train_hash = pd.util.hash_pandas_object(train[features], index=False)
    test_hash = pd.util.hash_pandas_object(test[features], index=False)
    destination = Path("data/prepared") / name
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "preparation_source.py").write_bytes(preparation_source)
    train.drop(columns=constants).to_parquet(destination / "train.parquet", index=False)
    test.drop(columns=constants).to_parquet(destination / "test.parquet", index=False)
    provenance = {"dataset": name, "author_record": 14919237 if name == "GeNIS2025" else 14502760,
        "acquisition": json.loads((source_root / "acquisition.json").read_text()),
        "license": "CC-BY-4.0", "source_files": source_files, "source_label_counts": dict(label_counts),
        "supervised_excluded_label_counts": {label: label_counts[label] for label in sorted(supervised_excluded_labels)},
        "label_scope": "known provider labels only; Unknown is excluded from both supervised tasks, not relabeled as Attack",
        "sampled_label_counts": frame.Label.value_counts().to_dict(), "per_class_cap": cap,
        "sampling": "global per-label lowest independent RNG priorities; all selected official members scanned",
        "source_date_range_utc": [date_min, date_max], "features": features,
        "excluded_identifier_or_payload_columns": sorted(excludes), "training_constant_columns_removed": constants,
        "split_audit": split_audit, "test_feature_vectors_also_present_in_training": int(test_hash.isin(train_hash).sum()),
        "feature_overlap_policy": "retained; independently captured equal patterns are not automatically duplicate source records; connection groups must be disjoint",
        "conversion": "provider CSV -> known-label scope -> deterministic class cap -> group split -> training-only constant removal -> parquet; no scaling or imputation before split",
        "preparation_source_sha256": __import__("hashlib").sha256(preparation_source).hexdigest(),
        "prepared_files": {file.name: {"sha256": sha256(file), "bytes": file.stat().st_size} for file in destination.glob("*.parquet")}}
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"[prepared] {name}: train={len(train)} test={len(test)} features={len(features)}", flush=True)

