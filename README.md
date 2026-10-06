# Iran Soil Landscapes

**Status:** SRTMGL3_ACQUIRED / DEM_PROCESSED — HWSD v2.01 + Natural Earth were acquired, verified, and processed into a dominant WRB-2022 soil-group map of Iran. SRTMGL3 acquisition is complete for all **198/198 required tiles**, and the DEM was processed successfully. Earthdata authentication is no longer an active blocker. Terrain is used only as topographic context.

Iran Soil Landscapes is a reproducible geospatial-cartography project for mapping **dominant soil groups in Iran according to the Harmonized World Soil Database (HWSD) v2.01 schema**. The repository records source acquisition, transformations, quality controls, and cartographic specifications. Soil classification comes from HWSD; SRTM terrain is visual context only.

[Methods and sources](docs/METHODS.md) · [Area accounting and QA](provenance/metadata/area_qa.json) · [Reproducibility checks](docs/QA_PLAN.md)

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

The current dominant-soil result and area accounting are recorded in [area_qa.json](provenance/metadata/area_qa.json): **Leptosols 40.7 %**, **Regosols 18.7 %**, **Solonchaks 18.6 %**, and **Calcisols 16.8 %** of classified soil area. Rendered proof maps and poster files are regenerable but gitignored under [publication.yaml](config/publication.yaml), so the current GitHub branch has no map image to preview. SRTMGL3 adds topographic context only: it creates no soil observations, does not increase HWSD’s native spatial resolution or thematic accuracy, and is not field validation or ground truth.

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

`config/` project settings; `docs/` project records; `data/raw/` immutable downloads; `data/interim/` working products; `data/processed/` documented derived products; `scripts/` reproducible pipeline code; `tests/` invariant checks; `provenance/` manifests and checksums; `outputs/` regenerable rendered products (gitignored); `qgis/` inspection project; `blender/` scripted terrain rendering.

## Publication outputs

The configured v1.1 publication pair defines a 6000 × 7500 px archival master and a 2160 × 2700 px (4:5) feed sheet, composed over one hash-locked scientific render. The [publication QA record](provenance/metadata/final_publication_qa.json) reports its checks; rendered files are regenerable and gitignored, so they are not viewable from the current repository. Cartographic production does not establish field validation or reduce uncertainty inherited from HWSD.

The current pair is **v1.1**, declared in [config/publication.yaml](config/publication.yaml). v1.1 changed composition only — typography, grid, legend hierarchy, map furniture and label placement — over a render frozen by hash at `provenance/checksums/scientific_render_frozen_2026-09-12.txt`; see [docs/CARTOGRAPHIC_FURNITURE_V1_1.md](docs/CARTOGRAPHIC_FURNITURE_V1_1.md), which also records the national keyline and the palette adjustment that were built, measured and rejected. v1.0 is superseded rather than deleted and stays reproducible from its own layout keys.

## Citation

See [CITATION.cff](CITATION.cff). Source citations and required attributions remain mandatory in every downstream map and publication.
