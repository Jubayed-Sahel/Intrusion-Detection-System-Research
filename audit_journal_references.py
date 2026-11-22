"""Audit the retained journal bibliography and optionally refresh DOI identities.

Identity, citation coverage and title agreement are machine checks. Scientific
claim support requires the separately recorded source reading; no similarity or
AI-detector score is inferred by this script.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata

from pypdf import PdfReader
from verify_references import dois_from, resolve, fetch_json

ROOT = Path(__file__).resolve().parent
DIRECTORY = ROOT / "outputs/reference_audit_20261123"


def plain(text):
    text = re.sub(r"\\(?:c|['`^~\"])(?:\{([A-Za-z])\}|([A-Za-z]))",
                  lambda m: m[1] or m[2], text)
    text = re.sub(r"\\(?:emph|textit|textbf)\{([^}]+)\}", r"\1", text)
    return text


def normalized(text):
    text = text.translate(str.maketrans({"ø": "o", "Ø": "O", "ł": "l", "Ł": "L"}))
    text = unicodedata.normalize("NFKD", plain(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def bibliography(source):
    entries = re.findall(r"\\bibitem\{(ref\d+)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})",
                         source, flags=re.S)
    keys = [key for key, _ in entries]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate bibliography labels")
    body = source.split(r"\begin{thebibliography}")[0]
    cited = list(dict.fromkeys(key.strip() for group in re.findall(r"\\cite\{([^}]+)\}", body)
                               for key in group.split(",")))
    if keys != cited or keys != [f"ref{i}" for i in range(1, len(keys) + 1)]:
        raise ValueError("Undefined, uncited, noncontiguous or out-of-order references")
    return entries


def context_hash(source, key):
    body = source.split(r"\begin{thebibliography}")[0]
    paragraphs = [part for part in body.split("\n\n") if any(
        key in [item.strip() for item in group.split(",")]
        for group in re.findall(r"\\cite\{([^}]+)\}", part))]
    return hashlib.sha256("\n\n".join(paragraphs).encode("utf-8")).hexdigest()


def refresh_record(item):
    key, entry = item
    dois = dois_from(entry.replace("}{", " ").replace("}", " "))
    doi = dois[0] if dois else None
    if not doi:
        return dict(key=key, status="non_doi_source", entry=entry.strip(),
                    urls=re.findall(r"\\href\{([^}]+)\}", entry))
    try:
        for attempt in range(3):
            try:
                record = resolve(doi)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if key == "ref38":
            registered = fetch_json("https://api.crossref.org/works/" + doi)["message"]
            record["publisher_abstract"] = registered.get("abstract")
        title = record["title"][0]
        title = title["title"] if isinstance(title, dict) else title
        subtitle = record.get("subtitle") or []
        full_title = ": ".join([title, *subtitle])
        match = normalized(full_title) in normalized(entry)
        authors = record.get("authors") or []
        authors = authors[:1] if r"\emph{et al.}" in entry else authors
        names = [author.get("family") or author.get("familyName") or
                 author.get("name", "").split(",")[0] for author in authors]
        author_match = bool(names) and all(normalized(name) in normalized(entry) for name in names)
        volume = record.get("volume")
        volume_match = not volume or bool(re.search(r"vol\.\s*" + re.escape(str(volume)) + r"\b", entry))
        pages = record.get("page") or record.get("article_number")
        page_match = not pages or normalized(str(pages)) in normalized(entry)
        identity_match = match and author_match and volume_match and page_match
        return dict(key=key, status="verified" if identity_match else "identity_mismatch",
                    title_match=match, listed_author_surnames_match=author_match,
                    volume_match=volume_match, page_or_article_match=page_match,
                    entry=entry.strip(), registered_title=full_title, metadata=record)
    except Exception as exc:
        return dict(key=key, status="unresolved", doi=doi, error=str(exc), entry=entry.strip())


def scan_overlap(source, minimum_words=12):
    """Flag literal runs against available local PDFs; do not assign a plagiarism score."""
    body = source.split(r"\begin{thebibliography}")[0].split(r"\maketitle", 1)[1]
    body = re.sub(r"\\begin\{tabular\}.*?\\end\{tabular\}", " ", body, flags=re.S)
    body = re.sub(r"\\(?:cite|label|ref)\{[^}]+\}", " ", body)
    body = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", " ", plain(body))

    def words(text):
        text = re.sub(r"(?<=\w)-\s*\n(?=\w)", "", text)
        return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())

    tokens = words(body)
    grams = {tuple(tokens[i:i + minimum_words]) for i in range(len(tokens) - minimum_words + 1)}
    checked, flags = [], []
    for path in sorted((ROOT / "data/reference_papers").rglob("*.pdf")):
        reader = PdfReader(path)
        matches = []
        text_pages = 0
        for page_number, page in enumerate(reader.pages, 1):
            source_words = words(page.extract_text() or "")
            text_pages += int(len(source_words) >= minimum_words)
            for index in range(len(source_words) - minimum_words + 1):
                phrase = tuple(source_words[index:index + minimum_words])
                if phrase in grams:
                    matches.append((page_number, phrase))
        checked.append(dict(path=path.relative_to(ROOT).as_posix(),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pages=len(reader.pages),
                            pages_with_at_least_12_extracted_words=text_pages))
        if matches:
            flags.append(dict(path=path.relative_to(ROOT).as_posix(), matching_windows=len(matches),
                              first_pdf_page=matches[0][0], first_excerpt=" ".join(matches[0][1])))
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  normalized_source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
                  prose_tokens_sha256=hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest(),
                  scope="Literal 12-word windows against machine-readable text in local reference PDFs only; bibliography and tables excluded",
                  limitations="No OCR of image-only pages. Not Turnitin/iThenticate, not an AI detector, not a global similarity percentage; neither absence nor presence proves plagiarism",
                  minimum_words=minimum_words, source_files=checked, flags=flags)
    (DIRECTORY / "local_overlap.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Local overlap screening: {len(checked)} PDFs; {len(flags)} source files flagged for manual review.")


def audit(refresh=False, overlap=False):
    source_path = ROOT / "paper/journal/main.tex"
    source = source_path.read_text(encoding="utf-8")
    entries = bibliography(source)
    pdf = ROOT / "output/pdf/xai_ids_traffic_sources_and_feature_masking.pdf"
    reader = PdfReader(pdf)
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    pdf_body = pdf_text.rsplit("REFERENCES", 1)[0]
    for key, _ in entries:
        number = key[3:]
        if not re.search(r"\[" + number + r"\]", pdf_body):
            raise ValueError(f"Reference {number} missing from PDF body")
    if re.search(r"\?\?|undefined", pdf_text, flags=re.I):
        raise ValueError("Unresolved PDF text or citation")
    report = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Citation structure and bibliographic identity; not plagiarism clearance or author approval",
                  bibliography_count=len(entries), all_cited=True, first_citation_order=True,
                  pdf_citation_presence=True,
                  source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if refresh:
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = list(pool.map(refresh_record, entries))
        path = DIRECTORY / "live_metadata.json"
        path.write_text(json.dumps(dict(checked_at_utc=report["checked_at_utc"], records=records),
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        path = DIRECTORY / "live_metadata.json"
        records = json.loads(path.read_text(encoding="utf-8"))["records"] if path.exists() else []
    if not records or [(item["key"], item["entry"]) for item in records] != [
            (key, entry.strip()) for key, entry in entries]:
        raise ValueError("Missing or stale bibliography identity records; run --refresh")
    report["doi_records"] = sum("metadata" in item or "doi" in item for item in records)
    report["verified_doi_titles"] = sum(item.get("title_match", False) for item in records)
    report["verified_doi_identities"] = sum(item["status"] == "verified" for item in records)
    report["non_doi_entries"] = sum(item["status"] == "non_doi_source" for item in records)
    failures = [dict(key=item["key"], status=item["status"], detail=item.get("error", item.get("registered_title")))
                for item in records if item["status"] not in ("verified", "non_doi_source")]
    report["identity_exceptions"] = failures
    claim_path = DIRECTORY / "claim_review.json"
    if claim_path.exists():
        claims = json.loads(claim_path.read_text(encoding="utf-8"))["records"]
        if [item["key"] for item in claims] != [key for key, _ in entries]:
            raise ValueError("Claim review does not cover the current bibliography")
        for item in claims:
            if item.get("citation_context_sha256") != context_hash(source, item["key"]):
                raise ValueError(f"Claim context needs renewed review: {item['key']}")
            local = ROOT / item.get("local_source", "missing-local-source")
            if local.is_file() and hashlib.sha256(local.read_bytes()).hexdigest() != item["local_sha256"]:
                raise ValueError(f"Reviewed source changed: {local}")
        report["claim_reviews"] = len(claims)
        report["claim_review_scope"] = "Targeted reading with explicit source-access limits; see claim_review.json"
    (DIRECTORY / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit("Resolve or document bibliographic identity exceptions")
    if overlap:
        scan_overlap(source)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch current Crossref/DataCite records")
    parser.add_argument("--scan-overlap", action="store_true", help="Screen literal prose overlap against local reference PDFs")
    args = parser.parse_args()
    audit(args.refresh, args.scan_overlap)
