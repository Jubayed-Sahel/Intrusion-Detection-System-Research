"""Inspect an author's large ZIP through standard HTTP byte-range requests."""
import io
import json
import urllib.request
import zipfile
from pathlib import Path


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0
    def seekable(self):
        return True
    def tell(self):
        return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position
    def read(self, size=-1):
        if size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if not size:
            return b""
        if size > 128 * 1024 * 1024:
            raise ValueError("Refusing oversized range read")
        start = self.position
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{start + size - 1}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 206:
                raise ValueError(f"Server does not honor Range: {response.status}")
            body = response.read(size + 1)
        if len(body) != size:
            raise ValueError("Unexpected range response length")
        self.position += len(body)
        return body


def main():
    metadata = json.loads(Path("tmp/dataset_sources/zenodo-14502760.json").read_text())
    file = metadata["files"][0]
    url = "https://zenodo.org/records/14502760/files/GothamDataset2025.zip?download=1"
    remote = HTTPRangeFile(url, file["size"])
    with zipfile.ZipFile(remote) as archive:
        members = [{"filename": item.filename, "bytes": item.file_size, "compressed_bytes": item.compress_size,
                    "crc32": item.CRC} for item in archive.infolist()]
        Path("tmp/dataset_sources/gotham_members.json").write_text(json.dumps(members, indent=2))
        for item in members:
            if item["filename"].endswith((".csv", ".txt", ".md")):
                print(item, flush=True)


if __name__ == "__main__":
    main()
