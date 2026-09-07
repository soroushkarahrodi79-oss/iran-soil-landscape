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

## Explicit unresolved issues

1. The workspace has no installed Python or geospatial runtime. `environment.yml` is the reproducible solution, but has not been created locally.
2. No official HWSD or Natural Earth archive is present, so their generated SHA-256 values and all downstream products are intentionally absent.
3. HWSD's actual MDB table/field names have not been inspected; `config/hwsd_schema.yaml` remains an explicit null-valued stop gate.
4. The official SRTM download route requires a user-authenticated EarthExplorer/Earthdata action. No credential bypass or substitute source is permitted.

## Required next gate

Run the reproducible environment setup and acquire/inspect the two non-authenticated primary archives. Review the data-derived HWSD schema record, explicitly accept the mapping fields, then execute the soil derivation and area QA. Only if those gates pass may the first 2D proof be rendered. Do not begin Blender without explicit `GO_3D_CARTOGRAPHY`.
