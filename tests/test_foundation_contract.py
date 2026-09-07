from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_has_required_columns():
    manifest = ROOT / "provenance/manifests/source_manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "dataset_id", "dataset_name", "provider", "official_url", "version",
            "access_date", "native_crs", "native_resolution", "data_type",
            "license", "required_attribution", "local_raw_path", "sha256", "status",
        }
        assert required <= set(reader.fieldnames or [])
        rows = list(reader)
    assert {row["dataset_id"] for row in rows} >= {
        "fao_iiasa_hwsd_v201_raster", "fao_iiasa_hwsd_v201_database",
        "natural_earth_admin0_10m", "usgs_nasa_srtmgl1",
    }


def test_soil_schema_contract_is_explicitly_pending_not_fabricated():
    text = (ROOT / "config/hwsd_schema.yaml").read_text(encoding="utf-8")
    assert "status: PENDING_SCHEMA_REVIEW" in text
    assert "wrb_2022_reference_soil_group_field: null" in text


def test_no_generated_spatial_outputs_are_tracked():
    assert not (ROOT / "data/processed/soils/iran_dominant_soil_group.tif").exists()
    assert not (ROOT / "outputs/proof/iran_soils_proof_v01.png").exists()


def _manifest_rows():
    manifest = ROOT / "provenance/manifests/source_manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_manifest_is_well_formed_no_ragged_rows():
    # Every row must parse to exactly the header's fields (guards CSV quoting).
    manifest = ROOT / "provenance/manifests/source_manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader)
        for i, row in enumerate(reader, start=2):
            assert len(row) == len(header), f"row {i} has {len(row)} fields, expected {len(header)}"


def test_no_fabricated_checksums_while_download_pending():
    # A source that is not yet downloaded must NOT carry a sha256 value.
    for row in _manifest_rows():
        if "DOWNLOAD_PENDING" in row["status"] or "BLOCKED" in row["status"]:
            assert not (row["sha256"] or "").strip(), (
                f"{row['dataset_id']} has a checksum but is not downloaded: fabrication guard"
            )


def test_hwsd_license_matches_verified_primary_source():
    # Guards the 2026-09-07 D-007 correction against regression to 3.0/IGO.
    for row in _manifest_rows():
        if row["dataset_id"].startswith("fao_iiasa_hwsd"):
            assert row["license"] == "CC-BY-NC-SA-4.0", row["license"]
            assert "IGO" not in row["license"] and "3.0" not in row["license"]
