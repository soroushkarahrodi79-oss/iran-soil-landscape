"""Guard the 2D proof stage against rendering before data-derived classes exist."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    required = [
        ROOT / "data/processed/boundary/iran_boundary.gpkg",
        ROOT / "data/processed/soils/iran_dominant_soil_group.tif",
        ROOT / "data/processed/tables/soil_groups_iran.csv",
        ROOT / "provenance/metadata/area_qa.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Proof rendering is blocked; missing: " + ", ".join(missing))
    raise SystemExit(
        "Proof inputs exist, but the deterministic palette must first be populated from actual discovered classes in config/project.yaml. "
        "No placeholder palette may be used for scientific proof."
    )


if __name__ == "__main__":
    main()
