"""Compose the publication poster: Blender renders the map, this composes everything else.

Typography stays out of the terrain renderer. Blender produces only the soil/terrain/water
image; title, legend, labels, scale, north indicator, explanation and attribution are laid
out here as real text, and are emitted as vector (PDF/SVG) alongside the raster so nothing
depends on rasterised type.

Layout is resolution-independent: the figure is a fixed 20 x 25 in (4:5 portrait) and only
dpi changes, so the 2500 px proof, the 4000 px QA render and the 6000 px master are the
same composition at three sizes.

    python scripts/rendering/build_poster.py --width 2500 --map <render.png> --out <dir>

Visual hierarchy, in order: soil distribution, terrain context, geographic orientation,
supporting explanation. Terrain is never allowed to outrank the soil classes.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
PALETTE = ROOT / "config/soil_palette.yaml"
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
FURNITURE = ROOT / "provenance/metadata/map_furniture_qa.json"

TITLE = "SOIL LANDSCAPES OF IRAN"
SUBTITLE = "Terrain, climate and the geography beneath our feet"
PAPER = "#F4F1EA"
INK = "#22282E"
INK_SOFT = "#5A6570"
WATER_INK = "#2F5D82"

FIG_W, FIG_H = 20.0, 25.0          # inches, 4:5 portrait
MAP_LEFT, MAP_RIGHT = 0.10, 0.90
MAP_TOP = 0.885                     # top of the map axes, figure fraction
NOTES_TOP = 0.095                   # fixed anchor: explanation never floats into the legend
LEGEND_COLS = 5
MAP_CROP = 0.015                    # trims the terrain slab's lit edge (a DEM-bbox artefact)
LEGEND_MINOR_MAX = 0.05             # share % below which classes are grouped in the legend


def pick_font() -> str:
    """A restrained professional sans-serif already licensed on this machine."""
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Segoe UI", "Calibri", "Arial", "DejaVu Sans"):
        if name in have:
            return name
    return "sans-serif"


def load_classes() -> tuple[list[dict], list[dict], list[dict]]:
    pal = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    rows = list(csv.DictReader(SOIL_CSV.open(encoding="utf-8")))
    soils, nonsoil, minor = [], [], []
    for r in rows:
        entry = {"name": r["soil_group"], "code": r["classification_code"],
                 "share": float(r["share_percent"]), "hex": pal[r["classification_code"]]}
        if r["is_soil"].strip().lower() != "true":
            nonsoil.append(entry)               # Open Water is an accounting class, not a soil
        elif entry["share"] < LEGEND_MINOR_MAX:
            minor.append(entry)
        else:
            soils.append(entry)
    soils.sort(key=lambda e: -e["share"])       # mapped share: what the reader actually sees
    minor.sort(key=lambda e: -e["share"])
    return soils, nonsoil, minor


def draw_map(fig, map_png: Path, furniture: dict, font: str) -> None:
    img = Image.open(map_png).convert("RGBA")
    w, h = img.size
    cw, ch = int(w * MAP_CROP), int(h * MAP_CROP)
    img = img.crop((cw, ch, w - cw, h - ch))
    flat = Image.new("RGBA", img.size, tuple(int(PAPER[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    flat.alpha_composite(img)
    arr = np.asarray(flat.convert("RGB"))

    aspect = img.size[0] / img.size[1]
    width_frac = MAP_RIGHT - MAP_LEFT
    height_frac = width_frac * FIG_W / aspect / FIG_H
    ax = fig.add_axes((MAP_LEFT, MAP_TOP - height_frac, width_frac, height_frac))
    ax.imshow(arr, interpolation="lanczos")
    ax.set_axis_off()

    halo = [pe.withStroke(linewidth=5, foreground=PAPER, alpha=0.85)]
    def remap(f: float) -> float:                # frame fraction -> cropped-frame fraction
        return (f - MAP_CROP) / (1.0 - 2.0 * MAP_CROP)

    for lab in furniture["labels"]:
        x = remap(lab["frac_x"])
        y = 1.0 - remap(lab["frac_y"] + lab.get("text_dy_frac", 0.0))
        water = lab["style"] == "water"
        ax.text(x, y, lab["text"].upper() if not water else lab["text"],
                transform=ax.transAxes, ha="center", va="center",
                fontsize=13 if water else 12.5, fontfamily=font,
                fontstyle="italic" if water else "normal",
                fontweight="normal" if water else "semibold",
                color=WATER_INK if water else INK,
                alpha=0.92, path_effects=halo,
                # letter-spacing stand-in: physical features read as spaced small caps
                fontstretch="expanded" if not water else "normal")

    # --- scale bar: length derived from the map transform, tolerance from measurement ---
    sb = furniture["scale_bar"]
    span_km = furniture["map_frame"]["ortho_width_km"]
    bar_km = 400
    bar = bar_km / span_km
    x0, y0 = 0.035, 0.055
    ax.add_patch(Rectangle((x0, y0), bar, 0.006, transform=ax.transAxes,
                           facecolor=INK, edgecolor="none", alpha=0.85))
    ax.add_patch(Rectangle((x0, y0), bar / 2, 0.006, transform=ax.transAxes,
                           facecolor=PAPER, edgecolor=INK, linewidth=0.8, alpha=0.95))
    for frac, text in ((0.0, "0"), (0.5, f"{bar_km // 2}"), (1.0, f"{bar_km} km")):
        ax.text(x0 + bar * frac, y0 + 0.012, text, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=9.5, color=INK, fontfamily=font)
    ax.text(x0, y0 - 0.006, f"equal-area projection; distance scale accurate to "
                            f"±{sb['worst_deviation_percent']:.1f}% across the map",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=8, color=INK_SOFT, fontfamily=font)

    # --- north indicator: subtle, and honest about convergence ---
    nx, ny = 0.963, 0.052
    ax.annotate("", xy=(nx, ny + 0.055), xytext=(nx, ny),
                xycoords=ax.transAxes, textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.4, alpha=0.8))
    ax.text(nx, ny + 0.062, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=11, color=INK, fontfamily=font, fontweight="semibold")
    ax.text(nx, ny - 0.008, f"±{furniture['north_indicator']['grid_convergence_deg_max']:.0f}°",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=7.5, color=INK_SOFT, fontfamily=font)


def draw_title(fig, font: str) -> None:
    fig.text(0.055, 0.958, TITLE, ha="left", va="center", fontsize=54,
             fontfamily=font, fontweight="bold", color=INK)
    fig.text(0.055, 0.930, SUBTITLE, ha="left", va="center", fontsize=21,
             fontfamily=font, color=INK_SOFT)
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.911, 0.911], color=INK,
                              linewidth=1.1, alpha=0.35))
    fig.text(0.945, 0.930, "Dominant WRB-correlated soil groups\nHWSD v2.01 · SRTMGL3 terrain",
             ha="right", va="center", fontsize=11.5, fontfamily=font,
             color=INK_SOFT, linespacing=1.5)


def draw_legend(fig, soils, nonsoil, minor, font: str, top: float) -> float:
    fig.text(0.055, top, "SOIL REFERENCE GROUPS", ha="left", va="top", fontsize=13.5,
             fontfamily=font, fontweight="bold", color=INK)
    fig.text(0.055, top - 0.017, "WRB-2022-correlated dominant group per HWSD v2.01 mapping "
                                 "unit, ordered by mapped share of Iran",
             ha="left", va="top", fontsize=10.5, fontfamily=font, color=INK_SOFT)

    cols = LEGEND_COLS
    col_w = (0.945 - 0.055) / cols
    row_h, sw = 0.0235, 0.015
    y_start = top - 0.043
    for i, cls in enumerate(soils):
        cx = 0.055 + (i % cols) * col_w
        cy = y_start - (i // cols) * row_h
        fig.patches.append(Rectangle((cx, cy - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                     transform=fig.transFigure, facecolor=cls["hex"],
                                     edgecolor=INK, linewidth=0.5, alpha=1.0))
        fig.text(cx + sw + 0.008, cy - 0.009, cls["name"], ha="left", va="center",
                 fontsize=12, fontfamily=font, color=INK)
        fig.text(cx + col_w - 0.022, cy - 0.009, f"{cls['share']:.1f}%", ha="right",
                 va="center", fontsize=11, fontfamily=font, color=INK_SOFT)
    y = y_start - ((len(soils) - 1) // cols + 1) * row_h

    names = ", ".join(c["name"] for c in minor)
    fig.text(0.055, y - 0.004, f"Also mapped, each below 0.02% of Iran: {names} "
                               f"(combined {sum(c['share'] for c in minor):.3f}%).",
             ha="left", va="top", fontsize=10, fontfamily=font, color=INK_SOFT)

    y -= 0.030
    fig.text(0.055, y, "NON-SOIL", ha="left", va="top", fontsize=13.5,
             fontfamily=font, fontweight="bold", color=INK)
    y -= 0.022
    for i, cls in enumerate(nonsoil):
        cx = 0.055 + i * col_w
        fig.patches.append(Rectangle((cx, y - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                     transform=fig.transFigure, facecolor=cls["hex"],
                                     edgecolor=INK, linewidth=0.5))
        fig.text(cx + sw + 0.008, y - 0.009, f"{cls['name']} (HWSD accounting class)",
                 ha="left", va="center", fontsize=11.5, fontfamily=font, color=INK)
    cx = 0.055 + max(len(nonsoil), 1) * col_w
    fig.patches.append(Rectangle((cx, y - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                 transform=fig.transFigure,
                                 facecolor="#6E93B8", edgecolor=INK, linewidth=0.5))
    fig.text(cx + sw + 0.008, y - 0.009, "Seas and lakes (Natural Earth)",
             ha="left", va="center", fontsize=11.5, fontfamily=font, color=INK)
    cx += col_w
    fig.patches.append(Rectangle((cx, y - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                 transform=fig.transFigure,
                                 facecolor="#BFBAB2", edgecolor=INK, linewidth=0.5))
    fig.text(cx + sw + 0.008, y - 0.009, "Outside Iran — no soil data shown",
             ha="left", va="center", fontsize=11.5, fontfamily=font, color=INK)
    return y - 0.030


def draw_notes(fig, font: str, top: float) -> None:
    import textwrap

    def wrap(text: str, width: int = 95) -> str:
        nl = chr(10)
        return (nl + nl).join(nl.join(textwrap.wrap(par, width))
                              for par in text.split(nl + nl))

    fig.add_artist(plt.Line2D([0.055, 0.945], [top + 0.004, top + 0.004],
                              color=INK, linewidth=0.8, alpha=0.25))
    left = (
        "Each colour is the DOMINANT soil group of the HWSD v2.01 mapping unit at that "
        "location — the most extensive soil in a unit that usually contains several. It is "
        "not the soil at any single point, and no field survey was carried out for this map.\n\n"
        "Terrain is shaded relief from SRTMGL3 (~90 m), at 2× vertical exaggeration, used as "
        "context only: it never alters a soil class. The terrain is visualised at finer "
        "spatial detail than the soil data, and that detail does not increase the soil "
        "dataset's native ~1 km resolution."
    )
    right = (
        "Water is Natural Earth physical geometry — a cartographic outline, not a "
        "hydrographic observation — and is kept separate from the HWSD “Open Water” "
        "accounting class.\n\n"
        "Projection: Lambert azimuthal equal-area (lat₀ 32°N, lon₀ 53°E). Areas are "
        "comparable across the map; distances are accurate to a fraction of a percent."
    )
    fig.text(0.055, top - 0.008, wrap(left), ha="left", va="top", fontsize=9.5,
             fontfamily=font, color=INK, linespacing=1.45)
    fig.text(0.515, top - 0.008, wrap(right), ha="left", va="top", fontsize=9.5,
             fontfamily=font, color=INK, linespacing=1.45)

    attribution = (
        "Soils: FAO & IIASA — Harmonized World Soil Database v2.01, Rome and Laxenburg "
        "(DOI 10.4060/cc3823en), licensed CC BY-NC-SA 4.0.   "
        "Terrain: NASA/USGS SRTMGL3.003 (public domain).   "
        "Boundary and water: Made with Natural Earth."
    )
    fig.text(0.055, 0.021, attribution, ha="left", va="bottom", fontsize=9.5,
             fontfamily=font, color=INK_SOFT, linespacing=1.5)
    fig.text(0.055, 0.009, "This map is a derivative of HWSD v2.01 and is released under "
                           "CC BY-NC-SA 4.0.  Visual inspiration: Hemed Lungo’s "
                           "terrain-enhanced geospatial cartography (no affiliation).",
             ha="left", va="bottom", fontsize=9, fontfamily=font, color=INK_SOFT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="Blender map render PNG")
    ap.add_argument("--width", type=int, default=2500, help="output width px (height = 1.25x)")
    ap.add_argument("--out", default=str(ROOT / "outputs/proof/poster"))
    ap.add_argument("--vector", action="store_true", help="also write PDF and SVG")
    args = ap.parse_args()

    furniture = json.loads(FURNITURE.read_text(encoding="utf-8"))
    if furniture["labels_failed_verification"]:
        raise SystemExit(f"labels failed verification: {furniture['labels_failed_verification']}")
    font = pick_font()
    soils, nonsoil, minor = load_classes()

    dpi = args.width / FIG_W
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=dpi, facecolor=PAPER)
    draw_title(fig, font)
    draw_map(fig, Path(args.map), furniture, font)

    img = Image.open(args.map)
    aspect = img.size[0] / img.size[1]
    map_bottom = MAP_TOP - (MAP_RIGHT - MAP_LEFT) * FIG_W / aspect / FIG_H
    legend_bottom = draw_legend(fig, soils, nonsoil, minor, font, top=map_bottom - 0.024)
    if legend_bottom < NOTES_TOP:
        raise SystemExit(f"legend overruns the explanation block "
                         f"({legend_bottom:.3f} < {NOTES_TOP}); layout must be adjusted")
    draw_notes(fig, font, top=NOTES_TOP)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"iran_soil_landscapes_{args.width}x{int(args.width * 1.25)}"
    png = out_dir / f"{stem}.png"
    fig.savefig(png, dpi=dpi, facecolor=PAPER)
    written = [png]
    if args.vector:
        for ext in ("pdf", "svg"):
            v = out_dir / f"{stem}.{ext}"
            fig.savefig(v, facecolor=PAPER)
            written.append(v)
    plt.close(fig)
    for w in written:
        size = Image.open(w).size if w.suffix == ".png" else None
        rel = w.relative_to(ROOT) if w.is_relative_to(ROOT) else w
        print(f"wrote {rel} "
              f"({w.stat().st_size / 1e6:.1f} MB{'' if size is None else f', {size[0]}x{size[1]}'})")
    print(f"font: {font}; map: {Path(args.map).name}; labels: {len(furniture['labels'])}")


if __name__ == "__main__":
    main()
