"""Compose the publication sheet: Blender renders the map, this composes everything else.

Typography stays out of the terrain renderer. Blender produces only the soil/terrain/water
image; title, legend, labels, scale, north indicator, explanation and attribution are laid
out here as real text, and are emitted as vector (PDF/SVG) alongside the raster so nothing
depends on rasterised type.

Layout is resolution-independent: the figure is a fixed 20 x 25 in (4:5 portrait) and only
dpi changes, so the 2160 px feed sheet and the 6000 px master are the same composition at
two sizes.

    python scripts/rendering/build_poster.py --width 2160 --layout v11_b --map <render.png>

Visual hierarchy, in order: Iran and its soil pattern, title, terrain context, legend,
geographic orientation, method and sources. Terrain is never allowed to outrank the soil
classes.

--------------------------------------------------------------------------------------
CARTOGRAPHIC FURNITURE v1.1
--------------------------------------------------------------------------------------
The v1.1 layouts change composition only. The scientific render, projection, camera, 2x
exaggeration, classification, statistics and palette are inputs to this file, never
outputs of it. Three controlled directions are composed over the identical render:

    v11_a  ACADEMIC_MINIMAL      restrained; hairline furniture, journal-atlas quiet
    v11_b  EDITORIAL_CARTOGRAPHY strongest hierarchy; the furniture is designed, not added
    v11_c  EXHIBITION_POSTER     heaviest framing that is still defensible cartography

The v1.0 `master` and `linkedin` layouts are kept unchanged so v1.0 stays reproducible.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.textpath import TextToPath  # noqa: E402
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
INK_MID = "#3E4954"          # attribution/method secondary: darker than INK_SOFT, still quiet
WATER_INK = "#2F5D82"

FIG_W, FIG_H = 20.0, 25.0          # inches, 4:5 portrait
LEGEND_COLS = 5
MAP_CROP = 0.015                    # trims the terrain slab's lit edge (a DEM-bbox artefact)
LEGEND_MINOR_MAX = 0.05             # share % below which classes are grouped in the legend
LEGEND_MAJOR_MIN = 10.0             # share % at or above which a class leads the legend

# --------------------------------------------------------------------------------------
# THE GRID (v1.1)
#
# v1.0 had one accidental alignment that showed on every sheet: the map frame started at
# 0.068 of the sheet width while the title, legend, method and attribution all started at
# 0.055 — a 1.3% step, 28 px at 2160, that nothing justified. v1.1 puts every element on
# the map frame's own left rail, so the map defines the measure and the type hangs off it.
#
# Vertical positions are integer multiples of RHYTHM from the top of the sheet, and the
# stack below the map is built from named gaps rather than from nudges.
# --------------------------------------------------------------------------------------
GRID = {
    "margin_l": 0.068,              # = map_left: one rail for the whole sheet
    "margin_r": 0.932,
    "rhythm": 0.0045,               # 0.1125 in; every vertical stop is a multiple of this
    "top_margin": 0.0315,
    "bottom_margin": 0.0135,
}


def q(v: float) -> float:
    """Snap a vertical position to the compositional rhythm."""
    return round(round(v / GRID["rhythm"]) * GRID["rhythm"], 5)


# --------------------------------------------------------------------------------------
# Two v1.0 layouts over ONE scientific render, kept so v1.0 stays reproducible.
# --------------------------------------------------------------------------------------
LAYOUTS = {
    "master": {
        "map_left": 0.10, "map_right": 0.90, "map_top": 0.885,
        "footer_top": 0.095,
        "label_land_pt": 12.5, "label_water_pt": 13.0,
        "legend_head_pt": 13.5, "legend_name_pt": 12.0, "legend_pct_pt": 11.0,
        "legend_pct_colour": INK_SOFT, "legend_row_h": 0.0235, "legend_sub": True,
        "meta_block": True, "footer": "full",
        "scale_note": "equal-area projection; distance scale accurate to ±{dev:.1f}% across the map",
    },
    "linkedin": {
        "map_left": 0.068, "map_right": 0.932, "map_top": 0.900,   # map frame +8%
        "footer_top": 0.090,
        "label_land_pt": 15.0, "label_water_pt": 15.5,     # +20% / +19%
        "legend_head_pt": 15.0, "legend_name_pt": 15.0, "legend_pct_pt": 13.2,  # +25% / +20%
        "legend_pct_colour": INK, "legend_row_h": 0.026, "legend_sub": False,
        "nonsoil_gap": 0.026, "nonsoil_row": 0.024,
        # Sized from the 540 px mobile test, not from a percentage: at 2160 px these are
        # ~36 px and ~29 px, which survive the 4x reduction. The 20-25% uplift asked for
        # elsewhere is not enough for body copy at feed size.
        "method_pt": 24.0, "method_wrap": 100, "attrib_pt": 19.0, "attrib_y": 0.012,
        "meta_block": False, "footer": "short",
        "scale_note": "Scale variation <0.3%",
    },
}
LAYOUTS["master"].update({"nonsoil_gap": 0.030, "nonsoil_row": 0.024,
                          "method_pt": 9.5, "method_wrap": 95,
                          "attrib_pt": 9.5, "attrib_y": 0.021})

# --------------------------------------------------------------------------------------
# v1.1: one base composition, three furniture treatments.
#
# Type sizes are held at or above the v1.0 feed-size minimums (build_linkedin.py measures
# them), so the directions differ in *furniture and hierarchy*, never in whether the sheet
# is readable. Line weights are in points and are therefore physical, but the feed sheet is
# viewed at a quarter of its pixel size, so every rule that has to survive that reduction
# is specified from the 540 px test and not from print habit: 1 pt is 0.375 px at 540.
# --------------------------------------------------------------------------------------
V11_BASE = {
    "version": "v1.1",
    "map_left": GRID["margin_l"], "map_right": GRID["margin_r"],
    "map_top": q(0.9005),
    "footer": "short",
    "meta_block": False,
    "legend_sub": False,
    "legend_pct_colour": INK,
    "scale_note": "Scale variation <0.3%",
    # type
    "title_pt": 54.0, "title_tracking": 0.020, "title_weight": "bold",
    "subtitle_pt": 21.0, "subtitle_colour": INK_SOFT, "subtitle_tracking": 0.0,
    "label_land_pt": 15.0, "label_water_pt": 15.5, "label_tracking": 0.085,
    "legend_head_pt": 15.0, "legend_head_tracking": 0.075,
    "legend_major_pt": 16.5, "legend_major_pct_pt": 16.5,
    "legend_minor_pt": 14.0, "legend_minor_pct_pt": 14.0,
    "rare_pt": 13.5,
    "nonsoil_head_pt": 13.0, "nonsoil_pt": 13.0,
    "scale_label_pt": 14.0, "scale_note_pt": 11.5,
    "north_pt": 15.0, "north_note_pt": 11.5,
    "method_lead_pt": 24.0, "method_pt": 24.0, "method_leading": 1.28,
    "attrib_pt": 21.0,
    # furniture
    "neatline_pt": 2.4, "neatline_alpha": 0.55, "neatline_double": False,
    # National keyline: built, measured, and switched off. qa_keyline_decision.py reports
    # that no width both survives the 540 px feed reduction (>= 2.27 pt) and stays inside
    # HWSD's ~1 km native support (<= 0.7 pt), while the border ring already separates from
    # the ground outside Iran at mean dE00 22.1 with none of its 21,157 px below the
    # project's dE00 >= 10 threshold. The stroke would have darkened 0.9% of mapped Iran to
    # sharpen an edge that is already sharp. The geometry stays in the furniture record so
    # the decision can be re-run rather than re-argued.
    "boundary_pt": 0.0, "boundary_alpha": 0.50,
    "title_rule_pt": 1.4, "title_rule_alpha": 0.45,
    "legend_rule": True, "footer_rule_pt": 1.2, "footer_rule_alpha": 0.30,
    "swatch_major": 0.0195, "swatch_minor": 0.0155, "swatch_nonsoil": 0.0135,
    "swatch_edge_pt": 0.6,
    "scale_bar_h": 0.0085, "scale_bar_lw": 1.1,
    "north_lw": 2.0,
    # vertical stack (fractions of sheet height)
    "gap_map_legend": 0.020, "gap_head_rows": 0.0225,
    "row_major": 0.0315, "row_minor": 0.0270,
    "gap_rare": 0.0090, "rare_leading": 1.30,
    "gap_nonsoil": 0.0180, "gap_nonsoil_head_row": 0.0180,
    "row_nonsoil": 0.0225,
    "footer_top": 0.0945, "attrib_y": 0.0135,
    # title block, measured upward from the map so the rule always hangs off the frame
    "gap_rule_map": 0.0180, "gap_sub_rule": 0.0135, "gap_title_sub": 0.0075,
}


def _v11(name: str, **over) -> dict:
    d = dict(V11_BASE)
    d.update(over)
    d["variant"] = name
    return d


LAYOUTS["v11_a"] = _v11(
    "A_academic_minimal",
    # Journal atlas: the furniture recedes. One hairline neatline, no national keyline
    # (the colour step at the border is left to do that work), quiet title, even legend.
    title_pt=46.0, title_tracking=0.030, title_weight="semibold",
    subtitle_pt=19.0,
    neatline_pt=1.6, neatline_alpha=0.40,
    title_rule_pt=0.9, title_rule_alpha=0.30,
    legend_rule=False, footer_rule_pt=0.8, footer_rule_alpha=0.22,
    legend_major_pt=15.0, legend_major_pct_pt=15.0,
    legend_minor_pt=14.0, legend_minor_pct_pt=14.0,
    legend_head_pt=13.5,
    swatch_major=0.0165, swatch_minor=0.0150,
    scale_bar_h=0.0060, scale_bar_lw=0.8, north_lw=1.4,
    row_major=0.0270, row_minor=0.0270,
    method_lead_pt=23.0, method_pt=23.0, attrib_pt=20.0,
)

LAYOUTS["v11_b"] = _v11(
    "B_editorial_cartography",
    # The intended publication sheet: a keyline that reads at feed size, a two-tier legend
    # that puts the four dominant groups first, and a method caption with a real first line.
    gap_head_rows=0.0180,
)

LAYOUTS["v11_c"] = _v11(
    "C_exhibition_poster",
    # Strongest framing that is still cartography rather than decoration: a double
    # keyline, a heavier national stroke, a larger title and a scale bar sized for a wall.
    title_pt=60.0, title_tracking=0.045,
    subtitle_pt=22.0, subtitle_colour=INK_MID,
    neatline_pt=3.0, neatline_alpha=0.70, neatline_double=True,
    title_rule_pt=2.2, title_rule_alpha=0.55,
    footer_rule_pt=1.6, footer_rule_alpha=0.40,
    legend_head_pt=15.5, legend_head_tracking=0.095,
    legend_major_pt=17.5, legend_major_pct_pt=17.5,
    swatch_major=0.0225, swatch_minor=0.0160,
    scale_bar_h=0.0110, scale_bar_lw=1.4, north_lw=2.6,
    scale_label_pt=15.0, north_pt=16.0,
    row_major=0.0335, row_minor=0.0270,
    gap_nonsoil=0.0135,
)

# Control layout for the keyline decision: B with the national stroke switched off, so the
# gain can be looked at rather than argued about. Nothing else differs.
LAYOUTS["v11_b_nokeyline"] = _v11("B_editorial_cartography_no_keyline",
                                  gap_head_rows=0.0180, boundary_pt=0.0)
LAYOUTS["v11_b_keyline"] = _v11("B_editorial_cartography_keyline",
                                gap_head_rows=0.0180, boundary_pt=1.2)

# The archival sheet for the selected direction: the same composition, with the full
# citations, licence sentence and method paragraphs the feed sheet delegates to the post.
LAYOUTS["v11_master"] = _v11(
    "B_editorial_cartography_master",
    # The archival frame stays at v1.0's 0.800 of the sheet. The feed sheet's map is
    # deliberately 8% larger than the archival one, and that margin is a tested invariant —
    # widening the master here would have quietly spent it.
    map_left=0.100, map_right=0.900, map_top=q(0.8825),
    footer="full", legend_sub=True, meta_block=True,
    scale_note="equal-area projection; distance scale accurate to ±{dev:.1f}% across the map",
    title_pt=54.0, subtitle_pt=20.0,
    label_land_pt=12.5, label_water_pt=13.0,
    legend_head_pt=13.5, legend_major_pt=13.5, legend_major_pct_pt=13.5,
    legend_minor_pt=11.5, legend_minor_pct_pt=11.5,
    legend_pct_colour=INK, rare_pt=10.5,
    nonsoil_head_pt=11.5, nonsoil_pt=11.5,
    scale_label_pt=10.5, scale_note_pt=8.5, north_pt=11.5, north_note_pt=8.0,
    neatline_pt=1.2, neatline_alpha=0.55,
    title_rule_pt=1.1, footer_rule_pt=0.9,
    swatch_major=0.0165, swatch_minor=0.0140, swatch_nonsoil=0.0130,
    scale_bar_h=0.0065, scale_bar_lw=0.9, north_lw=1.4,
    row_major=0.0250, row_minor=0.0220,
    method_lead_pt=9.5, method_pt=9.5, attrib_pt=9.5,
    footer_top=0.0980, attrib_y=0.0210,
    gap_map_legend=0.0180, gap_head_rows=0.0270,
    gap_rare=0.0090, gap_nonsoil=0.0180, gap_nonsoil_head_row=0.0160,
    row_nonsoil=0.0200,
)


# --------------------------------------------------------------------------------------
# Typography helpers
# --------------------------------------------------------------------------------------
_T2P = TextToPath()


def text_w_pt(s: str, prop: FontProperties) -> float:
    """Advance width of a string in points, at the property's own size."""
    return float(_T2P.get_text_width_height_descent(s, prop, False)[0])


