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
