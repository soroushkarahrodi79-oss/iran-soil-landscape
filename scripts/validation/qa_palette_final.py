"""FINAL_PALETTE QA — categorical distinguishability under the accepted 2x relief.

Colour here is display-only: class boundaries and class identity are frozen and this
script cannot move them. What it can do is test whether the display colours survive the
ways a categorical map fails its reader:

  1. adjacent-class confusion   pairs that actually touch on the map, in CIEDE2000
  2. luminance hierarchy        separable without colour at all
  3. colour-vision robustness   deuteranopia and protanopia (Vienot-Brettel-Mollon)
  4. shadow interference        the same pairs under the measured 2x shading range

Pairs are weighted by how much boundary they actually share in Iran: low contrast between
classes that never meet matters far less than between true neighbours.

CIEDE2000 is implemented here rather than taken from an unavailable dependency, and is
self-tested against the published Sharma et al. (2005) reference pairs before any result
is used.

    python scripts/validation/qa_palette_final.py
"""
from __future__ import annotations

import csv
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
SOIL_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
IDS = ROOT / "data/processed/render/iran_soil_ids_render.tif"
PROTO_QA = ROOT / "provenance/metadata/prototype_3d_qa.json"
OUT = ROOT / "provenance/metadata/palette_final_qa.json"

DELTA_E_ADJACENT_MIN = 10.0     # touching classes must be clearly different
DELTA_L_MIN = 5.0               # and separable without colour at all
MAJOR_BORDER_PX = 20000         # "high-contact" neighbours


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_xyz(rgb: np.ndarray) -> np.ndarray:
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    return rgb @ m.T


