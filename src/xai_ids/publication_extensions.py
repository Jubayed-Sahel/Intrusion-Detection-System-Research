"""Checked result readers for the separately frozen November extensions."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TITLE = "TreeSHAP and LIME for Intrusion Detection: Sensitivity to Masking and Source Holdout"


def masking_results():
    directory = ROOT / "outputs/masking_extension_20261108"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    table = pd.read_csv(directory / "paired_comparisons.csv", float_precision="round_trip")
    expected = {(d, t, m, s) for d in ("GeNIS2025", "Gotham2025")
                for t in ("binary", "multiclass") for m in ("random_forest", "xgboost")
                for s in ("training_median_mode", "empirical_joint_donor", "retained_nearest_donor")}
    keys = ["dataset", "task", "model", "scheme"]
    if manifest.get("status") != "complete" or table.duplicated(keys).any() or set(table[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Incomplete paired masking extension")
    nearest = table[table.scheme.eq("retained_nearest_donor")]
    genis = nearest[nearest.dataset.eq("GeNIS2025")]
    summary = dict(contexts=8, records=800, schemes=3,
        nearest_positive_means=int(nearest.mean_difference_shap_minus_lime.gt(0).sum()),
        nearest_positive_intervals=int(nearest.ci_low.gt(0).sum()),
        nearest_positive_sign_tests=int(((nearest.sign_holm_p_24_comparisons < .05) & (nearest.positive_groups > nearest.negative_groups)).sum()),
        genis_nearest_min=float(genis.mean_difference_shap_minus_lime.min()),
        genis_nearest_max=float(genis.mean_difference_shap_minus_lime.max()),
        genis_crossing_intervals=int(((genis.ci_low <= 0) & (genis.ci_high >= 0)).sum()))
    return manifest, table, summary


def lime_budget_results():
    directory = ROOT / "outputs/lime_budget_20261108"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    contrasts = pd.read_csv(directory / "contrasts.csv", float_precision="round_trip")
    diagnostics = pd.read_csv(directory / "surrogate_fit.csv", float_precision="round_trip")
    context = ["dataset", "task", "model"]
    if manifest.get("status") != "complete" or len(contrasts) != 16 or len(diagnostics) != 1600:
        raise ValueError("Incomplete controlled LIME budget results")
    by_budget = diagnostics.groupby([*context, "lime_samples"])[
        ["weighted_surrogate_r2", "absolute_local_prediction_error"]].mean().unstack("lime_samples")
    against_shap = contrasts[contrasts.left.eq("TreeSHAP_saved")]
    more_lime = contrasts[contrasts.left.eq("LIME_3500")]
    if len(by_budget) != 8 or len(against_shap) != 8 or len(more_lime) != 8:
        raise ValueError("LIME budget result contexts are missing")
    error = by_budget.absolute_local_prediction_error
    summary = dict(contexts=8, explanations=len(diagnostics),
        shap_positive_means=int(against_shap.mean_difference.gt(0).sum()),
        shap_positive_sign_tests=int(((against_shap.sign_holm_p_16_contrasts < .05) & (against_shap.positive_groups > against_shap.negative_groups)).sum()),
        budget_positive_means=int(more_lime.mean_difference.gt(0).sum()),
        budget_positive_sign_tests=int(((more_lime.sign_holm_p_16_contrasts < .05) & (more_lime.positive_groups > more_lime.negative_groups)).sum()),
        error_increases=int(error[3500].gt(error[350]).sum()),
        default_high_budget_error_min=float(error[3500].min()),
        default_high_budget_error_max=float(error[3500].max()),
        weighted_r2_decreases=int(by_budget.weighted_surrogate_r2[3500].lt(by_budget.weighted_surrogate_r2[350]).sum()))
    return manifest, contrasts, by_budget, summary


def source_holdout_results():
    directory = ROOT / "outputs/source_holdout_20261108"
    status = json.loads((directory / "completion_status.json").read_text(encoding="utf-8"))
    verified = json.loads((directory / "verification.json").read_text(encoding="utf-8"))
    if (status.get("completed_predictive_contexts"), status.get("completed_explanation_contexts"),
            verified.get("predictive_contexts_verified"), verified.get("explanation_contexts_verified")) != (64, 64, 64, 64):
        raise ValueError("Source holdout is incomplete or unverified")
    predictive = pd.read_csv(directory / "predictive_metrics.csv", float_precision="round_trip")
    explanation = pd.read_csv(directory / "explanation_comparison.csv", float_precision="round_trip")
    keys = ["dataset", "fold", "task", "model"]
    for table in (predictive, explanation):
        if len(table) != 64 or table.duplicated(keys).any() or not table.groupby(keys[::2] + ["model"]).size().eq(8).all():
            raise ValueError("Source holdout fold coverage is incomplete or duplicated")
    if set(predictive[keys].itertuples(index=False, name=None)) != set(explanation[keys].itertuples(index=False, name=None)):
        raise ValueError("Source holdout predictive and explanation contexts disagree")
    metric = "macro_f1_all_test_supported_labels"
    gap = "TreeSHAP_minus_LIME"
    combined = predictive.merge(explanation[keys + [gap]], on=keys, validate="one_to_one")
    summary = combined.assign(shap_mean_positive=combined[gap].gt(0)).groupby(["dataset", "task", "model"], as_index=False).agg(
        f1_mean=(metric, "mean"), f1_min=(metric, "min"), f1_max=(metric, "max"),
        gap_min=(gap, "min"), gap_max=(gap, "max"), positive_gaps=("shap_mean_positive", "sum"))
    unique_multiclass = predictive[predictive.task.eq("multiclass")].drop_duplicates(["dataset", "fold"])
    counts = dict(contexts=len(combined), positive_gaps=int(combined[gap].gt(0).sum()),
        negative_gaps=int(combined[gap].lt(0).sum()),
        unseen_multiclass_rows=int(unique_multiclass.unseen_label_test_rows.sum()),
        genis_multiclass_min=float(summary.loc[summary.dataset.eq("GeNIS2025") & summary.task.eq("multiclass"), "f1_min"].min()),
        gotham_multiclass_min=float(summary.loc[summary.dataset.eq("Gotham2025") & summary.task.eq("multiclass"), "f1_min"].min()))
    return combined, summary, counts


def kernel_paragraph():
    directory = ROOT / "outputs/lime_kernel_20261108"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    contrasts = pd.read_csv(directory / "contrasts.csv")
    fit = pd.read_csv(directory / "surrogate_summary.csv")
    if manifest.get("status") != "complete" or len(contrasts) != 24 or len(fit) != 24:
        raise ValueError("Incomplete LIME kernel-width sensitivity")
    errors = fit.pivot(index=["dataset", "task", "model"], columns="kernel_multiplier", values="mean_absolute_point_error")
    improved = int(errors[.15].lt(errors[.75]).sum())
    new = contrasts[contrasts.kernel_multiplier.ne(.75)]
    significant = int(((new.sign_holm_p_16_new_contrasts < .05) & (new.positive_groups > new.negative_groups)).sum())
    return ("At 3,500 draws, a width grid (0.15, 0.35, 0.75 times the square root of the feature count) reuses identical sampled neighborhoods and model outputs, and reproduces the saved 0.75 fits. "
            f"The narrowest width lowers mean query error in {improved}/8 contexts but does not eliminate large errors in Gotham multiclass. Under median/mode deletion, TreeSHAP mean gaps remain positive in {int(new.mean_difference.gt(0).sum())}/16 new contrasts, with {significant}/16 positive signs after separate Holm correction. "
            "No width is selected on test performance. Weighted fit scores use different kernel weights and are not a common test distribution.")


def scenario_six_misses():
    """Replay the operational example from the saved binary confusion counts."""
    source = ROOT / "outputs/source_holdout_20261108"
    fields = ["model", "attack_test_rows", "normal_test_rows", "false_negative_rate", "false_positive_rate"]
    selected = []
    for name in ("predictive_metrics.csv", "predictive_baselines.csv"):
        frame = pd.read_csv(source / name)
        selected.append(frame.loc[frame.dataset.eq("GeNIS2025") & frame.fold.eq(6) & frame.task.eq("binary") &
                                  frame.model.isin(["random_forest", "xgboost", "depth5_tree"]), fields])
    comparison = pd.concat(selected).set_index("model", verify_integrity=True)
    if len(comparison) != 3 or comparison.attack_test_rows.nunique() != 1 or comparison.normal_test_rows.nunique() != 1:
        raise ValueError("Scenario 6 models did not evaluate the same cohort")
    return (int(comparison.attack_test_rows.iloc[0]), int(comparison.normal_test_rows.iloc[0]),
            (comparison.false_negative_rate * comparison.attack_test_rows).round().astype(int).to_dict(),
            (comparison.false_positive_rate * comparison.normal_test_rows).round().astype(int).to_dict())


def extension_abstract():
    _, _, mask = masking_results()
    _, _, source = source_holdout_results()
    from .extended_validation_results import load_extended
    coverage, _, _ = load_extended()
    attacks, _, misses, false_alarms = scenario_six_misses()
    if any(false_alarms.values()):
        raise ValueError("Scenario 6 zero false-alarm statement no longer holds")
    low, high = min(misses.values()), max(misses.values())
    return (f"In one held-out GeNIS scenario, three binary intrusion detectors raise no false alarms yet miss {low:,}-{high:,} of {attacks:,} attack records. This failure is obscured by near-perfect scores on the original connection split. We evaluate TreeSHAP and LIME for Random Forest and XGBoost on traceable, class-capped cohorts from official GeNIS and Gotham 2025 releases. On the frozen connection-group split, TreeSHAP yields greater mean predicted-class probability drop in all 24 paired contexts under median/mode replacement. "
            f"On the same seed-42 records, nearest training donors chosen by retained predictors shrink the GeNIS gaps to {mask['genis_nearest_min']:.4f}-{mask['genis_nearest_max']:.4f}; three of four pointwise mean intervals include zero. "
            "Increasing LIME from 350 to 3,500 draws does not close the median/mode gap. Narrower kernels improve fit at the explained input without consistently improving deletion. "
            f"Across sixteen source-file folds with shared connections purged, we refit 64 models and find predictive failures even for attack types seen in training. Mean median/mode deletion favors TreeSHAP in {source['positive_gaps']}/64 refits, with {source['negative_gaps']} reversals. "
            f"Uncapped testing covers {int(coverage.eligible.sum()):,} eligible records and retains substantial errors. In an independent 4,415-flow charging-network test, GeNIS-trained protocol/port models flag 34-37% of benign flows; adding duration and packet count improves source F1 but worsens external F1. These studies distinguish detector transfer from explanation fidelity and do not establish deployment readiness.")
