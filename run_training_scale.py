"""Fit nested GeNIS training cohorts against identical held-out scenarios."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from sklearn.utils.class_weight import compute_sample_weight

from run_extended_validation import scores
from src.xai_ids.benchmark import TabularPreprocessor, make_model, sha256
from src.xai_ids.recent_data import GENIS_CATEGORICAL, GENIS_EXCLUDE


OUT = Path("outputs/training_scale")
FOLDS = Path("outputs/source_holdout_20261108/fold_assignments.json")
ROOT = Path("data/official/14919237")
SIZES = (10_000, 40_000, 160_000)
MODELS = ("random_forest", "xgboost")
GROUP, LABEL = "FlowID", "CategoryLabel"
CONFIG = Path("config_recent.yaml")
PROTOCOL = Path("TRAINING_SCALE_PROTOCOL.md")


def stage(archive, members, work):
    """Normalize source files to bounded Parquet row groups for repeated access."""
    paths, metadata = [], []
    with zipfile.ZipFile(archive) as zipped:
        with zipped.open(members[0]) as stream:
            columns = pd.read_csv(stream, nrows=0).columns
        features = sorted(set(columns) - GENIS_EXCLUDE)
        types = dict.fromkeys({GROUP, LABEL} | (set(features) & GENIS_CATEGORICAL), "string")
        for number, member in enumerate(members):
            path = work / f"{number}.parquet"
            writer = None
            groups = []
            try:
                for frame in pd.read_csv(zipped.open(member), usecols=[GROUP, LABEL, *features],
                                         dtype=types, chunksize=60_000, low_memory=False):
                    if frame[[GROUP, LABEL]].isna().any().any():
                        raise ValueError(f"Missing group or category in {member}")
                    frame[LABEL] = frame[LABEL].str.strip()
                    groups.append(frame[GROUP])
                    for name in features:
                        frame[name] = (frame[name].astype("string") if name in GENIS_CATEGORICAL
                                       else pd.to_numeric(frame[name], errors="coerce").astype("float64"))
                    batch = pa.Table.from_pandas(frame.drop(columns=GROUP), preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(path, batch.schema)
                    writer.write_table(batch)
            finally:
                if writer is not None:
                    writer.close()
            paths.append(path)
            metadata.append(pd.concat(groups, ignore_index=True))
            print(f"Staged source {number + 1}: {len(metadata[-1]):,} rows", flush=True)
    return features, paths, metadata


def select_training(paths, groups, heldout):
    test_groups = set(groups[heldout])
    eligible = [np.flatnonzero(~ids.isin(test_groups).to_numpy()) if i != heldout else np.array([], dtype=int)
                for i, ids in enumerate(groups)]
    offsets = np.cumsum([0, *(len(rows) for rows in eligible)])
    rng = np.random.default_rng(43 + heldout)
    picks = rng.choice(offsets[-1], SIZES[-1], replace=False)
    sources = np.searchsorted(offsets[1:], picks, side="right")
    frames = []
    for source_id in np.unique(sources):
        positions = np.flatnonzero(sources == source_id)
        rows = eligible[source_id][picks[positions] - offsets[source_id]]
        frame = pq.read_table(paths[source_id]).take(rows).to_pandas()
        frames.append(frame.assign(_order=positions))
    train = pd.concat(frames, ignore_index=True).sort_values("_order").drop(columns="_order")
    return train, int(offsets[-1])


def binary(frame):
    return frame[LABEL].str.lower().eq("benign").to_numpy(dtype=np.int64)


def fit_fold(features, paths, groups, heldout, config):
    train, pool = select_training(paths, groups, heldout)
    rows = []
    parquet = pq.ParquetFile(paths[heldout])
    for size in SIZES:
        subset = train.iloc[:size]
        y = binary(subset)
        if np.unique(y).size != 2:
            raise ValueError("Both training classes are required")
        pre = TabularPreprocessor(features).fit(subset)
        x = pre.transform(subset)
        fitted = {}
        for name in MODELS:
            model = make_model(name, config, 42, 2)
            model.set_params(n_jobs=4)
            weight = compute_sample_weight("balanced", y) if name == "xgboost" else None
            model.fit(x, y, sample_weight=weight)
            fitted[name] = model
        matrices = {name: np.zeros((2, 2), dtype=np.int64) for name in MODELS}
        for batch in parquet.iter_batches(batch_size=60_000):
            test = batch.to_pandas()
            actual = binary(test)
            x_test = pre.transform(test)
            for name, model in fitted.items():
                pred = model.predict(x_test).astype(int)
                matrices[name] += np.bincount(2 * actual + pred, minlength=4).reshape(2, 2)
        for name, matrix in matrices.items():
            rows.append(dict(fold=heldout + 1, model=name, train_rows=size, pool_rows=pool,
                             train_attacks=int((y == 0).sum()), **scores(matrix, ["Attack", "Normal"])))
        print(f"Fold {heldout + 1}: scored both models trained on {size:,} rows", flush=True)
    return rows


def run(out):
    ledger = json.loads((ROOT / "acquisition.json").read_text())
    record = next(item for item in ledger["files"] if item["filename"] == "3-scenarios.zip")
    archive = ROOT / record["filename"]
    if not record["checksum_verified"] or sha256(archive) != record["sha256"]:
        raise ValueError("GeNIS archive does not match the acquisition ledger")
    folds = [fold for fold in json.loads(FOLDS.read_text()) if fold["dataset"] == "GeNIS2025"]
    members = [fold["test_sources"][0] for fold in folds]
    if len(set(members)) != 8 or [fold["fold"] for fold in folds] != list(range(1, 9)):
        raise ValueError("Unexpected GeNIS source assignment")
    config = yaml.safe_load(CONFIG.read_text())["models"]
    dependencies = (Path(__file__), PROTOCOL, FOLDS, CONFIG, Path("src/xai_ids/benchmark.py"),
                    Path("src/xai_ids/recent_data.py"), Path("run_extended_validation.py"))
    signature = dict(archive_sha256=record["sha256"], members=members,
                     inputs={p.as_posix(): sha256(p) for p in dependencies})
    out.mkdir(parents=True, exist_ok=True)
    for checkpoint in out.glob("fold_*.json"):
        if json.loads(checkpoint.read_text())["signature"] != signature:
            raise ValueError(f"Training-size checkpoint has different inputs: {checkpoint}")
    rows = []
    with TemporaryDirectory(prefix="training-scale-", dir="data") as temp:
        features, paths, groups = stage(archive, members, Path(temp))
        for heldout in range(len(members)):
            checkpoint = out / f"fold_{heldout + 1}.json"
            if checkpoint.exists():
                rows.extend(json.loads(checkpoint.read_text())["rows"])
                continue
            result = fit_fold(features, paths, groups, heldout, config)
            pending = checkpoint.with_suffix(".tmp")
            pending.write_text(json.dumps(dict(signature=signature, rows=result), indent=2))
            pending.replace(checkpoint)
            rows.extend(result)
    pd.DataFrame(rows).to_csv(out / "metrics.csv", index=False)
    (out / "manifest.json").write_text(json.dumps(dict(**signature, contexts=len(rows),
        metrics_sha256=sha256(out / "metrics.csv")), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    run(parser.parse_args().output)