def xyz_to_lab(xyz: np.ndarray) -> np.ndarray:
    white = np.array([0.95047, 1.0, 1.08883])
    t = xyz / white
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def srgb_to_lab(rgb01: np.ndarray) -> np.ndarray:
    return xyz_to_lab(linear_to_xyz(srgb_to_linear(rgb01)))


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(C1p * C2p == 0, 0,
                   np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hsum, hdiff = h1p + h2p, np.abs(h1p - h2p)
    hbp = np.where(C1p * C2p == 0, hsum,
                   np.where(hdiff <= 180, hsum / 2,
                            np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                   + Rt * (dCp / Sc) * (dHp / Sh))


def self_test() -> None:
    """Sharma et al. (2005) reference pairs: the implementation must reproduce these."""
    cases = [((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
             ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
             ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
             ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
             ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644)]
    for lab1, lab2, want in cases:
        got = float(ciede2000(np.array(lab1), np.array(lab2)))
        if abs(got - want) > 0.001:
            raise SystemExit(f"CIEDE2000 self-test FAILED: {lab1} vs {lab2} -> {got}, want {want}")
    print(f"CIEDE2000 self-test: {len(cases)}/{len(cases)} published reference pairs reproduced")


def simulate_cvd(rgb01: np.ndarray, kind: str) -> np.ndarray:
    """Vienot, Brettel & Mollon (1999) dichromat simulation, applied in linear RGB."""
    lin = srgb_to_linear(rgb01)
    to_lms = np.array([[17.8824, 43.5161, 4.11935],
                       [3.45565, 27.1554, 3.86714],
                       [0.0299566, 0.184309, 1.46709]])
    lms = lin @ to_lms.T
    if kind == "deuteranopia":
        m = np.array([[1.0, 0.0, 0.0], [0.494207, 0.0, 1.24827], [0.0, 0.0, 1.0]])
    elif kind == "protanopia":
        m = np.array([[0.0, 2.02344, -2.52581], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    else:
        raise ValueError(kind)
    return np.clip((lms @ m.T) @ np.linalg.inv(to_lms).T, 0.0, 1.0)


def hex_to_rgb01(value: str) -> np.ndarray:
    h = value.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255.0


def adjacency_counts(pid: dict[int, str]) -> dict[tuple[str, str], int]:
    ids = np.asarray(Image.open(IDS))
    out: dict[tuple[str, str], int] = {}
    for dy, dx in ((0, 1), (1, 0)):
        a = ids[:-1 or None, :] if dy else ids[:, :-1]
        b = ids[1:, :] if dy else ids[:, 1:]
        m = (a > 0) & (b > 0) & (a != b)
        if not m.any():
            continue
        pairs, counts = np.unique(np.stack([a[m], b[m]]), axis=1, return_counts=True)
        for (p, q), n in zip(pairs.T, counts):
            if int(p) in pid and int(q) in pid:
                key = tuple(sorted((pid[int(p)], pid[int(q)])))
                out[key] = out.get(key, 0) + int(n)
    return out


def main() -> None:
    self_test()
    pal = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    rows = list(csv.DictReader(SOIL_CSV.open(encoding="utf-8")))
    codes = [r["classification_code"] for r in rows]
    names = {r["classification_code"]: r["soil_group"] for r in rows}
    share = {r["classification_code"]: float(r["share_percent"]) for r in rows}
    pid = {int(r["wrb2_project_int"]): r["classification_code"] for r in rows}

    rgb = {c: hex_to_rgb01(pal[c]) for c in codes}
    lab = {c: srgb_to_lab(rgb[c]) for c in codes}

    shading = json.loads(PROTO_QA.read_text(encoding="utf-8"))["by_exaggeration"]["2x"]
    shade_lo = float(shading["p01_shading"])

    findings = []
    for (c1, c2), border in sorted(adjacency_counts(pid).items(), key=lambda kv: -kv[1]):
        de = float(ciede2000(lab[c1], lab[c2]))
        dl = abs(float(lab[c1][0] - lab[c2][0]))
        de_deut = float(ciede2000(srgb_to_lab(simulate_cvd(rgb[c1], "deuteranopia")),
                                  srgb_to_lab(simulate_cvd(rgb[c2], "deuteranopia"))))
        de_prot = float(ciede2000(srgb_to_lab(simulate_cvd(rgb[c1], "protanopia")),
                                  srgb_to_lab(simulate_cvd(rgb[c2], "protanopia"))))
        # worst case: one class fully lit against its neighbour in the deepest measured shade
        de_shadow = float(ciede2000(lab[c1], srgb_to_lab(rgb[c2] * shade_lo)))
        findings.append({
            "pair": f"{names[c1]} / {names[c2]}", "codes": [c1, c2],
            "shared_border_px": border,
            "delta_e2000": round(de, 2), "delta_L": round(dl, 2),
            "delta_e_deuteranopia": round(de_deut, 2),
            "delta_e_protanopia": round(de_prot, 2),
            "delta_e_under_deepest_shade": round(de_shadow, 2),
            "pass_adjacent": de >= DELTA_E_ADJACENT_MIN,
            "pass_luminance": dl >= DELTA_L_MIN,
            "pass_cvd": min(de_deut, de_prot) >= DELTA_E_ADJACENT_MIN,
        })

    failing = [f for f in findings if not (f["pass_adjacent"] and f["pass_cvd"])]
    major_failing = [f for f in failing if f["shared_border_px"] >= MAJOR_BORDER_PX]
    payload = {
        "thresholds": {"delta_e2000_adjacent_min": DELTA_E_ADJACENT_MIN,
                       "delta_L_min": DELTA_L_MIN,
                       "major_border_px": MAJOR_BORDER_PX,
                       "shading_p01_at_2x": shade_lo},
        "classes": {c: {"name": names[c], "hex": pal[c].upper(),
                        "share_percent": share[c],
                        "L_star": round(float(lab[c][0]), 1)} for c in codes},
        "adjacent_pairs": findings,
        "adjacent_pairs_failing": [f["pair"] for f in failing],
        "major_adjacent_pairs_failing": [f["pair"] for f in major_failing],
    }
    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    print(f"\n{len(findings)} class pairs actually share a boundary in Iran")
    header = f"{'pair':<34}{'border px':>11}{'dE00':>7}{'dL':>6}{'deut':>7}{'prot':>7}  flags"
    print(header)
    for f in findings[:14]:
        flags = "".join(["" if f["pass_adjacent"] else " LOW-dE",
                         "" if f["pass_luminance"] else " LOW-L",
                         "" if f["pass_cvd"] else " CVD"])
        print(f"{f['pair']:<34}{f['shared_border_px']:>11,}{f['delta_e2000']:>7.1f}"
              f"{f['delta_L']:>6.1f}{f['delta_e_deuteranopia']:>7.1f}"
              f"{f['delta_e_protanopia']:>7.1f} {flags or ' ok'}")
    print(f"\nfailing pairs: {len(failing)} (high-contact: {len(major_failing)})")
    for f in failing:
        print(f"  {f['pair']}: dE00 {f['delta_e2000']}, deut {f['delta_e_deuteranopia']}, "
              f"prot {f['delta_e_protanopia']}, border {f['shared_border_px']:,} px")


if __name__ == "__main__":
    main()
