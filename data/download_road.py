"""Download the official ROAD archive after the user accepts its data terms.

This utility is deliberately not run by the test suite and does not infer
labels or CAV/PBFT fields.  It records the exact source URL and SHA-256 so a
future benchmark can be reproduced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


RECORD = "https://zenodo.org/api/records/10462796"


def download(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(RECORD, timeout=90) as response:
        record = json.load(response)
    files = record.get("files", [])
    if not files:
        raise RuntimeError("Zenodo record did not expose any downloadable files")
    file_info = max(files, key=lambda item: item.get("size", 0))
    url = file_info["links"]["self"]
    output = destination / file_info["key"]
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=90) as source, output.open("wb") as target:
        while block := source.read(1024 * 1024):
            target.write(block); digest.update(block)
    manifest = {
        "record": RECORD,
        "file": file_info["key"],
        "bytes": output.stat().st_size,
        "sha256": digest.hexdigest(),
        "source_checksum": file_info.get("checksum"),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ROAD from its official Zenodo record.")
    parser.add_argument("--destination", type=Path, default=Path("data/raw/ROAD"))
    args = parser.parse_args()
    archive = download(args.destination)
    print(f"downloaded={archive}")


if __name__ == "__main__":
    main()
