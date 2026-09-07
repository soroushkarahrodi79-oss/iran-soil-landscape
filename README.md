# Iran Soil Landscapes

**Status:** FOUNDATION_IN_PROGRESS — source contracts verified; no soil or DEM data have yet been processed.

Iran Soil Landscapes is a reproducible geospatial-cartography project to produce a terrain-enhanced depiction of **dominant soil groups in Iran according to the Harmonized World Soil Database (HWSD) v2.01 schema**. The intended publication is a professional LinkedIn and portfolio work. This repository is the source of record for source acquisition, transformations, quality controls, and cartographic outputs.

## Scientific objective

The eventual map will communicate HWSD's dominant component classification at its native 30 arc-second (~1 km) support. It will not claim a field-validated national soil survey, site-scale soil truth, or 30 m soil information. Higher-resolution terrain is a visual context layer only; it does not increase the soil dataset's spatial resolution.

Every geographic claim must follow: **source data → scripted processing → derived dataset → cartographic representation**. Raw inputs are immutable, are not committed by default, and are tracked with acquisition metadata and SHA-256 checksums.

## Source status

| Dataset | Role | Status |
| --- | --- | --- |
| FAO/IIASA HWSD v2.01 | Primary soil mapping units and component database | SOURCE_VERIFIED / DOWNLOAD_PENDING |
| Natural Earth Admin 0 Countries 1:10m v5.1.1 | National boundary | SOURCE_VERIFIED / DOWNLOAD_PENDING |
| USGS/NASA SRTMGL1 | Terrain source | SOURCE_VERIFIED / BLOCKED_USER_ACTION (EarthExplorer/Earthdata access) |

The exact URLs, licenses, dates, and open questions are in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) and `provenance/manifests/source_manifest.csv`.

## Workflow

1. Acquire only the authoritative archives, then checksum and register them.
2. Extract and validate the Natural Earth `ADM0_A3 = IRN` feature without hand-editing it.
3. Inspect the downloaded HWSD database schema and record the exact selected classification fields.
4. Derive a dominant component/Reference Soil Group raster with nearest-neighbour categorical operations only.
5. Account for boundary, raster-covered, classified, and nodata area before rendering a plain 2D proof.
6. Use the proof for data QA. Blender production is explicitly out of scope until `GO_3D_CARTOGRAPHY`.

## Reproducibility

Create the environment from `environment.yml`, then run the numbered scripts in `scripts/`. Scripts intentionally fail closed when an expected source, schema field, or invariant is missing. See [docs/METHODS.md](docs/METHODS.md) and [docs/QA_PLAN.md](docs/QA_PLAN.md).

## Layout

`config/` project settings; `docs/` project records; `data/raw/` immutable downloads; `data/interim/` working products; `data/processed/` documented derived products; `scripts/` reproducible pipeline code; `tests/` invariant checks; `provenance/` manifests and checksums; `outputs/proof/` plain scientific QA map; `qgis/` inspection project; `blender/` reserved for later.

## Publication target

The future archival master is planned at a minimum of approximately 6000 × 7500 px, with a controlled 2160 × 2700 px (4:5) LinkedIn derivative. No final publication asset is produced in this foundation phase.

## Citation

See [CITATION.cff](CITATION.cff). Source citations and required attributions remain mandatory in every downstream map and publication.
