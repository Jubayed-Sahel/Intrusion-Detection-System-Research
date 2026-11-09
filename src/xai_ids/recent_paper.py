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

from .paper import make_table, paper_metadata, register_fonts, styles
from .extended_validation_results import load_extended, large_test_finding
from .publication_extensions import TITLE, extension_abstract, kernel_paragraph, lime_budget_results, masking_results, scenario_six_misses, source_holdout_results


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "outputs" / "recent2025"
OUTPUT = ROOT / "output" / "pdf" / "xai_ids_recent2025_paper.pdf"
DEFAULT_TITLE = TITLE
DATASETS = ("GeNIS2025", "Gotham2025")
MODELS = {"random_forest": "RF", "xgboost": "XGB"}
TASKS = {"binary": "Binary", "multiclass": "Multi"}


def manuscript_identity():
    """Read approved identity fields; withhold names during anonymous review."""
    meta = paper_metadata()
    title = meta.get("recent_title") or DEFAULT_TITLE
    authors = meta.get("authors") or "Anonymous Author(s)"
    affiliation = meta.get("affiliation") or ""
    date = meta.get("recent_date") or "14 October 2026"
    footer = meta.get("recent_footer") or (
        "Research draft | official-source 2025 benchmarks | venue not selected"
    )
    anonymous = str(meta.get("anonymous_review", "true")).strip().lower() in {
        "1", "true", "yes", "y",
    }
    if anonymous:
        author_line = f"Anonymous research draft<br/>{escape(date)}"
        document_author = "Anonymous research draft"
    else:
        details = affiliation if affiliation and "anonymous" not in affiliation.lower() else ""
        author_line = (
            f"{escape(authors)}<br/><font size='8'>{escape(details)}</font><br/>{escape(date)}"
            if details else f"{escape(authors)}<br/>{escape(date)}"
        )
        document_author = authors
    return {
        "title": title,
        "authors": authors,
        "document_author": document_author,
        "author_line": author_line,
        "footer": footer,
        "date": date,
        "anonymous": anonymous,
    }


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


