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
        # Single-file downloads must carry a 64-char sha256. Multi-file products
        # (local_raw_path is a directory) keep per-file checksums in provenance/checksums/.
        if row["status"] == "SOURCE_DOWNLOADED_VERIFIED" and not row["local_raw_path"].endswith("/"):
            assert len((row["sha256"] or "").strip()) == 64, row["dataset_id"]


# --- Scientific-invariant tests over the derived products (skip cleanly if not yet run) ---
import json  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
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


def test_soil_truth_unchanged_since_freeze():
    import hashlib
    frozen = ROOT / "provenance/checksums/soil_truth_frozen_2026-09-08.txt"
    if not frozen.exists():
        pytest.skip("freeze file absent")
    for line in frozen.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, rel = line.split()[0], line.split()[-1].lstrip("*")
        p = ROOT / rel
        if not p.exists():
            pytest.skip(f"{rel} not present locally")
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        assert got == want, f"SOIL TRUTH CHANGED: {rel}"


DEM = ROOT / "data/processed/dem/iran_dem_90m.tif"
DEM_QA = ROOT / "provenance/metadata/dem_qa.json"
RENDER_META = ROOT / "provenance/metadata/render_substrate.json"


def test_dem_unchanged_since_freeze():
    import hashlib
    frozen = ROOT / "provenance/checksums/dem_frozen_2026-09-09.txt"
    if not frozen.exists() or not DEM.exists():
        pytest.skip("dem freeze or DEM not present")
    want = frozen.read_text(encoding="utf-8").split()[0]
    got = hashlib.sha256(DEM.read_bytes()).hexdigest()
    assert got == want, "SOURCE DEM CHANGED since freeze"


def test_render_substrate_grid_and_classes_match_source():
    if not RENDER_META.exists():
        pytest.skip("render substrate not built")
    m = json.loads(RENDER_META.read_text(encoding="utf-8"))
    assert max(m["render_grid"]["width"], m["render_grid"]["height"]) == 4096
    assert "LAEA" in m["render_grid"]["crs"]
    # soil texture must use exactly the classes actually present (no invented class)
    n_csv = len(list(csv.DictReader(SOIL_CSV.open(encoding="utf-8")))) if SOIL_CSV.exists() else None
    if n_csv is not None:
        assert m["soil_classes_present"] == n_csv


def test_dem_elevation_and_crs_plausible():
    if not DEM_QA.exists():
        pytest.skip("dem_qa.json not generated yet")
    qa = json.loads(DEM_QA.read_text(encoding="utf-8"))
    assert qa["nodata"] == -32768
    assert qa["valid_pixels"] > 0
    # Iran: lowest ~ Caspian coast (-28 m; SRTM water noise can reach ~-100 m),
    # highest Damavand ~5610 m. Bounds catch nodata leakage / absurd values.
    assert -120 <= qa["elev_min_m"] <= 60, qa["elev_min_m"]
    assert 3500 <= qa["elev_max_m"] <= 6000, qa["elev_max_m"]
    assert 0 <= qa["nodata_share_pct"] < 60


# --- 3D prototype invariants (Blender scene is generated, never hand-authored) ---
import yaml  # noqa: E402

RENDER_CFG = ROOT / "config/render_3d.yaml"
BLENDER_INPUTS = ROOT / "data/processed/render/blender/blender_inputs.json"
SCENE_SCRIPT = ROOT / "scripts/rendering/blender_build_scene.py"
PROOF_3D = ROOT / "outputs/proof/3d"


def test_blender_scene_and_toolchain_are_not_git_tracked():
    # The .blend is regenerable from the script; the portable Blender build is tooling.
    for rel in ("blender/iran_soil_landscapes_prototype.blend",
                "tools/blender-4.5.13-windows-x64/blender.exe"):
        out = subprocess.run(["git", "check-ignore", rel], cwd=ROOT, capture_output=True, text=True)
        assert out.stdout.strip() == rel, f"{rel} is not gitignored"


