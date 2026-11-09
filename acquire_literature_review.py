"""Acquire open primary papers for the November review; PDFs stay ignored.

This is a focused narrative review, not a systematic-review search protocol.
The acquisition ledger records bytes actually obtained, not reading completion.
"""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone

PAPERS = {
    "kalakoti2025": "https://arxiv.org/pdf/2506.07882v1",
    "kumar2024": "https://arxiv.org/pdf/2408.14040v1",
    "forensic2025": "https://publica-rest.fraunhofer.de/server/api/core/bitstreams/9e8bfb7e-97a6-4b25-ab78-4d28d87b9904/content",
    "versatile2025": "https://link.springer.com/content/pdf/10.1007/s12243-025-01118-9.pdf",
    "lxaids2025": "https://arxiv.org/pdf/2508.17244v1",
    "arp2022": "https://www.usenix.org/system/files/sec22-arp.pdf",
    "tesseract2019": "https://www.usenix.org/system/files/sec19-pendlebury.pdf",
    "engelen2021": "https://intrusion-detection.distrinet-research.be/WTMC2021/Resources/wtmc2021_Engelen_Troubleshooting.pdf",
    "slack2020": "https://arxiv.org/pdf/1911.02508",
    "hase2021": "https://arxiv.org/pdf/2106.00786",
    "road2022": "https://arxiv.org/pdf/2202.00449",
    "openxai2022": "https://papers.neurips.cc/paper_files/paper/2022/file/65398a0eba88c9b4a1c38ae405b125ef-Paper-Datasets_and_Benchmarks.pdf",
    "quantus2023": "https://jmlr.org/papers/volume24/22-0142/22-0142.pdf",
    "sundararajan2020": "https://proceedings.mlr.press/v119/sundararajan20b/sundararajan20b.pdf",
    "aas2021": "https://martinjullum.com/publication/aas-2021-explaining/aas-2021-explaining.pdf",
    "hooker2019": "https://papers.neurips.cc/paper/9167-a-benchmark-for-interpretability-methods-in-deep-neural-networks.pdf",
    "krishna2022": "https://arxiv.org/pdf/2202.01602v1",
    "alvarez2018": "https://arxiv.org/pdf/1806.08049",
    "rudin2019": "https://arxiv.org/pdf/1811.10154",
    "anchors2018": "https://homes.cs.washington.edu/~marcotcr/aaai18.pdf",
}


def main():
    root = Path("data/reference_papers/review_20261107")
    root.mkdir(parents=True, exist_ok=True)
    def fetch(item):
        key, url = item
        path = root / (key + ".pdf")
        try:
            if not path.exists():
                request = urllib.request.Request(url, headers={"User-Agent": "IDS-XAI-academic-review/1.0"})
                with urllib.request.urlopen(request, timeout=70) as response:
                    data = response.read()
                if not data.lstrip().startswith(b"%PDF"):
                    raise ValueError("Response is not a PDF")
                path.write_bytes(data)
            data = path.read_bytes()
            return {"id": key, "url": url, "path": path.as_posix(), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "status": "acquired"}
        except Exception as exc:
            return {"id": key, "url": url, "status": "unavailable", "error": str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(fetch, PAPERS.items()))
    output = Path("outputs/literature_review_20261107")
    output.mkdir(parents=True, exist_ok=True)
    (output / "acquisition.json").write_text(json.dumps({"checked_utc": datetime.now(timezone.utc).isoformat(),
        "records": records}, indent=2), encoding="utf-8")
    for record in records:
        print(record["id"], record["status"], record.get("bytes", record.get("error")))


if __name__ == "__main__":
    main()
