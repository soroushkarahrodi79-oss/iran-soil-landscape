# Data sources and source hierarchy

**Access date for all web records: 2026-09-07.** This register distinguishes verified source identity from downloaded-file verification. A source is not treated as spatially processed until its exact raw archive and SHA-256 are recorded.

## Primary soil source — SOURCE_VERIFIED / DOWNLOAD_PENDING

**Harmonized World Soil Database v2.01 (HWSD v2.0, September 2023 revision)** is the authoritative primary soil source. FAO's current HWSD page identifies the 2023 v2.0 release and a revised v2.01 release in September 2023. The supplied technical report is *FAO & IIASA (2023), Harmonized World Soil Database version 2.0*, DOI `10.4060/cc3823en`.

Official assets, linked by FAO:

- Raster archive: `https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_RASTER.zip`
- Attribute database archive: `https://s3.eu-west-1.amazonaws.com/data.gaezdev.aws.fao.org/HWSD/HWSD2_DB.zip`
- Viewer/soil-type installer: `https://data.apps.fao.org/static/downloads/HWSD/hwsd21_setup_v20230905.exe`
- Source landing page: `https://www.fao.org/land-water/resources/tools/databases/hwsd/en`

HWSD is a 30 arc-second global GIS raster linked to a Microsoft Access 2003-format attribute database. FAO reports approximately 1 km resolution, 29,385 soil association mapping units, up to 12 soil-unit/phase component records per mapping unit, and seven depth layers (0–20 through 150–200 cm). Soil units use the FAO 1990 Revised Legend with correlation to WRB 2022. This project will render only a derived **dominant component WRB Reference Soil Group**, after the exact database fields and joins are verified from the downloaded archive.

Required citation: *FAO & IIASA. 2023. Harmonized World Soil Database version 2.0. Rome and Laxenburg. https://doi.org/10.4060/cc3823en.* The report is released under CC BY-NC-SA 3.0 IGO; its terms must be retained in downstream publication notes. The team must not infer that all individual source layers have broader redistribution rights than this record states.

## National boundary — SOURCE_VERIFIED / DOWNLOAD_PENDING

**Natural Earth, Admin 0 Countries, 1:10m, version 5.1.1** is the boundary source. Official archive: `https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip`. Official landing page: `https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/`.

Natural Earth describes this theme as WGS 84 geographic data and as a de facto country representation. The extraction criterion is exactly `ADM0_A3 == "IRN"`; no geometry will be redrawn, dissolved with a different source, or manually edited. Natural Earth says its data are public domain; the map should still credit “Made with Natural Earth” as good scholarly practice. The project uses its country polygon only, not a political claim beyond the provider’s representation.

## Terrain — SOURCE_VERIFIED / BLOCKED_USER_ACTION

The selected terrain source is **USGS/NASA SRTMGL1, 1 Arc-Second Global**, acquired through USGS EarthExplorer or NASA Earthdata Search. USGS's SRTM collection page identifies 1-arc-second global data and EarthExplorer as an official acquisition route. SRTMGL1 tiles are 1° × 1°, 3601 × 3601 samples, WGS 84 horizontal datum, elevations in metres relative to EGM96. Product documentation says that non-void-filled data use `-32768` for voids; the chosen product/void treatment must be written to the run metadata before processing.

Official entry points:

- `https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm`
- `https://earthexplorer.usgs.gov/`
- `https://search.earthdata.nasa.gov/`

Download requires the user's registered access path; no credentials are present in this workspace and the project will not bypass authentication, scrape a session, or substitute a third-party mirror. USGS data are generally U.S. public-domain works; cite USGS/NASA and retain product provenance regardless.

## Secondary validation sources — NOT A SPATIAL OVERRIDE

The HWSD technical report and authoritative FAO soil materials may be used to validate the derived broad pattern and terminology. They may not alter classes, geometry, or statistics. Iranian institutional or peer-reviewed references can be added only with an explicit entry in `source_manifest.csv` and a note explaining their validation-only role.

## Source discrepancy resolution

FAO retains a legacy HWSD v1.2 page while its current database page presents v2.0/v2.01. This project resolves the ambiguity in favour of the current FAO HWSD page, its official v2.01 assets, and the 2023 technical report. The legacy v1.2 page is not an input.
