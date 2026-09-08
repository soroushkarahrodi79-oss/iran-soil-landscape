# Data sources and source hierarchy

**Access date for all web records: 2026-09-07.** This register distinguishes verified source identity from downloaded-file verification. A source is not treated as spatially processed until its exact raw archive and SHA-256 are recorded.

## Primary soil source — SOURCE_VERIFIED / DOWNLOAD_PENDING

**Harmonized World Soil Database v2.01 (HWSD v2.0, September 2023 revision)** is the authoritative primary soil source. FAO's current HWSD page identifies the 2023 v2.0 release and a revised v2.01 release in September 2023. The supplied technical report is *FAO & IIASA (2023), Harmonized World Soil Database version 2.0* (report title), DOI `10.4060/cc3823en`; the dataset release itself is cited as *FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.*

Official assets, linked by FAO:

- Raster archive: `https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_RASTER.zip`
- Attribute database archive: `https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_DB.zip`
- Viewer/soil-type installer: `https://data.apps.fao.org/static/downloads/HWSD/hwsd21_setup_v20230905.exe`
- Source landing page: `https://www.fao.org/land-water/resources/tools/databases/hwsd/en`

HWSD is a 30 arc-second global GIS raster linked to a Microsoft Access 2003-format attribute database. The downloaded raster asset (`HWSD2_RASTER.zip`) is **ESRI BIL** — `HWSD2.bil` + `.hdr`/`.prj`/`.stx` — **UInt16 little-endian, nodata = 65535, 43,200 × 21,600 cells, XDIM/YDIM 0.0083333°, EPSG:4326**, confirmed directly from `HWSD2.hdr` on 2026-09-08. (The FAO catalog record `ff5c613c` describes a GeoTIFF/UInt16 distribution; that is a different/derived distribution, **not** this S3 `HWSD2_RASTER.zip` asset. The cell dimensions, UInt16 type, and nodata match; only the container differs — BIL, not GeoTIFF. See DECISIONS D-007.) FAO reports approximately 1 km resolution and seven depth layers (0–20 through 150–200 cm). The exact mapping-unit count, the maximum number of soil-unit/phase component records per mapping unit, and every field name **will be counted/read directly from the downloaded database** — no specific counts are asserted from memory here, because an earlier draft carried an unverified "29,385 mapping units / up to 12 components" figure that this project does not vouch for until measured. Soil units use the FAO 1990 Revised Legend with correlation to WRB 2022. This project will render only a derived **dominant component WRB Reference Soil Group**, after the exact database fields and joins are verified from the downloaded archive.

Required citation: *FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.* (technical report DOI `https://doi.org/10.4060/cc3823en`). The dataset is released under **CC BY-NC-SA 4.0** (verified against FAO catalog record `ff5c613c`, 2026-09-07; corrected from a prior "3.0 IGO" record — see DECISIONS D-007) with additional FAO terms prohibiting commercial resale/redistribution without written permission; its terms must be retained in downstream publication notes. The team must not infer that all individual source layers have broader redistribution rights than this record states.

## National boundary — SOURCE_VERIFIED / DOWNLOAD_PENDING

**Natural Earth, Admin 0 Countries, 1:10m, version 5.1.1** is the boundary source. Official archive: `https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip`. Official landing page: `https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/`.

Natural Earth describes this theme as WGS 84 geographic data and as a de facto country representation. The extraction criterion is exactly `ADM0_A3 == "IRN"`; no geometry will be redrawn, dissolved with a different source, or manually edited. Natural Earth says its data are public domain; the map should still credit “Made with Natural Earth” as good scholarly practice. The project uses its country polygon only, not a political claim beyond the provider’s representation.

## Terrain — SOURCE SELECTED / BLOCKED_USER_AUTH

**Selected national SOURCE_DEM: NASA/USGS SRTMGL3 v003 (~90 m, 3 arc-second)** — chosen over SRTMGL1 (~30 m) on storage/adequacy grounds (DECISIONS D-011); 30 m is reserved for possible future insets. Terrain's only role is **topographic context**; it never modifies soil classification (D-013).

