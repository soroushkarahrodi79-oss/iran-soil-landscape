"""Should the map carry a national keyline at all? Measure the gain and the bill.

A thin stroke along Iran's outline is the standard way to sharpen a silhouette, and on this
sheet it looks good. That is not the test. The test is what it costs, because the stroke is
drawn along the one line where the soil data is least forgiving: every border and coastal
HWSD pixel sits directly under it.

Two numbers decide it.

  THE GAIN   How much figure/ground separation the map needs that it does not already have.
             Iran's mean soil surface against the neutral ground outside it is measured on
             the render and compared with the ΔE00 >= 10 threshold this project applies to
             every other colour decision.

  THE BILL   The stroke's width converted to ground distance at feed size, against HWSD's
             ~1 km native support, and the share of Iran's mapped area that falls under it.

A stroke narrow enough to stay inside one HWSD pixel is too thin to survive the 540 px feed
reduction; a stroke that survives the reduction is wider than the data it runs along. The
script reports both ends of that trade rather than picking a comfortable middle.

    python scripts/validation/qa_keyline_decision.py

Writes provenance/metadata/keyline_decision_v11.json and, for visual inspection, a pair of
crops of the same corner of the map with and without the stroke.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs/proof/furniture_v11"
FURNITURE = ROOT / "provenance/metadata/map_furniture_qa.json"
RENDER_CFG = ROOT / "config/render_3d.yaml"
RENDER_DIR = ROOT / "data/processed/render"
RENDER = ROOT / "outputs/proof/3d/iran_map_2x_topdown_5400x4897.png"
OUT = ROOT / "provenance/metadata/keyline_decision_v11.json"

DELTA_E_MIN = 10.0              # the project's standing separation threshold
HWSD_SUPPORT_KM = 1.0
MIN_RULE_PX_AT_540 = 0.85
CANDIDATE_PT = (0.6, 0.9, 1.2, 1.6, 2.0)
FIG_W_IN, PREVIEW_W = 20.0, 540
MAP_CROP = 0.015


def _qp():
    spec = importlib.util.spec_from_file_location(
        "qa_palette_final", ROOT / "scripts/validation/qa_palette_final.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


qp = _qp()


def main() -> None:
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))["surface"]
    fq = json.loads(FURNITURE.read_text(encoding="utf-8"))

    # --- THE GAIN -------------------------------------------------------------------
    base = np.asarray(Image.open(RENDER_DIR / "blender/iran_render_basecolor.png")
                      .convert("RGB"))
    ids = np.asarray(Image.open(RENDER_DIR / "iran_soil_ids_render.tif"))
    water = np.asarray(Image.open(RENDER_DIR / "iran_water_mask.png").convert("L"))
    wet = water >= int(cfg["water_threshold"])
    soil = (ids > 0) & ~wet

    # The silhouette is not read from Iran's average colour but from whatever happens to lie
    # against the border, so the border ring itself is what has to separate.
    ring = np.zeros_like(soil)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        ring |= soil & ~np.roll(np.roll(soil, dy, axis=0), dx, axis=1)
    outside = qp.srgb_to_lab(qp.hex_to_rgb01(cfg["context_land_srgb"]))
    ring_rgb = base[ring].astype(np.float64) / 255.0
    ring_lab = qp.srgb_to_lab(ring_rgb)
    de_ring = qp.ciede2000(ring_lab, np.broadcast_to(outside, ring_lab.shape))
    mean_lab = qp.srgb_to_lab(base[soil].mean(axis=0) / 255.0)

    gain = {
        "iran_mean_vs_outside_delta_e2000": round(float(qp.ciede2000(mean_lab, outside)), 2),
        "iran_mean_vs_outside_delta_L": round(abs(float(mean_lab[0] - outside[0])), 2),
        "border_ring_px": int(ring.sum()),
        "border_ring_delta_e2000_mean": round(float(de_ring.mean()), 2),
        "border_ring_delta_e2000_p10": round(float(np.percentile(de_ring, 10)), 2),
        "border_ring_share_below_threshold":
            round(float((de_ring < DELTA_E_MIN).mean()), 4),
        "threshold": DELTA_E_MIN,
    }

    # --- THE BILL -------------------------------------------------------------------
    span_km = fq["map_frame"]["ortho_width_km"] * (1.0 - 2.0 * MAP_CROP)
    map_frac = 0.864
    km_per_px_540 = span_km / (map_frac * PREVIEW_W)
    border_km = 0.0
    for line in fq["boundary"]["polylines_frac"]:
        xy = np.asarray(line)
        d = np.diff(xy, axis=0) * np.array([fq["map_frame"]["ortho_width_km"],
                                            fq["map_frame"]["ortho_height_km"]])
        border_km += float(np.hypot(d[:, 0], d[:, 1]).sum())
    iran_km2 = 1_612_385.0                       # classified soil area, area_qa.json

    bill = []
    for pt in CANDIDATE_PT:
        px540 = pt / 72.0 * (PREVIEW_W / FIG_W_IN)
        width_km = px540 * km_per_px_540
        covered = border_km * width_km
        bill.append({
            "linewidth_pt": pt,
            "px_at_540": round(px540, 3),
            "resolves_at_540": bool(px540 >= MIN_RULE_PX_AT_540),
            "ground_width_km": round(width_km, 2),
            "within_one_hwsd_pixel": bool(width_km < HWSD_SUPPORT_KM),
            "soil_area_under_stroke_km2": round(covered, 0),
            "share_of_mapped_iran_percent": round(covered / iran_km2 * 100.0, 2),
        })

    workable = [b for b in bill if b["resolves_at_540"] and b["within_one_hwsd_pixel"]]
    silhouette_already_clears = gain["iran_mean_vs_outside_delta_e2000"] >= DELTA_E_MIN

    if workable:
        verdict = "DRAW_KEYLINE"
        reason = (f"{workable[0]['linewidth_pt']} pt both resolves at feed size and stays "
                  f"inside one HWSD pixel")
    elif silhouette_already_clears:
        verdict = "REJECT_KEYLINE"
        reason = ("no width both resolves at 540 px and stays inside HWSD's ~1 km support, "
                  f"and the silhouette already separates at dE00 "
                  f"{gain['iran_mean_vs_outside_delta_e2000']} >= {DELTA_E_MIN} without one")
    else:
        verdict = "DRAW_KEYLINE_DESPITE_COST"
        reason = ("the silhouette does not separate on colour alone, so the stroke buys "
                  "something the map cannot get otherwise")

    # --- visual proof: the same corner, with and without ------------------------------
    # The render arrays above are hundreds of megabytes; the composition subprocess needs
    # that memory back before it can load the 5400 px map.
    import gc
    del base, ids, water, wet, soil, ring, ring_rgb, ring_lab, de_ring
    gc.collect()

    crops = {}
    for tag, extra in (("keyline_on", []), ("keyline_off", [])):
        stem = f"keyline_proof_{tag}"
        layout = "v11_b_keyline" if tag == "keyline_on" else "v11_b_nokeyline"
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/rendering/build_poster.py"),
             "--map", str(RENDER), "--width", "2160", "--layout", layout,
             "--out", str(OUT_DIR), "--name", stem], capture_output=True, text=True)
        if r.returncode:
            sys.stderr.write(r.stderr)
            raise SystemExit(f"could not compose {layout}")
        im = Image.open(OUT_DIR / f"{stem}.png").convert("RGB")
        w, h = im.size
        crop = im.crop((int(0.05 * w), int(0.10 * h), int(0.45 * w), int(0.24 * h)))
        cp = OUT_DIR / f"{stem}_nw_corner.png"
        crop.save(cp, optimize=True)
        crops[tag] = cp.name
        (OUT_DIR / f"{stem}.png").unlink()
        (OUT_DIR / f"{stem}.build.json").unlink()

    payload = {"gain": gain, "border_length_km": round(border_km, 0),
               "mapped_iran_km2": iran_km2,
               "bill_by_linewidth": bill, "visual_proof": crops,
               "verdict": verdict, "reason": reason}
    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    print("THE GAIN")
    print(f"  Iran mean soil vs ground outside Iran: dE00 "
          f"{gain['iran_mean_vs_outside_delta_e2000']}, dL "
          f"{gain['iran_mean_vs_outside_delta_L']} (threshold {DELTA_E_MIN})")
    print(f"  border ring {gain['border_ring_px']:,} px: mean dE00 "
          f"{gain['border_ring_delta_e2000_mean']}, p10 "
          f"{gain['border_ring_delta_e2000_p10']}, "
          f"{gain['border_ring_share_below_threshold'] * 100:.1f}% of the ring below "
          f"threshold")
    print(f"\nTHE BILL  (border {border_km:,.0f} km)")
    print(f"  {'pt':>5}{'px@540':>9}{'resolves':>10}{'km wide':>9}{'<1km':>7}"
          f"{'soil km2':>11}{'% Iran':>8}")
    for b in bill:
        print(f"  {b['linewidth_pt']:>5.1f}{b['px_at_540']:>9.3f}"
              f"{str(b['resolves_at_540']):>10}{b['ground_width_km']:>9.2f}"
              f"{str(b['within_one_hwsd_pixel']):>7}"
              f"{b['soil_area_under_stroke_km2']:>11,.0f}"
              f"{b['share_of_mapped_iran_percent']:>8.2f}")
    print(f"\nVERDICT: {verdict}\n  {reason}")
    print(f"visual proof: {crops}")


if __name__ == "__main__":
    main()
