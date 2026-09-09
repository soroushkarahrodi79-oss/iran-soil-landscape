"""Assemble labelled comparison sheets from the 3D prototype renders.

The gate's tests are comparisons, not single images: the exaggeration, camera and
lighting choices are only defensible side by side under identical conditions. Each
sheet varies exactly ONE parameter; everything else is held fixed by the job that
produced the frames.

    python scripts/rendering/build_prototype_sheets.py --selected-exaggeration 2

Renders carry alpha (film_transparent); sheets composite them over white so the
comparison is not confounded by a background choice.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/proof/3d"


def load(name: str) -> Image.Image:
    path = OUT / f"{name}.png"
    if not path.exists():
        raise SystemExit(f"missing render: {path}")
    img = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat.alpha_composite(img)
    return flat.convert("RGB")


def sheet(names: list[str], titles: list[str], cols: int, out_name: str,
          suptitle: str, subtitle: str) -> Path:
    imgs = [load(n) for n in names]
    rows = (len(imgs) + cols - 1) // cols
    w, h = imgs[0].size
    fig_w = 13.0
    fig_h = fig_w / cols * (h / w) * rows + 1.0
    fig, axes = plt.subplots(rows, cols, figsize=(fig_w, fig_h), facecolor="white")
    axes = [axes] if rows * cols == 1 else list(axes.ravel())
    for ax, img, title in zip(axes, imgs, titles):
        ax.imshow(img)
        ax.set_title(title, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor("#999999")
    for ax in axes[len(imgs):]:
        ax.axis("off")
    fig.suptitle(suptitle, fontsize=15, y=0.995)
    fig.text(0.5, 0.008, subtitle, ha="center", fontsize=9, color="#444444")
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    path = OUT / out_name
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    print(f"wrote {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected-exaggeration", type=int, default=2)
    ap.add_argument("--skip-lighting", action="store_true")
    args = ap.parse_args()
    k = args.selected_exaggeration
    fixed = "Identical data, camera and lighting in every panel; only the stated parameter varies."

    for cam, label in (("topdown", "orthographic top-down"), ("oblique", "orthographic oblique, 55° tilt, viewed from the south")):
        sheet([f"iran_3d_{e}x_{cam}" for e in (1, 2, 3, 4)],
              [f"{e}× vertical exaggeration" for e in (1, 2, 3, 4)], 2,
              f"exaggeration_test_{cam}.png",
              f"Vertical exaggeration test — {label}",
              f"Iran, HWSD2 dominant WRB soil groups on SRTMGL3 terrain. {fixed}")

    sheet([f"iran_3d_{k}x_topdown", f"iran_3d_{k}x_oblique"],
          ["Top-down (planimetric, true map scale)",
           "Oblique 55° (foreshortened, scale varies with depth)"], 2,
          "camera_test.png", f"Camera test — both at {k}× vertical exaggeration",
          f"Both orthographic: no perspective convergence. {fixed}")

    if not args.skip_lighting:
        sheet([f"iran_3d_light_{v}_{k}x_topdown" for v in ("low", "default", "high")],
              ["Sun 22° elevation (long shadows)", "Sun 40° elevation",
               "Sun 58° elevation (flat, low contrast)"], 3,
              "lighting_test.png", f"Lighting test — top-down, {k}× exaggeration, sun from the NW (315°)",
              f"NW illumination throughout: light from the upper left avoids relief inversion. {fixed}")


if __name__ == "__main__":
    main()
