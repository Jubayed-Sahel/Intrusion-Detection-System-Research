"""Export the verified recent-study content to the official IEEEtran class."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import KeepTogether, Paragraph, Table

from . import recent_paper


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


def export(results, project=PROJECT):
    manifest, tables = recent_paper.load_results(results)
    identity = recent_paper.manuscript_identity()
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
                body.append(r"\section{" + tex_escape(title) + "}")
            elif item.style.name == "Subsection":
                title = re.sub(r"^[A-Z]\.\s*", "", item.getPlainText())
                body.append(r"\subsection{" + tex_escape(title) + "}")
            elif item.style.name == "Equation":
                body.append(r"\begin{equation} D(x,r)=\frac{1}{4}\sum_{k\in\{1,3,5,10\}} D_k(x,r).\label{eq:deletion}\end{equation}")
            else:
                body.append(latex(item.text) + "\n")
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
    abstract = re.sub(r"^<b>Abstract</b>-", "", recent_paper.make_abstract(tables))
    author = "Anonymous Author(s)" if identity["anonymous"] else identity["authors"]
    affiliation = "" if identity["anonymous"] else recent_paper.paper_metadata().get("affiliation", "")
    source = "\n".join([
        "% Generated from the verified recent-study artifacts; edit the Python narrative to regenerate.",
        r"\documentclass[conference,letterpaper]{IEEEtran}",
        r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}",
        r"\usepackage{cite,amsmath,graphicx,array,booktabs}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\hypersetup{pdftitle={" + tex_escape(identity["title"]) + "},pdfauthor={" + tex_escape(author) + "}}",
        r"\begin{document}", r"\title{" + tex_escape(identity["title"]) + "}",
        r"\author{\IEEEauthorblockN{" + tex_escape(author) + "}" +
        (r"\IEEEauthorblockA{" + tex_escape(affiliation) + "}" if affiliation else "") + "}",
        r"\maketitle", r"\begin{abstract}", latex(abstract), r"\end{abstract}",
        r"\begin{IEEEkeywords}Intrusion detection, explainable AI, TreeSHAP, LIME, explanation fidelity, provenance, group holdout.\end{IEEEkeywords}",
        *body, r"\begin{thebibliography}{20}", *references,
        r"\end{thebibliography}", r"\end{document}",
    ])
    (project / "main.tex").write_text(source, encoding="utf-8")
    return project / "main.tex"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=recent_paper.RESULTS)
    parser.add_argument("--output", type=Path, default=recent_paper.OUTPUT)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    source = export(args.results)
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source.with_suffix(".pdf"), args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
