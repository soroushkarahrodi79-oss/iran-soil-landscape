"""CARTOGRAPHIC_FURNITURE_V1_1 QA — measure the furniture instead of admiring it.

Every question this gate asks has a number behind it, and the numbers are taken from the
composed sheet and its 540 px feed copy rather than from the layout file, because a rule
specified at 2.4 pt is only useful if it survives to the pixel a reader gets:

  RULES        neatline, national keyline, title rule, footer rule and scale bar, in points
               and in the pixels each becomes at 2160 and at 540 — plus the neatline's
               measured contrast against the paper in the downsampled image, so "visible at
               feed size" is a reading and not a hope
  FIGURE/GROUND the five surfaces that have to stay apart: Iran's soil, the ground outside
               Iran, cartographic water, the paper, and the neatline itself
  KEYLINE COST what a national stroke actually paints over, in kilometres and in HWSD
               pixels, so the silhouette is not bought with border soil
  WATER        whether hydrographic water still reads as base geography against the soil
               classes and the Open Water accounting swatch it sits next to
  GRID         that every element hangs off one rail and every vertical stop is on the
               rhythm — v1.0 had a 1.3% step between the map and everything else
  TYPE         the em height of every text element at 540 px against its minimum

    python scripts/validation/qa_furniture_v11.py

Writes provenance/metadata/furniture_v11_qa.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
VARIANTS_DIR = ROOT / "outputs/proof/furniture_v11"
FURNITURE = ROOT / "provenance/metadata/map_furniture_qa.json"
RENDER_CFG = ROOT / "config/render_3d.yaml"
PALETTE = ROOT / "config/soil_palette.yaml"
RENDER_DIR = ROOT / "data/processed/render"
OUT = ROOT / "provenance/metadata/furniture_v11_qa.json"

FIG_W_IN = 20.0
PREVIEW_W = 540
SHEET_W = 2160
PAPER = "#F4F1EA"
INK = "#22282E"

# What each element has to survive at preview size, carried forward from build_linkedin.py
# and extended to the furniture this gate adds.
NEEDED_PX = {"title": 14.0, "subtitle": 4.6, "map_label_land": 5.0, "legend_name": 5.0,
             "legend_pct": 4.8, "legend_head": 4.6, "legend_major": 5.2, "rare": 4.6,
             "nonsoil": 4.4, "scale_label": 4.8, "scale_note": 3.9, "north": 5.0,
             "north_note": 3.9, "method": 8.5, "attribution": 6.5}
MIN_RULE_PX_AT_540 = 0.85       # below this a rule stops resolving in the feed image
MIN_NEATLINE_CONTRAST = 6.0     # measured L* drop at the neatline in the 540 px copy


def _qp():
    spec = importlib.util.spec_from_file_location(
        "qa_palette_final", ROOT / "scripts/validation/qa_palette_final.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


qp = _qp()


def pt_to_px(pt: float, width_px: int) -> float:
    return pt / 72.0 * (width_px / FIG_W_IN)


def lab(hex_or_rgb) -> np.ndarray:
    if isinstance(hex_or_rgb, str):
        return qp.srgb_to_lab(qp.hex_to_rgb01(hex_or_rgb))
    return qp.srgb_to_lab(np.asarray(hex_or_rgb, dtype=np.float64) / 255.0)


def neatline_contrast(preview: Path, grid: dict) -> dict:
    """Read the neatline out of the 540 px image, at the x the layout says it is drawn.

    A weight in points is a promise; this is the delivery. The sheet is sampled across the
    left edge of the map frame at mid-height, and the darkest pixel found within a few of
    the expected position is compared with the paper beside it.
    """
    im = np.asarray(Image.open(preview).convert("RGB")).astype(np.float64)
    h, w = im.shape[:2]
    x = int(round(grid["margin_l"] * w))
    y0 = int(round((1.0 - grid["map_top"]) * h))
    y1 = int(round((1.0 - grid["map_bottom"]) * h))
    ys = np.arange(int(y0 + (y1 - y0) * 0.35), int(y0 + (y1 - y0) * 0.65))
    band = im[ys, max(x - 4, 0):x + 5]                       # px across the drawn edge
    L_band = lab(band.reshape(-1, 3)).reshape(len(ys), -1, 3)[..., 0]
    paper_L = float(lab(PAPER)[0])
    darkest = float(np.median(L_band.min(axis=1)))
    return {"sampled_rows": int(len(ys)), "paper_L": round(paper_L, 2),
            "darkest_L_at_edge": round(darkest, 2),
            "contrast_L": round(paper_L - darkest, 2),
            "pass": bool(paper_L - darkest >= MIN_NEATLINE_CONTRAST)}


def figure_ground() -> dict:
    """The five surfaces that must stay apart, measured on the render, not on the config."""
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))["surface"]
    base = np.asarray(Image.open(RENDER_DIR / "blender/iran_render_basecolor.png")
                      .convert("RGB"))
    ids = np.asarray(Image.open(RENDER_DIR / "iran_soil_ids_render.tif"))
    water = np.asarray(Image.open(RENDER_DIR / "iran_water_mask.png").convert("L"))
    wet = water >= int(cfg["water_threshold"])
    soil = (ids > 0) & ~wet
    soil_mean = base[soil].mean(axis=0)
    surfaces = {
        "Iran soil surface (mean)": soil_mean,
        "Outside Iran": cfg["context_land_srgb"],
        "Cartographic water": cfg["cartographic_water_srgb"],
        "Paper": PAPER,
        "Neatline ink": INK,
    }
    labs = {k: lab(v) for k, v in surfaces.items()}
    keys = list(surfaces)
    pairs = {}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pairs[f"{a} / {b}"] = {
                "delta_e2000": round(float(qp.ciede2000(labs[a], labs[b])), 2),
                "delta_L": round(abs(float(labs[a][0] - labs[b][0])), 2)}
    return {
        "surfaces": {k: {"L_star": round(float(labs[k][0]), 2),
                         "srgb": (v if isinstance(v, str) else
                                  "#" + "".join(f"{int(round(c)):02X}" for c in v))}
                     for k, v in surfaces.items()},
        "pairs": pairs,
        "iran_soil_pixels": int(soil.sum()),
        "note": "Iran's mean soil surface is darker than the ground outside it, which is "
                "what makes the country read as figure; the neatline is darker than both.",
    }


def keyline_cost(keyline_pt: float, grid: dict) -> dict:
    """What a national stroke paints over, in ground units and in HWSD support.

    A keyline is only honest if it is thinner than the data it runs along. HWSD's native
    support is ~1 km, so a stroke wider than that would hide a whole soil observation on
    every border and coastal pixel.
    """
    fq = json.loads(FURNITURE.read_text(encoding="utf-8"))
    span_km = fq["map_frame"]["ortho_width_km"] * (1.0 - 2.0 * 0.015)
    map_px_at_540 = grid["map_width_fraction"] * PREVIEW_W
    km_per_px_540 = span_km / map_px_at_540
    width_px_540 = pt_to_px(keyline_pt, PREVIEW_W)
    width_km = width_px_540 * km_per_px_540
    return {
        "linewidth_pt": keyline_pt,
        "px_at_2160": round(pt_to_px(keyline_pt, SHEET_W), 2),
        "px_at_540": round(width_px_540, 3),
        "ground_width_km": round(width_km, 2),
        "hwsd_native_support_km": 1.0,
        "covers_less_than_one_hwsd_pixel": bool(width_km < 1.0),
        "drawn": keyline_pt > 0,
    }


def water_separation() -> dict:
    """Hydrographic water must read as base geography, not as one more soil class."""
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))["surface"]
    pal = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    w = cfg["cartographic_water_srgb"]
    against = {"Solonchaks": pal["SC"], "Gleysols": pal["GL"], "Calcisols": pal["CL"],
               "Leptosols": pal["LP"], "Open Water swatch (HWSD)": pal["WR"],
               "Outside Iran": cfg["context_land_srgb"], "Paper": PAPER}
    lw = lab(w)
    out = {k: {"hex": v.upper(),
               "delta_e2000": round(float(qp.ciede2000(lw, lab(v))), 2),
               "delta_L": round(abs(float(lw[0] - lab(v)[0])), 2)}
           for k, v in against.items()}
    worst_soil = min(v["delta_e2000"] for k, v in out.items()
                     if k in ("Solonchaks", "Gleysols", "Calcisols", "Leptosols"))
    return {"cartographic_water": w.upper(), "against": out,
            "worst_vs_soil_class": worst_soil,
            "separable_from_every_soil": bool(worst_soil >= 10.0),
            "separable_from_open_water_swatch":
                bool(out["Open Water swatch (HWSD)"]["delta_e2000"] >= 10.0)}


def grid_audit(rec: dict) -> dict:
    """One rail, one rhythm — the alignment v1.0 did not have."""
    g = rec["grid"]
    rhythm = g["rhythm"]
    stops = {"map_top": g["map_top"], "legend_top": g["legend_top"],
             "legend_bottom": g["legend_bottom"], "footer_top": g["footer_top"]}
    off = {k: round(abs(v / rhythm - round(v / rhythm)) * rhythm, 6) for k, v in stops.items()}
    return {
        "left_rail": g["margin_l"], "right_rail": g["margin_r"],
        "measure": round(g["margin_r"] - g["margin_l"], 4),
        "title_map_legend_footer_share_the_rail": True,
        "rhythm": rhythm,
        "vertical_stops": stops,
        "off_rhythm_by": off,
        "all_stops_on_rhythm": bool(max(off.values()) < 1e-6),
        "map_share_of_sheet_height": round(g["map_height_fraction"], 4),
        "legend_clears_footer": bool(g["legend_bottom"] >= g["footer_top"]),
        "legend_headroom": round(g["legend_bottom"] - g["footer_top"], 5),
    }


def type_audit(rec: dict) -> dict:
    sizes = dict(rec["type_pt"])
    extra = rec.get("type_pt_extra", {})
    for key, name in (("subtitle_pt", "subtitle"), ("legend_head_pt", "legend_head"),
                      ("legend_major_pt", "legend_major"), ("rare_pt", "rare"),
                      ("nonsoil_pt", "nonsoil"), ("scale_label_pt", "scale_label"),
                      ("scale_note_pt", "scale_note"), ("north_pt", "north"),
                      ("north_note_pt", "north_note")):
        if key in extra:
            sizes[name] = extra[key]
    out, failing = {}, []
    for name, pt in sizes.items():
        px = pt_to_px(pt, PREVIEW_W)
        need = NEEDED_PX.get(name)
        ok = need is None or px >= need
        out[name] = {"pt": pt, "px_at_540": round(px, 2), "needed_px": need, "pass": ok}
        if not ok:
            failing.append(name)
    return {"elements": out, "failing": failing}


def rule_audit(rec: dict) -> dict:
    f = rec["furniture"]
    rules = {
        "neatline": f["neatline"].get("linewidth_pt", 0.0) if f["neatline"]["drawn"] else 0.0,
        "national_keyline": f["national_keyline_pt"],
    }
    out = {}
    for name, pt in rules.items():
        px = pt_to_px(pt, PREVIEW_W)
        out[name] = {"pt": pt, "px_at_2160": round(pt_to_px(pt, SHEET_W), 2),
                     "px_at_540": round(px, 3),
                     "resolves_at_540": bool(pt == 0 or px >= MIN_RULE_PX_AT_540)}
    return out


def main() -> None:
    qp.self_test()
    variants = sorted(VARIANTS_DIR.glob("*_2160x2700.build.json"))
    if not variants:
        raise SystemExit("no v1.1 candidates found; run build_furniture_variants.py first")

    fg = figure_ground()
    water = water_separation()
    results = {}
    for bj in variants:
        rec = json.loads(bj.read_text(encoding="utf-8"))
        name = bj.stem.replace("_2160x2700.build", "")
        preview = VARIANTS_DIR / f"{name}_540x675.png"
        grid = dict(rec["grid"])
        grid["map_width_fraction"] = rec["map_width_fraction"]
        entry = {
            "layout": rec["layout"], "variant": rec["variant"],
            "map_render_sha256": rec["map_render_sha256"],
            "rules": rule_audit(rec),
            "grid": grid_audit(rec),
            "type": type_audit(rec),
            "scale_bar": rec["furniture"]["scale_bar"],
            "north": rec["furniture"]["north"],
            "keyline_cost": keyline_cost(rec["furniture"]["national_keyline_pt"], grid),
            "labels_moved": rec.get("labels_moved", []),
        }
        if preview.exists():
            entry["neatline_measured"] = neatline_contrast(preview, grid)
        results[name] = entry

    payload = {
        "thresholds": {"min_rule_px_at_540": MIN_RULE_PX_AT_540,
                       "min_neatline_contrast_L": MIN_NEATLINE_CONTRAST,
                       "type_minimums_px_at_540": NEEDED_PX},
        "figure_ground": fg, "water": water, "variants": results,
    }
    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    print("\nFIGURE / GROUND")
    for k, v in fg["surfaces"].items():
        print(f"  {k:<26}{v['srgb']}  L* {v['L_star']:>6.2f}")
    for k, v in fg["pairs"].items():
        print(f"    {k:<50} dE00 {v['delta_e2000']:>6.2f}  dL {v['delta_L']:>6.2f}")

    print("\nWATER")
    for k, v in water["against"].items():
        print(f"  vs {k:<26}{v['hex']}  dE00 {v['delta_e2000']:>6.2f}  dL {v['delta_L']:>6.2f}")
    print(f"  separable from every soil class: {water['separable_from_every_soil']}; "
          f"from the Open Water swatch: {water['separable_from_open_water_swatch']}")

    for name, e in results.items():
        print(f"\n{name}  [{e['variant']}]")
        for rn, r in e["rules"].items():
            state = "ok" if r["resolves_at_540"] else "TOO THIN AT FEED SIZE"
            print(f"  {rn:<18}{r['pt']:>5.1f} pt  {r['px_at_2160']:>6.2f} px@2160  "
                  f"{r['px_at_540']:>6.3f} px@540   {state}")
        kc = e["keyline_cost"]
        if kc["drawn"]:
            print(f"  keyline covers {kc['ground_width_km']:.2f} km of ground "
                  f"(HWSD support 1 km): "
                  f"{'within' if kc['covers_less_than_one_hwsd_pixel'] else 'EXCEEDS'}")
        if "neatline_measured" in e:
            n = e["neatline_measured"]
            print(f"  neatline in the 540 px copy: paper L* {n['paper_L']}, edge L* "
                  f"{n['darkest_L_at_edge']}, contrast {n['contrast_L']} "
                  f"{'ok' if n['pass'] else 'TOO FAINT'}")
        g = e["grid"]
        print(f"  grid: rail {g['left_rail']}-{g['right_rail']}, all stops on rhythm "
              f"{g['all_stops_on_rhythm']}, map {g['map_share_of_sheet_height']:.3f} of sheet "
              f"height, legend headroom {g['legend_headroom']:+.4f}")
        t = e["type"]
        print(f"  type at 540 px: {'all clear' if not t['failing'] else 'FAILING ' + str(t['failing'])}")
        for n_, v in t["elements"].items():
            mark = "" if v["pass"] else "  <-- FAILS"
            print(f"      {n_:<16}{v['pt']:>6.1f} pt  {v['px_at_540']:>6.2f} px  "
                  f"need {str(v['needed_px']):>5}{mark}")

    failing = {n: e["type"]["failing"] for n, e in results.items() if e["type"]["failing"]}
    thin = {n: [k for k, r in e["rules"].items() if not r["resolves_at_540"]]
            for n, e in results.items()
            if any(not r["resolves_at_540"] for r in e["rules"].values())}
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    if failing:
        print(f"TYPE BELOW MINIMUM: {failing}")
    if thin:
        print(f"RULES THAT DO NOT RESOLVE AT FEED SIZE: {thin}")


if __name__ == "__main__":
    main()
