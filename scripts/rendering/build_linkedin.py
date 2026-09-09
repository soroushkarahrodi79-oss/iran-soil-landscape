"""Derive the LinkedIn asset from the archival master — never recomposed independently.

A separately re-rendered "social version" drifts from the master: different type sizes,
different crops, and eventually different claims. This takes the accepted master and only
resamples it, so the published image is provably the same map.

    python scripts/rendering/build_linkedin.py --master outputs/master/<file>.png

Emits outputs/linkedin/iran_soil_landscapes_linkedin_2160x2700.png and reports the file
size against the upload budget. LinkedIn's published limits change; the budget here is a
conservative working figure and should be re-checked against current guidance before
posting rather than trusted from this script.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs/linkedin"
TARGET = (2160, 2700)              # 4:5, the portrait ratio LinkedIn renders largest
SIZE_BUDGET_MB = 5.0               # conservative working figure, re-check before posting


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    args = ap.parse_args()
    master = Path(args.master).resolve()
    if not master.exists():
        raise SystemExit(f"master not found: {master}")

    img = Image.open(master).convert("RGB")
    if abs(img.width / img.height - TARGET[0] / TARGET[1]) > 1e-3:
        raise SystemExit(f"master is {img.width}x{img.height}, not the 4:5 of {TARGET}")
    if img.width < TARGET[0]:
        raise SystemExit(f"master {img.width}px is smaller than the derivative "
                         f"{TARGET[0]}px — upscaling would fake resolution")

    out = img.resize(TARGET, Image.LANCZOS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / f"iran_soil_landscapes_linkedin_{TARGET[0]}x{TARGET[1]}.png"
    out.save(png, format="PNG", optimize=True)
    mb = png.stat().st_size / 1e6

    record = {
        "derived_from": str(master.relative_to(ROOT) if master.is_relative_to(ROOT) else master),
        "master_size": [img.width, img.height],
        "derivative_size": list(TARGET),
        "resample": "Lanczos downsample only; no re-composition, no upscaling",
        "file_size_mb": round(mb, 2),
        "size_budget_mb": SIZE_BUDGET_MB,
        "within_budget": mb <= SIZE_BUDGET_MB,
        "note": "Platform limits change; verify against current LinkedIn guidance before posting.",
    }
    (OUT_DIR / "linkedin_derivative.json").write_text(
        json.dumps(record, indent=2) + chr(10), encoding="utf-8")
    print(f"wrote {png.relative_to(ROOT)}  ({TARGET[0]}x{TARGET[1]}, {mb:.2f} MB)")
    print(f"downsampled from {img.width}x{img.height}; "
          f"{'within' if mb <= SIZE_BUDGET_MB else 'OVER'} the {SIZE_BUDGET_MB} MB working budget")


if __name__ == "__main__":
    main()
