"""Build the deterministic render substrate for the 3D prototype (no Blender).

All layers are produced on ONE common LAEA render grid so they are aligned by
construction (registration is exact, not eyeballed):
  A. RENDER_HEIGHTMAP  <- data/processed/dem/iran_dem_90m.tif  (downsample, bilinear)
  B. SOIL TEXTURE      <- data/processed/soils/iran_dominant_soil_group.tif (nearest)
  D. CARTOGRAPHIC WATER<- Natural Earth ne_10m_ocean + ne_10m_lakes (rasterized)
The scientific DEM and soil rasters are NOT modified; only render-only derivatives
are written under data/processed/render/.

Outputs (data/processed/render/):
  iran_heightmap_prototype.tif   Int16 real elevation on the render grid (nodata -32768)
  iran_heightmap_prototype_u16.png  normalized 0..65535 displacement map for Blender
  iran_soil_ids_render.tif       UInt8 dominant-RSG project id on the render grid (0=outside)
  iran_soil_texture.png          RGBA soil colours (alpha=0 outside Iran)
  iran_water_mask.png            UInt8 0/255 cartographic water within the render extent
  provenance/metadata/render_substrate.json
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
from osgeo import gdal  # noqa: E402
import rasterio  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
import geopandas as gpd  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parents[2]
DEM = ROOT / "data/processed/dem/iran_dem_90m.tif"
SOIL = ROOT / "data/processed/soils/iran_dominant_soil_group.tif"
CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
PALETTE = ROOT / "config/soil_palette.yaml"
OCEAN = ROOT / "data/raw/natural_earth/ne_10m_ocean.zip"
LAKES = ROOT / "data/raw/natural_earth/ne_10m_lakes.zip"
OUT = ROOT / "data/processed/render"
META = ROOT / "provenance/metadata/render_substrate.json"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"
DEM_NODATA = -32768
TARGET_LONG_PX = 4096


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    src = gdal.Open(str(DEM))
    W, H = src.RasterXSize, src.RasterYSize
    long_px = TARGET_LONG_PX
    scale = long_px / max(W, H)
    tw, th = int(round(W * scale)), int(round(H * scale))

    # A. Heightmap: downsample real elevation (bilinear), keep nodata.
    hm_tif = OUT / "iran_heightmap_prototype.tif"
    gdal.Warp(str(hm_tif), str(DEM), width=tw, height=th, resampleAlg="bilinear",
              srcNodata=DEM_NODATA, dstNodata=DEM_NODATA, outputType=gdal.GDT_Int16,
              creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=2"])
    hds = gdal.Open(str(hm_tif))
    gt = hds.GetGeoTransform()
    hm = hds.GetRasterBand(1).ReadAsArray()
    valid = hm != DEM_NODATA
    zmin, zmax = int(hm[valid].min()), int(hm[valid].max())
    # normalized u16 displacement (nodata -> 0 = lowest)
    norm = np.zeros_like(hm, dtype=np.uint16)
    norm[valid] = np.clip(((hm[valid] - zmin) / max(zmax - zmin, 1) * 65535), 0, 65535).astype(np.uint16)
    Image.fromarray(norm, mode="I;16").save(OUT / "iran_heightmap_prototype_u16.png")

    # target-grid geotransform / bounds for the other layers
    outb = [gt[0], gt[3] + gt[5] * th, gt[0] + gt[1] * tw, gt[3]]  # minx,miny,maxx,maxy

    # B. Soil ids resampled (NEAREST) onto the identical grid.
    soil_tif = OUT / "iran_soil_ids_render.tif"
    gdal.Warp(str(soil_tif), str(SOIL), dstSRS=LAEA, outputBounds=outb,
              width=tw, height=th, resampleAlg="near",
              srcNodata=0, dstNodata=0, outputType=gdal.GDT_Byte,
              creationOptions=["COMPRESS=DEFLATE"])
    sds = gdal.Open(str(soil_tif))
    sids = sds.GetRasterBand(1).ReadAsArray()
    sds = None

    # colourise soil ids via palette + csv (id->code)
    colours = yaml.safe_load(PALETTE.read_text(encoding="utf-8"))["wrb2_rsg_colours"]
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    id_to_code = {int(r["wrb2_project_int"]): r["classification_code"] for r in rows}
    rgba = np.zeros((th, tw, 4), dtype=np.uint8)
    for pid, code in id_to_code.items():
        h = colours[code].lstrip("#")
        m = sids == pid
        rgba[m] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    Image.fromarray(rgba, "RGBA").save(OUT / "iran_soil_texture.png")

    # D. Water mask: NE ocean + lakes -> LAEA -> rasterize onto the render grid.
    transform = rasterio.transform.from_bounds(outb[0], outb[1], outb[2], outb[3], tw, th)
    from shapely.geometry import box as _box  # noqa: E402
    bbox4326 = _box(42.0, 22.0, 66.0, 42.0)  # local clip avoids global-polygon LAEA distortion
    geoms = []
    for z in (OCEAN, LAKES):
        g = gpd.read_file(f"zip://{z}")
        g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
        g["geometry"] = g.geometry.intersection(bbox4326)
        g = g[~g.geometry.is_empty].to_crs(LAEA)
        geoms += [gg for gg in g.geometry if gg is not None and not gg.is_empty]
    water = rasterize([(gg, 255) for gg in geoms], out_shape=(th, tw),
                      transform=transform, fill=0, dtype="uint8")
    Image.fromarray(water, "L").save(OUT / "iran_water_mask.png")

    META.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "render_grid": {"crs": "LAEA lat0=32 lon0=53", "width": tw, "height": th,
                        "pixel_size_m": [gt[1], -gt[5]], "bounds_laea": outb},
        "source_dem": "data/processed/dem/iran_dem_90m.tif",
        "dem_downsample": {"from": [H, W], "to": [th, tw], "method": "bilinear", "long_px": long_px},
        "heightmap_normalization": {"elev_min_m": zmin, "elev_max_m": zmax,
                                    "u16": "0=elev_min .. 65535=elev_max; nodata->0"},
        "soil_resample": "nearest (categorical); ids from data/processed/soils/iran_dominant_soil_group.tif",
        "soil_classes_present": len(id_to_code),
        "water_source": "ne_10m_ocean + ne_10m_lakes (rasterized in LAEA); NOT merged into HWSD",
        "note": "Render-only derivatives. Scientific soil/DEM rasters untouched. All layers share "
                "one LAEA grid so registration is exact by construction.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"render grid {tw}x{th}; elev {zmin}..{zmax} m; soil classes {len(id_to_code)}; water px {int((water>0).sum())}")
    print("wrote:", *[p.name for p in sorted(OUT.glob('*'))])


if __name__ == "__main__":
    main()
