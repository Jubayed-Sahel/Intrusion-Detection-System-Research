"""Frozen, post hoc source-file transfer stress test; preserve primary outputs."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import yaml
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight

from src.xai_ids.benchmark import (TabularPreprocessor, explanation_indices,
    explain_lime, extract_shap_vector, fidelity_rows, make_lime_explainer,
    make_model, sha256, stratified_indices)

OUT = Path("outputs/source_holdout_20261108")
CACHE = Path("data/prepared/source_holdout_20261108")
DATASETS = ("GeNIS2025", "Gotham2025")
SOURCE_PATHS = (Path(__file__), Path("SOURCE_HOLDOUT_PROTOCOL_20261108.md"),
    Path("src/xai_ids/benchmark.py"), Path("src/xai_ids/recent_data.py"),
    Path("config_recent.yaml"), Path("requirements.txt"))
SEED = 42
K_VALUES = [1, 3, 5, 10]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_order(values):
    return sorted(values, key=lambda s: (hashlib.sha256(str(s).encode()).hexdigest(), str(s)))


def make_folds(frame, dataset):
    sources = sorted(frame["__source_file"].unique())
    if dataset == "GeNIS2025":
        bundles = [[source] for source in sources]
    elif dataset == "Gotham2025":
        attacks = source_order(frame.loc[frame.Label.str.lower() != "benign", "__source_file"].unique())
        if not attacks:
            raise ValueError("No attack-bearing sources")
        bundles = [[source] for source in attacks]
        for i, source in enumerate(source_order(set(sources) - set(attacks))):
            bundles[i % len(bundles)].append(source)
    else:
        raise ValueError(dataset)
    flat = [source for bundle in bundles for source in bundle]
    if len(flat) != len(set(flat)) or set(flat) != set(sources):
        raise ValueError("Incomplete or repeated source assignment")
    return [{"dataset": dataset, "fold": i + 1, "test_sources": bundle} for i, bundle in enumerate(bundles)]


def partition(frame, test_sources):
    test = frame.loc[frame["__source_file"].isin(test_sources)].copy()
    pool = frame.loc[~frame["__source_file"].isin(test_sources)]
    train = pool.loc[~pool["__group"].isin(set(test["__group"]))].copy()
    if train.empty or test.empty:
        raise ValueError("Empty source partition")
    if set(train["__group"]) & set(test["__group"]):
        raise ValueError("Connection leakage")
    audit = {"train_rows": len(train), "test_rows": len(test),
        "train_groups": train["__group"].nunique(), "test_groups": test["__group"].nunique(),
        "purged_train_rows": len(pool)-len(train),
        "purged_train_groups": pool["__group"].nunique()-train["__group"].nunique(),
        "train_test_group_overlap": 0, "train_test_source_overlap": 0,
        "raw_train_label_support": train.Label.value_counts().sort_index().to_dict(),
        "raw_test_label_support": test.Label.value_counts().sort_index().to_dict()}
    return train.reset_index(drop=True), test.reset_index(drop=True), audit


def labels_for(frame, task):
    return np.where(frame.Label.str.lower() == "benign", "Normal", "Attack") if task == "binary" else frame.Label.to_numpy(dtype=str)


def score_predictions(actual, predicted, train_labels):
    actual, predicted, train_labels = (np.asarray(x, dtype=str) for x in (actual, predicted, train_labels))
    if len(actual) != len(predicted) or not len(actual):
        raise ValueError("Invalid prediction coverage")
    if not set(predicted) <= set(train_labels):
        raise ValueError("Predicted label outside trained vocabulary")
    supported = sorted(set(actual))
    vocabulary = sorted(set(actual) | set(train_labels))
    seen = np.isin(actual, np.unique(train_labels))
    seen_labels = sorted(set(actual[seen]))
    result = {"accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1_all_test_supported_labels": float(f1_score(actual, predicted, labels=supported, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(actual, predicted, labels=supported, average="weighted", zero_division=0)),
        "test_rows": len(actual), "test_supported_labels": len(supported),
        "training_labels": len(set(train_labels)), "unseen_label_test_rows": int((~seen).sum()),
        "seen_label_test_rows": int(seen.sum()),
        "macro_f1_seen_label_subset": float(f1_score(actual[seen], predicted[seen], labels=seen_labels, average="macro", zero_division=0)) if seen.any() else None}
    p, r, f, support = precision_recall_fscore_support(actual, predicted, labels=vocabulary, zero_division=0)
    rows = [{"class": label, "precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
        "test_support": int(support[i]), "training_support": int((train_labels == label).sum()),
        "seen_in_training": bool(label in set(train_labels))} for i, label in enumerate(vocabulary)]
    matrix = confusion_matrix(actual, predicted, labels=vocabulary)
    confusions = [{"actual_class": a, "predicted_class": b, "count": int(matrix[i,j])} for i,a in enumerate(vocabulary) for j,b in enumerate(vocabulary)]
    if set(vocabulary) <= {"Attack", "Normal"}:
        normal = actual == "Normal"; attack = actual == "Attack"
        result.update({"normal_test_rows": int(normal.sum()), "attack_test_rows": int(attack.sum()),
            "false_positive_rate": float((predicted[normal] == "Attack").mean()) if normal.any() else None,
            "false_negative_rate": float((predicted[attack] == "Normal").mean()) if attack.any() else None})
    return result, rows, confusions


def load_primary(dataset):
    root = Path("data/prepared") / dataset
    provenance = read_json(root / "provenance.json")
    for name, expected in provenance["prepared_files"].items():
        if sha256(root / name) != expected["sha256"]:
            raise ValueError(f"Primary prepared input changed: {dataset}/{name}")
    frame = pd.concat([pd.read_parquet(root / (split + ".parquet")) for split in ("train", "test")], ignore_index=True)
    frame = frame.sort_values(["__source_file", "__source_row"]).reset_index(drop=True)
    if frame.duplicated(["__source_file", "__source_row"]).any():
        raise ValueError("Repeated source row identity")
    return frame, provenance


def restore_candidates(dataset, frame, provenance):
    destination = CACHE / (dataset + ".parquet")
    metadata_path = CACHE / (dataset + "_restoration.json")
    original_hashes = {name: info["sha256"] for name, info in provenance["prepared_files"].items()}
    if destination.exists() and metadata_path.exists():
        metadata = read_json(metadata_path)
        if metadata["primary_input_hashes"] != original_hashes or sha256(destination) != metadata["restored_sha256"]:
            raise ValueError("Restoration cache changed")
        return pd.read_parquet(destination), metadata
    columns = provenance["training_constant_columns_removed"]
    expected = {item["member"]: item for item in provenance["source_files"]}
    roots = Path("data/official") / str(provenance["author_record"])
    archive = zipfile.ZipFile(roots / "3-scenarios.zip") if dataset == "GeNIS2025" else None
    records = []
    member_checks = []
    label_column = "CategoryLabel" if dataset == "GeNIS2025" else "label"
    try:
        for source, selected in frame.groupby("__source_file", sort=True):
            print(f"[restore] {dataset}: {source}", flush=True)
            opener = (lambda: archive.open(source)) if archive else (lambda: (roots / source).open("rb"))
            digest = hashlib.sha256()
            with opener() as stream:
                for block in iter(lambda: stream.read(1024*1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected[source]["sha256"]:
                raise ValueError(f"Official source SHA-256 mismatch: {source}")
            wanted = selected["__source_row"].to_numpy(dtype=np.int64)
            selected_parts = []
            offset = 0
            with opener() as stream:
                for chunk in pd.read_csv(stream, usecols=columns+[label_column], chunksize=100000, low_memory=False):
                    lower, upper = np.searchsorted(wanted, [offset, offset+len(chunk)])
                    if upper > lower:
                        chosen_rows = wanted[lower:upper]
                        part = chunk.iloc[chosen_rows-offset].copy()
                        part["__source_row"] = chosen_rows
                        selected_parts.append(part)
                    offset += len(chunk)
            if offset != expected[source]["parsed_rows"]:
                raise ValueError(f"Official source row count mismatch: {source}")
            restored = pd.concat(selected_parts, ignore_index=True).sort_values("__source_row")
            if len(restored) != len(selected) or not np.array_equal(restored["__source_row"], wanted):
                raise ValueError(f"Restoration row coverage mismatch: {source}")
            raw_labels = restored[label_column].astype(str).str.strip().to_numpy()
            if not np.array_equal(raw_labels, selected.Label.astype(str).to_numpy()):
                raise ValueError(f"Restoration source label mismatch: {source}")
            restored = restored.drop(columns=label_column)
            restored["__source_file"] = source
            for column in columns:
                values = restored[column]
                if dataset == "Gotham2025":
                    values = values.map(lambda v: int(v,16) if isinstance(v,str) and v.startswith("0x") else v)
                restored[column] = pd.to_numeric(values, errors="coerce").replace([np.inf,-np.inf], np.nan)
            records.append(restored)
            member_checks.append({"member": source, "sha256": digest.hexdigest(), "parsed_rows": offset, "selected_rows_verified": len(selected)})
    finally:
        if archive:
            archive.close()
    extras = pd.concat(records, ignore_index=True)
    merged = frame.merge(extras, on=["__source_file", "__source_row"], how="left", validate="one_to_one", indicator=True)
    if len(merged) != len(frame) or not merged["_merge"].eq("both").all():
        raise ValueError("Incomplete restored cohort")
    merged = merged.drop(columns="_merge").sort_values(["__source_file", "__source_row"]).reset_index(drop=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(destination, index=False)
    metadata = {"dataset": dataset, "primary_input_hashes": original_hashes, "restored_columns": columns,
        "rows": len(merged), "member_checks": member_checks, "restored_sha256": sha256(destination),
        "row_identity_policy": "exact original filename and zero-based source CSV row number; all selected raw labels checked"}
    write_json(metadata_path, metadata)
    return merged, metadata


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    code = {str(path).replace("\\", "/"): sha256(path) for path in SOURCE_PATHS}
    inputs = {}
    frames, provenance = {}, {}
    all_folds = []
    for dataset in DATASETS:
        frames[dataset], provenance[dataset] = load_primary(dataset)
        inputs[dataset] = {"prepared_files": provenance[dataset]["prepared_files"],
            "provenance_sha256": sha256(Path("data/prepared") / dataset / "provenance.json")}
        all_folds.extend(make_folds(frames[dataset], dataset))
    assignments_path = OUT / "fold_assignments.json"
    if assignments_path.exists() and read_json(assignments_path) != all_folds:
        raise ValueError("Frozen fold assignments changed")
    if not assignments_path.exists():
        write_json(assignments_path, all_folds)
    declaration = {"source_code": code, "primary_inputs": inputs,
        "fold_assignment_sha256": sha256(assignments_path), "model_seed": SEED, "model_threads": 4,
        "explanation_samples": 50, "lime_samples": 350, "background_max_rows": 5000, "fidelity_budgets": K_VALUES,
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {line.split("==")[0]: importlib.metadata.version(line.split("==")[0]) for line in Path("requirements.txt").read_text().splitlines() if "==" in line}}}
    manifest_path = OUT / "run_manifest.json"
    if manifest_path.exists() and read_json(manifest_path) != declaration:
        raise ValueError("Frozen protocol/source/configuration/input/environment changed; use another study directory")
    if not manifest_path.exists():
        write_json(manifest_path, declaration)
        for path in SOURCE_PATHS:
            snapshot = OUT / "source_snapshots" / path.name
            snapshot.parent.mkdir(exist_ok=True)
            snapshot.write_bytes(path.read_bytes())
    return declaration, all_folds, frames, provenance


def output_hashes(directory, filenames):
    return {name: sha256(directory / name) for name in filenames}


def validate_checkpoint(path, model_path=None):
    info = read_json(path)
    if info["manifest_sha256"] != sha256(OUT / "run_manifest.json"):
        raise ValueError(f"Checkpoint has another manifest: {path}")
    for name, digest in info["output_sha256"].items():
        if sha256(path.parent / name) != digest:
            raise ValueError(f"Checkpoint output changed: {path.parent / name}")
    if model_path is not None and sha256(model_path) != info["model_sha256"]:
        raise ValueError(f"Checkpoint model changed: {model_path}")
    return info


def context_common(fold, task, model):
    return {"dataset": fold["dataset"], "fold": fold["fold"], "task": task, "model": model, "seed": SEED}


def context_name(fold, task, model):
    return f"{fold['dataset']}_fold{fold['fold']:02d}_{task}_{model}"


def prepare_folds():
    _, folds, frames, provenance = freeze()
    restorations = {}
    for dataset in DATASETS:
        frames[dataset], restorations[dataset] = restore_candidates(dataset, frames[dataset], provenance[dataset])
    restoration_path = OUT / "restoration_audit.json"
    if restoration_path.exists() and read_json(restoration_path) != restorations:
        raise ValueError("Frozen restoration audit changed")
    if not restoration_path.exists():
        write_json(restoration_path, restorations)
    return folds, frames, provenance


def predictive():
    folds, frames, provenance = prepare_folds()
    config = yaml.safe_load(Path("config_recent.yaml").read_text())
    for fold in folds:
        dataset = fold["dataset"]
        train, test, audit = partition(frames[dataset], fold["test_sources"])
        candidates = provenance[dataset]["features"] + provenance[dataset]["training_constant_columns_removed"]
        constants = [c for c in candidates if train[c].nunique(dropna=False) <= 1]
        features = [c for c in candidates if c not in constants]
        prep = TabularPreprocessor(features).fit(train)
        x_train, x_test = prep.transform(train), prep.transform(test)
        audit.update({"dataset": dataset, "fold": fold["fold"], "test_sources": fold["test_sources"],
            "constant_columns_removed_using_fold_training": constants, "features": features, "feature_count": len(features)})
        fold_dir = OUT / "folds" / f"{dataset}_fold{fold['fold']:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        if (fold_dir / "split_audit.json").exists() and read_json(fold_dir / "split_audit.json") != json.loads(json.dumps(audit, default=lambda x: x.item() if isinstance(x, np.generic) else str(x))):
            raise ValueError("Fold audit changed")
        write_json(fold_dir / "split_audit.json", audit)
        for task in ("binary", "multiclass"):
            actual_train, actual_test = labels_for(train, task), labels_for(test, task)
            encoder = LabelEncoder().fit(actual_train)
            classes = encoder.classes_.tolist()
            if len(classes) < 2:
                raise ValueError("Training fold has fewer than two classes")
            y_train = encoder.transform(actual_train)
            baseline_path = fold_dir / f"{task}_baselines.csv"
            if not baseline_path.exists():
                majority = classes[int(np.bincount(y_train).argmax())]
                tree = DecisionTreeClassifier(max_depth=5, random_state=SEED).fit(x_train, y_train)
                baseline_results = []
                for name, predictions in (("majority", np.full(len(actual_test), majority)), ("depth5_tree", encoder.inverse_transform(tree.predict(x_test)))):
                    metrics, _, _ = score_predictions(actual_test, predictions, actual_train)
                    baseline_results.append({**context_common(fold, task, name), **metrics})
                pd.DataFrame(baseline_results).to_csv(baseline_path, index=False)
            for model_name in ("random_forest", "xgboost"):
                name = context_name(fold, task, model_name)
                dest = OUT / "contexts" / name
                dest.mkdir(parents=True, exist_ok=True)
                model_path = OUT / "models" / (name+".joblib")
                if (dest / "predictive_complete.json").exists():
                    validate_checkpoint(dest / "predictive_complete.json", model_path)
                    print(f"[resume predictive] {name}", flush=True)
                    continue
                print(f"[fit] {name}; training={len(train)} testing={len(test)} features={len(features)}", flush=True)
                model = make_model(model_name, config["models"], SEED, len(classes))
                model.set_params(n_jobs=4)
                weights = compute_sample_weight("balanced", y_train) if model_name == "xgboost" else None
                started = time.perf_counter()
                model.fit(x_train, y_train, sample_weight=weights)
                fit_seconds = time.perf_counter()-started
                probabilities = model.predict_proba(x_test)
                predicted = encoder.inverse_transform(probabilities.argmax(axis=1))
                metrics, per_class, confusions = score_predictions(actual_test, predicted, actual_train)
                common = context_common(fold, task, model_name)
                pd.DataFrame([{**common, **metrics, "training_seconds": fit_seconds, "train_rows": len(train),
                    "feature_count": len(features), "purged_train_rows": audit["purged_train_rows"]}]).to_csv(dest / "predictive_metrics.csv", index=False)
                pd.DataFrame([{**common, **row} for row in per_class]).to_csv(dest / "per_class_metrics.csv", index=False)
                pd.DataFrame([{**common, **row} for row in confusions]).to_csv(dest / "confusion_matrices.csv", index=False)
                predictions = test[["__source_file", "__source_row", "__group"]].copy()
                predictions["actual_class"] = actual_test
                predictions["predicted_class"] = predicted
                predictions["actual_seen_in_training"] = np.isin(actual_test, classes)
                for i, label in enumerate(classes):
                    predictions["probability::"+label] = probabilities[:, i]
                predictions.to_csv(dest / "predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
                model_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump({"model": model, "preprocessor": prep, "classes": classes,
                    "dataset": dataset, "fold": fold["fold"], "task": task, "seed": SEED,
                    "manifest_sha256": sha256(OUT / "run_manifest.json")}, model_path, compress=3)
                files = ["predictive_metrics.csv", "per_class_metrics.csv", "confusion_matrices.csv", "predictions.csv.gz"]
                write_json(dest / "predictive_complete.json", {**common,
                    "manifest_sha256": sha256(OUT / "run_manifest.json"), "restoration_audit_sha256": sha256(OUT / "restoration_audit.json"),
                    "split_audit_sha256": sha256(fold_dir / "split_audit.json"), "baseline_sha256": sha256(baseline_path),
                    "output_sha256": output_hashes(dest, files), "model_sha256": sha256(model_path)})
                print(f"[score] {name}: all-test macro-F1={metrics['macro_f1_all_test_supported_labels']:.6f}; unseen rows={metrics['unseen_label_test_rows']}", flush=True)
    summarize()


def explanation_pass():
    folds, frames, _ = prepare_folds()
    for fold in folds:
        train, test, _ = partition(frames[fold["dataset"]], fold["test_sources"])
        for task in ("binary", "multiclass"):
            actual_test = labels_for(test, task)
            for model_name in ("random_forest", "xgboost"):
                name = context_name(fold, task, model_name)
                dest = OUT / "contexts" / name
                model_path = OUT / "models" / (name+".joblib")
                predictive_info = validate_checkpoint(dest / "predictive_complete.json", model_path)
                if (dest / "explanation_complete.json").exists():
                    validate_checkpoint(dest / "explanation_complete.json", model_path)
                    print(f"[resume explanation] {name}", flush=True)
                    continue
                bundle = joblib.load(model_path)
                model, prep, classes = bundle["model"], bundle["preprocessor"], bundle["classes"]
                x_train, x_test = prep.transform(train), prep.transform(test)
                full_pred = np.asarray(classes)[model.predict(x_test).astype(int)]
                indices = explanation_indices(actual_test, full_pred, 50, SEED)
                if len(indices) != min(50, len(test)) or len(set(indices)) != len(indices):
                    raise ValueError("Diagnostic selection is incomplete or repeated")
                selected = x_test[indices]
                local_prediction = model.predict(selected).astype(int)
                selection_path = dest / "diagnostic_selection.csv"
                selection = test.iloc[indices][["__source_file", "__source_row", "__group"]].reset_index(drop=True)
                selection["source_test_index"] = indices
                selection["actual_class"] = actual_test[indices]
                selection["predicted_class"] = np.asarray(classes)[local_prediction]
                selection.to_csv(selection_path, index=False)
                for explainer_name in ("TreeSHAP", "LIME"):
                    partial = dest / (explainer_name+"_complete.json")
                    if partial.exists():
                        validate_checkpoint(partial, model_path)
                        continue
                    print(f"[explain] {name} {explainer_name}: {len(indices)} matched records", flush=True)
                    common = {**context_common(fold, task, model_name), "explainer": explainer_name}
                    if explainer_name == "TreeSHAP":
                        explainer = shap.TreeExplainer(model)
                        _ = explainer(selected[:1], check_additivity=False)
                    else:
                        background = stratified_indices(model.predict(x_train), min(5000, len(x_train)), SEED)
                        explainer = make_lime_explainer(x_train[background], prep, classes, SEED)
                        _ = explain_lime(explainer, selected[0], model.predict_proba, int(local_prediction[0]), selected.shape[1], 350)
                    attributes, drops, timings = [], [], []
                    rng = np.random.default_rng(SEED)
                    for i, (source_index, row, prediction) in enumerate(zip(indices, selected, local_prediction)):
                        start = time.perf_counter()
                        if explainer_name == "TreeSHAP":
                            vector = extract_shap_vector(explainer(row.reshape(1,-1), check_additivity=False), int(prediction))
                        else:
                            vector = explain_lime(explainer, row, model.predict_proba, int(prediction), selected.shape[1], 350)
                        timings.append((time.perf_counter()-start)*1000)
                        if not np.isfinite(vector).all():
                            raise ValueError("Nonfinite attribution")
                        row_common = {**common, "explanation_id": i, "source_test_index": int(source_index),
                            "connection_group": test.iloc[source_index]["__group"],
                            "source_file": test.iloc[source_index]["__source_file"], "source_row": int(test.iloc[source_index]["__source_row"]),
                            "actual_class": str(actual_test[source_index]), "predicted_class": classes[int(prediction)],
                            "actual_seen_in_training": bool(actual_test[source_index] in classes)}
                        attributes.extend([{**row_common, "feature": f, "attribution": float(v)} for f,v in zip(prep.feature_names, vector)])
                        drops.extend([{**row_common, **item} for item in fidelity_rows(model, row, vector, int(prediction), np.asarray(prep.baseline_), K_VALUES, rng)])
                    pd.DataFrame(attributes).to_csv(dest / (explainer_name+"_attributions.csv.gz"), index=False, compression={"method":"gzip", "mtime":0})
                    pd.DataFrame(drops).to_csv(dest / (explainer_name+"_fidelity.csv"), index=False)
                    pd.DataFrame([{**common, "records": len(indices), "connection_groups": test.iloc[indices]["__group"].nunique(),
                        "median_explanation_ms": float(np.median(timings)), "mean_explanation_ms": float(np.mean(timings)),
                        "construction_and_warmup_excluded": True}]).to_csv(dest / (explainer_name+"_timing.csv"), index=False)
                    filenames = [explainer_name+"_attributions.csv.gz", explainer_name+"_fidelity.csv", explainer_name+"_timing.csv", "diagnostic_selection.csv"]
                    write_json(partial, {**common, "manifest_sha256": sha256(OUT / "run_manifest.json"),
                        "output_sha256": output_hashes(dest, filenames), "model_sha256": predictive_info["model_sha256"]})
                fidelity = pd.concat([pd.read_csv(dest / (e+"_fidelity.csv"), float_precision="round_trip") for e in ("TreeSHAP", "LIME")], ignore_index=True)
                grouped = fidelity.groupby(["explainer", "connection_group", "control", "k"], as_index=False).probability_drop.mean()
                by_group = grouped.groupby(["explainer", "connection_group", "control"], as_index=False).probability_drop.mean()
                group_pivot = by_group.loc[by_group.control == "top"].pivot(index="connection_group", columns="explainer", values="probability_drop")
                if group_pivot.isna().any().any():
                    raise ValueError("Unmatched explained groups")
                difference = group_pivot.TreeSHAP-group_pivot.LIME
                pd.DataFrame([{**context_common(fold, task, model_name), "explained_records": len(indices),
                    "explained_groups": len(difference), "TreeSHAP_mean_group_drop": float(group_pivot.TreeSHAP.mean()),
                    "LIME_mean_group_drop": float(group_pivot.LIME.mean()), "TreeSHAP_minus_LIME": float(difference.mean()),
                    "inference_policy": "descriptive only; source folds and groups are dependent"}]).to_csv(dest / "explanation_comparison.csv", index=False)
                grouped.to_csv(dest / "group_budget_drops.csv", index=False)
                group_pivot.assign(TreeSHAP_minus_LIME=difference).reset_index().to_csv(dest / "paired_group_drops.csv", index=False)
                write_json(dest / "explanation_complete.json", {**context_common(fold, task, model_name),
                    "manifest_sha256": sha256(OUT / "run_manifest.json"), "model_sha256": predictive_info["model_sha256"],
                    "output_sha256": output_hashes(dest, ["explanation_comparison.csv", "group_budget_drops.csv", "paired_group_drops.csv", "diagnostic_selection.csv"])})
                print(f"[explanation difference] {name}: {difference.mean():.6f}", flush=True)
                summarize()
    summarize()


def summarize():
    for name in ("predictive_metrics", "per_class_metrics", "confusion_matrices", "explanation_comparison"):
        files = sorted((OUT / "contexts").glob("*/"+name+".csv"))
        if files:
            pd.concat([pd.read_csv(path, float_precision="round_trip") for path in files], ignore_index=True).to_csv(OUT / (name+".csv"), index=False)
    baseline_files = sorted((OUT / "folds").glob("*/*_baselines.csv"))
    if baseline_files:
        pd.concat([pd.read_csv(path, float_precision="round_trip") for path in baseline_files], ignore_index=True).to_csv(OUT / "predictive_baselines.csv", index=False)
    if (OUT / "predictive_metrics.csv").exists():
        metrics = pd.read_csv(OUT / "predictive_metrics.csv", float_precision="round_trip")
        summary = metrics.groupby(["dataset","task","model"], as_index=False).agg(
            completed_folds=("fold","count"), mean_macro_f1=("macro_f1_all_test_supported_labels","mean"),
            min_macro_f1=("macro_f1_all_test_supported_labels","min"), max_macro_f1=("macro_f1_all_test_supported_labels","max"),
            min_accuracy=("accuracy","min"), mean_accuracy=("accuracy","mean"), total_test_rows=("test_rows","sum"), unseen_label_test_rows=("unseen_label_test_rows","sum"))
        summary.to_csv(OUT / "predictive_summary.csv", index=False)
    if (OUT / "explanation_comparison.csv").exists():
        explain = pd.read_csv(OUT / "explanation_comparison.csv", float_precision="round_trip")
        explain.assign(positive=explain.TreeSHAP_minus_LIME>0).groupby(["dataset","task","model"], as_index=False).agg(
            completed_folds=("fold","count"), positive_TreeSHAP_minus_LIME=("positive","sum"),
            mean_difference=("TreeSHAP_minus_LIME","mean"), min_difference=("TreeSHAP_minus_LIME","min"),
            max_difference=("TreeSHAP_minus_LIME","max")).to_csv(OUT / "explanation_summary.csv", index=False)
    write_json(OUT / "completion_status.json", {"expected_predictive_contexts": 64, "expected_explanation_contexts": 64,
        "completed_predictive_contexts": len(list((OUT / "contexts").glob("*/predictive_complete.json"))),
        "completed_explanation_contexts": len(list((OUT / "contexts").glob("*/explanation_complete.json")))})


def verify():
    folds, frames, _ = prepare_folds()
    n_pred = n_exp = 0
    for fold in folds:
        train, test, _ = partition(frames[fold["dataset"]], fold["test_sources"])
        for task in ("binary", "multiclass"):
            train_labels, actual = labels_for(train,task), labels_for(test,task)
            fold_dir = OUT / "folds" / f"{fold['dataset']}_fold{fold['fold']:02d}"
            for model_name in ("random_forest", "xgboost"):
                name = context_name(fold,task,model_name)
                dest = OUT / "contexts" / name
                model_path = OUT / "models" / (name+".joblib")
                info = validate_checkpoint(dest / "predictive_complete.json", model_path)
                for file_name, digest in (("split_audit.json", info["split_audit_sha256"]), (task+"_baselines.csv",info["baseline_sha256"])):
                    if sha256(fold_dir / file_name) != digest:
                        raise ValueError("Fold/baseline checkpoint changed")
                if sha256(OUT / "restoration_audit.json") != info["restoration_audit_sha256"]:
                    raise ValueError("Restoration audit changed")
                predictions = pd.read_csv(dest / "predictions.csv.gz", float_precision="round_trip")
                if not np.array_equal(predictions.actual_class.astype(str),actual) or not np.array_equal(predictions["__source_row"], test["__source_row"]) or not np.array_equal(predictions["__source_file"], test["__source_file"]):
                    raise ValueError("Saved predictions do not cover held-out source rows")
                metrics, per_class, confusions = score_predictions(actual,predictions.predicted_class,train_labels)
                recorded = pd.read_csv(dest / "predictive_metrics.csv", float_precision="round_trip").iloc[0]
                for key,value in metrics.items():
                    if value is not None and not np.isclose(recorded[key],value,rtol=1e-10,atol=1e-12):
                        raise ValueError(f"Metric replay mismatch: {name}/{key}")
                recorded_classes = pd.read_csv(dest / "per_class_metrics.csv", float_precision="round_trip").set_index("class")
                for row in per_class:
                    for key in ("precision","recall","f1","test_support","training_support"):
                        if not np.isclose(recorded_classes.loc[row["class"],key],row[key],rtol=1e-10,atol=1e-12):
                            raise ValueError("Per-class replay mismatch")
                saved_conf = pd.read_csv(dest / "confusion_matrices.csv")[["actual_class","predicted_class","count"]]
                pd.testing.assert_frame_equal(saved_conf,pd.DataFrame(confusions),check_dtype=False)
                n_pred += 1
                if (dest / "explanation_complete.json").exists():
                    validate_checkpoint(dest / "explanation_complete.json",model_path)
                    for explainer in ("TreeSHAP","LIME"):
                        validate_checkpoint(dest / (explainer+"_complete.json"),model_path)
                    left = pd.read_csv(dest / "TreeSHAP_fidelity.csv",float_precision="round_trip")
                    right = pd.read_csv(dest / "LIME_fidelity.csv",float_precision="round_trip")
                    keys = ["source_test_index","connection_group","k","control"]
                    if len(left) != 50*4*3 or len(right) != len(left):
                        raise ValueError("Incomplete masking evaluation")
                    pd.testing.assert_frame_equal(left[keys],right[keys])
                    random_left = left[left.control=="random"].probability_drop.to_numpy()
                    random_right = right[right.control=="random"].probability_drop.to_numpy()
                    np.testing.assert_allclose(random_left,random_right,rtol=0,atol=0)
                    n_exp += 1
    result = {"predictive_contexts_verified":n_pred,"explanation_contexts_verified":n_exp,
        "expected_predictive_contexts":64,"expected_explanation_contexts":64,
        "predictive_complete":n_pred==64,"explanations_complete":n_exp==64,
        "verification":"all checkpoint hashes; row coverage; full-label metrics; per-class support; confusion matrices; matched masking and random controls"}
    write_json(OUT / "verification.json",result)
    print(json.dumps(result),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage",choices=["prepare","predict","explain","summarize","verify","all"],default="all")
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare_folds()
    elif args.stage == "predict":
        predictive()
    elif args.stage == "explain":
        explanation_pass()
    elif args.stage == "summarize":
        freeze(); summarize()
    elif args.stage == "verify":
        verify()
    else:
        predictive(); explanation_pass(); verify()


if __name__ == "__main__":
    main()
