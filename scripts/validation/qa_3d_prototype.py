"""Objective QA for the 3D prototype: pick the vertical exaggeration by measurement.

Choosing an exaggeration by eye is not defensible. Terrain shading is a multiplier on
the soil palette, so for every rendered pixel inside Iran we can recover it:

    shading = luminance(render) / luminance(flat palette colour at the same pixel)

That gives two competing quantities, measured over identical pixels:

  RELIEF CONTRAST  std(shading)          -- how much landform information the render carries
  SHADOW BURDEN    share(shading < 0.5)  -- how much soil colour is being crushed toward black

The defensible choice is the LOWEST exaggeration whose relief contrast clears the
legibility threshold while the shadow burden stays under budget: the least terrain
distortion that still does the cartographic job.

    python scripts/validation/qa_3d_prototype.py

Writes provenance/metadata/prototype_3d_qa.json.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config/render_3d.yaml"
RENDER = ROOT / "data/processed/render"
BLENDER_DIR = RENDER / "blender"
PROOF = ROOT / "outputs/proof/3d"
OUT = ROOT / "provenance/metadata/prototype_3d_qa.json"

# Legibility thresholds, fixed BEFORE looking at the numbers so the choice is not
# reverse-engineered from the result.
RELIEF_CONTRAST_MIN = 0.060      # std of the shading multiplier inside Iran
SHADOW_BURDEN_MAX = 0.020        # share of Iran pixels crushed below half brightness


def srgb_luminance(rgb: np.ndarray) -> np.ndarray:
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def grid_to_render(arr: np.ndarray, cfg: dict, meta: dict, cam: str) -> np.ndarray:
    """Resample a full-grid layer into the frame the orthographic camera actually shows."""
    rx, ry = cfg["cameras"][cam]["resolution"]
    margin = float(cfg["cameras"][cam]["ortho_margin"])
    ext_x, ext_y = meta["extent_km"]["x"], meta["extent_km"]["y"]
    ortho = margin * max(ext_x, ext_y * rx / ry)          # mirrors place_camera()
    km_per_px = ortho / rx
    w, h = int(round(ext_x / km_per_px)), int(round(ext_y / km_per_px))
    img = Image.fromarray(arr).resize((w, h), Image.NEAREST)
    canvas = Image.new(img.mode, (rx, ry), 0)
    canvas.paste(img, ((rx - w) // 2, (ry - h) // 2))     # camera is centred on the grid
    return np.asarray(canvas)


def class_agreement(render: np.ndarray, base_r: np.ndarray, mask: np.ndarray,
                    palette_hex: list[str]) -> dict:
    """End-to-end registration + palette check on the finished render.

    'Registration is exact by construction' is an argument, not evidence. This measures
    it on the output: diffuse shading scales a pixel's brightness but barely moves its
    chromaticity, so each rendered pixel can be classified back to the nearest palette
    colour and compared with the class the substrate says belongs there. Disagreement
    means the texture slipped, the UVs are wrong, or a class colour is being distorted.
    """
    cols = np.array([[int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
                     for h in palette_hex], dtype=np.float64)

    def chroma(rgb: np.ndarray) -> np.ndarray:
        total = rgb.sum(axis=-1, keepdims=True)
        return np.divide(rgb, total, out=np.full_like(rgb, 1 / 3), where=total > 1e-6)[..., :2]

    pal_c = chroma(cols)
    exp_c = chroma(base_r[mask].astype(np.float64))
    obs_c = chroma(render[mask].astype(np.float64) * 255.0)

    def nearest(points: np.ndarray) -> np.ndarray:
        # Chunked: the full pixel x class distance matrix does not fit in RAM.
        out = np.empty(len(points), dtype=np.int16)
        for i in range(0, len(points), 200_000):
            block = points[i:i + 200_000]
            out[i:i + 200_000] = np.argmin(
                ((block[:, None, :] - pal_c[None, :, :]) ** 2).sum(-1), axis=1)
        return out

    agree = nearest(exp_c) == nearest(obs_c)
    return {"pixels": int(mask.sum()),
            "class_agreement": round(float(agree.mean()), 5),
            "disagreeing_pixels": int((~agree).sum())}


def main() -> None:
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    meta = json.loads((BLENDER_DIR / "blender_inputs.json").read_text(encoding="utf-8"))

    soil_a = np.asarray(Image.open(RENDER / "iran_soil_texture.png").convert("RGBA"))[..., 3]
    water = np.asarray(Image.open(RENDER / "iran_water_mask.png").convert("L"))
    base = np.asarray(Image.open(BLENDER_DIR / "iran_render_basecolor.png").convert("RGB"))
    # Iran land only: water is a display layer and would skew both statistics.
    land = (soil_a > 0) & (water < int(cfg["surface"]["water_threshold"]))

    land_r = grid_to_render(land.astype(np.uint8), cfg, meta, "topdown") > 0
    base_r = grid_to_render(base, cfg, meta, "topdown")

    # Measure only where the palette colour is locally constant. At a class boundary a
    # one-pixel disagreement between the resampled palette and the render produces a huge
    # luminance ratio that has nothing to do with terrain, and that contamination is
    # identical at every exaggeration — it puts a floor under the statistic and would make
    # a flat render look like it carried relief.
    flat = np.ones(base_r.shape[:2], dtype=bool)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        shifted = np.roll(np.roll(base_r, dy, axis=0), dx, axis=1)
        flat &= (shifted == base_r).all(axis=2)
    edge_share = float((land_r & ~flat).sum()) / float(land_r.sum())
    land_r = land_r & flat
    base_lum = srgb_luminance(base_r[land_r].astype(np.float64) / 255.0)

    def stats(path: Path) -> dict | None:
        if not path.exists():
            return None
        img = np.asarray(Image.open(path).convert("RGB")).astype(np.float64) / 255.0
        lum = srgb_luminance(img[land_r])
        shading = np.divide(lum, base_lum, out=np.zeros_like(lum), where=base_lum > 1e-6)
        return {
            "relief_contrast_std": round(float(shading.std()), 4),
            "shadow_burden_below_0.5": round(float((shading < 0.5).mean()), 4),
            "mean_shading": round(float(shading.mean()), 4),
            "p01_shading": round(float(np.percentile(shading, 1)), 4),
            "meets_relief_threshold": bool(shading.std() >= RELIEF_CONTRAST_MIN),
            "within_shadow_budget": bool((shading < 0.5).mean() <= SHADOW_BURDEN_MAX),
        }

    results = {}
    for k in cfg["exaggeration_tests"]:
        st = stats(PROOF / f"iran_3d_{k}x_topdown.png")
        if st:
            results[f"{k}x"] = st

    # Registration/palette fidelity measured on the selected render itself.
    pal = yaml.safe_load((ROOT / "config/soil_palette.yaml").read_text(encoding="utf-8"))
    codes = [r["classification_code"] for r in csv.DictReader(
        (ROOT / "data/processed/tables/soil_groups_iran.csv").open(encoding="utf-8"))]
    palette_hex = [pal["wrb2_rsg_colours"][c] for c in codes]

    passing = [k for k, v in results.items()
               if v["meets_relief_threshold"] and v["within_shadow_budget"]]
    selected = passing[0] if passing else None

    # CAMERA_TEST, computed rather than eyeballed. The oblique buys relief silhouette and
    # pays in foreshortening; at national scale both terms are exactly calculable.
    k_sel = int(selected.rstrip("x")) if selected else max(cfg["exaggeration_tests"])
    tilt = math.radians(float(cfg["cameras"]["oblique"]["tilt_deg"]))
    rx, ry = cfg["cameras"]["oblique"]["resolution"]
    ext_x, ext_y = meta["extent_km"]["x"], meta["extent_km"]["y"]
    relief_km = meta["elevation_m"]["max"] / 1000.0 * k_sel
    ortho = float(cfg["cameras"]["oblique"]["ortho_margin"]) * max(
        ext_x, (ext_y * math.cos(tilt) + 2.0 * relief_km * math.sin(tilt)) * rx / ry)
    km_per_px = ortho / rx
    camera = {
        "at_exaggeration": f"{k_sel}x",
        "oblique_tilt_deg": cfg["cameras"]["oblique"]["tilt_deg"],
        "oblique_north_south_compression": round(math.cos(tilt), 4),
        "oblique_relief_silhouette_px": round(relief_km * math.sin(tilt) / km_per_px, 1),
        "frame_width_px": rx,
        "note": "Relief silhouette is what the oblique adds: the tallest point in Iran rises "
                "this many pixels above the datum in a frame this wide. Compression is what it "
                "costs: north-south scale is multiplied by cos(tilt), so the map no longer has "
                "one scale and areas cannot be compared.",
    }

    sel_render = PROOF / f"iran_3d_{selected}_topdown.png" if selected else None
    registration = None
    if sel_render and sel_render.exists():
        img = np.asarray(Image.open(sel_render).convert("RGB")).astype(np.float64) / 255.0
        registration = class_agreement(img, base_r, land_r, palette_hex)
        registration["render"] = sel_render.name

    # LIGHTING_TEST, same statistic: the best sun elevation is the one that carries the
    # most relief information while keeping soil colour out of the shadows.
    lighting = {}
    if selected:
        for v in cfg["lighting"]["variants"]:
            st = stats(PROOF / f"iran_3d_light_{v['name']}_{selected}_topdown.png")
            if st:
                st["sun_elevation_deg"] = v["elevation_deg"]
                st["sun_azimuth_deg"] = v["azimuth_deg"]
                lighting[v["name"]] = st
    lit_ok = {k: v for k, v in lighting.items() if v["within_shadow_budget"]}
    lighting_selected = max(lit_ok, key=lambda k: lit_ok[k]["relief_contrast_std"]) if lit_ok else None

    payload = {
        "thresholds": {"relief_contrast_min": RELIEF_CONTRAST_MIN,
                       "shadow_burden_max": SHADOW_BURDEN_MAX,
                       "note": "fixed before measurement; selection = lowest exaggeration meeting both"},
        "pixels_measured_iran_land": int(land_r.sum()),
        "class_edge_pixels_excluded_share": round(edge_share, 4),
        "by_exaggeration": results,
        "selected_exaggeration": selected,
        "camera_test": camera,
        "registration_on_render": registration,
        "lighting_test": {"by_variant": lighting, "selected": lighting_selected,
                          "rule": "most relief contrast among variants within the shadow budget"},
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Iran land pixels measured: {int(land_r.sum()):,} "
          f"(excluded {edge_share:.1%} as class-boundary pixels)")
    print(f"{'exag':>5} {'relief_std':>11} {'shadow<0.5':>11} {'mean':>7}  verdict")
    for k, v in results.items():
        ok = "PASS" if (v["meets_relief_threshold"] and v["within_shadow_budget"]) else (
            "relief too low" if not v["meets_relief_threshold"] else "shadow over budget")
        print(f"{k:>5} {v['relief_contrast_std']:>11.4f} {v['shadow_burden_below_0.5']:>11.4f} "
              f"{v['mean_shading']:>7.3f}  {ok}")
    print(f"SELECTED: {selected} (lowest exaggeration meeting both criteria)")
    for name, v in lighting.items():
        print(f"light {name:>8} (sun {v['sun_elevation_deg']:>2}deg): relief "
              f"{v['relief_contrast_std']:.4f}  shadow {v['shadow_burden_below_0.5']:.4f}"
              f"{'  <- selected' if name == lighting_selected else ''}")
    if registration:
        print(f"registration on {registration['render']}: "
              f"{registration['class_agreement']:.3%} of Iran land pixels still classify to "
              f"their substrate class ({registration['disagreeing_pixels']:,} disagree)")
    print(f"camera: oblique at {camera['at_exaggeration']} raises the highest summit "
          f"{camera['oblique_relief_silhouette_px']} px in a {rx} px frame, "
          f"and compresses north-south scale to {camera['oblique_north_south_compression']:.3f}")


if __name__ == "__main__":
    main()
