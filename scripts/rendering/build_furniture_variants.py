"""Compose the three v1.1 furniture directions over ONE scientific render, and compare them.

The gate this belongs to changes composition only. Every direction is drawn from the same
Blender render, the same projection, the same orthographic camera, the same 2x exaggeration
and the same palette; the hash of the render is written into each sheet's build record so
"same map, three sheets" is provable rather than asserted.

    python scripts/rendering/build_furniture_variants.py

Writes, for each of A / B / C:

    outputs/proof/furniture_v11/<name>_2160x2700.png        the candidate sheet
    outputs/proof/furniture_v11/<name>_540x675.png          the feed-size inspection copy
    outputs/proof/furniture_v11/<name>_2160x2700.build.json layout, grid and furniture record

and one comparison sheet placing the three side by side at equal display size.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "outputs/proof/3d/iran_map_2x_topdown_5400x4897.png"
OUT = ROOT / "outputs/proof/furniture_v11"
PREVIEW = (540, 675)
SHEET = (2160, 2700)

VARIANTS = [
    ("v11_a", "A_academic_minimal", "A — ACADEMIC MINIMAL"),
    ("v11_b", "B_editorial_cartography", "B — EDITORIAL CARTOGRAPHY"),
    ("v11_c", "C_exhibition_poster", "C — EXHIBITION POSTER"),
]


def compose(layout: str, name: str, width: int) -> Path:
    stem = f"{name}_{width}x{int(width * 1.25)}"
    cmd = [sys.executable, str(ROOT / "scripts/rendering/build_poster.py"),
           "--map", str(RENDER), "--width", str(width), "--layout", layout,
           "--out", str(OUT), "--name", stem]
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr)
        raise SystemExit(f"{layout} failed to compose")
    return OUT / f"{stem}.png"


def comparison_sheet(sheets: list[tuple[str, Path]], records: dict, out: Path) -> None:
    """A / B / C at one display size, with the measurements that separate them underneath.

    Composed in matplotlib rather than with Pillow's bitmap font so the sheet uses the same
    typeface as the candidates and can set an em dash. The caption under each thumbnail is
    measured, not editorial: the scoring is a judgement and belongs in the written record,
    but the numbers the judgement rests on belong here, next to the thing they describe.
    """
    from build_poster import pick_font

    font = pick_font()
    n = len(sheets)
    fig_w, fig_h = 4.6 * n + 1.2, 8.6
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=200, facecolor="#F4F1EA")
    fig.text(0.028, 0.972, "CARTOGRAPHIC FURNITURE v1.1", fontsize=11, fontfamily=font,
             fontweight="bold", color="#22282E", va="center")
    fig.text(0.028, 0.949, "Three directions over one scientific render, shown at "
                           "540 × 675 — the size the sheet is judged at.",
             fontsize=8.5, fontfamily=font, color="#5A6570", va="center")

    pad, top, w = 0.028, 0.905, (1.0 - 2 * 0.028 - 0.030 * (n - 1)) / n
    h = w * fig_w / fig_h * (675 / 540)
    for i, (label, path) in enumerate(sheets):
        x = pad + i * (w + 0.030)
        fig.text(x, top + 0.014, label, fontsize=9, fontfamily=font, fontweight="semibold",
                 color="#22282E", va="center")
        ax = fig.add_axes((x, top - h, w, h))
        ax.imshow(np.asarray(Image.open(path).convert("RGB").resize(PREVIEW, Image.LANCZOS)))
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#9AA0A6"); sp.set_linewidth(0.6)

        rec = records[path.stem.replace("_2160x2700", "")]
        f, g = rec["furniture"], rec["grid"]
        lines = [
            f"title {rec['type_pt']['title']:.0f} pt · legend lead "
            f"{rec['type_pt_extra']['legend_major_pt']:.1f} pt",
            f"neatline {f['neatline']['linewidth_pt']:.1f} pt"
            + (" double" if f["neatline"]["double"] else " single")
            + f" · national keyline {'off' if not f['national_keyline_pt'] else 'on'}",
            f"map {g['map_height_fraction']:.3f} of sheet height · legend headroom "
            f"{g['legend_bottom'] - g['footer_top']:+.4f}",
        ]
        fig.text(x, top - h - 0.018, chr(10).join(lines), fontsize=7.2, fontfamily=font,
                 color="#3E4954", va="top", linespacing=1.6)

    fig.savefig(out, facecolor="#F4F1EA")
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def before_after(out: Path) -> None:
    """The accepted v1.0 feed sheet beside the selected v1.1 one, at the same size.

    A gate that only ever compares its own candidates can talk itself into a change. This is
    the comparison that decides whether the gate was worth running at all.
    """
    pub = yaml.safe_load((ROOT / "config/publication.yaml").read_text(encoding="utf-8"))
    old = ROOT / pub["superseded"][0]["linkedin"]
    new = ROOT / pub["linkedin"]["path"]
    if not (old.exists() and new.exists()):
        print("skipping before/after: both published feed sheets are needed")
        return
    from build_poster import pick_font

    font = pick_font()
    fig = plt.figure(figsize=(10.4, 7.4), dpi=200, facecolor="#F4F1EA")
    fig.text(0.026, 0.966, "SOIL LANDSCAPES OF IRAN — feed sheet, v1.0 and v1.1 at "
                           "540 × 675", fontsize=10, fontfamily=font, fontweight="bold",
             color="#22282E", va="center")
    for i, (label, path) in enumerate((("v1.0 — accepted", old), ("v1.1 — selected", new))):
        x = 0.026 + i * 0.487
        fig.text(x, 0.936, label, fontsize=8.5, fontfamily=font, fontweight="semibold",
                 color="#3E4954", va="center")
        ax = fig.add_axes((x, 0.918 - 0.845, 0.462, 0.845))
        ax.imshow(np.asarray(Image.open(path).convert("RGB").resize(PREVIEW, Image.LANCZOS)))
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#9AA0A6"); sp.set_linewidth(0.6)
    fig.savefig(out, facecolor="#F4F1EA")
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="build one variant key (v11_a/v11_b/v11_c)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    render_sha = hashlib.sha256(RENDER.read_bytes()).hexdigest()
    built, records = [], {}
    for layout, name, label in VARIANTS:
        if args.only and layout != args.only:
            continue
        png = compose(layout, name, SHEET[0])
        prev = OUT / f"{name}_{PREVIEW[0]}x{PREVIEW[1]}.png"
        Image.open(png).convert("RGB").resize(PREVIEW, Image.LANCZOS).save(
            prev, format="PNG", optimize=True)
        rec = json.loads((png.parent / f"{png.stem}.build.json").read_text(encoding="utf-8"))
        if rec["map_render_sha256"] != render_sha:
            raise SystemExit(f"{name} did not draw the frozen render")
        records[name] = rec
        built.append((label, png))
        print(f"  preview {prev.name}  ({PREVIEW[0]}x{PREVIEW[1]})")

    if len(built) == len(VARIANTS):
        comparison_sheet(built, records, OUT / "comparison_A_B_C_540x675.png")
        before_after(OUT / "comparison_v1_0_vs_v1_1_540x675.png")

    (OUT / "variants.json").write_text(json.dumps({
        "map_render": RENDER.name,
        "map_render_sha256": render_sha,
        "same_render_for_every_variant": True,
        "sheet_px": list(SHEET), "preview_px": list(PREVIEW),
        "variants": {k: {"layout": v["layout"], "variant": v["variant"],
                         "grid": v["grid"], "furniture": v["furniture"],
                         "type_pt": v["type_pt"], "type_pt_extra": v.get("type_pt_extra", {})}
                     for k, v in records.items()},
    }, indent=2) + chr(10), encoding="utf-8")
    print(f"\nall variants drew {RENDER.name} sha {render_sha[:12]}…")


if __name__ == "__main__":
    main()
