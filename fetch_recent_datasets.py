"""Download author-published archives with provider checksum verification."""
import argparse
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def download(record_id, names):
    output = Path("data/official") / str(record_id)
    output.mkdir(parents=True, exist_ok=True)
    metadata_url = f"https://zenodo.org/api/records/{record_id}"
    with urllib.request.urlopen(metadata_url, timeout=40) as response:
        record = json.load(response)
    metadata_path = output / "provider_record.json"
    metadata_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    provenance_path = output / "acquisition.json"
    acquisition = json.loads(provenance_path.read_text()) if provenance_path.exists() else {"record_id": record_id, "metadata_url": metadata_url, "files": []}
    for name in names:
        descriptor = next(file for file in record["files"] if file["key"] == name)
        target = output / name
        cached_ok = False
        if target.exists() and target.stat().st_size == descriptor["size"]:
            with target.open("rb") as existing:
                cached_ok = hashlib.file_digest(existing, "md5").hexdigest() == descriptor["checksum"].split(":")[1]
        if not cached_ok:
            partial = target.with_suffix(target.suffix + ".part")
            chunks_dir = output / (name + ".chunks")
            chunks_dir.mkdir(exist_ok=True)
            chunk_size = 4 * 1024 * 1024
            chunks = [(start, min(descriptor["size"], start + chunk_size) - 1) for start in range(0, descriptor["size"], chunk_size)]
            final_url = f"https://zenodo.org/records/{record_id}/files/{name}?download=1"
            def fetch_chunk(bounds):
                start, end = bounds
                chunk_path = chunks_dir / str(start)
                if chunk_path.exists() and chunk_path.stat().st_size == end - start + 1:
                    return chunk_path
                for attempt in range(4):
                    try:
                        request = urllib.request.Request(final_url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "IDS-XAI-research/1.0"})
                        with urllib.request.urlopen(request, timeout=90) as response:
                            if response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-{end}/"):
                                raise ValueError("Server did not return the requested byte range")
                            data = response.read(end - start + 2)
                        if len(data) != end - start + 1:
                            raise ValueError("Truncated range response")
                        chunk_path.write_bytes(data)
                        return chunk_path
                    except Exception:
                        if attempt == 3:
                            raise
                        time.sleep(2 ** attempt)
            received = 0
            with ThreadPoolExecutor(max_workers=6) as executor:
                for future in as_completed([executor.submit(fetch_chunk, bounds) for bounds in chunks]):
                    received += future.result().stat().st_size
                    print(f"[download] {name}: {received/1e6:.1f}/{descriptor['size']/1e6:.1f} MB", flush=True)
            with partial.open("wb") as stream:
                for start, _ in chunks:
                    stream.write((chunks_dir / str(start)).read_bytes())
            partial.replace(target)
            response_headers = {"transfer": "verified-length HTTP byte ranges; six workers"}
        else:
            response_headers, final_url = {}, descriptor["links"]["self"]
        digests = {"md5": hashlib.md5(), "sha256": hashlib.sha256()}
        with target.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                for digest in digests.values():
                    digest.update(block)
        algorithm, expected = descriptor["checksum"].split(":")
        if digests[algorithm].hexdigest() != expected or target.stat().st_size != descriptor["size"]:
            raise ValueError(f"Provider checksum or size mismatch: {target}")
        entry = {"filename": name, "url": descriptor["links"]["self"], "final_url": final_url,
                 "acquired_utc": datetime.now(timezone.utc).isoformat(), "bytes": target.stat().st_size,
                 "provider_checksum": descriptor["checksum"], "checksum_verified": True,
                 "sha256": digests["sha256"].hexdigest(), "response_headers": response_headers,
                 "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest()}
        acquisition["files"] = [file for file in acquisition["files"] if file["filename"] != name] + [entry]
        provenance_path.write_text(json.dumps(acquisition, indent=2), encoding="utf-8")
        print(f"[verified] {name}: {entry['sha256']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=int, required=True)
    parser.add_argument("--files", nargs="+", required=True)
    args = parser.parse_args()
    download(args.record, args.files)
