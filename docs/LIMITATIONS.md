# Scientific limitations

- HWSD is a global harmonized mapping-unit dataset at 30 arc-second (~1 km) raster support; it is not a field-validated, site-specific soil survey of Iran.
- A mapping unit can contain multiple soil components. A displayed dominant component intentionally simplifies that mixture and must be labelled as such.
- “Dominant” is an attribute-table decision based on the dataset's components and shares, not a claim that every point in a cell has that soil group.
- The projected area of a raster cell varies in the source geographic CRS. Area statistics must be calculated after an explicitly recorded equal-area operation or by a documented geodesic equivalent.
- The boundary source has its own scale, coastline, and de facto representation. Boundary area, raster coverage, and any remembered national-area figure are not expected to be identical.
- SRTMGL3’s ~90 m elevation support does not confer finer soil resolution. Terrain detail is a visual enhancement and cannot change the categorical soil geography.
- SRTM elevation is referenced to EGM96 and may include radar-surface/void-fill limitations. Any vertical exaggeration in a future render must be numerical and disclosed.
- **Dominant-soil simplification (explicit).** The map shows the `SEQUENCE=1` component per SMU. The HWSD technical report warns: *"Relying on dominant soils within soil associations only, may lead to misleading results."* Each ~1 km cell may contain up to 12 soil components; associated/inclusion soils are not shown.
- **`SEQUENCE=1` ≠ strictly largest share everywhere.** In 2.22 % of SMUs globally the `SEQUENCE=1` component is not the maximum-`SHARE` component. We use the dataset's `SEQUENCE=1` designation (the report's definition of dominant), not a recomputed max-share.
- **Non-soil classes.** `WR` (Open Water, e.g. Lake Urmia), `GG`, `IS`, `ND` are HWSD categories, not soils; they are reported separately and excluded from soil-class shares.
- **Data quirks handled, not hidden.** `HWSD2_SMU.WRB2` is NULL for 1,748 SMUs (we use `HWSD2_LAYERS` instead); WRB2 codes have casing inconsistencies (uppercased before lookup). These are documented in DECISIONS D-008.
- **Area accounting is internally consistent, not an official cadastral figure.** Boundary area 1,622,510 km² (Natural Earth 1:10m) is ~1.5 % below commonly cited official areas (~1.648 M km²) due to the generalized 1:10m coastline/borders and inland-water treatment — expected and documented, not an error.
- **Terrain (superseded note).** SRTM **GL3 (~90 m)** was acquired and verified (D-011), not GL1; `iran_dem_90m.tif` is frozen. The published map applies 2x vertical exaggeration, disclosed on the map itself. Terrain detail remains a visual enhancement and cannot change the categorical soil geography.
- **DEM nodata (4.5% of the render grid, SRTM water voids) is rendered at sea level** in the 3D scene. Those pixels lie under the cartographic water layer, so nothing false is displayed, but the geometry there is a rendering convenience rather than measured elevation.
- **Greyscale reproduction.** Arenosols and Solonchaks are unmistakable in colour (CIEDE2000 38.1) but close in luminance (dL* 4.4); a greyscale print would not separate them well.
