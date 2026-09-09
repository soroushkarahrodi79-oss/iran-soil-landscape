"""Plain terrain QA diagnostic: hillshade + hypsometric tint of the Iran DEM.

For VALIDATION ONLY (is Alborz/Zagros/etc. plausible?) — not a publication render.
No terrain is modified. Hillshade shading exaggeration is a lighting effect for
visibility only; elevation values are unchanged and real.

Output: outputs/proof/iran_dem_hillshade_qa_v01.png
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
import geopandas as gpd  # noqa: E402

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parents[2]
DEM = ROOT / "data/processed/dem/iran_dem_90m.tif"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
OUT = ROOT / "outputs/proof/iran_dem_hillshade_qa_v01.png"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"
NODATA = -32768


def main() -> None:
    if not DEM.exists():
        raise SystemExit(f"DEM missing: {DEM} (run build_dem.py)")
    ds = gdal.Open(str(DEM))
    full_w, full_h = ds.RasterXSize, ds.RasterYSize
    # Decimate on read (this is a national QA image, not the master render) to keep memory small.
    bw = 2200
    bh = max(1, int(round(full_h * bw / full_w)))
    arr = ds.GetRasterBand(1).ReadAsArray(buf_xsize=bw, buf_ysize=bh).astype(np.float64)
    gt = ds.GetGeoTransform()
    left, top = gt[0], gt[3]
    right = left + gt[1] * full_w
    bottom = top + gt[5] * full_h
    px = gt[1] * full_w / bw  # decimated pixel size (m)
    masked = np.ma.masked_equal(arr, NODATA)
    zmin, zmax = float(masked.min()), float(masked.max())

    ls = LightSource(azdeg=315, altdeg=45)
    dem = np.where(masked.mask, zmin, arr)
    rgba = ls.shade(dem, cmap=plt.cm.terrain, blend_mode="soft",
                    vert_exag=5.0, dx=px, dy=px, vmin=zmin, vmax=zmax)  # (M,N,4) RGBA
    rgba[..., 3] = (~masked.mask).astype(float)  # transparent outside Iran

    fig = plt.figure(figsize=(12, 10), dpi=200)
    ax = fig.add_axes([0.05, 0.08, 0.9, 0.86])
    ax.imshow(rgba, extent=[left, right, bottom, top], origin="upper", interpolation="nearest")

    b = gpd.read_file(BOUNDARY).to_crs(LAEA)
    geom = b.geometry.iloc[0]
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color="#222222", linewidth=0.5)

    import json
    qa_path = ROOT / "provenance/metadata/dem_qa.json"
    if qa_path.exists():
        q = json.loads(qa_path.read_text(encoding="utf-8"))
        tmin, tmax = int(q["elev_min_m"]), int(q["elev_max_m"])
    else:
        tmin, tmax = int(zmin), int(zmax)
    ax.set_aspect("equal")
    ax.set_xlim(left, right); ax.set_ylim(bottom, top)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Iran — SRTMGL3 (~90 m) terrain QA diagnostic (hillshade + hypsometric tint)\n"
                 f"elevation {tmin}–{tmax} m (EGM96) — validation only, not a publication render",
                 fontsize=12, loc="left")
    fig.text(0.05, 0.02,
             "Source: NASA/USGS SRTMGL3 v003 (public domain). Display CRS: custom LAEA (lat_0=32, lon_0=53). "
             "Hillshade lighting is a visibility effect; elevation values are real and unmodified. "
             "QA target features: Alborz, Zagros, Iranian Plateau, Kerman highlands, Makran, Khuzestan lowland, central basins.",
             fontsize=7, va="bottom", color="#333333")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor="white")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
