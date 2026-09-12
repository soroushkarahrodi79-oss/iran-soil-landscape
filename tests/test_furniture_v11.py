"""Invariants for the CARTOGRAPHIC_FURNITURE_V1_1 gate.

That gate changed composition only. These tests exist to make the claim falsifiable: the
scientific render, the class statistics and the palette have to be exactly where the
previous gate left them, each furniture decision has to still match the measurement that
produced it, and v1.0 has to stay composable after being superseded.

Every check skips cleanly when the artefact it needs has not been produced locally, so the
suite runs on a fresh clone without the multi-gigabyte derived data.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POSTER_SCRIPT = ROOT / "scripts/rendering/build_poster.py"
PALETTE = ROOT / "config/soil_palette.yaml"
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
PUBLICATION_CFG = ROOT / "config/publication.yaml"
META = ROOT / "provenance/metadata"
FURNITURE_QA = META / "map_furniture_qa.json"
FURNITURE_V11_QA = META / "furniture_v11_qa.json"
KEYLINE_QA = META / "keyline_decision_v11.json"
RESIDUAL_QA = META / "palette_residual_v11.json"
VARIANTS_JSON = ROOT / "outputs/proof/furniture_v11/variants.json"
LINKEDIN_REC = ROOT / "outputs/linkedin/linkedin_derivative.json"
RENDER_FREEZE = ROOT / "provenance/checksums/scientific_render_frozen_2026-09-12.txt"


def _publication() -> dict:
    return yaml.safe_load(PUBLICATION_CFG.read_text(encoding="utf-8"))


def _poster():
    spec = importlib.util.spec_from_file_location("build_poster", POSTER_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _soil_rows() -> list[dict]:
    if not SOIL_CSV.exists():
        pytest.skip("soil_groups_iran.csv not generated yet")
    with SOIL_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _frozen_render() -> tuple[str, str]:
    line = next(l for l in RENDER_FREEZE.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#"))
    return line.split()[0], line.split()[-1].lstrip("*")


# --- the map did not move --------------------------------------------------------------

def test_scientific_render_unchanged_by_a_composition_gate():
    # A composition gate that changed the map would be a scientific change wearing a design
    # gate's name. Projection, camera, 2x exaggeration, classification and palette are all
    # baked into this one file, so its hash is the whole check.
    want, rel = _frozen_render()
    if not (ROOT / rel).exists():
        pytest.skip(f"{rel} not present locally")
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert got == want, "SCIENTIFIC RENDER CHANGED during a composition-only gate"


def test_published_sheets_draw_the_frozen_render():
    if not LINKEDIN_REC.exists():
        pytest.skip("sheets not composed yet")
    want, _ = _frozen_render()
    assert json.loads(LINKEDIN_REC.read_text(encoding="utf-8"))["map_render_sha256"] == want
    master = ROOT / _publication()["master"]["path"]
    build = master.parent / (master.stem + ".build.json")
    if build.exists():
        assert json.loads(build.read_text(encoding="utf-8"))["map_render_sha256"] == want


def test_every_v11_direction_drew_the_same_render():
    # "Three furniture treatments over one map" is the premise of the comparison; if the
    # candidates differed in the map itself, choosing between them would mean nothing.
    if not VARIANTS_JSON.exists():
        pytest.skip("v1.1 candidates not built")
    v = json.loads(VARIANTS_JSON.read_text(encoding="utf-8"))
    assert v["same_render_for_every_variant"]
    assert set(v["variants"]) == {"A_academic_minimal", "B_editorial_cartography",
                                  "C_exhibition_poster"}
    want, _ = _frozen_render()
    assert v["map_render_sha256"] == want


def test_exact_class_statistics_are_unchanged():
    # The figures the sheet prints, at the precision it prints them.
    shares = {r["soil_group"]: round(float(r["share_percent"]), 1) for r in _soil_rows()}
    assert shares["Leptosols"] == 40.7
    assert shares["Regosols"] == 18.7
    assert shares["Solonchaks"] == 18.6
    assert shares["Calcisols"] == 16.8
    assert shares["Arenosols"] == 2.1


# --- legend ----------------------------------------------------------------------------

def test_legend_lead_tier_is_chosen_by_share_not_by_taste():
    mod = _poster()
    soils, _, _ = mod.load_classes()
    lead = [c["name"] for c in soils if c["share"] >= mod.LEGEND_MAJOR_MIN]
    assert lead == ["Leptosols", "Regosols", "Solonchaks", "Calcisols"]
    rest = [c["name"] for c in soils if c["share"] < mod.LEGEND_MAJOR_MIN]
    assert rest[0] == "Arenosols", "the next tier must open with the largest class left"


def test_rare_class_note_states_a_bound_the_classes_actually_meet():
    # v1.1 corrected a real error: the note quoted the grouping threshold (0.05%) as though
    # it described the classes, when the largest of the six is 0.015%.
    mod = _poster()
    _, _, minor = mod.load_classes()
    assert minor, "no minor classes to group"
    bound = math.ceil(max(c["share"] for c in minor) * 100.0) / 100.0
    assert bound <= mod.LEGEND_MINOR_MAX
    src = POSTER_SCRIPT.read_text(encoding="utf-8")
    assert "Minor mapped RSGs" in src
    assert "np.ceil(max(c[" in src, (
        "the printed bound must be derived from the classes, not from the grouping constant")


def test_v11_legend_colours_still_come_from_config():
    src = POSTER_SCRIPT.read_text(encoding="utf-8")
    legend = src.split("def _draw_legend_v11")[1].split("def draw_notes")[0]
    assert 'surface["context_land_srgb"]' in legend
    assert 'surface["cartographic_water_srgb"]' in legend
    literal = re.search(r"[\"']#[0-9A-Fa-f]{6}[\"']", legend)
    assert not literal, f"colour literal {literal and literal.group()} in the v1.1 legend"


def test_every_mapped_class_still_appears_exactly_once():
    mod = _poster()
    soils, nonsoil, minor = mod.load_classes()
    listed = [c["code"] for c in soils + nonsoil + minor]
    present = [r["classification_code"] for r in _soil_rows()]
    assert sorted(listed) == sorted(present)
    assert len(set(listed)) == len(listed)


# --- map labels ------------------------------------------------------------------------

def test_every_drawn_label_clears_the_map_edge_and_reads_against_its_background():
    if not FURNITURE_QA.exists():
        pytest.skip("map furniture not built")
    f = json.loads(FURNITURE_QA.read_text(encoding="utf-8"))
    tp = f["text_placement"]
    for lab in f["labels"]:
        assert lab["text_edge_clearance_frac"] >= tp["min_edge_clearance_frac"], lab["text"]
        assert lab["text_background_clutter"] <= tp["clutter_limit"], lab["text"]


def test_sea_labels_are_drawn_on_the_water_they_name():
    # v1.0 verified the anchor and drew the text 2.8% of the frame above it, which put
    # "Gulf of Oman" on the Makran coast. The anchor is still the evidence; the drawn text
    # is now checked too.
    if not FURNITURE_QA.exists():
        pytest.skip("map furniture not built")
    goo = next(l for l in json.loads(FURNITURE_QA.read_text(encoding="utf-8"))["labels"]
               if l["text"] == "Gulf of Oman")
    assert goo["verified"], "anchor no longer on water"
    assert (goo["lon"], goo["lat"]) == (59.3, 25.3), "the verified anchor moved"
    assert goo["text_on_water"], "a sea label drawn over land"
    assert 57.0 <= goo["text_lon"] <= 61.5, (
        f"text at {goo['text_lon']}E is outside the Gulf of Oman")


# --- furniture decisions ---------------------------------------------------------------

def test_national_keyline_follows_its_own_measurement():
    if not KEYLINE_QA.exists():
        pytest.skip("keyline decision not run")
    kd = json.loads(KEYLINE_QA.read_text(encoding="utf-8"))
    drawn = '"boundary_pt": 0.0' not in POSTER_SCRIPT.read_text(encoding="utf-8")
    assert (kd["verdict"] == "REJECT_KEYLINE") != drawn, (
        f"verdict {kd['verdict']} but stroke {'drawn' if drawn else 'not drawn'}")
    if kd["verdict"] == "REJECT_KEYLINE":
        # the reason has to still hold: no width both survives the feed reduction and
        # stays inside HWSD's native support
        assert not [b for b in kd["bill_by_linewidth"]
                    if b["resolves_at_540"] and b["within_one_hwsd_pixel"]]


def test_palette_is_unchanged_unless_the_residual_search_said_otherwise():
    if not RESIDUAL_QA.exists():
        pytest.skip("palette residual search not run")
    pr = json.loads(RESIDUAL_QA.read_text(encoding="utf-8"))
    pal = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    unchanged = all(pal[c] == pr["accepted_palette"][c] for c in pr["codes"])
    assert (pr["verdict"] == "KEEP_EXISTING_PALETTE") == unchanged
    if pr["verdict"] == "KEEP_EXISTING_PALETTE":
        assert pr["search"]["acceptable_candidates"] == 0


def test_sheet_carries_attribution_the_scale_note_and_an_honest_north():
    src = POSTER_SCRIPT.read_text(encoding="utf-8")
    assert "Data: FAO & IIASA · NASA/USGS · Natural Earth · CC BY-NC-SA 4.0" in src
    assert "Scale variation <0.3%" in src
    assert "grid north" in src, "the arrow must say what it can honestly claim"
    assert "bar_km" in src, "the scale bar is drawn from a measured length"


# --- grid and sheet ---------------------------------------------------------------------

def test_the_sheet_hangs_off_one_rail_and_one_rhythm():
    mod = _poster()
    for key in ("v11_a", "v11_b", "v11_c"):
        L = mod.LAYOUTS[key]
        assert L["map_left"] == mod.GRID["margin_l"]
        assert L["map_right"] == mod.GRID["margin_r"]
    if not FURNITURE_V11_QA.exists():
        pytest.skip("furniture v1.1 QA not run")
    for name, v in json.loads(FURNITURE_V11_QA.read_text(encoding="utf-8"))["variants"].items():
        g = v["grid"]
        assert g["all_stops_on_rhythm"], (name, g["off_rhythm_by"])
        assert g["legend_clears_footer"], name
        assert g["map_share_of_sheet_height"] > 0.55, (
            f"{name}: the map must stay the dominant area of the sheet")


def test_feed_type_minimums_cover_the_furniture_this_gate_added():
    if not LINKEDIN_REC.exists():
        pytest.skip("feed sheet not built")
    rec = json.loads(LINKEDIN_REC.read_text(encoding="utf-8"))
    assert rec["failing_elements"] == [], rec["failing_elements"]
    measured = rec["type_at_preview_size"]
    for element in ("title", "method", "attribution", "legend_major", "rare",
                    "scale_label", "north", "nonsoil", "subtitle"):
        assert element in measured, f"{element} is not measured at feed size"
        assert measured[element]["pass"], element


def test_published_pair_is_declared_and_v1_0_is_preserved():
    pub = _publication()
    mod = _poster()
    assert pub["master"]["layout"] in mod.LAYOUTS
    assert pub["linkedin"]["layout"] in mod.LAYOUTS
    old = pub["superseded"][0]
    assert old["version"] == "v1.0"
    for layout in old["layouts"]:
        assert layout in mod.LAYOUTS, f"v1.0 layout {layout} is no longer composable"
    assert pub["master"]["path"] != old["master"]
    assert pub["linkedin"]["path"] != old["linkedin"]


def test_v11_outputs_are_not_git_tracked():
    for rel in ("outputs/master/iran_soil_landscapes_v1_1_6000x7500.png",
                "outputs/linkedin/iran_soil_landscapes_v1_1_2160x2700.png",
                "outputs/proof/furniture_v11/B_editorial_cartography_2160x2700.png"):
        out = subprocess.run(["git", "check-ignore", rel], cwd=ROOT,
                             capture_output=True, text=True)
        assert out.stdout.strip() == rel, f"{rel} is not gitignored"


def test_v1_0_layouts_still_compose():
    """Superseding v1.0 must not quietly break it.

    The first attempt at this gate did exactly that: shared drawing code started reading
    v1.1-only layout keys, and both v1.0 layouts died with a KeyError that no test saw,
    because the tests only checked that the layout keys still existed in the dict.
    """
    render = ROOT / "outputs/proof/3d/iran_map_2x_topdown_5400x4897.png"
    if not (render.exists() and FURNITURE_QA.exists()):
        pytest.skip("scientific render or furniture metadata not present locally")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for layout in _publication()["superseded"][0]["layouts"]:
            r = subprocess.run(
                [__import__("sys").executable, str(POSTER_SCRIPT), "--map", str(render),
                 "--width", "600", "--layout", layout, "--out", tmp,
                 "--name", f"smoke_{layout}"],
                capture_output=True, text=True, cwd=ROOT)
            assert r.returncode == 0, f"{layout} no longer composes:\n{r.stderr[-1500:]}"
            assert (Path(tmp) / f"smoke_{layout}.png").exists()
