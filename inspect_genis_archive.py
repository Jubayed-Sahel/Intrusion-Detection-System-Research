import zipfile
from inspect_gotham_archive import HTTPRangeFile

url = "https://zenodo.org/records/14919237/files/3-scenarios.zip?download=1"
with zipfile.ZipFile(HTTPRangeFile(url, 491738368)) as archive:
    for item in archive.infolist():
        print(item.filename, item.file_size, item.compress_size, flush=True)
    csv_files = [item for item in archive.infolist() if item.filename.endswith(".csv")]
    for item in csv_files[:2]:
        with archive.open(item) as stream:
            print(stream.read(2500).decode("utf-8", errors="replace"), flush=True)
