"""Prepare the numeric inputs Blender consumes for the 3D prototype.

Blender's bundled Python has no GDAL/rasterio, so the georeferenced work stays here
and Blender receives only plain arrays/images that are already on the frozen LAEA
render grid. Nothing georeferenced is re-projected, so registration stays exact.

Inputs  (data/processed/render/, built by build_render_substrate.py):
  iran_heightmap_prototype.tif   Int16 real elevation, LAEA render grid
  iran_soil_texture.png          RGBA soil colours (alpha=0 outside Iran)
  iran_water_mask.png            0/255 cartographic water

Outputs (data/processed/render/blender/):
  elev_mesh.npy          float32 metres at mesh resolution (NaN = DEM nodata)
  iran_render_basecolor.png  RGB display composite: soil inside Iran, neutral grey
                             outside, cartographic water over both
  blender_inputs.json    mesh/grid geometry + provenance for the Blender script

The basecolor composite is a DISPLAY product only: it is built from the frozen soil
ids already rendered in iran_soil_texture.png, and no soil class is created, merged
or moved by it.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from osgeo import gdal  # noqa: E402
from PIL import Image  # noqa: E402

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config/render_3d.yaml"
RENDER = ROOT / "data/processed/render"
HEIGHT = RENDER / "iran_heightmap_prototype.tif"
SOIL_TEX = RENDER / "iran_soil_texture.png"
WATER = RENDER / "iran_water_mask.png"
SUBSTRATE_META = ROOT / "provenance/metadata/render_substrate.json"
OUT = RENDER / "blender"
DEM_NODATA = -32768


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def main() -> None:
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    sub = json.loads(SUBSTRATE_META.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    # --- elevation at mesh resolution (bilinear; real metres, nodata preserved) ---
    src = gdal.Open(str(HEIGHT))
    gw, gh = src.RasterXSize, src.RasterYSize
    gt = src.GetGeoTransform()
    long_px = int(cfg["mesh"]["long_px"])
    scale = long_px / max(gw, gh)
    mw, mh = int(round(gw * scale)), int(round(gh * scale))
    mem = gdal.Warp("", src, format="MEM", width=mw, height=mh, resampleAlg="bilinear",
                    srcNodata=DEM_NODATA, dstNodata=DEM_NODATA, outputType=gdal.GDT_Float32)
    elev = mem.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nodata_px = int((elev == DEM_NODATA).sum())
    elev[elev == DEM_NODATA] = np.nan
    np.save(OUT / "elev_mesh.npy", elev)
    zmin, zmax = float(np.nanmin(elev)), float(np.nanmax(elev))

    # --- display basecolor composite on the full render grid (no resampling) ---
    soil = np.asarray(Image.open(SOIL_TEX).convert("RGBA"))
    water = np.asarray(Image.open(WATER).convert("L"))
    if soil.shape[:2] != water.shape[:2]:
        raise SystemExit(f"substrate grids disagree: soil {soil.shape[:2]} vs water {water.shape[:2]}")
    base = np.empty((*soil.shape[:2], 3), dtype=np.uint8)
    base[:] = hex_to_rgb(cfg["surface"]["context_land_srgb"])
    iran = soil[..., 3] > 0
    base[iran] = soil[iran, :3]
    wet = water >= int(cfg["surface"]["water_threshold"])
    base[wet] = hex_to_rgb(cfg["surface"]["cartographic_water_srgb"])
    Image.fromarray(base, "RGB").save(OUT / "iran_render_basecolor.png")

    # --- geometry the Blender script needs (kilometres; LAEA metres / 1000) ---
    bounds_m = sub["render_grid"]["bounds_laea"]
    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "render_grid": {"width": gw, "height": gh, "pixel_size_m": [gt[1], -gt[5]]},
        "mesh": {"width": mw, "height": mh, "verts": mw * mh,
                 "posting_m": [gt[1] * gw / mw, -gt[5] * gh / mh],
                 "nodata_px": nodata_px},
        "extent_km": {"x": (bounds_m[2] - bounds_m[0]) / 1000.0,
                      "y": (bounds_m[3] - bounds_m[1]) / 1000.0},
        "elevation_m": {"min": zmin, "max": zmax},
        "unit": "km (1 Blender unit = 1 km); z from real metres / 1000",
        "source_dem_sha_ref": "provenance/checksums/dem_frozen_2026-09-09.txt",
        "note": "Mesh is a decimation of the frozen render heightmap; basecolor is a display "
                "composite of the frozen soil texture + Natural Earth water. No soil class "
                "is created or altered.",
    }
    (OUT / "blender_inputs.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"mesh {mw}x{mh} ({mw * mh:,} verts), posting ~{gt[1] * gw / mw:.0f} m, "
          f"elev {zmin:.0f}..{zmax:.0f} m, DEM nodata px {nodata_px:,}")
    print(f"basecolor {base.shape[1]}x{base.shape[0]}; Iran px {int(iran.sum()):,}; water px {int(wet.sum()):,}")


if __name__ == "__main__":
    main()
