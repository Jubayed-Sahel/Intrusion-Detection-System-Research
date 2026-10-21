import unittest
from pathlib import Path
from unittest.mock import patch

from verify_references import audit_citation_structure, dois_from


class ReferenceTests(unittest.TestCase):
    def test_current_paper_has_ordered_complete_citations(self):
        result = audit_citation_structure(Path("src/xai_ids/recent_paper.py"))
        self.assertEqual(result["references"], 20)
        self.assertEqual(result["doi_count"], 14)

    def test_rejects_wrong_order_missing_and_duplicate_references(self):
        examples = [
            'para("First [2], then [1].")\nreferences=["[1] First", "[2] Second"]',
            'para("Only [1].")\nreferences=["[1] First", "[2] Second"]',
            'para("Unknown [3].")\nreferences=["[1] First"]',
            'para("One [1].")\nreferences=["[1] First", "[1] Duplicate"]',
        ]
        for example in examples:
            with self.subTest(example=example), patch.object(Path, "read_text", return_value=example):
                with self.assertRaises(ValueError):
                    audit_citation_structure(Path("paper.py"))

    def test_extracts_unique_dois_without_markup(self):
        self.assertEqual(dois_from('doi: 10.1234/example. <link href="https://doi.org/10.1234/example">x</link>'),
                         ["10.1234/example"])
