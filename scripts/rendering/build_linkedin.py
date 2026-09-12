"""Mobile preview and readability metrics for the LinkedIn sheet.

The LinkedIn asset is composed by build_poster.py at 2160 x 2700 using the `linkedin`
layout. It is **not** a downsample of the master: larger type at the same pixel size cannot
be reached by resampling. The invariant that still holds — and that is checked elsewhere —
is that both sheets draw the *same scientific render*, proven by the map hash in each
sheet's `.build.json`.

What this script does is the part that cannot be argued from a layout file: it produces the
540 x 675 preview used for the feed-size inspection, and converts every type size into the
pixel height a reader actually gets at that size, so "readable" is a number rather than an
opinion.

    python scripts/rendering/build_linkedin.py --asset outputs/linkedin/<file>.png

The record is written twice: once beside the asset under its own name, so an earlier
published version keeps its evidence when a new one is composed, and once as
`linkedin_derivative.json`, which always describes the currently published feed asset and
is what the final QA and the tests read.
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
PREVIEW = (540, 675)               # the harsh feed-size test: 1x, quarter scale
SIZE_BUDGET_MB = 5.0               # conservative working figure, re-check before posting
FIG_W_IN = 20.0                    # the poster's physical width, from build_poster

# What each element has to survive at preview size. Body copy needs more than a label,
# because a label is short, bold and haloed while a sentence is not.
NEEDED_PX = {"title": 14.0, "map_label_land": 5.0, "legend_name": 5.0,
             "legend_pct": 4.8, "method": 8.5, "attribution": 6.5,
             # v1.1 furniture: each of these is text a reader has to actually read at feed
             # size, and each was below its minimum, or absent, before this gate.
             "subtitle": 4.6, "legend_head": 4.6, "legend_major": 5.2, "rare": 4.6,
             "nonsoil": 4.4, "scale_label": 4.8, "scale_note": 3.9, "north": 5.0,
             "north_note": 3.9}
EXTRA_KEYS = {"subtitle_pt": "subtitle", "legend_head_pt": "legend_head",
              "legend_major_pt": "legend_major", "rare_pt": "rare",
              "nonsoil_pt": "nonsoil", "scale_label_pt": "scale_label",
              "scale_note_pt": "scale_note", "north_pt": "north",
              "north_note_pt": "north_note"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True, help="composed 2160x2700 LinkedIn PNG")
    args = ap.parse_args()
    asset = Path(args.asset).resolve()
    if not asset.exists():
        raise SystemExit(f"asset not found: {asset}")

    img = Image.open(asset).convert("RGB")
    if img.size != (2160, 2700):
        raise SystemExit(f"asset is {img.size}, expected 2160x2700")
    build_path = asset.parent / f"{asset.stem}.build.json"
    if not build_path.exists():
        raise SystemExit(f"missing build record {build_path.name}; compose the sheet with "
                         f"build_poster.py --layout linkedin first")
    build = json.loads(build_path.read_text(encoding="utf-8"))

    preview = img.resize(PREVIEW, Image.LANCZOS)
    out = asset.parent / f"{asset.stem}_preview_{PREVIEW[0]}x{PREVIEW[1]}.png"
    preview.save(out, format="PNG", optimize=True)

    # em height a reader gets at preview size: pt -> inches -> asset px -> preview px
    dpi = img.size[0] / FIG_W_IN
    shrink = PREVIEW[0] / img.size[0]
    sizes = dict(build["type_pt"])
    for key, name in EXTRA_KEYS.items():
        if key in build.get("type_pt_extra", {}):
            sizes[name] = build["type_pt_extra"][key]
    metrics, failing = {}, []
    for name, pt in sizes.items():
        px = pt / 72.0 * dpi * shrink
        need = NEEDED_PX.get(name)
        ok = need is None or px >= need
        metrics[name] = {"pt": pt, "preview_px": round(px, 1),
                         "needed_px": need, "pass": ok}
        if not ok:
            failing.append(name)

    mb = asset.stat().st_size / 1e6
    record = {
        "asset": asset.name,
        "asset_px": list(img.size),
        "preview": out.name,
        "preview_px": list(PREVIEW),
        "composed_not_downsampled": True,
        "map_render": build["map_render"],
        "map_render_sha256": build["map_render_sha256"],
        "map_width_fraction": build["map_width_fraction"],
        "layout": build["layout"],
        "variant": build.get("variant"),
        "grid": build.get("grid"),
        "furniture": build.get("furniture"),
        "labels_moved": build.get("labels_moved", []),
        "type_at_preview_size": metrics,
        "failing_elements": failing,
        "file_size_mb": round(mb, 2),
        "size_budget_mb": SIZE_BUDGET_MB,
        "within_budget": mb <= SIZE_BUDGET_MB,
        "note": "Platform limits change; verify against current LinkedIn guidance before posting.",
    }
    blob = json.dumps(record, indent=2) + chr(10)
    (asset.parent / f"{asset.stem}.linkedin.json").write_text(blob, encoding="utf-8")
    (asset.parent / "linkedin_derivative.json").write_text(blob, encoding="utf-8")

    print(f"asset {asset.name} ({img.size[0]}x{img.size[1]}, {mb:.2f} MB)")
    print(f"preview {out.name} ({PREVIEW[0]}x{PREVIEW[1]})")
    print(f"{'element':<18}{'pt':>7}{'px @540':>10}{'needs':>8}  verdict")
    for name, m in metrics.items():
        print(f"{name:<18}{m['pt']:>7}{m['preview_px']:>10}"
              f"{str(m['needed_px']):>8}  {'ok' if m['pass'] else 'TOO SMALL'}")
    if failing:
        raise SystemExit(f"type too small at feed size: {failing}")
    print("all elements clear their feed-size minimum")


if __name__ == "__main__":
    main()