def make_document(path: Path, abstract: str, identity: dict):
    fonts, s = register_fonts(), styles()
    page_w, page_h = letter
    margin, gutter = 0.55 * inch, 0.22 * inch
    usable = page_w - 2 * margin
    col_w = (usable - gutter) / 2
    # Measure the full-width front matter before defining body frames. This
    # prevents a longer data-driven abstract spilling into the first column.
    front = [Paragraph(identity["title"], s["title"]),
             Paragraph(identity["author_line"], s["author"]),
             Paragraph(abstract, s["abstract"]),
             Paragraph("<b>Index Terms</b>-Intrusion detection, explainable AI, TreeSHAP, LIME, explanation fidelity, provenance, group holdout.", s["abstract"])]
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
        canvas.drawString(margin, 0.30 * inch, identity["footer"])
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
    document = BaseDocTemplate(str(path), pagesize=letter, title=identity["title"],
                              author=identity["document_author"], creator="Reproducible XAI-IDS research artifact",
                              subject="Official-source 2025 dataset provenance and group-aware explanation evaluation",
                              keywords="intrusion detection, TreeSHAP, LIME, explanation fidelity, GeNIS, Gotham, dataset provenance")
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
    para("An explanation ranking can appear effective because of the intervention used to evaluate it. In network intrusion detection, replacing correlated protocol fields by marginal reference values may create records far from the observed traffic distribution. Method comparisons should therefore state the replacement rule and examine whether their conclusions persist when that rule and the source partition change. We evaluate two openly accessible author-published 2025 datasets with an inspectable preparation chain: GeNIS [1], [2] and Gotham [3], [4]. A recent release date alone does not resolve leakage, class coverage, or external validity.")
    para("We compare Random Forest (RF) [5] and XGBoost (XGB) [6] under binary and multiclass targets, and compare TreeSHAP with LIME on the same selected test records for each fitted model. Section II positions this protocol against prior XAI-IDS evaluations. We do not propose a new explanation algorithm or establish analyst benefit.")
    para("The research questions are how predictive and explanation results vary across fitting seeds on a frozen group split; whether top-ranked predictors outperform random rankings; and how the paired TreeSHAP-LIME difference responds to replacement schemes, a larger LIME sampling budget, and source-file holdouts with shared connections purged. The follow-up studies were designed after inspecting the primary results. They are explicitly exploratory; their protocols were fixed before their own execution, not prospectively preregistered.")

    sec("II", "Related work")
    para("SHAP represents a prediction as additive feature contributions under a specified value function [7], and TreeSHAP computes those contributions from a fitted tree ensemble [8]. LIME fits an interpretable surrogate on perturbed neighbors of one input [9]. Visual plausibility is not a sufficient test: Yeh <i>et al.</i> define infidelity and sensitivity with respect to a perturbation distribution [10], and Adebayo <i>et al.</i> show that saliency maps can remain visually convincing after model-parameter randomization [11].")
    para("Neupane <i>et al.</i> survey explainable IDS (X-IDS) designs and call for stakeholder-specific explanations and explicit evaluation metrics rather than visualization alone [12]. Mane and Rao illustrate several explanation styles, including SHAP and LIME, for a deep IDS on NSL-KDD [13]. Gaspar <i>et al.</i> apply LIME and SHAP to a multilayer-perceptron detector using ADFA-LD-derived system-call sequences, perform explanation-guided perturbations, and survey perceived interpretability [14]. Their experiments include randomly chosen replacement system calls; this differs from our random permutations of feature rankings under a fixed median/mode mask. Warnecke <i>et al.</i> evaluate descriptive accuracy, completeness, efficiency, and robustness on malware detection and vulnerability discovery [15]. Arreche <i>et al.</i> propose E-XAI, scoring SHAP and LIME with descriptive accuracy, sparsity, stability, efficiency, robustness, and completeness on NSL-KDD, CIC-IDS2017, and RoEduNet-SIMARGL2021, including Wilcoxon tests [16]. Its descriptive-accuracy curves evaluate prediction accuracy as top-ranked features are removed from training and evaluation. Our primary endpoint instead measures probability drops in an already fitted model on matched diagnostic records.")
    para("This paper does not claim SHAP/LIME use, perturbation testing, or metric-based explainer comparison as new ideas. Relative to those studies, the contribution is a provenance-traceable protocol on two independently acquired 2025 author releases: member-level source verification, exclusion of Gotham Unknown from supervised tasks, deterministic class caps, a frozen connection-group holdout with group-level inference, matched TreeSHAP and LIME records, deletion versus random and bottom-ranked controls, Holm-corrected families over 24 explainer and 48 control tests, and explicit limits on checksum scope, class support, and analyst usefulness. No participant study is reported.")
    para("Recent comparisons further narrow this contribution. Kalakoti <i>et al.</i> evaluate four explainers for LSTM-based prioritization of real SOC alerts and use analyst-selected features as a reference [17]; that task and its DeepExplainer implementation differ from traffic classification with TreeSHAP. Kumar and Thing compare TRUSTEE and SHAP for online IoT detectors and investigate inductive bias [18]. Hermosilla <i>et al.</i> evaluate SHAP/LIME fidelity, stability and feature agreement for XGBoost and TabNet on UNSW-NB15 [19], while Nugraha <i>et al.</i> combine statistical/SHAP feature selection, refitting and local explanations on DDoS, IoT and 5G traces [20]. We therefore contribute neither the first quantitative IDS comparison nor dual-explainer validation. Their scores, SHAP variants, perturbation budgets and tasks do not permit numerical league-table comparisons with our deletion endpoint.")
    para("Security evaluation guidance identifies spurious correlations, lab-only tests and distorted base rates as recurring pitfalls [21]. Dataset reconstruction can change class-level findings while leaving aggregate accuracy similar [22]. Accordingly, we retain the simple tree baseline and report failed classes; interpretable-model alternatives should not be dismissed a priori [23]. Explanations can also disagree in feature identity, order or sign [24], so feature-set overlap alone cannot validate a ranking.")
    para("Perturbation-based explanations can be manipulated by classifiers that distinguish real and synthetic inputs [25]. Hase <i>et al.</i> examine replacement-induced distribution shift [26]; Aas <i>et al.</i> examine dependent predictors [27]; and Sundararajan and Najmi distinguish Shapley value functions [28]. OpenXAI [29] and Quantus [30] separate evaluation dimensions instead of treating any single metric as explanation truth. ROAR evaluates refitted models after feature removal [31], and ROAD addresses image-mask confounding [32]. Neither is equivalent to our fixed-model tabular intervention; image-specific imputation is not assumed valid for protocol fields.")

    sec("III", "Explanation methods and evaluation scope")
    para("We explain the model's predicted class, including wrong predictions. Absolute attribution magnitude determines deletion order. Values from the two methods need not share an output scale: TreeExplainer may return margin units for XGBoost while Random Forest output is a class probability, so comparisons use ranking and the fitted model's target-class probability after masking. Removal-based explanations depend on how features are removed, which model behavior is measured, and how influence is summarized [33]. A probability-drop test measures the model's response to synthetic masking. It does not show that the selected feature is a causal attack indicator, that the masked record is physically valid, or that an analyst will make a better decision. We therefore call the endpoint deletion fidelity under the stated baseline, report random and bottom-ranked controls, and separate this endpoint from classification quality and human usefulness.")

    sec("IV", "Source provenance and data preparation")
    sub("A", "Official releases and verification scope")
    para("GeNIS was released on 24 February 2025 at author Zenodo record 14919237. It supplies simulated enterprise attack scenarios exported at multiple flow intervals [1], [2]. We use all eight scenario CSV members at the 5-second interval. The downloaded 3-scenarios.zip archive and 0-info.zip match their provider MD5 values; SHA-256 is recorded for those archives and each consumed CSV member. The provider's exporter output is the starting input; raw packet recapture and flow regeneration are outside this study.")
    para("Gotham was released on 5 February 2025 at author Zenodo record 14502760. Its packet-level CSVs preserve captures from 78 emulated IoT devices [3], [4]. All 78 author CSV members were acquired directly from the official ZIP through HTTP byte ranges. Each extracted member's CRC32 was checked against the ZIP directory, and a SHA-256 was recorded. The provider MD5 for the complete 23.8-GB ZIP was recorded but <b>was not recomputed or verified</b>: the complete archive was not downloaded. Member integrity checking is narrower than full-archive checksum verification.")
    dates = sources["Gotham2025"].get("source_date_range_utc", [None, None])
    if all(dates):
        para(f"The Gotham CSV timestamps parsed during preparation span {esc(dates[0])} through {esc(dates[1])} (UTC). GeNIS capture timestamps are not reliably established by the consumed CSV representation. The names GeNIS2025 and Gotham2025 denote release-year identifiers; they do not imply 2025 capture dates. The acquisition manifest records source URLs, UTC download times, metadata snapshots, checksum scope, transformation code hashes, and prepared parquet hashes.")
    else:
        para("The dataset identifiers denote 2025 release years. GeNIS capture dates are not reliably established by the consumed CSV representation. We do not equate release year with capture year. The acquisition manifest records source URLs, UTC download times, metadata snapshots, checksum scope, transformation code hashes, and prepared parquet hashes.")
    sub("B", "Deterministic sampling and grouped holdout")
    para("Every selected source member is scanned. Independent random priorities with seed 42 retain at most 10,000 records per eligible original source label globally, rather than per file. Consequently the study uses a bounded class-capped cohort, not the full natural traffic distribution. Source filename and row offset are retained as audit metadata and excluded from the model. Known attack labels are merged only for the binary target; the multiclass target retains eligible provider labels. Table I reports the frozen cohort sizes.")
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
    table("TABLE I. FROZEN COHORT SIZES; p = FEATURE COUNT", rows, [.16, .26, .28, .10, .20], 6.2)
    for dataset in DATASETS:
        source = sources[dataset]
        audit = source["split_audit"]
        absent = sorted(set(audit["training_labels"]) - set(audit["test_labels"]))
        para(f"{short_dataset(dataset)} has zero overlapping train/test groups. {source['test_feature_vectors_also_present_in_training']:,} test feature vectors also occur in training; these are retained under the declared policy because equal predictor patterns can arise in different recorded groups. " +
             (f"Training-only labels are {', '.join(esc(v) for v in absent)}; no test recall or generalization claim is made for them." if absent else "Every sampled multiclass label has test support."))
    sub("C", "Predictors and preprocessing")
    para("Labels, IP/MAC addresses, timestamps, identifiers, payload fields, and selected exporter-specific metadata are excluded before modeling. The exact dataset-specific exclusion list is saved in the provenance manifest. Constants are removed using training rows alone. Numeric infinities become missing values and are imputed with training medians. Categorical features are mapped with training-only category dictionaries; unseen test values map to -1. Median/mode training values form the masking baseline. No scaling or imputation is fit on the test set. Retained ports, protocol, flags, sizes, and timing features may still encode testbed-specific shortcuts.")

    sec("V", "Experimental protocol")
    sub("A", "Prediction and class support")
    config = manifest["config"]
    rf, xgb = config["models"]["random_forest"], config["models"]["xgboost"]
    para(f"Predictive seeds are {', '.join(map(str, config['predictive_seeds']))} on the same frozen cohort and split. RF uses {rf['n_estimators']} trees, maximum depth {rf['max_depth']}, minimum leaf size {rf['min_samples_leaf']}, and balanced-subset class weights. XGB uses {xgb['n_estimators']} trees, maximum depth {xgb['max_depth']}, learning rate {xgb['learning_rate']}, and row/column fractions {xgb['subsample']}/{xgb['colsample_bytree']}; training sample weights balance classes. Fixed hyperparameters are not selected on this test set. Majority-class and depth-5 single-tree baselines use the same split.")
    para("Accuracy, balanced accuracy, macro-F1, weighted-F1, and per-class support are saved. Binary false-positive rate uses Normal as the negative class; false-negative rate and average precision use Attack as positive. Headline macro-F1 averages a fixed label set with positive test support, identical across model seeds on the frozen split. A training-only class is excluded from that average, but predictions into it still cause false negatives for the supported true class and reduce its recall. Per-class precision is also computed from all predictions rather than discarding unsupported predictions. This scorer does not imply coverage of every provider label. The default true/predicted-label union macro-F1 and training-vocabulary macro-F1 are retained separately for compatibility and audit. Mean and sample standard deviation over five seeds quantify training-seed variation on one split, not uncertainty over networks or captures.")
    sub("B", "Matched explanation records and masking")
    para("For each model at seeds 42, 52, and 62, the two explainers process the same 100 selected test records. Selection is stratified by true class and prioritizes available misclassification types. Thus the explanation cohort is intentionally diagnostic and is not a prevalence-representative sample; selected records can differ between fitted models. LIME uses up to 5,000 training background rows stratified by model prediction, continuous discretization, all predictors, and 350 perturbations per call. TreeExplainer uses its model-based defaults without an explicit background matrix; additivity checking is disabled. XGB attributions can be in margin units, while RF output differs, so comparisons rely on ranking rather than raw attribution magnitudes.")
    para("For record x, predicted class c, and ranking r, replace the top k predictors by training median/mode values for k in {1, 3, 5, 10}. Recompute p(c|x) after masking. The per-budget score is D<sub>k</sub>(x,r)=p(c|x)-p(c|mask<sub>k</sub>(x,r)); the primary endpoint D(x,r) averages these four budgets. Negative values are permitted. One seeded random ranking and a reversed bottom ranking use the same masking budgets. Random-control permutations are matched between the explainers for a fitted context.")
    story.append(Paragraph("D(x,r) = (1/4) &Sigma;<sub>k &isin; {1,3,5,10}</sub> D<sub>k</sub>(x,r)", s["equation"]))
    sub("C", "Group-level statistical analysis")
    para("Repeated packets or windows within one explained connection are averaged first at each masking budget. Budgets are then averaged to obtain one endpoint per explained group, giving groups equal weight. TreeSHAP-minus-LIME differences and top-minus-random control lifts are paired within group. Percentile 95% confidence intervals use 2,000 paired group bootstrap resamples, applying bootstrap resampling [34] to our declared connection-group unit. One-sided Wilcoxon signed-rank tests [35] use the alternatives TreeSHAP &gt; LIME and top &gt; random; these are directional tests and do not establish a significant LIME advantage when negative. Fewer than five groups are marked insufficient and assigned p = 1. Holm adjustment [36] is computed across all 24 explainer contexts and separately all 48 control contexts. Seeds reuse a fixed test partition and are not independent datasets; we do not pool them into one pseudo-replicated test.")
    sub("D", "Secondary endpoints and audits")
    para("Explainer timings measure a warmed individual explanation call, excluding constructor setup, packet extraction, preprocessing, and rendering. Other preparation or experiment jobs were active during parts of the project run. Median and upper percentiles are therefore descriptive project-run measurements on this machine, not an isolated service benchmark; CPU contention can affect timing comparisons. Neighborhood similarity compares each selected record to its nearest selected record with the same predicted class after scaling the selected matrix: cosine similarity of signed attributions and top-5 Jaccard overlap. This diagnostic is descriptive and is not a train-fitted deployment transformation. LIME repeatability uses six selected records and five repeat seeds, with training-background sampling varying as well. Feature ablation refits seed-42 models with 5, 10, 20, and all predictors ranked by training-fitted model importance; it is not SHAP-guided selection.")

    sec("VI", "Results")
    sub("A", "Predictive performance")
    para("Table II reports five-seed predictive results using test-supported-label macro-F1. Table III lists majority and depth-5 tree baselines on the same split. Table IV reports seed-42 multiclass recall by class.")
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
    para("Per-class recall and support temper aggregate scores. Both models have zero recall for Gotham Mirai C&amp;C Communication across all five predictive seeds despite 358 test records. Merlin ICMP Flooding has only three test records; its perfect recall cannot establish reliable coverage. CoAP Amplification has no test support. A zero-support label has no measured recall, even if included in the training class dictionary. The full per-class CSV preserves zero-support rows and seed-specific precision, recall, and F1. These failures and sparse supports prevent interpreting high aggregate scores as comprehensive attack detection.")
    sub("B", "Paired deletion fidelity")
    para(f"TreeSHAP-minus-LIME mean deletion differences are positive in {positive}/{total} contexts. The pre-specified TreeSHAP-greater directional test is significant after full-family Holm adjustment in {int(significant.sum())}/{total} contexts. Figs. 1 and 2 show the context-specific effect estimates and group-bootstrap intervals; Table V summarizes the three model seeds. A non-significant result should not be read as equivalence, and a positive deletion difference is not evidence of superior analyst decisions.")
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
    para("Table VI asks whether the ranking is informative under the same synthetic intervention. CI + Holm requires a positive lower 95% group-bootstrap bound together with Holm-adjusted directional p &lt; 0.05. Every top-minus-random hypothesis is adjusted in the 48-test family. " +
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
        para("Additional seed-42 audits evaluate binary calibration on the test cohort (Table IX), weighted versus unweighted fitting, TreeSHAP masking under five baselines on 12 diagnostic records, and LIME perturbation budgets 100, 350, and 700 on six records with five repeats (Table X). These small sensitivity cohorts provide descriptive checks; they are not independent confirmatory studies or a replacement for the paired group-level primary endpoint.")
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

    sub("E", "Post-hoc sign, influence and pattern-exclusion checks")
    if result_dir.resolve() == RESULTS.resolve():
        robustness_dir = ROOT / "outputs" / "explanation_robustness"
        robustness = json.loads((robustness_dir / "manifest.json").read_text(encoding="utf-8"))["summary"]
        if robustness["contexts"] != 24:
            raise ValueError("Incomplete sign/influence supplement")
        para(f"A separately labelled post-hoc sensitivity analysis reproduces all 24 original paired means and group counts. Exact two-sided sign tests on connection-level differences, excluding absolute differences at most 1e-12, favor TreeSHAP in {robustness['positive_sign_test_holm']}/24 contexts after Holm correction within this separate family. Removing any one explained connection reverses the mean sign in {robustness['single_group_reversals']}/24 contexts. The sign test targets direction frequency, not the mean endpoint, and still requires sufficiently independent connection signs. Leave-one-out extrema are influence diagnostics, not confidence intervals.")
        pattern_dir = ROOT / "outputs" / "pattern_sensitivity_20261107"
        pattern_summary = json.loads((pattern_dir / "manifest.json").read_text(encoding="utf-8"))["summary"]
        pattern_predictive = pd.read_csv(pattern_dir / "predictive.csv")
        pattern_coverage = pd.read_csv(pattern_dir / "coverage.csv")
        rows = [["Dataset / model", "Original F1", "Pattern-excluded F1"]]
        for (dataset, model), group in pattern_predictive[pattern_predictive.task.eq("multiclass")].groupby(["dataset", "model"]):
            values = group.set_index("cohort").macro_f1_fixed_original_test_labels
            rows.append([f"{short_dataset(dataset)} {MODELS[model]}", fmt(values['original'],4), fmt(values['no_train_matching_pattern'],4)])
        table("TABLE XI. POST-HOC SEED-42 MULTICLASS PATTERN SENSITIVITY", rows, [.48,.26,.26])
        coverage_text = "; ".join(f"{short_dataset(row.dataset)}: {row.excluded_test_rows:,} excluded and {row.retained_test_rows:,} retained" for row in pattern_coverage.itertuples())
        para(f"A second post-hoc diagnostic excludes test records with exactly matching raw predictor vectors in training, without using labels in the matching key ({coverage_text}). No model is refitted or selected. Macro-F1 keeps the original supported-test-label denominator; no supported label is lost. Table XI exposes the Gotham multiclass reduction. Reusing the saved explanation records after this exclusion retains {pattern_summary['retained_group_range'][0]}-{pattern_summary['retained_group_range'][1]} explained groups per context; {pattern_summary['positive_means']}/24 mean differences remain positive and {pattern_summary['positive_sign_test_holm']}/24 two-sided sign tests favor TreeSHAP after a separate Holm adjustment. This is a conditional selection diagnostic, not a new disjoint split or external validation; it cannot remove shared campaign or testbed mechanisms.")
    else:
        para("Post-hoc sign/influence and exact-pattern supplements belong to the original primary run. They are not imported into this separate result directory; no recomputed sensitivity result is implied.")

    if result_dir.resolve() == RESULTS.resolve():
        sub("F", "Paired sensitivity to the replacement distribution")
        _, masking, mask_summary = masking_results()
        para("The earlier five-reference audit evaluated only TreeSHAP on twelve records per context. To test the comparison itself, a new exploratory protocol reuses all 100 saved matched records, both saved rankings and the eight seed-42 models. It compares the original median/mode reference with two training-donor schemes. A fixed pool samples 5,000 training rows uniformly. Empirical replacement copies removed features jointly from 32 donors, using the same draws for both explainers and all budgets of a record. Nearest-donor replacement chooses 32 pool rows using retained predictors only: numeric distances use training IQR (standard deviation, then one, as fallbacks), are capped at one, and categorical predictors contribute mismatch indicators. Distances average retained predictors; labels and model outputs never select donors. Removed values are copied jointly and the 32 target probabilities averaged. This approximate conditioning sensitivity does not guarantee physically valid network traffic.")
        rows = [["Dataset / task / model", "Median", "Joint", "Nearest", "Nearest 95% CI"]]
        for (dataset, task, model), group in masking.groupby(["dataset", "task", "model"]):
            by_scheme = group.set_index("scheme")
            nearest = by_scheme.loc["retained_nearest_donor"]
            rows.append([f"{short_dataset(dataset)} {TASKS[task]} {MODELS[model]}",
                fmt(by_scheme.loc["training_median_mode", "mean_difference_shap_minus_lime"],4),
                fmt(by_scheme.loc["empirical_joint_donor", "mean_difference_shap_minus_lime"],4),
                fmt(nearest.mean_difference_shap_minus_lime,4),
                f"[{fmt(nearest.ci_low,4)}, {fmt(nearest.ci_high,4)}]"])
        table("TABLE XII. REPLACEMENT-SPECIFIC MEAN TREESHAP-MINUS-LIME DELETION, SEED 42", rows, [.29,.13,.13,.13,.32], 6.2)
        para(f"Original median/mode drops reproduce to a maximum absolute error of 3.33e-16. Table XII shows that the measured advantage depends strongly on replacement. GeNIS nearest-donor mean gaps are only {fmt(mask_summary['genis_nearest_min'],4)}-{fmt(mask_summary['genis_nearest_max'],4)}, and {mask_summary['genis_crossing_intervals']}/4 corresponding pointwise mean intervals cross zero. Across both datasets, nearest donors retain {mask_summary['nearest_positive_means']}/8 positive means and {mask_summary['nearest_positive_intervals']}/8 positive lower interval bounds. Exact two-sided sign tests favor TreeSHAP in {mask_summary['nearest_positive_sign_tests']}/8 nearest contexts after Holm adjustment across the separate 24-context/scheme family; median/mode and empirical donors each have 8/8. The tests target non-tied direction frequency rather than the mean: GeNIS binary RF has 69 ties among 93 groups, while multiclass RF has 56 among 95. A positive mean, a positive interval and a significant sign test are not interchangeable findings. All schemes, including weak effects, are retained.")

        sub("G", "Controlled LIME budget and local fit")
        _, budget_contrasts, budget_fit, budget_summary = lime_budget_results()
        para("A second exploratory extension refits LIME explanations, not detectors. On the same 100 records in each seed-42 context, it fits a fresh default-neighborhood surrogate at 350 and 3,500 perturbations using a common per-record seed and training background. Common seeds do not guarantee nested random samples. This fresh schedule differs from the original sequential warm-up and is not a reproduction of the primary 350-draw ranking. Saved TreeSHAP and both fresh LIME rankings are evaluated with the original median/mode mask. Group bootstrap intervals and exact two-sided sign tests follow the other exploratory analyses, with Holm adjustment over eight TreeSHAP-minus-LIME-3500 and eight LIME-3500-minus-LIME-350 contrasts as one separate family.")
        rows = [["Dataset / task / model", "Fit error 350 / 3500", "LIME budget delta", "SHAP - LIME 3500"]]
        for (dataset, task, model), group in budget_contrasts.groupby(["dataset", "task", "model"]):
            by_left = group.set_index("left").mean_difference
            errors = budget_fit.absolute_local_prediction_error.loc[(dataset, task, model)]
            rows.append([f"{short_dataset(dataset)} {TASKS[task]} {MODELS[model]}",
                         f"{fmt(errors[350],3)} / {fmt(errors[3500],3)}",
                         fmt(by_left.loc["LIME_3500"],3), fmt(by_left.loc["TreeSHAP_saved"],3)])
        table("TABLE XIII. CONTROLLED LIME BUDGET: QUERY FIT AND GROUP DELETION", rows, [.34,.25,.19,.22], 6.2)
        para(f"LIME-3500 mean deletion improves over LIME-350 in {budget_summary['budget_positive_means']}/8 contexts, with {budget_summary['budget_positive_sign_tests']}/8 corrected sign tests in that direction. TreeSHAP still has larger mean deletion in {budget_summary['shap_positive_means']}/8 contexts and positive corrected sign tests in {budget_summary['shap_positive_sign_tests']}/8. Yet mean absolute error at the explained input increases in {budget_summary['error_increases']}/8 contexts; at 3,500 samples its context means range from {fmt(budget_summary['default_high_budget_error_min'],3)} to {fmt(budget_summary['default_high_budget_error_max'],3)} on the probability scale. Mean in-neighborhood weighted R-squared falls in {budget_summary['weighted_r2_decreases']}/8. These descriptive fit scores are distinct from deletion fidelity. More draws do not guarantee an adequate surrogate or establish convergence; the observed comparison remains conditional on the chosen LIME neighborhood.")

        para(kernel_paragraph())

        sub("H", "Source-file transfer with shared groups purged")
        transfer, transfer_summary, transfer_counts = source_holdout_results()
        para("A separate stress test partitions the union of the original prepared rows by source instead of by connection alone. It holds out each of eight GeNIS scenario CSVs. For Gotham, each of eight bundles holds out one attack-bearing source and an assigned subset of the 57 benign-only sources. Stable SHA-256 filename order fixes the attack-source order and round-robin benign assignments before fitting. All 65 represented Gotham CSVs are held out once; thirteen acquired files have no rows in the capped cohort. All remaining training rows whose global connection keys occur anywhere in the held-out sources are purged. No source or group overlaps within a fold. Raw member hashes and row identities are verified while restoring the fifteen GeNIS and one Gotham candidate predictors removed as constants in the original split. Constant filtering, imputation and category encoding then fit on each fold's training rows alone.")
        para("For each of sixteen folds, the same binary/multiclass RF and XGB hyperparameters and training-weight policies are refitted at seed 42, for 64 fits; majority and depth-five trees remain baselines. Every held-out class with test support contributes to macro-F1, including labels missing from the training vocabulary. A separate seen-label score restricts both test rows and averaging labels. The two explainers process 50 matched class/error diagnostic records per refit, with the original median/mode mask, random control and 350 LIME perturbations. We report mean differences descriptively: the folds share training data and can reuse connection groups across different test sources, so the 64 contexts are not pooled for significance inference.")
        rows = [["Dataset / task / model", "F1 mean [range]", "SHAP - LIME range", "Positive / 8"]]
        for row in transfer_summary.itertuples(index=False):
            rows.append([f"{short_dataset(row.dataset)} {TASKS[row.task]} {MODELS[row.model]}",
                         f"{fmt(row.f1_mean)} [{fmt(row.f1_min)}, {fmt(row.f1_max)}]",
                         f"{fmt(row.gap_min)} to {fmt(row.gap_max)}", str(row.positive_gaps)])
        table("TABLE XIV. SOURCE HOLDOUT: ALL-TEST-LABEL MACRO-F1 AND PAIRED DELETION", rows, [.30,.32,.25,.13], 6.2)
        example = transfer[(transfer.dataset.eq("GeNIS2025")) & (transfer.fold.eq(6)) &
                           (transfer.task.eq("binary")) & (transfer.model.eq("xgboost"))].iloc[0]
        classes = pd.read_csv(ROOT / "outputs/source_holdout_20261108/per_class_metrics.csv")
        brute = classes[(classes.dataset.eq("GeNIS2025")) & (classes.fold.eq(6)) & (classes.task.eq("multiclass")) &
                        (classes.model.eq("xgboost")) & (classes["class"].eq("bruteforce"))].iloc[0]
        para(f"The source-held-out scores in Table XIV vary substantially even when all test labels appear in training. In GeNIS scenario 6, binary XGB macro-F1 is {fmt(example.macro_f1_all_test_supported_labels,4)} and the attack false-negative rate is {100*example.false_negative_rate:.2f}%. Its multiclass model has recall {brute.recall:.3f} on {brute.test_support:,} brute-force records despite {brute.training_support:,} same-label training records. Gotham's combined-cycle-1 fold additionally contains {transfer_counts['unseen_multiclass_rows']:,} records from labels absent in training (CoAP Amplification and UDP Scan), which contribute zero recall. TreeSHAP-minus-LIME mean deletion is positive in {transfer_counts['positive_gaps']}/64 contexts and negative in {transfer_counts['negative_gaps']}/64 under this mask. This alternative split changes source membership, group purging, train size and test class mix jointly; their individual effects are not identified. The experiment is within the original two testbeds, not an external capture validation.")

    if result_dir.resolve() == RESULTS.resolve():
        sub("I", "Uncapped source files and independent capture")
        coverage, uncapped, external = load_extended()
        para("Without refitting, we score the same 64 source-holdout detectors on the complete assigned files: eight GeNIS scenarios and 65 Gotham sources. Gotham files absent from the capped assignment are outside this comparison. We exclude Unknown and any additional raw test rows whose connection keys match capped training, then replay full confusion matrices. The original sampled training sets remain fixed. This tests a change in test coverage and recorded prevalence together, not the effect of increasing training size.")
        para(large_test_finding(coverage, uncapped))
        example = uncapped.query("dataset == 'GeNIS2025' and fold == 6 and task == 'binary' and model == 'xgboost'").iloc[0]
        para(f"On the expanded GeNIS scenario 6 test, binary XGBoost misses {int(example.missed):,} of {int(example.attacks):,} attack records and flags {int(example.false_alarms):,} of {int(example.benign):,} benign records. Capped and uncapped results use different test compositions and should not be interpreted as a causal sample-size effect.")
        para("For independent capture transfer, fresh binary RF and XGB models fit only the original GeNIS training partition. The official OCPP 1.6 charging-network dataset [37] supplies 4,415 externally captured flows from both provider Combined partitions, kept entirely out of fitting and threshold selection. One fixed feature set uses protocol and unordered TCP/UDP ports; the other adds duration in seconds and total packets. Units and directions are harmonized, but Argus and CICFlowMeter may segment traffic differently. The external release is provider-balanced by category (883 benign and 3,532 attack-labeled flows); it cannot estimate operational prevalence or alert volume.")
        rows = [["Set / model", "GeNIS F1", "OCPP F1", "Missed", "False alarms"]]
        for (spec, model), group in external.groupby(["feature_set", "model"]):
            values = group.set_index("test")
            target = values.loc["OCPP"]
            rows.append([f"{'Transport' if spec=='transport' else 'Plus volume'} {MODELS[model]}",
                         fmt(values.loc["GeNIS","macro_f1"]), fmt(target.macro_f1),
                         int(target.missed), int(target.false_alarms)])
        table("TABLE XV. INDEPENDENT OCPP TRANSFER; MISSES OF 3,532, FALSE ALARMS OF 883", rows, [.32,.16,.16,.16,.20], 6.2)
        para("Protocol/port models miss only two to five attack-labeled flows but flag 303-325 benign flows. Adding duration and packet count raises source-test macro-F1 yet lowers external macro-F1 for both models; it misses 807-821 attack-labeled flows, mainly unauthorized-access examples. This is transfer of reduced-feature binary classifiers to one independent testbed, not validation of the original full-feature models, multiclass taxonomies, or explanation fidelity.")
    else:
        para("The independent OCPP comparison [37] belongs to the original GeNIS source training partition and is not reused for this build.")

    sec("VII", "Discussion and threats to validity")
    para("The refreshed evidence addresses the missing local conversion history by making the source-to-cohort transformation inspectable and rerunnable. It does not retrospectively recover the legacy parquet provenance. Source snapshots and hashes fix the consumed author files and executed transformations, while the narrower Gotham member-verification scope remains a declared limitation. CRC32 detects transfer or extraction inconsistency; it is not a publisher-signed cryptographic authenticity proof.")
    para("The primary group split prevents the chosen connection keys from crossing partitions but does not separate source files. The secondary holdout adds that separation and purges shared connection keys, while GeNIS scenarios can still share generation mechanisms and Gotham source files can share a virtual testbed or campaign. Neither original within-testbed design is forward-in-time or cross-network; the separate reduced-feature OCPP experiment tests only binary transfer. The source analysis exposes weak transfer within the observed cohorts; it does not estimate an external site's error rates. Equal feature patterns can still occur in different groups and sources.")
    para("The class cap changes prevalence and can underrepresent rare attack diversity. Unknown-labelled packets are outside both supervised tasks. A label confined to one group cannot support an independent test claim; the supported-class macro-F1 is restricted to labels present in test. Five predictive seeds share one preparation seed and one split; they do not explore split uncertainty. Explanation sampling prioritizes error types, and the inferential population is the explained groups represented by this selection rather than every packet in the full dataset. Group means reduce within-key dependence but do not remove all dependence across groups or model seeds.")
    para("The directional TreeSHAP-greater test permits checking that specific hypothesis; a reverse claim requires a separately specified analysis. Bootstrap intervals are per context and are not simultaneous confidence intervals, whereas Holm controls the reported hypothesis families. The default TreeSHAP value function and LIME's discretized local surrogate can respond differently to correlated and categorical predictors. Masking by a mixed median/mode vector can create off-manifold combinations, so a larger deletion drop is a protocol-specific ranking result.")
    para("This work has no participant study, production monitoring, packet-capture throughput benchmark, drift test, or attack intervention study. Gaspar <i>et al.</i> [14] include a perceived-interpretability survey; our work has no corresponding human evidence. Neither our deletion results nor that survey establish operational alert cost, current attack coverage, or adversarial safety. A stronger next evaluation would freeze the chosen configuration, use a separately captured device/scenario/time holdout, retain natural prevalence for operational calibration, and measure analyst decisions with a pre-specified human study.")

    if result_dir.resolve() == RESULTS.resolve():
        attacks, normal, misses, _ = scenario_six_misses()
        para(f"<b>Implications for detector review:</b> In GeNIS scenario 6, the two ensembles and the depth-five tree each raise zero false alarms over {normal:,} benign records, yet miss {misses['random_forest']:,}, {misses['xgboost']:,} and {misses['depth5_tree']:,} of {attacks:,} attack records, respectively. The failure is shared across model families. Report missed attacks and false alarms with denominators on held-out sources before judging detector coverage. For explanations, report original-query surrogate error separately from deletion and show sensitivity to alternative replacements. These checks inform review priorities; they have not been validated as an analyst workflow.")

    sec("VIII", "Reproducibility and reporting status")
    environment = manifest["environment"]
    packages = environment["packages"]
    para(f"The executed environment uses Python {esc(environment['python'])}, scikit-learn {esc(packages['scikit-learn'])}, XGBoost {esc(packages['xgboost'])}, SHAP {esc(packages['shap'])}, and LIME {esc(packages['lime'])}. The project saves author-record metadata, acquisition and per-member hashes, exclusions, source row counts, class counts, split and overlap audits, prepared parquet hashes, source snapshots, fitted seed-42 models, and per-context checkpoints. The configuration and source hashes in run_manifest.json define this run. Artifact verification checks coverage and internal consistency; it is not independent external replication.")
    para("A clean rerun begins with the official acquisition scripts, then deterministic preparation, the recent-data benchmark, and artifact verification. It requires the author data downloads and the pinned requirements. The benchmark caps are part of the experiment and should not be silently replaced with full-data or per-file caps. No repository release, archival DOI, or externally executed replication is claimed in this draft.")
    para("<b>AI assistance disclosure:</b> OpenAI Codex assisted with source acquisition tooling, data auditing, experiment orchestration, and manuscript drafting. The authors must verify the methods, results, citations, and disclosure against the selected venue's requirements and accept responsibility for the final work. No specific IEEE journal or conference has been selected. The generic IEEE conference format used here does not establish compliance with a selected venue's submission requirements.")

    sec("IX", "Conclusion")
    para(f"TreeSHAP has a positive mean deletion difference in {positive}/{total} primary contexts, all meeting the directional Holm-adjusted criterion under median/mode masking. That finding is conditional: on the same records, retained-feature donor replacement greatly reduces GeNIS gaps and removes clear positive mean intervals in three of four contexts. Increasing LIME's sampling budget alone does not close the median/mode gap or fix its local surrogate. Source-file separation with group purging reveals predictive failures even for attack classes seen in training. The contribution is a traceable evaluation showing which conclusions change when these choices change. External captures, validated traffic interventions and analyst decisions remain distinct validation targets.")

    story.append(Paragraph("REFERENCES", s["section"]))
    references = [
        '[1] M. Silva, D. Pinto, J. Vitorino, J. Gonçalves, E. Maia, and I. Praça, "GeNIS: GECAD Network Intrusion Scenarios," Zenodo, ver. 1.0.0, Feb. 24, 2025, doi: <link href="https://doi.org/10.5281/zenodo.14919237">10.5281/zenodo.14919237</link>.',
        '[2] M. Silva, D. Pinto, J. Vitorino, J. Gonçalves, E. Maia, and I. Praça, "GeNIS: A modular dataset for network intrusion detection and classification," <i>Data in Brief</i>, vol. 60, art. no. 111487, Jun. 2025, doi: <link href="https://doi.org/10.1016/j.dib.2025.111487">10.1016/j.dib.2025.111487</link>.',
        '[3] O. Belarbi, T. Spyridopoulos, E. Anthi, O. Rana, P. Carnelli, and A. Khan, "A Device-Level IoT Network Traffic Dataset with Distributed Capture and Non-IID Characteristics," Zenodo, ver. v1, Feb. 5, 2025, doi: <link href="https://doi.org/10.5281/zenodo.14502760">10.5281/zenodo.14502760</link>.',
        '[4] O. Belarbi, T. Spyridopoulos, E. Anthi, O. Rana, P. Carnelli, and A. Khan, "Gotham Dataset 2025: A Reproducible Large-Scale IoT Network Dataset for Intrusion Detection and Security Research," arXiv:2502.03134, ver. 1, Feb. 5, 2025, doi: <link href="https://doi.org/10.48550/arXiv.2502.03134">10.48550/arXiv.2502.03134</link>.',
        '[5] L. Breiman, "Random forests," <i>Machine Learning</i>, vol. 45, no. 1, pp. 5-32, 2001, doi: <link href="https://doi.org/10.1023/A:1010933404324">10.1023/A:1010933404324</link>.',
        '[6] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in <i>Proc. ACM SIGKDD</i>, 2016, pp. 785-794, doi: <link href="https://doi.org/10.1145/2939672.2939785">10.1145/2939672.2939785</link>.',
        '[7] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in <i>Advances in Neural Information Processing Systems</i>, vol. 30, 2017. [Online]. Available: <link href="https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html">NeurIPS proceedings</link>.',
        '[8] S. M. Lundberg <i>et al.</i>, "From local explanations to global understanding with explainable AI for trees," <i>Nature Machine Intelligence</i>, vol. 2, pp. 56-67, 2020, doi: <link href="https://doi.org/10.1038/s42256-019-0138-9">10.1038/s42256-019-0138-9</link>.',
        '[9] M. T. Ribeiro, S. Singh, and C. Guestrin, &quot;Why should I trust you?&quot;: Explaining the predictions of any classifier, in <i>Proc. ACM SIGKDD</i>, 2016, pp. 1135-1144, doi: <link href="https://doi.org/10.1145/2939672.2939778">10.1145/2939672.2939778</link>.',
        '[10] C.-K. Yeh, C.-Y. Hsieh, A. S. Suggala, D. I. Inouye, and P. Ravikumar, "On the (in)fidelity and sensitivity of explanations," in <i>Advances in Neural Information Processing Systems</i>, vol. 32, 2019. [Online]. Available: <link href="https://proceedings.neurips.cc/paper/2019/hash/a7471fdc77b3435276507cc8f2dc2569-Abstract.html">NeurIPS proceedings</link>.',
        '[11] J. Adebayo, J. Gilmer, M. Muelly, I. Goodfellow, M. Hardt, and B. Kim, "Sanity checks for saliency maps," in <i>Advances in Neural Information Processing Systems</i>, vol. 31, 2018. [Online]. Available: <link href="https://proceedings.neurips.cc/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html">NeurIPS proceedings</link>.',
        '[12] S. Neupane <i>et al.</i>, "Explainable intrusion detection systems (X-IDS): A survey of current methods, challenges, and opportunities," <i>IEEE Access</i>, vol. 10, pp. 112392-112415, 2022, doi: <link href="https://doi.org/10.1109/ACCESS.2022.3216617">10.1109/ACCESS.2022.3216617</link>.',
        '[13] S. Mane and D. Rao, "Explaining network intrusion detection system using explainable AI framework," arXiv:2103.07110, ver. 1, Mar. 12, 2021, doi: <link href="https://doi.org/10.48550/arXiv.2103.07110">10.48550/arXiv.2103.07110</link>.',
        '[14] D. Gaspar, P. Silva, and C. Silva, "Explainable AI for intrusion detection systems: LIME and SHAP applicability on multi-layer perceptron," <i>IEEE Access</i>, vol. 12, pp. 30164-30175, 2024, doi: <link href="https://doi.org/10.1109/ACCESS.2024.3368377">10.1109/ACCESS.2024.3368377</link>.',
        '[15] A. Warnecke, D. Arp, C. Wressnegger, and K. Rieck, "Evaluating explanation methods for deep learning in security," in <i>Proc. IEEE Eur. Symp. Security and Privacy (EuroS&amp;P)</i>, 2020, pp. 158-174, doi: <link href="https://doi.org/10.1109/EuroSP48549.2020.00018">10.1109/EuroSP48549.2020.00018</link>.',
        '[16] O. Arreche, T. R. Guntur, J. W. Roberts, and M. Abdallah, "E-XAI: Evaluating black-box explainable AI frameworks for network intrusion detection," <i>IEEE Access</i>, vol. 12, pp. 23954-23988, 2024, doi: <link href="https://doi.org/10.1109/ACCESS.2024.3365140">10.1109/ACCESS.2024.3365140</link>.',
        '[17] R. Kalakoti, R. Vaarandi, H. Bahsi, and S. Nomm, "Evaluating explainable AI for deep learning-based network intrusion detection system alert classification," arXiv:2506.07882, ver. 1, 2025. [Online]. Available: <link href="https://arxiv.org/abs/2506.07882v1">arXiv preprint</link>.',
        '[18] A. Kumar and V. L. L. Thing, "Evaluating the explainability of state-of-the-art machine learning-based IoT network intrusion detection systems," arXiv:2408.14040, ver. 1, 2024. [Online]. Available: <link href="https://arxiv.org/abs/2408.14040v1">arXiv preprint</link>.',
        '[19] P. Hermosilla, S. Berrios, and H. Allende-Cid, "Explainable AI for forensic analysis: A comparative study of SHAP and LIME in intrusion detection models," <i>Applied Sciences</i>, vol. 15, no. 13, art. 7329, 2025, doi: <link href="https://doi.org/10.3390/app15137329">10.3390/app15137329</link>.',
        '[20] B. Nugraha, A. V. Jnanashree, and T. Bauschert, "A versatile XAI-based framework for efficient and explainable intrusion detection systems," <i>Annals of Telecommunications</i>, vol. 80, pp. 1095-1120, 2025, doi: <link href="https://doi.org/10.1007/s12243-025-01118-9">10.1007/s12243-025-01118-9</link>.',
        '[21] D. Arp <i>et al.</i>, "Dos and don\'ts of machine learning in computer security," in <i>Proc. USENIX Security</i>, 2022, pp. 3971-3988. [Online]. Available: <link href="https://www.usenix.org/conference/usenixsecurity22/presentation/arp">USENIX proceedings</link>.',
        '[22] G. Engelen, V. Rimmer, and W. Joosen, "Troubleshooting an intrusion detection dataset: The CICIDS2017 case study," in <i>Proc. IEEE Security and Privacy Workshops</i>, 2021, pp. 7-12, doi: <link href="https://doi.org/10.1109/SPW53761.2021.00009">10.1109/SPW53761.2021.00009</link>.',
        '[23] C. Rudin, "Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead," <i>Nature Machine Intelligence</i>, vol. 1, pp. 206-215, 2019, doi: <link href="https://doi.org/10.1038/s42256-019-0048-x">10.1038/s42256-019-0048-x</link>.',
        '[24] S. Krishna, T. Han, A. Gu, J. Pombra, S. Jabbari, S. Wu, and H. Lakkaraju, "The disagreement problem in explainable machine learning: A practitioner\'s perspective," arXiv:2202.01602, ver. 1, 2022. [Online]. Available: <link href="https://arxiv.org/abs/2202.01602v1">arXiv preprint</link>.',
        '[25] D. Slack, S. Hilgard, E. Jia, S. Singh, and H. Lakkaraju, "Fooling LIME and SHAP: Adversarial attacks on post hoc explanation methods," in <i>Proc. AAAI/ACM AIES</i>, 2020, pp. 180-186, doi: <link href="https://doi.org/10.1145/3375627.3375830">10.1145/3375627.3375830</link>.',
        '[26] P. Hase, H. Xie, and M. Bansal, "The out-of-distribution problem in explainability and search methods for feature importance explanations," in <i>Advances in Neural Information Processing Systems</i>, vol. 34, 2021. [Online]. Available: <link href="https://arxiv.org/abs/2106.00786">Author preprint</link>.',
        '[27] K. Aas, M. Jullum, and A. Loland, "Explaining individual predictions when features are dependent: More accurate approximations to Shapley values," <i>Artificial Intelligence</i>, vol. 298, art. 103502, 2021, doi: <link href="https://doi.org/10.1016/j.artint.2021.103502">10.1016/j.artint.2021.103502</link>.',
        '[28] M. Sundararajan and A. Najmi, "The many Shapley values for model explanation," in <i>Proc. ICML</i>, PMLR, vol. 119, 2020, pp. 9269-9278. [Online]. Available: <link href="https://proceedings.mlr.press/v119/sundararajan20b.html">PMLR proceedings</link>.',
        '[29] C. Agarwal <i>et al.</i>, "OpenXAI: Towards a transparent evaluation of post hoc model explanations," in <i>Advances in Neural Information Processing Systems</i>, vol. 35, 2022. [Online]. Available: <link href="https://papers.neurips.cc/paper_files/paper/2022/file/65398a0eba88c9b4a1c38ae405b125ef-Paper-Datasets_and_Benchmarks.pdf">NeurIPS proceedings</link>.',
        '[30] A. Hedstrom <i>et al.</i>, "Quantus: An explainable AI toolkit for responsible evaluation of neural network explanations and beyond," <i>Journal of Machine Learning Research</i>, vol. 24, no. 34, pp. 1-11, 2023. [Online]. Available: <link href="https://jmlr.org/papers/v24/22-0142.html">JMLR article</link>.',
        '[31] S. Hooker, D. Erhan, P.-J. Kindermans, and B. Kim, "A benchmark for interpretability methods in deep neural networks," in <i>Advances in Neural Information Processing Systems</i>, vol. 32, 2019. [Online]. Available: <link href="https://arxiv.org/abs/1806.10758">Author preprint</link>.',
        '[32] Y. Rong, T. Leemann, V. Borisov, G. Kasneci, and E. Kasneci, "A consistent and efficient evaluation strategy for attribution methods," in <i>Proc. ICML</i>, PMLR, vol. 162, 2022, pp. 18770-18795. [Online]. Available: <link href="https://proceedings.mlr.press/v162/rong22a.html">PMLR proceedings</link>.',
        '[33] I. C. Covert, S. Lundberg, and S.-I. Lee, "Explaining by removing: A unified framework for model explanation," <i>Journal of Machine Learning Research</i>, vol. 22, no. 209, pp. 1-90, 2021. [Online]. Available: <link href="https://jmlr.org/papers/v22/20-1316.html">JMLR 20-1316</link>.',
        '[34] B. Efron, "Bootstrap methods: Another look at the jackknife," <i>Annals of Statistics</i>, vol. 7, no. 1, pp. 1-26, 1979, doi: <link href="https://doi.org/10.1214/aos/1176344552">10.1214/aos/1176344552</link>.',
        '[35] F. Wilcoxon, "Individual comparisons by ranking methods," <i>Biometrics Bulletin</i>, vol. 1, no. 6, pp. 80-83, 1945. [Online]. Available: <link href="https://www.jstor.org/stable/3001968">JSTOR 3001968</link>.',
        '[36] S. Holm, "A simple sequentially rejective multiple test procedure," <i>Scandinavian Journal of Statistics</i>, vol. 6, no. 2, pp. 65-70, 1979. [Online]. Available: <link href="https://www.jstor.org/stable/4615733">JSTOR 4615733</link>.',
        '[37] C. Dalamagkas <i>et al.</i>, "Federated OCPP 1.6 Intrusion Detection Dataset," Zenodo, 2025, doi: <link href="https://doi.org/10.21227/v1f0-9t13">10.21227/v1f0-9t13</link>.',
    ]
    for reference in references:
        story.append(KeepTogether([Paragraph(reference, s["reference"])]))
    return story


def make_abstract(tables, include_original_supplements=True):
    if include_original_supplements:
        return "<b>Abstract</b>-" + esc(extension_abstract())
    pairs = tables["paired_comparisons"]
    positive = int((pairs.mean_difference_shap_minus_lime > 0).sum())
    significant = int(((pairs.holm_adjusted_p_all_contexts < .05) &
                       (pairs.mean_difference_shap_minus_lime > 0)).sum())
    posthoc = ("Post-hoc sign and influence checks support directional consistency. Excluding train-matching test feature patterns preserves positive explanation differences in all contexts but lowers Gotham multiclass macro-F1. "
               if include_original_supplements else "")
    return ("<b>Abstract</b>-Quantitative explanation comparisons require traceable data preparation and explicit evaluation units. We evaluate Random Forest and XGBoost with TreeSHAP and LIME using official GeNIS and Gotham 2025 releases. Class-capped, known-label cohorts use a frozen connection-group holdout and training-only preprocessing. Unknown-labelled Gotham records are excluded. GeNIS archive checksums are verified; Gotham verification covers consumed members, with its complete archive checksum unverified. Binary and multiclass classifiers are fitted over five seeds. Both explainers process 100 matched diagnostic records per context across three model seeds. The primary endpoint averages target-class probability drops over four masking budgets, weighting explained connections equally. We report paired group-bootstrap intervals and directional Wilcoxon tests, with Holm adjustment of tests across 24 explainer and 48 random-control comparisons. "
            f"TreeSHAP-minus-LIME mean differences are positive in {positive}/24 contexts and significant under the directional corrected test in {significant}/24. "
            + posthoc + "Both detectors miss all test Mirai C&amp;C records; CoAP Amplification has no test support. The contribution is a provenance-traceable, group-aware evaluation protocol. Findings concern sampled within-testbed cohorts and a specified synthetic masking procedure; they do not establish causal relevance, analyst usefulness, or deployment readiness.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest, tables = load_results(args.results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    identity = manuscript_identity()
    document, col_w, front = make_document(args.output, make_abstract(
        tables, include_original_supplements=args.results.resolve() == RESULTS.resolve()), identity)
    fonts = register_fonts()

    def embedded_font_canvas(*a, **kwargs):
        kwargs.update(initialFontName=fonts["regular"], initialFontSize=9)
        return pdf_canvas.Canvas(*a, **kwargs)

    document.build(build_story(manifest, tables, col_w, front, args.results),
                   canvasmaker=embedded_font_canvas)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
