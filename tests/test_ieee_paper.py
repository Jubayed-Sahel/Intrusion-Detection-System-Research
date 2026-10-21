import re
import unittest
from pathlib import Path

from src.xai_ids.ieee_paper import latex


class IeeePaperTests(unittest.TestCase):
    def test_markup_preserves_citations_and_escapes_scientific_text(self):
        text = latex('<b>95% CI</b>: x_1 &gt; 0 [20]; <i>p</i> &lt; .05')
        self.assertIn(r'\textbf{95\% CI}', text)
        self.assertIn(r'x\_1', text)
        self.assertIn(r'\cite{ref20}', text)
        self.assertIn(r'\ensuremath{>}', text)
        self.assertIn(r'\emph{p}', text)

    def test_editable_source_uses_ieee_class_and_preserves_all_artifacts(self):
        source = Path('paper/ieee/main.tex').read_text(encoding='utf-8')
        self.assertIn(r'\documentclass[conference,letterpaper]{IEEEtran}', source)
        self.assertNotIn(r'\usepackage{geometry}', source)
        self.assertNotIn(r'\fontsize', source)
        self.assertEqual(re.findall(r'\\bibitem\{ref(\d+)\}', source), [str(i) for i in range(1, 21)])
        self.assertEqual(set(re.findall(r'\\cite\{ref(\d+)\}', source)), {str(i) for i in range(1, 21)})
        self.assertEqual(source.count(r'\begin{table}'), 10)
        self.assertEqual(source.count(r'\begin{figure}'), 2)
        abstract = source.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
        self.assertLessEqual(len(abstract.split()), 250)
