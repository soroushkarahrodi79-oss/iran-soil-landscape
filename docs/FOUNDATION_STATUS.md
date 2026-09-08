# Project status — updated 2026-09-08 (DATA_GATE_COMPLETE)

| Exit criterion | Status | Evidence / reason |
| --- | --- | --- |
| Coherent repository structure | DONE | Directories, ignore rules, `environment-geospatial.yml`, provenance folders, scripts. |
| Populated documentation | DONE | README + all records populated and updated to the executed pipeline. |
| Verified source manifest | DONE | Identity/URLs/versions/licences/attribution; downloaded rows carry SHA-256 and byte sizes. |
| Reproducible environment | DONE | Miniforge conda env `iran-soil-geospatial`, Python 3.12 (GDAL 3.13.3, rasterio 1.5.1, geopandas 1.1.4, pyproj 3.8.0). |
| Raw-file provenance/checksums | DONE | `provenance/checksums/raw_sha256.txt` (verifies OK) + `acquisition_2026-09-08.json`. |
| Processed Iran boundary | DONE | `data/processed/boundary/iran_boundary.gpkg` (EPSG:4326, unaltered); CRS QA in metadata. |
| HWSD schema interpretation | SCHEMA_LOCKED | Read from `HWSD2.mdb` (ODBC); `config/hwsd_schema.yaml` + `docs/HWSD_SCHEMA.md`; DECISIONS D-008. |
| Dominant-soil raster + statistics | DONE | `iran_hwsd_mapping_units.tif`, `iran_dominant_soil_group.tif`, `soil_groups_iran.csv` (16 classes). |
| Area QA | DONE | `area_qa.json`; B = C+E+F exactly; A−B = 0.081 % explained by nodata. |
| Plain 2D proof | DONE | `outputs/proof/iran_soils_proof_v01.png` (2D categorical, no terrain/AI). |
| Automated tests | DONE (10 passed) | Provenance guards + scientific invariants (shares≈100 %, reconciliation, palette coverage). |
| DEM / SRTM | BLOCKED_USER_ACTION | Requires the user's authenticated EarthExplorer/Earthdata download. |
| QGIS / Blender production | NOT_STARTED | Out of scope until `GO_3D_CARTOGRAPHY`. |

## Verification/correction trail

- **2026-09-07 (metadata pass):** re-verified source identity against the FAO primary catalog `ff5c613c`; corrected licence `3.0 IGO`→`4.0` for the dataset and (over-)corrected raster format to GeoTIFF.
- **2026-09-08 (artifact pass):** downloading and inspecting the artifacts **reverted the format to ESRI BIL** (confirmed by `HWSD2.hdr` and the report, which recommends converting BIL→GeoTIFF — explaining the catalog's GeoTIFF). Also clarified the licence nuance: the **report PDF** is CC BY-NC-SA 3.0 IGO (its own copyright page); the **dataset** is 4.0. See DECISIONS D-007.

## Key results

- Dominant WRB-2022 RSG of Iran: Leptosols 40.7 %, Regosols 18.7 %, Solonchaks 18.6 %, Calcisols 16.8 % (12 more classes; 0 unmapped SMUs).
- Boundary area 1,622,510 km²; classified soil area 1,612,385 km²; non-soil (water) 8,817 km²; nodata-in-polygon 1,334 km².

## Remaining blockers / next gate

1. **SRTMGL1 terrain** requires the user's authenticated EarthExplorer/Earthdata download (no bypass, no mirror). Everything else for terrain is ready.
2. Optional polish before publication: QGIS inspection project, palette refinement, and the master/LinkedIn render specs — all deferred until `GO_3D_CARTOGRAPHY`.
