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
        "natural_earth_admin0_10m", "usgs_nasa_srtmgl3",
    }


def test_soil_schema_contract_is_locked_from_evidence():
    text = (ROOT / "config/hwsd_schema.yaml").read_text(encoding="utf-8")
    assert "status: SCHEMA_LOCKED" in text
    # rule locked to SEQUENCE=1 dominant with the actual WRB2 field, no guessed ISSOIL value
    assert "wrb_2022_reference_soil_group_field: WRB2" in text
    assert "component_sequence_field: SEQUENCE" in text


def test_generated_data_products_are_not_git_tracked():
    # Derived rasters/proof may exist locally but must be gitignored (not committed).
    import subprocess
    for rel in ("data/processed/soils/iran_dominant_soil_group.tif",
                "outputs/proof/iran_soils_proof_v01.png"):
        out = subprocess.run(["git", "check-ignore", rel], cwd=ROOT,
                             capture_output=True, text=True)
        assert out.stdout.strip() == rel, f"{rel} is not gitignored"


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


def test_hwsd_dataset_license_is_4_0_report_is_3_0_igo():
    # D-007: the DATASET (raster/DB) is CC BY-NC-SA 4.0; the REPORT pdf is 3.0 IGO.
    by_id = {r["dataset_id"]: r for r in _manifest_rows()}
    for did in ("fao_iiasa_hwsd_v201_raster", "fao_iiasa_hwsd_v201_database"):
        assert by_id[did]["license"] == "CC-BY-NC-SA-4.0", by_id[did]["license"]
    assert by_id["fao_iiasa_hwsd_v201_report"]["license"] == "CC-BY-NC-SA-3.0-IGO"


def test_downloaded_rows_have_checksums():
    for row in _manifest_rows():
        if row["status"] == "SOURCE_DOWNLOADED_VERIFIED":
            assert len((row["sha256"] or "").strip()) == 64, row["dataset_id"]


# --- Scientific-invariant tests over the derived products (skip cleanly if not yet run) ---
import json  # noqa: E402
import pytest  # noqa: E402

SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
AREA_QA = ROOT / "provenance/metadata/area_qa.json"
PALETTE = ROOT / "config/soil_palette.yaml"


def _soil_rows():
    if not SOIL_CSV.exists():
        pytest.skip("soil_groups_iran.csv not generated yet (run derive_hwsd_iran.py)")
    with SOIL_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_class_shares_sum_to_100():
    rows = _soil_rows()
    total = sum(float(r["share_percent"]) for r in rows)
    assert abs(total - 100.0) < 0.5, f"shares sum to {total}, expected ~100"


def test_every_class_has_a_palette_colour():
    rows = _soil_rows()
    pal_text = PALETTE.read_text(encoding="utf-8")
    for r in rows:
        assert f"\n  {r['classification_code']}:" in pal_text, r["classification_code"]


def test_area_reconciliation_holds():
    if not AREA_QA.exists():
        pytest.skip("area_qa.json not generated yet")
    qa = json.loads(AREA_QA.read_text(encoding="utf-8"))
    # B must equal C + E + F (no leakage), and A-B must be small and explainable.
    assert abs(qa["reconciliation_B_minus_C_E_F"]) < 1.0
    assert abs(qa["A_minus_B_pct"]) < 2.0, qa["A_minus_B_pct"]
    assert qa["F_unmapped_smu_area_km2"] == 0.0


# --- Terrain-precheck / credential-safety invariants ---
import subprocess  # noqa: E402

SRTM_TILES = ROOT / "provenance/manifests/srtm_tiles_iran.csv"


def test_no_credential_files_are_git_tracked():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    bad = [f for f in tracked if any(tok in f.lower()
           for tok in ("netrc", ".urs_cookies", ".edl_token", "credential", ".env"))
           and not f.endswith(".gitignore")]
    assert not bad, f"credential-bearing files are tracked: {bad}"


def test_gitignore_protects_credentials():
    for rel in ("_netrc", ".netrc", ".urs_cookies", ".env"):
        out = subprocess.run(["git", "check-ignore", rel], cwd=ROOT, capture_output=True, text=True)
        assert out.stdout.strip() == rel, f"{rel} is not gitignored"


def test_srtm_tile_manifest_coverage_and_official_endpoint():
    if not SRTM_TILES.exists():
        pytest.skip("srtm tile manifest not generated")
    rows = list(csv.DictReader(SRTM_TILES.open(encoding="utf-8")))
    assert len(rows) == 198, f"expected 198 Iran tiles, got {len(rows)}"
    for r in rows:
        assert r["product"] == "SRTMGL3" and r["version"] == "003"
        assert r["official_download_url"].startswith(
            "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL3.003/")
        # legacy deprecated host must not reappear
        assert "e4ftl01.cr.usgs.gov" not in r["official_download_url"]
