# QA plan and release gates

## Gate A — source identity and custody

- Official URL, exact version, access date, licence, attribution, native CRS/resolution, and local path are recorded in the source manifest.
- Every downloaded raw file has a generated—not hand-entered—SHA-256 sidecar.
- No raw input is changed by the pipeline.

## Gate B — boundary

- Source archive opens and source layer CRS is explicit.
- `ADM0_A3 == IRN` returns exactly one non-empty feature.
- Geometry is valid before writing; invalidity is a stop condition, not an automatic repair.
- Derived layer has explicit target CRS and metadata records exact selection expression.

## Gate C — HWSD schema and semantics

- Raster mapping-unit IDs resolve to database rows using a data-confirmed join key.
- The exact component table and field names are stored in the schema report.
- `ISSOIL`, `SHARE`, and `SEQ` semantics are verified against the technical report and data.
- Every output class is a single, named FAO/WRB hierarchy; no USDA labels are mixed in.
- Ties, missing values, and one-to-many mapping anomalies are counted and block a final classification unless explicitly resolved from the source documentation.

## Gate D — raster and statistics

- Soil transformations use nearest-neighbour resampling only.
- Class IDs are integers and every non-nodata class resolves to a lookup row.
- Class shares do not exceed 100%, and classified + nodata accounting equals raster-covered area within numerical tolerance.
- Boundary/raster/classified/nodata areas are independently reported; unexplained residual >0.5% fails the gate.

## Gate E — DEM

- Official-source tiles and checksums exist.
- SRTM product/version, WGS84 horizontal reference, EGM96 vertical reference, void treatment, and elevation range are recorded.
- Continuous resampling is recorded and never applied to the categorical soil raster.

## Gate F — proof map

- Proof contains only classes actually present in the processed raster.
- Palette is deterministic and lives in version-controlled configuration.
- Title, legend, source note, and projection note are legible.
- No 3D/AI/generated geographic content is present.

## Present state

Only Gate A's source-identity portion is passed. No data-derived QA gate is claimed passed until executable environment, raw archives, and processed outputs exist.
