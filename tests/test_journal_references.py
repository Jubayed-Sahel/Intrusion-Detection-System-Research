import unittest

from audit_journal_references import bibliography, context_hash, normalized


class JournalReferenceTests(unittest.TestCase):
    def source(self, cites, entries):
        return cites + r"\begin{thebibliography}{2}" + entries + r"\end{thebibliography}"

    def test_multiple_citations_and_repeated_use_preserve_first_order(self):
        source = self.source(r"A \cite{ref1,ref2}. B \cite{ref1}.",
                             r"\bibitem{ref1} First. \bibitem{ref2} Second.")
        self.assertEqual([key for key, _ in bibliography(source)], ["ref1", "ref2"])

    def test_rejects_dangling_uncited_duplicate_and_out_of_order_entries(self):
        cases = [(r"\cite{ref1,ref3}", r"\bibitem{ref1} One. \bibitem{ref2} Two."),
                 (r"\cite{ref1}", r"\bibitem{ref1} One. \bibitem{ref2} Two."),
                 (r"\cite{ref1}", r"\bibitem{ref1} One. \bibitem{ref1} Duplicate."),
                 (r"\cite{ref2,ref1}", r"\bibitem{ref1} One. \bibitem{ref2} Two.")]
        for cites, entries in cases:
            with self.subTest(cites=cites, entries=entries), self.assertRaises(ValueError):
                bibliography(self.source(cites, entries))

    def test_review_binding_changes_with_claim_but_not_uncited_author_text(self):
        original = "Claim \\cite{ref1}.\n\nAuthors."
        self.assertNotEqual(context_hash(original, "ref1"), context_hash(original.replace("Claim", "Different claim"), "ref1"))
        self.assertEqual(context_hash(original, "ref1"), context_hash(original.replace("Authors", "New authors"), "ref1"))

    def test_registry_comparison_normalizes_latex_accents(self):
        self.assertEqual(normalized(r"Manuten\c{c}\~ao"), normalized("Manutenção"))
