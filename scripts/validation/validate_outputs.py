"""Validate that outputs exist only when all source-derived metadata is present."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def required(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Required QA artifact missing: {path.relative_to(ROOT)}")


def main() -> None:
    required(ROOT / "data/processed/boundary/iran_boundary.gpkg")
    required(ROOT / "provenance/metadata/iran_boundary_processing.json")
    required(ROOT / "data/processed/soils/iran_hwsd_mapping_units.tif")
    required(ROOT / "data/processed/soils/iran_dominant_soil_group.tif")
    required(ROOT / "data/processed/tables/soil_groups_iran.csv")
    area = ROOT / "provenance/metadata/area_qa.json"
    required(area)
    payload = json.loads(area.read_text(encoding="utf-8"))
    required_keys = {"boundary_area_km2", "raster_covered_area_km2", "classified_area_km2", "nodata_area_km2", "residual_area_km2"}
    if required_keys - payload.keys():
        raise SystemExit("Area QA lacks one or more required accounting values.")
    print("Required foundation QA outputs are present; inspect scientific values before declaring a pass.")


if __name__ == "__main__":
    main()
