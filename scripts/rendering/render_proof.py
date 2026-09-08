"""Render the plain 2D scientific soil-QA proof (no hillshade/DEM/AI/3D).

Deterministic: colours come from config/soil_palette.yaml; the legend is built
ONLY from classes present in data/processed/tables/soil_groups_iran.csv.

Output: outputs/proof/iran_soils_proof_v01.png
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import yaml  # noqa: E402
import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RSG_TIF = ROOT / "data/processed/soils/iran_dominant_soil_group.tif"
CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
PALETTE = ROOT / "config/soil_palette.yaml"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
AREA_QA = ROOT / "provenance/metadata/area_qa.json"
OUT = ROOT / "outputs/proof/iran_soils_proof_v01.png"


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def main() -> None:
    for p in (RSG_TIF, CSV, PALETTE, BOUNDARY):
        if not p.exists():
            raise SystemExit(f"Proof blocked; missing required input: {p}")

    colours = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    # present classes only, ordered by area desc (CSV already is)
    present = [(r["classification_code"], r["soil_group"], int(r["wrb2_project_int"]),
                float(r["share_percent"]), r["is_soil"] == "True") for r in rows]

    with rasterio.open(RSG_TIF) as src:
        arr = src.read(1)
        t = src.transform
        left, top = t.c, t.f
        right = left + t.a * src.width
        bottom = top + t.e * src.height

    rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
    for code, _name, pint, _share, _issoil in present:
        if code not in colours:
            raise SystemExit(f"Palette missing colour for present class {code}")
        r, g, b = hex_to_rgb(colours[code])
        m = arr == pint
        rgba[m] = (r, g, b, 255)

    boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:4326")
    mean_lat = (top + bottom) / 2.0
    aspect = 1.0 / math.cos(math.radians(mean_lat))

    fig = plt.figure(figsize=(12, 11), dpi=200)
    ax = fig.add_axes([0.04, 0.10, 0.66, 0.82])
    ax.imshow(rgba, extent=[left, right, bottom, top], origin="upper", interpolation="nearest")
    # Draw boundary rings directly (geopandas .plot() aborts on this GEOS/Windows build; D-009).
    geom = boundary.geometry.iloc[0]
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color="#222222", linewidth=0.6)
        for ring in poly.interiors:
            xi, yi = ring.xy
            ax.plot(xi, yi, color="#222222", linewidth=0.4)
    ax.set_aspect(aspect)
    ax.set_xlim(left, right); ax.set_ylim(bottom, top)
    ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)")
    ax.tick_params(labelsize=8)
    ax.set_title("Iran — Dominant Soil Group (HWSD v2.01, WRB 2022)\nScientific data proof v01 — not a publication map",
                 fontsize=13, loc="left")

    # legend (present classes, share %)
    def fmt(share: float) -> str:
        return "<0.1%" if 0 < share < 0.05 else f"{share:.1f}%"
    handles = [Patch(facecolor=colours[c], edgecolor="#555555",
                     label=f"{name} ({c}) — {fmt(share)}" + ("" if issoil else "  [non-soil]"))
               for c, name, _pint, share, issoil in present]
    leg_ax = fig.add_axes([0.71, 0.10, 0.28, 0.82]); leg_ax.axis("off")
    leg_ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=False,
                  title="Dominant WRB-2022 Reference Soil Group\n(share of classified area)",
                  title_fontsize=9, handlelength=1.2, labelspacing=0.7)

    qa = json.loads(AREA_QA.read_text(encoding="utf-8")) if AREA_QA.exists() else {}
    note = (
        "Source: FAO & IIASA, Harmonized World Soil Database v2.01 (Rome & Laxenburg; report DOI 10.4060/cc3823en), "
        "CC BY-NC-SA 4.0. Boundary: Made with Natural Earth (Admin-0, 1:10m, v5.1.1).\n"
        "Method: dominant soil component per SMU = HWSD2_LAYERS SEQUENCE=1; class = WRB2 Reference Soil Group. "
        "Native soil support ~1 km (30 arc-second) — categorical, nearest-neighbour only; no interpolation.\n"
        "Display CRS: EPSG:4326 (geographic). Area statistics CRS: custom Lambert Azimuthal Equal Area (lat_0=32, lon_0=53). "
        f"Classified soil area ≈ {qa.get('C_classified_soil_area_km2', 'n/a'):,} km²; boundary area ≈ "
        f"{qa.get('A_boundary_area_laea_km2', 'n/a'):,} km². "
        "This is a data-QA proof; terrain resolution does NOT increase soil resolution."
    )
    fig.text(0.04, 0.015, note, fontsize=7.2, va="bottom", ha="left", color="#333333")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor="white")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes); classes drawn: {len(present)}")


if __name__ == "__main__":
    main()
