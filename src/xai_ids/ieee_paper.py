"""Export the verified recent-study content to the official IEEEtran class."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

import pandas as pd
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import KeepTogether, Paragraph, Table

from . import recent_paper
from . import journal_audit
from . import independent_tcp
from . import training_scale


ROOT = recent_paper.ROOT
PROJECT = ROOT / "paper" / "ieee"


def tex_escape(text):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
                    "<": r"\ensuremath{<}", ">": r"\ensuremath{>}",
                    "−": "-", "–": "--", "—": "---", "Σ": r"\ensuremath{\Sigma}"}
    return "".join(replacements.get(character, character) for character in str(text))


class Markup(HTMLParser):
    def __init__(self, citations=True):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.citations = citations

    def handle_starttag(self, tag, attrs):
        commands = {"b": r"\textbf{", "i": r"\emph{", "sub": r"\textsubscript{",
                    "super": r"\textsuperscript{"}
        if tag in commands:
            self.parts.append(commands[tag])
        elif tag == "link":
            self.parts.append(r"\href{" + dict(attrs)["href"] + "}{")
        elif tag == "br":
            self.parts.append(r"\newline{}")

    def handle_endtag(self, tag):
        if tag in {"b", "i", "sub", "super", "link"}:
            self.parts.append("}")

    def handle_data(self, data):
        for part in re.split(r"(\[\d+\])", data):
            match = re.fullmatch(r"\[(\d+)\]", part)
            self.parts.append(r"\cite{ref" + match[1] + "}" if match and self.citations
                              else tex_escape(part))


def latex(text, citations=True):
    parser = Markup(citations)
    parser.feed(str(text))
    return "".join(parser.parts)


def external_tcp_table(root):
    """Compare capture-level errors using the frozen TCP diagnostic counts."""
    pdmfc, _, _ = independent_tcp.load_independent_tcp(root)
    ocpp = pd.read_csv(root / "outputs/journal_audit_20261109/tcp_metrics.csv")
    rows = []
    for capture, metrics in (("OCPP", ocpp), ("PDMFC", pdmfc[pdmfc.subset.eq("TCP")])):
        for model, label in (("random_forest", "RF"), ("xgboost", "XGB")):
            row = metrics[metrics.feature_set.eq("transport") & metrics.model.eq(model)].iloc[0]
            cells = [f"{capture} / {label}",
                     f"{int(row.false_alarms):,} / {int(row.benign):,}",
                     f"{row.fpr:.1%}", f"{int(row.missed):,} / {int(row.attacks):,}"]
            rows.append(" & ".join(tex_escape(cell) for cell in cells) + r" \\")
    return "\n".join([
        r"\begin{table}[!t]\centering",
        r"\caption{TCP-only external transfer of protocol-and-port models}",
        r"\label{tab:external-tcp}",
        r"\footnotesize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.10}",
        r"\begin{tabular}{lrrr}\toprule",
        r"\textbf{Capture / model} & \textbf{FP / benign} & \textbf{FPR} & \textbf{FN / attacks} \\\midrule",
        *rows,
        r"\bottomrule\end{tabular}",
        r"\par\smallskip\parbox{\columnwidth}{\footnotesize FP: false positives; FN: false negatives; FPR: FP / benign. Counts describe each capture, not independent flow-level replications.}",
        r"\end{table}",
    ])


def export(results, project=PROJECT, journal=False):
    manifest, tables = recent_paper.load_results(results)
    identity = recent_paper.manuscript_identity()
    if journal:
        if results.resolve() != recent_paper.RESULTS.resolve():
            raise ValueError("The journal audit applies to the original verified benchmark")
        identity["title"] = journal_audit.TITLE
        journal_abstract, journal_paragraphs = journal_audit.manuscript_text(ROOT)
        scale_paragraphs = training_scale.manuscript_text(ROOT)
        tcp_paragraphs = independent_tcp.manuscript_text(ROOT)
    # Reuse the exact data-driven narrative, tables and bibliography. IEEEtran
    # takes responsibility for typography and page layout instead of ReportLab.
    story = recent_paper.build_story(manifest, tables, 252, [], results)
    project.mkdir(parents=True, exist_ok=True)
    (project / "figures").mkdir(exist_ok=True)
    body, references = [], []
    table_number = figure_number = 0
    for item in story:
        if isinstance(item, Paragraph):
            if item.style.name == "Section":
                if item.getPlainText() == "REFERENCES":
                    continue
                title = re.sub(r"^[IVX]+\.\s*", "", item.getPlainText()).capitalize()
                if journal and title == "Discussion and threats to validity":
                    body.extend([r"\subsection{Training-size sensitivity on unseen GeNIS scenarios}",
                                 *(latex(paragraph) for paragraph in scale_paragraphs),
                                 r"\subsection{Protocol shortcut controls and base-rate sensitivity}",
                                 *(latex(paragraph) for paragraph in journal_paragraphs),
                                 r"\subsection{Independent protocol-matched TCP transfer}",
                                 *(latex(paragraph) + "\n" for paragraph in tcp_paragraphs),
                                 external_tcp_table(ROOT),
                                 "The TCP-only comparison in Table~\\ref{tab:external-tcp} separates missed attacks "
                                 "from false alarms using the same three-field feature set. High attack recall "
                                 "coexists with near-universal alerts on benign TCP traffic in both captures. "
                                 "The capture is the replication unit; these flow counts do not establish "
                                 "precision across a population of networks.\n"])
                body.append(r"\section{" + tex_escape(title) + "}")
            elif item.style.name == "Subsection":
                title = re.sub(r"^[A-Z]\.\s*", "", item.getPlainText())
                body.append(r"\subsection{" + tex_escape(title) + "}")
            elif item.style.name == "Equation":
                body.append(r"\begin{equation} D(x,r)=\frac{1}{4}\sum_{k\in\{1,3,5,10\}} D_k(x,r).\label{eq:deletion}\end{equation}")
            else:
                content = item.text
                if journal and content.startswith("The research questions are "):
                    content = (
                        "We ask three research questions. <b>RQ1:</b> How does the paired TreeSHAP-LIME "
                        "deletion difference depend on the replacement distribution and LIME sampling "
                        "budget? <b>RQ2:</b> How does detector performance change when entire traffic "
                        "sources are held out with shared connections purged, and when training size "
                        "increases on fixed source tests? <b>RQ3:</b> Do reduced-feature classifiers "
                        "transfer beyond protocol-label associations to independently collected traffic? "
                        "The contributions are a matched, group-aware explanation evaluation with random "
                        "controls; replacement and surrogate-fit sensitivity analyses; and source-transfer "
                        "stress tests with explicit missed-attack and false-alarm counts. These studies "
                        "address different validation targets: a strong explanation ranking does not "
                        "establish detector transfer. Follow-up studies were designed after inspecting "
                        "the primary results; their protocols were fixed before their own execution, "
                        "not prospectively preregistered."
                    )
                if journal and "the separate reduced-feature OCPP experiment" in content:
                    content = content.replace(
                        "the separate reduced-feature OCPP experiment tests only binary transfer",
                        "the separate OCPP and PDMFC captures test reduced-feature binary transfer",
                    )
                if journal and content.endswith("External captures, validated traffic interventions and analyst decisions remain distinct validation targets."):
                    content = (
                        "Source holdouts expose missed attacks that aggregate scores can hide. "
                        "Increasing the GeNIS training cohort from 10,000 to 160,000 rows improves some "
                        "scenarios but does not consistently improve binary detection. The reduced-feature "
                        "detectors also flag nearly all benign TCP flows in two independent captures. "
                        "Separately, TreeSHAP leads LIME under median/mode deletion in all 24 primary "
                        "contexts, but retained-feature donor replacement weakens the GeNIS gaps. "
                        "These findings concern the evaluated detectors, captures and replacement rules. "
                        "External explanation fidelity and analyst decisions remain untested."
                    )
                if journal and content.startswith("<b>AI assistance disclosure:"):
                    content = ("<b>AI assistance disclosure:</b> OpenAI Codex assisted with source acquisition "
                               "tooling, data auditing, experiment orchestration, and manuscript drafting.")
                if journal and content.startswith("A clean rerun begins "):
                    content += (
                        ' The public <link href="https://github.com/Jubayed-Sahel/'
                        'Intrusion-Detection-System-Research/tree/dc61046">code and frozen evidence '
                        'snapshot (commit dc61046)</link> includes the supplementary index, experiment '
                        'protocols, fold-level counts and pinned requirements. Run '
                        'python verify_research_closeout.py to replay the recorded evidence without '
                        'raw datasets or fitted models. This internal replay verifies saved results; '
                        'independent retraining requires the official input files.'
                    )
                body.append(latex(content) + "\n")
        elif isinstance(item, KeepTogether):
            content = item._content
            if len(content) == 1 and isinstance(content[0], Paragraph):
                reference = content[0].text
                number = re.match(r"\[(\d+)\]", reference)[1]
                references.append(r"\bibitem{ref" + number + "} " +
                                  latex(re.sub(r"^\[\d+\]\s*", "", reference), citations=False))
            elif any(isinstance(child, Table) for child in content):
                table_number += 1
                table = next(child for child in content if isinstance(child, Table))
                caption = next(child for child in content if isinstance(child, Paragraph))
                title = re.sub(r"^TABLE [IVX]+\.\s*", "", caption.getPlainText()).capitalize()
                for term, spelling in (("treeshap", "TreeSHAP"), ("lime", "LIME"),
                                       ("ocpp", "OCPP"), ("macro-f1", "macro-F1")):
                    title = re.sub(r"\b" + term + r"\b", spelling, title, flags=re.I)
                widths = table._argW
                fractions = [width / sum(widths) for width in widths]
                columns = "".join(r">{\centering\arraybackslash}p{\dimexpr " +
                                  f"{fraction:.5f}" + r"\columnwidth-2\tabcolsep\relax}"
                                  for fraction in fractions)
                rows = []
                for index, row in enumerate(table._cellvalues):
                    cells = [latex(cell.text if isinstance(cell, Paragraph) else str(cell)) for cell in row]
                    if index == 0:
                        cells = [r"\textbf{" + cell + "}" for cell in cells]
                    rows.append(" & ".join(cells) + r" \\" + (r"\midrule" if index == 0 else ""))
                body.append("\n".join([
                    r"\begin{table}[!t]\centering", r"\caption{" + tex_escape(title) + "}",
                    r"\label{tab:" + str(table_number) + "}",
                    r"\footnotesize\setlength{\tabcolsep}{2pt}\renewcommand{\arraystretch}{1.10}",
                    r"\begin{tabular}{" + columns + r"}\toprule", *rows,
                    r"\bottomrule\end{tabular}\end{table}",
                ]))
            elif any(isinstance(child, Drawing) for child in content):
                figure_number += 1
                drawing = next(child for child in content if isinstance(child, Drawing))
                caption = next(child for child in content if isinstance(child, Paragraph))
                for child in drawing.contents:
                    if isinstance(child, String):
                        child.fontSize = max(child.fontSize, 8)
                        if child.text == "TreeSHAP minus LIME probability-drop difference":
                            child.text = "Mean probability-drop difference"
                name = f"paired-{figure_number}.pdf"
                renderPDF.drawToFile(drawing, str(project / "figures" / name))
                title = re.sub(r"^Fig\. \d+\.\s*", "", caption.text)
                body.append("\n".join([r"\begin{figure}[!t]\centering",
                    r"\includegraphics[width=\columnwidth]{figures/" + name + "}",
                    r"\caption{" + latex(title) + "}", r"\label{fig:" + str(figure_number) + "}",
                    r"\end{figure}"]))
    abstract = re.sub(r"^<b>Abstract</b>-", "", recent_paper.make_abstract(
        tables, include_original_supplements=results.resolve() == recent_paper.RESULTS.resolve()))
    if journal:
        abstract = journal_abstract
        references.append(r'\bibitem{ref38} S. Axelsson, "The base-rate fallacy and the difficulty of '
                          r'intrusion detection," \textit{ACM Trans. Inf. Syst. Secur.}, vol. 3, '
                          r'no. 3, pp. 186--205, 2000, doi: 10.1145/357830.357849.')
        references.append(r'\bibitem{ref39} Projecto Desenvolvimento Manuten\c{c}\~ao Forma\c{c}\~ao '
                          r'e Consultadoria, "PDMFC Dataset," Zenodo, ver. v1, 2025, '
                          r'doi: 10.5281/zenodo.16943481.')
    author = "Anonymous Author(s)" if identity["anonymous"] else identity["authors"]
    affiliation = "" if identity["anonymous"] else recent_paper.paper_metadata().get("affiliation", "")
    metadata = recent_paper.paper_metadata()
    supervisor = metadata.get("supervisor_name")
    acknowledgments = []
    if journal and not identity["anonymous"] and supervisor:
        acknowledgments = [
            r"\section*{Acknowledgment}",
            latex(f"The authors acknowledge {supervisor}, {metadata['supervisor_designation']}, "
                  f"{metadata['supervisor_affiliation']}, for supervising this research."),
        ]
    source = "\n".join([
        "% Generated from the verified recent-study artifacts; edit the Python narrative to regenerate.",
        r"\documentclass[journal,letterpaper]{IEEEtran}" if journal else
        r"\documentclass[conference,letterpaper]{IEEEtran}",
        r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}",
        r"\usepackage{cite,amsmath,graphicx,array,booktabs}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\hypersetup{pdftitle={" + tex_escape(identity["title"]) + "},pdfauthor={" + tex_escape(author) + "}}",
        r"\begin{document}", r"\title{" + tex_escape(identity["title"]) + "}",
        (r"\author{" + tex_escape(author) +
         (r"\thanks{" + tex_escape(affiliation) + "}" if affiliation else "") + "}") if journal else
        (r"\author{\IEEEauthorblockN{" + tex_escape(author) + "}" +
         (r"\IEEEauthorblockA{" + tex_escape(affiliation) + "}" if affiliation else "") + "}"),
        r"\maketitle", r"\begin{abstract}", latex(abstract), r"\end{abstract}",
        (r"\begin{IEEEkeywords}Explainable artificial intelligence, explanation fidelity, feature masking, intrusion detection, traffic shift.\end{IEEEkeywords}" if journal else
         r"\begin{IEEEkeywords}Intrusion detection, explainable AI, TreeSHAP, LIME, explanation fidelity, provenance, group holdout.\end{IEEEkeywords}"),
        *body, *acknowledgments, r"\begin{thebibliography}{" + str(len(references)) + "}", *references,
        r"\end{thebibliography}", r"\end{document}",
    ])
    (project / "main.tex").write_text(source, encoding="utf-8")
    return project / "main.tex"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=recent_paper.RESULTS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--journal", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    project = ROOT / "paper" / "journal" if args.journal else PROJECT
    output = args.output or (ROOT / "output/pdf/xai_ids_traffic_sources_and_feature_masking.pdf" if args.journal else recent_paper.OUTPUT)
    source = export(args.results, project, journal=args.journal)
    if args.source_only:
        print(source)
        return
    compiler = shutil.which("pdflatex")
    if not compiler:
        raise SystemExit(f"IEEEtran source saved at {source}. Compile main.tex with a LaTeX distribution or Overleaf.")
    for _ in range(2):
        run = subprocess.run([compiler, "-interaction=nonstopmode", "-halt-on-error",
                              "-no-shell-escape", "main.tex"], cwd=source.parent,
                             capture_output=True, text=True, errors="replace")
        if run.returncode:
            raise SystemExit(run.stdout[-6000:] + run.stderr[-1000:])
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source.with_suffix(".pdf"), output)
    print(output.resolve())


if __name__ == "__main__":
    main()
