"""2D registration QA + terrain-enhanced proof (no Blender).

Because the heightmap, soil texture and water mask share ONE LAEA grid, draping
the soil colours over the DEM hillshade and overlaying water is an exact
registration check: soil classes must sit on the correct landforms and water on
the correct basins. Labelled control regions aid the check.

Output: outputs/proof/3d/registration_qa_v01.png
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LightSource  # noqa: E402
import numpy as np  # noqa: E402
from osgeo import gdal  # noqa: E402
from PIL import Image  # noqa: E402
import geopandas as gpd  # noqa: E402
from pyproj import Transformer  # noqa: E402

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "data/processed/render"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
OUT = ROOT / "outputs/proof/3d/registration_qa_v01.png"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"
NODATA = -32768
CONTROL = {  # lon, lat
    "Caspian Sea": (51.0, 37.8), "Lake Urmia": (45.5, 37.6), "Khuzestan": (48.7, 31.3),
    "Dasht-e Kavir": (54.5, 34.6), "Lut Desert": (58.6, 30.9), "Makran": (61.0, 26.2),
    "Persian Gulf": (52.5, 27.6), "Alborz": (52.0, 36.1), "Zagros": (49.8, 32.2),
}


def main() -> None:
    hds = gdal.Open(str(R / "iran_heightmap_prototype.tif"))
    gt = hds.GetGeoTransform()
    hm = hds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    th, tw = hm.shape
    left, top = gt[0], gt[3]
    right, bottom = left + gt[1] * tw, top + gt[5] * th
    valid = hm != NODATA
    zmin = float(hm[valid].min())
    dem = np.where(valid, hm, zmin)

    ls = LightSource(azdeg=315, altdeg=45)
    inten = ls.hillshade(dem, vert_exag=4.0, dx=gt[1], dy=-gt[5])  # 0..1

    soil = np.array(Image.open(R / "iran_soil_texture.png"))  # RGBA
    water = np.array(Image.open(R / "iran_water_mask.png"))    # L
    land = soil[..., 3] > 0

    comp = np.ones((th, tw, 3), dtype=np.float64)  # white bg
    shaded = soil[..., :3].astype(np.float64) / 255.0 * (0.35 + 0.65 * inten[..., None])
    comp[land] = shaded[land]
    water_only = (water > 0) & (~land)
    wcol = np.array([0.42, 0.55, 0.68])
    comp[water_only] = wcol * (0.6 + 0.4 * inten[water_only, None])

    fig = plt.figure(figsize=(13, 12), dpi=200)
    ax = fig.add_axes([0.03, 0.06, 0.94, 0.88])
    ax.imshow(np.clip(comp, 0, 1), extent=[left, right, bottom, top], origin="upper", interpolation="nearest")

    b = gpd.read_file(BOUNDARY).to_crs(LAEA)
    geom = b.geometry.iloc[0]
    for poly in (list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]):
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color="#111111", linewidth=0.6)

    tf = Transformer.from_crs("EPSG:4326", LAEA, always_xy=True)
    for name, (lon, lat) in CONTROL.items():
        x, y = tf.transform(lon, lat)
        ax.plot(x, y, "o", ms=4, mfc="white", mec="black", mew=0.8)
        ax.annotate(name, (x, y), fontsize=8, ha="left", va="center",
                    xytext=(6, 0), textcoords="offset points",
                    color="#111", path_effects=None,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))

    ax.set_aspect("equal"); ax.set_xlim(left, right); ax.set_ylim(bottom, top)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Iran — registration QA / terrain-enhanced proof (2D)\n"
                 "dominant WRB-2022 soil group draped on SRTMGL3 hillshade + Natural Earth water — "
                 "prototype substrate, NOT a publication render",
                 fontsize=12, loc="left")
    fig.text(0.03, 0.02,
             "All layers on one LAEA grid (registration exact by construction). Soil = HWSD v2.01 (frozen). "
             "Terrain = SRTMGL3 ~90m (hillshade lighting only). Water = Natural Earth 10m (cartographic, not merged into HWSD). "
             "QA: Solonchaks should fill the low Kavir/Lut basins; Leptosols the Zagros/Alborz ridges; water match Caspian/Gulf/Urmia.",
             fontsize=7, va="bottom", color="#333")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor="white")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