def tracked(target, x: float, y: float, s: str, *, pt: float, font: str, width_in: float,
            tracking: float = 0.0, weight: str = "normal", style: str = "normal",
            colour: str = INK, ha: str = "left", va: str = "center", alpha: float = 1.0,
            effects=None, transform=None, zorder: float = 3) -> float:
    """Draw text with real letter-spacing, and return its width in coordinate fractions.

    matplotlib has no tracking, and v1.0 reached for `fontstretch="expanded"` as a stand-in
    — which asks the font for a wider *design*, not for wider spacing, and silently does
    nothing when that design is absent. Glyphs are placed here at measured advances
    instead, so tracking is a real number of ems and prefix kerning is preserved.
    """
    prop = FontProperties(family=font, size=pt, weight=weight, style=style)
    step = tracking * pt
    advances = [text_w_pt(s[:i], prop) + i * step for i in range(len(s) + 1)]
    total_pt = advances[-1] - (step if s else 0.0)
    total = total_pt / 72.0 / width_in
    x0 = x if ha == "left" else (x - total if ha == "right" else x - total / 2.0)
    # Figure.text/Axes.text install their own default transform only when the caller does
    # not supply one, and an explicit None is a supplied one — it drops the text into raw
    # display pixels. So the key is omitted rather than passed as None.
    kw = dict(ha="left", va=va, fontsize=pt, fontfamily=font, fontweight=weight,
              fontstyle=style, color=colour, alpha=alpha, path_effects=effects,
              zorder=zorder)
    if transform is not None:
        kw["transform"] = transform
    if not tracking:
        target.text(x0, y, s, **kw)
        return total
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        target.text(x0 + advances[i] / 72.0 / width_in, y, ch, **kw)
    return total


