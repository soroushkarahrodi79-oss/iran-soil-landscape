"""Inspect Natural Earth, extract Iran, and run CRS/area QA — no geometry edits.

- Confirms the selection field from the actual schema (does not assume ADM0_A3).
- Keeps the canonical processed boundary in the SOURCE CRS (EPSG:4326).
- Reports geodesic vs LAEA-equal-area area; does NOT lock the LAEA CRS here.
Outputs:
  data/processed/boundary/iran_boundary.gpkg   (EPSG:4326, unaltered geometry)
  provenance/metadata/iran_boundary_processing.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401  (sets PROJ_DATA/PROJ_LIB/GDAL_DATA before geopandas/pyproj)

import geopandas as gpd
from pyproj import CRS, Geod

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/natural_earth/ne_10m_admin_0_countries.zip"
OUTPUT = ROOT / "data/processed/boundary/iran_boundary.gpkg"
METADATA = ROOT / "provenance/metadata/iran_boundary_processing.json"
# Candidate national analysis CRS (PROVISIONAL — evaluated, not yet locked).
LAEA = CRS.from_proj4("+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs")
# Plausibility envelope for Iran (deg): lon ~44-64E, lat ~25-40N.
PLAUSIBLE = {"minx": 43.0, "maxx": 64.0, "miny": 24.0, "maxy": 40.5}


def geodesic_area_km2(frame_4326: gpd.GeoDataFrame) -> float:
    geod = Geod(ellps="WGS84")
    return abs(sum(geod.geometry_area_perimeter(g)[0] for g in frame_4326.geometry)) / 1e6


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Missing Natural Earth archive: {RAW}")
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite derived boundary: {OUTPUT} (delete to regenerate)")

    src = gpd.read_file(f"zip://{RAW}")
    if src.crs is None:
        raise SystemExit("Source CRS absent; stop rather than assume WGS84.")

    # Confirm a stable Iran selector from the ACTUAL schema (do not assume ADM0_A3).
    candidates = [
        ("ADM0_A3", "IRN"), ("SOV_A3", "IRN"), ("ISO_A3", "IRN"),
        ("ADMIN", "Iran"), ("NAME", "Iran"), ("NAME_EN", "Iran"),
        ("SOVEREIGNT", "Iran"),
    ]
    usable = [(f, v) for f, v in candidates if f in src.columns]
    if not usable:
        raise SystemExit(f"No known Iran selector field present. Columns: {list(src.columns)}")
    selections = {}
    for field, value in usable:
        sel = src[src[field].astype(str).str.strip().str.upper() == value.upper()]
        selections[f"{field}=={value}"] = int(len(sel))
    field, value = usable[0]
    iran = src[src[field].astype(str).str.strip().str.upper() == value.upper()].copy()

    if len(iran) != 1:
        raise SystemExit(f"Expected exactly one feature for {field}=={value}; got {len(iran)}. selections={selections}")
    if iran.geometry.is_empty.any():
        raise SystemExit("Selected Iran geometry is empty.")
    if not iran.geometry.is_valid.all():
        raise SystemExit("Selected Iran geometry is invalid; no automatic repair permitted (report instead).")

    minx, miny, maxx, maxy = map(float, iran.total_bounds)
    bbox_ok = (minx >= PLAUSIBLE["minx"] and maxx <= PLAUSIBLE["maxx"]
               and miny >= PLAUSIBLE["miny"] and maxy <= PLAUSIBLE["maxy"])

    geod_area = geodesic_area_km2(iran.to_crs("EPSG:4326"))
    laea_area = float(iran.to_crs(LAEA).geometry.area.sum() / 1e6)

    # Save canonical boundary in the SOURCE CRS, geometry unaltered.
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    iran.to_file(OUTPUT, layer="iran_boundary", driver="GPKG")

    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "source_crs": str(src.crs),
        "selection_field": field,
        "selection_value": value,
        "selection_counts_by_candidate": selections,
        "selected_features": int(len(iran)),
        "multipolygon_parts": int(sum(len(getattr(g, "geoms", [g])) for g in iran.geometry)),
        "bounds_4326": {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        "bbox_plausible": bool(bbox_ok),
        "geometry_valid": True,
        "geodesic_area_km2_wgs84": geod_area,
        "laea_area_km2": laea_area,
        "laea_vs_geodesic_rel_diff_pct": abs(laea_area - geod_area) / geod_area * 100,
        "laea_proj4": LAEA.to_proj4(),
        "laea_wkt": LAEA.to_wkt(),
        "laea_status": "PROVISIONAL_PENDING_BOUNDARY_QA (evaluated here; lock decision recorded in DECISIONS)",
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "output_crs": "EPSG:4326 (source CRS preserved; geometry unaltered)",
        "status": "BOUNDARY_PROCESSED",
    }
    METADATA.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Iran extracted via {field}=={value}; geodesic={geod_area:,.0f} km2, "
          f"LAEA={laea_area:,.0f} km2 (rel diff {payload['laea_vs_geodesic_rel_diff_pct']:.3f}%)")
    print(f"Wrote {OUTPUT} and {METADATA}")


if __name__ == "__main__":
    main()
