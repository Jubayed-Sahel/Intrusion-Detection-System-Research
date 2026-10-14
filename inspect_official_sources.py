"""Read provider metadata and small documentation archives for candidate datasets."""
import json
import urllib.request
import zipfile
from pathlib import Path


def main():
    output = Path("tmp/dataset_sources")
    output.mkdir(parents=True, exist_ok=True)
    for record_id in (14919237, 14887131, 14502760):
        url = f"https://zenodo.org/api/records/{record_id}"
        with urllib.request.urlopen(url, timeout=40) as response:
            record = json.load(response)
        (output / f"zenodo-{record_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(record_id, record["metadata"]["title"], record["metadata"].get("license"), flush=True)
        for file in record["files"]:
            print(file["key"], file["size"], file["checksum"], file["links"]["self"], flush=True)
            if file["key"] == "0-info.zip" or file["key"] == "scripts.zip":
                target = output / f"{record_id}-{file['key']}"
                urllib.request.urlretrieve(file["links"]["self"], target)
                with zipfile.ZipFile(target) as archive:
                    for member in archive.infolist():
                        print("member", member.filename, member.file_size, flush=True)
                        if member.filename.endswith((".txt", ".md")):
                            print(archive.read(member).decode("utf-8", errors="replace"), flush=True)


if __name__ == "__main__":
    main()
