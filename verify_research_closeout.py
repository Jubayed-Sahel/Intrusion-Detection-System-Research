"""Verify the current study from frozen results without retraining."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.xai_ids.benchmark import sha256
from src.xai_ids.extended_validation_results import load_extended
from src.xai_ids.journal_audit import manuscript_text
from src.xai_ids.independent_tcp import load_independent_tcp
from src.xai_ids.publication_extensions import kernel_paragraph, lime_budget_results, masking_results
from src.xai_ids.training_scale import load_training_scale
from verify_manuscript_revision import main as verify_manuscripts
from verify_recent_benchmark import main as verify_primary


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"


def verify_hashes(base, hashes, optional_local=False):
    checked = 0
    for name, digest in hashes.items():
        path = base / name
        if optional_local and not path.exists() and (
            name.startswith("data/") or "/models/" in name
        ):
            continue
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"Missing or changed evidence: {path}")
        checked += 1
    return checked


def read_manifest(directory):
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def verify_extensions():
    checked = 0
    for name, input_key, output_key in (
        ("masking_extension_20261108", "sha256", "artifacts_sha256"),
        ("lime_budget_20261108", "inputs", "aggregate_outputs"),
        ("lime_kernel_20261108", "inputs", "aggregate_outputs"),
        ("pattern_sensitivity_20261107", "sha256", None),
    ):
        directory = OUTPUTS / name
        manifest = read_manifest(directory)
        checked += verify_hashes(ROOT, manifest[input_key], optional_local=True)
        if output_key:
            checked += verify_hashes(directory, manifest[output_key])
    extended = OUTPUTS / "extended_validation_20261108"
    for path in sorted(extended.glob("*/manifest.json")):
        manifest = read_manifest(path.parent)
        checked += verify_hashes(ROOT, {
            "run_extended_validation.py": manifest.get("runner", manifest.get("runner_sha256")),
            "EXTENDED_VALIDATION_PROTOCOL.md": manifest.get("protocol", manifest.get("protocol_sha256")),
        })
        if "source_manifest" in manifest:
            checked += verify_hashes(OUTPUTS / "source_holdout_20261108",
                                     {"run_manifest.json": manifest["source_manifest"]})
    masking_results()
    lime_budget_results()
    kernel_paragraph()
    load_extended()
    manuscript_text(ROOT)
    load_training_scale(ROOT)
    load_independent_tcp(ROOT)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-raw", action="store_true",
                        help="Also rehash the locally acquired GeNIS and Gotham input bytes.")
    args = parser.parse_args()
    verify_primary(verify_raw=args.verify_raw, output=OUTPUTS / "recent2025")
    subprocess.run([sys.executable, str(OUTPUTS / "source_holdout_20261108/verify_saved_results.py")],
                   cwd=ROOT, check=True)
    checked = verify_extensions()
    verify_manuscripts()
    print(f"Research closeout passed. Checked {checked} extension hash references "
          "plus the uncapped, journal, primary and source-holdout verifiers.")


if __name__ == "__main__":
    main()
