"""Can the one documented palette residual be bought out without spending something else?

`FINAL_CARTOGRAPHY.md` accepts exactly one colour limitation: Arenosols and Solonchaks are
unmistakable in colour (ΔE00 38.1) but nearly the same lightness (ΔL* 4.4), so a greyscale
reproduction loses the boundary between them. They share 6,435 boundary pixels, which is
real contact, so the residual is worth re-testing rather than re-asserting.

This does not change the palette. It searches for a display colour that would, and reports
whether one exists that pays for the improvement without taking it out of some other pair:

  * lightness moves only — hue and chroma are held in CIELCh, so class identity (amber
    sand, pink salt) survives the change
  * the candidate must reach a materially better ΔL* on the residual pair
  * EVERY high-contact pair in Iran must still clear ΔE00 >= 10 in normal vision and under
    both simulated dichromacies — the standard this project already holds itself to
  * no pair may be pushed below the ΔL* floor, and a pair already below it may not be
    pushed lower still — "it was already failing" is not a licence to make it worse
  * the pair must stay separable under the deepest shading the accepted 2x render produces
  * the two display surfaces a coastal class actually touches — cartographic water and the
    neutral ground outside Iran — are treated as neighbours too, with their own measured
    contact lengths. A greyscale fix that separates two soils by merging one of them into
    "no soil data shown" has moved the residual, not removed it.

The palette is baked into the Blender render, so accepting a candidate is not a layout
change — it is a re-render of the scientific map. The bar is therefore set at "clearly
better and costs nothing", not "different".

    python scripts/validation/qa_palette_residual.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[2]
PALETTE = ROOT / "config/soil_palette.yaml"
RENDER_CFG = ROOT / "config/render_3d.yaml"
RENDER_DIR = ROOT / "data/processed/render"
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
PALETTE_QA = ROOT / "provenance/metadata/palette_final_qa.json"
PROTO_QA = ROOT / "provenance/metadata/prototype_3d_qa.json"
OUT = ROOT / "provenance/metadata/palette_residual_v11.json"

RESIDUAL_PAIR = ("AR", "SC")
DELTA_L_TARGET = 8.0            # "materially improves": roughly double the 4.4 residual
DELTA_E_ADJACENT_MIN = 10.0     # the project's standing threshold
DELTA_L_MIN = 5.0
MAJOR_BORDER_PX = 20000
L_STEP = 0.5
L_RANGE = 9.0                   # how far either class may be moved in L*


def _qp():
    spec = importlib.util.spec_from_file_location(
        "qa_palette_final", ROOT / "scripts/validation/qa_palette_final.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


qp = _qp()


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Inverse of qa_palette_final.srgb_to_lab, so a candidate L* returns a real colour."""
    L, a, b = lab
    fy = (L + 16.0) / 116.0
    fx, fz = fy + a / 500.0, fy - b / 200.0
    d = 6.0 / 29.0

    def finv(t):
        return t ** 3 if t > d else 3 * d * d * (t - 4.0 / 29.0)

    white = np.array([0.95047, 1.0, 1.08883])
    xyz = np.array([finv(fx), finv(fy), finv(fz)]) * white
    m = np.array([[3.2404542, -1.5371385, -0.4985314],
                  [-0.9692660, 1.8760108, 0.0415560],
                  [0.0556434, -0.2040259, 1.0572252]])
    lin = xyz @ m.T
    # Gamut is decided in linear RGB, before the transfer function: a negative linear
    # component is a colour sRGB cannot show, and clipping it would silently change the
    # hue the candidate was built to preserve.
    in_gamut = bool(np.all(lin >= -1e-6) and np.all(lin <= 1.0 + 1e-6))
    lin = np.clip(lin, 0.0, 1.0)
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    return srgb, in_gamut


def shift_lightness(hex_colour: str, dL: float) -> tuple[str, np.ndarray, bool]:
    """Move a colour in L* only, holding hue and chroma. Returns hex, rgb01, in-gamut."""
    lab = qp.srgb_to_lab(qp.hex_to_rgb01(hex_colour))
    rgb, in_gamut = lab_to_srgb(np.array([lab[0] + dL, lab[1], lab[2]]))
    q = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(int)
    return "#" + "".join(f"{v:02X}" for v in q), q / 255.0, in_gamut


