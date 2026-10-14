"""Keep the provider records and acquisition ledgers with published results."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main(output=Path("outputs/recent2025")):
    destination = output / "acquisition_snapshots"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"captured_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Post-acquisition copies of provider metadata, acquisition ledgers and reproducible retrieval scripts; script execution-time hashes are not asserted.",
        "files": {}}
    for dataset, record in (("GeNIS2025", "14919237"), ("Gotham2025", "14502760")):
        record_root = Path("data/official") / record
        ledger = json.loads((record_root / "acquisition.json").read_text())
        metadata = json.loads((record_root / "provider_record.json").read_text())
        assert str(metadata["id"]) == record and str(ledger["record_id"]) == record
        for name in ("provider_record.json", "acquisition.json", "member_index.json"):
            source = record_root / name
            if source.exists():
                target = destination / dataset / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.read_bytes())
                manifest["files"][target.relative_to(destination).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    for name in ("fetch_recent_datasets.py", "fetch_gotham_members.py", "inspect_gotham_archive.py"):
        target = destination / name
        target.write_bytes(Path(name).read_bytes())
        manifest["files"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Frozen {len(manifest['files'])} acquisition records/scripts alongside results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/recent2025"))
    main(parser.parse_args().output)
