"""Fetch DOI registration metadata; this checks identity, not claim support."""
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
        "authors": metadata.get("author"),
        "published": metadata.get("published"),
        "venue": metadata.get("container-title"),
        "volume": metadata.get("volume"),
        "page": metadata.get("page"),
        "article_number": metadata.get("article-number"),
        "url": metadata.get("URL"),
    }


def main():
    for source, output in SOURCES:
        text = source.read_text(encoding="utf-8")
        records = []
        for doi in dois_from(text):
            try:
                records.append(resolve(doi))
            except Exception as exc:
                records.append({"doi": doi, "status": "unresolved", "error": str(exc)})
            print(source.name, doi, records[-1]["status"], flush=True)
            time.sleep(0.2)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