def wrap_to_width(s: str, pt: float, font: str, width_in: float, weight: str = "normal",
                  max_lines: int | None = None) -> list[str]:
    """Wrap by measured width, not by a guessed character count."""
    prop = FontProperties(family=font, size=pt, weight=weight)
    limit_pt = width_in * 72.0
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and text_w_pt(trial, prop) > limit_pt:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        raise SystemExit(f"text needs {len(lines)} lines at {pt} pt, budget is {max_lines}: "
                         f"{s[:60]}…")
    return lines


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


# --------------------------------------------------------------------------------------
# Map
# --------------------------------------------------------------------------------------
def draw_map(fig, map_png: Path, furniture: dict, font: str, L: dict,
             out_width_px: int) -> dict:
    img = Image.open(map_png).convert("RGBA")
    w, h = img.size
    cw, ch = int(w * MAP_CROP), int(h * MAP_CROP)
    img = img.crop((cw, ch, w - cw, h - ch))
    flat = Image.new("RGBA", img.size, tuple(int(PAPER[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    flat.alpha_composite(img)

    aspect = img.size[0] / img.size[1]
    width_frac = L["map_right"] - L["map_left"]
    height_frac = width_frac * FIG_W / aspect / FIG_H

    # Resample once, here, to exactly the pixels the axes will occupy. Handing matplotlib a
    # 5238 px map for an 1866 px frame makes it build a float64 RGBA copy of the full render
    # (760 MB) and then throw most of it away; doing the reduction in Pillow is one Lanczos
    # pass instead of two and keeps the feed sheet composable in ordinary memory.
    target_w = max(int(round(width_frac * out_width_px)), 1)
    resized = target_w < flat.size[0]
    if resized:
        flat = flat.resize((target_w, max(int(round(target_w / aspect)), 1)), Image.LANCZOS)
    # Keep the alpha channel and stay in uint8. Handing imshow a 3-channel array makes
    # matplotlib build a float64 RGBA copy to add the alpha it needs — 677 MB at master
    # size, on top of the copy it already made.
    arr = np.asarray(flat)

    ax = fig.add_axes((L["map_left"], L["map_top"] - height_frac, width_frac, height_frac))
    ax.imshow(arr, interpolation="nearest" if resized else "lanczos")
    ax.set_axis_off()
    del flat, img
    axes_w_in = width_frac * FIG_W

    def remap(f: float) -> float:                # frame fraction -> cropped-frame fraction
        return (f - MAP_CROP) / (1.0 - 2.0 * MAP_CROP)

    # --- national keyline: display-only, from the same Natural Earth geometry ----------
    # Drawn under the labels and under the neatline, at low alpha, so it sharpens the
    # silhouette without painting over the border soil pixels it runs along.
    if L.get("boundary_pt") and "boundary" in furniture:
        for line in furniture["boundary"]["polylines_frac"]:
            xy = np.asarray(line)
            ax.plot(remap(xy[:, 0]), 1.0 - remap(xy[:, 1]), color=INK,
                    linewidth=L["boundary_pt"], alpha=L["boundary_alpha"],
                    solid_joinstyle="round", solid_capstyle="round", zorder=2)

    v11 = L.get("version") == "v1.1"
    halo = [pe.withStroke(linewidth=5.5 if v11 else 5, foreground=PAPER,
                          alpha=0.88 if v11 else 0.85)]
    for lab in furniture["labels"]:
        # v1.0 drew the anchor plus a hand-set vertical nudge; v1.1 uses the searched
        # offset, which has an x component and is verified against the rasters.
        dx = lab.get("text_dx_frac", 0.0) if v11 else 0.0
        dy = lab.get("text_dy_frac", 0.0)
        x, y = remap(lab["frac_x"] + dx), 1.0 - remap(lab["frac_y"] + dy)
        water = lab["style"] == "water"
        if not v11:
            ax.text(x, y, lab["text"] if water else lab["text"].upper(),
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=L["label_water_pt"] if water else L["label_land_pt"],
                    fontfamily=font, fontstyle="italic" if water else "normal",
                    fontweight="normal" if water else "semibold",
                    color=WATER_INK if water else INK, alpha=0.92, path_effects=halo,
                    fontstretch="expanded" if not water else "normal")
            continue
        tracked(ax, x, y, lab["text"] if water else lab["text"].upper(),
                pt=L["label_water_pt"] if water else L["label_land_pt"],
                font=font, width_in=axes_w_in,
                tracking=0.0 if water else L["label_tracking"],
                weight="normal" if water else "semibold",
                style="italic" if water else "normal",
                colour=WATER_INK if water else INK,
                ha="center", va="center", alpha=0.95, effects=halo,
                transform=ax.transAxes, zorder=4)

    span_km = furniture["map_frame"]["ortho_width_km"] * (1.0 - 2.0 * MAP_CROP)
    if v11:
        sb = draw_scale_bar(ax, furniture, font, L, axes_w_in, span_km)
        ni = draw_north(ax, furniture, font, L, axes_w_in)
        nl = draw_neatline(fig, L)
    else:
        sb, ni = _draw_furniture_v10(ax, furniture, font, L, span_km)
        nl = {"drawn": False}
    return {"axes": ax, "aspect": aspect, "height_frac": height_frac,
            "scale_bar": sb, "north": ni, "neatline": nl,
            "axes_w_in": axes_w_in, "span_km": span_km}


def _draw_furniture_v10(ax, furniture: dict, font: str, L: dict, span_km: float):
    """v1.0's scale bar and north arrow, kept so the superseded sheets still compose.

    They are not what v1.1 draws — the labels were 9.5 pt (3.6 px at feed size, which is why
    the gate replaced them) and the arrow hung half in the page margin at x=0.963. Preserving
    them here is what makes "v1.0 is superseded, not deleted" a statement the build can back.
    """
    sb = furniture["scale_bar"]
    bar_km = 400
    bar = bar_km / (furniture["map_frame"]["ortho_width_km"] * (1.0 - 2.0 * MAP_CROP))
    x0, y0 = 0.035, 0.055
    ax.add_patch(Rectangle((x0, y0), bar, 0.006, transform=ax.transAxes,
                           facecolor=INK, edgecolor="none", alpha=0.85))
    ax.add_patch(Rectangle((x0, y0), bar / 2, 0.006, transform=ax.transAxes,
                           facecolor=PAPER, edgecolor=INK, linewidth=0.8, alpha=0.95))
    for frac, text in ((0.0, "0"), (0.5, f"{bar_km // 2}"), (1.0, f"{bar_km} km")):
        ax.text(x0 + bar * frac, y0 + 0.012, text, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=9.5, color=INK, fontfamily=font)
    note = L["scale_note"].format(dev=sb["worst_deviation_percent"])
    ax.text(x0, y0 - 0.006, note, transform=ax.transAxes, ha="left", va="top",
            fontsize=8 if L["footer"] == "full" else 9.5, color=INK_SOFT, fontfamily=font)

    conv = furniture["north_indicator"]["grid_convergence_deg_max"]
    nx, ny = 0.963, 0.052
    ax.annotate("", xy=(nx, ny + 0.055), xytext=(nx, ny),
                xycoords=ax.transAxes, textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.4, alpha=0.8))
    ax.text(nx, ny + 0.062, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=11, color=INK, fontfamily=font, fontweight="semibold")
    ax.text(nx, ny - 0.008, f"±{conv:.0f}°", transform=ax.transAxes, ha="center", va="top",
            fontsize=7.5, color=INK_SOFT, fontfamily=font)
    return ({"bar_km": bar_km, "bar_frac_of_axes": round(bar, 5), "label_pt": 9.5,
             "note": note},
            {"note": f"±{conv:.0f}°", "convergence_deg_max": conv, "x_axes": nx})


def draw_neatline(fig, L: dict) -> dict:
    """A restrained keyline that makes the map read as a defined cartographic field.

    Weight is chosen from the feed test rather than from print habit: at 2160 px one point
    is 1.5 px, and the sheet is inspected at 540 px, so anything under about 2.7 pt drops
    below a pixel there. The master sheet, which is read at size, takes the print weight.
    """
    if not L.get("neatline_pt"):
        return {"drawn": False}
    x0, x1 = L["map_left"], L["map_right"]
    y1 = L["map_top"]
    y0 = y1 - L["_map_height_frac"]
    specs = [(L["neatline_pt"], L["neatline_alpha"], 0.0)]
    if L.get("neatline_double"):
        specs.append((L["neatline_pt"] * 0.30, L["neatline_alpha"] * 0.75, 0.0085))
    for lw, alpha, off in specs:
        fig.patches.append(Rectangle(
            (x0 - off, y0 - off * FIG_W / FIG_H),
            (x1 - x0) + 2 * off, (y1 - y0) + 2 * off * FIG_W / FIG_H,
            transform=fig.transFigure, facecolor="none", edgecolor=INK,
            linewidth=lw, alpha=alpha, zorder=5))
    return {"drawn": True, "linewidth_pt": L["neatline_pt"],
            "alpha": L["neatline_alpha"], "double": bool(L.get("neatline_double"))}


def draw_scale_bar(ax, furniture: dict, font: str, L: dict, axes_w_in: float,
                   span_km: float) -> dict:
    """Alternating bar with a tick hierarchy, sized so its labels survive the feed test."""
    sb = furniture["scale_bar"]
    bar_km = 400
    bar = bar_km / span_km
    x0, y0 = 0.038, 0.062
    h = L["scale_bar_h"]
    lw = L["scale_bar_lw"]
    ax.add_patch(Rectangle((x0, y0), bar, h, transform=ax.transAxes,
                           facecolor=INK, edgecolor="none", alpha=0.92, zorder=4))
    ax.add_patch(Rectangle((x0, y0), bar / 2, h, transform=ax.transAxes,
                           facecolor=PAPER, edgecolor=INK, linewidth=lw, alpha=0.96,
                           zorder=4))
    ax.add_patch(Rectangle((x0, y0), bar, h, transform=ax.transAxes, facecolor="none",
                           edgecolor=INK, linewidth=lw, alpha=0.92, zorder=5))
    # Tick hierarchy: the ends and the midpoint carry a label, the quarters only a tick.
    for frac in (0.25, 0.75):
        ax.plot([x0 + bar * frac] * 2, [y0 + h, y0 + h * 1.55], transform=ax.transAxes,
                color=INK, linewidth=lw, alpha=0.75, zorder=5)
    for frac, text in ((0.0, "0"), (0.5, f"{bar_km // 2}"), (1.0, f"{bar_km} km")):
        ax.plot([x0 + bar * frac] * 2, [y0 + h, y0 + h * 2.1], transform=ax.transAxes,
                color=INK, linewidth=lw * 1.2, alpha=0.9, zorder=5)
        ax.text(x0 + bar * frac, y0 + h * 2.6, text, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=L["scale_label_pt"], color=INK,
                fontfamily=font, fontweight="semibold", zorder=5,
                path_effects=[pe.withStroke(linewidth=4, foreground=PAPER, alpha=0.85)])
    note = L["scale_note"].format(dev=sb["worst_deviation_percent"])
    ax.text(x0, y0 - 0.010, note, transform=ax.transAxes, ha="left", va="top",
            fontsize=L["scale_note_pt"], color=INK_MID, fontfamily=font, zorder=5,
            path_effects=[pe.withStroke(linewidth=4, foreground=PAPER, alpha=0.85)])
    return {"bar_km": bar_km, "bar_frac_of_axes": round(bar, 5),
            "label_pt": L["scale_label_pt"], "note": note}


def draw_north(ax, furniture: dict, font: str, L: dict, axes_w_in: float) -> dict:
    """A needle, not a compass rose — and captioned with what it can honestly claim.

    Meridians converge in an azimuthal projection, so the arrow is grid north: exact on the
    central meridian and up to the measured convergence away from true north at the corners.
    v1.0 pushed it to x=0.963, half of it hanging in the page margin; it is inset here so it
    sits inside the cartographic field like the scale bar opposite.
    """
    conv = furniture["north_indicator"]["grid_convergence_deg_max"]
    nx, ny = 0.920, 0.062
    ax.annotate("", xy=(nx, ny + 0.062), xytext=(nx, ny),
                xycoords=ax.transAxes, textcoords=ax.transAxes, zorder=5,
                arrowprops=dict(arrowstyle="-|>,head_width=0.22,head_length=0.5",
                                color=INK, linewidth=L["north_lw"], alpha=0.9,
                                shrinkA=0, shrinkB=0))
    ax.text(nx, ny + 0.070, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=L["north_pt"], color=INK, fontfamily=font, fontweight="bold",
            zorder=5, path_effects=[pe.withStroke(linewidth=4.5, foreground=PAPER, alpha=0.85)])
    note = f"grid north ±{conv:.0f}°"
    ax.text(nx, ny - 0.010, note, transform=ax.transAxes, ha="center", va="top",
            fontsize=L["north_note_pt"], color=INK_MID, fontfamily=font, zorder=5,
            path_effects=[pe.withStroke(linewidth=4, foreground=PAPER, alpha=0.85)])
    return {"note": note, "convergence_deg_max": conv, "x_axes": nx}


# --------------------------------------------------------------------------------------
# Title
# --------------------------------------------------------------------------------------
def draw_title(fig, font: str, L: dict) -> None:
    if L.get("version") != "v1.1":
        fig.text(0.055, 0.958, TITLE, ha="left", va="center", fontsize=54,
                 fontfamily=font, fontweight="bold", color=INK)
        fig.text(0.055, 0.930, SUBTITLE, ha="left", va="center", fontsize=21,
                 fontfamily=font, color=INK_SOFT)
        fig.add_artist(plt.Line2D([0.055, 0.945], [0.911, 0.911], color=INK,
                                  linewidth=1.1, alpha=0.35))
        if L["meta_block"]:
            fig.text(0.945, 0.930,
                     "Dominant WRB-correlated soil groups\nHWSD v2.01 · SRTMGL3 terrain",
                     ha="right", va="center", fontsize=11.5, fontfamily=font,
                     color=INK_SOFT, linespacing=1.5)
        return

    left, right = L["map_left"], L["map_right"]
    rule_y = q(L["map_top"] + L["gap_rule_map"])
    sub_y = q(rule_y + L["gap_sub_rule"])
    title_y = q(sub_y + L["title_pt"] / 72.0 / FIG_H + L["gap_title_sub"])
    cap_top = title_y + L["title_pt"] * 0.72 / 72.0 / FIG_H / 2.0
    if cap_top > 1.0 - GRID["top_margin"] * 0.5:
        raise SystemExit(f"title block overruns the sheet top ({cap_top:.4f}); "
                         f"lower map_top or tighten the title gaps")
    tracked(fig, left, title_y, TITLE, pt=L["title_pt"], font=font, width_in=FIG_W,
            tracking=L["title_tracking"], weight=L["title_weight"], colour=INK,
            ha="left", va="center")
    tracked(fig, left, sub_y, SUBTITLE, pt=L["subtitle_pt"], font=font, width_in=FIG_W,
            tracking=L.get("subtitle_tracking", 0.0), colour=L["subtitle_colour"],
            ha="left", va="center")
    fig.add_artist(plt.Line2D([left, right], [rule_y, rule_y], color=INK,
                              linewidth=L["title_rule_pt"], alpha=L["title_rule_alpha"]))
    if L["meta_block"]:
        fig.text(right, sub_y, "Dominant WRB-correlated soil groups\n"
                               "HWSD v2.01 · SRTMGL3 terrain",
                 ha="right", va="center", fontsize=11.5, fontfamily=font,
                 color=INK_SOFT, linespacing=1.5)


# --------------------------------------------------------------------------------------
# Legend
# --------------------------------------------------------------------------------------
def draw_legend(fig, soils, nonsoil, minor, font: str, top: float, L: dict,
                surface: dict) -> float:
    if L.get("version") != "v1.1":
        return _draw_legend_v10(fig, soils, nonsoil, minor, font, top, L, surface)
    return _draw_legend_v11(fig, soils, nonsoil, minor, font, top, L, surface)


def _draw_legend_v10(fig, soils, nonsoil, minor, font, top, L, surface) -> float:
    head, name_pt, pct_pt = L["legend_head_pt"], L["legend_name_pt"], L["legend_pct_pt"]
    fig.text(0.055, top, "SOIL REFERENCE GROUPS", ha="left", va="top", fontsize=head,
             fontfamily=font, fontweight="bold", color=INK)
    y_start = top - 0.026
    if L["legend_sub"]:
        fig.text(0.055, top - 0.017, "WRB-2022-correlated dominant group per HWSD v2.01 mapping "
                                     "unit, ordered by mapped share of Iran",
                 ha="left", va="top", fontsize=10.5, fontfamily=font, color=INK_SOFT)
        y_start = top - 0.043

    cols = LEGEND_COLS
    col_w = (0.945 - 0.055) / cols
    row_h = L["legend_row_h"]
    sw = 0.015 if L["footer"] == "full" else 0.018
    for i, cls in enumerate(soils):
        cx = 0.055 + (i % cols) * col_w
        cy = y_start - (i // cols) * row_h
        fig.patches.append(Rectangle((cx, cy - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                     transform=fig.transFigure, facecolor=cls["hex"],
                                     edgecolor=INK, linewidth=0.5, alpha=1.0))
        fig.text(cx + sw + 0.008, cy - 0.009, cls["name"], ha="left", va="center",
                 fontsize=name_pt, fontfamily=font, color=INK)
        fig.text(cx + col_w - 0.018, cy - 0.009, f"{cls['share']:.1f}%", ha="right",
                 va="center", fontsize=pct_pt, fontfamily=font,
                 color=L["legend_pct_colour"])
    y = y_start - ((len(soils) - 1) // cols + 1) * row_h

    names = ", ".join(c["name"] for c in minor)
    fig.text(0.055, y - 0.004, f"Also mapped, each below 0.02% of Iran: {names} "
                               f"(combined {sum(c['share'] for c in minor):.3f}%).",
             ha="left", va="top", fontsize=10 if L["footer"] == "full" else 11,
             fontfamily=font, color=INK_SOFT)

    y -= L["nonsoil_gap"]
    fig.text(0.055, y, "NON-SOIL", ha="left", va="top", fontsize=head,
             fontfamily=font, fontweight="bold", color=INK)
    y -= L["nonsoil_row"]
    entries = [(c["hex"], f"{c['name']} (HWSD accounting class)") for c in nonsoil]
    # Swatches read from configuration, never hard-coded: a legend chip that has drifted
    # from the rendered colour is a factual error in the map.
    entries.append((surface["cartographic_water_srgb"], "Seas and lakes (Natural Earth)"))
    entries.append((surface["context_land_srgb"], "Outside Iran — no soil data shown"))
    for i, (hexcol, text) in enumerate(entries):
        cx = 0.055 + i * col_w
        fig.patches.append(Rectangle((cx, y - sw * FIG_W / FIG_H), sw, sw * FIG_W / FIG_H,
                                     transform=fig.transFigure, facecolor=hexcol,
                                     edgecolor=INK, linewidth=0.5))
        fig.text(cx + sw + 0.008, y - 0.009, text, ha="left", va="center",
                 fontsize=11.5 if L["footer"] == "full" else name_pt * 0.86,
                 fontfamily=font, color=INK)
    return y - 0.030


def _swatch(fig, x: float, y_centre: float, size: float, hexcol: str, lw: float) -> None:
    """A square swatch, centred on the row baseline so rows sit on a true rhythm."""
    h = size * FIG_W / FIG_H
    fig.patches.append(Rectangle((x, y_centre - h / 2.0), size, h,
                                 transform=fig.transFigure, facecolor=hexcol,
                                 edgecolor=INK, linewidth=lw, alpha=1.0, zorder=3))


def _draw_legend_v11(fig, soils, nonsoil, minor, font, top, L, surface) -> float:
    """Two tiers, one rail, tabular percentages.

    The split is the data's, not a designer's: classes at or above LEGEND_MAJOR_MIN% of
    Iran lead the block, the rest follow at a smaller size. That puts Leptosols, Regosols,
    Solonchaks and Calcisols — 94.7% of the mapped country between them — in the reader's
    first fixation, and leaves Arenosols at the head of the second tier rather than lost in
    a flat list. Nothing is greyed out: a smaller row is a lower information priority, not
    a claim that the class matters less scientifically.
    """
    left, right = L["map_left"], L["map_right"]
    width = right - left
    major = [c for c in soils if c["share"] >= LEGEND_MAJOR_MIN]
    minor_tier = [c for c in soils if c["share"] < LEGEND_MAJOR_MIN]

    y = top
    tracked(fig, left, y, "SOIL REFERENCE GROUPS", pt=L["legend_head_pt"], font=font,
            width_in=FIG_W, tracking=L["legend_head_tracking"], weight="bold",
            colour=INK, ha="left", va="center")
    if L["legend_sub"]:
        y = q(y - 0.0135)
        fig.text(left, y, "WRB-2022-correlated dominant group per HWSD v2.01 mapping unit, "
                          "ordered by mapped share of Iran",
                 ha="left", va="center", fontsize=10.5, fontfamily=font, color=INK_SOFT)
    y = q(y - L["gap_head_rows"])

    def row(entries, pt, pct_pt, sw, row_h, weight, pct_weight):
        """One tier on one line, as content-width blocks spread across the measure.

        An equal-column grid right-aligns each percentage to a rail that has nothing to do
        with its class name, so "Leptosols" and "40.7%" end up a thumb apart and the reader
        has to re-pair them. The block is measured instead — swatch, widest name, widest
        percentage — so name and value stay a fixed short gap apart while the blocks
        themselves sit on an even rhythm and their percentage edges still line up.
        """
        nonlocal y
        name_prop = FontProperties(family=font, size=pt, weight=weight)
        pct_prop = FontProperties(family=font, size=pct_pt, weight=pct_weight)
        name_w = max(text_w_pt(c["name"], name_prop) for c in entries) / 72.0 / FIG_W
        pct_w = max(text_w_pt(f"{c['share']:.1f}%", pct_prop) for c in entries) / 72.0 / FIG_W
        block = sw + 0.0075 + name_w + 0.0110 + pct_w
        n = len(entries)
        step = (width - block) / (n - 1) if n > 1 else 0.0
        for i, cls in enumerate(entries):
            cx = left + i * step
            _swatch(fig, cx, y, sw, cls["hex"], L["swatch_edge_pt"])
            fig.text(cx + sw + 0.0075, y, cls["name"], ha="left", va="center",
                     fontsize=pt, fontfamily=font, fontweight=weight, color=INK)
            fig.text(cx + block, y, f"{cls['share']:.1f}%", ha="right",
                     va="center", fontsize=pct_pt, fontfamily=font,
                     fontweight=pct_weight, color=L["legend_pct_colour"])
        y = q(y - row_h)

    row(major, L["legend_major_pt"], L["legend_major_pct_pt"],
        L["swatch_major"], L["row_major"], "semibold", "bold")
    row(minor_tier, L["legend_minor_pt"], L["legend_minor_pct_pt"],
        L["swatch_minor"], L["row_minor"], "normal", "semibold")

    # --- rare classes: small, but not something the reader has to hunt for -------------
    y = q(y - L["gap_rare"])
    rare_pt = L["rare_pt"]
    # The grouping constant is the threshold the classes fall under, not what they measure.
    # The stated bound is the largest minor share rounded up, so the sheet says something
    # true of these six classes rather than something true of the rule that collected them.
    bound = np.ceil(max(c["share"] for c in minor) * 100.0) / 100.0
    lead = f"Minor mapped RSGs (each <{bound:.2f}% of Iran)"
    names = ", ".join(c["name"] for c in minor)
    tail = f"  {names}  ·  combined {sum(c['share'] for c in minor):.3f}%"
    w_lead = tracked(fig, left, y, lead, pt=rare_pt, font=font, width_in=FIG_W,
                     tracking=0.03, weight="semibold", colour=INK, ha="left", va="center")
    fig.text(left + w_lead + 0.006, y, tail.strip(), ha="left", va="center",
             fontsize=rare_pt, fontfamily=font, color=INK_MID)
    y = q(y - rare_pt / 72.0 / FIG_H * L["rare_leading"])

    # --- non-soil: subordinate to the soil legend, but not an afterthought ------------
    y = q(y - L["gap_nonsoil"])
    if L.get("legend_rule"):
        fig.add_artist(plt.Line2D([left, right], [y + 0.0090, y + 0.0090], color=INK,
                                  linewidth=0.8, alpha=0.22))
    tracked(fig, left, y, "NON-SOIL", pt=L["nonsoil_head_pt"], font=font, width_in=FIG_W,
            tracking=L["legend_head_tracking"], weight="bold", colour=INK_MID,
            ha="left", va="center")
    y = q(y - L["gap_nonsoil_head_row"])
    # Swatches read from configuration, never hard-coded: a legend chip that has drifted
    # from the rendered colour is a factual error in the map.
    # Cartographic water and the HWSD Open Water accounting class are measurably close in
    # colour, and should be: both depict water. What separates them is provenance, so the
    # separation is carried in type — one em-dash construction across all three entries, so
    # the reader sees three statements of "where this colour comes from" rather than three
    # unrelated captions.
    entries = [(c["hex"], f"{c['name']} — HWSD accounting class") for c in nonsoil]
    entries.append((surface["cartographic_water_srgb"],
                    "Seas and lakes — Natural Earth cartography"))
    entries.append((surface["context_land_srgb"], "Outside Iran — no soil data shown"))
    sw = L["swatch_nonsoil"]
    col_w = width / len(entries)
    for i, (hexcol, text) in enumerate(entries):
        cx = left + i * col_w
        _swatch(fig, cx, y, sw, hexcol, L["swatch_edge_pt"])
        fig.text(cx + sw + 0.0065, y, text, ha="left", va="center",
                 fontsize=L["nonsoil_pt"], fontfamily=font, color=INK_MID)
    return q(y - L["row_nonsoil"])


# --------------------------------------------------------------------------------------
# Method strip and attribution
# --------------------------------------------------------------------------------------
METHOD_LEAD = "Dominant WRB-correlated soil groups from HWSD v2.01 (~1 km native support)."
METHOD_BODY = ("Terrain: SRTMGL3.003, vertically exaggerated 2× for visualization. "
               "Terrain detail does not increase soil-data resolution.")
ATTRIBUTION_SHORT = "Data: FAO & IIASA · NASA/USGS · Natural Earth · CC BY-NC-SA 4.0"


def draw_notes(fig, font: str, top: float, L: dict) -> dict:
    def wrap(text: str, width: int = 95) -> str:
        nl = chr(10)
        return (nl + nl).join(nl.join(textwrap.wrap(par, width))
                              for par in text.split(nl + nl))

    if L.get("version") != "v1.1":
        fig.add_artist(plt.Line2D([0.055, 0.945], [top + 0.004, top + 0.004],
                                  color=INK, linewidth=0.8, alpha=0.25))
        if L["footer"] == "short":
            method = f"{METHOD_LEAD} {METHOD_BODY}"
            fig.text(0.055, top - 0.012, wrap(method, L["method_wrap"]), ha="left", va="top",
                     fontsize=L["method_pt"], fontfamily=font, color=INK, linespacing=1.4)
            fig.text(0.055, L["attrib_y"], ATTRIBUTION_SHORT, ha="left", va="bottom",
                     fontsize=L["attrib_pt"], fontfamily=font, color=INK_SOFT)
            return {"lines": 0}
        _draw_full_footer(fig, font, top, wrap)
        return {"lines": 0}

    left, right = L["map_left"], L["map_right"]
    width_in = (right - left) * FIG_W
    fig.add_artist(plt.Line2D([left, right], [top, top], color=INK,
                              linewidth=L["footer_rule_pt"], alpha=L["footer_rule_alpha"]))

    if L["footer"] == "full":
        # The archival sheet carries the full method paragraphs and citations; they already
        # say everything the feed sheet compresses into the two-line caption.
        _draw_full_footer(fig, font, top - 0.010, wrap, left=left)
        return {"lines": 0}

    # A methodological caption, not body copy: the claim that qualifies every colour on the
    # sheet leads in the sheet's ink and weight, the terrain qualification follows quieter.
    y = q(top - 0.0180)
    step = L["method_pt"] / 72.0 / FIG_H * L["method_leading"]
    lines = 0
    for ln in wrap_to_width(METHOD_LEAD, L["method_lead_pt"], font, width_in, "semibold"):
        fig.text(left, y, ln, ha="left", va="center", fontsize=L["method_lead_pt"],
                 fontfamily=font, fontweight="semibold", color=INK)
        y -= step
        lines += 1
    for ln in wrap_to_width(METHOD_BODY, L["method_pt"], font, width_in):
        fig.text(left, y, ln, ha="left", va="center", fontsize=L["method_pt"],
                 fontfamily=font, color=INK_MID)
        y -= step
        lines += 1

    fig.text(left, L["attrib_y"], ATTRIBUTION_SHORT, ha="left", va="bottom",
             fontsize=L["attrib_pt"], fontfamily=font, color=INK_MID)
    return {"lines": lines, "method_bottom": y + step}


def _draw_full_footer(fig, font: str, top: float, wrap, left: float = 0.055) -> None:
    right_col = left + 0.460
    body_left = (
        "Each colour is the DOMINANT soil group of the HWSD v2.01 mapping unit at that "
        "location — the most extensive soil in a unit that usually contains several. It is "
        "not the soil at any single point, and no field survey was carried out for this map.\n\n"
        "Terrain is shaded relief from SRTMGL3 (~90 m), at 2× vertical exaggeration, used as "
        "context only: it never alters a soil class. The terrain is visualised at finer "
        "spatial detail than the soil data, and that detail does not increase the soil "
        "dataset's native ~1 km resolution."
    )
    body_right = (
        "Water is Natural Earth physical geometry — a cartographic outline, not a "
        "hydrographic observation — and is kept separate from the HWSD “Open Water” "
        "accounting class.\n\n"
        "Projection: Lambert azimuthal equal-area (lat₀ 32°N, lon₀ 53°E). Areas are "
        "comparable across the map; distances are accurate to a fraction of a percent."
    )
    fig.text(left, top, wrap(body_left), ha="left", va="top", fontsize=9.5,
             fontfamily=font, color=INK, linespacing=1.45)
    fig.text(right_col, top, wrap(body_right), ha="left", va="top", fontsize=9.5,
             fontfamily=font, color=INK, linespacing=1.45)

    attribution = (
        "Soils: FAO & IIASA — Harmonized World Soil Database v2.01, Rome and Laxenburg "
        "(DOI 10.4060/cc3823en), licensed CC BY-NC-SA 4.0.   "
        "Terrain: NASA/USGS SRTMGL3.003 (public domain).   "
        "Boundary and water: Made with Natural Earth."
    )
    fig.text(left, 0.021, attribution, ha="left", va="bottom", fontsize=9.5,
             fontfamily=font, color=INK_SOFT, linespacing=1.5)
    fig.text(left, 0.009, "This map is a derivative of HWSD v2.01 and is released under "
                          "CC BY-NC-SA 4.0.  Visual inspiration: Hemed Lungo’s "
                          "terrain-enhanced geospatial cartography (no affiliation).",
             ha="left", va="bottom", fontsize=9, fontfamily=font, color=INK_SOFT)


# --------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="Blender map render PNG")
    ap.add_argument("--width", type=int, default=2500, help="output width px (height = 1.25x)")
    ap.add_argument("--out", default=str(ROOT / "outputs/proof/poster"))
    ap.add_argument("--vector", action="store_true", help="also write PDF and SVG")
    ap.add_argument("--layout", choices=tuple(LAYOUTS), default="master")
    ap.add_argument("--stem", default="iran_soil_landscapes")
    ap.add_argument("--name", default=None, help="exact output stem (overrides --stem/size)")
    args = ap.parse_args()

    L = dict(LAYOUTS[args.layout])
    furniture = json.loads(FURNITURE.read_text(encoding="utf-8"))
    if furniture["labels_failed_verification"]:
        raise SystemExit(f"labels failed verification: {furniture['labels_failed_verification']}")
    surface = yaml.safe_load((ROOT / "config/render_3d.yaml").read_text(encoding="utf-8"))["surface"]
    font = pick_font()
    soils, nonsoil, minor = load_classes()

    img = Image.open(args.map)
    aspect = img.size[0] / img.size[1]
    L["_map_height_frac"] = (L["map_right"] - L["map_left"]) * FIG_W / aspect / FIG_H
    map_bottom = L["map_top"] - L["_map_height_frac"]

    dpi = args.width / FIG_W
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=dpi, facecolor=PAPER)
    draw_title(fig, font, L)
    mapinfo = draw_map(fig, Path(args.map), furniture, font, L, args.width)

    legend_top = (q(map_bottom - L["gap_map_legend"]) if L.get("version") == "v1.1"
                  else map_bottom - 0.024)
    legend_bottom = draw_legend(fig, soils, nonsoil, minor, font,
                                top=legend_top, L=L, surface=surface)
    if legend_bottom < L["footer_top"]:
        raise SystemExit(f"legend overruns the footer block "
                         f"({legend_bottom:.4f} < {L['footer_top']}); layout must be adjusted")
    notes = draw_notes(fig, font, top=L["footer_top"], L=L)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or f"{args.stem}_{args.width}x{int(args.width * 1.25)}"
    png = out_dir / f"{stem}.png"
    fig.savefig(png, dpi=dpi, facecolor=PAPER)
    written = [png]
    if args.vector:
        for ext in ("pdf", "svg"):
            v = out_dir / f"{stem}.{ext}"
            fig.savefig(v, facecolor=PAPER)
            written.append(v)
    plt.close(fig)

    # Build record. The feed sheet is a re-composition rather than a downsample of the
    # master, so "derived from the master" is not the invariant to check. What must hold is
    # that both sheets draw the SAME scientific render, and this records the hash that
    # proves it. The grid is recorded too, so an alignment can be audited from the file.
    import hashlib
    map_path = Path(args.map)
    (out_dir / f"{stem}.build.json").write_text(json.dumps({
        "layout": args.layout,
        "variant": L.get("variant"),
        "map_render": map_path.name,
        "map_render_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
        "output_px": [args.width, int(args.width * 1.25)],
        "figure_in": [FIG_W, FIG_H],
        "type_pt": {"title": L.get("title_pt", 54.0), "map_label_land": L["label_land_pt"],
                    "legend_name": L.get("legend_minor_pt", L.get("legend_name_pt")),
                    "legend_pct": L.get("legend_minor_pct_pt", L.get("legend_pct_pt")),
                    "method": L["method_pt"], "attribution": L["attrib_pt"]},
        "type_pt_extra": {k: L[k] for k in
                          ("subtitle_pt", "legend_head_pt", "legend_major_pt", "rare_pt",
                           "nonsoil_pt", "scale_label_pt", "scale_note_pt", "north_pt",
                           "north_note_pt") if k in L},
        "map_width_fraction": round(L["map_right"] - L["map_left"], 4),
        "grid": {"margin_l": L["map_left"], "margin_r": L["map_right"],
                 "rhythm": GRID["rhythm"], "map_top": L["map_top"],
                 "map_bottom": round(map_bottom, 5),
                 "legend_top": round(legend_top, 5),
                 "legend_bottom": round(legend_bottom, 5),
                 "footer_top": L["footer_top"],
                 "map_height_fraction": round(L["_map_height_frac"], 5)},
        "furniture": {"neatline": mapinfo["neatline"],
                      "national_keyline_pt": float(L.get("boundary_pt", 0.0)),
                      "national_keyline_alpha": L.get("boundary_alpha", 0.0),
                      "scale_bar": mapinfo["scale_bar"],
                      "north": mapinfo["north"],
                      "method_lines": notes.get("lines", 0)},
        "labels_moved": furniture.get("text_placement", {}).get("moved", []),
    }, indent=2) + chr(10), encoding="utf-8")

    for w in written:
        size = Image.open(w).size if w.suffix == ".png" else None
        rel = w.relative_to(ROOT) if w.is_relative_to(ROOT) else w
        print(f"wrote {rel} "
              f"({w.stat().st_size / 1e6:.1f} MB{'' if size is None else f', {size[0]}x{size[1]}'})")
    print(f"layout: {args.layout}; font: {font}; map: {Path(args.map).name}; "
          f"labels: {len(furniture['labels'])}; map width {L['map_right'] - L['map_left']:.3f} "
          f"of sheet; legend bottom {legend_bottom:.4f} (footer at {L['footer_top']})")


if __name__ == "__main__":
    main()
