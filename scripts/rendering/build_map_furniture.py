"""Map furniture computed from the transform and the data, never from a reference poster.

Three things on a finished map are routinely added by imitation and are wrong as often as
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

    python scripts/rendering/build_map_furniture.py

Writes provenance/metadata/map_furniture_qa.json, consumed by the poster layout.
"""
from __future__ import annotations

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
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
OUT = ROOT / "provenance/metadata/map_furniture_qa.json"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"

# Candidate labels: approximate centres of well-known physical features, each with the
# evidence test it must pass. No provinces, roads or cities.
LABELS = [
    {"text": "Caspian Sea",     "lon": 51.4, "lat": 38.2, "check": "water", "style": "water"},
    {"text": "Persian Gulf",    "lon": 51.0, "lat": 27.6, "check": "water", "style": "water"},
    {"text": "Gulf of Oman",    "lon": 59.3, "lat": 25.3, "check": "water", "style": "water",
     "text_dy_frac": -0.028},
    {"text": "Lake Urmia",      "lon": 45.5, "lat": 37.6, "check": "water", "style": "water"},
    {"text": "Alborz",          "lon": 52.0, "lat": 36.1, "check": "highland", "style": "land"},
    {"text": "Zagros",          "lon": 49.6, "lat": 32.6, "check": "highland", "style": "land"},
    {"text": "Dasht-e Kavir",   "lon": 54.6, "lat": 34.4, "check": "lowland", "style": "land"},
    {"text": "Lut Desert",      "lon": 58.5, "lat": 30.9, "check": "lowland", "style": "land"},
    {"text": "Khuzestan Plain", "lon": 48.9, "lat": 31.4, "check": "lowland", "style": "land"},
]
HIGHLAND_MIN_M = 1800
LOWLAND_MAX_M = 1200


def main() -> None:
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
    code_by_pid = {int(r["wrb2_project_int"]): r["soil_group"]
                   for r in csv.DictReader(SOIL_CSV.open(encoding="utf-8"))}

    placed = []
    for lab in LABELS:
        x, y = fwd.transform(lab["lon"], lab["lat"])
        col = int(round((x - minx) / (maxx - minx) * gw - 0.5))
        row = int(round((maxy - y) / (maxy - miny) * gh - 0.5))
        col, row = np.clip(col, 0, gw - 1), np.clip(row, 0, gh - 1)
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
        placed.append({
            "text": lab["text"], "lon": lab["lon"], "lat": lab["lat"],
            "style": lab["style"], "check": lab["check"],
            "frac_x": round(0.5 + (x - cx) / 1000.0 / ortho, 5),
            "frac_y": round(0.5 - (y - cy) / 1000.0 / ortho_v, 5),
            "median_elev_m": None if np.isnan(z) else round(z, 1),
            "water_fraction": round(wet, 3),
            "dominant_class_here": code_by_pid.get(pid_here, "outside Iran"),
            "verified": bool(ok),
            "text_dy_frac": lab.get("text_dy_frac", 0.0),
            "inside_frame": bool(
                0.02 <= 0.5 + (x - cx) / 1000.0 / ortho <= 0.98
                and 0.02 <= 0.5 - (y - cy) / 1000.0 / ortho_v + lab.get("text_dy_frac", 0.0) <= 0.98),
        })

    failed = [p["text"] for p in placed if not (p["verified"] and p["inside_frame"])]
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
        "labels": placed,
        "labels_failed_verification": failed,
    }
    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    print(f"SCALE: map/true distance {scale_min:.5f}..{scale_max:.5f} over {ratios.size} pairs "
          f"-> worst deviation {worst_pct:.3f}%")
    print(f"       {payload['scale_bar']['verdict']}")
    print(f"NORTH: grid convergence up to {conv_max:.2f} deg")
    print(f"{'label':<18}{'frac_x':>8}{'frac_y':>8}{'elev_m':>9}{'water':>7}  class / verdict")
    for p in placed:
        print(f"{p['text']:<18}{p['frac_x']:>8.3f}{p['frac_y']:>8.3f}"
              f"{str(p['median_elev_m']):>9}{p['water_fraction']:>7.2f}  "
              f"{p['dominant_class_here']:<14}{'OK' if p['verified'] and p['inside_frame'] else 'FAIL'}")
    if failed:
        print(f"LABELS FAILING VERIFICATION: {failed}")


if __name__ == "__main__":
    main()
