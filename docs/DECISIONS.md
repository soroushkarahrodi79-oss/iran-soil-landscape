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

**Status:** LOCKED (2026-09-08). On the extracted Iran boundary, the LAEA projected area = 1,622,509.5 km² vs the WGS84 geodesic area = 1,622,510.2 km² — a relative difference of 4.2e-5 %. Negligible distortion at the national extent, so the candidate is adopted for national area statistics. Exact WKT/PROJ recorded in `provenance/metadata/iran_boundary_processing.json`.

## D-004 — Dominant class semantics

**Decision:** The planned output semantic is “dominant soil component by recorded SHARE, represented as a WRB 2022 Reference Soil Group.” It is not a mixture or a USDA Soil Taxonomy order.

**Guardrail:** The database schema must demonstrate the join key, eligible soil indicator, share field, and selected WRB group field. Ties, missing shares, non-soil components, or discrepancies with `SEQ=1` cause a blocked processing run; they are never resolved by visual judgement.

## D-005 — No terrain rendering yet

**Decision:** Do not create a QGIS project, Blender file, terrain map, or final proof until the primary soil database has been inspected and the derived data can be checked. Blender's future role is documented as rendering only: DEM → geometry, soil raster → exact surface classes, boundary → geographic clipping.

## D-006 — Sensitive labels

**Decision:** The future publication may use “Persian Gulf” for the relevant water-body label, independently of the authoritative boundary geometry. Labels remain separate from geometries and must be cited in publication notes.

## D-007 — HWSD licence & raster-format resolution (verification pass 2026-09-07, corrected by artifact inspection 2026-09-08)

**Decision:** Record the HWSD v2.01 **licence as CC BY-NC-SA 4.0** and the **raster format as ESRI BIL** (`HWSD2.bil`+`.hdr`+`.prj`+`.stx`; UInt16 LE; nodata 65535; 43,200 × 21,600; EPSG:4326).

**Two-step evidence trail (kept deliberately, to show how the record was corrected):**

1. *2026-09-07 (metadata pass):* the FAO **primary catalog** ISO record `ff5c613c` (data.apps.fao.org) gave licence CC BY-NC-SA 4.0 (correcting a prior "3.0 IGO") and *described* a GeoTIFF/UInt16 distribution. Trusting that catalog description, the format record was changed from the scaffold's "ESRI BIL" to "GeoTIFF". The ISRIC mirror `54aebf11` was found internally inconsistent (labels "3.0", links the 4.0 URL) and set aside.
2. *2026-09-08 (artifact pass):* the actual `HWSD2_RASTER.zip` was downloaded and inspected. `HWSD2.hdr` shows **LAYOUT BIL**, UInt16 LE, nodata 65535, 43200×21600, EPSG:4326. **The asset is ESRI BIL, not GeoTIFF.** The 2026-09-07 GeoTIFF change was an over-correction based on catalog metadata; it is reverted. The original scaffold's "ESRI BIL" was correct. Cell size, UInt16 type, and nodata are consistent throughout.

**Principle affirmed:** where third-party/catalog metadata and the actual downloaded artifact disagree on the data's own properties, **the artifact is authoritative**. Catalog records remain authoritative for licence/citation, which the artifact does not carry.

**Rejected alternatives:** trusting the ISRIC "3.0" licence field (rejected — inconsistent mirror); keeping "GeoTIFF" from the catalog after the `.hdr` contradicted it (rejected — artifact wins).

**Residual uncertainty:** the database's exact table/field names are still confirmed only by direct inspection of `HWSD2.mdb` (D-004 gate).

**Status:** ACCEPTED. Applied to `source_manifest.csv`, `docs/LICENSES.md`, `docs/DATA_SOURCES.md`, `CITATION.cff`, and `provenance/metadata/acquisition_2026-09-08.json`.

**Addendum (2026-09-08, from the report PDF):** the technical report's own copyright page (p.3) states the *report document* is CC BY-NC-SA **3.0 IGO**, while the FAO catalog states the *dataset* is CC BY-NC-SA **4.0**. These are not contradictory — they license different artifacts. The manifest records the **report row** as 3.0 IGO and the **dataset rows** (raster/DB) as 4.0. Derived products inherit the dataset's 4.0 NC-SA terms.

