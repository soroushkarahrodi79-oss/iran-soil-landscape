# Reproducible processing method

## Operating rule

Critical transformations are scripted. QGIS may inspect the results and develop a layout only after the same products exist from scripts. Raw data are immutable: no script writes into `data/raw/`, and every downloaded archive is SHA-256 hashed before a processing run.

## Environment

Miniforge/conda-forge, Python 3.12, env `iran-soil-geospatial` (`environment-geospatial.yml`). Every script first imports `scripts/_geoenv.py`, which points PROJ/GDAL data and native DLLs at the active env — required on Windows because a system `PROJ_LIB`/`libpng` otherwise breaks CRS lookups and matplotlib PNG writes (see DECISIONS D-009). Run scripts with the env's interpreter.

## Executed pipeline (2026-09-08)

```text
# acquisition: official artifacts fetched with curl into immutable data/raw/ (see acquisition_2026-09-08.json)
python scripts/acquisition/inspect_hwsd_schema.py     # HWSD2.mdb structure via GDAL/OGR ODBC
python scripts/processing/preprocess_boundary.py      # extract Iran, CRS QA
python scripts/processing/derive_hwsd_iran.py         # dominant WRB soil group, area QA, tables
python scripts/rendering/render_proof.py              # 2D data proof
pytest -q
```

`derive_hwsd_iran.py` and `render_proof.py` are fail-closed until the schema is `SCHEMA_LOCKED` and their inputs exist. SRTM is not part of this chain until the user downloads tiles through an official authenticated route.

## Boundary

1. Keep the official Natural Earth ZIP under `data/raw/natural_earth/`.
2. Record its SHA-256 in `provenance/checksums/` and its actual file name/path in the manifest.
3. Read the original `ne_10m_admin_0_countries` layer in source CRS, select exactly `ADM0_A3 == "IRN"`, and require exactly one non-empty feature.
4. Reject invalid geometry rather than repairing or hand-editing it. Write the canonical boundary **in the source CRS (EPSG:4326), geometry unaltered**, to `data/processed/boundary/iran_boundary.gpkg`. The LAEA is used only as a separate area-QA comparison, not for the stored geometry.
5. Write a metadata JSON record containing source CRS, LAEA WKT/PROJ, source feature count, selection criterion (confirmed `ADM0_A3 == "IRN"`, cross-checked against 6 other selectors), geodesic and equal-area areas, bounding box, multipart count, and validity outcome.

## Soils

1. Acquire only the FAO-linked `HWSD2_RASTER.zip` and `HWSD2_DB.zip` archives; store unmodified copies under `data/raw/hwsd/`.
2. `inspect_hwsd_schema.py` exports a data-derived schema report (`hwsd_mdb_report.json`) via GDAL/OGR ODBC. It identified the join field (`HWSD2_SMU_ID`), tables (`HWSD2_LAYERS`, `HWSD2_SMU`), `SEQUENCE`, `SHARE`, `WRB2`, `FAO90`, and the `D_WRB2` lookup, and found **no ISSOIL field**. It does not guess column names. Contract locked in `config/hwsd_schema.yaml` (`SCHEMA_LOCKED`).
3. `derive_hwsd_iran.py` requires `SCHEMA_LOCKED`. The dominant per SMU = the **`SEQUENCE=1`** component in `HWSD2_LAYERS` (`LAYER='D1'`); class = its `WRB2` (uppercased) resolved via `D_WRB2`. Non-soil WRB2 codes (`GG`,`IS`,`ND`,`WR`) are reported separately. SMUs with no `SEQUENCE=1`/empty WRB2 are left unmapped and counted as anomalies (0 in Iran), never guessed.
4. The Iran window is read at **native resolution with no resampling** (categorical): `iran_hwsd_mapping_units.tif` preserves SMU IDs; `iran_dominant_soil_group.tif` holds the deterministic integer RSG code. No bilinear/cubic on class IDs. Transform, window, nodata, and CRS (EPSG:4326) are recorded.
5. `soil_groups_iran.csv` reports each present class's WRB group, code, project int, is_soil flag, area km² (latitude-correct WGS84 pixel areas), share %, mapping-unit count, source classification, and notes.

