"""FINAL_SCIENTIFIC_QA — re-verify every publication claim against the artefacts.

This runs last, after the master exists, and re-checks the things that would embarrass the
project if they were wrong: that the frozen inputs never moved, that the map still carries
exactly the classes the raster contains, that every claim printed on the poster is true,
and that the derivative really came from the master.

Each check is independent and reports PASS/FAIL; the script exits non-zero if any fails.

    python scripts/validation/qa_final_publication.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "provenance/metadata"
MASTER = ROOT / "outputs/master/iran_soil_landscapes_6000x7500.png"
LINKEDIN = ROOT / "outputs/linkedin/iran_soil_landscapes_linkedin_2160x2700.png"
POSTER_SRC = ROOT / "scripts/rendering/build_poster.py"
OUT = META / "final_publication_qa.json"


def check_frozen(results: list) -> None:
    for name in ("soil_truth_frozen_2026-09-08.txt", "dem_frozen_2026-09-09.txt"):
        f = ROOT / "provenance/checksums" / name
        bad = []
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            want, rel = line.split()[0], line.split()[-1].lstrip("*")
            got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            if got != want:
                bad.append(rel)
        results.append({"check": f"frozen inputs unchanged ({name.split('_')[0]})",
                        "pass": not bad, "detail": bad or "all hashes match"})


def check_classes(results: list) -> None:
    ids = np.asarray(Image.open(ROOT / "data/processed/render/iran_soil_ids_render.tif"))
    present = {int(v) for v in np.unique(ids) if v != 0}
    rows = list(csv.DictReader((ROOT / "data/processed/tables/soil_groups_iran.csv")
                               .open(encoding="utf-8")))
    expected = {int(r["wrb2_project_int"]) for r in rows}
    results.append({"check": "render class IDs == frozen soil table",
                    "pass": present == expected,
                    "detail": f"{len(present)} classes; "
                              f"missing {sorted(expected - present)}, extra {sorted(present - expected)}"})


def check_geometry(results: list) -> None:
    idq = json.loads((META / "registration_idpass_qa.json").read_text(encoding="utf-8"))
    a = idq["A_geometric_registration"]
    results.append({"check": "unlit ID pass: no geometric offset",
                    "pass": a["zero_offset_is_best"] and a["exact_class_agreement"] >= 0.999,
                    "detail": f"agreement {a['exact_class_agreement']:.6f}, "
                              f"best offset {a['best_offset_dy_dx']}"})
    pq = json.loads((META / "palette_final_qa.json").read_text(encoding="utf-8"))
    results.append({"check": "palette: all high-contact neighbours separable",
                    "pass": not pq["major_adjacent_pairs_failing"],
                    "detail": pq["major_adjacent_pairs_failing"] or "none failing"})
    fq = json.loads((META / "map_furniture_qa.json").read_text(encoding="utf-8"))
    results.append({"check": "labels verified against the rasters",
                    "pass": not fq["labels_failed_verification"],
                    "detail": f"{len(fq['labels'])} labels, "
                              f"{fq['labels_failed_verification'] or 'none failing'}"})
    results.append({"check": "scale bar supported by measurement",
                    "pass": fq["scale_bar"]["worst_deviation_percent"] < 2.0,
                    "detail": f"worst distance deviation "
                              f"{fq['scale_bar']['worst_deviation_percent']:.3f}%"})


def check_poster_claims(results: list) -> None:
    src = POSTER_SRC.read_text(encoding="utf-8")
    required = {
        "FAO & IIASA attribution": "FAO & IIASA",
        "HWSD version": "v2.01",
        "licence notice on the map": "CC BY-NC-SA 4.0",
        "terrain source": "SRTMGL3",
        "Natural Earth credit": "Natural Earth",
        "exaggeration disclosed": "2× vertical",
        "native soil resolution stated": "~1 km resolution",
        "dominant-not-point wording": "not the soil at any single",
        "equal-area projection named": "Lambert azimuthal equal-area",
    }
    for label, needle in required.items():
        results.append({"check": f"poster states: {label}", "pass": needle in src,
                        "detail": needle})
    forbidden = ("high-resolution soil map", "30 m soil map", "field-validated",
                 "real-time soil")
    hits = [f for f in forbidden if f in src.lower()]
    results.append({"check": "no claim beyond the publication ceiling",
                    "pass": not hits, "detail": hits or "none present"})


def check_shaded_readability(results: list) -> None:
    """Re-measure class readability on the PUBLISHED map, not on a superseded render.

    The prototype figure was computed under the prototype palette. Quoting it for a map
    whose colours have since changed would be citing a stale number, so it is recomputed
    here against the final palette and the final 2x render.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qa3d", ROOT / "scripts/validation/qa_3d_prototype.py")
    qa3d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa3d)

    import yaml
    cfg = yaml.safe_load((ROOT / "config/render_3d.yaml").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "data/processed/render/blender/blender_inputs.json")
                      .read_text(encoding="utf-8"))
    render_dir = ROOT / "data/processed/render"
    soil_a = np.asarray(Image.open(render_dir / "iran_soil_texture.png").convert("RGBA"))[..., 3]
    water = np.asarray(Image.open(render_dir / "iran_water_mask.png").convert("L"))
    base = np.asarray(Image.open(render_dir / "blender/iran_render_basecolor.png").convert("RGB"))
    land = (soil_a > 0) & (water < int(cfg["surface"]["water_threshold"]))
    land_r = qa3d.grid_to_render(land.astype(np.uint8), cfg, meta, "topdown") > 0
    base_r = qa3d.grid_to_render(base, cfg, meta, "topdown")

    pal = yaml.safe_load((ROOT / "config/soil_palette.yaml").read_text(encoding="utf-8"))
    codes = [r["classification_code"] for r in csv.DictReader(
        (ROOT / "data/processed/tables/soil_groups_iran.csv").open(encoding="utf-8"))]
    palette_hex = [pal["wrb2_rsg_colours"][c] for c in codes]

    # Classify in full CIELAB, not chromaticity. Chromaticity throws away lightness, which
    # puts Chernozems (#2B2B2B, pure neutral, 6.7 km2 of Iran) 0.0088 from Leptosols
    # (#8B8A83) — closer than any real neighbour. Leptosols is 40.7% of the map, so a
    # chromaticity metric reassigns a slice of the country to an invisible class and reports
    # a readability failure that no reader could experience. Shading at 2x is mild
    # (mean 0.978), so lightness stays informative.
    spec2 = importlib.util.spec_from_file_location(
        "qapal", ROOT / "scripts/validation/qa_palette_final.py")
    qapal = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(qapal)

    render = ROOT / "outputs/proof/3d/iran_map_2x_topdown_2500x2267.png"
    img = np.asarray(Image.open(render).convert("RGB")).astype(np.float64) / 255.0

    # measure on locally-constant palette pixels: a class edge disagrees for sampling
    # reasons at any palette, and would be charged to readability
    flat = np.ones(base_r.shape[:2], dtype=bool)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        flat &= (np.roll(np.roll(base_r, dy, axis=0), dx, axis=1) == base_r).all(axis=2)
    mask = land_r & flat

    pal_lab = qapal.srgb_to_lab(np.array([qapal.hex_to_rgb01(h) for h in palette_hex]))

    def nearest_lab(rgb01: np.ndarray) -> np.ndarray:
        lab = qapal.srgb_to_lab(rgb01)
        out = np.empty(len(lab), dtype=np.int16)
        for i in range(0, len(lab), 200_000):
            blk = lab[i:i + 200_000]
            out[i:i + 200_000] = np.argmin(
                ((blk[:, None, :] - pal_lab[None, :, :]) ** 2).sum(-1), axis=1)
        return out

    expected = nearest_lab(base_r[mask].astype(np.float64) / 255.0)
    observed = nearest_lab(img[mask])
    agree = float((expected == observed).mean())
    results.append({"check": "shaded class readability on the published map (NOT registration)",
                    "pass": agree >= 0.99,
                    "detail": f"{agree:.5f} over {int(mask.sum()):,} px at 2x, final palette, "
                              f"CIELAB nearest-class"})


