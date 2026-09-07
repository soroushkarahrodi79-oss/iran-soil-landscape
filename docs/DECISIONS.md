# Decision record

## D-001 — Soil source selection

**Decision:** Use FAO/IIASA HWSD v2.01, not the legacy v1.2 download.

**Evidence:** FAO's current HWSD landing page identifies v2.0 (2023) and a September 2023 revision called v2.01. It documents a 30 arc-second raster linked to a mapping-unit / component attribute database, FAO 1990 / WRB 2022 correlation, and seven depth layers. (The exact mapping-unit and component counts are deliberately **not** asserted here; they will be measured from the downloaded database. A prior draft's "29,385 mapping units / up to 12 components" figure was unverified and has been removed pending measurement.)

**Status:** SOURCE_VERIFIED; raw archives remain DOWNLOAD_PENDING.

## D-002 — Boundary representation

**Decision:** Extract the single Natural Earth Admin 0 Countries v5.1.1 record with `ADM0_A3 = IRN`.

**Reason:** It is the requested 1:10m authoritative boundary source for this project. The default Natural Earth representation is de facto; this is documented rather than silently altered. No political or geometric edits are allowed.

## D-003 — Area and cartographic CRS

**Decision:** Propose a custom Iran-centred Lambert Azimuthal Equal Area CRS: `+proj=laea +lat_0=32 +lon_0=53 +datum=WGS84 +units=m +no_defs +type=crs`.

**Reason:** An equal-area, Iran-centred CRS avoids Web Mercator area distortion and avoids imposing one UTM zone across the national extent.

**Status:** PROVISIONAL_PENDING_BOUNDARY_SCALE_QA. The processing script will record the exact WKT/PROJ representation and compare its area with a WGS84 geodesic calculation. If the geometry or scale behaviour is materially unsuitable, this decision must be revisited before any statistics are accepted.

## D-004 — Dominant class semantics

**Decision:** The planned output semantic is “dominant soil component by recorded SHARE, represented as a WRB 2022 Reference Soil Group.” It is not a mixture or a USDA Soil Taxonomy order.

**Guardrail:** The database schema must demonstrate the join key, eligible soil indicator, share field, and selected WRB group field. Ties, missing shares, non-soil components, or discrepancies with `SEQ=1` cause a blocked processing run; they are never resolved by visual judgement.

## D-005 — No terrain rendering yet

**Decision:** Do not create a QGIS project, Blender file, terrain map, or final proof until the primary soil database has been inspected and the derived data can be checked. Blender's future role is documented as rendering only: DEM → geometry, soil raster → exact surface classes, boundary → geographic clipping.

## D-006 — Sensitive labels

**Decision:** The future publication may use “Persian Gulf” for the relevant water-body label, independently of the authoritative boundary geometry. Labels remain separate from geometries and must be cited in publication notes.

## D-007 — HWSD licence & raster-format discrepancy resolution (second verification pass, 2026-09-07)

**Decision:** Record the HWSD v2.01 licence as **CC BY-NC-SA 4.0** and the raster format as **GeoTIFF, UInt16, nodata 65535, 43,200 × 21,600, EPSG:4326**, superseding an earlier repository record of "CC BY-NC-SA 3.0 IGO" and "ESRI BIL".

**Evidence:** Independent re-verification of the FAO **primary catalog** ISO record `ff5c613c-75bb-46a9-a162-bc728059b465` (data.apps.fao.org) confirms CC BY-NC-SA 4.0, GeoTIFF/UInt16/nodata 65535/43200×21600, and the citation *FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.* The ISRIC geonetwork mirror record `54aebf11-…` is internally inconsistent (labels "3.0" but links the 4.0 licence URL) and is treated as a non-authoritative secondary mirror.

**Rejected alternative:** Trusting the ISRIC "3.0" field, or retaining the "3.0 IGO" / "BIL" values from memory. Rejected because the FAO catalog is the strongest primary source and the two disagreed.

**Residual uncertainty:** The raster's exact internal byte layout and the database's exact table/field names are still confirmed **only** by direct inspection of the downloaded archives (D-004 gate); this decision fixes the licence and top-level format metadata, not the internal schema.

**Status:** ACCEPTED. Applied to `source_manifest.csv`, `docs/LICENSES.md`, `docs/DATA_SOURCES.md`, and `CITATION.cff`.
