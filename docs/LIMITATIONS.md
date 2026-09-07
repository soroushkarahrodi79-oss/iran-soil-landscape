# Scientific limitations

- HWSD is a global harmonized mapping-unit dataset at 30 arc-second (~1 km) raster support; it is not a field-validated, site-specific soil survey of Iran.
- A mapping unit can contain multiple soil components. A displayed dominant component intentionally simplifies that mixture and must be labelled as such.
- “Dominant” is an attribute-table decision based on the dataset's components and shares, not a claim that every point in a cell has that soil group.
- The projected area of a raster cell varies in the source geographic CRS. Area statistics must be calculated after an explicitly recorded equal-area operation or by a documented geodesic equivalent.
- The boundary source has its own scale, coastline, and de facto representation. Boundary area, raster coverage, and any remembered national-area figure are not expected to be identical.
- SRTMGL1’s ~30 m elevation support does not confer ~30 m soil resolution. Terrain detail is a visual enhancement and cannot change the categorical soil geography.
- SRTM elevation is referenced to EGM96 and may include radar-surface/void-fill limitations. Any vertical exaggeration in a future render must be numerical and disclosed.
- This foundation stage contains no processed soil raster, no soil-class statistics, no DEM, and no proof map. These are intentionally reported as pending, not estimated.
