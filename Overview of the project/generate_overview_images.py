"""Generate nine beginner-friendly PNG diagrams from recorded project evidence."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "outputs"

NAVY, BLUE, TEAL, GREEN = "#102A43", "#1769AA", "#00796B", "#2E7D32"
ORANGE, RED, PURPLE, GRAY = "#E67E22", "#C62828", "#6A4C93", "#52616B"
PALE_BLUE, PALE_TEAL = "#E8F3FA", "#E5F5F2"
PALE_GREEN, PALE_ORANGE = "#EAF5EA", "#FFF2E5"
PALE_RED, PALE_PURPLE, PALE_GRAY = "#FDECEC", "#F0EAF7", "#F3F6F8"
WHITE, INK = "#FFFFFF", "#17212B"


def csv_rows(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_data(name):
    with (OUT / name).open(encoding="utf-8") as handle:
        return json.load(handle)


PRED = csv_rows("predictive_metrics.csv")
PAIRED = csv_rows("paired_comparisons.csv")
CONTROLS = csv_rows("fidelity_control_tests.csv")
MANIFEST = json_data("run_manifest.json")
ALERT = json_data("alert_reports/unsw_binary_xgb_example.json")


def metric(dataset, task, model):
    values = [float(r["macro_f1"]) for r in PRED if r["dataset"] == dataset and r["task"] == task and r["model"] == model]
    return sum(values) / len(values)


def canvas(title, subtitle):
    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor(WHITE)
    ax.set_xlim(0, 160); ax.set_ylim(0, 90); ax.axis("off")
    ax.add_patch(Rectangle((0, 84), 160, 6, color=NAVY))
    ax.text(5, 86.8, title, color=WHITE, fontsize=25, weight="bold", va="center")
    ax.text(5, 81.8, subtitle, color=GRAY, fontsize=12.5, va="center")
    return fig, ax


def wrap(text, width):
    lines = []
    for paragraph in text.splitlines():
        if paragraph:
            lines.extend(textwrap.wrap(paragraph, max(12, width), break_long_words=False))
        else:
            lines.append("")
    return "\n".join(lines)


def box(ax, x, y, w, h, title, body, fill=PALE_BLUE, edge=BLUE, center=False, ts=14, bs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.7,rounding_size=1.4",
                                linewidth=2, edgecolor=edge, facecolor=fill))
    tx, ha = (x + w / 2, "center") if center else (x + 2.2, "left")
    title_text = wrap(title, int(w * 0.82))
    title_lines = title_text.count("\n") + 1
    ax.text(tx, y + h - 2.8, title_text, fontsize=ts, weight="bold", color=edge, ha=ha,
            va="top", linespacing=1.0)
    body_top = y + h - 7.1 - (title_lines - 1) * 2.5
    ax.text(tx, body_top, wrap(body, int(w * 0.95)), fontsize=bs, color=INK, ha=ha,
            va="top", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=NAVY, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18,
                                linewidth=2.1, color=color))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+1.5, label, fontsize=9.5, color=color, ha="center", weight="bold")


def step(ax, x, y, n, color):
    ax.scatter([x], [y], s=850, color=color, edgecolor=WHITE, linewidth=2.5, zorder=5)
    ax.text(x, y, str(n), color=WHITE, fontsize=15, weight="bold", ha="center", va="center", zorder=6)


def finish(fig, ax, name, note):
    ax.plot([4, 156], [4.2, 4.2], color="#D7E0E7", lw=1)
    ax.text(5, 2.1, "XAI-IDS research project | Beginner visual overview", color=GRAY, fontsize=9)
    ax.text(155, 2.1, note, color=GRAY, fontsize=8.5, ha="right")
    fig.savefig(HERE / name, dpi=160, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


def picture_01():
    fig, ax = canvas("01 | The project in one picture", "What goes in, what happens, and what a trustworthy output looks like")
    items = [
        (5, "Network traffic", "CIC-IDS2017 and UNSW-NB15 flow records", PALE_BLUE, BLUE),
        (37, "Black-box IDS", "Random Forest and XGBoost predict Normal or Attack", PALE_PURPLE, PURPLE),
        (69, "Explanations", "TreeSHAP and LIME rank influential features", PALE_ORANGE, ORANGE),
        (101, "Evidence tests", "Mask top, random, and bottom features; test stability", PALE_TEAL, TEAL),
        (133, "Human decision", "Show support, uncertainty, or review required", PALE_GREEN, GREEN),
    ]
    for i, (x, title, body, fill, edge) in enumerate(items):
        box(ax, x, 48, 22, 23, title, body, fill, edge, True, 13.5, 10.1)
        step(ax, x+11, 74.2, i+1, edge)
        if i < 4: arrow(ax, x+22.8, 59.5, x+30.1, 59.5)
    box(ax, 12, 17, 62, 20, "Research question", "Can strong intrusion detection be paired with explanations that are measurable, repeatable, and honest about uncertainty?", PALE_BLUE, BLUE, False, 16, 12)
    box(ax, 86, 17, 62, 20, "Answer", "Partly yes. TreeSHAP passed all global ranking controls, but explanations are not causal and weak local evidence still requires analyst review.", PALE_GREEN, GREEN, False, 16, 12)
    finish(fig, ax, "01-project-big-picture.png", "Start here")


def picture_02():
    fig, ax = canvas("02 | End-to-end workflow", "The complete path from raw traffic data to reproducible evidence and an IEEE paper")
    items = [
        ("Load", "Read datasets and configuration", BLUE), ("Audit", "Find duplicates, overlap, missing and infinite values", TEAL),
        ("Prepare", "Clean, encode, impute, and keep test data held out", PURPLE), ("Train", "Fit RF and XGBoost for four tasks", ORANGE),
        ("Evaluate", "Repeat five seeds and compute detection metrics", GREEN), ("Explain", "Generate TreeSHAP and LIME rankings", RED),
        ("Stress-test", "Fidelity, random controls, stability, and latency", TEAL), ("Report", "CSV/JSON evidence, notebook, figures, and IEEE PDF", NAVY),
    ]
    pos = [(7,52),(44,52),(81,52),(118,52),(118,18),(81,18),(44,18),(7,18)]
    for i, ((title, body, color), (x,y)) in enumerate(zip(items, pos)):
        box(ax, x, y, 29, 19, title, body, WHITE, color, False, 14, 10.3); step(ax, x+25.8, y+16, i+1, color)
        if i < 3: arrow(ax, x+29.8, y+9.5, pos[i+1][0]-1, y+9.5)
        elif i == 3: arrow(ax, x+14.5, y-1, x+14.5, pos[i+1][1]+20)
        elif i < 7: arrow(ax, x-1, y+9.5, pos[i+1][0]+29.8, y+9.5)
    ax.text(80, 44.2, "The model is not the end product.", ha="center", fontsize=16, weight="bold", color=NAVY)
    ax.text(80, 40.7, "A defensible claim needs clean data -> tested model -> tested explanation -> preserved evidence.", ha="center", fontsize=12, color=GRAY)
    finish(fig, ax, "02-end-to-end-workflow.png", "Follow steps 1-8")


def picture_03():
    d = MANIFEST["datasets"]["UNSW-NB15/binary"]
    fig, ax = canvas("03 | Data cleaning and leakage control", "Why repeated and overlapping flows were removed before reporting UNSW-NB15 results")
    box(ax, 7,53,32,21,"Original training",f"{d['original_training_rows']:,} rows\n\n{d['training_exact_duplicates_removed']:,} exact duplicates",PALE_BLUE,BLUE,True,15,11.3)
    arrow(ax,40,63.5,53,63.5,RED,"deduplicate")
    box(ax,54,53,32,21,"Clean training",f"{d['clean_training_rows']:,} unique rows\n\nUsed to fit the models",PALE_GREEN,GREEN,True,15,11.3)
    box(ax,7,20,32,21,"Original test",f"{d['original_testing_rows']:,} rows\n\n{d['testing_exact_duplicates_removed']:,} exact duplicates",PALE_BLUE,BLUE,True,15,11.3)
    arrow(ax,40,30.5,53,30.5,RED,"clean + compare")
    box(ax,54,20,32,21,"Clean held-out test",f"{d['clean_testing_rows']:,} rows\n\n{d['cross_partition_feature_overlaps_removed_from_test']:,} cross-partition\noverlaps removed",PALE_GREEN,GREEN,True,15,10.8)
    box(ax,99,48,52,28,"Why this matters","If the same feature vector appears in training and testing, the model can look better because it effectively saw the answer before. Removing overlap reduces this leakage risk.",PALE_RED,RED,False,17,12.2)
    box(ax,99,15,52,25,"Integrity check after cleaning","Train-test feature overlap: 0\nHeld-out test stays separate\nPreprocessing is fitted on training data only",PALE_TEAL,TEAL,False,17,12.2)
    finish(fig, ax, "03-data-cleaning-and-leakage-control.png", "Source: run_manifest.json")


def picture_04():
    p = ALERT["alert"]["predicted_probability"]
    fig, ax = canvas("04 | How the black box is explained", "We test which inputs matter to the fitted model; we do not claim real-world causation")
    box(ax,5,48,30,25,"One network flow","duration, bytes, load, packet timing, connection counts, protocol, and other measured features",PALE_BLUE,BLUE,False,16,11)
    arrow(ax,36,60.5,50,60.5,NAVY,"features")
    box(ax,51,48,34,25,"Black-box model","Random Forest or XGBoost combines many tree decisions that are hard to inspect manually.",PALE_PURPLE,PURPLE,True,16,11.2)
    arrow(ax,86,60.5,100,60.5,NAVY,"predict")
    box(ax,101,48,26,25,"Prediction",f"ATTACK\n\nProbability: {p:.1%}",PALE_RED,RED,True,16,14)
    arrow(ax,128,60.5,145,60.5,ORANGE,"explain")
    box(ax,142,48,13,25,"Why?","Which features pushed the score up or down?",PALE_ORANGE,ORANGE,True,15,9.8)
    box(ax,12,14,61,24,"TreeSHAP","Uses the fitted tree structure to assign signed feature contributions. It was fast and had stronger tested fidelity in all 8 configurations.",PALE_GREEN,GREEN,False,17,11.5)
    box(ax,87,14,61,24,"LIME","Perturbs one flow and fits a simple local surrogate. It is model-agnostic, but its sampling budget and randomness can change the ranking.",PALE_ORANGE,ORANGE,False,17,11.5)
    arrow(ax,148,47,118,39,ORANGE); arrow(ax,148,47,43,39,GREEN)
    ax.text(80,8.3,"Important: tested model-behavior evidence is not causal proof about the attacker.",ha="center",fontsize=13,color=RED,weight="bold")
    finish(fig, ax, "04-how-the-black-box-is-explained.png", "Mitigated, not eliminated")


def picture_05():
    fig, ax = canvas("05 | How explanation quality is tested", "A good-looking feature ranking is not trusted until it survives measurable controls")
    box(ax,62,36,36,18,"Candidate explanation","Ranked features for one model prediction",PALE_PURPLE,PURPLE,True,16,11)
    tests=[(6,58,"Top deletion","Mask top features. The prediction should change strongly.",BLUE,PALE_BLUE),(6,21,"Random control","Top features should beat many random feature sets.",TEAL,PALE_TEAL),(117,58,"Bottom deletion","Low-ranked features should have a smaller effect.",ORANGE,PALE_ORANGE),(117,21,"Stability","Nearby samples and repeat runs should be reasonably consistent.",GREEN,PALE_GREEN)]
    for x,y,title,body,edge,fill in tests: box(ax,x,y,37,18,title,body,fill,edge,False,15,10.5)
    arrow(ax,61,47,44,63,BLUE); arrow(ax,61,42,44,30,TEAL); arrow(ax,99,47,116,63,ORANGE); arrow(ax,99,42,116,30,GREEN)
    ax.text(80,13,"PASS only when top-ranked evidence beats controls statistically; otherwise mark the alert for review.",ha="center",fontsize=14,color=NAVY,weight="bold")
    ax.text(80,8.5,"This turns explainability from a picture into a falsifiable engineering claim.",ha="center",fontsize=12,color=GRAY)
    finish(fig, ax, "05-how-explanations-are-tested.png", "Controls prevent blind trust")


def bar(ax, y, label, value, color):
    ax.text(7,y+2,label,fontsize=10.5,color=INK,va="center")
    ax.add_patch(FancyBboxPatch((32,y),46,4,boxstyle="round,pad=0.1,rounding_size=1.5",facecolor="#E4EAF0",edgecolor="none"))
    ax.add_patch(FancyBboxPatch((32,y),max(.4,46*value),4,boxstyle="round,pad=0.1,rounding_size=1.5",facecolor=color,edgecolor="none"))
    ax.text(80,y+2,f"{value:.4f}",fontsize=10.5,weight="bold",color=color,va="center")


def picture_06():
    fig, ax = canvas("06 | Key research results", "Detection performance and explanation evidence from saved experiment outputs")
    ax.text(7,75,"Mean macro-F1 across five seeds",fontsize=17,weight="bold",color=NAVY)
    rows=[("CIC binary RF",metric("CIC-IDS2017","binary","random_forest"),BLUE),("CIC binary XGB",metric("CIC-IDS2017","binary","xgboost"),TEAL),("CIC multiclass RF",metric("CIC-IDS2017","multiclass","random_forest"),BLUE),("CIC multiclass XGB",metric("CIC-IDS2017","multiclass","xgboost"),TEAL),("UNSW binary RF",metric("UNSW-NB15","binary","random_forest"),BLUE),("UNSW binary XGB",metric("UNSW-NB15","binary","xgboost"),TEAL),("UNSW multiclass RF",metric("UNSW-NB15","multiclass","random_forest"),BLUE),("UNSW multiclass XGB",metric("UNSW-NB15","multiclass","xgboost"),TEAL)]
    for i,row in enumerate(rows): bar(ax,67-i*6.7,*row)
    wins=sum(float(r["mean_difference_shap_minus_lime"])>0 for r in PAIRED)
    sp=sum(r["explainer"]=="TreeSHAP" and float(r["holm_adjusted_p"])<=.05 for r in CONTROLS)
    lp=sum(r["explainer"]=="LIME" and float(r["holm_adjusted_p"])<=.05 for r in CONTROLS)
    diffs=[float(r["mean_difference_shap_minus_lime"]) for r in PAIRED]; ps=[float(r["holm_adjusted_p"]) for r in PAIRED]
    box(ax,96,53,56,22,"Explanation scoreboard",f"TreeSHAP higher paired fidelity: {wins}/8\nTreeSHAP random-control passes: {sp}/8\nLIME random-control passes: {lp}/8",PALE_GREEN,GREEN,False,17,12.5)
    box(ax,96,26,56,20,"Strength of paired evidence",f"Mean TreeSHAP-LIME lift: {min(diffs):.3f} to {max(diffs):.3f}\nLargest adjusted paired p: {max(ps):.4f}",PALE_TEAL,TEAL,False,17,12.2)
    box(ax,96,8,56,12,"Interpretation","TreeSHAP is the stronger default; UNSW multiclass remains the hardest task.",PALE_ORANGE,ORANGE,False,15,10.8)
    finish(fig, ax, "06-key-research-results.png", "Values read from outputs/*.csv")


def picture_07():
    p=ALERT["alert"]["predicted_probability"]; local=ALERT["local_fidelity_evidence"]; glob=ALERT["benchmark_validation_context"]
    fig, ax = canvas("07 | From model alert to human decision", "A gate stops a confident prediction from being confused with a trustworthy local explanation")
    items=[(5,"Model alert",f"Attack\nProbability: {p:.1%}",RED,PALE_RED),(42,"Global check",f"Random control passed\nAdjusted p = {glob['global_holm_adjusted_p']:.4f}",GREEN,PALE_GREEN),(79,"Local check",f"Top-random lift = {local['top_minus_random_lift']:.3f}\nLocal p = {local['local_empirical_one_sided_p']:.3f}",ORANGE,PALE_ORANGE),(116,"Evidence tier","REVIEW REQUIRED\nLocal test did not clear\np <= 0.05",ORANGE,PALE_ORANGE)]
    for i,(x,title,body,edge,fill) in enumerate(items):
        box(ax,x,48,31,24,title,body,fill,edge,True,15,11.2); step(ax,x+27.5,73.5,i+1,edge)
        if i<3: arrow(ax,x+31.8,60,items[i+1][0]-1,60)
    box(ax,11,16,41,21,"SUPPORTED","Global controls pass and this alert's\ntop features beat its random test.",PALE_GREEN,GREEN,True,16,10.4)
    box(ax,60,16,41,21,"REVIEW REQUIRED","Global explainer is credible, but this\nindividual alert has uncertain evidence.",PALE_ORANGE,ORANGE,True,16,10.4)
    box(ax,109,16,41,21,"UNSUPPORTED","The explainer fails globally. Do not\npresent the ranking as validated.",PALE_RED,RED,True,16,10.4)
    finish(fig, ax, "07-alert-evidence-decision.png", "Real example alert")


def picture_08():
    fig, ax = canvas("08 | How the research paper was built", "Every important statement should trace to a question, method, and saved output")
    items=[("Purpose + literature","Define problem, gap, and research questions",BLUE,PALE_BLUE),("Experiment contract","Lock data, cleaning, models, seeds, metrics, and tests",PURPLE,PALE_PURPLE),("Machine evidence","Save CSV, JSON, manifest, figures, and model artifacts",TEAL,PALE_TEAL),("Statistical claims","Report means, intervals, tests, controls, and limits",GREEN,PALE_GREEN),("IEEE manuscript","Write abstract, methods, results, discussion, and references",NAVY,PALE_GRAY)]
    xs=[4,35,66,97,128]
    for i,((title,body,edge,fill),x) in enumerate(zip(items,xs)):
        box(ax,x,45,27,28,title,body,fill,edge,True,12.2,9.8); step(ax,x+13.5,76.1,i+1,edge)
        if i<4: arrow(ax,x+27.8,59,xs[i+1]-1,59)
    box(ax,12,15,62,20,"Claim rule","If a number or conclusion cannot be traced to an output file and documented method, it does not belong in Results.",PALE_RED,RED,False,16,11.8)
    box(ax,86,15,62,20,"Publication rule","The paper is a strong research draft, not automatic acceptance. External validation and peer review still matter.",PALE_ORANGE,ORANGE,False,16,11.8)
    finish(fig, ax, "08-how-the-paper-was-built.png", "Evidence first, prose second")


def picture_09():
    fig, ax = canvas("09 | What is solved, what is not, and what comes next", "Clear boundaries improve credibility and prevent overclaiming")
    box(ax,6,45,46,30,"What is solved","- Reproducible IDS benchmarking\n- Duplicate and overlap controls\n- TreeSHAP and LIME explanations\n- Fidelity, random, stability, latency tests\n- Evidence-gated alert reports",PALE_GREEN,GREEN,False,18,12)
    box(ax,57,45,46,30,"What is not solved","- Causal attribution to an attacker\n- Every type of dataset shift\n- Trust in every local explanation\n- Live-network validation\n- Human analyst usability",PALE_RED,RED,False,18,12)
    box(ax,108,45,46,30,"Best next steps","- Test a newer external dataset\n- Add temporal or site-level splits\n- Run analyst usability studies\n- Calibrate thresholds prospectively\n- Compare more explainers",PALE_BLUE,BLUE,False,18,12)
    ax.text(80,33,"Correct conclusion",fontsize=19,weight="bold",color=NAVY,ha="center")
    ax.text(80,26,"The black-box problem is mitigated with tested, scoped evidence. It is not eliminated,\nbecause feature attribution explains model behavior - not real-world causation.",fontsize=15,color=INK,ha="center",va="center",linespacing=1.45)
    ax.add_patch(FancyBboxPatch((27,12),106,7,boxstyle="round,pad=0.5,rounding_size=2",facecolor=NAVY,edgecolor=NAVY))
    ax.text(80,15.5,"This honest boundary is a strength of the paper, not a weakness.",color=WHITE,fontsize=14,weight="bold",ha="center",va="center")
    finish(fig, ax, "09-limitations-and-next-steps.png", "Scope claims carefully")


def main():
    pictures=[picture_01,picture_02,picture_03,picture_04,picture_05,picture_06,picture_07,picture_08,picture_09]
    for make in pictures: make()
    print(f"Created {len(pictures)} images in {HERE}")


if __name__ == "__main__": main()
