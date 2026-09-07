"""Fail-closed HWSD dominant-component derivation entry point.

This deliberately refuses to guess MDB fields or create an output before the
project's generated schema evidence has been reviewed and recorded.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config/hwsd_schema.yaml"
REQUIRED = (
    "database_table", "raster_mapping_unit_field", "database_mapping_unit_field",
    "soil_indicator_field", "soil_indicator_value", "component_share_field",
    "component_sequence_field", "wrb_2022_reference_soil_group_field",
    "fao_1990_soil_unit_field", "acceptance_note", "accepted_by", "accepted_date",
)


def main() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["schema_contract"]
    missing = [field for field in REQUIRED if contract.get(field) in (None, "")]
    if contract.get("status") != "ACCEPTED_FROM_EVIDENCE" or missing:
        raise SystemExit(
            "HWSD schema decision is not accepted from evidence. Missing: "
            + ", ".join(missing)
            + ". Run inspect_hwsd_schema.py, reconcile it to the official report, and record the decision."
        )
    raise SystemExit(
        "Schema contract is recorded, but no data transformation is implemented until the exact "
        "raster/database structure is exercised on the official downloaded files. This is an intentional stop condition."
    )


if __name__ == "__main__":
    main()