### Terrain scientific contract (SRTMGL3 v003)

| Attribute | Value |
| --- | --- |
| Product / version | NASA Shuttle Radar Topography Mission Global 3 arc-second, **SRTMGL3.003** (NASADEM-adjacent SRTM release, void-filled) |
| Native resolution | 3 arc-second (~90 m at equator); tiles 1°×1°, **1201 × 1201** samples |
| Horizontal datum / CRS | WGS 84, EPSG:4326 |
| Vertical datum | EGM96 geoid; elevation in **metres** |
| NoData | `-32768` |
| Tile convention | SW-corner name, e.g. `N25E044` (all Iran = N/E) |
| Distributor | NASA LP DAAC **Earthdata Cloud** — `https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL3.003/{TILE}.SRTMGL3.hgt/{TILE}.SRTMGL3.hgt.zip` (collection `C2763264762-LPCLOUD`; Earthdata Search `https://search.earthdata.nasa.gov/`). The legacy Data Pool host `e4ftl01.cr.usgs.gov` is **deprecated** for SRTM (migrated to Earthdata Cloud, 2026-09-08 confirmation). |
| Access mechanism | **Earthdata Login required** (`.netrc` for `urs.earthdata.nasa.gov` + cookie jar, or `EARTHDATA_TOKEN` bearer). Verified 2026-09-08: an unauthenticated GET returns "HTTP Basic: Access denied", so downloads fail closed without credentials. |
| Licence | U.S. Government work, public domain; cite NASA/USGS |
| Iran tile set | **198** tiles intersecting the boundary (`provenance/manifests/srtm_tiles_iran.csv`) |

Acquisition requires the user's Earthdata credentials; the project will not bypass authentication, scrape a session, or substitute a third-party mirror. See `docs/DECISIONS.md` D-011/D-Storage and the acquisition manifest.

## Secondary validation sources — NOT A SPATIAL OVERRIDE

The HWSD technical report and authoritative FAO soil materials may be used to validate the derived broad pattern and terminology. They may not alter classes, geometry, or statistics. Iranian institutional or peer-reviewed references can be added only with an explicit entry in `source_manifest.csv` and a note explaining their validation-only role.

## Source discrepancy resolution

FAO retains a legacy HWSD v1.2 page while its current database page presents v2.0/v2.01. This project resolves the ambiguity in favour of the current FAO HWSD page, its official v2.01 assets, and the 2023 technical report. The legacy v1.2 page is not an input.

**License / format discrepancy (resolved 2026-09-07, second verification pass).** An earlier record in this repository stated the HWSD licence as "CC BY-NC-SA 3.0 IGO" and the raster format as "ESRI BIL". Independent re-verification found:

- The **FAO primary catalog** record `ff5c613c-75bb-46a9-a162-bc728059b465` (data.apps.fao.org) states **CC BY-NC-SA 4.0** and the citation *FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.* — both confirmed.
- The **ISRIC geonetwork** mirror record (`54aebf11-…`) is internally inconsistent: it labels the licence "3.0" in one field while linking the `by-nc-sa/4.0/` URL. Non-authoritative; superseded by the FAO catalog.
- On **raster format** the catalog and the actual asset disagreed. The catalog describes a GeoTIFF; the actual downloaded `HWSD2_RASTER.zip` (2026-09-08) is **ESRI BIL** (`HWSD2.hdr`: LAYOUT BIL, UInt16 LE, nodata 65535, 43200×21600, EPSG:4326). A verification pass on 2026-09-07 had over-corrected the format to "GeoTIFF" based on catalog metadata; **inspecting the artifact reverted this to BIL** (the original scaffold's "ESRI BIL" was correct). The cell size, UInt16 type, and nodata are consistent across both records.

Resolution: the FAO primary catalog is authoritative for **licence and citation** (CC BY-NC-SA 4.0), corrected in the manifest, LICENSES.md, and CITATION.cff. The **downloaded artifact itself** is authoritative for **format** (ESRI BIL). This illustrates the project principle that the artifact — not third-party metadata — is the final authority on the data it contains. See DECISIONS D-007.
