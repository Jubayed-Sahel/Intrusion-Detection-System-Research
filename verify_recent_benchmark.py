"""Validate recent results, independent units, and the recorded source chain.

The default checks work in CI without ignored raw/prepared data. Local prepared
files are checked when present. ``--verify-raw`` additionally rehashes all the
downloaded official source bytes, including every GeNIS ZIP member used.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import zipfile
import zlib

import numpy as np
import pandas as pd

from run_recent_benchmark import group_comparisons, holm
from src.xai_ids.recent_data import GENIS_EXCLUDE, GOTHAM_EXCLUDE


KEYS = ["dataset", "task", "model", "model_seed"]


def source_basename(path):
    # Recorded Windows paths must remain readable by Linux CI.
    return Path(str(path).replace("\\", "/")).name


def file_hash(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def read_source_csv(path):
    """Recover original checkpoint doubles; rank tests are sensitive to ties."""
    return pd.read_csv(path, float_precision="round_trip")


def _aggregate_matches(output, name):
    # The frozen runner used the default CSV parser when merging checkpoints.
    # Replay that exact serialization path rather than treating its rounded
    # aggregate as the original input to a near-tie-sensitive signed-rank test.
    paths = sorted((output / "contexts").glob(f"*/{name}.csv"))
    merged = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    if "wilcoxon_one_sided_p" in merged:
        merged["holm_adjusted_p_all_contexts"] = holm(merged.wilcoxon_one_sided_p)
    replay = read_source_csv(io.StringIO(merged.to_csv(index=False)))
    pd.testing.assert_frame_equal(read_source_csv(output / f"{name}.csv"), replay, check_exact=True)


def _contexts(frame, keys, expected):
    actual = list(frame[keys].itertuples(index=False, name=None))
    assert len(actual) == len(set(actual)), f"Duplicate contexts in {keys}"
    assert set(actual) == set(expected), f"Missing or unexpected contexts in {keys}"


def _source_chain(dataset, provenance, source_hash, verify_raw):
    assert provenance["dataset"] == dataset
    record_id = 14919237 if dataset == "GeNIS2025" else 14502760
    assert provenance["author_record"] == record_id
    assert provenance["acquisition"]["record_id"] == record_id
    assert provenance["preparation_source_sha256"] == source_hash
    features = provenance["features"]
    excluded = GENIS_EXCLUDE if dataset == "GeNIS2025" else GOTHAM_EXCLUDE
    assert features and len(features) == len(set(features))
    assert not set(features) & excluded
    assert not any(feature.startswith("__") or feature == "Label" for feature in features)
    assert set(provenance["prepared_files"]) == {"train.parquet", "test.parquet"}
    source_files = {entry["member"]: entry for entry in provenance["source_files"]}
    assert len(source_files) == len(provenance["source_files"])
    assert sum(file["parsed_rows"] for file in source_files.values()) == sum(provenance["source_label_counts"].values())
    assert all(file["parsed_rows"] > 0 and re.fullmatch(r"[0-9a-f]{64}", file["sha256"]) for file in source_files.values())
    assert sum(provenance["sampled_label_counts"].values()) == provenance["split_audit"]["train_rows"] + provenance["split_audit"]["test_rows"]
    excluded_labels = provenance.get("supervised_excluded_label_counts", {})
    assert all(label in provenance["source_label_counts"] and count == provenance["source_label_counts"][label]
               for label, count in excluded_labels.items())
    assert not excluded_labels if dataset == "GeNIS2025" else all(label.lower() == "unknown" for label in excluded_labels)
    eligible_labels = set(provenance["source_label_counts"]) - set(excluded_labels)
    assert all(count == min(provenance["per_class_cap"], provenance["source_label_counts"][label])
               for label, count in provenance["sampled_label_counts"].items())
    assert set(provenance["sampled_label_counts"]) == eligible_labels
    assert not any(label.lower() == "unknown" for label in provenance["sampled_label_counts"])
    assert provenance["split_audit"]["overlapping_groups"] == 0
    acquisition = provenance["acquisition"]
    if dataset == "GeNIS2025":
        assert {file["filename"] for file in acquisition["files"]} == {"0-info.zip", "3-scenarios.zip"}
        assert all(file["checksum_verified"] for file in acquisition["files"])
        assert set(source_files) == {
            f"3-scenarios/scenarios-5-sec/scenario-{index}-{'disrupt' if index < 6 else 'authtest'}.csv"
            for index in range(1, 9)
        }
    else:
        csv_files = {file["filename"]: file for file in acquisition["files"] if file["filename"].endswith(".csv")}
        assert len(csv_files) == 78 and set(csv_files) == set(source_files)
        assert all(file["member_crc_verified"] for file in csv_files.values())
        assert not acquisition["full_archive_checksum_verified"]
        assert all(source_files[name]["sha256"] == file["sha256"] for name, file in csv_files.items())
        assert all(provenance["source_date_range_utc"])
    prepared = Path("data/prepared") / dataset
    frames = None
    if prepared.exists():
        assert file_hash(prepared / "preparation_source.py") == source_hash
        for name, expected in provenance["prepared_files"].items():
            path = prepared / name
            assert path.stat().st_size == expected["bytes"] and file_hash(path) == expected["sha256"]
        train, test = (pd.read_parquet(prepared / name) for name in ("train.parquet", "test.parquet"))
        assert not set(train.__group) & set(test.__group)
        assert len(train) == provenance["split_audit"]["train_rows"]
        assert len(test) == provenance["split_audit"]["test_rows"]
        assert train.__group.nunique() == provenance["split_audit"]["training_groups"]
        assert test.__group.nunique() == provenance["split_audit"]["testing_groups"]
        assert sorted(train.Label.unique()) == provenance["split_audit"]["training_labels"]
        assert sorted(test.Label.unique()) == provenance["split_audit"]["test_labels"]
        assert pd.concat([train.Label, test.Label]).value_counts().to_dict() == provenance["sampled_label_counts"]
        assert set(train.columns) == set(test.columns) == set(features) | {"Label", "__group", "__source_file", "__source_row"}
        assert not pd.concat([train, test]).duplicated(["__source_file", "__source_row"]).any()
        for frame in (train, test):
            assert not frame.duplicated(["__source_file", "__source_row"]).any()
            assert set(frame.__source_file) <= set(source_files)
            assert frame.__source_row.ge(0).all()
            assert all(row < source_files[member]["parsed_rows"]
                       for member, row in frame[["__source_file", "__source_row"]].itertuples(index=False, name=None))
        frames = train, test
    if verify_raw:
        root = Path("data/official") / str(record_id)
        if dataset == "GeNIS2025":
            for file in acquisition["files"]:
                path = root / file["filename"]
                algorithm, expected = file["provider_checksum"].split(":")
                assert path.stat().st_size == file["bytes"]
                assert file_hash(path, algorithm) == expected and file_hash(path) == file["sha256"]
            with zipfile.ZipFile(root / "3-scenarios.zip") as archive:
                for name, file in source_files.items():
                    with archive.open(name) as stream:
                        assert hashlib.file_digest(stream, "sha256").hexdigest() == file["sha256"]
        else:
            for file in acquisition["files"]:
                path = root / file["filename"]
                assert path.stat().st_size == file["bytes"]
                crc, digest = 0, hashlib.sha256()
                with path.open("rb") as stream:
                    while block := stream.read(1024 * 1024):
                        crc = zlib.crc32(block, crc)
                        digest.update(block)
                assert crc == file["crc32"] and digest.hexdigest() == file["sha256"]
    return frames


def _inference_matches(actual, expected, metrics):
    for name in metrics:
        if name == "n_pairs":
            assert np.array_equal(actual[name].to_numpy(), expected[name].to_numpy()), f"Incorrect group inference: {name}"
        else:
            # Pinned wheels can still differ in floating arithmetic between
            # platforms. Keep original checkpoint inputs exact via round-trip
            # parsing, then allow only tight numerical error in recomputation.
            np.testing.assert_allclose(actual[name].to_numpy(), expected[name].to_numpy(),
                                       rtol=1e-8, atol=1e-12, equal_nan=True,
                                       err_msg=f"Incorrect group inference: {name}")
    assert (actual["inference_unit"] == "explained connection-group mean").all()
    assert np.array_equal(actual["insufficient_groups"], expected["insufficient_groups"])


def _verify_acquisition(output, manifest):
    root = output / "acquisition_snapshots"
    snapshot = json.loads((root / "snapshot_manifest.json").read_text())
    assert set(snapshot["files"]) == {
        "GeNIS2025/provider_record.json", "GeNIS2025/acquisition.json",
        "Gotham2025/provider_record.json", "Gotham2025/acquisition.json", "Gotham2025/member_index.json",
        "fetch_recent_datasets.py", "fetch_gotham_members.py", "inspect_gotham_archive.py"}
    for name, expected_hash in snapshot["files"].items():
        assert file_hash(root / name) == expected_hash
    for dataset in manifest["config"]["datasets"]:
        source = manifest["sources"][dataset]
        provider = json.loads((root / dataset / "provider_record.json").read_text())
        acquisition = json.loads((root / dataset / "acquisition.json").read_text())
        assert acquisition == source["acquisition"]
        assert provider["id"] == source["author_record"] == acquisition["record_id"]
        assert provider["metadata"]["access_right"] == "open"
        assert provider["metadata"]["license"]["id"] == "cc-by-4.0"
        descriptors = {file["key"]: file for file in provider["files"]}
        if dataset == "GeNIS2025":
            for file in acquisition["files"]:
                descriptor = descriptors[file["filename"]]
                assert file["provider_checksum"] == descriptor["checksum"]
                assert file["bytes"] == descriptor["size"]
                assert file["metadata_sha256"] == snapshot["files"][f"{dataset}/provider_record.json"]
        else:
            descriptor = descriptors["GothamDataset2025.zip"]
            assert acquisition["provider_archive_checksum"] == descriptor["checksum"]
            index_rows = json.loads((root / dataset / "member_index.json").read_text())
            index = {file["filename"]: file for file in index_rows}
            files = {file["filename"]: file for file in acquisition["files"]}
            assert len(index_rows) == len(index) and len(acquisition["files"]) == len(files)
            assert set(index) == set(files)
            for name, file in files.items():
                indexed = index[name]
                assert all(file[field] == indexed[field] for field in ("bytes", "compressed_bytes", "crc32"))
                assert file["compressed_offset"] >= indexed["header_offset"] + 30
                assert file["compressed_offset"] + file["compressed_bytes"] < descriptor["size"]


def _verify_audit(output, manifest, predictions, contexts, local_frames):
    destination = output / "extended"
    audit = json.loads((destination / "audit_manifest.json").read_text())
    assert audit["config"] == manifest["config"]
    assert {source_basename(path) for path in audit["source_code"]} == {
        "run_recent_audit.py", "extended_audit.py", "benchmark.py", "transparency.py"}
    for path, expected_hash in audit["source_code"].items():
        assert file_hash(destination / "source_snapshots" / source_basename(path)) == expected_hash
    expected_inputs = set()
    input_locations = {}
    for dataset, source in manifest["sources"].items():
        for name, prepared in source["prepared_files"].items():
            path = Path("data/prepared") / dataset / name
            expected_inputs.add(path.as_posix())
            input_locations[path.as_posix()] = path
            assert audit["inputs"][path.as_posix()] == prepared["sha256"]
    for dataset, task, model in contexts:
        model_name = f"{dataset}_{task}_{model}.joblib"
        recorded_output = Path(str(manifest["config"]["output_dir"]).replace("\\", "/"))
        path = recorded_output / "models" / model_name
        expected_inputs.add(path.as_posix())
        input_locations[path.as_posix()] = output / "models" / model_name
        assert (destination / f"{dataset}_{task}_{model}" / "complete.json").is_file()
    assert set(audit["inputs"]) == expected_inputs
    for path, expected_hash in audit["inputs"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        local_path = input_locations[path]
        if local_path.is_file():
            assert file_hash(local_path) == expected_hash
    tables = {}
    for name in ("calibration_bins", "calibration_summary", "balancing_ablation", "masking_baseline_ablation", "lime_budget_ablation"):
        table = pd.read_csv(destination / f"{name}.csv")
        checkpoint_tables = [pd.read_csv(path) for path in sorted(destination.glob(f"*/{name}.csv"))]
        pd.testing.assert_frame_equal(table, pd.concat(checkpoint_tables, ignore_index=True))
        tables[name] = table
    calibration = tables["calibration_summary"]
    _contexts(calibration, ["dataset", "model"], [(d, m) for d, t, m in contexts if t == "binary"])
    assert calibration.brier_score.between(0, 1).all() and calibration.expected_calibration_error.between(0, 1).all()
    for (dataset, model), bins in tables["calibration_bins"].groupby(["dataset", "model"]):
        assert bins["count"].sum() == manifest["sources"][dataset]["split_audit"]["test_rows"]
        assert not bins.bin.duplicated().any()
        expected_ece = (bins["count"] * (bins.mean_attack_probability - bins.observed_attack_frequency).abs()).sum() / bins["count"].sum()
        summary = calibration[calibration.dataset.eq(dataset) & calibration.model.eq(model)].iloc[0]
        assert np.isclose(summary.expected_calibration_error, expected_ece)
    balancing = tables["balancing_ablation"]
    _contexts(balancing, ["dataset", "task", "model", "training_weighting"],
              [(*context, weighting) for context in contexts for weighting in ("none", "class_weighted")])
    assert balancing.seed.eq(manifest["config"]["seed"]).all() and balancing.macro_f1.between(0, 1).all()
    primary = predictions[predictions.seed.eq(manifest["config"]["seed"])].set_index(["dataset", "task", "model"])
    weighted = balancing[balancing.training_weighting.eq("class_weighted")].set_index(["dataset", "task", "model"])
    assert np.allclose(weighted.macro_f1.sort_index(), primary.macro_f1.sort_index())
    assert balancing.macro_f1_supported_classes.between(0, 1).all()
    assert np.allclose(weighted.macro_f1_supported_classes.sort_index(), primary.macro_f1_supported_classes.sort_index())
    for name, index_column, levels, instances, score in (
            ("masking_baseline_ablation", "baseline", {"training_median_mode", "zero", "marginal_training_row", "nearest_same_prediction", "nearest_opposite_prediction"}, 12, "deletion_score"),
            ("lime_budget_ablation", "lime_samples", {100, 350, 700}, 6, "mean_deletion_fidelity")):
        table = tables[name]
        assert set(table[["dataset", "task", "model"]].itertuples(index=False, name=None)) == set(contexts)
        assert not table.duplicated(["dataset", "task", "model", "source_test_index", index_column]).any()
        assert np.isfinite(table[score]).all() and table[score].between(-1 - 1e-12, 1 + 1e-12).all()
        for context, frame in table.groupby(["dataset", "task", "model"]):
            assert frame.source_test_index.nunique() == instances
            assert all(set(values) == levels for _, values in frame.groupby("source_test_index")[index_column])
            if context[0] in local_frames:
                assert frame.source_test_index.ge(0).all() and frame.source_test_index.lt(len(local_frames[context[0]][1])).all()
    assert tables["masking_baseline_ablation"].any_prediction_flip.isin([0, 1]).all()
    assert tables["lime_budget_ablation"].mean_self_stability_cosine.between(-1 - 1e-12, 1 + 1e-12).all()
    assert tables["lime_budget_ablation"].median_latency_ms.ge(0).all()


def main(verify_raw=False, output=Path("outputs/recent2025")):
    output = Path(output)
    manifest = json.loads((output / "run_manifest.json").read_text())
    config = manifest["config"]
    predictions = pd.read_csv(output / "predictive_metrics.csv")
    baselines = pd.read_csv(output / "predictive_baselines.csv")
    per_class = pd.read_csv(output / "per_class_metrics.csv")
    fidelity = read_source_csv(output / "fidelity.csv")
    summaries = pd.read_csv(output / "explanation_summary.csv")
    paired = read_source_csv(output / "paired_comparisons.csv")
    controls = read_source_csv(output / "fidelity_control_tests.csv")
    for name in ("fidelity", "paired_comparisons", "fidelity_control_tests"):
        _aggregate_matches(output, name)
    families = ("random_forest", "xgboost")
    base = list(itertools.product(config["datasets"], ("binary", "multiclass"), families))
    _contexts(predictions, ["dataset", "task", "model", "seed"],
              [(*context, seed) for context in base for seed in config["predictive_seeds"]])
    _contexts(baselines, ["dataset", "task", "model"],
              itertools.product(config["datasets"], ("binary", "multiclass"), ("majority", "depth5_tree")))
    for table in (predictions, baselines):
        assert table.macro_f1_supported_classes.between(0, 1).all()
        assert table.macro_f1_training_vocabulary.between(0, 1).all()
        assert (table.macro_f1_training_vocabulary <= table.macro_f1 + 1e-12).all()
        assert (table.macro_f1 <= table.macro_f1_supported_classes + 1e-12).all()
    for dataset, task, model in base:
        for seed in config["predictive_seeds"]:
            checkpoint = output / "contexts" / f"{dataset}_{task}_{model}_{seed}" / "complete.json"
            assert json.loads(checkpoint.read_text()) == {"dataset": dataset, "task": task, "model": model, "seed": seed}
    explanation_contexts = [(*context, seed) for context in base for seed in config["explanation_model_seeds"]]
    _contexts(paired, KEYS, explanation_contexts)
    _contexts(controls, [*KEYS, "explainer"], [(*context, method) for context in explanation_contexts for method in ("TreeSHAP", "LIME")])
    _contexts(summaries, [*KEYS, "explainer"], [(*context, method) for context in explanation_contexts for method in ("TreeSHAP", "LIME")])
    assert set(manifest["sources"]) == set(config["datasets"])
    preparation_hash = next(value for key, value in manifest["source_code"].items() if source_basename(key) == "recent_data.py")
    local_frames = {}
    for dataset in config["datasets"]:
        provenance = manifest["sources"][dataset]
        frames = _source_chain(dataset, provenance, preparation_hash, verify_raw)
        if frames:
            local_frames[dataset] = frames
        selected = predictions[predictions.dataset.eq(dataset)]
        assert selected.train_rows.eq(provenance["split_audit"]["train_rows"]).all()
        assert selected.test_rows.eq(provenance["split_audit"]["test_rows"]).all()
        assert selected.feature_count.eq(len(provenance["features"])).all()
        for task in ("binary", "multiclass"):
            classes = ["Attack", "Normal"] if task == "binary" else provenance["split_audit"]["training_labels"]
            selected = per_class[per_class.dataset.eq(dataset) & per_class.task.eq(task)]
            _contexts(selected, ["model", "seed", "class"], itertools.product(families, config["predictive_seeds"], classes))
            for (model, seed), group in selected.groupby(["model", "seed"]):
                assert group.support.sum() == provenance["split_audit"]["test_rows"]
                metrics = predictions[predictions.dataset.eq(dataset) & predictions.task.eq(task) & predictions.model.eq(model) & predictions.seed.eq(seed)].iloc[0]
                supported = group[group.support.gt(0)]
                assert metrics.training_classes == len(classes) and metrics.test_classes_with_support == len(supported)
                assert np.isclose(metrics.macro_f1_supported_classes, supported.f1.mean())
                assert np.isclose(metrics.macro_f1_training_vocabulary, group.f1.mean())
                assert np.isclose(metrics.weighted_f1, (group.f1 * group.support).sum() / group.support.sum())
                assert np.isclose(metrics.accuracy, (group.recall * group.support).sum() / group.support.sum())
                assert np.isclose(metrics.balanced_accuracy, supported.recall.mean())
                if task == "binary":
                    recalls = group.set_index("class").recall
                    assert np.isclose(metrics.false_positive_rate, 1 - recalls["Normal"])
                    assert np.isclose(metrics.false_negative_rate, 1 - recalls["Attack"])
                if frames:
                    labels = frames[1].Label
                    if task == "binary":
                        labels = pd.Series(np.where(labels.str.lower().eq("benign"), "Normal", "Attack"))
                    support = labels.value_counts().reindex(classes, fill_value=0)
                    assert group.set_index("class").support.to_dict() == support.to_dict()
    assert set(fidelity[KEYS].itertuples(index=False, name=None)) == set(explanation_contexts)
    for key, group in fidelity.groupby(KEYS):
        sets = {name: set(frame.source_test_index) for name, frame in group.groupby("explainer")}
        assert set(sets) == {"TreeSHAP", "LIME"} and sets["TreeSHAP"] == sets["LIME"]
        assert len(sets["TreeSHAP"]) == config["evaluation"]["explanation_samples"]
        assert not group.duplicated(["explainer", "source_test_index", "control", "k"]).any()
        assert set(group.control) == {"top", "random", "bottom"}
        assert set(group.k) == set(config["evaluation"]["fidelity_k"])
        assert len(group) == len(sets["TreeSHAP"]) * 2 * 3 * len(config["evaluation"]["fidelity_k"])
        assert group.groupby("source_test_index").connection_group.nunique().max() == 1
        assert np.isfinite(group.probability_drop).all() and group.probability_drop.between(-1 - 1e-12, 1 + 1e-12).all()
        if key[0] in local_frames:
            test = local_frames[key[0]][1]
            assert group.source_test_index.ge(0).all() and group.source_test_index.lt(len(test)).all()
            assert np.array_equal(group.connection_group.astype(str), test.iloc[group.source_test_index]["__group"].astype(str).to_numpy())
        dataset, task, model, seed = key
        checkpoint = output / "contexts" / f"{dataset}_{task}_{model}_{seed}"
        source_fidelity = read_source_csv(checkpoint / "fidelity.csv")
        assert set(source_fidelity[KEYS].itertuples(index=False, name=None)) == {key}
        selected_paired = read_source_csv(checkpoint / "paired_comparisons.csv")
        selected_controls = read_source_csv(checkpoint / "fidelity_control_tests.csv").sort_values("explainer")
        expected_paired, expected_controls = group_comparisons(source_fidelity, seed)
        _inference_matches(selected_paired, expected_paired, ["n_pairs", "mean_difference_shap_minus_lime", "ci_low", "ci_high", "wilcoxon_one_sided_p"])
        _inference_matches(selected_controls, expected_controls.sort_values("explainer"), ["n_pairs", "mean_lift_top_minus_random", "ci_low", "ci_high", "wilcoxon_one_sided_p"])
    for table in (paired, controls):
        assert np.allclose(table.holm_adjusted_p_all_contexts, holm(table.wilcoxon_one_sided_p), rtol=1e-8, atol=1e-12)
        assert (table.n_pairs <= config["evaluation"]["explanation_samples"]).all()
    for source_path, expected_hash in manifest["source_code"].items():
        snapshot = output / "source_snapshots" / source_basename(source_path)
        assert file_hash(snapshot) == expected_hash
    _verify_acquisition(output, manifest)
    _verify_audit(output, manifest, predictions, base, local_frames)
    print(f"Verified {len(predictions)} predictive fits, {len(paired)} paired group-aware explanation comparisons, and {len(base)} extended audit contexts on traceable recent data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/recent2025"), help="Completed benchmark result directory.")
    parser.add_argument("--verify-raw", action="store_true", help="Rehash all downloaded official source bytes as well.")
    args = parser.parse_args()
    main(verify_raw=args.verify_raw, output=args.output)