## D-008 — Dominant-soil rule, LOCKED from MDB evidence (2026-09-08)

**Decision:** For each `HWSD2_SMU_ID`, the dominant soil is the **`SEQUENCE=1` component in `HWSD2_LAYERS`** (`LAYER='D1'`); the class is that component's **`WRB2`** (WRB 2022 Reference Soil Group), **uppercased** and resolved to a name via `D_WRB2`. Non-soil WRB2 codes (`GG` Glaciers, `IS` Islands, `ND` No Data, `WR` Open Water) are reported separately, not counted as soil. `HWSD_SCHEMA_STATUS = SCHEMA_LOCKED`.

**Evidence (provenance/metadata/hwsd_mdb_report.json + cross-check):**
- `HWSD2_SMU` has 29,538 rows (= SMU count; this resolves the report's internal 29,538-vs-29,385 inconsistency in favour of **29,538**).
- `HWSD2_SMU.WRB2` is NULL for 1,748 SMUs, but **every** SMU has a `SEQUENCE=1` row in `HWSD2_LAYERS` → LAYERS is the complete, authoritative dominant source.
- `SEQUENCE=1` equals the max-`SHARE` component in only 97.78 % of SMUs; the report defines `SEQUENCE=1` as the dominant, so the dataset's designation is used rather than a recomputed max-share.
- Casing inconsistencies exist in the data (`NT`/`Nt`, `GL`/`Gl`, `PT`/`Pt`); codes are uppercased before the `D_WRB2` join.

**Modification vs the D-004 hypothesis:** D-004 proposed "dominant by max SHARE among ISSOIL=1". Evidence changed two things: (a) HWSD2 has **no ISSOIL field** — non-soil is identified by WRB2 code instead; (b) dominant is **SEQUENCE=1**, not recomputed max-share. The hypothesis is thus *modified*, exactly as the gate permits.

**Result:** 16 classes present in Iran; Leptosols 40.7 %, Regosols 18.7 %, Solonchaks 18.6 %, Calcisols 16.8 % lead; 0 unmapped SMUs; area reconciles (see D-010 / area_qa.json).

## D-009 — Tooling workarounds on this Windows/conda stack (2026-09-08)

Three environment-specific issues were found and worked around **without changing the science**:
1. **MDB access:** conda-forge GDAL has no Java `MDB` driver; the **ODBC** driver opens `HWSD2.mdb` (a system Access ODBC driver is present). No mdbtools, no Access/Office install, no web converter — consistent with the environment decision.
2. **`rasterio.windows.from_bounds` hard-aborts** (exit 127) on this GDAL build; the Iran window is computed manually from the inverse geotransform instead (identical result).
3. **DLL resolution:** running `python.exe` without activating the env let a stray system `libpng`/`zlib` load, hard-aborting matplotlib PNG writes and `geopandas.plot()`. Fixed reproducibly in `scripts/_geoenv.py` (registers the env `Library/bin` via `os.add_dll_directory` + PATH) and by drawing boundary rings directly with matplotlib rather than `GeoDataFrame.plot()`.

## D-010 — Area accounting method (2026-09-08)

**Decision:** Compute national area statistics on the **native EPSG:4326 grid using latitude-correct WGS84 cell areas** (no categorical resampling), and the boundary area in the locked LAEA. Reconciliation A ≈ B + D and B = C + E + F held: A=1,622,509.5, B=1,621,202.1, C(soil)=1,612,385.2, E(non-soil)=8,816.9, F(unmapped)=0.0, D(nodata in polygon)=1,334.4 km²; A−B=1,307 km² (0.081 %) explained by the NE 1:10m coastline/border vs HWSD land-mask mismatch. No value was forced to a remembered national area.

## D-011 — National source DEM = SRTMGL3 (~90 m), not SRTMGL1 (~30 m) (2026-09-08)

**Decision:** Use **NASA/USGS SRTMGL3 v003 (~90 m, 3 arc-second)** as the national SOURCE_DEM for the terrain-enhanced poster. Reserve SRTMGL1 (~30 m) for possible future detail/inset work only.

**Evidence (`provenance/metadata/srtm_storage_estimate.json`, `scripts/acquisition/plan_srtm_tiles.py`):**
- Iran intersects **198** 1°×1° tiles (of 300 in the full rectangle).
- **GL3 (~90 m):** ~571 MB extracted / ~314 MB download. With mosaic/reproject/clip transients, peak ≲ ~1.5–2 GB.
- **GL1 (~30 m):** ~5,135 MB extracted / ~2.8 GB download; peak with transients ≳ ~10 GB — **exceeds the ~4.9 GB free disk** (D-Storage).
- **Publication adequacy:** the master is ~6,000–9,000 px across ~1,900 km → ground sampling ≈ 210–320 m/px. 90 m is ~2.5–3× finer than the render grid; 30 m would merely be downsampled away. 90 m is scientifically and visually adequate at national scale.

**Rejected alternative:** SRTMGL1 for the national base — rejected on storage (would risk exhausting the disk) with no visible benefit at poster scale.

**Reproducibility caveat:** SRTMGL3 v003 is void-filled/aggregated from SRTMGL1 by the provider; it is a distinct official product, not a resample we perform. Provenance recorded per D-Terrain-Contract.

## D-Storage — Storage gate before any terrain download (2026-09-08)

**MINIMUM_SAFE_FREE_SPACE = 3.0 GB** for the GL3 (~90 m) workflow (peak transient ≈ 1.5–2 GB + margin). Current free ≈ 4.9 GB → **adequate for GL3, inadequate for GL1**. Policy: prefer VRT/streaming mosaics; delete reproducible intermediates (extracted `.hgt`, VRT, full-bbox reprojected DEM) after the clipped DEM is written; **never** delete immutable `data/raw/` provenance without an explicit policy change. Re-check free space immediately before acquisition.

## D-012 — Water representation: HWSD accounting vs cartographic hydrology (2026-09-08)

**Decision:** Keep HWSD `WR` "Open Water" as a **non-soil accounting class only** (it is HWSD's land-mask category, not a hydrographic layer). For final cartography, use a **separate authoritative water/coastline source** — **Natural Earth 10m physical** (`ne_10m_ocean`, `ne_10m_lakes`; same provider/scale as the boundary) — for the Caspian Sea, Persian Gulf, Gulf of Oman, Lake Urmia, and major inland water. **Never** inject contemporary hydrology into the HWSD soil raster. Water-body **labels** ("Persian Gulf" per D-006) remain separate from geometry. NE physical layers are acquired in the render gate, not here.

## D-013 — Render-resolution strategy (SOURCE ≠ RENDER) (2026-09-08)

**Decision:** Three distinct artifacts, documented separately:
- **SOURCE_DEM** — SRTMGL3 tiles as downloaded, traceable to NASA/USGS (immutable in `data/raw/srtm/`).
- **PROCESSING_DEM** — mosaicked, reprojected, clipped to the Iran boundary; provenance recorded.
- **RENDER_HEIGHTMAP** — resampled (bilinear, **downsample only**) to the render grid (target ≈ master px dimension, e.g. ~6,000–8,000 across), deterministic and documented.

The project will **not** claim the render retains every native SRTM sample, and will not create a Blender vertex per native cell. Vertical exaggeration (future) will be a disclosed numeric factor. Terrain has exactly one role: **topographic context**; it never alters soil classification.

## D-014 — Soil-truth freeze (2026-09-08)

The four soil-truth products are frozen as immutable unless a documented defect is found: `iran_hwsd_mapping_units.tif`, `iran_dominant_soil_group.tif`, `soil_groups_iran.csv`, `iran_boundary.gpkg`. SHA-256 recorded in `provenance/checksums/soil_truth_frozen_2026-09-08.txt`; reproducible checkpoint tagged `data-gate-v1` at commit `df8cd5f`. No cosmetic alteration of soil geography is permitted.

## D-015 — Vertical exaggeration: 2× selected for publication (2026-09-09)

**Decision:** publish at **2×**, not the 3× that the prototype's pre-declared rule selected.

The rule was "lowest exaggeration whose relief contrast ≥ 0.060 with shadow burden ≤ 0.020",
applied honestly at the prototype gate: 2× measured **0.0590**, missing by 0.001. Because the
gap is under 2% of the threshold, the two are effectively tied on readability, and where two
options are equivalent the one that distorts real elevation less wins. 2× also loses an order
of magnitude less soil colour to shade (0.0001 vs 0.0016). **3× remains documented as a valid
alternative**, not an error. Threshold and measurements were left untouched; only the
preference between two passing-adjacent options was exercised.

## D-016 — Registration semantics: geometry and readability measured separately (2026-09-09)

**Decision:** never report a shaded reclassification score as spatial registration accuracy.

The prototype's 99.876% was measured on a lit render, so lighting and tone entered it; a real
geometric offset could have hidden inside it. Geometry is now proven by an **unlit class-ID
pass** — pure emission of a class-code texture, 1 sample, box filter, no denoise, one render
pixel per grid cell — decoded back through the camera's own geometry, with a ±3 px offset
search. Result: **100.0000%** over 8,432,268 px, best offset (0,0). The shaded figure is
retained but relabelled as **cartographic class readability**.

## D-017 — Final palette revision (display colours only) (2026-09-09)

**Decision:** revise eight display colours; change no class, boundary or ID.

Measurement (CIEDE2000, self-tested against Sharma et al. 2005; pairs weighted by the
boundary each shares in Iran; re-scored under simulated deuteranopia/protanopia) found the
prototype palette put **Arenosols, Calcisols and Regosols in one near-identical beige
cluster** (ΔE00 4.5–8.6), covering 37% of the country. Calcisols, Regosols, Arenosols,
Leptosols, Cambisols, Fluvisols, Luvisols and Technosols were re-specified until **every pair
sharing ≥20,000 boundary pixels passes ΔE00 ≥ 10 in normal vision and under both
dichromacies**. Two iterations were themselves corrections of collisions the previous
iteration introduced. Final hex values are recorded in `config/soil_palette.yaml` and
tabulated in `FINAL_CARTOGRAPHY.md`.

## D-018 — Scale bar and north arrow: measured before drawn (2026-09-09)

**Decision:** include both, each annotated with its measured error.

The CRS is equal-**area**, so distance is not preserved and a bar was not assumed. Across 71
sample pairs, map-to-geodesic distance ratios ranged 0.99825–1.00274 — a worst deviation of
**0.274%**, about ±1.1 km on the 400 km bar drawn. The bar is therefore included and labelled
"distance scale accurate to ±0.3% across the map" (gate option B). Grid convergence reaches
**5.79°** at the extreme corners, so the north arrow is small, is exact only on the central
meridian, and is labelled "±6°". Had either measurement been material, the element would have
been omitted rather than decorated.

## D-019 — Label placement is verified against the rasters (2026-09-09)

**Decision:** every physical-geography label must pass a data test before it is drawn, and the
poster build aborts if one fails. Sea labels must land on Natural Earth water; range labels on
high ground; basin labels on low ground. The Gulf of Oman is the documented compromise: the DEM
bounding box cuts through the gulf, so the anchor stays on verified Gulf of Oman water at 98%
of frame height and only the **text** is offset upward — moving the anchor would have placed
the name over the Strait of Hormuz, a different feature.

## D-020 — Two sheets over one render; feed sheet is composed, not downsampled (2026-09-10)

**Decision:** publish an archival `master` sheet and a `linkedin` sheet from a single
scientific render, and drop the earlier requirement that the LinkedIn asset be a downsample
of the master.

That earlier rule was correct while the two differed only in size, and it protected a real
risk: a separately recreated social image drifts from the map and eventually from its
claims. But feed legibility requires *larger type at a smaller pixel count*, which
resampling cannot produce. The protection is therefore re-expressed rather than dropped:
each sheet records the SHA-256 of the map render it drew, and `qa_final_publication.py`
plus `test_both_sheets_draw_the_same_scientific_render` fail if the two diverge. Full
citations, DOI and licence prose stay on the master, the PDF and `LICENSES.md`; the feed
sheet carries the licence identifier and a compact credit, which is what ShareAlike
requires on the artefact.

**Also decided:** body copy on the feed sheet is sized from the 540 px inspection
(methodology 24 pt, attribution 19 pt) rather than from the 20–25% uplift specified for
labels and legend text. At 20–25% both failed the readability requirement in the same
gate, so the two instructions could not both be satisfied; the readability requirement was
treated as the binding one and the deviation is recorded in `FINAL_QA.md`.

## D-021 — Outside-Iran background lightened to #D2CFC9 (2026-09-10)

**Decision:** `context_land_srgb` `#BFBAB2` → `#D2CFC9`. No soil palette colour touched.

Chosen by measurement against the competing constraint: lightening the surround improves
figure/ground against Leptosols (ΔE00 14.9 → 20.0) but pushes it toward Calcisols, which
reaches the border (14.1 → 11.5), and toward the paper (12.8 → 7.6). `#D2CFC9` is the
lightest value that keeps Calcisols above the project's ΔE00 ≥ 10 threshold. This is the
one change baked into the render rather than the composition, so it required a single
re-run of the accepted scene with every other parameter unchanged.

## D-022 — Cartographic furniture v1.1: composition only, and three decisions made by measurement (2026-09-12)

**Decision:** publish a v1.1 pair composed with the `v11_b` (feed) and `v11_master`
(archival) layouts, superseding v1.0 without deleting it. `config/publication.yaml` declares
which pair is published; both v1.0 layouts stay in `build_poster.py` so v1.0 remains
reproducible. Full record in `docs/CARTOGRAPHIC_FURNITURE_V1_1.md`.

The gate changed composition only. The scientific render is byte-identical to v1.0's and is
now frozen by hash in its own right
(`provenance/checksums/scientific_render_frozen_2026-09-12.txt`), so a future composition
gate that silently moved the map would fail a test rather than ship.

Three sub-decisions were resolved by measuring rather than by taste, and two of them came
out as "no".

**No national keyline.** Built from the project's own Natural Earth geometry, simplified to
one render pixel, then rejected: no stroke width both survives the 540 px feed reduction
(needs ≥ 2.27 pt) and stays inside HWSD's ~1 km native support (needs ≤ 0.7 pt), and the
border ring already separates from the surround at mean ΔE00 22.1 with none of its 21,157 px
below the ΔE00 ≥ 10 threshold. A visible stroke would have tinted ~0.9% of mapped Iran — the
outermost, most contact-sensitive band — to sharpen an edge that is already sharp.

**No palette change.** The Arenosols/Solonchaks greyscale residual (ΔL\* 4.4) was searched,
not re-asserted: 1,368 lightness-only candidates, hue and chroma held. Every one of the 513
that reached ΔL\* ≥ 8 regressed another pair. Two flaws in the first search had to be fixed
before it could say that honestly — it originally forbade only *new* low-luminance pairs
(letting a candidate pass by weakening the already-weakest pair) and ignored the two display
surfaces that every coastal class is actually drawn against. **KEEP_EXISTING_PALETTE.**

**Yes to a neatline, at a weight read out of the downsampled image.** 2.4 pt at 55% ink —
0.90 px at 540, measured ΔL\* 30.2 against the paper. 1.6 pt reads at only ΔL\* 17.8 and
leaves the map half-floating; 3.0 pt doubled reads as a card.

**Also decided:** the drawn text of a label is now verified, not just its anchor. v1.0
verified "Gulf of Oman" on Natural Earth water and then offset the text 2.8% of the frame
upward to escape the bottom edge, which put it on the Makran coast — a sea label over land
that every existing check passed. Offsets are now searched for under measured constraints
(edge clearance in the *cropped* frame, class-edge clutter, and for a sea label, staying on
the water body it names within a longitude window). Anchors are unchanged; two labels moved.
