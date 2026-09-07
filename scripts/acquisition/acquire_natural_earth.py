"""Acquire the official Natural Earth Admin 0 archive without overwriting raw data."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
URL = "https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip"
DESTINATION = ROOT / "data/raw/natural_earth/ne_10m_admin_0_countries.zip"
CHECKSUM = ROOT / "provenance/checksums/ne_10m_admin_0_countries.zip.sha256"
METADATA = ROOT / "provenance/metadata/ne_admin0_acquisition.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if DESTINATION.exists():
        raise SystemExit(f"Refusing to overwrite immutable raw file: {DESTINATION}")
    temporary = DESTINATION.with_suffix(".zip.part")
    try:
        with requests.get(URL, stream=True, timeout=90, headers={"User-Agent": "iran-soil-landscapes/0.1"}) as response:
            response.raise_for_status()
            with temporary.open("xb") as output:
                for block in response.iter_content(1024 * 1024):
                    if block:
                        output.write(block)
        temporary.replace(DESTINATION)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = sha256(DESTINATION)
    CHECKSUM.write_text(f"{digest}  {DESTINATION.name}\n", encoding="utf-8")
    METADATA.write_text(json.dumps({
        "dataset_id": "natural_earth_admin0_10m",
        "official_url": URL,
        "access_date": date.today().isoformat(),
        "local_raw_path": str(DESTINATION.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
        "status": "RAW_DOWNLOADED_CHECKSUMMED",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Acquired {DESTINATION.name}; SHA-256 written to {CHECKSUM}")


if __name__ == "__main__":
    main()
