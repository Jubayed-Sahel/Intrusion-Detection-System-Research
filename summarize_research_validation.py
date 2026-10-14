"""Write supplemental research findings from completed validation outputs."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import pandas as pd


def main():
    output = Path("outputs/research_validation_corrected")
    paired = pd.read_csv(output / "paired_comparisons.csv")
    controls = pd.read_csv(output / "fidelity_control_tests.csv")
    primary = pd.read_csv("outputs/predictive_metrics.csv")
    clean = pd.read_csv("outputs/clean_reproduction/predictive_reproduction.csv")
    differences = []
    for row in clean.itertuples():
        reference = primary[(primary.dataset == row.dataset) & (primary.task == row.task) & (primary.model == row.model) & (primary.seed == row.model_seed)].iloc[0]
        differences.append({"dataset": row.dataset, "task": row.task, "model": row.model,
                            "seed": row.model_seed, "metric": row.metric,
                            "primary": float(reference[row.metric]), "clean": row.reproduced,
                            "absolute_difference": abs(float(reference[row.metric]) - row.reproduced)})
    comparison = pd.DataFrame(differences)
    comparison.to_csv(output / "clean_vs_current_primary.csv", index=False)
    significant = (paired.ci_low > 0) & (paired.holm_adjusted_p_all_seeds < 0.05)
    passing_controls = (controls.ci_low > 0) & (controls.holm_adjusted_p_all_seeds < 0.05)
    summary = {"model_seed_contexts": len(paired), "flows_per_context": int(paired.n_pairs.iloc[0]),
               "positive_mean_differences": int((paired.mean_difference_shap_minus_lime > 0).sum()),
               "positive_ci_and_global_holm_significance": int(significant.sum()),
               "mean_difference_range": [float(paired.mean_difference_shap_minus_lime.min()), float(paired.mean_difference_shap_minus_lime.max())],
               "random_control_passes_global_holm": {name: int(passing_controls[controls.explainer == name].sum()) for name in ("TreeSHAP", "LIME")},
               "clean_primary_seed_predictive_max_absolute_difference": float(comparison.absolute_difference.max()),
               "clean_predictive_contexts": int(comparison.groupby(["dataset", "task", "model", "seed"]).ngroups),
               "limitations": ["source conversion history unavailable", "flow-level inference may underestimate session dependence", "latency under concurrent jobs is descriptive", "no human usefulness or live deployment evidence"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    fig, axes = plt.subplots(4, 2, figsize=(10, 11), sharex=True)
    for ax, ((dataset, task, model), group) in zip(axes.flat, paired.groupby(["dataset", "task", "model"])):
        group = group.sort_values("model_seed")
        values = group.mean_difference_shap_minus_lime.to_numpy()
        ax.errorbar(values, group.model_seed.astype(str),
                    xerr=[values - group.ci_low.to_numpy(), group.ci_high.to_numpy() - values],
                    fmt="o", capsize=4, color="#245c7a")
        ax.axvline(0, color="gray", linewidth=1)
        ax.set_title(f"{dataset} / {task} / {model}", fontsize=9)
        ax.set_ylabel("Model seed")
        ax.set_xlabel("Mean SHAP − LIME probability-drop difference")
    fig.suptitle("Expanded XAI validation: 100 matched flows per model seed", fontsize=13)
    fig.text(0.5, 0.005, "Source: corrected local validation, 14 October 2026. Bars: paired flow bootstrap 95% intervals; seeds are not independent flow samples.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.025, 1, 0.97))
    fig.savefig(output / "model_seed_fidelity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
