import re
import unittest
from pathlib import Path

from build_conference_paper import bibliography


class ConferencePaperTests(unittest.TestCase):
    def test_statistical_citations_resolve_by_identity_after_full_paper_renumbering(self):
        # Regression: new related-work citations once silently changed these
        # numeric imports into unrelated IDS papers.
        bib = bibliography()
        expected = {"covert": "Explaining by removing", "efron": "Bootstrap methods",
                    "wilcoxon": "Individual comparisons by ranking methods",
                    "holm": "A simple sequentially rejective multiple test procedure"}
        for key, title in expected.items():
            self.assertIn(title.casefold(), bib[key].casefold())

    def test_review_source_is_anonymous_and_has_complete_first_use_bibliography(self):
        source = Path("paper/conference/main.tex").read_text(encoding="utf-8")
        for name in ("Jubayed", "Nafiul", "Shadman", "Jubayed-Sahel", "github.com"):
            self.assertNotIn(name, source)
        self.assertIn("pdfauthor={}", source)
        cited = []
        for block in re.findall(r"\\cite\{([^}]+)\}", source):
            for key in block.split(","):
                if key not in cited:
                    cited.append(key)
        self.assertEqual(cited, re.findall(r"\\bibitem\{([^}]+)\}", source))
        self.assertIn("post-hoc", source)
        self.assertIn("whole-archive MD5", source)


if __name__ == "__main__":
    unittest.main()