No categorical class is interpolated, generalized, painted, or inferred from a visual reference. No USDA orders are mixed with FAO/WRB Reference Soil Groups.

## Area accounting

For the accepted common analysis grid, report all of the following in `area_qa.json`: boundary area, raster-covered area, classified area, nodata area, and residual. A discrepancy greater than 0.5% of boundary area requires a documented explanation before proof rendering. The report must distinguish coastline/source-geometry differences, pixel inclusion, projection, and nodata from unexplained error.

## DEM (deferred)

Once the user has acquired SRTMGL1 tiles through EarthExplorer/Earthdata:

1. Preserve each tile unchanged in `data/raw/srtm/` and hash it.
2. Mosaic, reproject to the accepted analysis CRS with bilinear resampling, clip to the derived Iran boundary, and record input tiles, original WGS84/EGM96 reference, nodata/void policy, transform, dimensions, and valid elevation range.
3. Write `data/processed/dem/iran_dem_30m.tif`. Its name refers to native SRTM sampling, not a promise of every post-warp pixel dimension or soil resolution.

## Proof rendering

The first proof is a deliberately plain 2D QA image: extracted boundary, derived classes only, deterministic palette, simple legend/title, source note, and CRS note. No terrain shading, texture, Blender, AI imagery, or decorative effects are permitted. The proof must be regenerated from `project.yaml` and the processed data.

## Terrain (as executed — supersedes the deferred plan above)

SRTM**GL3 (~90 m)** was selected and acquired, not GL1 (see DECISIONS D-011). Tiles were
preserved and hashed, mosaicked, warped to the analysis CRS, and frozen as
`data/processed/dem/iran_dem_90m.tif` (`provenance/checksums/dem_frozen_2026-09-09.txt`).

## Final publication cartography

1. **Render substrate.** `build_render_substrate.py` puts every layer on one LAEA grid
   (4096 × 3714, ~438 m/px): heightmap (bilinear from the frozen DEM), soil IDs (**nearest**
   only), soil texture from `config/soil_palette.yaml`, and Natural Earth water. Scientific
   rasters are never modified.
2. **Blender inputs.** `prepare_blender_inputs.py` decimates elevation to the mesh grid
   (1536 × 1393, ~1.17 km posting) and composites a display basecolor plus a class-ID
   texture. The geospatial stack stays on this side; Blender receives arrays and images
   already on the frozen grid, so no reprojection occurs inside the renderer.
3. **Scene.** `blender_build_scene.py` builds the whole scene by script: one mesh vertex per
   heightmap sample (asserted), UVs derived from geometry, orthographic camera, sun at
   40° NW, neutral ambient, Cycles, **Standard** view transform, **Closest** texture
   sampling. Vertical exaggeration is applied as object z-scale; real metres are never
   rescaled in the data.
4. **Registration proof.** The scene is re-rendered unlit, as pure emission of the class-ID
   texture at one render pixel per grid cell (1 sample, box filter, no denoise), and decoded
   back to the source raster through the camera's own geometry. This separates geometric
   registration from shaded readability instead of conflating them.
5. **Composition.** `build_poster.py` composes title, legend, labels, scale, north
   indicator, explanation and attribution as real text outside the renderer, exporting
   vector PDF/SVG beside the raster. Layout is fixed at 20 × 25 in; only dpi varies, so the
   proof, QA and master renders are the same composition.
6. **Map furniture is derived, not imitated.** `build_map_furniture.py` measures the
   projection's distance distortion before a scale bar is allowed, measures grid
   convergence before a north arrow is allowed, and verifies every label against the
   project's own rasters. The poster build aborts if a label fails.

Render sequence is always proof (2500 px) → QA (4000 px) → master, never straight to the
largest output.
