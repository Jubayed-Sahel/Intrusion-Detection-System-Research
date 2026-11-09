"""Verify the November manuscripts and review record without network or raw data."""
from pathlib import Path
from html import unescape
import ast
import hashlib
import json
import re
import unicodedata
from zipfile import ZipFile
from pypdf import PdfReader
from verify_references import audit_citation_structure, dois_from

ROOT = Path(__file__).resolve().parent


def normalized(value):
    plain = re.sub(r"<[^>]+>", "", unescape(value))
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", plain).encode("ascii", "ignore").decode().lower())


def pdf_checks(path, max_pages, anonymous=False):
    reader = PdfReader(path)
    assert len(reader.pages) <= max_pages
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert all((page.extract_text() or "").strip() for page in reader.pages)
    font_count = 0
    for page in reader.pages:
        for ref in page.get("/Resources", {}).get("/Font", {}).values():
            font = ref.get_object()
            assert font.get("/Subtype") != "/Type3"
            if font.get("/DescendantFonts"):
                font = font["/DescendantFonts"][0].get_object()
            descriptor = font.get("/FontDescriptor")
            assert descriptor is not None
            descriptor = descriptor.get_object()
            assert any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))
            font_count += 1
    if anonymous:
        for name in ("Jubayed", "Nafiul", "Shadman", "Jubayed-Sahel", "github.com"):
            assert name not in text
        assert not reader.metadata.get("/Author")
    return dict(pages=len(reader.pages), searchable=True, embedded_fonts=True, type3_fonts=0,
                font_references_checked=font_count, anonymous=anonymous,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def citation_keys(source):
    cited = dict.fromkeys(key for block in re.findall(r"\\cite\{([^}]+)\}", source)
                          for key in block.split(","))
    assert list(cited) == re.findall(r"\\bibitem\{([^}]+)\}", source)
    return list(cited)


def review_archive_checks():
    with ZipFile(ROOT / "output/ids_xai_anonymous_review.zip") as archive:
        hashes = json.loads(archive.read("SHA256.json"))
        assert sorted(archive.namelist()) == sorted([*hashes, "SHA256.json"])
        for name, digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        for member, path in {
            "latex/main.tex": "paper/conference/main.tex",
            "latex/figures/mask_sensitivity.pdf": "paper/conference/figures/mask_sensitivity.pdf",
            "manuscript.pdf": "output/pdf/xai_ids_conference_review.pdf",
        }.items():
            assert archive.read(member) == (ROOT / path).read_bytes(), member
        return len(hashes)


def main():
    structure = audit_citation_structure(ROOT / "src/xai_ids/recent_paper.py")
    assert structure["references"] == 37 and structure["doi_count"] == 21
    tree = ast.parse((ROOT / "src/xai_ids/recent_paper.py").read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
                any(isinstance(v, ast.Name) and v.id == "references" for v in n.targets))
    refs = ast.literal_eval(node.value)
    metadata = json.loads((ROOT / "outputs/recent2025/reference_metadata.json").read_text())
    assert len(metadata) == 21 and all(item["status"] == "resolved" for item in metadata)
    assert set(item["doi"] for item in metadata) == set(dois_from("\n".join(refs)))
    checked = []
    for item in metadata:
        title = item["title"][0]
        if isinstance(title, dict):
            title = title["title"]
        reference = next(ref for ref in refs if item["doi"] in ref)
        assert normalized(title) in normalized(reference), (item["doi"], title)
        checked.append(dict(doi=item["doi"], registered_title=title, title_present=True))
    review = json.loads((ROOT / "literature_review_20261107.json").read_text(encoding="utf-8"))
    papers = review["papers"]
    assert len(papers) == 20 and len({p["id"] for p in papers}) == 20
    assert all(p.get("read") and p.get("finding") and p.get("decision") for p in papers)
    ledger = json.loads((ROOT / "outputs/literature_review_20261107/acquisition.json").read_text())
    acquired = [record for record in ledger["records"] if record["status"] == "acquired"]
    assert len(acquired) == 18
    local_checked = 0
    for record in acquired:
        path = ROOT / record["path"]
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
            local_checked += 1
    conference = (ROOT / "paper/conference/main.tex").read_text(encoding="utf-8")
    cited = citation_keys(conference)
    journal = (ROOT / "paper/journal/main.tex").read_text(encoding="utf-8")
    journal_refs = citation_keys(journal)
    assert len(journal_refs) == 39
    assert r"\documentclass[journal,letterpaper]{IEEEtran}" in journal
    journal_pdf = ROOT / "output/pdf/xai_ids_tdsc_draft.pdf"
    journal_text = " ".join(page.extract_text() or "" for page in PdfReader(journal_pdf).pages)
    assert "Stress Testing Explainable Intrusion Detection" in journal_text
    assert "Training-size sensitivity on unseen GeNIS scenarios" in journal_text
    assert "Independent protocol-matched TCP transfer" in journal_text
    assert normalized("External explanation fidelity and analyst decisions remain untested.") in normalized(journal_text)
    assert re.search(r"161\s+of\s+162", journal_text)
    result = dict(checked_date="2026-11-09", scope="Local consistency and formatting; not author approval or venue certification",
        citation_structure=structure, resolved_doi_titles=checked,
        additional_full_text_reviews=20, local_acquired_pdfs=18, local_pdf_hashes_rechecked=local_checked,
        full_report=pdf_checks(ROOT / "output/pdf/xai_ids_recent2025_paper.pdf", 12),
        conference_report=pdf_checks(ROOT / "output/pdf/xai_ids_conference_review.pdf", 6, anonymous=True),
        journal_report=pdf_checks(journal_pdf, 12),
        conference_references=len(cited), journal_references=len(journal_refs),
        review_archive_members_verified=review_archive_checks())
    output = ROOT / "outputs/literature_review_20261107/manuscript_validation.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("additional_full_text_reviews", "citation_structure",
                                             "conference_references", "journal_references")}, indent=2))
    print("All three manuscripts: searchable text, embedded fonts, no Type 3 fonts; conference identity removed.")


if __name__ == "__main__":
    main()