def _roundtrip_self_test() -> None:
    """The inverse must return the colours it was given, or the search is measuring noise."""
    worst = 0.0
    for h in ("#E3B15A", "#E3B9D6", "#F2E8C6", "#8B8A83", "#2B2B2B", "#FFFFFF", "#2E8B6B"):
        rgb, ok = lab_to_srgb(qp.srgb_to_lab(qp.hex_to_rgb01(h)))
        worst = max(worst, float(np.abs(rgb - qp.hex_to_rgb01(h)).max()))
        if not ok:
            raise SystemExit(f"round-trip reports {h} out of gamut")
    if worst > 1e-6:
        raise SystemExit(f"Lab->sRGB round-trip error {worst:.2e}, expected < 1e-6")
    print(f"Lab->sRGB inverse self-test: 7/7 colours round-trip within {worst:.1e}")


def display_surface_adjacency(pid: dict[int, str]) -> dict[tuple[str, str], int]:
    """How much boundary each soil class actually shares with the two display surfaces.

    Cartographic water and the ground outside Iran are not soil classes, so they are absent
    from the ID raster's own adjacency — yet every coastal and border class is drawn against
    them. Measuring the contact here puts them into the same test as any other neighbour.
    """
    ids = np.asarray(Image.open(RENDER_DIR / "iran_soil_ids_render.tif"))
    water = np.asarray(Image.open(RENDER_DIR / "iran_water_mask.png").convert("L"))
    cfg = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))["surface"]
    wet = water >= int(cfg["water_threshold"])
    outside = (ids == 0) & ~wet
    out: dict[tuple[str, str], int] = {}
    for surf, mask in (("CWA", wet), ("CTX", outside)):
        for dy, dx in ((0, 1), (1, 0)):
            a_ = ids[:-1, :] if dy else ids[:, :-1]
            b_ = ids[1:, :] if dy else ids[:, 1:]
            ma = mask[:-1, :] if dy else mask[:, :-1]
            mb = mask[1:, :] if dy else mask[:, 1:]
            for sid, smask in ((a_, mb), (b_, ma)):
                m = (sid > 0) & smask
                if not m.any():
                    continue
                vals, counts = np.unique(sid[m], return_counts=True)
                for v, n in zip(vals, counts):
                    if int(v) in pid:
                        key = tuple(sorted((pid[int(v)], surf)))
                        out[key] = out.get(key, 0) + int(n)
    return out


def evaluate(palette: dict[str, str], adjacency: dict, names: dict,
             shade_lo: float) -> dict:
    """Score a whole palette the way qa_palette_final scores the accepted one."""
    rgb = {c: qp.hex_to_rgb01(h) for c, h in palette.items()}
    lab = {c: qp.srgb_to_lab(rgb[c]) for c in palette}
    deut = {c: qp.srgb_to_lab(qp.simulate_cvd(rgb[c], "deuteranopia")) for c in palette}
    prot = {c: qp.srgb_to_lab(qp.simulate_cvd(rgb[c], "protanopia")) for c in palette}
    rows = []
    for (c1, c2), border in adjacency.items():
        rows.append({
            "pair": f"{names[c1]} / {names[c2]}", "codes": [c1, c2],
            "shared_border_px": border,
            "delta_e2000": float(qp.ciede2000(lab[c1], lab[c2])),
            "delta_L": abs(float(lab[c1][0] - lab[c2][0])),
            "delta_e_deuteranopia": float(qp.ciede2000(deut[c1], deut[c2])),
            "delta_e_protanopia": float(qp.ciede2000(prot[c1], prot[c2])),
            "delta_e_under_deepest_shade": float(
                qp.ciede2000(lab[c1], qp.srgb_to_lab(rgb[c2] * shade_lo))),
        })
    major_fail = [r["pair"] for r in rows if r["shared_border_px"] >= MAJOR_BORDER_PX
                  and (r["delta_e2000"] < DELTA_E_ADJACENT_MIN
                       or min(r["delta_e_deuteranopia"],
                              r["delta_e_protanopia"]) < DELTA_E_ADJACENT_MIN)]
    low_L = {r["pair"] for r in rows if r["delta_L"] < DELTA_L_MIN}
    return {"rows": rows, "major_failing": major_fail, "low_luminance_pairs": low_L,
            "by_pair": {r["pair"]: r for r in rows}}