def test_soil_texture_is_sampled_categorically_and_palette_is_not_regraded():
    # Two ways a render could silently corrupt the science: bilinear sampling would
    # invent blended soil colours between classes, and a filmic/AgX view transform
    # would re-grade the documented palette. Both must stay locked in the script.
    src = SCENE_SCRIPT.read_text(encoding="utf-8")
    assert src.count('interpolation = "Closest"') >= 2, "categorical textures must sample Closest"
    assert 'view_transform = "Standard"' in src, "palette must not be re-graded by a view transform"
    assert "ORTHO" in src, "map cameras must be orthographic (constant scale)"


def test_render_display_colours_never_collide_with_a_soil_class():
    # Context land (outside Iran) and cartographic water are display-only. If either
    # matched a soil colour, a reader could mistake 'no data' for a mapped soil.
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))
    palette = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    used = {v.upper() for v in palette.values()}
    for key in ("context_land_srgb", "cartographic_water_srgb"):
        assert cfg["surface"][key].upper() not in used, f"{key} collides with a soil class colour"


def test_prototype_mesh_is_one_vertex_per_heightmap_sample():
    if not BLENDER_INPUTS.exists():
        pytest.skip("blender inputs not prepared yet")
    m = json.loads(BLENDER_INPUTS.read_text(encoding="utf-8"))
    mesh = m["mesh"]
    assert mesh["verts"] == mesh["width"] * mesh["height"], "mesh duplicates or drops samples"
    # Elevation must stay inside the DEM's plausible envelope: the mesh is a decimation,
    # never a rescaling, so no exaggeration may be baked into the geometry.
    assert -120 <= m["elevation_m"]["min"] <= 60, m["elevation_m"]["min"]
    assert 3500 <= m["elevation_m"]["max"] <= 6000, m["elevation_m"]["max"]


def test_prototype_renders_match_configured_resolution():
    if not (PROOF_3D / "iran_3d_1x_topdown.png").exists():
        pytest.skip("prototype renders not produced yet")
    from PIL import Image
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))
    for cam in ("topdown", "oblique"):
        want = tuple(cfg["cameras"][cam]["resolution"])
        for k in cfg["exaggeration_tests"]:
            p = PROOF_3D / f"iran_3d_{k}x_{cam}.png"
            if p.exists():
                assert Image.open(p).size == want, f"{p.name} is {Image.open(p).size}, want {want}"


PROTO_QA = ROOT / "provenance/metadata/prototype_3d_qa.json"


def test_exaggeration_choice_is_the_lowest_that_passes_its_own_thresholds():
    # Guards the selection against being edited to a preferred answer after the fact:
    # it must still be the LOWEST exaggeration meeting both pre-set criteria.
    if not PROTO_QA.exists():
        pytest.skip("3D prototype QA not run yet")
    qa = json.loads(PROTO_QA.read_text(encoding="utf-8"))
    passing = [k for k, v in qa["by_exaggeration"].items()
               if v["meets_relief_threshold"] and v["within_shadow_budget"]]
    assert qa["selected_exaggeration"] == (passing[0] if passing else None)
    chosen = qa["by_exaggeration"][qa["selected_exaggeration"]]
    assert chosen["shadow_burden_below_0.5"] <= qa["thresholds"]["shadow_burden_max"]


def test_render_still_shows_the_soil_class_the_substrate_says():
    # End-to-end: mesh + UVs + texture sampling + render must not move a class.
    if not PROTO_QA.exists():
        pytest.skip("3D prototype QA not run yet")
    reg = json.loads(PROTO_QA.read_text(encoding="utf-8"))["registration_on_render"]
    if reg is None:
        pytest.skip("selected render absent")
    assert reg["class_agreement"] >= 0.99, reg


# --- Publication cartography invariants ---
IDPASS_QA = ROOT / "provenance/metadata/registration_idpass_qa.json"
PALETTE_QA = ROOT / "provenance/metadata/palette_final_qa.json"
FURNITURE_QA = ROOT / "provenance/metadata/map_furniture_qa.json"
POSTER_SCRIPT = ROOT / "scripts/rendering/build_poster.py"


