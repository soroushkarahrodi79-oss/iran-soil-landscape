# Iran Soil Landscapes

**Status:** DATA_GATE_COMPLETE — HWSD v2.01 + Natural Earth acquired, verified, and processed into a dominant WRB-2022 soil-group map of Iran with area QA and a 2D data proof. Terrain (SRTM) remains pending user-authenticated acquisition. Not yet a publication map.

Iran Soil Landscapes is a reproducible geospatial-cartography project to produce a terrain-enhanced depiction of **dominant soil groups in Iran according to the Harmonized World Soil Database (HWSD) v2.01 schema**. The intended publication is a professional LinkedIn and portfolio work. This repository is the source of record for source acquisition, transformations, quality controls, and cartographic outputs.

## Scientific objective

The eventual map will communicate HWSD's dominant component classification at its native 30 arc-second (~1 km) support. It will not claim a field-validated national soil survey, site-scale soil truth, or 30 m soil information. Higher-resolution terrain is a visual context layer only; it does not increase the soil dataset's spatial resolution.

Every geographic claim must follow: **source data → scripted processing → derived dataset → cartographic representation**. Raw inputs are immutable, are not committed by default, and are tracked with acquisition metadata and SHA-256 checksums.

## Source status

| Dataset | Role | Status |
| --- | --- | --- |
| FAO/IIASA HWSD v2.01 | Primary soil mapping units and component database | DOWNLOADED_VERIFIED / SCHEMA_LOCKED / PROCESSED |
| Natural Earth Admin 0 Countries 1:10m v5.1.1 | National boundary | DOWNLOADED_VERIFIED / PROCESSED |
| USGS/NASA SRTMGL1 | Terrain source | SOURCE_VERIFIED / BLOCKED_USER_ACTION (EarthExplorer/Earthdata access) |

The exact URLs, licenses, dates, and open questions are in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) and `provenance/manifests/source_manifest.csv`. Raw SHA-256 checksums are in `provenance/checksums/raw_sha256.txt`; the acquisition record is `provenance/metadata/acquisition_2026-09-08.json`.

## Current result (data proof, not publication)

Dominant WRB-2022 Reference Soil Group of Iran from HWSD v2.01 (rule: `SEQUENCE=1` component per SMU; see [docs/HWSD_SCHEMA.md](docs/HWSD_SCHEMA.md)). Leading classes by area: **Leptosols 40.7 %**, **Regosols 18.7 %**, **Solonchaks 18.6 %**, **Calcisols 16.8 %**. Boundary area 1,622,510 km² (Natural Earth 1:10m), classified soil area 1,612,385 km²; full accounting in `provenance/metadata/area_qa.json`. Proof: `outputs/proof/iran_soils_proof_v01.png` (2D, no terrain/AI). Reproduce with `scripts/` in the numbered pipeline order.

## Workflow

1. Acquire only the authoritative archives, then checksum and register them.
2. Extract and validate the Natural Earth `ADM0_A3 = IRN` feature without hand-editing it.
3. Inspect the downloaded HWSD database schema and record the exact selected classification fields.
4. Derive a dominant component/Reference Soil Group raster with nearest-neighbour categorical operations only.
5. Account for boundary, raster-covered, classified, and nodata area before rendering a plain 2D proof.
6. Use the proof for data QA. Blender production is explicitly out of scope until `GO_3D_CARTOGRAPHY`.

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

Scripts intentionally fail closed when an expected source, schema field, or invariant is missing. See [docs/METHODS.md](docs/METHODS.md) and [docs/QA_PLAN.md](docs/QA_PLAN.md).

## Layout

`config/` project settings; `docs/` project records; `data/raw/` immutable downloads; `data/interim/` working products; `data/processed/` documented derived products; `scripts/` reproducible pipeline code; `tests/` invariant checks; `provenance/` manifests and checksums; `outputs/proof/` plain scientific QA map; `qgis/` inspection project; `blender/` reserved for later.

## Publication target

The future archival master is planned at a minimum of approximately 6000 × 7500 px, with a controlled 2160 × 2700 px (4:5) LinkedIn derivative. No final publication asset is produced in this foundation phase.

## Citation

See [CITATION.cff](CITATION.cff). Source citations and required attributions remain mandatory in every downstream map and publication.