def check_outputs(results: list) -> None:
    m = Image.open(MASTER)
    results.append({"check": "master is 4:5 and >= 6000x7500",
                    "pass": m.size == (6000, 7500),
                    "detail": f"{m.size[0]}x{m.size[1]}"})
    d = Image.open(LINKEDIN)
    rec = json.loads((LINKEDIN.parent / "linkedin_derivative.json").read_text(encoding="utf-8"))
    master_build = json.loads(
        (MASTER.parent / (MASTER.stem + ".build.json")).read_text(encoding="utf-8"))
    # The feed sheet is a re-composition, not a downsample, so the invariant is that both
    # sheets draw the SAME scientific render — proven by hash, not by resemblance.
    same_render = rec["map_render_sha256"] == master_build["map_render_sha256"]
    results.append({"check": "LinkedIn sheet draws the same scientific render as the master",
                    "pass": same_render and d.size == (2160, 2700),
                    "detail": f"{d.size[0]}x{d.size[1]}, map {rec['map_render']} "
                              f"sha {rec['map_render_sha256'][:12]}… "
                              f"{'matches' if same_render else 'DIFFERS FROM'} master"})
    results.append({"check": "LinkedIn type clears its feed-size minimum at 540 px",
                    "pass": not rec["failing_elements"],
                    "detail": rec["failing_elements"] or
                              f"method {rec['type_at_preview_size']['method']['preview_px']} px, "
                              f"attribution "
                              f"{rec['type_at_preview_size']['attribution']['preview_px']} px"})
    results.append({"check": "LinkedIn map frame enlarged over the master",
                    "pass": rec["map_width_fraction"] > master_build["map_width_fraction"],
                    "detail": f"{master_build['map_width_fraction']:.3f} -> "
                              f"{rec['map_width_fraction']:.3f} of sheet width "
                              f"(+{(rec['map_width_fraction'] / master_build['map_width_fraction'] - 1) * 100:.1f}%)"})
    results.append({"check": "archival master is lossless",
                    "pass": MASTER.suffix.lower() in (".png", ".tif", ".tiff"),
                    "detail": MASTER.suffix})


def main() -> None:
    results: list[dict] = []
    check_frozen(results)
    check_classes(results)
    check_geometry(results)
    check_poster_claims(results)
    check_shaded_readability(results)
    check_outputs(results)

    failed = [r for r in results if not r["pass"]]
    OUT.write_text(json.dumps({"checks": results, "failed": len(failed),
                               "verdict": "PASS" if not failed else "FAIL"},
                              indent=2) + chr(10), encoding="utf-8")
    for r in results:
        print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['check']}: {r['detail']}")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks pass")
    if failed:
        raise SystemExit(f"FINAL QA FAILED: {[r['check'] for r in failed]}")


if __name__ == "__main__":
    main()
