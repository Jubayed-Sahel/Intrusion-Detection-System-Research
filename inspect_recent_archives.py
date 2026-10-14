import json
import sys
import zipfile
from pathlib import Path

from inspect_gotham_archive import HTTPRangeFile
sys.stdout.reconfigure(encoding="utf-8")


metadata = json.loads(Path("tmp/dataset_sources/zenodo-14502760.json").read_text())
remote = HTTPRangeFile("https://zenodo.org/records/14502760/files/GothamDataset2025.zip?download=1", metadata["files"][0]["size"])
with zipfile.ZipFile(remote) as archive:
    text = archive.read("README.md").decode("utf-8")
    Path("tmp/dataset_sources/gotham_readme.md").write_text(text, encoding="utf-8")
    print(text)
    for name in ("processed/iotsim-cooler-motor-1.csv", "processed/iotsim-city-power-1.csv"):
        with archive.open(name) as stream:
            print(name, stream.read(3500).decode("utf-8", errors="replace"))
