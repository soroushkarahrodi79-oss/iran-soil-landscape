"""Extract and validate Iran from Natural Earth without geometry alteration."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
from pyproj import CRS, Geod

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/natural_earth/ne_10m_admin_0_countries.zip"
OUTPUT = ROOT / "data/processed/boundary/iran_boundary.gpkg"
METADATA = ROOT / "provenance/metadata/iran_boundary_processing.json"
TARGET = CRS.from_proj4("+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs")


def geodesic_area_km2(frame: gpd.GeoDataFrame) -> float:
    geod = Geod(ellps="WGS84")
    return abs(sum(geod.geometry_area_perimeter(shape)[0] for shape in frame.geometry)) / 1_000_000


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Official Natural Earth archive missing: {RAW}")
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite derived boundary: {OUTPUT}")
    source = gpd.read_file(f"zip://{RAW}")
    if source.crs is None:
        raise SystemExit("Source CRS is absent; stop rather than assume WGS84.")
    if "ADM0_A3" not in source.columns:
        raise SystemExit("Expected Natural Earth field ADM0_A3 is absent.")
    iran = source.loc[source["ADM0_A3"] == "IRN"].copy()
    if len(iran) != 1 or iran.geometry.is_empty.any():
        raise SystemExit(f"Expected one non-empty IRN feature; found {len(iran)}.")
    if not iran.geometry.is_valid.all():
        raise SystemExit("Source Iran geometry is invalid; no automatic repair is permitted.")
    projected = iran.to_crs(TARGET)
    projected.to_file(OUTPUT, layer="iran_boundary", driver="GPKG")
    geodesic = geodesic_area_km2(iran.to_crs("EPSG:4326"))
    equal_area = float(projected.geometry.area.sum() / 1_000_000)
    METADATA.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "selection": "ADM0_A3 == 'IRN'",
        "selected_features": len(iran),
        "source_crs": str(source.crs),
        "target_projjson": TARGET.to_json_dict(),
        "target_wkt": TARGET.to_wkt(),
        "source_bounds": list(iran.total_bounds),
        "geometry_valid": True,
        "geodesic_area_km2": geodesic,
        "equal_area_crs_area_km2": equal_area,
        "relative_area_difference_percent": abs(equal_area - geodesic) / geodesic * 100,
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "status": "BOUNDARY_PROCESSED",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote validated boundary to {OUTPUT}")


if __name__ == "__main__":
    main()
