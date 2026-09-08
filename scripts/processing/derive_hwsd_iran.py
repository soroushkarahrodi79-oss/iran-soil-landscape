"""Derive Iran dominant WRB-2022 Reference Soil Group from HWSD2 (SCHEMA_LOCKED gate).

Requires config/hwsd_schema.yaml status == SCHEMA_LOCKED. Refuses otherwise.

Pipeline (categorical => NEAREST only; the raster window is read at native
resolution with no resampling):
  1. Read SMU -> dominant WRB2 (RSG code) from HWSD2_SMU; RSG names from D_WRB2.
  2. Window-read the HWSD2.bil over Iran's bbox (native 30 arc-sec, EPSG:4326).
  3. Mask to the Iran polygon (rasterized at the window transform).
  4. Emit the clipped SMU-id raster and the dominant-RSG raster.
  5. Area accounting with latitude-correct WGS84 pixel areas (no reprojection
     of categorical data); classified vs nodata vs non-soil (water/glacier/etc).

Outputs:
  data/processed/soils/iran_hwsd_mapping_units.tif    (Int32 SMU ids, 0=outside/nodata)
  data/processed/soils/iran_dominant_soil_group.tif   (UInt8 project RSG code, 0=nodata)
  data/processed/tables/soil_groups_iran.csv
  provenance/metadata/area_qa.json
"""
from __future__ import annotations

import csv
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import yaml  # noqa: E402
from osgeo import ogr  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.windows import Window  # noqa: E402
import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config/hwsd_schema.yaml"
MDB = ROOT / "data/interim/hwsd/HWSD2.mdb"
RASTER_ZIP = ROOT / "data/raw/hwsd/HWSD2_RASTER.zip"
BIL = ROOT / "data/interim/hwsd/HWSD2.bil"
BOUNDARY = ROOT / "data/processed/boundary/iran_boundary.gpkg"
OUT_SMU = ROOT / "data/processed/soils/iran_hwsd_mapping_units.tif"
OUT_RSG = ROOT / "data/processed/soils/iran_dominant_soil_group.tif"
OUT_CSV = ROOT / "data/processed/tables/soil_groups_iran.csv"
AREA_QA = ROOT / "provenance/metadata/area_qa.json"

RASTER_NODATA = 65535
NON_SOIL_CODES = {"GG": "Glaciers", "IS": "Islands", "ND": "No Data", "WR": "Open Water"}
WGS84_A = 6378137.0
WGS84_E2 = 0.00669437999014


def require_locked() -> dict:
    c = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["schema_contract"]
    if c.get("status") != "SCHEMA_LOCKED":
        raise SystemExit(f"HWSD schema not locked (status={c.get('status')}). Refusing to derive.")
    return c


def ensure_bil() -> None:
    if BIL.exists():
        return
    BIL.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RASTER_ZIP) as z:
        for m in ("HWSD2.bil", "HWSD2.hdr", "HWSD2.prj", "HWSD2.stx"):
            z.extract(m, BIL.parent)


def read_lookups() -> tuple[dict[int, str], dict[str, str], dict[str, int]]:
    """Dominant WRB2 per SMU from HWSD2_LAYERS (SEQUENCE=1, LAYER='D1'); uppercased."""
    ds = ogr.GetDriverByName("ODBC").Open(str(MDB), 0)
    smu_to_wrb2: dict[int, str] = {}
    sql = "SELECT HWSD2_SMU_ID, WRB2 FROM HWSD2_LAYERS WHERE LAYER = 'D1' AND SEQUENCE = 1"
    res = ds.ExecuteSQL(sql)
    for f in res:
        sid = f.GetField("HWSD2_SMU_ID")
        wrb2 = (f.GetField("WRB2") or "").strip().upper()  # normalize NT/Nt, GL/Gl, PT/Pt ...
        if sid is not None:
            smu_to_wrb2[int(sid)] = wrb2
    ds.ReleaseResultSet(res)
    code_to_name: dict[str, str] = {}
    lyr = ds.GetLayerByName("D_WRB2")
    for f in lyr:
        code_to_name[(f.GetField("CODE") or "").strip().upper()] = (f.GetField("Value") or "").strip()
    codes_sorted = sorted(code_to_name)
    code_to_int = {c: i + 1 for i, c in enumerate(codes_sorted)}  # deterministic 1..N
    ds = None
    return smu_to_wrb2, code_to_name, code_to_int


