"""Fetch DOI registration metadata; this checks identity, not claim support."""
import json
import re
import time
import urllib.request
from pathlib import Path


def main():
    text = Path("src/xai_ids/paper.py").read_text(encoding="utf-8")
    doi_values = re.findall(r'doi: (10\.[^\s"\\]+)', text)
    records = []
    for doi in doi_values:
        doi = doi.rstrip(".")
        try:
            request = urllib.request.Request("https://api.crossref.org/works/" + doi,
                                             headers={"User-Agent": "IDS-XAI-research-reference-audit/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                metadata = json.load(response)["message"]
            records.append({"doi": doi, "status": "resolved", "title": metadata.get("title"),
                            "authors": metadata.get("author"), "published": metadata.get("published"),
                            "venue": metadata.get("container-title"), "volume": metadata.get("volume"),
                            "page": metadata.get("page"), "article_number": metadata.get("article-number"),
                            "url": metadata.get("URL")})
        except Exception as exc:
            records.append({"doi": doi, "status": "unresolved", "error": str(exc)})
        print(doi, records[-1]["status"], flush=True)
        time.sleep(0.2)
    output = Path("outputs/research_validation/reference_metadata.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
