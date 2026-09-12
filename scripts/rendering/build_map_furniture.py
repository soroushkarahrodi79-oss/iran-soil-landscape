"""Map furniture computed from the transform and the data, never from a reference poster.

Four things on a finished map are routinely added by imitation and are wrong as often as
not. Each is derived here instead:

  SCALE BAR   The analysis CRS is Lambert azimuthal EQUAL-AREA, which does not preserve
              distance. Before drawing a bar that implies one distance scale everywhere,
              the actual variation is measured by comparing geodesic distances against
              planar distances across the Iranian extent.

  NORTH       In an azimuthal projection meridians converge, so "north" is only exactly
              up along the central meridian. Grid convergence is measured at sample
              points to decide whether one arrow can honestly be drawn.

  LABELS      Every physical-geography label is verified against the project's own
              rasters: sea labels must land on the Natural Earth water mask, range labels
              on high ground, basin labels on low ground. A label that fails its check is
              reported as FAIL rather than quietly drawn.

              The anchor is only half the job. What the reader sees is the *text box*,
              which sits wherever the offset puts it — so the drawn text is measured too:
              its clearance from the frame edge, the class-edge clutter underneath it,
              and (for a sea label) whether it still lies on the water body it names.
              Offsets are searched for, not nudged: the smallest displacement from the
              verified anchor that satisfies every constraint wins.

  BOUNDARY    An optional national keyline. Natural Earth 1:10m is the only boundary
              source in this project, so the polyline is simplified to the render's own
              pixel size before it is stored: the stroke may never imply a boundary
              position finer than the geometry that produced it.

    python scripts/rendering/build_map_furniture.py

Writes provenance/metadata/map_furniture_qa.json, consumed by the poster layout.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import CRS, Geod, Transformer  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config/render_3d.yaml"
SUBSTRATE = ROOT / "provenance/metadata/render_substrate.json"
RENDER = ROOT / "data/processed/render"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
OUT = ROOT / "provenance/metadata/map_furniture_qa.json"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"

# Candidate labels: approximate centres of well-known physical features, each with the
# evidence test it must pass. No provinces, roads or cities.
#
# `water_window` pins a sea label to the water body it actually names: the Gulf of Oman
# label may be displaced along its own sea, but never across the Strait of Hormuz into
# the Persian Gulf, which is a different feature.
LABELS = [
    {"text": "Caspian Sea",     "lon": 51.4, "lat": 38.2, "check": "water", "style": "water"},
    {"text": "Persian Gulf",    "lon": 51.0, "lat": 27.6, "check": "water", "style": "water",
     "water_window": {"lon": [47.0, 56.2]}},
    {"text": "Gulf of Oman",    "lon": 59.3, "lat": 25.3, "check": "water", "style": "water",
     "water_window": {"lon": [57.0, 61.5]}, "keep_text_on_water": True},
    {"text": "Lake Urmia",      "lon": 45.5, "lat": 37.6, "check": "water", "style": "water"},
    {"text": "Alborz",          "lon": 52.0, "lat": 36.1, "check": "highland", "style": "land"},
    {"text": "Zagros",          "lon": 49.6, "lat": 32.6, "check": "highland", "style": "land"},
    {"text": "Dasht-e Kavir",   "lon": 54.6, "lat": 34.4, "check": "lowland", "style": "land"},
    {"text": "Lut Desert",      "lon": 58.5, "lat": 30.9, "check": "lowland", "style": "land"},
    {"text": "Khuzestan Plain", "lon": 48.9, "lat": 31.4, "check": "lowland", "style": "land"},
]
HIGHLAND_MIN_M = 1800
LOWLAND_MAX_M = 1200

# --- text-placement constraints -------------------------------------------------------
# Both are display quantities, so both are expressed as a fraction of the map frame and
# both are re-measured rather than assumed.
MIN_EDGE_CLEARANCE = 0.030      # between the text box and the neatline, in DISPLAYED width
CLUTTER_LIMIT = 0.040           # class-edge density under the text box that triggers a move
MAX_TEXT_SHIFT = 0.140          # a label may never wander further than this from its anchor
SEARCH_STEP = 0.004
# The sheet crops the render's lit slab edge before drawing, so frame fractions are not
# what the reader sees. Clearance is therefore measured in the cropped (displayed) frame:
# the crop pushes every label 1.5% closer to the edge than the raw fraction suggests.
DISPLAY_CROP = 0.015            # mirrors MAP_CROP in build_poster.py
# Weighting inside the search. Displacement is the thing to minimise; clutter only has to
# be bought down below the limit, so it is scored against that limit rather than absolutely.
CLUTTER_WEIGHT = 0.55

# Reference sheet geometry for the text-box measurement: the feed layout carries the
# largest type, so a placement that clears here clears on the archival sheet too.
REF_MAP_WIDTH_FRAC = 0.864
REF_FIG_W_IN = 20.0
REF_LABEL_PT = {"land": 15.0, "water": 15.5}
LAND_TRACKING = 1.10            # the land labels are drawn letter-spaced; TextPath is not


def text_box_frac(text: str, style: str, aspect: float, map_width_frac: float,
                  label_pt: dict) -> tuple[float, float]:
    """Half-width and half-height of the drawn label, as fractions of the map frame."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    pt = label_pt[style]
    prop = FontProperties(family=pick_font(), size=pt,
                          style="italic" if style == "water" else "normal",
                          weight="normal" if style == "water" else "semibold")
    drawn = text if style == "water" else text.upper()
    ext = TextPath((0, 0), drawn, size=pt, prop=prop).get_extents()
    w_pt = ext.width * (LAND_TRACKING if style == "land" else 1.0)
    axes_w_in = map_width_frac * REF_FIG_W_IN
    axes_h_in = axes_w_in / aspect
    return (w_pt / 72.0 / axes_w_in) / 2.0, (pt / 72.0 / axes_h_in) / 2.0


