"""Download the 198 SRTMGL3.003 tiles for Iran from the official LP DAAC endpoint.

Requires Earthdata Login credentials configured LOCALLY, one of:
  - ~/.netrc (or _netrc on Windows) with:  machine urs.earthdata.nasa.gov login <u> password <p>
  - env EARTHDATA_TOKEN (bearer token)
This script NEVER prints, logs, or stores credentials. It fails closed on any
response that is not a valid ZIP (e.g. an EDL "Access denied" or HTML login page),
so no unauthorized/corrupt file is ever accepted into data/raw/.

Reads:  provenance/manifests/srtm_tiles_iran.csv
Writes: data/raw/srtm/<TILE>.SRTMGL3.hgt.zip (+ sha256/bytes/status back into the manifest)
        provenance/checksums/srtm_sha256.txt
        provenance/metadata/srtm_acquisition_record.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "provenance/manifests/srtm_tiles_iran.csv"
RAW = ROOT / "data/raw/srtm"
COOKIES = RAW / ".urs_cookies"           # gitignored
CHECKSUMS = ROOT / "provenance/checksums/srtm_sha256.txt"
RECORD = ROOT / "provenance/metadata/srtm_acquisition_record.json"
ZIP_MAGIC = b"PK\x03\x04"


def have_credentials() -> tuple[bool, str]:
    home = Path(os.path.expanduser("~"))
    for nm in (".netrc", "_netrc"):
        p = home / nm
        if p.exists() and "urs.earthdata.nasa.gov" in p.read_text(encoding="utf-8", errors="ignore"):
            return True, f"netrc:{nm}"
    if os.environ.get("EARTHDATA_TOKEN"):
        return True, "env:EARTHDATA_TOKEN"
    return False, ""


def curl_download(url: str, dest: Path) -> None:
    if shutil.which("curl") is None:
        raise SystemExit("curl not found on PATH.")
    token = os.environ.get("EARTHDATA_TOKEN")
    cmd = ["curl", "-sS", "-L", "--fail", "--max-time", "600",
           "--retry", "3", "--retry-delay", "3",
           "--cookie-jar", str(COOKIES), "--cookie", str(COOKIES),
           "-o", str(dest)]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]  # value never printed by this script
    else:
        cmd += ["--netrc"]
    cmd.append(url)
    # We do not echo cmd (would not contain the secret anyway; token is in env/header).
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"curl exit {res.returncode}: {res.stderr.strip()[:200]}")


def is_valid_hgt_zip(path: Path) -> tuple[bool, str]:
    try:
        with path.open("rb") as fh:
            if fh.read(4) != ZIP_MAGIC:
                head = path.read_bytes()[:120]
                return False, f"not a ZIP (starts with {head[:40]!r})"
        with zipfile.ZipFile(path) as z:
            hgts = [i for i in z.infolist() if i.filename.lower().endswith(".hgt")]
            if not hgts:
                return False, "zip has no .hgt member"
            # SRTMGL3 .hgt is 1201*1201*2 = 2,884,802 bytes
            if hgts[0].file_size != 1201 * 1201 * 2:
                return False, f".hgt size {hgts[0].file_size} != expected 2884802 (1201x1201 int16)"
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"zip error: {exc}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ok, how = have_credentials()
    if not ok:
        raise SystemExit(
            "TERRAIN_AUTH_NOT_CONFIGURED: no Earthdata credentials found locally.\n"
            "Create ~/.netrc (or _netrc on Windows) containing:\n"
            "  machine urs.earthdata.nasa.gov login <username> password <password>\n"
            "and (Windows) chmod 600 it, OR set env EARTHDATA_TOKEN=<bearer>. "
            "Then re-run. This file is gitignored; the script never stores or prints it."
        )
    print(f"[auth] using {how}")
    RAW.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    done, skipped, failed = [], [], []
    for i, row in enumerate(rows, 1):
        tile, url = row["tile_id"], row["official_download_url"]
        dest = RAW / f"{tile}.SRTMGL3.hgt.zip"
        if dest.exists() and is_valid_hgt_zip(dest)[0]:
            row["status"] = "DOWNLOADED_VERIFIED"; row["bytes"] = str(dest.stat().st_size)
            row["sha256"] = row.get("sha256") or sha256(dest)
            skipped.append(tile); continue
        try:
            curl_download(url, dest)
            valid, why = is_valid_hgt_zip(dest)
            if not valid:
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"invalid response: {why}")
            row["bytes"] = str(dest.stat().st_size); row["sha256"] = sha256(dest)
            row["status"] = "DOWNLOADED_VERIFIED"; done.append(tile)
            print(f"[{i}/{len(rows)}] {tile} ok ({row['bytes']} B)")
        except Exception as exc:  # noqa: BLE001
            row["status"] = "FAILED"; failed.append((tile, str(exc)[:120]))
            print(f"[{i}/{len(rows)}] {tile} FAILED: {str(exc)[:120]}")

    # write manifest back
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    # checksums file
    with CHECKSUMS.open("w", encoding="utf-8") as fh:
        for row in rows:
            if row["status"] == "DOWNLOADED_VERIFIED":
                fh.write(f"{row['sha256']}  data/raw/srtm/{row['tile_id']}.SRTMGL3.hgt.zip\n")
    RECORD.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "product": "SRTMGL3.003", "auth": how,
        "tiles_total": len(rows), "downloaded": len(done), "skipped_present": len(skipped),
        "failed": failed,
        "endpoint": "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL3.003/",
    }, indent=2) + "\n", encoding="utf-8")
    COOKIES.unlink(missing_ok=True)
    print(f"done={len(done)} skipped={len(skipped)} failed={len(failed)}")
    if failed:
        raise SystemExit(f"{len(failed)} tiles failed; see manifest/record. Fail closed.")


if __name__ == "__main__":
    main()