def wgs84_row_pixel_area_km2(lat_top: float, dlat: float, dlon: float) -> float:
    """Ellipsoidal area of one cell whose north edge is lat_top (deg), spanning dlat/dlon (deg)."""
    lat1 = np.radians(lat_top - dlat)
    lat2 = np.radians(lat_top)
    e = np.sqrt(WGS84_E2)
    def q(phi):
        s = np.sin(phi)
        return s / (1 - WGS84_E2 * s * s) + (1 / (2 * e)) * np.log((1 + e * s) / (1 - e * s))
    area_zone = np.pi * WGS84_A**2 * (1 - WGS84_E2) * (q(lat2) - q(lat1))  # full 360deg lon band
    return float(area_zone * (dlon / 360.0) / 1e6)


def main() -> None:
    require_locked()
    ensure_bil()
    smu_to_wrb2, code_to_name, code_to_int = read_lookups()

    boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:4326")
    minx, miny, maxx, maxy = map(float, boundary.total_bounds)

    with rasterio.open(BIL) as src:
        # Manual window from the inverse transform (rasterio.from_bounds aborts on
        # this GDAL/Windows build; see DECISIONS D-009).
        inv = ~src.transform
        cmin, rmin = inv * (minx, maxy)   # top-left
        cmax, rmax = inv * (maxx, miny)   # bottom-right
        col_off, row_off = int(np.floor(cmin)), int(np.floor(rmin))
        width = int(np.ceil(cmax)) - col_off
        height = int(np.ceil(rmax)) - row_off
        win = Window(col_off, row_off, width, height)
        smu = src.read(1, window=win).astype(np.int64)
        wtrans = src.window_transform(win)
        dlon = src.transform.a
        dlat = -src.transform.e

    mask = rasterize([(geom, 1) for geom in boundary.geometry], out_shape=smu.shape,
                     transform=wtrans, fill=0, dtype="uint8").astype(bool)

    inside = mask & (smu != RASTER_NODATA)
    # Vectorized SMU -> WRB2 -> project int via a lookup array (fast).
    uniq = np.unique(smu[inside]).tolist()
    maxid = max(uniq) if uniq else 0
    lut = np.zeros(maxid + 1, dtype=np.uint8)
    unmapped_smus = []
    for sid in uniq:
        wrb2 = smu_to_wrb2.get(int(sid), "")
        pint = code_to_int.get(wrb2, 0)
        lut[sid] = pint
        if pint == 0:
            unmapped_smus.append(int(sid))
    smu_safe = np.where(inside, smu, 0).astype(np.int64)
    smu_safe[smu_safe > maxid] = 0
    smu_int = lut[smu_safe]
    smu_int[~inside] = 0

    # latitude-correct pixel areas per row
    nrows = smu.shape[0]
    row_lat_top = np.array([wtrans.f + wtrans.e * r for r in range(nrows)])
    row_area = np.array([wgs84_row_pixel_area_km2(lt, dlat, dlon) for lt in row_lat_top])
    area_grid = np.repeat(row_area[:, None], smu.shape[1], axis=1)

    # accounting
    poly_pixels = mask
    A_boundary_laea = float(boundary.to_crs(
        "+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs").geometry.area.sum() / 1e6)
    B_supported = float(area_grid[inside].sum())
    nodata_in_poly = poly_pixels & (smu == RASTER_NODATA)
    D_nodata = float(area_grid[nodata_in_poly].sum())
    unmapped_mask = inside & (smu_int == 0)
    F_unmapped = float(area_grid[unmapped_mask].sum())

    # per-RSG stats
    rows = []
    soil_area = 0.0
    nonsoil_area = 0.0
    for code in sorted(code_to_name):
        pint = code_to_int[code]
        sel = inside & (smu_int == pint)
        # also count SMUs whose WRB2==code that resolved to 0 (shouldn't happen for known codes)
        a = float(area_grid[sel].sum())
        if a <= 0:
            continue
        mu_count = int(np.unique(smu[sel]).size)
        is_nonsoil = code in NON_SOIL_CODES
        if is_nonsoil:
            nonsoil_area += a
        else:
            soil_area += a
        rows.append({
            "soil_group": code_to_name[code],
            "classification_code": code,
            "wrb2_project_int": pint,
            "is_soil": (not is_nonsoil),
            "area_km2": round(a, 3),
            "mapping_unit_count": mu_count,
        })
    total_class_area = soil_area + nonsoil_area
    for r in rows:
        r["share_percent"] = round(100.0 * r["area_km2"] / total_class_area, 4) if total_class_area else None
        r["source_classification"] = "WRB 2022 Reference Soil Group (HWSD2 WRB2), dominant component per SMU"
        r["notes"] = "non-soil/special class" if not r["is_soil"] else ""

    rows.sort(key=lambda x: (-x["area_km2"]))

    # write CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "soil_group", "classification_code", "wrb2_project_int", "is_soil",
            "area_km2", "share_percent", "mapping_unit_count", "source_classification", "notes"])
        w.writeheader()
        w.writerows(rows)

    # write rasters
    OUT_SMU.parent.mkdir(parents=True, exist_ok=True)
    smu_out = np.where(inside, smu, 0).astype(np.int32)
    prof = {"driver": "GTiff", "height": smu.shape[0], "width": smu.shape[1], "count": 1,
            "dtype": "int32", "crs": "EPSG:4326", "transform": wtrans, "nodata": 0,
            "compress": "deflate"}
    with rasterio.open(OUT_SMU, "w", **prof) as dst:
        dst.write(smu_out, 1)
    prof8 = dict(prof); prof8.update(dtype="uint8", nodata=0)
    with rasterio.open(OUT_RSG, "w", **prof8) as dst:
        dst.write(smu_int, 1)
        dst.write_colormap(1, {0: (0, 0, 0, 0)})

    qa = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "window_shape": [int(smu.shape[0]), int(smu.shape[1])],
        "native_cell_deg": [dlon, dlat],
        "A_boundary_area_laea_km2": round(A_boundary_laea, 1),
        "B_hwsd_supported_area_km2": round(B_supported, 1),
        "C_classified_soil_area_km2": round(soil_area, 1),
        "E_nonsoil_special_area_km2": round(nonsoil_area, 1),
        "F_unmapped_smu_area_km2": round(F_unmapped, 1),
        "unmapped_smu_ids": unmapped_smus,
        "D_raster_nodata_within_polygon_km2": round(D_nodata, 1),
        "reconciliation_B_minus_C_E_F": round(B_supported - (soil_area + nonsoil_area + F_unmapped), 3),
        "A_minus_B_km2": round(A_boundary_laea - B_supported, 1),
        "A_minus_B_pct": round(100 * (A_boundary_laea - B_supported) / A_boundary_laea, 4),
        "note": "A from LAEA polygon; B/C/D/E from latitude-correct WGS84 pixel areas on the native grid (no categorical resampling). A-B reflects coastline/border mismatch between the NE 1:10m vector and the HWSD land mask plus boundary rasterization.",
    }
    AREA_QA.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print("Wrote", OUT_SMU.name, OUT_RSG.name, OUT_CSV.name)
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
