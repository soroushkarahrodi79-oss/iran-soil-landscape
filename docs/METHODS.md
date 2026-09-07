# Reproducible processing method

## Operating rule

Critical transformations are scripted. QGIS may inspect the results and develop a layout only after the same products exist from scripts. Raw data are immutable: no script writes into `data/raw/`, and every downloaded archive is SHA-256 hashed before a processing run.

## Planned commands

After creating the conda environment specified in `environment.yml`:

```text
python scripts/acquisition/acquire_natural_earth.py
python scripts/processing/preprocess_boundary.py
python scripts/acquisition/inspect_hwsd_schema.py
python scripts/processing/preprocess_soils.py
python scripts/validation/validate_outputs.py
python scripts/rendering/render_proof.py
pytest -q
```

`preprocess_soils.py` and `render_proof.py` are intentionally fail-closed until their inputs and schema contract are present. SRTM is not part of this chain until the user downloads tiles through an official authenticated route.

## Boundary

1. Keep the official Natural Earth ZIP under `data/raw/natural_earth/`.
2. Record its SHA-256 in `provenance/checksums/` and its actual file name/path in the manifest.
3. Read the original `ne_10m_admin_0_countries` layer in source CRS, select exactly `ADM0_A3 == "IRN"`, and require exactly one non-empty feature.
4. Reject invalid geometry rather than repairing or hand-editing it. Reproject only the copied derived feature to the documented Iran-centred LAEA CRS and write `data/processed/boundary/iran_boundary.gpkg`.
5. Write a metadata JSON record containing source/target CRS, WKT, source feature count, selection criterion, geodesic and equal-area areas, bounding box, and validity outcome.

## Soils

1. Acquire only the FAO-linked `HWSD2_RASTER.zip` and `HWSD2_DB.zip` archives; store unmodified copies under `data/raw/hwsd/`.
2. `inspect_hwsd_schema.py` exports a data-derived schema report. It must identify the raster's mapping-unit ID, the database table, join field, `SHARE`, `SEQ`, soil indicator, and a WRB 2022 Reference Soil Group field. It does not guess column names.
3. `preprocess_soils.py` requires that accepted schema contract. It will select components where `ISSOIL == 1`, choose the maximum `SHARE` per mapping unit, fail on tied maximum shares or unmapped IDs, and cross-check `SEQ == 1` rather than assuming it is correct.
4. The output categorical raster preserves mapping-unit identifiers in `iran_hwsd_mapping_units.tif`, then writes an integer class-ID raster `iran_dominant_soil_group.tif`. All categorical warping uses **nearest neighbour only**. The target transform, dimensions, nodata, and output CRS are recorded in metadata.
5. `soil_groups_iran.csv` reports each actual class's WRB group, source code, area km², share %, mapping-unit count, source classification, and notes. Nulls remain null when values are not defensible.

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