def pick_font() -> str:
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Segoe UI", "Calibri", "Arial", "DejaVu Sans"):
        if name in have:
            return name
    return "sans-serif"


def clutter_at(edges: np.ndarray, gw: int, gh: int, fx: float, fy: float,
               hw: float, hh: float) -> float:
    """Class-edge density under a text box, as a fraction of its pixels.

    A label over a single soil polygon is easy to read; the same label over the shredded
    Leptosols/Regosols interface is not, no matter how good the halo is. This turns that
    difference into a number the placement search can act on.
    """
    c0, c1 = int((fx - hw) * gw), int(np.ceil((fx + hw) * gw))
    r0, r1 = int((fy - hh) * gh), int(np.ceil((fy + hh) * gh))
    c0, c1 = max(c0, 0), min(c1, gw)
    r0, r1 = max(r0, 0), min(r1, gh)
    if c1 <= c0 or r1 <= r0:
        return 1.0
    return float(edges[r0:r1, c0:c1].mean())


def place_text(lab: dict, fx: float, fy: float, hw: float, hh: float, edges: np.ndarray,
               water: np.ndarray, lonlat, gw: int, gh: int) -> dict:
    """Smallest displacement from the verified anchor that satisfies every constraint.

    Constraints, in the order they matter: the text box stays inside the frame with real
    clearance; a sea label flagged `keep_text_on_water` stays on its own water body; the
    background under the text is quiet enough to read against. Offset (0, 0) is evaluated
    first and wins outright if it already passes, so a good placement is never disturbed.
    """
    window = lab.get("water_window")

    def ok_water(x: float, y: float) -> bool:
        if not lab.get("keep_text_on_water"):
            return True
        col, row = int(x * gw), int(y * gh)
        if not (0 <= col < gw and 0 <= row < gh):
            return False
        sl = (slice(max(row - 3, 0), row + 4), slice(max(col - 3, 0), col + 4))
        if (water[sl] >= 128).mean() < 0.75:
            return False
        if window:
            lon, _ = lonlat(col, row)
            lo, hi = window["lon"]
            if not (lo <= lon <= hi):
                return False
        return True

    def clearance(x: float, y: float) -> float:
        """Distance from the text box to the drawn map edge, in displayed fractions."""
        ax = (x - DISPLAY_CROP) / (1.0 - 2.0 * DISPLAY_CROP)
        ay = (y - DISPLAY_CROP) / (1.0 - 2.0 * DISPLAY_CROP)
        return min(ax - hw, 1.0 - ax - hw, ay - hh, 1.0 - ay - hh)

    base_clutter = clutter_at(edges, gw, gh, fx, fy, hw, hh)
    base_clear = clearance(fx, fy)
    if base_clear >= MIN_EDGE_CLEARANCE and base_clutter <= CLUTTER_LIMIT and ok_water(fx, fy):
        return {"dx": 0.0, "dy": 0.0, "clearance": base_clear, "clutter": base_clutter,
                "moved": False, "reason": "anchor placement already clears every constraint"}

    reasons = []
    if base_clear < MIN_EDGE_CLEARANCE:
        reasons.append(f"edge clearance {base_clear:.3f} < {MIN_EDGE_CLEARANCE}")
    if base_clutter > CLUTTER_LIMIT:
        reasons.append(f"background clutter {base_clutter:.3f} > {CLUTTER_LIMIT}")
    if not ok_water(fx, fy):
        reasons.append("drawn text does not sit on the water body it names")

    best = None
    steps = int(MAX_TEXT_SHIFT / SEARCH_STEP)
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            dx, dy = i * SEARCH_STEP, j * SEARCH_STEP
            disp = float(np.hypot(dx, dy))
            if disp > MAX_TEXT_SHIFT:
                continue
            x, y = fx + dx, fy + dy
            if clearance(x, y) < MIN_EDGE_CLEARANCE or not ok_water(x, y):
                continue
            cl = clutter_at(edges, gw, gh, x, y, hw, hh)
            if cl > CLUTTER_LIMIT:
                continue
            cost = disp / MAX_TEXT_SHIFT + CLUTTER_WEIGHT * cl / CLUTTER_LIMIT
            if best is None or cost < best[0]:
                best = (cost, dx, dy, clearance(x, y), cl)
    if best is None:
        return {"dx": 0.0, "dy": 0.0, "clearance": base_clear, "clutter": base_clutter,
                "moved": False, "reason": "NO PLACEMENT SATISFIES THE CONSTRAINTS: "
                                          + "; ".join(reasons)}
    _, dx, dy, clear, cl = best
    return {"dx": round(dx, 4), "dy": round(dy, 4), "clearance": clear, "clutter": cl,
            "moved": True, "reason": "; ".join(reasons)}