def test_unshaded_id_pass_shows_no_geometric_offset():
    # Geometry must be proven without lighting: a shaded score cannot stand in for this.
    if not IDPASS_QA.exists():
        pytest.skip("ID pass not run")
    a = json.loads(IDPASS_QA.read_text(encoding="utf-8"))["A_geometric_registration"]
    assert a["zero_offset_is_best"], f"registration offset detected: {a['best_offset_dy_dx']}"
    assert a["best_offset_dy_dx"] == [0, 0]
    assert a["exact_class_agreement"] >= 0.999, a["exact_class_agreement"]


def test_final_palette_separates_every_high_contact_neighbour():
    if not PALETTE_QA.exists():
        pytest.skip("palette QA not run")
    qa = json.loads(PALETTE_QA.read_text(encoding="utf-8"))
    assert qa["major_adjacent_pairs_failing"] == [], qa["major_adjacent_pairs_failing"]


def test_every_mapped_class_appears_in_exactly_one_legend_group():
    # No class present in Iran may be dropped from the legend, and no absent class added.
    sys.path.insert(0, str(ROOT / "scripts/rendering"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_poster", POSTER_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    soils, nonsoil, minor = mod.load_classes()
    listed = [c["code"] for c in soils + nonsoil + minor]
    present = [r["classification_code"] for r in csv.DictReader(SOIL_CSV.open(encoding="utf-8"))]
    assert sorted(listed) == sorted(present), (sorted(listed), sorted(present))
    assert len(set(listed)) == len(listed), "a class appears in two legend groups"
    assert [c["code"] for c in nonsoil] == ["WR"], "Open Water must be the non-soil group"
    assert all(c["code"] != "WR" for c in soils + minor), "Open Water shown as a soil"


def test_labels_are_verified_against_the_rasters():
    if not FURNITURE_QA.exists():
        pytest.skip("map furniture not built")
    f = json.loads(FURNITURE_QA.read_text(encoding="utf-8"))
    assert f["labels_failed_verification"] == [], f["labels_failed_verification"]
    assert len(f["labels"]) >= 8
    for lab in f["labels"]:
        assert lab["verified"] and lab["inside_frame"], lab["text"]


def test_scale_bar_decision_follows_the_measurement():
    # A bar may only be drawn because distortion was measured and found small.
    if not FURNITURE_QA.exists():
        pytest.skip("map furniture not built")
    sb = json.loads(FURNITURE_QA.read_text(encoding="utf-8"))["scale_bar"]
    drawn = "bar_km" in POSTER_SCRIPT.read_text(encoding="utf-8")
    if sb["worst_deviation_percent"] >= 2.0:
        assert not drawn, "scale bar drawn although distance scale varies materially"
    else:
        assert "OMIT" not in sb["verdict"]


def test_publication_claim_ceiling_is_not_breached():
    # Wording that would overstate the product must not appear in map or publication text.
    forbidden = ("high-resolution soil map", "30 m soil", "field-validated",
                 "real-time soil", "national soil survey")
    for rel in ("scripts/rendering/build_poster.py", "docs/PUBLICATION_NOTES.md",
                "docs/FINAL_CARTOGRAPHY.md"):
        text = (ROOT / rel).read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            # allowed only where the document explicitly rejects the claim
            # Prose wraps across lines, so check the whole paragraph: a rejection can
            # sit a line above the phrase it rejects.
            for para in text.split(chr(10) + chr(10)):
                if phrase in para:
                    negated = re.search(r"\b(not|never|no|avoid|avoided|"
                                        r"forbidden|cannot|neither|without)\b", para)
                    assert negated, f"{rel}: unqualified claim {phrase!r}"


def test_master_outputs_are_not_git_tracked():
    for rel in ("outputs/master/x.png", "outputs/linkedin/x.png"):
        out = subprocess.run(["git", "check-ignore", rel], cwd=ROOT,
                             capture_output=True, text=True)
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
