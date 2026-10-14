"""An IEEE-style research draft backed only by completed official-source runs.

The legacy manuscript is preserved. This document deliberately distinguishes
dataset release dates, capture dates, checksum verification scopes, and the
population actually evaluated. No explainer outcome is hard-coded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, FrameBreak, KeepTogether, NextPageTemplate,
    PageTemplate, Paragraph, Spacer,
)

from .paper import make_table, register_fonts, styles


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "outputs" / "recent2025"
OUTPUT = ROOT / "output" / "pdf" / "xai_ids_recent2025_paper.pdf"
TITLE = "Provenance-Traceable Evaluation of TreeSHAP and LIME for Intrusion Detection on Two 2025 Benchmarks"
DATASETS = ("GeNIS2025", "Gotham2025")
MODELS = {"random_forest": "RF", "xgboost": "XGB"}
TASKS = {"binary": "Binary", "multiclass": "Multi"}


def fmt(value, digits=3):
    return f"{float(value):.{digits}f}" if pd.notna(value) else "-"


def esc(value):
    return escape(str(value))


def short_dataset(value):
    return str(value).removesuffix("2025")


def load_results(result_dir: Path):
    manifest = json.loads((result_dir / "run_manifest.json").read_text(encoding="utf-8"))
    missing = set(DATASETS) - set(manifest["sources"])
    if missing:
        raise ValueError(f"Both official-source datasets must be prepared: {sorted(missing)}")
    tables = {}
    expected = {"predictive_metrics": 40, "paired_comparisons": 24,
                "fidelity_control_tests": 48, "explanation_summary": 48,
                "feature_ablation": 32}
    for name in (*expected, "per_class_metrics", "predictive_baselines"):
        tables[name] = pd.read_csv(result_dir / f"{name}.csv")
        if name in expected and len(tables[name]) != expected[name]:
            raise ValueError(f"Incomplete {name}: {len(tables[name])}, expected {expected[name]}")
        if set(tables[name].dataset) != set(DATASETS):
            raise ValueError(f"Incorrect dataset coverage in {name}")
    for name in ("predictive_metrics", "predictive_baselines"):
        if "macro_f1_supported_classes" not in tables[name]:
            raise ValueError(f"Fixed positive-support macro-F1 is missing: {name}")
    if not tables["explanation_summary"].n_explanations.eq(100).all():
        raise ValueError("The paper protocol requires 100 explanations per context")
    if manifest["config"]["evaluation"]["lime_samples"] != 350:
        raise ValueError("The paper protocol requires the declared 350-sample LIME budget")
    contexts = [(d, t, m, s) for d in DATASETS for t in TASKS for m in MODELS
                for s in manifest["config"]["predictive_seeds"]]
    for d, t, m, s in contexts:
        checkpoint = result_dir / "contexts" / f"{d}_{t}_{m}_{s}" / "complete.json"
        if not checkpoint.is_file():
            raise ValueError(f"Experiment is still running: {checkpoint.parent.name}")
    for name in ("paired_comparisons", "fidelity_control_tests"):
        if "holm_adjusted_p_all_contexts" not in tables[name]:
            raise ValueError(f"Full-family Holm correction missing: {name}")
        if tables[name].wilcoxon_one_sided_p.isna().any():
            raise ValueError(f"Missing inferential result: {name}")
    for dataset, source in manifest["sources"].items():
        if source["split_audit"]["overlapping_groups"] != 0:
            raise ValueError(f"Connection-group leakage: {dataset}")
        if any(str(label).lower() == "unknown" for label in source["sampled_label_counts"]):
            raise ValueError(f"Unsupervised Unknown label entered the supervised cohort: {dataset}")
        if dataset == "Gotham2025":
            unknown = int(source["source_label_counts"].get("Unknown", 0))
            if source.get("supervised_excluded_label_counts", {}).get("Unknown") != unknown:
                raise ValueError("Gotham Unknown exclusion is not documented against raw counts")
    return manifest, tables


def make_document(path: Path, abstract: str):
    fonts, s = register_fonts(), styles()
    page_w, page_h = letter
    margin, gutter = 0.55 * inch, 0.22 * inch
    usable = page_w - 2 * margin
    col_w = (usable - gutter) / 2
    # Measure the full-width front matter before defining body frames. This
    # prevents a longer data-driven abstract spilling into the first column.
    front = [Paragraph(TITLE, s["title"]),
             Paragraph("Anonymous research draft<br/>14 October 2026", s["author"]),
             Paragraph(abstract, s["abstract"]),
             Paragraph("<b>Index Terms</b>-Intrusion detection, explainable AI, TreeSHAP, LIME, provenance, group holdout.", s["abstract"])]
    height = sum(item.wrap(usable, page_h)[1] + item.getSpaceBefore() + item.getSpaceAfter()
                 for item in front)
    front_top = page_h - 0.50 * inch
    front_bottom = front_top - height - 3
    body_bottom = 0.52 * inch
    first_body_top = front_bottom - 0.13 * inch
    if first_body_top - body_bottom < 3 * inch:
        raise ValueError("Front matter is too long for the first-page body")

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont(fonts["regular"], 6.3)
        canvas.drawString(margin, 0.30 * inch, "Research draft | official-source 2025 benchmarks | venue not selected")
        canvas.drawRightString(page_w - margin, 0.30 * inch, str(document.page))
        canvas.restoreState()

    def columns(top, prefix):
        return [Frame(margin, body_bottom, col_w, top - body_bottom,
                      id=f"{prefix}_left", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0),
                Frame(margin + col_w + gutter, body_bottom, col_w, top - body_bottom,
                      id=f"{prefix}_right", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0)]

    first_frames = [Frame(margin, front_bottom, usable, height + 3,
                          id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                    *columns(first_body_top, "first")]
    document = BaseDocTemplate(str(path), pagesize=letter, title=TITLE,
                              author="Anonymous research draft", creator="Reproducible XAI-IDS research artifact",
                              subject="Official-source 2025 dataset provenance and group-aware explanation evaluation",
                              keywords="intrusion detection, TreeSHAP, LIME, GeNIS, Gotham, dataset provenance")
    document.addPageTemplates([
        PageTemplate(id="First", frames=first_frames, onPage=footer),
        PageTemplate(id="Later", frames=columns(page_h - 0.54 * inch, "later"), onPage=footer),
    ])
    return document, col_w - 4, front


def paired_plot(table: pd.DataFrame, width: float):
    """All model-seed confidence intervals without treating seeds as replicates."""
    fonts = register_fonts()
    data = table.sort_values(["task", "model", "model_seed"]).reset_index(drop=True)
    height = 215
    drawing = Drawing(width, height)
    drawing.initialFontName = fonts["regular"]
    left, right, top, bottom = 90, width - 8, height - 14, 24
    xmin = min(-0.015, float(data.ci_low.min()) - 0.02)
    xmax = max(0.04, float(data.ci_high.max()) + 0.02)
    span = xmax - xmin

    def x(value):
        return left + (float(value) - xmin) / span * (right - left)

    for tick in np.linspace(xmin, xmax, 5):
        drawing.add(Line(x(tick), bottom, x(tick), top, strokeColor=colors.HexColor("#e1e1e1"), strokeWidth=0.4))
        drawing.add(String(x(tick), 13, f"{tick:.2f}", fontName=fonts["regular"], fontSize=6.3, textAnchor="middle"))
    drawing.add(Line(x(0), bottom, x(0), top, strokeColor=colors.black, strokeWidth=0.8))
    row_h = (top - bottom) / len(data)
    for index, row in data.iterrows():
        y = top - (index + 0.5) * row_h
        label = f"{TASKS[row.task]} {MODELS[row.model]} s{int(row.model_seed)}"
        drawing.add(String(left - 5, y - 2.1, label, fontName=fonts["regular"], fontSize=6.5, textAnchor="end"))
        ink = colors.HexColor("#123d62") if row.holm_adjusted_p_all_contexts < .05 else colors.HexColor("#747474")
        drawing.add(Line(x(row.ci_low), y, x(row.ci_high), y, strokeColor=ink, strokeWidth=1.1))
        drawing.add(Rect(x(row.mean_difference_shap_minus_lime) - 1.8, y - 1.8, 3.6, 3.6, fillColor=ink, strokeColor=ink))
    drawing.add(String((left + right) / 2, 1, "TreeSHAP minus LIME probability-drop difference", fontName=fonts["regular"], fontSize=6.4, textAnchor="middle"))
    return drawing


def build_story(manifest, tables, col_w, front, result_dir):
    s = styles()
    story = [*front, NextPageTemplate("Later"), FrameBreak()]

    def para(text):
        story.append(Paragraph(text, s["body"]))

    def sec(number, title):
        story.append(Paragraph(f"{number}. {title.upper()}", s["section"]))

    def sub(letter, title):
        story.append(Paragraph(f"<i>{letter}. {title}</i>", s["subsection"]))

    def table(caption, rows, fractions, size=6.5):
        story.append(KeepTogether([Paragraph(caption, s["table_caption"]),
                                  make_table(rows, [col_w * f for f in fractions], font_size=size),
                                  Spacer(1, 4)]))

    predictive, pairs = tables["predictive_metrics"], tables["paired_comparisons"]
    controls, xai = tables["fidelity_control_tests"], tables["explanation_summary"]
    sources = manifest["sources"]
    significant = (pairs.holm_adjusted_p_all_contexts < .05) & (pairs.mean_difference_shap_minus_lime > 0)
    positive = int((pairs.mean_difference_shap_minus_lime > 0).sum())
    total = len(pairs)
    sec("I", "Introduction")
    para("An explainable intrusion detector must be assessed on a traceable input pipeline and on an evaluation design that respects traffic dependence. A recent release date alone does not resolve leakage, label coverage, or external validity. This study replaces unauditable local benchmark conversions as the primary evidence with two openly accessible author-published 2025 datasets: GeNIS [1], [2] and Gotham [3], [4]. The original CIC-IDS2017 and UNSW-NB15 experiments are retained as historical project artifacts because their local parquet transformation histories could not be recovered.")
    para("We compare Random Forest (RF) and XGBoost (XGB) under binary and multiclass targets, and compare TreeSHAP with LIME on the same selected test records for each fitted model. The contribution is an auditable experimental artifact: source-member verification, deterministic class caps, a frozen connection-group split, five model seeds, three explanation-model seeds, deletion controls, and explicit statement of checksum and class-support limits. We do not propose a new explanation algorithm or establish analyst benefit.")
    para("The research questions are whether predictive performance persists across training seeds; whether a feature ranking produces more target-probability reduction than a random ranking; how the two explainers compare on a paired group-level deletion endpoint; and how explanation timing, neighborhood similarity, and reduced-feature models change under the chosen protocol.")

    sec("II", "Explanation methods and evaluation scope")
    para("SHAP expresses predictions through additive feature contributions under a specified value function [5]. Tree-based computation provides an efficient implementation for the fitted ensembles [6]. LIME fits an interpretable surrogate near one input using perturbed samples [7]. We explain the model's predicted class, including wrong predictions. Absolute attribution magnitude determines deletion order. Values from the two methods need not have the same output scale; deletion recomputes the fitted model's target-class probability for both.")
    para("A probability-drop test measures the model's response to synthetic masking. It does not show that the selected feature is a causal attack indicator, that the masked packet is physically valid, or that an analyst will make a better decision. We therefore call the endpoint deletion fidelity under the stated baseline, report random and bottom-ranked controls, and separate this endpoint from classification quality and human usefulness.")

    sec("III", "Source provenance and data preparation")
    sub("A", "Official releases and verification scope")
    para("GeNIS was released on 24 February 2025 at author Zenodo record 14919237. It supplies simulated enterprise attack scenarios exported at multiple flow intervals [1], [2]. We use all eight scenario CSV members at the 5-second interval. The downloaded 3-scenarios.zip archive and 0-info.zip match their provider MD5 values; SHA-256 is recorded for those archives and each consumed CSV member. The provider's exporter output is the starting input; raw packet recapture and flow regeneration are outside this study.")
    para("Gotham was released on 5 February 2025 at author Zenodo record 14502760. Its packet-level CSVs preserve captures from 78 emulated IoT devices [3], [4]. All 78 author CSV members were acquired directly from the official ZIP through HTTP byte ranges. Each extracted member's CRC32 was checked against the ZIP directory, and a SHA-256 was recorded. The provider MD5 for the complete 23.8-GB ZIP was recorded but <b>was not recomputed or verified</b>: the complete archive was not downloaded. Member integrity checking is narrower than full-archive checksum verification.")
    dates = sources["Gotham2025"].get("source_date_range_utc", [None, None])
    if all(dates):
        para(f"The Gotham CSV timestamps parsed during preparation span {esc(dates[0])} through {esc(dates[1])} (UTC). GeNIS capture timestamps are not reliably established by the consumed CSV representation. The names GeNIS2025 and Gotham2025 denote release-year identifiers; they do not imply 2025 capture dates. The acquisition manifest records source URLs, UTC download times, metadata snapshots, checksum scope, transformation code hashes, and prepared parquet hashes.")
    else:
        para("The dataset identifiers denote 2025 release years. GeNIS capture dates are not reliably established by the consumed CSV representation. We do not equate release year with capture year. The acquisition manifest records source URLs, UTC download times, metadata snapshots, checksum scope, transformation code hashes, and prepared parquet hashes.")
    sub("B", "Deterministic sampling and grouped holdout")
    para("Every selected source member is scanned. Independent random priorities with seed 42 retain at most 10,000 records per eligible original source label globally, rather than per file. Consequently the study uses a bounded class-capped cohort, not the full natural traffic distribution. Source filename and row offset are retained as audit metadata and excluded from the model. Known attack labels are merged only for the binary target; the multiclass target retains eligible provider labels.")
    raw_gotham = sources["Gotham2025"]["source_label_counts"]
    unknown_count = sum(int(n) for label, n in raw_gotham.items() if str(label).lower() == "unknown")
    raw_count = sum(int(n) for n in raw_gotham.values())
    para(f"Gotham's provider label Unknown occurs in {unknown_count:,} of {raw_count:,} scanned raw packets. It is excluded from both supervised tasks before the class cap and group split because it supplies neither a known benign nor a known attack target. Raw counts remain in the provenance manifest. These experiments do not classify Unknown as an attack and do not evaluate unknown-attack recognition.")
    para("GeNIS groups use the provider FlowID globally across scenarios, which prevents repeated flow identifiers from crossing the split. Gotham groups use a canonical bidirectional IP/transport-port tuple plus IP protocol globally across device files, so endpoint-equivalent packets share a group. A GroupShuffleSplit with seed 42 requests a 20% test-group fraction. The first candidate with all eligible labels represented in both partitions is frozen before fitting. A label confined to one group stays in training and is explicitly omitted from test coverage. No row-random fallback is used.")
    rows = [["Dataset", "Train / test", "Groups train / test", "p", "Classes train / test"]]
    for dataset in DATASETS:
        source, audit = sources[dataset], sources[dataset]["split_audit"]
        rows.append([short_dataset(dataset), f"{audit['train_rows']:,} / {audit['test_rows']:,}",
                     f"{audit['training_groups']:,} / {audit['testing_groups']:,}", len(source["features"]),
                     f"{len(audit['training_labels'])} / {len(audit['test_labels'])}"])
    table("TABLE I. COHORT AND MULTICLASS COVERAGE; p = INPUT COUNT", rows, [.16, .26, .28, .10, .20], 6.2)
    for dataset in DATASETS:
        source = sources[dataset]
        audit = source["split_audit"]
        absent = sorted(set(audit["training_labels"]) - set(audit["test_labels"]))
        para(f"{short_dataset(dataset)} has zero overlapping train/test groups. {source['test_feature_vectors_also_present_in_training']:,} test feature vectors also occur in training; these are retained under the declared policy because equal predictor patterns can arise in different recorded groups. " +
             (f"Training-only labels are {', '.join(esc(v) for v in absent)}; no test recall or generalization claim is made for them." if absent else "Every sampled multiclass label has test support."))
    sub("C", "Predictors and preprocessing")
    para("Labels, IP/MAC addresses, timestamps, identifiers, payload fields, and selected exporter-specific metadata are excluded before modeling. The exact dataset-specific exclusion list is saved in the provenance manifest. Constants are removed using training rows alone. Numeric infinities become missing values and are imputed with training medians. Categorical features are mapped with training-only category dictionaries; unseen test values map to -1. Median/mode training values form the masking baseline. No scaling or imputation is fit on the test set. Retained ports, protocol, flags, sizes, and timing features may still encode testbed-specific shortcuts.")

    sec("IV", "Experimental protocol")
    sub("A", "Prediction and class support")
    config = manifest["config"]
    rf, xgb = config["models"]["random_forest"], config["models"]["xgboost"]
    para(f"Predictive seeds are {', '.join(map(str, config['predictive_seeds']))} on the same frozen cohort and split. RF uses {rf['n_estimators']} trees, maximum depth {rf['max_depth']}, minimum leaf size {rf['min_samples_leaf']}, and balanced-subset class weights. XGB uses {xgb['n_estimators']} trees, maximum depth {xgb['max_depth']}, learning rate {xgb['learning_rate']}, and row/column fractions {xgb['subsample']}/{xgb['colsample_bytree']}; training sample weights balance classes. Fixed hyperparameters are not selected on this test set. Majority-class and depth-5 single-tree baselines use the same split.")
    para("Accuracy, balanced accuracy, macro-F1, weighted-F1, and per-class support are saved. Binary false-positive rate uses Normal as the negative class; false-negative rate and average precision use Attack as positive. Headline macro-F1 averages a fixed label set with positive test support, identical across model seeds on the frozen split. A training-only class is excluded from that average, but predictions into it still cause false negatives for the supported true class and reduce its recall. Per-class precision is also computed from all predictions rather than discarding unsupported predictions. This scorer does not imply coverage of every provider label. The default true/predicted-label union macro-F1 and training-vocabulary macro-F1 are retained separately for compatibility and audit. Mean and sample standard deviation over five seeds quantify training-seed variation on one split, not uncertainty over networks or captures.")
    sub("B", "Matched explanation records and masking")
    para("For each model at seeds 42, 52, and 62, the two explainers process the same 100 selected test records. Selection is stratified by true class and prioritizes available misclassification types. Thus the explanation cohort is intentionally diagnostic and is not a prevalence-representative sample; selected records can differ between fitted models. LIME uses up to 5,000 training background rows stratified by model prediction, continuous discretization, all predictors, and 350 perturbations per call. TreeExplainer uses its model-based defaults without an explicit background matrix; additivity checking is disabled. XGB attributions can be in margin units, while RF output differs, so comparisons rely on ranking rather than raw attribution magnitudes.")
    para("For record x and predicted class c, rank predictors by absolute contribution. Replace the top k entries by training median/mode values for k in {1, 3, 5, 10}. Recompute p(c|x) after masking. The endpoint is the mean probability drop across these four budgets; negative values are permitted. One seeded random ranking and a reversed bottom ranking are evaluated with the same masking budgets. Random-control permutations are matched between the explainers for a fitted context.")
    story.append(Paragraph("D(x) = (1/4) &Sigma;<sub>k &isin; {1,3,5,10}</sub> [p(c|x) - p(c|mask<sub>k</sub>(x))]", s["equation"]))
    sub("C", "Group-level statistical analysis")
    para("Repeated packets or windows within one explained connection are averaged first at each masking budget. Budgets are then averaged to obtain one endpoint per explained group, giving groups equal weight. TreeSHAP-minus-LIME differences and top-minus-random control lifts are paired within group. Percentile 95% confidence intervals use 2,000 paired group bootstrap resamples. One-sided Wilcoxon tests use the alternatives TreeSHAP &gt; LIME and top &gt; random; these are directional tests and do not establish a significant LIME advantage when negative. Fewer than five groups are marked insufficient and assigned p = 1. Holm adjustment is computed across all 24 explainer contexts and separately all 48 control contexts. Seeds reuse a fixed test partition and are not independent datasets; we do not pool them into one pseudo-replicated test.")
    sub("D", "Secondary endpoints and audits")
    para("Explainer timings measure a warmed individual explanation call, excluding constructor setup, packet extraction, preprocessing, and rendering. Other preparation or experiment jobs were active during parts of the project run. Median and upper percentiles are therefore descriptive project-run measurements on this machine, not an isolated service benchmark; CPU contention can affect timing comparisons. Neighborhood similarity compares each selected record to its nearest selected record with the same predicted class after scaling the selected matrix: cosine similarity of signed attributions and top-5 Jaccard overlap. This diagnostic is descriptive and is not a train-fitted deployment transformation. LIME repeatability uses six selected records and five repeat seeds, with training-background sampling varying as well. Feature ablation refits seed-42 models with 5, 10, 20, and all predictors ranked by training-fitted model importance; it is not SHAP-guided selection.")

    sec("V", "Results")
    sub("A", "Predictive performance")
    rows = [["Dataset", "Task / model", "Supported F1 mean (SD)", "Balanced acc.", "Weighted F1"]]
    grouped = predictive.groupby(["dataset", "task", "model"])
    for (dataset, task, model), group in grouped:
        rows.append([short_dataset(dataset), f"{TASKS[task]} {MODELS[model]}",
                     f"{fmt(group.macro_f1_supported_classes.mean(),4)} ({fmt(group.macro_f1_supported_classes.std(),4)})",
                     fmt(group.balanced_accuracy.mean(),4), fmt(group.weighted_f1.mean(),4)])
    table("TABLE II. FIVE-SEED RESULTS; MACRO-F1 USES TEST-SUPPORTED LABELS", rows, [.17, .21, .28, .17, .17], 6.3)
    for dataset in DATASETS:
        subset = predictive[predictive.dataset == dataset]
        multi = subset[subset.task == "multiclass"]
        para(f"{short_dataset(dataset)} test-supported-label macro-F1 ranges from {fmt(subset.macro_f1_supported_classes.min(),4)} to {fmt(subset.macro_f1_supported_classes.max(),4)} over the fitted contexts; multiclass weighted-F1 ranges from {fmt(multi.weighted_f1.min(),4)} to {fmt(multi.weighted_f1.max(),4)}. These values describe the known-label class-capped cohort. Strong within-testbed performance can reflect repeated mechanisms or testbed signatures and does not establish current operational detection accuracy.")
        binary = subset[subset.task == "binary"]
        parts = []
        for model, group in binary.groupby("model"):
            parts.append(f"{MODELS[model]}: mean FPR {fmt(group.false_positive_rate.mean(),6)}, "
                         f"FNR {fmt(group.false_negative_rate.mean(),6)}, "
                         f"Attack average precision {fmt(group.pr_auc.mean(),6)}")
        para(f"{short_dataset(dataset)} binary error rates averaged over five seeds are " +
             "; ".join(parts) + ". These denominators use the held-out capped cohort, so they do not predict alert volume under deployment prevalence.")
    baseline = tables["predictive_baselines"]
    rows = [["Dataset", "Task", "Majority F1", "Depth-5 tree F1"]]
    for (dataset, task), group in baseline.groupby(["dataset", "task"]):
        rows.append([short_dataset(dataset), TASKS[task], fmt(group.loc[group.model == "majority", "macro_f1_supported_classes"].iloc[0],4),
                     fmt(group.loc[group.model == "depth5_tree", "macro_f1_supported_classes"].iloc[0],4)])
    table("TABLE III. SINGLE-SEED BASELINE TEST-SUPPORTED-LABEL MACRO-F1", rows, [.22, .20, .29, .29])
    para("Gotham's multiclass training majority is CoAP Amplification, whose single connection group stays entirely in training. The majority baseline therefore predicts a label absent from test and scores zero on supported-class macro-F1. This result reflects the split's class-support mismatch; it does not provide an unqualified claim about gains over a prevalence-matched deployment baseline.")
    class_rows = [["Dataset / class", "Test n", "RF recall", "XGB recall"]]
    per_class = tables["per_class_metrics"]
    per_class = per_class[(per_class.task == "multiclass") & (per_class.seed == 42)]
    for (dataset, label), group in per_class.groupby(["dataset", "class"]):
        n = int(group.support.iloc[0])
        by_model = group.set_index("model")
        class_rows.append([f"{short_dataset(dataset)} / {esc(label)}", f"{n:,}",
                           fmt(by_model.loc["random_forest", "recall"]) if n else "N/A",
                           fmt(by_model.loc["xgboost", "recall"]) if n else "N/A"])
    table("TABLE IV. SEED-42 MULTICLASS RECALL; N/A MEANS NO TEST SUPPORT", class_rows, [.49, .15, .18, .18], 6.1)
    para("Per-class recall and support temper aggregate scores. A zero-support label has no measured recall, even if included in the training class dictionary. The full per-class CSV preserves zero-support rows and seed-specific precision, recall, and F1. The small number of independent groups for some attack types limits interpretation beyond this captured cohort.")
    sub("B", "Paired deletion fidelity")
    para(f"TreeSHAP-minus-LIME mean deletion differences are positive in {positive}/{total} contexts. The pre-specified TreeSHAP-greater directional test is significant after full-family Holm adjustment in {int(significant.sum())}/{total} contexts. The context-specific effect estimates and group-bootstrap intervals are shown in Figs. 1 and 2. A non-significant result should not be read as equivalence, and a positive deletion difference is not evidence of superior analyst decisions.")
    for index, dataset in enumerate(DATASETS, start=1):
        subset = pairs[pairs.dataset == dataset]
        story.append(KeepTogether([paired_plot(subset, col_w), Paragraph(
            f"Fig. {index}. {short_dataset(dataset)} paired connection-group mean differences with 95% bootstrap intervals. Blue denotes Holm-adjusted directional p &lt; 0.05; gray denotes non-significance. Each row is one model seed on the frozen split.", s["caption"])]))
    rows = [["Dataset", "Task / model", "Groups range", "Mean delta range", "Sig. / 3"]]
    for (dataset, task, model), group in pairs.groupby(["dataset", "task", "model"]):
        delta = group.mean_difference_shap_minus_lime
        sig = ((group.holm_adjusted_p_all_contexts < .05) & (delta > 0)).sum()
        rows.append([short_dataset(dataset), f"{TASKS[task]} {MODELS[model]}",
                     f"{int(group.n_pairs.min())}-{int(group.n_pairs.max())}",
                     f"{fmt(delta.min())} to {fmt(delta.max())}", f"{int(sig)} / 3"])
    table("TABLE V. PAIRED DIFFERENCES ACROSS THREE MODEL SEEDS", rows, [.17, .22, .18, .29, .14], 6.2)
    rows = [["Dataset", "Explainer", "Positive lift / n", "CI + Holm / n", "Lift range"]]
    for (dataset, explainer), group in controls.groupby(["dataset", "explainer"]):
        lift = group.mean_lift_top_minus_random
        sig = (group.holm_adjusted_p_all_contexts < .05) & (lift > 0) & (group.ci_low > 0)
        rows.append([short_dataset(dataset), explainer, f"{int((lift>0).sum())}/{len(group)}",
                     f"{int(sig.sum())}/{len(group)}", f"{fmt(lift.min())} to {fmt(lift.max())}"])
    table("TABLE VI. TOP-RANKED MASKING RELATIVE TO RANDOM CONTROL", rows, [.18, .21, .18, .18, .25], 6.2)
    weak_controls = controls[(controls.mean_lift_top_minus_random > 0) &
                             (controls.holm_adjusted_p_all_contexts < .05) & (controls.ci_low <= 0)]
    weak_description = ", ".join(f"{short_dataset(row.dataset)} {TASKS[row.task].lower()} {row.explainer}"
                                 for _, row in weak_controls[["dataset", "task", "explainer"]].drop_duplicates().iterrows())
    weak_sentence = (f"{len(weak_controls)} contexts ({esc(weak_description)}) have positive mean lift and significant directional tests but intervals that cross zero, so they fail the combined criterion. "
                     if len(weak_controls) else "")
    para("The controls ask whether the ranking is informative under the same synthetic intervention. CI + Holm requires a positive lower 95% group-bootstrap bound together with Holm-adjusted directional p &lt; 0.05. Every top-minus-random hypothesis is adjusted in the 48-test family. " +
         weak_sentence + "Bottom-ranked scores remain in the artifacts as a descriptive check. An explainer comparison alone cannot show that either ranking improves over a random ranking.")
    sub("C", "Latency, neighborhood similarity, and feature reduction")
    rows = [["Dataset", "Task / model", "SHAP / LIME ms", "SHAP / LIME cosine"]]
    for (dataset, task, model), group in xai.groupby(["dataset", "task", "model"]):
        means = group.groupby("explainer")[["latency_median_ms", "stability_cosine_mean"]].mean()
        rows.append([short_dataset(dataset), f"{TASKS[task]} {MODELS[model]}",
                     f"{fmt(means.loc['TreeSHAP','latency_median_ms'],2)} / {fmt(means.loc['LIME','latency_median_ms'],2)}",
                     f"{fmt(means.loc['TreeSHAP','stability_cosine_mean'])} / {fmt(means.loc['LIME','stability_cosine_mean'])}"])
    table("TABLE VII. MEAN OF THREE CONTEXT MEDIANS AND COSINE MEANS", rows, [.18, .23, .30, .29], 6.3)
    para("Table VII keeps each dataset/task/model context visible rather than combining correlated rows into one inferential claim. Timing excludes explainer construction and the complete IDS path, and background project-job contention was not controlled; the artifact additionally saves p90, p95, p99, throughput, top-5 overlap, and LIME repeatability. The reciprocal call-time throughput is not production IDS throughput. Neighborhood similarity depends on the chosen comparison set and representation, so it should not be called adversarial robustness.")
    rows = [["Dataset", "Task / model", "5 features", "10 features", "20 features", "All"]]
    for (dataset, task, model), group in tables["feature_ablation"].groupby(["dataset", "task", "model"]):
        maximum = int(group.feature_count.max())
        # The benchmark caps requested subsets at p and retains repeated
        # full-count rows. Display one scalar per actual feature count, and
        # mark an unavailable nominal budget rather than inventing its result.
        by_count = group.drop_duplicates("feature_count").set_index("feature_count")
        values = [fmt(by_count.loc[k, "macro_f1"],4) if k <= maximum and k in by_count.index
                  else "N/A" for k in (5,10,20)]
        values.append(fmt(by_count.loc[maximum, "macro_f1"],4))
        rows.append([short_dataset(dataset), f"{TASKS[task]} {MODELS[model]}",
                     *values])
    table("TABLE VIII. FEATURE ABLATION; LEGACY LABEL-UNION MACRO-F1", rows, [.16, .24, .15, .15, .15, .15], 6.1)
    para("Feature reduction results are exploratory seed-42 refits and use the default true/predicted-label union macro-F1, which can include a predicted training-only class. They therefore use a different label averaging definition from Table II. N/A means the nominal subset exceeds the available predictor count. Requested counts are capped in the raw experiment, so repeated full-count rows are displayed once under All. The ranking is fitted on training data, but comparing multiple subsets on the held-out test set does not constitute independently validated feature selection. Any final subset should be fixed and confirmed on a new holdout. SHAP latency measured in this ablation is a small batched probe and is not directly interchangeable with Table VII's warmed single-record timings.")

    extended = result_dir / "extended"
    complete_extended = all((extended / name).is_file() for name in (
        "calibration_summary.csv", "masking_baseline_ablation.csv", "lime_budget_ablation.csv", "balancing_ablation.csv"))
    sub("D", "Sensitivity and calibration audits")
    if complete_extended:
        calibration = pd.read_csv(extended / "calibration_summary.csv")
        masking = pd.read_csv(extended / "masking_baseline_ablation.csv")
        budgets = pd.read_csv(extended / "lime_budget_ablation.csv")
        balancing = pd.read_csv(extended / "balancing_ablation.csv")
        if set(calibration.dataset) != set(DATASETS) or len(calibration) != 4:
            raise ValueError("Extended audit calibration is incomplete")
        if len(list(extended.glob("*/complete.json"))) != 8:
            raise ValueError("Extended audit is still running")
        para("Additional seed-42 audits evaluate binary calibration on the test cohort, weighted versus unweighted fitting, TreeSHAP masking under five baselines on 12 diagnostic records, and LIME perturbation budgets 100, 350, and 700 on six records with five repeats. These small sensitivity cohorts provide descriptive checks; they are not independent confirmatory studies or a replacement for the paired group-level primary endpoint.")
        rows = [["Dataset / model", "Brier", "10-bin ECE"]]
        for _, row in calibration.sort_values(["dataset","model"]).iterrows():
            rows.append([f"{short_dataset(row.dataset)} {MODELS[row.model]}", fmt(row.brier_score,4), fmt(row.expected_calibration_error,4)])
        table("TABLE IX. BINARY SEED-42 CALIBRATION ON THE CAPPED COHORT", rows, [.48,.26,.26])
        mask_mean = masking.groupby("baseline").deletion_score.mean()
        para("Across the eight contexts, descriptive TreeSHAP mean deletion scores under the masking alternatives are " +
             "; ".join(f"{esc(name.replace('_',' '))}: {fmt(value)}" for name,value in mask_mean.items()) +
             ". This pooling is a sensitivity summary only. Baseline-dependent scores reinforce that the masking intervention is part of the measured construct.")
        budget_mean = budgets.groupby("lime_samples")[["mean_deletion_fidelity","mean_self_stability_cosine","median_latency_ms"]].mean()
        rows = [["LIME samples", "Deletion", "Repeat cosine", "Median ms"]]
        for budget, row in budget_mean.iterrows():
            rows.append([str(budget), fmt(row.mean_deletion_fidelity), fmt(row.mean_self_stability_cosine), fmt(row.median_latency_ms,2)])
        table("TABLE X. DESCRIPTIVE LIME BUDGET AUDIT, CONTEXTS POOLED", rows, [.24,.25,.25,.26])
        paired_weights = balancing.pivot(index=["dataset","task","model"], columns="training_weighting", values="macro_f1_supported_classes")
        differences = paired_weights.class_weighted - paired_weights["none"]
        para(f"Class-weighted minus unweighted test-supported-label macro-F1 varies from {fmt(differences.min(),4)} to {fmt(differences.max(),4)} across seed-42 contexts. Calibration values apply to the known-label capped test cohort; they do not estimate calibration at natural deployment prevalence. The LIME budget audit reuses seeds and records and is presented without a pooled significance claim.")
    else:
        para("Sensitivity and calibration audits are not included because their completed aggregate artifacts were unavailable when this draft was built. The primary conclusion is restricted to the declared median/mode baseline and the 350-perturbation LIME budget. No uncomputed sensitivity result is implied.")

    sec("VI", "Discussion and threats to validity")
    para("The refreshed evidence addresses the missing local conversion history by making the source-to-cohort transformation inspectable and rerunnable. It does not retrospectively recover the legacy parquet provenance. Source snapshots and hashes fix the consumed author files and executed transformations, while the narrower Gotham member-verification scope remains a declared limitation. CRC32 detects transfer or extraction inconsistency; it is not a publisher-signed cryptographic authenticity proof.")
    para("The group split prevents the chosen connection keys from crossing partitions. It is not a device-disjoint, scenario-disjoint, forward-in-time, cross-network, or external-attack evaluation. GeNIS scenarios can share testbed material beyond FlowID, and Gotham endpoint tuples can merge repeated sessions or leave other correlations across different tuples. Equal feature patterns across groups remain in the primary cohort. High performance can therefore coexist with limited external validity.")
    para("The class cap changes prevalence and can underrepresent rare attack diversity. Unknown-labelled packets are outside both supervised tasks. A label confined to one group cannot support an independent test claim; the supported-class macro-F1 is restricted to labels present in test. Five predictive seeds share one preparation seed and one split; they do not explore split uncertainty. Explanation sampling prioritizes error types, and the inferential population is the explained groups represented by this selection rather than every packet in the full dataset. Group means reduce within-key dependence but do not remove all dependence across groups or model seeds.")
    para("The directional TreeSHAP-greater test permits checking that specific hypothesis; a reverse claim requires a separately specified analysis. Bootstrap intervals are per context and are not simultaneous confidence intervals, whereas Holm controls the reported hypothesis families. The default TreeSHAP value function and LIME's discretized local surrogate can respond differently to correlated and categorical predictors. Masking by a mixed median/mode vector can create off-manifold combinations, so a larger deletion drop is a protocol-specific ranking result.")
    para("This work has no participant study, production monitoring, packet-capture throughput benchmark, drift test, or attack intervention study. It cannot establish analyst usefulness, operational alert cost, current attack coverage, or adversarial safety. A stronger next evaluation would freeze the chosen configuration, use a separately captured device/scenario/time holdout, retain natural prevalence for operational calibration, and measure analyst decisions with a pre-specified human study.")

    sec("VII", "Reproducibility and reporting status")
    environment = manifest["environment"]
    packages = environment["packages"]
    para(f"The executed environment uses Python {esc(environment['python'])}, scikit-learn {esc(packages['scikit-learn'])}, XGBoost {esc(packages['xgboost'])}, SHAP {esc(packages['shap'])}, and LIME {esc(packages['lime'])}. The project saves author-record metadata, acquisition and per-member hashes, exclusions, source row counts, class counts, split and overlap audits, prepared parquet hashes, source snapshots, fitted seed-42 models, and per-context checkpoints. The configuration and source hashes in run_manifest.json define this run. Artifact verification checks coverage and internal consistency; it is not independent external replication.")
    para("A clean rerun begins with the official acquisition scripts, then deterministic preparation, the recent-data benchmark, and artifact verification. It requires the author data downloads and the pinned requirements. The benchmark caps are part of the experiment and should not be silently replaced with full-data or per-file caps. No repository release, archival DOI, or externally executed replication is claimed in this draft.")
    para("<b>AI assistance disclosure:</b> OpenAI Codex assisted with source acquisition tooling, data auditing, experiment orchestration, and manuscript drafting. The authors must verify the methods, results, citations, and disclosure against the selected venue's requirements and accept responsibility for the final work. Author identities are withheld in this research draft; no specific IEEE journal or conference has been selected. This layout is IEEE-style and is not a certification of venue-template or submission compliance.")

    sec("VIII", "Conclusion")
    para(f"Two official author releases from 2025 now supply traceable primary inputs for the intrusion-detection explanation benchmark. The frozen group-aware protocol produces 40 predictive fits, 24 paired explainer contexts, and 48 random-control tests. TreeSHAP has a positive mean deletion difference in {positive}/{total} contexts and meets the directional Holm-adjusted criterion in {int(significant.sum())}/{total}. These findings are limited to the sampled cohorts, explanation budgets, masks, and connection-group holdout. Dataset provenance is documented for the new cohorts; legacy conversion provenance remains unresolved and its results remain historical.")

    # The short conclusion starts the final page's left column. Move the
    # references to the right column to balance the final page.
    story.append(FrameBreak())
    story.append(Paragraph("REFERENCES", s["section"]))
    references = [
        '[1] M. Silva, D. Pinto, J. Vitorino, J. Goncalves, E. Maia, and I. Praca, "GeNIS: GECAD Network Intrusion Scenarios," Zenodo, ver. 1.0.0, Feb. 24, 2025, doi: <link href="https://doi.org/10.5281/zenodo.14919237">10.5281/zenodo.14919237</link>.',
        '[2] M. Silva, D. Pinto, J. Vitorino, J. Goncalves, E. Maia, and I. Praca, "GeNIS: A modular dataset for network intrusion detection and classification," <i>Data in Brief</i>, vol. 60, art. no. 111487, Jun. 2025, doi: <link href="https://doi.org/10.1016/j.dib.2025.111487">10.1016/j.dib.2025.111487</link>.',
        '[3] O. Belarbi, T. Spyridopoulos, E. Anthi, O. Rana, P. Carnelli, and A. Khan, "A Device-Level IoT Network Traffic Dataset with Distributed Capture and Non-IID Characteristics," Zenodo, ver. v1, Feb. 5, 2025, doi: <link href="https://doi.org/10.5281/zenodo.14502760">10.5281/zenodo.14502760</link>.',
        '[4] O. Belarbi <i>et al.</i>, "Gotham Dataset 2025: A Reproducible Large-Scale IoT Network Dataset for Intrusion Detection and Security Research," arXiv:2502.03134, 2025, doi: <link href="https://doi.org/10.48550/arXiv.2502.03134">10.48550/arXiv.2502.03134</link>.',
        '[5] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in <i>Advances in Neural Information Processing Systems</i>, vol. 30, 2017. [Online]. Available: <link href="https://arxiv.org/abs/1705.07874">arxiv.org/abs/1705.07874</link>.',
        '[6] S. M. Lundberg <i>et al.</i>, "From local explanations to global understanding with explainable AI for trees," <i>Nature Machine Intelligence</i>, vol. 2, pp. 56-67, 2020, doi: <link href="https://doi.org/10.1038/s42256-019-0138-9">10.1038/s42256-019-0138-9</link>.',
        '[7] M. T. Ribeiro, S. Singh, and C. Guestrin, "Why should I trust you?: Explaining the predictions of any classifier," in <i>Proc. ACM SIGKDD</i>, 2016, pp. 1135-1144, doi: <link href="https://doi.org/10.1145/2939672.2939778">10.1145/2939672.2939778</link>.',
    ]
    for reference in references:
        story.append(Paragraph(reference, s["reference"]))
    return story


def make_abstract(tables):
    pairs = tables["paired_comparisons"]
    positive = int((pairs.mean_difference_shap_minus_lime > 0).sum())
    significant = int(((pairs.holm_adjusted_p_all_contexts < .05) &
                       (pairs.mean_difference_shap_minus_lime > 0)).sum())
    return ("<b>Abstract</b>-We evaluate intrusion-detection classifiers and explanations using traceable inputs from the official GeNIS and Gotham 2025 releases. Author files are deterministically converted into known-label class-capped cohorts with a frozen connection-group holdout and training-only preprocessing. Unknown-labelled packets are excluded from supervised evaluation. GeNIS archives match provider MD5 values; Gotham CSV members are CRC32-checked and SHA-256-recorded, while the complete Gotham ZIP checksum is not verified. Random Forest and XGBoost are fitted for binary and multiclass tasks over five seeds, with headline macro-F1 fixed to test-supported labels. TreeSHAP and LIME explain 100 matched diagnostic test records per fitted context over three model seeds. The primary endpoint averages target-probability deletion across four masking budgets and gives connection groups equal weight. Paired bootstrap intervals and directional Wilcoxon tests use Holm correction over 24 explainer comparisons and 48 random-control comparisons. "
            f"TreeSHAP-minus-LIME mean differences are positive in {positive}/24 contexts and significant under the directional corrected test in {significant}/24. "
            "The evidence concerns within-testbed, class-capped cohorts and a stated masking protocol; it does not establish analyst usefulness, deployment readiness, or coverage of unsupported attack labels. Legacy benchmark conversions remain historical because their transformation histories are unknown.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest, tables = load_results(args.results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document, col_w, front = make_document(args.output, make_abstract(tables))
    fonts = register_fonts()

    def embedded_font_canvas(*a, **kwargs):
        kwargs.update(initialFontName=fonts["regular"], initialFontSize=9)
        return pdf_canvas.Canvas(*a, **kwargs)

    document.build(build_story(manifest, tables, col_w, front, args.results),
                   canvasmaker=embedded_font_canvas)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
