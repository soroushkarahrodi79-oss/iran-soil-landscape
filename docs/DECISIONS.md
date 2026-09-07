# Decision record

## D-001 — Soil source selection

**Decision:** Use FAO/IIASA HWSD v2.01, not the legacy v1.2 download.

**Evidence:** FAO's current HWSD landing page identifies v2.0 (2023) and a September 2023 revision called v2.01. It documents a 30 arc-second raster linked to 29,385 soil association mapping units, FAO 1990 / WRB 2022 correlation, and seven depth layers.

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
