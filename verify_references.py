"""Fetch DOI registration metadata; this checks identity, not claim support."""
import argparse
import ast
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


SOURCES = (
    (Path("src/xai_ids/paper.py"), Path("outputs/research_validation/reference_metadata.json")),
    (Path("src/xai_ids/recent_paper.py"), Path("outputs/recent2025/reference_metadata.json")),
)


def dois_from(text):
    found = []
    for match in re.findall(r"(?:doi:\s*|https://doi.org/)(10\.\d+/[^\s\"'<>]+)", text, flags=re.I):
        doi = match.replace("</link>", "").rstrip(".,);")
        if doi not in found:
            found.append(doi)
    return found


def audit_citation_structure(source):
    """Check literal manuscript citations, including references without DOIs."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    lists = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "references"
                     for target in node.targets)]
    if len(lists) != 1:
        raise ValueError("Expected one explicit bibliography list")
    references = ast.literal_eval(lists[0].value)
    ids = []
    for reference in references:
        match = re.match(r"\[(\d+)\] ", reference)
        if not match:
            raise ValueError("Bibliography entry lacks a numbered label")
        ids.append(int(match[1]))
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("Bibliography labels must be unique and contiguous")
    calls = sorted((node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "para"),
                   key=lambda node: (node.lineno, node.col_offset))
    first = []
    for call in calls:
        for argument in call.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                parts = [argument.value]
            elif isinstance(argument, ast.JoinedStr):
                parts = [item.value for item in argument.values if isinstance(item, ast.Constant)
                         and isinstance(item.value, str)]
            else:
                continue
            for part in parts:
                for match in re.finditer(r"\[(\d+)\]", part):
                    value = int(match[1])
                    if value not in first:
                        first.append(value)
    if set(first) != set(ids):
        raise ValueError("Uncited bibliography entries or undefined citations")
    if first != ids:
        raise ValueError("References must be numbered in first-citation order")
    return {"references": len(references), "first_citation_order": first,
            "doi_count": len(dois_from("\n".join(references)))}


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "IDS-XAI-research-reference-audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def resolve(doi):
    if doi.lower().startswith("10.5281/") or doi.lower().startswith("10.48550/"):
        payload = fetch_json("https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe=""))
        attributes = payload["data"]["attributes"]
        return {
            "doi": doi,
            "registry": "datacite",
            "status": "resolved",
            "title": attributes.get("titles"),
            "authors": attributes.get("creators"),
            "published": attributes.get("published"),
            "url": attributes.get("url"),
        }
    metadata = fetch_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
    return {
        "doi": doi,
        "registry": "crossref",
        "status": "resolved",
        "title": metadata.get("title"),
        "subtitle": metadata.get("subtitle"),
        "authors": metadata.get("author"),
        "published": metadata.get("published"),
        "venue": metadata.get("container-title"),
        "volume": metadata.get("volume"),
        "page": metadata.get("page"),
        "article_number": metadata.get("article-number"),
        "url": metadata.get("URL"),
    }


def main(offline=False):
    audit = audit_citation_structure(Path("src/xai_ids/recent_paper.py"))
    print("Current manuscript citation structure:", json.dumps(audit), flush=True)
    if offline:
        return
    unresolved = []
    for source, output in SOURCES:
        text = source.read_text(encoding="utf-8")
        records = []
        for doi in dois_from(text):
            try:
                records.append(resolve(doi))
            except Exception as exc:
                records.append({"doi": doi, "status": "unresolved", "error": str(exc)})
                unresolved.append(doi)
            print(source.name, doi, records[-1]["status"], flush=True)
            time.sleep(0.2)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, indent=2), encoding="utf-8")
    if unresolved:
        raise SystemExit("Unresolved DOI records: " + ", ".join(unresolved))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Check citation numbering and coverage without network access.")
    main(parser.parse_args().offline)
