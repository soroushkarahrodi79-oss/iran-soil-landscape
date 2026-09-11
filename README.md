# Iran Soil Landscapes

**Status:** SRTMGL3_ACQUIRED / DEM_PROCESSED — HWSD v2.01 + Natural Earth were acquired, verified, and processed into a dominant WRB-2022 soil-group map of Iran. SRTMGL3 acquisition is complete for all **198/198 required tiles**, and the DEM was processed successfully. Earthdata authentication is no longer an active blocker. Terrain is used only as topographic context.

Iran Soil Landscapes is a reproducible geospatial-cartography project to produce a terrain-enhanced depiction of **dominant soil groups in Iran according to the Harmonized World Soil Database (HWSD) v2.01 schema**. The intended publication is a professional LinkedIn and portfolio work. This repository is the source of record for source acquisition, transformations, quality controls, and cartographic outputs.

## Scientific objective

The eventual map will communicate HWSD's dominant component classification at its native 30 arc-second (~1 km) support. It will not claim a field-validated national soil survey, site-scale soil truth, or 30 m soil information. Higher-resolution terrain is a visual context layer only; it does not increase the soil dataset's spatial resolution.

Every geographic claim must follow: **source data → scripted processing → derived dataset → cartographic representation**. Raw inputs are immutable, are not committed by default, and are tracked with acquisition metadata and SHA-256 checksums.

## Source status

| Dataset | Role | Status |
| --- | --- | --- |
| FAO/IIASA HWSD v2.01 | Primary soil mapping units and component database | DOWNLOADED_VERIFIED / SCHEMA_LOCKED / PROCESSED |
| Natural Earth Admin 0 Countries 1:10m v5.1.1 | National boundary | DOWNLOADED_VERIFIED / PROCESSED |
| USGS/NASA SRTMGL3 v003 | Topographic context | 198/198 TILES DOWNLOADED_VERIFIED / DEM PROCESSED |

The exact URLs, licenses, dates, and open questions are in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) and `provenance/manifests/source_manifest.csv`. SRTM tile status and checksums are in `provenance/manifests/srtm_tiles_iran.csv` and `provenance/checksums/srtm_sha256.txt`; its acquisition and processing records are `provenance/metadata/srtm_acquisition_record.json` and `provenance/metadata/terrain_processing_record.json`.

## Current result

Dominant WRB-2022 Reference Soil Group of Iran from HWSD v2.01 (rule: `SEQUENCE=1` component per SMU; see [docs/HWSD_SCHEMA.md](docs/HWSD_SCHEMA.md)). Leading classes by area: **Leptosols 40.7 %**, **Regosols 18.7 %**, **Solonchaks 18.6 %**, **Calcisols 16.8 %**. Boundary area 1,622,510 km² (Natural Earth 1:10m), classified soil area 1,612,385 km²; full accounting in `provenance/metadata/area_qa.json`. The plain soil-data proof is `outputs/proof/iran_soils_proof_v01.png`; generated terrain-context outputs include `outputs/proof/iran_dem_hillshade_qa_v01.png` and the poster files under `outputs/proof/poster/`. The SRTMGL3 DEM and its derivatives add topographic context only: they create no soil observations, do not increase HWSD's native spatial resolution or thematic accuracy, and are not field validation or ground truth.

## Workflow

1. Acquire only the authoritative archives, then checksum and register them.
2. Extract and validate the Natural Earth `ADM0_A3 = IRN` feature without hand-editing it.
3. Inspect the downloaded HWSD database schema and record the exact selected classification fields.
4. Derive a dominant component/Reference Soil Group raster with nearest-neighbour categorical operations only.
5. Account for boundary, raster-covered, classified, and nodata area before rendering a plain 2D proof.
6. Acquire and verify all required SRTMGL3 tiles, then build the DEM and terrain-context derivatives without altering the soil classification.

## Reproducibility

Create the environment from `environment-geospatial.yml` (Miniforge/conda-forge, Python 3.12, env `iran-soil-geospatial`):

```
conda env create -f environment-geospatial.yml
```

Then run the numbered pipeline with that environment's interpreter (scripts import `scripts/_geoenv.py`, which points PROJ/GDAL and native DLLs at the env so runs are reproducible without manual activation):

1. `scripts/acquisition/inspect_hwsd_schema.py` — read HWSD2.mdb structure (GDAL/OGR ODBC)
2. `scripts/processing/preprocess_boundary.py` — extract Iran + CRS QA
3. `scripts/processing/derive_hwsd_iran.py` — dominant WRB soil group + area QA + tables
4. `scripts/rendering/render_proof.py` — 2D data proof
5. `scripts/acquisition/acquire_srtm.py` — acquire and verify the 198 required SRTMGL3 tiles
6. `scripts/processing/build_dem.py` — mosaic, reproject, and clip the terrain DEM

Scripts intentionally fail closed when an expected source, schema field, or invariant is missing. See [docs/METHODS.md](docs/METHODS.md) and [docs/QA_PLAN.md](docs/QA_PLAN.md).

## Layout

`config/` project settings; `docs/` project records; `data/raw/` immutable downloads; `data/interim/` working products; `data/processed/` documented derived products; `scripts/` reproducible pipeline code; `tests/` invariant checks; `provenance/` manifests and checksums; `outputs/proof/` scientific and terrain-context QA/cartographic outputs; `qgis/` inspection project; `blender/` scripted terrain rendering.

## Publication outputs

The workflow has generated a 6000 × 7500 px archival master and a controlled 2160 × 2700 px (4:5) LinkedIn derivative. Their completion is a cartographic production result, not evidence that the HWSD soil classes are field-validated or that terrain resolves uncertainty inherited from HWSD.

## Citation

See [CITATION.cff](CITATION.cff). Source citations and required attributions remain mandatory in every downstream map and publication.
