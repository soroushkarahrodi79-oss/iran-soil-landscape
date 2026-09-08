"""Compute the minimal SRTM 1x1-degree tile set intersecting the Iran boundary.

Does NOT download anything. Emits a machine-readable acquisition manifest and a
storage estimate for both SRTMGL1 (~30 m) and SRTMGL3 (~90 m). Tiles are named by
their SW corner, e.g. N25E044 (all of Iran is N latitude / E longitude).

Outputs:
  provenance/manifests/srtm_tiles_iran.csv
  provenance/metadata/srtm_storage_estimate.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import geopandas as gpd  # noqa: E402
from shapely.geometry import box  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
CSV = ROOT / "provenance/manifests/srtm_tiles_iran.csv"
JSON = ROOT / "provenance/metadata/srtm_storage_estimate.json"

# Extracted .hgt byte sizes (int16): GL1 = 3601^2*2, GL3 = 1201^2*2.
GL1_HGT_BYTES = 3601 * 3601 * 2
GL3_HGT_BYTES = 1201 * 1201 * 2


def tile_name(lat: int, lon: int) -> str:
    ns = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    ew = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
    return ns + ew


def main() -> None:
    iran = gpd.read_file(BOUNDARY).to_crs("EPSG:4326")
    geom = iran.union_all() if hasattr(iran, "union_all") else iran.unary_union
    minx, miny, maxx, maxy = geom.bounds
    lon0, lon1 = math.floor(minx), math.ceil(maxx) - 1
    lat0, lat1 = math.floor(miny), math.ceil(maxy) - 1

    tiles = []
    for lat in range(lat0, lat1 + 1):
        for lon in range(lon0, lon1 + 1):
            cell = box(lon, lat, lon + 1, lat + 1)
            if cell.intersects(geom):
                tiles.append((tile_name(lat, lon), lat, lon))
    tiles.sort()

    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tile_id", "sw_lat", "sw_lon",
                    "gl3_file", "gl1_file",
                    "gl3_dir_url", "status"])
        for name, lat, lon in tiles:
            w.writerow([
                name, lat, lon,
                f"{name}.SRTMGL3.hgt.zip", f"{name}.SRTMGL1.hgt.zip",
                "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL3.003/2000.02.11/",
                "PLANNED_BLOCKED_USER_AUTH",
            ])

    n = len(tiles)
    est = {
        "boundary_bounds_4326": [minx, miny, maxx, maxy],
        "tile_grid_lon_range": [lon0, lon1],
        "tile_grid_lat_range": [lat0, lat1],
        "candidate_full_rectangle_tiles": (lon1 - lon0 + 1) * (lat1 - lat0 + 1),
        "tiles_intersecting_iran": n,
        "srtmgl3_90m": {
            "extracted_bytes_per_tile": GL3_HGT_BYTES,
            "extracted_total_mb": round(n * GL3_HGT_BYTES / 1e6, 1),
            "approx_zip_download_mb": round(n * GL3_HGT_BYTES * 0.55 / 1e6, 1),
        },
        "srtmgl1_30m": {
            "extracted_bytes_per_tile": GL1_HGT_BYTES,
            "extracted_total_mb": round(n * GL1_HGT_BYTES / 1e6, 1),
            "approx_zip_download_mb": round(n * GL1_HGT_BYTES * 0.55 / 1e6, 1),
        },
        "note": "Extracted .hgt sizes are exact (int16); zip sizes are ~0.55x heuristics. "
                "Mosaic/reproject/clip add transient copies of similar magnitude to the extracted total.",
    }
    JSON.write_text(json.dumps(est, indent=2) + "\n", encoding="utf-8")
    print(f"Iran intersects {n} SRTM 1x1-deg tiles "
          f"(vs {est['candidate_full_rectangle_tiles']} for the full rectangle).")
    print(f"GL3 (~90m) extracted ~{est['srtmgl3_90m']['extracted_total_mb']} MB; "
          f"GL1 (~30m) extracted ~{est['srtmgl1_30m']['extracted_total_mb']} MB.")
    print(f"Wrote {CSV} and {JSON}")


if __name__ == "__main__":
    main()
