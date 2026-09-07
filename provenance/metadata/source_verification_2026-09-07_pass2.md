# Source verification record — 2026-09-07 (second pass)

This record supplements (does not replace) `source_verification_2026-09-07.md`. It documents an independent re-verification of source identity against **primary** sources and the corrections that resulted.

## Method

Live fetches on 2026-09-07 of:

- FAO SOILS PORTAL HWSD v2.0 landing page (fao.org/soils-portal).
- FAO **primary catalog** ISO record `ff5c613c-75bb-46a9-a162-bc728059b465` (data.apps.fao.org) — treated as authoritative for HWSD licence/format/citation.
- ISRIC geonetwork mirror record `54aebf11-ec73-4ff8-bf6c-ecff4b0725ea` (data.isric.org) — secondary; found internally inconsistent.
- Natural Earth 10m cultural vectors download page (naturalearthdata.com).
- USGS/NASA SRTM documentation (via search).

## Findings

| Attribute | Prior repository record | Verified value (primary source) | Action |
| --- | --- | --- | --- |
| HWSD licence | CC BY-NC-SA 3.0 IGO | **CC BY-NC-SA 4.0** (FAO catalog `ff5c613c`) | Corrected |
| HWSD raster format | ESRI BIL | **GeoTIFF, UInt16, nodata 65535, 43,200 × 21,600, EPSG:4326** | Corrected |
| HWSD dataset citation | "...version 2.0, DOI ..." | **FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.** (report DOI 10.4060/cc3823en) | Corrected |
| HWSD mapping-unit / component counts | 29,385 units / up to 12 components | **Not asserted** — to be measured from downloaded DB | Removed pending measurement |
| HWSD version / revision date | v2.01, Sept 2023 | v2.01, Sept 2023 | Confirmed unchanged |
| HWSD resolution / CRS | 30 arc-second, EPSG:4326 | 30 arc-second (~0.0083333°), EPSG:4326 | Confirmed unchanged |
| Natural Earth Admin 0 10m version | 5.1.1, public domain | 5.1.1, public domain | Confirmed unchanged |
| SRTMGL1 acquisition | Requires authenticated EarthExplorer/Earthdata | Requires authenticated access | Confirmed unchanged |

## Discrepancy note

The ISRIC mirror labels the HWSD licence "3.0" in one metadata field while linking the Creative Commons `by-nc-sa/4.0/` URL — an internal inconsistency. Where FAO's own catalog and a mirror disagree, the FAO primary catalog is authoritative. Resolution recorded in DECISIONS D-007.

## Scope limit of this record

This record verifies **source identity, licence, and top-level format metadata only**. It claims **no** raw-archive checksum, no database-schema field inspection, no spatial processing, no area statistic, and no map proof. Those remain blocked pending download + runtime (see FOUNDATION_STATUS.md).