def regressions(current: dict, trial: dict, tol: float = 0.05) -> list[str]:
    """Pairs the candidate makes worse in a way that matters.

    The floor is per pair: a pair sitting above the threshold may not be dropped below it,
    and a pair already below may not be pushed any lower. Without the second half of that
    rule a candidate can "pass" by taking lightness out of a pair that was already the
    weakest on the sheet.
    """
    out = []
    for pair, cur in current["by_pair"].items():
        new = trial["by_pair"][pair]
        for key, floor in (("delta_L", DELTA_L_MIN), ("delta_e2000", DELTA_E_ADJACENT_MIN)):
            allowed = min(cur[key], floor)
            if new[key] < allowed - tol:
                out.append(f"{pair}: {key} {cur[key]:.2f} -> {new[key]:.2f}")
    return out


def main() -> None:
    qp.self_test()
    _roundtrip_self_test()
    pal = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    rows = list(csv.DictReader(SOIL_CSV.open(encoding="utf-8")))
    codes = [r["classification_code"] for r in rows]
    names = {r["classification_code"]: r["soil_group"] for r in rows}
    pid = {int(r["wrb2_project_int"]): r["classification_code"] for r in rows}
    surface = yaml.safe_load(RENDER_CFG.read_text(encoding="utf-8"))["surface"]
    base = {c: pal[c] for c in codes}
    base["CWA"] = surface["cartographic_water_srgb"]
    base["CTX"] = surface["context_land_srgb"]
    names = dict(names)
    names["CWA"] = "Seas and lakes (display)"
    names["CTX"] = "Outside Iran (display)"
    adjacency = qp.adjacency_counts(pid)
    adjacency.update(display_surface_adjacency(pid))
    shade_lo = float(json.loads(PROTO_QA.read_text(encoding="utf-8"))
                     ["by_exaggeration"]["2x"]["p01_shading"])

    for (c1, c2), n in sorted(adjacency.items(), key=lambda kv: -kv[1])[:6]:
        if "CWA" in (c1, c2) or "CTX" in (c1, c2):
            print(f"  display-surface contact: {names[c1]} / {names[c2]}: {n:,} px")

    a, b = RESIDUAL_PAIR
    border = adjacency.get(tuple(sorted((a, b))), 0)
    current = evaluate(base, adjacency, names, shade_lo)
    cur_pair = next(r for r in current["rows"] if set(r["codes"]) == {a, b})
    print(f"residual pair: {names[a]} / {names[b]} - {border:,} shared boundary px")
    print(f"  as accepted: dE00 {cur_pair['delta_e2000']:.1f}, dL* {cur_pair['delta_L']:.2f}, "
          f"deut {cur_pair['delta_e_deuteranopia']:.1f}, prot {cur_pair['delta_e_protanopia']:.1f}")
    print(f"  target: dL* >= {DELTA_L_TARGET} with no new high-contact failure and no new "
          f"low-luminance pair\n")

    steps = int(L_RANGE / L_STEP)
    worst_regressions: dict[str, int] = {}
    candidates, rejected = [], {"out_of_gamut": 0, "target_not_met": 0,
                                "new_major_failure": 0, "new_low_luminance": 0,
                                "shade_regression": 0}
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            dLa, dLb = i * L_STEP, j * L_STEP
            if dLa == 0 and dLb == 0:
                continue
            hex_a, _, ok_a = shift_lightness(base[a], dLa)
            hex_b, _, ok_b = shift_lightness(base[b], dLb)
            if not (ok_a and ok_b):
                rejected["out_of_gamut"] += 1
                continue
            trial = dict(base)
            trial[a], trial[b] = hex_a, hex_b
            res = evaluate(trial, adjacency, names, shade_lo)
            pair = next(r for r in res["rows"] if set(r["codes"]) == {a, b})
            if pair["delta_L"] < DELTA_L_TARGET:
                rejected["target_not_met"] += 1
                continue
            if pair["delta_e2000"] < DELTA_E_ADJACENT_MIN or min(
                    pair["delta_e_deuteranopia"], pair["delta_e_protanopia"]) < DELTA_E_ADJACENT_MIN:
                rejected["new_major_failure"] += 1
                continue
            if set(res["major_failing"]) - set(current["major_failing"]):
                rejected["new_major_failure"] += 1
                continue
            reg = regressions(current, res)
            if reg:
                rejected["new_low_luminance"] += 1
                worst_regressions.setdefault(reg[0].split(":")[0], 0)
                worst_regressions[reg[0].split(":")[0]] += 1
                continue
            if pair["delta_e_under_deepest_shade"] < cur_pair["delta_e_under_deepest_shade"] * 0.9:
                rejected["shade_regression"] += 1
                continue
            candidates.append({
                "delta_L_shift": [dLa, dLb], "hex": {a: hex_a, b: hex_b},
                "delta_L": round(pair["delta_L"], 2),
                "delta_e2000": round(pair["delta_e2000"], 2),
                "deuteranopia": round(pair["delta_e_deuteranopia"], 2),
                "protanopia": round(pair["delta_e_protanopia"], 2),
                "under_deepest_shade": round(pair["delta_e_under_deepest_shade"], 2),
                "total_shift": round(abs(dLa) + abs(dLb), 2),
            })

    candidates.sort(key=lambda c: (c["total_shift"], -c["delta_L"]))
    print(f"searched {(2 * steps + 1) ** 2 - 1} lightness pairs "
          f"(+/-{L_RANGE} L* each, {L_STEP} steps), hue and chroma held")
    rejected["regressed_another_pair"] = rejected.pop("new_low_luminance")
    for k, v in rejected.items():
        print(f"  rejected {k:<24} {v}")
    for pair, n in sorted(worst_regressions.items(), key=lambda kv: -kv[1])[:4]:
        print(f"      most often regressed: {pair} ({n} candidates)")
    print(f"  ACCEPTABLE CANDIDATES      {len(candidates)}")

    verdict = "KEEP_EXISTING_PALETTE"
    chosen = None
    if candidates:
        chosen = candidates[0]
        print(f"\nsmallest acceptable change: {a} {base[a]} -> {chosen['hex'][a]} "
              f"(dL* {chosen['delta_L_shift'][0]:+.1f}), "
              f"{b} {base[b]} -> {chosen['hex'][b]} (dL* {chosen['delta_L_shift'][1]:+.1f})")
        print(f"  gives dL* {chosen['delta_L']:.2f} (was {cur_pair['delta_L']:.2f}), "
              f"dE00 {chosen['delta_e2000']:.1f}, deut {chosen['deuteranopia']:.1f}, "
              f"prot {chosen['protanopia']:.1f}")
        verdict = "CANDIDATE_EXISTS_REQUIRES_RERENDER"

    OUT.write_text(json.dumps({
        "residual_pair": [names[a], names[b]], "codes": list(RESIDUAL_PAIR),
        "shared_border_px": border,
        "accepted_palette": {a: base[a], b: base[b]},
        "accepted": {k: round(v, 3) for k, v in cur_pair.items()
                     if isinstance(v, (int, float))},
        "search": {"method": "CIELCh lightness only; hue and chroma held so class identity "
                             "survives", "l_range": L_RANGE, "l_step": L_STEP,
                   "delta_L_target": DELTA_L_TARGET,
                   "constraints": ["no new high-contact ΔE00 failure (normal, deuteranopia, "
                                   "protanopia)", "no new pair below the ΔL* floor",
                                   "no regression under the deepest measured 2x shading",
                                   "in sRGB gamut"],
                   "rejected_counts": rejected,
                   "acceptable_candidates": len(candidates)},
        "best_candidate": chosen,
        "verdict": verdict,
        "note": "The palette is baked into the Blender render, so adopting a candidate is a "
                "re-render of the scientific map, not a layout change.",
    }, indent=2) + chr(10), encoding="utf-8")
    print(f"\nVERDICT: {verdict}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
