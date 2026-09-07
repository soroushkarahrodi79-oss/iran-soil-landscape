# Foundation status — 2026-09-07

| Exit criterion | Status | Evidence / reason |
| --- | --- | --- |
| Coherent repository structure | READY | Directories, ignore rules, environment specification, provenance folders, and scripts are present. |
| Populated documentation | READY | README and all required records are populated. |
| Verified source manifest | SOURCE_VERIFIED | Source identity/URLs, versions, access date, licences, and attribution recorded; no raw checksum yet. |
| Raw-file provenance/checksums | PENDING_DOWNLOAD | Scripts generate checksums; no file has been downloaded or represented as present. |
| Processed Iran boundary | PENDING_DOWNLOAD | Script is ready but will not fabricate a boundary without the official archive. |
| HWSD schema interpretation | PENDING_SCHEMA_REVIEW | Report-driven schema contract exists but deliberately contains no guessed fields. |
| Dominant-soil raster/statistics/area QA | PROCESSING_NOT_STARTED | Blocked by official HWSD files and accepted schema contract. |
| Plain 2D proof | PROOF_PENDING | Blocked by the absence of derived soil data and actual data-derived palette. |
| DEM | BLOCKED_USER_ACTION | SRTM requires the user's official EarthExplorer/Earthdata acquisition path. |
| QGIS/Blender production | NOT_STARTED | Out of scope for this foundation phase. |

## Second verification pass — 2026-09-07 (this session)

Source identity was independently re-verified against the FAO **primary catalog** ISO record `ff5c613c` (data.apps.fao.org), the ISRIC mirror, the Natural Earth 10m cultural download page, and USGS/NASA SRTM documentation. This pass **corrected three records** that had been asserted from a weaker/second-hand source (see DECISIONS D-007):

- HWSD licence: `CC BY-NC-SA 3.0 IGO` → **`CC BY-NC-SA 4.0`** (manifest, LICENSES.md, CITATION.cff, DATA_SOURCES.md).
- HWSD raster format: `ESRI BIL` → **GeoTIFF, UInt16, nodata 65535, 43,200 × 21,600** (manifest, DATA_SOURCES.md).
- Removed an unverified `29,385 mapping units / up to 12 components` figure pending direct measurement.

Natural Earth v5.1.1 (1:10m, public domain) and the SRTMGL1 authenticated-access requirement were re-confirmed unchanged.

## Explicit unresolved issues

1. **No geospatial runtime for the current user.** `py` reports Python 3.14.5, but there is no `python` on PATH, no conda/miniforge, and none of GDAL, geopandas, rasterio, pyproj, or **mdbtools** (required by `inspect_hwsd_schema.py`) is installed. The prior `__pycache__` (cpython-312) came from a different Windows account's sandbox that this user cannot access. `environment.yml` is the reproducible solution but has not been built locally, and note that geospatial binary wheels may not yet exist for Python 3.14 — a 3.11/3.12 conda env is the safer target.
2. No official HWSD or Natural Earth archive is present, so their generated SHA-256 values and all downstream products are intentionally absent. Downloads require the user's explicit go-ahead.
3. HWSD's actual MDB table/field names have not been inspected; `config/hwsd_schema.yaml` remains an explicit null-valued stop gate.
4. The official SRTM download route requires a user-authenticated EarthExplorer/Earthdata action. No credential bypass or substitute source is permitted.

## Required next gate

Run the reproducible environment setup and acquire/inspect the two non-authenticated primary archives. Review the data-derived HWSD schema record, explicitly accept the mapping fields, then execute the soil derivation and area QA. Only if those gates pass may the first 2D proof be rendered. Do not begin Blender without explicit `GO_3D_CARTOGRAPHY`.