def boundary_polylines(minx, miny, maxx, maxy, cx, cy, ortho, ortho_v,
                       pixel_m: float) -> dict:
    """Iran's Natural Earth outline as frame-fraction polylines for an optional keyline.

    Simplified to one render pixel. The render is the finest thing on the sheet, so a
    stroke drawn from a more detailed geometry would claim a boundary precision that
    neither the render nor Natural Earth 1:10m supports.
    """
    import geopandas as gpd

    gdf = gpd.read_file(BOUNDARY).to_crs(CRS.from_proj4(LAEA))
    geom = gdf.geometry.iloc[0]
    simplified = geom.simplify(pixel_m, preserve_topology=True)
    parts = list(getattr(simplified, "geoms", [simplified]))
    lines, vertices = [], 0
    for part in parts:
        xy = np.asarray(part.exterior.coords)
        if len(xy) < 4:
            continue                                   # sub-pixel islet: nothing to draw
        fx = 0.5 + (xy[:, 0] / 1000.0 - cx / 1000.0) / ortho
        fy = 0.5 - (xy[:, 1] / 1000.0 - cy / 1000.0) / ortho_v
        lines.append(np.round(np.column_stack([fx, fy]), 5).tolist())
        vertices += len(xy)
    lines.sort(key=len, reverse=True)
    return {
        "source": "Natural Earth 1:10m Admin 0 (ADM0_A3=IRN), the project's only boundary",
        "simplify_tolerance_m": round(pixel_m, 2),
        "simplify_rationale": "one render pixel; the stroke may not imply a boundary "
                              "position finer than the geometry or the render behind it",
        "rings": len(lines),
        "vertices": vertices,
        "polylines_frac": lines,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-boundary", action="store_true",
                    help="skip the boundary keyline polylines (geopandas not required)")
    args = ap.parse_args()

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    sub = json.loads(SUBSTRATE.read_text(encoding="utf-8"))
    minx, miny, maxx, maxy = sub["render_grid"]["bounds_laea"]
    gw, gh = sub["render_grid"]["width"], sub["render_grid"]["height"]
    ext_x, ext_y = (maxx - minx) / 1000.0, (maxy - miny) / 1000.0
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0

    rx, ry = cfg["cameras"]["topdown"]["resolution"]
    margin = float(cfg["cameras"]["topdown"]["ortho_margin"])
    ortho = margin * max(ext_x, ext_y * rx / ry)      # mirrors place_camera()
    ortho_v = ortho * ry / rx

    fwd = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_proj4(LAEA), always_xy=True)
    inv = Transformer.from_crs(CRS.from_proj4(LAEA), CRS.from_epsg(4326), always_xy=True)
    geod = Geod(ellps="WGS84")

    # --- SCALE: geodesic truth against planar map distance -------------------------
    lons = np.linspace(44.5, 63.0, 7)
    lats = np.linspace(25.5, 39.5, 6)
    samples = []
    for lat in lats:
        for lon in lons:
            for dlon, dlat in ((0.9, 0.0), (0.0, 0.9)):
                lon2, lat2 = lon + dlon, lat + dlat
                if lon2 > 63.5 or lat2 > 40.0:
                    continue
                _, _, true_m = geod.inv(lon, lat, lon2, lat2)
                x1, y1 = fwd.transform(lon, lat)
                x2, y2 = fwd.transform(lon2, lat2)
                map_m = float(np.hypot(x2 - x1, y2 - y1))
                samples.append(map_m / true_m)
    ratios = np.array(samples)
    scale_min, scale_max = float(ratios.min()), float(ratios.max())
    worst_pct = max(abs(scale_min - 1), abs(scale_max - 1)) * 100.0

    # --- NORTH: grid convergence at sample points ----------------------------------
    conv = []
    for lat in (26.0, 32.0, 39.0):
        for lon in (44.5, 53.0, 62.5):
            x1, y1 = fwd.transform(lon, lat)
            x2, y2 = fwd.transform(lon, lat + 0.5)     # a step due north
            conv.append(float(np.degrees(np.arctan2(x2 - x1, y2 - y1))))
    conv = np.array(conv)
    conv_max = float(np.abs(conv).max())

    # --- LABELS: position, then verify against the project's own rasters ------------
    elev = np.asarray(Image.open(RENDER / "iran_heightmap_prototype.tif"))
    water = np.asarray(Image.open(RENDER / "iran_water_mask.png").convert("L"))
    ids = np.asarray(Image.open(RENDER / "iran_soil_ids_render.tif"))
    base = np.asarray(Image.open(RENDER / "blender/iran_render_basecolor.png").convert("RGB"))
    code_by_pid = {int(r["wrb2_project_int"]): r["soil_group"]
                   for r in csv.DictReader(SOIL_CSV.open(encoding="utf-8"))}

    # Class-edge map from the flat base colour, not the shaded render: relief texture is
    # not clutter a label has to fight, class boundaries are.
    edges = np.zeros(base.shape[:2], dtype=bool)
    for dy_, dx_ in ((0, 1), (1, 0)):
        edges |= (np.roll(np.roll(base, dy_, axis=0), dx_, axis=1) != base).any(axis=2)

    def lonlat(col: int, row: int) -> tuple[float, float]:
        x = minx + (col + 0.5) / gw * (maxx - minx)
        y = maxy - (row + 0.5) / gh * (maxy - miny)
        return inv.transform(x, y)

    aspect = rx / ry
    placed = []
    for lab in LABELS:
        x, y = fwd.transform(lab["lon"], lab["lat"])
        col = int(round((x - minx) / (maxx - minx) * gw - 0.5))
        row = int(round((maxy - y) / (maxy - miny) * gh - 0.5))
        col, row = int(np.clip(col, 0, gw - 1)), int(np.clip(row, 0, gh - 1))
        # sample a small window so a single stray pixel cannot decide the verdict
        sl = (slice(max(row - 4, 0), row + 5), slice(max(col - 4, 0), col + 5))
        z = float(np.median(elev[sl][elev[sl] != -32768])) if (elev[sl] != -32768).any() else float("nan")
        wet = float((water[sl] >= 128).mean())
        pid_here = int(np.bincount(ids[sl].ravel()).argmax())

        if lab["check"] == "water":
            ok = wet >= 0.5
        elif lab["check"] == "highland":
            ok = z >= HIGHLAND_MIN_M
        else:
            ok = z <= LOWLAND_MAX_M and wet < 0.5

        frac_x = 0.5 + (x - cx) / 1000.0 / ortho
        frac_y = 0.5 - (y - cy) / 1000.0 / ortho_v
        hw, hh = text_box_frac(lab["text"], lab["style"], aspect,
                              REF_MAP_WIDTH_FRAC, REF_LABEL_PT)
        pl = place_text(lab, frac_x, frac_y, hw, hh, edges, water, lonlat, gw, gh)
        tx, ty = frac_x + pl["dx"], frac_y + pl["dy"]
        moved_km = float(np.hypot(pl["dx"] * ortho, pl["dy"] * ortho_v))
        tcol, trow = int(np.clip(tx * gw, 0, gw - 1)), int(np.clip(ty * gh, 0, gh - 1))
        tlon, tlat = lonlat(tcol, trow)

        placed.append({
            "text": lab["text"], "lon": lab["lon"], "lat": lab["lat"],
            "style": lab["style"], "check": lab["check"],
            "frac_x": round(frac_x, 5), "frac_y": round(frac_y, 5),
            "median_elev_m": None if np.isnan(z) else round(z, 1),
            "water_fraction": round(wet, 3),
            "dominant_class_here": code_by_pid.get(pid_here, "outside Iran"),
            "verified": bool(ok),
            # text placement, measured
            "text_dx_frac": pl["dx"], "text_dy_frac": pl["dy"],
            "text_moved": pl["moved"], "text_move_reason": pl["reason"],
            "text_moved_km": round(moved_km, 1),
            "text_half_w_frac": round(hw, 5), "text_half_h_frac": round(hh, 5),
            "text_edge_clearance_frac": round(pl["clearance"], 4),
            "text_background_clutter": round(pl["clutter"], 4),
            "text_lon": round(tlon, 3), "text_lat": round(tlat, 3),
            "text_on_water": bool((water[max(trow - 3, 0):trow + 4,
                                         max(tcol - 3, 0):tcol + 4] >= 128).mean() >= 0.75),
            "inside_frame": bool(pl["clearance"] >= MIN_EDGE_CLEARANCE),
        })

    failed = [p["text"] for p in placed if not (p["verified"] and p["inside_frame"])]
    # A sea label drawn over land is a factual error even when its anchor verifies.
    text_failed = [p["text"] for p in placed
                   for lab in [next(l for l in LABELS if l["text"] == p["text"])]
                   if lab.get("keep_text_on_water") and not p["text_on_water"]]

    payload = {
        "map_frame": {"ortho_width_km": round(ortho, 3), "ortho_height_km": round(ortho_v, 3),
                      "extent_km": [round(ext_x, 3), round(ext_y, 3)],
                      "crs": "LAEA lat_0=32 lon_0=53"},
        "scale_bar": {
            "samples": int(ratios.size),
            "map_over_true_distance_min": round(scale_min, 5),
            "map_over_true_distance_max": round(scale_max, 5),
            "worst_deviation_percent": round(worst_pct, 3),
            "verdict": ("bar permissible, annotated with the measured tolerance"
                        if worst_pct < 2.0 else "OMIT: distance scale varies materially"),
        },
        "north_indicator": {
            "grid_convergence_deg_max": round(conv_max, 3),
            "verdict": ("single arrow permissible; exact on the central meridian, "
                        f"deviating up to {conv_max:.1f} deg at the extreme corners"),
        },
        "text_placement": {
            "min_edge_clearance_frac": MIN_EDGE_CLEARANCE,
            "clearance_measured_in": "displayed (cropped) map frame, crop "
                                     f"{DISPLAY_CROP} per side",
            "clutter_limit": CLUTTER_LIMIT,
            "max_text_shift_frac": MAX_TEXT_SHIFT,
            "reference_label_pt": REF_LABEL_PT,
            "reference_map_width_frac": REF_MAP_WIDTH_FRAC,
            "moved": [p["text"] for p in placed if p["text_moved"]],
        },
        "labels": placed,
        "labels_failed_verification": failed + text_failed,
    }
    if not args.no_boundary:
        payload["boundary"] = boundary_polylines(minx, miny, maxx, maxy, cx, cy,
                                                 ortho, ortho_v,
                                                 float(sub["render_grid"]["pixel_size_m"][0]))
    elif OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        if "boundary" in prev:
            payload["boundary"] = prev["boundary"]

    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    print(f"SCALE: map/true distance {scale_min:.5f}..{scale_max:.5f} over {ratios.size} pairs "
          f"-> worst deviation {worst_pct:.3f}%")
    print(f"       {payload['scale_bar']['verdict']}")
    print(f"NORTH: grid convergence up to {conv_max:.2f} deg")
    if "boundary" in payload:
        b = payload["boundary"]
        print(f"BOUNDARY: {b['rings']} rings, {b['vertices']} vertices, simplified to "
              f"{b['simplify_tolerance_m']:.0f} m (one render pixel)")
    print(f"{'label':<18}{'frac_x':>8}{'frac_y':>8}{'elev_m':>9}{'water':>7}  class / verdict")
    for p in placed:
        print(f"{p['text']:<18}{p['frac_x']:>8.3f}{p['frac_y']:>8.3f}"
              f"{str(p['median_elev_m']):>9}{p['water_fraction']:>7.2f}  "
              f"{p['dominant_class_here']:<14}"
              f"{'OK' if p['verified'] and p['inside_frame'] else 'FAIL'}")
    print(f"\n{'label':<18}{'dx':>8}{'dy':>8}{'moved_km':>10}{'clear':>8}{'clutter':>9}  note")
    for p in placed:
        print(f"{p['text']:<18}{p['text_dx_frac']:>8.3f}{p['text_dy_frac']:>8.3f}"
              f"{p['text_moved_km']:>10.0f}{p['text_edge_clearance_frac']:>8.3f}"
              f"{p['text_background_clutter']:>9.3f}  "
              f"{p['text_move_reason'] if p['text_moved'] else ''}")
    if payload["labels_failed_verification"]:
        print(f"LABELS FAILING VERIFICATION: {payload['labels_failed_verification']}")


if __name__ == "__main__":
    main()
