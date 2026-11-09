"""Retrieve all official CSV members, without transferring unrelated PCAPs.

The author archive's complete MD5 is advertised but not recomputed. Each
retrieved ZIP member is fully decompressed and checked against its ZIP CRC32;
its SHA-256 and the exact source record/index are recorded.
"""
import hashlib
import json
import struct
import time
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from inspect_gotham_archive import HTTPRangeFile


def get_range(url, start, end):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-{end}/"):
                    raise ValueError("Incorrect HTTP range response")
                data = response.read(end - start + 2)
            if len(data) != end - start + 1:
                raise ValueError("Truncated range response")
            return data
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    output = Path("data/official/14502760")
    output.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen("https://zenodo.org/api/records/14502760", timeout=40) as response:
        record = json.load(response)
    (output / "provider_record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    descriptor = record["files"][0]
    url = "https://zenodo.org/records/14502760/files/GothamDataset2025.zip?download=1"
    with zipfile.ZipFile(HTTPRangeFile(url, descriptor["size"])) as archive:
        infos = [info for info in archive.infolist() if info.filename.endswith((".csv", ".md", ".json"))]
        entries = [{"filename": info.filename, "bytes": info.file_size, "compressed_bytes": info.compress_size,
                    "crc32": info.CRC, "header_offset": info.header_offset} for info in infos]
    (output / "member_index.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    manifest_path = output / "acquisition.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "record_id": 14502760, "source_url": url, "provider_archive_checksum": descriptor["checksum"],
        "full_archive_checksum_verified": False, "method": "official ZIP members via HTTP ranges; full-member CRC32 and local SHA-256", "files": []}
    for info in infos:
        target = output / info.filename
        resolved = target.resolve()
        if not resolved.is_relative_to(output.resolve()):
            raise ValueError("Archive path leaves source directory")
        known = next((file for file in manifest["files"] if file["filename"] == info.filename), None)
        if known and target.exists():
            with target.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() == known["sha256"]:
                    print(f"[cached] {info.filename}", flush=True)
                    continue
        header = get_range(url, info.header_offset, info.header_offset + 29)
        fields = struct.unpack("<4s5H3L2H", header)
        if fields[0] != b"PK\x03\x04" or fields[3] != zipfile.ZIP_DEFLATED and fields[3] != zipfile.ZIP_STORED:
            raise ValueError("Unsupported ZIP local header")
        start = info.header_offset + 30 + fields[-2] + fields[-1]
        chunks = [(pos, min(start + info.compress_size, pos + 4 * 1024 * 1024) - 1) for pos in range(start, start + info.compress_size, 4 * 1024 * 1024)]
        compressed_dir = output / "compressed_parts" / target.name
        compressed_dir.mkdir(parents=True, exist_ok=True)
        def fetch(bounds):
            left, right = bounds
            chunk_path = compressed_dir / str(left)
            if not chunk_path.exists() or chunk_path.stat().st_size != right - left + 1:
                chunk_path.write_bytes(get_range(url, left, right))
            return chunk_path
        with ThreadPoolExecutor(max_workers=6) as executor:
            for future in as_completed([executor.submit(fetch, bounds) for bounds in chunks]):
                future.result()
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        decompressor = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
        crc, size, digest = 0, 0, hashlib.sha256()
        with partial.open("wb") as stream:
            for left, _ in chunks:
                compressed = (compressed_dir / str(left)).read_bytes()
                if decompressor:
                    block = decompressor.decompress(compressed, 1024 * 1024)
                    while True:
                        stream.write(block); digest.update(block); crc = zlib.crc32(block, crc); size += len(block)
                        if not decompressor.unconsumed_tail:
                            break
                        block = decompressor.decompress(decompressor.unconsumed_tail, 1024 * 1024)
                else:
                    stream.write(compressed); digest.update(compressed); crc = zlib.crc32(compressed, crc); size += len(compressed)
            if decompressor:
                block = decompressor.flush()
                stream.write(block); digest.update(block); crc = zlib.crc32(block, crc); size += len(block)
        if size != info.file_size or crc != info.CRC:
            raise ValueError(f"ZIP member failed CRC32/length verification: {info.filename}")
        partial.replace(target)
        entry = {"filename": info.filename, "bytes": size, "compressed_bytes": info.compress_size,
                 "compressed_offset": start, "sha256": digest.hexdigest(), "crc32": crc, "member_crc_verified": True,
                 "acquired_utc": datetime.now(timezone.utc).isoformat()}
        manifest["files"] = [file for file in manifest["files"] if file["filename"] != info.filename] + [entry]
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[verified member] {info.filename}: {size/1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
