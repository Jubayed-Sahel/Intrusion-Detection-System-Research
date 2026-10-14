"""Recover exact run-start snapshots; accept only a recorded hash match."""
import hashlib
import json
from pathlib import Path


current = Path("src/xai_ids/benchmark.py").read_bytes().replace(b"\r\n", b"\n")
plot_guard = b'    # Aggregate plots require both datasets and tasks. A scoped correction is\n    # plotted after its rows are merged into the complete result tables.\n    if not config.get("contexts"):\n        make_summary_plots(output_dir)'
scope_guard = b'            if config.get("contexts") and f"{dataset}/{task}" not in config["contexts"]:\n                continue\n'
candidates = [current, current.replace(plot_guard, b'    make_summary_plots(output_dir)')]
candidates += [value.replace(scope_guard, b"") for value in list(candidates)]
candidates += [value.replace(b"\n", b"\r\n") for value in list(candidates)]
for folder in ("research_validation_corrected", "clean_reproduction"):
    output = Path("outputs") / folder
    expected = json.loads((output / "protocol.json").read_text())["benchmark_source_sha256"]
    matches = [value for value in candidates if hashlib.sha256(value).hexdigest() == expected]
    if not matches:
        raise ValueError(f"Cannot recover exact recorded benchmark source for {folder}")
    (output / "benchmark_source_at_run_start.py").write_bytes(matches[0])
    print(folder, "recorded source hash matched")
