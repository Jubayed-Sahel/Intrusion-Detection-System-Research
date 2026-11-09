"""Exploratory paired sensitivity to training-only replacement distributions.

See MASKING_EXTENSION_PROTOCOL_20261108.md; frozen primary artifacts are read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest

SEED = 20261108
BUDGETS = (1, 3, 5, 10)
DONORS = 32
POOL_SIZE = 5000
SCHEMES = ("training_median_mode", "empirical_joint_donor", "retained_nearest_donor")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(context, row_index):
    token = f"{SEED}:{context}:{row_index}".encode()
    return int.from_bytes(hashlib.sha256(token).digest()[:8], "little")


def training_scale(x_train):
    """Numeric distances use training values alone, with finite fallbacks."""
    scale = np.subtract(*np.percentile(x_train, [75, 25], axis=0))
    std = np.std(x_train, axis=0)
    return np.where(scale > 1e-12, scale, np.where(std > 1e-12, std, 1.0))


def feature_distances(pool, row, scale, categorical_indices):
    distances = np.minimum(np.abs(pool - row) / scale, 1.0)
    if categorical_indices:
        distances[:, categorical_indices] = pool[:, categorical_indices] != row[categorical_indices]
    return distances


def nearest_donors(distances, retained_indices, n=DONORS):
    """Only retained predictors determine donor eligibility and ordering."""
    if not len(retained_indices):
        raise ValueError("Nearest-donor conditioning requires a retained predictor")
    mean_distance = distances[:, retained_indices].mean(axis=1)
    order = np.argsort(mean_distance, kind="stable")[:n]
    return order, mean_distance[order]


def masked_rows(row, removed_indices, donor_rows):
    result = np.repeat(np.asarray(row)[None, :], len(donor_rows), axis=0)
    result[:, removed_indices] = donor_rows[:, removed_indices]
    return result


def holm(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1, np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1)))
    return adjusted


def group_differences(frame):
    keys = ["scheme", "explainer", "source_test_index", "k"]
    if frame.duplicated(keys).any() or not np.isfinite(frame.probability_drop).all():
        raise ValueError("Duplicate or nonfinite deletion values")
    if not frame.groupby("source_test_index").connection_group.nunique().eq(1).all():
        raise ValueError("A diagnostic record has multiple connection groups")
    expected = set(BUDGETS)
    if not frame.groupby(keys[:3]).k.agg(set).map(lambda value: value == expected).all():
        raise ValueError("Incomplete masking budgets")
    paired = frame.pivot(index=["scheme", "connection_group", "source_test_index", "k"],
                         columns="explainer", values="probability_drop")
    if set(paired.columns) != {"TreeSHAP", "LIME"} or paired.isna().any().any():
        raise ValueError("Unmatched explanation records")
    values = paired.TreeSHAP - paired.LIME
    # Original endpoint: records within group and budget, then budgets within group.
    return values.groupby(level=[0, 1, 3]).mean().groupby(level=[0, 1]).mean()


def summarize(values, seed):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("At least two finite group differences are required")
    positive = int((values > 1e-12).sum())
    negative = int((values < -1e-12).sum())
    n_nonzero = positive + negative
    rng = np.random.default_rng(seed)
    bootstrap = values[rng.integers(0, len(values), (2000, len(values)))].mean(axis=1)
    low, high = np.percentile(bootstrap, [2.5, 97.5])
    return dict(n_groups=len(values), mean_difference_shap_minus_lime=float(values.mean()),
                median_difference=float(np.median(values)), ci_low=float(low), ci_high=float(high),
                positive_groups=positive, negative_groups=negative, tied_groups=len(values)-n_nonzero,
                sign_two_sided_p=float(binomtest(positive, n_nonzero, .5).pvalue) if n_nonzero else 1.)


def saved_attributions(path, feature_names):
    frame = pd.read_csv(path, float_precision="round_trip")
    if frame.duplicated(["source_test_index", "feature"]).any():
        raise ValueError("Duplicate saved attribution")
    if set(frame.feature) != set(feature_names):
        raise ValueError("Saved attribution features differ from the model")
    matrix = frame.pivot(index="source_test_index", columns="feature", values="attribution").reindex(columns=feature_names)
    if len(matrix) != 100 or not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Expected 100 complete saved explanation vectors")
    metadata = frame.drop_duplicates("source_test_index").set_index("source_test_index").loc[matrix.index]
    return matrix, metadata


def run(results: Path, output: Path):
    project = Path(__file__).resolve().parent
    protocol = project / "MASKING_EXTENSION_PROTOCOL_20261108.md"
    output.mkdir(parents=True, exist_ok=True)
    sources = {}

    def record(path):
        path = Path(path).resolve()
        key = path.relative_to(project).as_posix() if path.is_relative_to(project) else path.as_posix()
        sources[key] = sha256(path)

    record(Path(__file__))
    record(protocol)
    record(results / "run_manifest.json")
    source_config = json.loads((results / "run_manifest.json").read_text())["config"]
    snapshots = output / "source_snapshots"
    snapshots.mkdir(exist_ok=True)
    for source in (Path(__file__), protocol):
        (snapshots / source.name).write_bytes(source.read_bytes())
    all_summary, all_groups, audits = [], [], []
    for dataset in ("GeNIS2025", "Gotham2025"):
        root = project / "data/prepared" / dataset
        provenance = json.loads((root / "provenance.json").read_text())
        record(root / "provenance.json")
        for filename in ("train.parquet", "test.parquet"):
            record(root / filename)
            if sha256(root / filename) != provenance["prepared_files"][filename]["sha256"]:
                raise ValueError("Prepared input checksum mismatch")
        train, test = pd.read_parquet(root / "train.parquet"), pd.read_parquet(root / "test.parquet")
        for task in ("binary", "multiclass"):
            for model_name in ("random_forest", "xgboost"):
                context = f"{dataset}_{task}_{model_name}_42"
                print(f"[masking sensitivity] {context}", flush=True)
                checkpoint = results / "contexts" / context
                model_path = results / "models" / f"{dataset}_{task}_{model_name}.joblib"
                record(model_path)
                artifact = joblib.load(model_path)
                if artifact["seed"] != 42 or artifact["dataset"] != dataset or artifact["task"] != task:
                    raise ValueError("Saved model identity mismatch")
                model, preprocessor = artifact["model"], artifact["preprocessor"]
                # Execution parallelism only; predictive parameters/weights remain unchanged.
                model.set_params(n_jobs=2)
                x_train, x_test = preprocessor.transform(train), preprocessor.transform(test)
                if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
                    raise ValueError("Nonfinite transformed input")
                pool_indices = np.random.default_rng(SEED).choice(len(x_train), min(POOL_SIZE, len(x_train)), replace=False)
                pool, scale = x_train[pool_indices], training_scale(x_train)
                matrices, metadata = {}, {}
                for explainer in ("TreeSHAP", "LIME"):
                    path = checkpoint / f"{explainer}_attributions.csv"
                    record(path)
                    matrices[explainer], metadata[explainer] = saved_attributions(path, preprocessor.feature_names)
                    if set(metadata[explainer].model_seed) != {42} or set(metadata[explainer].explainer) != {explainer}:
                        raise ValueError("Saved explanation identity mismatch")
                if not matrices["TreeSHAP"].index.equals(matrices["LIME"].index):
                    raise ValueError("Saved explanation records are unmatched")
                indices = matrices["TreeSHAP"].index.to_numpy(dtype=int)
                probabilities = model.predict_proba(x_test[indices])
                predicted = probabilities.argmax(axis=1)
                for explainer in metadata:
                    labels = np.asarray(artifact["classes"])[predicted]
                    if not np.array_equal(labels, metadata[explainer].predicted_class):
                        raise ValueError("Model and explanation predicted classes differ")
                    if not np.allclose(probabilities.max(axis=1), metadata[explainer].confidence, rtol=0, atol=1e-7):
                        raise ValueError("Model and explanation probabilities differ")
                record(checkpoint / "fidelity.csv")
                original = pd.read_csv(checkpoint / "fidelity.csv", float_precision="round_trip")
                original_top = original[original.control.eq("top")].set_index(["explainer", "source_test_index", "k"])
                details, perturbations, cursor = [], [], 0
                for local_id, source_index in enumerate(indices):
                    row = x_test[source_index]
                    distances = feature_distances(pool, row, scale, preprocessor.categorical_indices)
                    common_donors = np.random.default_rng(stable_seed(context, int(source_index))).choice(len(pool), DONORS, replace=False)
                    for explainer, matrix in matrices.items():
                        ranking = np.argsort(-np.abs(matrix.loc[source_index].to_numpy()))
                        for k in BUDGETS:
                            removed, retained = ranking[:min(k, len(row))], ranking[min(k, len(row)):]
                            conditional, conditional_distance = nearest_donors(distances, retained)
                            for scheme, donor_ids in ((SCHEMES[0], None), (SCHEMES[1], common_donors), (SCHEMES[2], conditional)):
                                donors = np.asarray(preprocessor.baseline_)[None, :] if donor_ids is None else pool[donor_ids]
                                perturbed = masked_rows(row, removed, donors)
                                perturbations.append(perturbed)
                                details.append(dict(dataset=dataset, task=task, model=model_name, model_seed=42,
                                    explainer=explainer, source_test_index=int(source_index), connection_group=test.iloc[source_index]["__group"],
                                    k=k, scheme=scheme, original_probability=float(probabilities[local_id, predicted[local_id]]),
                                    target_class=int(predicted[local_id]), predicted_class=artifact["classes"][predicted[local_id]],
                                    removed_features=json.dumps([preprocessor.feature_names[i] for i in removed]),
                                    donor_training_indices=json.dumps([] if donor_ids is None else pool_indices[donor_ids].tolist()),
                                    mean_retained_distance=float(conditional_distance.mean()) if scheme == SCHEMES[2] else np.nan,
                                    _start=cursor, _stop=cursor+len(perturbed)))
                                cursor += len(perturbed)
                masked_probability = model.predict_proba(np.concatenate(perturbations))
                del perturbations
                maximum_reference_error = 0.
                for detail in details:
                    start, stop = detail.pop("_start"), detail.pop("_stop")
                    donor_probabilities = masked_probability[start:stop, detail["target_class"]]
                    detail["replacement_probability"] = float(donor_probabilities.mean())
                    detail["donor_probability_sd"] = float(donor_probabilities.std(ddof=0))
                    detail["probability_drop"] = detail["original_probability"] - detail["replacement_probability"]
                    if detail["scheme"] == SCHEMES[0]:
                        key = (detail["explainer"], detail["source_test_index"], detail["k"])
                        reference = original_top.loc[key]
                        if reference.connection_group != detail["connection_group"]:
                            raise ValueError("Original and current connection groups disagree")
                        maximum_reference_error = max(maximum_reference_error, abs(detail["probability_drop"]-reference.probability_drop))
                if maximum_reference_error > 1e-7:
                    raise ValueError(f"Original median/mode reproduction failed: {maximum_reference_error}")
                frame = pd.DataFrame(details)
                group_values = group_differences(frame)
                for scheme in SCHEMES:
                    values = group_values.loc[scheme]
                    common = dict(dataset=dataset, task=task, model=model_name, model_seed=42, scheme=scheme)
                    all_summary.append({**common, **summarize(values, stable_seed(context+scheme, 0))})
                    all_groups.extend({**common, "connection_group": str(group), "difference_shap_minus_lime": float(value)} for group, value in values.items())
                audits.append(dict(context=context, diagnostic_records=len(indices), pool_rows=len(pool), donor_rows=DONORS,
                                   maximum_original_reference_error=maximum_reference_error))
                frame.to_csv(output / f"{context}.csv", index=False)
    summary = pd.DataFrame(all_summary)
    if len(summary) != 24:
        raise ValueError("Incomplete extension context coverage")
    summary["sign_holm_p_24_comparisons"] = holm(summary.sign_two_sided_p)
    summary.to_csv(output / "paired_comparisons.csv", index=False)
    pd.DataFrame(all_groups).to_csv(output / "group_differences.csv", index=False)
    counts = {scheme: dict(positive_means=int(table.mean_difference_shap_minus_lime.gt(0).sum()),
        positive_sign_holm=int(((table.sign_holm_p_24_comparisons < .05) & (table.positive_groups > table.negative_groups)).sum()),
        negative_sign_holm=int(((table.sign_holm_p_24_comparisons < .05) & (table.negative_groups > table.positive_groups)).sum()))
        for scheme, table in summary.groupby("scheme")}
    manifest = dict(analysis="Exploratory paired replacement sensitivity, separate from frozen primary inference",
        protocol=protocol.name, seed=SEED, model_seed=42, diagnostic_records_per_context=100,
        contexts=8, comparisons=24, budgets=BUDGETS, donors=DONORS, pool_size=POOL_SIZE,
        bootstrap_replicates=2000, sign_test="two-sided exact; ties <=1e-12 omitted; Holm over 24 tests",
        interval="pointwise 95% connection-resampled percentile bootstrap; no simultaneous coverage",
        source_primary_configuration=source_config, execution_python=platform.python_version(),
        execution_packages={name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "scikit-learn", "xgboost", "joblib")},
        model_inference_threads=2,
        status="complete", summary=counts, context_audits=audits, sha256=sources,
        limitations="Retained-feature distance is an approximate conditioning sensitivity, not a validated conditional sampler. Hybrid records can be invalid. Diagnostic records and one fitted seed are not external-validation evidence; groups can retain campaign dependence.")
    manifest["artifacts_sha256"] = {path.relative_to(output).as_posix(): sha256(path)
        for path in sorted(output.rglob("*")) if path.is_file() and path.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2), flush=True)


def verify(output: Path):
    """Reconstruct group endpoints and all exploratory tests; validate byte hashes."""
    project = Path(__file__).resolve().parent
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest.get("status") != "complete":
        raise ValueError("Extension is not complete")
    for relative, expected in manifest["sha256"].items():
        if sha256(project / relative) != expected:
            raise ValueError(f"Input/source checksum mismatch: {relative}")
    for relative, expected in manifest["artifacts_sha256"].items():
        if sha256(output / relative) != expected:
            raise ValueError(f"Output checksum mismatch: {relative}")
    expected_contexts = {f"{d}_{t}_{m}_42" for d in ("GeNIS2025", "Gotham2025")
                         for t in ("binary", "multiclass") for m in ("random_forest", "xgboost")}
    if {row["context"] for row in manifest["context_audits"]} != expected_contexts:
        raise ValueError("Context coverage mismatch")
    reconstructed = []
    for audit in manifest["context_audits"]:
        context = audit["context"]
        frame = pd.read_csv(output / f"{context}.csv", float_precision="round_trip")
        if len(frame) != 2400 or frame.source_test_index.nunique() != 100 or set(frame.scheme) != set(SCHEMES):
            raise ValueError("Incomplete diagnostic record/scheme coverage")
        for (_, source_index), records in frame.groupby(["explainer", "source_test_index"]):
            if len(records) != 12:
                raise ValueError("Incomplete per-record comparison")
        # The empirical common random draws must be shared across both rankings and budgets.
        empirical = frame[frame.scheme.eq(SCHEMES[1])]
        if not empirical.groupby("source_test_index").donor_training_indices.nunique().eq(1).all():
            raise ValueError("Unpaired empirical donor draws")
        donor_lists = frame.loc[~frame.scheme.eq(SCHEMES[0]), "donor_training_indices"].map(json.loads)
        if not donor_lists.map(lambda values: len(values) == DONORS and len(set(values)) == DONORS).all():
            raise ValueError("Incorrect donor count or duplicate donors")
        values = group_differences(frame)
        first = frame.iloc[0]
        for scheme in SCHEMES:
            reconstructed.append(dict(dataset=first.dataset, task=first.task, model=first.model,
                model_seed=42, scheme=scheme, **summarize(values.loc[scheme], stable_seed(context+scheme, 0))))
    reconstructed = pd.DataFrame(reconstructed)
    reconstructed["sign_holm_p_24_comparisons"] = holm(reconstructed.sign_two_sided_p)
    actual = pd.read_csv(output / "paired_comparisons.csv", float_precision="round_trip")
    keys = ["dataset", "task", "model", "model_seed", "scheme"]
    if actual.duplicated(keys).any() or len(actual) != 24:
        raise ValueError("Comparison coverage mismatch")
    reconstructed, actual = [table.set_index(keys).sort_index() for table in (reconstructed, actual)]
    if not reconstructed.index.equals(actual.index):
        raise ValueError("Comparison identities disagree")
    np.testing.assert_allclose(reconstructed.to_numpy(), actual[reconstructed.columns].to_numpy(), rtol=1e-10, atol=1e-12)
    print("Verified all 8 contexts, 800 matched records, 24 group endpoints/tests, common donors, and input/output hashes.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("outputs/recent2025"))
    parser.add_argument("--output", type=Path, default=Path("outputs/masking_extension_20261108"))
    parser.add_argument("--verify", action="store_true", help="Validate saved artifacts without model inference")
    arguments = parser.parse_args()
    if arguments.verify:
        verify(arguments.output)
    else:
        run(arguments.results, arguments.output)
