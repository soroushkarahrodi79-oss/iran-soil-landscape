"""Acquire FAO-linked HWSD v2.01 archives without overwriting immutable raw data."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "HWSD2_RASTER.zip": "https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_RASTER.zip",
    "HWSD2_DB.zip": "https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_DB.zip",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def acquire(filename: str, url: str) -> dict[str, str]:
    destination = ROOT / "data/raw/hwsd" / filename
    checksum = ROOT / "provenance/checksums" / f"{filename}.sha256"
    if destination.exists():
        raise RuntimeError(f"Refusing to overwrite immutable raw file: {destination}")
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=180, headers={"User-Agent": "iran-soil-landscapes/0.1"}) as response:
            response.raise_for_status()
            with temporary.open("xb") as output:
                for block in response.iter_content(1024 * 1024):
                    if block:
                        output.write(block)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = file_hash(destination)
    checksum.write_text(f"{digest}  {filename}\n", encoding="utf-8")
    return {"filename": filename, "official_url": url, "sha256": digest}


def main() -> None:
    records = [acquire(filename, url) for filename, url in SOURCES.items()]
    metadata = ROOT / "provenance/metadata/hwsd_acquisition.json"
    metadata.write_text(json.dumps({
        "dataset_id": "fao_iiasa_hwsd_v201",
        "access_date": date.today().isoformat(),
        "status": "RAW_DOWNLOADED_CHECKSUMMED",
        "files": records,
    }, indent=2) + "\n", encoding="utf-8")
    print("Acquired official HWSD archives and generated SHA-256 sidecars.")


if __name__ == "__main__":
    main()
