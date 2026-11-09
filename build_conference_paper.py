"""Build a separate, anonymous IEEE conference review manuscript (at most six pages).

This concise narrative consumes the frozen primary study and separately labelled
post-hoc audits. It does not change their inputs, inference or saved outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from src.xai_ids.extended_validation_results import load_extended, large_test_finding
from src.xai_ids.publication_extensions import TITLE, extension_abstract, kernel_paragraph, lime_budget_results, masking_results, scenario_six_misses, source_holdout_results

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "paper" / "conference"
OUTPUT = ROOT / "output" / "pdf" / "xai_ids_conference_review.pdf"


def records(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def esc(value):
    return str(value).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def table(caption, label, columns, headers, rows):
    lines = [r"\begin{table}[t]\centering", r"\caption{" + caption + "}",
             r"\label{" + label + "}", r"\footnotesize",
             r"\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}",
             r"\begin{tabular}{" + columns + r"}\toprule",
             " & ".join(headers) + r" \\\midrule"]
    lines.extend(" & ".join(row) + r" \\" for row in rows)
    lines.extend([r"\bottomrule\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def figure(masking):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, ax = plt.subplots(figsize=(3.48, 2.95))
    contexts = [(d, t, m) for d in ("GeNIS2025", "Gotham2025")
                for t in ("binary", "multiclass") for m in ("random_forest", "xgboost")]
    colors = ["#165a8c", "#a24c13", "#378047"]
    schemes = ("training_median_mode", "empirical_joint_donor", "retained_nearest_donor")
    scheme_labels = ("Median/mode", "Joint donor", "Nearest donor")
    for i, (dataset, task, model) in enumerate(contexts):
        for j, scheme in enumerate(schemes):
            row = masking.loc[masking.dataset.eq(dataset) & masking.task.eq(task) &
                              masking.model.eq(model) & masking.scheme.eq(scheme)].iloc[0]
            mean, low, high = [float(row[k]) for k in
                               ("mean_difference_shap_minus_lime", "ci_low", "ci_high")]
            ax.errorbar(mean, 7-i+(1-j)*.20, xerr=[[mean-low], [high-mean]],
                        fmt=("o", "s", "^")[j], markersize=3.2, capsize=1.5,
                        elinewidth=.75, color=colors[j], label=scheme_labels[j] if i == 0 else None)
    ax.axvline(0, color="#555555", linewidth=.7)
    ax.axhline(3.5, color="#cccccc", linewidth=.6)
    ax.set_yticks(np.arange(8), [f"{d.replace('2025','')} {'Bin' if t=='binary' else 'Multi'} "
                                  f"{'RF' if m=='random_forest' else 'XGB'}"
                                  for d,t,m in contexts][::-1])
    ax.set_xlim(-.018,.37)
    ax.set_xlabel("TreeSHAP minus LIME probability drop")
    ax.grid(axis="x", alpha=.22, linewidth=.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(title="Replacement rule", loc="upper center", bbox_to_anchor=(.5, 1.23),
              ncol=3, fontsize=7, title_fontsize=7, frameon=False,
              handletextpad=.4, labelspacing=.2, columnspacing=1.2)
    fig.tight_layout(pad=.25)
    fig.savefig(PROJECT / "figures" / "mask_sensitivity.pdf")
    plt.close(fig)


def bibliography():
    # Resolve by bibliographic identity, not the full manuscript's mutable
    # citation numbers. Its related-work additions can renumber the methods.
    source = (ROOT / "paper" / "ieee" / "main.tex").read_text(encoding="utf-8")
    old = dict(re.findall(r"\\bibitem\{ref(\d+)\}\s*(.*?)(?=\n\\bibitem|\n\\end\{thebibliography\})",
                          source, flags=re.S))
    aliases = {"genis_record":"10.5281/zenodo.14919237", "genis":"10.1016/j.dib.2025.111487",
               "gotham_record":"10.5281/zenodo.14502760", "gotham":"10.48550/arXiv.2502.03134",
               "rf":"10.1023/A:1010933404324", "xgb":"10.1145/2939672.2939785",
               "shap":"A unified approach to interpreting model predictions",
               "treeshap":"10.1038/s42256-019-0138-9", "lime":"10.1145/2939672.2939778",
               "yeh":"On the (in)fidelity and sensitivity of explanations",
               "neupane":"10.1109/ACCESS.2022.3216617", "gaspar":"10.1109/ACCESS.2024.3368377",
               "warnecke":"10.1109/EuroSP48549.2020.00018", "exai":"10.1109/ACCESS.2024.3365140",
               "covert":"Explaining by removing", "efron":"10.1214/aos/1176344552",
               "wilcoxon":"Individual comparisons by ranking methods",
               "holm":"A simple sequentially rejective multiple test procedure"}
    bib = {}
    for key, marker in aliases.items():
        matches = [value.strip() for value in old.values() if marker.casefold() in value.casefold()]
        if len(matches) != 1:
            raise ValueError(f"Bibliographic identity must resolve uniquely: {key}")
        bib[key] = matches[0]
    bib.update({
        "forensic": r'P. Hermosilla, S. Berrios, and H. Allende-Cid, "Explainable AI for forensic analysis: A comparative study of SHAP and LIME in intrusion detection models," \emph{Applied Sciences}, vol. 15, no. 13, art. no. 7329, 2025, doi: 10.3390/app15137329.',
        "versatile": r'B. Nugraha, A. V. Jnanashree, and T. Bauschert, "A versatile XAI-based framework for efficient and explainable intrusion detection systems," \emph{Annals of Telecommunications}, vol. 80, pp. 1095--1120, 2025, doi: 10.1007/s12243-025-01118-9.',
        "kalakoti": r'R. Kalakoti, R. Vaarandi, H. Bahsi, and S. N\~omm, "Evaluating explainable AI for deep learning-based network intrusion detection system alert classification," arXiv:2506.07882, ver. 1, 2025. [Online]. Available: \url{https://arxiv.org/abs/2506.07882v1}.',
        "arp": r'D. Arp \emph{et al.}, "Dos and don\textquotesingle ts of machine learning in computer security," in \emph{Proc. USENIX Security Symp.}, 2022, pp. 3971--3988.',
        "engelen": r'G. Engelen, V. Rimmer, and W. Joosen, "Troubleshooting an intrusion detection dataset: The CICIDS2017 case study," in \emph{Proc. IEEE Security and Privacy Workshops}, 2021, pp. 7--12, doi: 10.1109/SPW53761.2021.00009.',
        "tesseract": r'F. Pendlebury, F. Pierazzi, R. Jordaney, J. Kinder, and L. Cavallaro, "TESSERACT: Eliminating experimental bias in malware classification across space and time," in \emph{Proc. USENIX Security Symp.}, 2019, pp. 729--746.',
        "hase": r'P. Hase, H. Xie, and M. Bansal, "The out-of-distribution problem in explainability and search methods for feature importance explanations," in \emph{Advances in Neural Information Processing Systems}, vol. 34, 2021.',
        "aas": r'K. Aas, M. Jullum, and A. L\o land, "Explaining individual predictions when features are dependent: More accurate approximations to Shapley values," \emph{Artificial Intelligence}, vol. 298, art. no. 103502, 2021, doi: 10.1016/j.artint.2021.103502.',
        "hooker": r'S. Hooker, D. Erhan, P.-J. Kindermans, and B. Kim, "A benchmark for interpretability methods in deep neural networks," in \emph{Advances in Neural Information Processing Systems}, vol. 32, 2019.',
        "quantus": r'A. Hedstr\"om \emph{et al.}, "Quantus: An explainable AI toolkit for responsible evaluation of neural network explanations and beyond," \emph{Journal of Machine Learning Research}, vol. 24, no. 34, pp. 1--11, 2023.',
        "slack": r'D. Slack, S. Hilgard, E. Jia, S. Singh, and H. Lakkaraju, "Fooling LIME and SHAP: Adversarial attacks on post hoc explanation methods," in \emph{Proc. AAAI/ACM Conf. AI, Ethics, and Society}, 2020, pp. 180--186.',
        "ocpp": next(v.strip() for v in old.values() if "10.21227/v1f0-9t13" in v),
        "almohammadi": r'K. Almohammadi et al., "An explainable data-local federated learning framework for intrusion detection in connected healthcare systems," Frontiers in Medicine, vol. 13, art. 1989148, 2026, doi: 10.3389/fmed.2026.1989148.',
        "rudin": r'C. Rudin, "Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead," \emph{Nature Machine Intelligence}, vol. 1, pp. 206--215, 2019, doi: 10.1038/s42256-019-0048-x.',
    })
    return bib


def export():
    PROJECT.mkdir(parents=True, exist_ok=True)
    (PROJECT / "figures").mkdir(exist_ok=True)
    primary = ROOT / "outputs" / "recent2025"
    patterns = ROOT / "outputs" / "pattern_sensitivity_20261107"
    paired = records(primary / "paired_comparisons.csv")
    predictive = records(primary / "predictive_summary.csv")
    baseline = records(primary / "predictive_baselines.csv")
    pattern_manifest = json.loads((patterns / "manifest.json").read_text())
    assert len(paired) == 24 and pattern_manifest["summary"]["contexts"] == 24
    assert pattern_manifest["summary"]["positive_sign_test_holm"] == 24
    _, masking, mask_summary = masking_results()
    _, _, _, budget_summary = lime_budget_results()
    transfer, transfer_summary, transfer_counts = source_holdout_results()
    figure(masking)
    coverage, uncapped, external = load_extended()
    extra_rows = []
    for (spec, model), group in external.groupby(["feature_set","model"]):
        values = group.set_index("test")
        target = values.loc["OCPP"]
        extra_rows.append(["Transport" if spec=="transport" else "+ duration/count", "RF" if model=="random_forest" else "XGB",
                           f'{values.loc["GeNIS","macro_f1"]:.3f}', f'{target.macro_f1:.3f}', str(int(target.missed)), str(int(target.false_alarms))])
    external_table = table("Independent OCPP test: misses out of 3,532 attacks; false alarms out of 883 benign flows",
                           "tab:external","llcccc",["Set","Model","Source F1","OCPP F1","Missed","False alarms"],extra_rows)

    prep_table = table("Prepared cohorts and frozen group holdout", "tab:data", "lrr", ["Property", "GeNIS", "Gotham"], [
        ["Source records scanned", "3,087,981", "35,134,281"],
        ["Selected known-label records", "40,000", "133,490"],
        ["Train / test records", "32,346 / 7,654", "107,120 / 26,370"],
        ["Train / test groups", "23,487 / 5,872", "46,615 / 11,654"],
        ["Predictors after preparation", "69", "13"],
        ["Train / test-supported labels", "4 / 4", "17 / 16"],
        ["Overlapping train/test groups", "0", "0"],
        ["Test patterns seen in training", "379", "1,914"]])
    predictive_rows = []
    for dataset in ("GeNIS2025", "Gotham2025"):
        for task in ("binary", "multiclass"):
            vals=[]
            for model in ("random_forest", "xgboost"):
                r=next(r for r in predictive if (r["dataset"],r["task"],r["model"])==(dataset,task,model))
                vals.append(f"{float(r['mean']):.4f} ({float(r['std']):.4f})")
            b=next(r for r in baseline if (r["dataset"],r["task"],r["model"])==(dataset,task,"depth5_tree"))
            predictive_rows.append([dataset.replace("2025", "") + (" bin." if task=="binary" else " multi."),
                                    *vals, f"{float(b['macro_f1_supported_classes']):.4f}"])
    pred_table = table("Supported-label macro-F1: five-seed mean (SD) and seed-42 shallow-tree baseline", "tab:prediction", "lccc",
                       ["Dataset/task", "RF", "XGB", "Tree"], predictive_rows)
    transfer_rows=[]
    for row in transfer_summary.itertuples(index=False):
        label = f"{row.dataset.removesuffix('2025')} {'Bin.' if row.task=='binary' else 'Multi.'} {'RF' if row.model=='random_forest' else 'XGB'}"
        transfer_rows.append([label, f"{row.f1_mean:.3f} [{row.f1_min:.3f},{row.f1_max:.3f}]",
                              f"{row.gap_min:.3f} to {row.gap_max:.3f}", f"{row.positive_gaps}/8"])
    transfer_table = table("Source holdout: all-test-label macro-F1 and paired deletion across eight folds per row",
                           "tab:transfer", "lccc", ["Dataset/task/model", "F1 mean [range]", r"Gap range", "Pos."], transfer_rows)

    body = r'''
\section{Introduction}
An intrusion detector's explanation is meaningful only relative to a specified model, data pipeline and evaluation target. Security machine learning can be distorted by sampling, labels, data leakage and testbed shortcuts \cite{arp}; reconstruction errors in an IDS dataset can materially change class-level results \cite{engelen}. A recent release date does not by itself resolve these problems. We evaluate two openly accessible 2025 author releases, GeNIS \cite{genis_record,genis} and Gotham \cite{gotham_record,gotham}, while retaining source-to-cohort provenance and explicit traffic-group boundaries.

We compare Random Forest (RF) \cite{rf} and XGBoost (XGB) \cite{xgb} for binary and multiclass prediction, and TreeSHAP and LIME on matched records. We ask how the comparison changes with the replacement rule, LIME settings and a source-file split that also purges shared connections. The contribution is empirical evidence about which conclusions persist, supported by traceable source preparation, rather than a new explanation algorithm.

The primary connection split and its statistical families remain frozen. Additional protocols were written before their own execution, after the primary results were known. These extensions diagnose setting dependence within two testbeds and are exploratory.

\section{Related work and evaluation construct}
SHAP assigns additive feature contributions for a specified value function \cite{shap}; TreeSHAP implements efficient tree-ensemble explanations \cite{treeshap}. LIME fits a local surrogate on perturbed neighbors \cite{lime}. Explanation quality has several dimensions rather than a universal scalar: the X-IDS survey \cite{neupane} and security evaluation by Warnecke \emph{et al.} \cite{warnecke} distinguish practical objectives and quantitative criteria. E-XAI compares SHAP and LIME on three IDS datasets using six criteria and Wilcoxon tests \cite{exai}. Gaspar \emph{et al.} investigate system-call sequence explanations, explanation-guided perturbations and perceived interpretability \cite{gaspar}. Therefore, neither using two explainers nor applying quantitative tests is new here.

More recent close comparisons further constrain the contribution. Hermosilla \emph{et al.} compare KernelSHAP and LIME for XGBoost/TabNet using fidelity, stability and feature agreement \cite{forensic}. Nugraha \emph{et al.} study feature selection, retraining, explanation consistency and cost \cite{versatile}. Kalakoti \emph{et al.} evaluate several explainers for deep alert classification, where method rankings depend on the metric \cite{kalakoti}. Their tasks, SHAP variants, backgrounds and perturbation budgets differ from ours; numerical scores cannot be directly ranked across those studies. Almohammadi et al. report weak LIME local fit and missed spoofing attacks in simulated healthcare federation \cite{almohammadi}. Their median-replacement evaluation motivates testing whether the intervention changes the comparison; their scores do not serve as a baseline for these testbeds.

Removal-based evaluation separates the removal mechanism, measured model behavior and summary statistic \cite{covert}. Infidelity and sensitivity likewise depend on perturbation distributions \cite{yeh}, and responsible evaluation requires specifying metric parameters \cite{quantus}. Replacing features can produce inputs outside training support \cite{hase}; dependencies among predictors alter both plausible replacements and attribution interpretations \cite{aas}. Our endpoint is consequently called \emph{deletion fidelity under the stated mask}. It tests a fitted model's response to synthetic predictor replacement, not causal attack relevance. Retraining after removal, as in ROAR \cite{hooker} and E-XAI's descriptive-accuracy analysis, asks a different question.

We extend these designs by comparing fixed rankings under three replacement rules, testing the LIME surrogate budget and locality, and repeating training and explanation under held-out source files. This links the measured explanation advantage to explicit evaluation choices.

\section{Traceable cohorts and frozen holdout}
\subsection{Acquisition and checksum scope}
GeNIS provides simulated enterprise traffic scenarios. We process all eight scenario CSVs at the 5-second flow interval. Both consumed archives match the provider MD5 values; archive and member SHA-256 digests are recorded. Gotham provides packet-level exports from 78 emulated IoT devices. All 78 CSVs and the README are acquired from the official ZIP using HTTP byte ranges. Each member's extracted length and CRC32 match the ZIP directory, and a local SHA-256 is recorded. The complete 23.8-GB Gotham ZIP was not downloaded, so its advertised whole-archive MD5 is \textbf{unverified}. Member checks must not be described as whole-archive verification. Author-generated exports, rather than regenerated raw packet features, are the starting inputs for both datasets.

\subsection{Sampling, labels and preprocessing}
Every selected source member is scanned. Deterministic random priorities with preparation seed 42 retain at most 10,000 records per original eligible label globally, not separately per file. Gotham's 7,670 Unknown-labelled records are excluded before either supervised task; unknown does not mean attack. Binary targets merge only known attacks. Multiclass targets retain the original known categories. Table~\ref{tab:data} describes the resulting cohorts. Class capping changes traffic prevalence and does not model natural alert load.

Audit identifiers, IP/MAC addresses, timestamps, payloads, labels and selected exporter artifacts are excluded from predictors. Retained ports, protocols and traffic statistics may still encode testbed signatures. Constant-column removal, numerical median imputation and categorical encoding/imputation are fitted on training data only. One constant Gotham predictor is removed, leaving 13. No test-set tuning or feature selection is used for the primary models.
''' + prep_table + r'''
\subsection{Global groups and label support}
GeNIS groups use the provider FlowID globally across scenario files. Gotham groups use a canonical bidirectional IP/transport-port tuple plus protocol globally across device files. Endpoint-equivalent records therefore cannot cross the partition through a different device filename. A GroupShuffleSplit requests 20\% test groups with seed 42. Before fitting, the first of at most 200 candidates covering every eligible label in both partitions is frozen. A label confined to one group is kept entirely in training; there is no row-random fallback. The accepted candidates are 0 for GeNIS and 11 for Gotham.

There are zero shared group keys between training and test. This does not imply all predictor vectors are distinct: 379 GeNIS and 1,914 Gotham test rows exactly match a training predictor vector. The declared primary policy retains these because identical measured predictors may occur in different recorded groups. We assess their influence separately without changing the primary partition. All four GeNIS labels have test support. Gotham has 17 training labels but only 16 supported test labels: CoAP Amplification occupies one group and remains training-only. No test recall or generalization claim is made for it.

\section{Models, explanations and inference}
\subsection{Predictive and diagnostic design}
RF uses 120 trees, maximum depth 18, minimum leaf size 2 and balanced-subsample class weights. XGB uses 160 estimators, maximum depth 7, learning rate 0.08, row/column subsampling 0.85 and class-balancing training sample weights. The same settings are retained across datasets/tasks. Five fitting seeds (42, 52, 62, 72, 82) produce 40 predictive fits. Reported macro-F1 averages only labels with positive test support, with a fixed supported-label set within each task; full class-vocabulary scores remain in the artifacts. A majority classifier and depth-5 tree provide simple baselines on the same holdout. Fitting seeds reuse a single split and do not estimate split uncertainty.

For each of three model seeds (42, 52, 62), both explainers process the same 100 selected records in each dataset/task/model context: 24 paired contexts in total. Selection stratifies class/error diagnostics rather than sampling natural traffic prevalence. The predicted class, including a wrong prediction, is the explanation target. TreeExplainer uses model-based defaults without an explicit background matrix; additivity checking is disabled. LIME uses discretized continuous predictors, 350 perturbations per explanation and a training-only background of at most 5,000 rows stratified by model prediction. These choices are fixed computation budgets, not proof of equal approximation error. A small separate LIME-budget audit is descriptive rather than a convergence guarantee.

Absolute attribution magnitude ranks features for removal. TreeSHAP may explain XGB margin units while LIME explains a probability surrogate; we therefore compare rankings through the same fitted target-class probability, not raw attribution magnitudes. Signed agreement, local surrogate fit, and fixed-model deletion fidelity remain different constructs.

\subsection{Primary endpoint and controls}
Let $f_c(x)$ be the probability of the original predicted class $c$, $r$ an explainer's absolute-magnitude ranking and $M_{k,r}(x;b)$ replace its first $k$ predictors using training numerical medians/categorical modes $b$. The per-record endpoint is
\begin{equation}
\begin{aligned}
D(x,r)&=\frac{1}{|K|}\sum_{k\in K}\left[f_c(x)-f_c(M_{k,r}(x;b))\right],\\
K&=\{1,3,5,10\}.
\end{aligned}
\label{eq:deletion}
\end{equation}
Larger positive drops mean that removing highly ranked predictors more strongly reduces the fitted model's support for that class under this intervention. Negative drops are retained. One seeded random ranking per record and bottom-ranked removal use the same mask/budgets. Random rankings are matched between explainers within context. The random comparison tests ranking utility relative to a weak reference; it is not a no-attack or causal control.

At each budget, records within an explained connection are averaged first; budgets are then averaged into one endpoint per group. Thus every explained group receives equal weight regardless of packet/window count. The paired group difference is $\Delta_g=D_g(\mathrm{TreeSHAP})-D_g(\mathrm{LIME})$. There are 57--95 explained groups per primary context, so 100 records must not be treated as 100 independent connections.

Percentile 95\% intervals use 2,000 paired group bootstrap resamples \cite{efron}. One-sided Wilcoxon signed-rank tests \cite{wilcoxon} assess the declared alternatives TreeSHAP $>$ LIME and top $>$ random. Holm correction \cite{holm} covers all 24 explainer comparisons and, separately, all 48 random-control comparisons. Intervals are per-context, not simultaneous. Signed-rank interpretation relies on the paired group-difference distribution; the post-hoc sign test below checks direction frequency without assuming symmetric magnitudes. Groups may still share campaigns; neither grouping nor correction removes every dependence source. Model seeds are reported separately rather than pooled as independent datasets.

\section{Results}
\subsection{Prediction quality and coverage failures}
Table~\ref{tab:prediction} reports five-seed supported-label macro-F1 and a shallow-tree reference. GeNIS performance is almost perfect, but the depth-5 tree already reaches 0.9906 multiclass F1. A complex model is therefore not automatically necessary on this testbed; an interpretable-model baseline matters \cite{rudin}. Gotham binary scores also approach one, while multiclass scores are substantially lower. Small standard deviations quantify fitting randomness on this partition, not variation over sites or capture periods.
''' + pred_table + r'''
The aggregate Gotham result hides important failures. Both RF and XGB have \textbf{zero recall for Mirai C\&C Communication in all five seeds}, despite 358 held-out records. Seed-42 recall for generic C\&C Communication is 0.817 (RF) and 0.439 (XGB), and TCP Scan recall is 0.773 and 0.850. Merlin ICMP Flooding has perfect recall on only three test records; this is weak coverage evidence. CoAP Amplification has no test records. These limitations prevent claims of complete attack-type detection.

The Gotham multiclass training majority is training-only CoAP Amplification, so that baseline scores zero on held-out supported labels. This is a support/prevalence mismatch and should not be used as an unqualified operational improvement claim. The full per-class outputs preserve unsupported labels and seed-specific errors.

\subsection{Primary paired deletion comparison}
TreeSHAP-minus-LIME group means are positive in all 24 primary contexts (0.0570--0.3058), with positive pointwise intervals and Holm-adjusted directional $p<0.05$. Requiring both a positive interval lower bound and corrected $p<0.05$ against random gives 24/24 TreeSHAP and 20/24 LIME contexts. Four Gotham binary LIME intervals cross zero. No primary mean reverses after omitting one explained group. Exact-pattern exclusion removes 379 GeNIS and 1,914 Gotham rows; all paired means remain positive, while Gotham multiclass macro-F1 decreases by about 0.01. These latter checks are post hoc and do not supply independent captures.

\subsection{Replacement and LIME sensitivity}
For both saved rankings on 100 matched records in each of eight seed-42 contexts, we compare median/mode replacement with joint draws from a fixed pool of up to 5,000 training rows. Empirical replacement uses the same 32 uniformly sampled donors for both rankings at every budget per record. Nearest-donor replacement selects 32 rows by retained-feature distance: capped training-scale numeric differences and categorical mismatch, without labels or predictions. We copy removed features jointly from each donor and average target probabilities. Donor hybrids need not be physically valid traffic.

Figure~\ref{fig:mask} shows that GeNIS mean gaps shrink to @MASK_RANGE@ with nearest donors, and @MASK_CROSS@/4 pointwise mean intervals include zero. All eight nearest-donor means are positive across the two datasets. Across a separate 24-test Holm family, median/mode and joint donors each have 8/8 significant positive signs; nearest donors have @MASK_SIGN@/8. These exact two-sided tests concern non-tied direction frequency; bootstrap intervals concern mean differences. The two findings are distinct.
\begin{figure}[t]\centering
\includegraphics[width=\columnwidth]{figures/mask_sensitivity.pdf}
\caption{Seed-42 paired mean deletion differences by replacement rule and pointwise 95\% connection-bootstrap intervals. Both explainers reuse the same diagnostic records.}
\label{fig:mask}
\end{figure}

Fresh default-neighborhood LIME fits at 350 and 3,500 draws share a fixed training background and per-record seeds. This schedule differs from the primary warm-up. With median/mode deletion, saved TreeSHAP still exceeds LIME-3500 in @BUDGET_SIGN@/8 corrected sign tests (separate family of 16 two-sided contrasts). Yet mean absolute surrogate error at the explained input increases in @BUDGET_ERR@/8 contexts, with 3,500-draw context means @BUDGET_RANGE@. A larger budget alone does not fix the local fit. @KERNEL_RESULT@

\subsection{Held-out source files}
We hold out each of eight GeNIS scenario CSVs and eight Gotham bundles of one attack-bearing source plus benign-only sources. Stable filename-hash order and round-robin assignment fix the latter bundles before fitting, covering all 65 represented files. Purging every training row whose group appears in test gives zero shared source files and groups within each fold. We restore candidates removed by the primary constant filter from verified raw row identities, then refit constant filtering and preprocessing on fold training only. RF and XGB reuse the primary hyperparameters and seed 42 for 64 fits; both explainers evaluate 50 matched records per fit at the original median/mode mask and 350 LIME draws.

Table~\ref{tab:transfer} reports macro-F1 over all labels with test support, including labels absent from training; a separate seen-label score restricts records and labels. GeNIS scenario 6 XGB misses @SOURCE_FNR@\% of attacks in binary testing and all @SOURCE_BRUTE@ brute-force records in multiclass testing despite training support. Gotham's combined-cycle-1 bundle has @SOURCE_UNSEEN@ test rows of CoAP Amplification or UDP Scan, both absent from its multiclass training set. The paired mean deletion difference favors TreeSHAP in @SOURCE_POS@/64 contexts and LIME in @SOURCE_NEG@/64. Fold results are descriptive: reused groups, overlapping training data and shared testbed mechanisms preclude pooling for inference.
''' + transfer_table + r'''

\subsection{Uncapped scoring and independent capture}
The same 64 saved detectors score all eight GeNIS and 65 assigned Gotham source files without test caps. We exclude Unknown labels and any additional test rows matching fold-training connection keys. @UNCAPPED@ GeNIS scenario 6 XGB misses 10,003 of 11,995 attacks. The expanded test changes class mix and coverage, with no additional training or independent capture.

For external transfer, we fit binary RF and XGB only on the original GeNIS training partition. The official OCPP charging-network capture \cite{ocpp} contributes both Combined partitions as external test only, totaling 4,415 provider-balanced flows. We use protocol and unordered TCP/UDP ports, with a second fixed set adding duration (converted to seconds) and total packet count. No target tuning is used. Table~\ref{tab:external} shows that protocol/port models catch almost all attack-labeled flows but flag over a third of benign flows. Adding duration and counts improves source-test F1 yet worsens external F1. Flow exporters and segmentation differ. This evaluates reduced-feature binary detectors, not external explanation fidelity.
''' + external_table + r'''
\section{Validity, reproducibility and next evaluation}
\textit{Construct validity:} synthetic replacement can expose model behavior on implausible inputs \cite{slack}. Nearest retained-feature donors are an approximate conditioning sensitivity, not a validated traffic generator. Kernel weighting, correlated predictors, output domains and LIME's discretization limit the comparison to the tested settings. Query fit, in-neighborhood fit and deletion assess different behavior.

\textit{Internal and external validity:} source segregation, group purging, training size and label mix change jointly. The comparison does not identify their individual effects. Class caps and diagnostic selection narrow the populations. Temporal and spatial bias matter in security evaluation \cite{tesseract}; the two original splits reuse the same testbeds. The separate OCPP test does not establish open-world or deployment performance.

\textit{Reproducibility:} pinned environment, acquisition hashes, preparation snapshots, assignments, and per-context artifacts support replay of numerical summaries. No identifying repository link appears in this draft. An anonymous supplement is available subject to venue policy.

\textit{Implications for detector review:} scenario 6 shows why a low false-alarm rate is not a release criterion by itself. Among @CASE_NORMAL@ benign and @CASE_ATTACK@ attack records, RF, XGB and the shallow tree each produce zero false alarms but miss @CASE_RF@, @CASE_XGB@ and @CASE_TREE@ attacks, respectively. Before using explanations in alert triage, check attack recall by held-out source with denominators, report original-query surrogate error separately from deletion, and show whether the ranking comparison persists across replacement rules. These are evaluation recommendations; their impact on analyst decisions was not measured.

\section{Conclusion}
Median/mode masking favors TreeSHAP throughout the primary study, but retained-feature donor replacement makes the GeNIS effects much smaller. Larger LIME budgets alone do not improve surrogate fit. Source separation exposes failures for attack types seen in training, despite the original near-ceiling detection scores. A traceable evaluation of explanation rankings must report both the intervention and the scope of the held-out traffic.

\section*{AI assistance disclosure}
OpenAI Codex assisted with literature discovery, source-acquisition tooling, data auditing, experiment orchestration and manuscript drafting/revision. Authors must verify the scientific content, citations, results and venue-policy compliance, and accept responsibility for the final submission. No automated text-origin or similarity score is asserted.
'''
    case = transfer.query("dataset == 'GeNIS2025' and fold == 6 and task == 'binary' and model == 'xgboost'").iloc[0]
    attacks, normal, misses, _ = scenario_six_misses()
    replacements = {
        "UNCAPPED": large_test_finding(coverage, uncapped),
        "CASE_NORMAL": f"{normal:,}", "CASE_ATTACK": f"{attacks:,}", "CASE_RF": f"{misses['random_forest']:,}",
        "CASE_XGB": f"{misses['xgboost']:,}", "CASE_TREE": f"{misses['depth5_tree']:,}",
        "MASK_RANGE": f"{mask_summary['genis_nearest_min']:.4f}--{mask_summary['genis_nearest_max']:.4f}",
        "MASK_CROSS": mask_summary["genis_crossing_intervals"], "MASK_SIGN": mask_summary["nearest_positive_sign_tests"],
        "BUDGET_SIGN": budget_summary["shap_positive_sign_tests"], "BUDGET_ERR": budget_summary["error_increases"],
        "BUDGET_RANGE": f"{budget_summary['default_high_budget_error_min']:.3f}--{budget_summary['default_high_budget_error_max']:.3f}",
        "KERNEL_RESULT": kernel_paragraph(),
        "SOURCE_FNR": f"{100*case.false_negative_rate:.1f}", "SOURCE_BRUTE": "3,853",
        "SOURCE_UNSEEN": f"{transfer_counts['unseen_multiclass_rows']:,}",
        "SOURCE_POS": transfer_counts["positive_gaps"], "SOURCE_NEG": transfer_counts["negative_gaps"],
    }
    for key, value in replacements.items():
        body = body.replace("@"+key+"@", str(value))
    assert not re.search(r"@[A-Z_]+@", body)
    abstract = esc(extension_abstract())
    bib=bibliography()
    cited=[]
    for block in re.findall(r"\\cite\{([^}]+)\}", body):
        for key in block.split(","):
            if key not in cited:
                cited.append(key)
    assert all(key in bib for key in cited)
    source="\n".join([
        "% Generated by build_conference_paper.py from frozen study outputs and labelled supplements.",
        r"\documentclass[conference,letterpaper]{IEEEtran}",
        r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}",
        r"\usepackage{cite,amsmath,graphicx,array,booktabs,textcomp}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\hypersetup{pdftitle={" + TITLE + r"},pdfauthor={}}",
        r"\begin{document}",
        r"\title{" + TITLE + "}",
        r"\author{\IEEEauthorblockN{Anonymous submission}}", r"\maketitle",
        r"\begin{abstract}", abstract,r"\end{abstract}",
        r"\begin{IEEEkeywords}Intrusion detection, explainable AI, TreeSHAP, LIME, provenance, group holdout.\end{IEEEkeywords}",
        body, r"\begin{thebibliography}{99}",
        *[r"\bibitem{"+key+"} "+bib[key] for key in cited],
        r"\end{thebibliography}",r"\end{document}"])
    (PROJECT / "main.tex").write_text(source,encoding="utf-8")
    inputs=[Path(__file__), ROOT/"paper/ieee/main.tex",
            primary/"run_manifest.json",primary/"predictive_summary.csv",primary/"predictive_baselines.csv",
            primary/"paired_comparisons.csv",patterns/"manifest.json",patterns/"predictive.csv",
            patterns/"explanatory.csv",ROOT/"outputs/explanation_robustness/manifest.json",
            *sorted((ROOT/"outputs/extended_validation_20261108").glob("*/manifest.json")),
            *[ROOT/"outputs"/d/f for d, f in (("masking_extension_20261108","paired_comparisons.csv"), ("lime_budget_20261108","contrasts.csv"), ("lime_kernel_20261108","manifest.json"), ("source_holdout_20261108","predictive_metrics.csv"), ("source_holdout_20261108","explanation_comparison.csv"), ("source_holdout_20261108","verification.json"))]]
    audit={"date":"2026-11-08","purpose":"Separate anonymous conference-length review draft",
           "target":"Provisional IEEE MIAC 2027, Track 5; not submitted",
           "anonymity":"No author, affiliation, identifying repository URL or PDF author metadata",
           "references":len(cited),"primary_unchanged":True,
           "inputs_sha256":{str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    (PROJECT/"build_manifest.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    return PROJECT/"main.tex"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only",action="store_true")
    args=parser.parse_args()
    source=export()
    if args.source_only:
        print(source)
        return
    compiler=shutil.which("pdflatex")
    if not compiler:
        raise SystemExit("pdflatex is required; editable source has been saved")
    for _ in range(2):
        run=subprocess.run([compiler,"-interaction=nonstopmode","-halt-on-error","-no-shell-escape","main.tex"],
                           cwd=PROJECT,capture_output=True,text=True,errors="replace")
        if run.returncode:
            raise SystemExit(run.stdout[-7000:]+run.stderr[-1000:])
    from pypdf import PdfReader
    pages=len(PdfReader(source.with_suffix(".pdf")).pages)
    if pages>6:
        raise SystemExit(f"Conference manuscript has {pages} pages; editorial compression is required (limit 6).")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source.with_suffix(".pdf"),OUTPUT)
    print(f"{OUTPUT} ({pages} pages)")


if __name__=="__main__":
    main()
