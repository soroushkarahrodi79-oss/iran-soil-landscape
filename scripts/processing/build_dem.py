"""Build the processed Iran DEM from verified SRTMGL3 tiles (low-storage VRT path).

RAW zips -> /vsizip/ .hgt -> VRT mosaic -> reproject to locked LAEA (D-003) ->
clip to frozen iran_boundary.gpkg -> data/processed/dem/iran_dem_90m.tif.
Real elevation only (no vertical exaggeration). Bilinear (continuous data).

Outputs:
  data/processed/dem/iran_dem_90m.tif
  provenance/metadata/terrain_processing_record.json
  provenance/metadata/dem_qa.json
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

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "provenance/manifests/srtm_tiles_iran.csv"
RAW = ROOT / "data/raw/srtm"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
OUT = ROOT / "data/processed/dem/iran_dem_90m.tif"
VRT = ROOT / "data/interim/iran_srtm.vrt"
REC = ROOT / "provenance/metadata/terrain_processing_record.json"
QA = ROOT / "provenance/metadata/dem_qa.json"
LAEA = "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs"
NODATA = -32768


def main() -> None:
    rows = [r for r in csv.DictReader(MANIFEST.open(encoding="utf-8"))
            if r["status"] == "DOWNLOADED_VERIFIED"]
    if not rows:
        raise SystemExit("No DOWNLOADED_VERIFIED tiles in manifest; run acquire_srtm.py first.")
    vsi = []
    for r in rows:
        z = RAW / f"{r['tile_id']}.SRTMGL3.hgt.zip"
        if not z.exists():
            raise SystemExit(f"Missing verified zip: {z}")
        vsi.append(f"/vsizip/{z.as_posix()}/{r['tile_id']}.hgt")
    print(f"tiles: {len(vsi)}")

    if OUT.exists() and gdal.Open(str(OUT)) is not None:
        print(f"DEM already exists ({OUT.name}); skipping warp, recomputing QA.")
    else:
        VRT.parent.mkdir(parents=True, exist_ok=True)
        gdal.BuildVRT(str(VRT), vsi, VRTNodata=NODATA)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        gdal.Warp(
            str(OUT), str(VRT),
            dstSRS=LAEA, xRes=90.0, yRes=90.0, resampleAlg="bilinear",
            cutlineDSName=str(BOUNDARY), cutlineLayer="iran_boundary", cropToCutline=True,
            srcNodata=NODATA, dstNodata=NODATA, outputType=gdal.GDT_Int16,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "BIGTIFF=IF_SAFER"],
            multithread=True,
        )
        VRT.unlink(missing_ok=True)

    ds = gdal.Open(str(OUT))
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    gt = ds.GetGeoTransform()
    mn, mx, mean, std = band.GetStatistics(False, True)  # GDAL: respects nodata, no huge array
    # Memory-safe counts + approximate median via row-block reads.
    valid_count = nodata_count = below0 = 0
    hist = np.zeros(1024, dtype=np.int64)
    lo, hi = int(mn), int(mx)
    span = max(hi - lo, 1)
    for y in range(ds.RasterYSize):
        row = band.ReadAsArray(0, y, ds.RasterXSize, 1)[0]
        m = row != NODATA
        v = row[m]
        valid_count += int(v.size)
        nodata_count += int(row.size - v.size)
        below0 += int((v < 0).sum())
        if v.size:
            idx = np.clip(((v.astype(np.int64) - lo) * 1023 // span), 0, 1023)
            hist += np.bincount(idx, minlength=1024)
    cum = np.cumsum(hist)
    med_bucket = int(np.searchsorted(cum, valid_count / 2))
    approx_median = lo + (med_bucket + 0.5) * span / 1024.0
    qa = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dimensions": [ds.RasterYSize, ds.RasterXSize],
        "pixel_size_m": [gt[1], -gt[5]],
        "crs": ds.GetProjection()[:80] + "...",
        "nodata": NODATA,
        "valid_pixels": valid_count,
        "nodata_pixels": nodata_count,
        "nodata_share_pct": round(100 * nodata_count / (valid_count + nodata_count), 3),
        "elev_min_m": float(mn),
        "elev_max_m": float(mx),
        "elev_mean_m": round(float(mean), 2),
        "elev_std_m": round(float(std), 2),
        "elev_median_m_approx": round(float(approx_median), 1),
        "below_sea_level_pixels": below0,
        "note": "Elevation in metres, vertical datum EGM96. NoData outside the frozen Iran "
                "boundary (cropToCutline) and any residual source voids; SRTMGL3 v003 is void-filled "
                "so interior source voids are ~0. Below-sea-level pixels are Caspian-margin/water noise. "
                "Median is histogram-approximate (memory-safe). Real elevation; no exaggeration.",
    }
    QA.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    REC.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "product": "SRTMGL3.003", "tiles_used": len(vsi),
        "source_crs": "EPSG:4326 (SRTM tiles)", "target_crs_proj4": LAEA,
        "resample": "bilinear", "clip": "iran_boundary.gpkg cropToCutline",
        "output": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "output_nodata": NODATA, "vertical_datum": "EGM96", "units": "metres",
        "vertical_exaggeration": "none (scientific DEM)",
    }, indent=2) + "\n", encoding="utf-8")
    ds = None
    print(json.dumps(qa, indent=2))
    # VRT is a tiny regenerable pointer; remove to keep interim clean.
    VRT.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
