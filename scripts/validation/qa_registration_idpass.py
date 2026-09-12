"""UNSHADED_CLASS_ID_PASS — geometric/UV registration, measured without any lighting.

The shaded reclassification score reported earlier is a CARTOGRAPHIC READABILITY figure:
it answers "can a reader still tell which class this pixel is after shading?". It is not
a registration measurement, because lighting, shadow and tone all enter it. Conflating the
two would let a geometric fault hide inside a lighting statistic.

This pass removes every optical variable. The terrain is rendered with a pure emission
material carrying a class-ID texture, one sample, box pixel filter, no denoising, no sun,
no ambient. A rendered pixel is then the class code itself, and it is decoded back to the
source categorical raster through the camera's own geometry:

    render pixel -> world coordinate (ortho camera) -> grid cell -> source class id

Reported:
  A. GEOMETRIC / UV REGISTRATION  exact class agreement, plus a +/-3 px offset search.
     If the best offset is not (0,0), a transform is wrong and the gate must stop.
  B. ENCODING FIDELITY            how far rendered levels drift from the exact codes.

    python scripts/validation/qa_registration_idpass.py
"""
from __future__ import annotations

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
CFG = ROOT / "config/render_3d.yaml"
BLENDER_DIR = ROOT / "data/processed/render/blender"
RENDER_PNG = ROOT / "outputs/proof/3d/iran_class_id_pass.png"
OUT = ROOT / "provenance/metadata/registration_idpass_qa.json"
SEARCH = 3


def main() -> None:
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    meta = json.loads((BLENDER_DIR / "blender_inputs.json").read_text(encoding="utf-8"))
    levels = json.loads((BLENDER_DIR / "class_id_levels.json").read_text(encoding="utf-8"))
    step = int(levels["step"])
    level_to_id = {int(v): int(k) for k, v in levels["level_by_project_int"].items()}

    src = np.asarray(Image.open(BLENDER_DIR / "iran_class_id_texture.png").convert("L"))
    gh, gw = src.shape
    rgba = np.asarray(Image.open(RENDER_PNG).convert("RGBA"))
    rendered, alpha = rgba[..., 0].astype(np.int16), rgba[..., 3]
    ry, rx = rendered.shape

    cam = cfg["cameras"]["idpass"]
    ext_x, ext_y = meta["extent_km"]["x"], meta["extent_km"]["y"]
    ortho = float(cam["ortho_margin"]) * ext_x          # sensor_fit HORIZONTAL
    ortho_v = ortho * ry / rx

    # Render pixel centres -> world -> source grid cell (the camera's own geometry, not an
    # assumed identity mapping: the vertical fit differs from the grid by a fraction of a px).
    xs = -ortho / 2.0 + (np.arange(rx) + 0.5) * (ortho / rx)
    ys = ortho_v / 2.0 - (np.arange(ry) + 0.5) * (ortho_v / ry)
    cols = np.clip(np.rint((xs + ext_x / 2.0) / (ext_x / gw) - 0.5), 0, gw - 1).astype(np.int32)
    rows = np.clip(np.rint((ext_y / 2.0 - ys) / (ext_y / gh) - 0.5), 0, gh - 1).astype(np.int32)

    # Decode: nearest legal level, then to a project class id.
    decoded = np.rint(rendered.astype(np.float64) / step).astype(np.int16) * step
    max_level_error = int(np.abs(rendered - decoded)[alpha > 0].max()) if (alpha > 0).any() else 0

    inside = np.zeros_like(decoded, dtype=bool)
    expected = src[np.ix_(rows, cols)]
    valid = (expected > 0) & (alpha > 0)
    inside |= valid

    def agreement(dy: int, dx: int) -> float:
        r = np.clip(rows + dy, 0, gh - 1)
        c = np.clip(cols + dx, 0, gw - 1)
        exp = src[np.ix_(r, c)]
        m = valid & (exp > 0)
        return float((decoded[m] == exp[m]).mean())

    scores = {(dy, dx): agreement(dy, dx)
              for dy in range(-SEARCH, SEARCH + 1) for dx in range(-SEARCH, SEARCH + 1)}
    best = max(scores, key=scores.get)
    zero = scores[(0, 0)]

    # Interior-only figure: class-boundary cells disagree for sampling reasons even when
    # the transform is perfect, so report them separately rather than blaming registration.
    interior = valid.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        interior &= (np.roll(np.roll(expected, dy, 0), dx, 1) == expected)
    interior_agreement = float((decoded[interior] == expected[interior]).mean())

    payload = {
        "render": RENDER_PNG.name,
        "method": "unlit emission of a class-ID texture; 1 sample, BOX filter width 0.01, "
                  "no denoise, no sun, no ambient — no optical variable can affect class identity",
        "render_size": [int(rx), int(ry)],
        "grid_size": [int(gw), int(gh)],
        "A_geometric_registration": {
            "pixels_compared": int(valid.sum()),
            "exact_class_agreement": round(zero, 6),
            "interior_class_agreement": round(interior_agreement, 6),
            "interior_pixels": int(interior.sum()),
            "best_offset_dy_dx": [int(best[0]), int(best[1])],
            "best_offset_agreement": round(scores[best], 6),
            "zero_offset_is_best": best == (0, 0),
            "offset_scores": {f"{dy},{dx}": round(v, 6) for (dy, dx), v in sorted(scores.items())},
        },
        "B_encoding_fidelity": {
            "level_step": step,
            "max_level_error": max_level_error,
            "decode_margin": step // 2,
            "roundtrip_exact": max_level_error <= step // 2,
        },
        "classes_recovered": int(len(set(np.unique(decoded[valid]).tolist()) & set(level_to_id))),
        "classes_expected": len(level_to_id),
    }
    OUT.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")

    a = payload["A_geometric_registration"]
    print(f"A. GEOMETRIC/UV REGISTRATION over {a['pixels_compared']:,} px")
    print(f"   exact agreement          {a['exact_class_agreement']:.4%}")
    print(f"   interior (non-boundary)  {a['interior_class_agreement']:.4%} "
          f"over {a['interior_pixels']:,} px")
    print(f"   best offset              dy={best[0]} dx={best[1]} "
          f"({scores[best]:.4%}) -> {'NO OFFSET' if best == (0, 0) else 'OFFSET PRESENT'}")
    print(f"B. ENCODING FIDELITY: max level error {max_level_error} "
          f"(decode margin +/-{step // 2}) -> {'exact' if payload['B_encoding_fidelity']['roundtrip_exact'] else 'DEGRADED'}")
    print(f"   classes recovered {payload['classes_recovered']}/{payload['classes_expected']}")


if __name__ == "__main__":
    main()
