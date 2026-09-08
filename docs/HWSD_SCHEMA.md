# HWSD v2.01 schema — evidence and interpretation

Two independent sources of evidence are combined here, and kept distinct:

- **DOC** = the official technical report *FAO & IIASA (2023), HWSD v2.0* (`data/raw/hwsd/HWSD2_technical_report_cc3823en.pdf`, sec. 2.2–2.3, Annex I–II).
- **MDB** = the actual `HWSD2.mdb` extracted from `HWSD2_DB.zip` (read via GDAL/OGR — see `provenance/metadata/hwsd_mdb_report.json`).

No field is used for derivation unless it is confirmed present in **MDB**. **DOC** supplies semantics only.

## 1. Raster ↔ database link (DOC, Annex II)

- The raster (`HWSD2.bil`, ESRI BIL, UInt16, nodata **65535**, 43200×21600, EPSG:4326) stores, in each pixel, the **soil mapping unit identifier**.
- That pixel value joins to the attribute database on the field **`HWSD2_SMU_ID`** (DOC Annex II, "the HWSD2_SMU_ID attribute can be joined to the GRID value").
- Note (DOC Annex II): the raster is natively **.BIL**, and FAO explicitly *recommends converting BIL to GeoTIFF* for convenience — this is why the FAO catalog lists a GeoTIFF distribution while the S3 asset is BIL. They are the same data in different containers.

## 2. Mapping-unit / component structure (DOC sec. 2.2–2.3.2)

- One **soil mapping unit (SMU)** is a *soil association*: a dominant soil plus up to 11 associated soils/inclusions (**up to 12 component records**; `SEQ` ranges 1–12).
- **`SEQ`** — sequence within the mapping unit, ordered by percentage share. **The dominant soil has `SEQ = 1`.**
- **`SHARE`** — percentage share of the soil unit within the mapping unit. **Shares within an SMU sum to 100%.**
- Classification fields per component:
  - **Soil unit symbol (WRB 2022)** — full WRB symbol = Reference Soil Group + primary qualifiers (+ phases).
  - **Soil unit name (WRB 2022)** — RSG plus most important primary qualifier.
  - **Soil unit symbol / name (FAO90)** — FAO 1990 Revised Legend.
- ⚠ **Count discrepancy inside DOC:** sec. 1.2 states "29 538" mapping units; sec. 2.2 states "29 385". Because the report is internally inconsistent, the SMU count is **measured from MDB**, not quoted.

## 3. Classification systems (DOC sec. 1.2 pt 5, Annex I)

- HWSD v2.0 uses the **FAO 1990 Revised Legend** for all soil units, **correlated** to **WRB 2022** (IUSS Working Group WRB, 2022).
- The project's target class is the **WRB 2022 Reference Soil Group (RSG)** of the dominant component — a single classification level. USDA Soil Taxonomy orders are **not** mixed into this legend.
- A WRB symbol's leading two-letter code is its RSG (e.g. `AN`→Andosols, `CM`→Cambisols, `CL`→Calcisols, `LP`→Leptosols, `RG`→Regosols, `SC`→Solonchaks). The exact RSG will be taken from an explicit MDB field where one exists, or derived from the WRB symbol prefix with the mapping recorded — decided after MDB inspection, not assumed.

## 4. Proposed derivation rule (hypothesis — see DECISIONS D-004)

> For each `HWSD2_SMU_ID`, take the **dominant component** and express it as its **WRB 2022 Reference Soil Group**.

- DOC establishes dominant = `SEQ = 1` (also the maximum `SHARE`). This will be **verified in MDB**: that `SEQ=1` exists for every SMU and coincides with max `SHARE`; ties/missing handled fail-closed.
- DOC limitation to carry into LIMITATIONS: *"Relying on dominant soils within soil associations only, may lead to misleading results"* — a dominant-soil map is a deliberate simplification of a soil-association database.

## 5. Non-soil / water handling (to confirm in MDB)

Some mapping units represent non-soil (water bodies, glaciers, rock, dunes, urban). Whether a dedicated flag (e.g. an `ISSOIL`-type field) exists, and how water/`SHARE=0`/`nodata` are encoded, is **confirmed from MDB** before any class counting. Nodata (65535) in the raster is excluded from classified area.

## 6. MDB actual structure — confirmed from inspection

**HWSD_SCHEMA_STATUS = SCHEMA_LOCKED** (evidence: `provenance/metadata/hwsd_mdb_report.json`, read via GDAL/OGR ODBC on 2026-09-08; 25 tables).

Tables used:

- **`HWSD2_SMU`** — 29,538 rows, one per soil mapping unit. Fields include `HWSD2_SMU_ID`, `SHARE`, `WRB4`, `WRB2`, `WRB2_CODE`, `WRB_PHASES`, `FAO90`, `COVERAGE`. ⚠ `WRB2` is **NULL for 1,748 SMUs** → not used as the dominant source.
- **`HWSD2_LAYERS`** — 408,835 rows (component × depth). Fields include `HWSD2_SMU_ID`, `SEQUENCE`, `SHARE`, `WRB2`, `WRB4`, `FAO90`, `LAYER` (`D1`–`D7`), plus per-layer properties. **This is the dominant source** (a `SEQUENCE=1` row exists for every SMU).
- **`D_WRB2`** — 35 rows, `CODE → Value`: 31 soil Reference Soil Groups + 4 non-soil (`GG` Glaciers, `IS` Islands, `ND` No Data, `WR` Open Water).

Confirmed facts that shaped the locked rule (see DECISIONS D-008):

| Question | Evidence-based answer |
| --- | --- |
| Raster→DB key | Raster pixel = `HWSD2_SMU_ID` (Annex II); nodata 65535 |
| Dominant component | `SEQUENCE = 1` in `HWSD2_LAYERS` (report-defined; present for all SMUs) |
| Share field | `SHARE` (sums to 100 within an SMU) |
| WRB 2022 RSG field | `WRB2` (2-letter code) → `D_WRB2` name |
| FAO90 field | `FAO90` |
| ISSOIL flag | **None exists** — non-soil identified via WRB2 ∈ {GG, IS, ND, WR} |
| SMU count | **29,538** (resolves the report's 29,538 vs 29,385 inconsistency) |
| Data quirks | `WRB2` casing inconsistency (`NT`/`Nt`, `GL`/`Gl`, `PT`/`Pt`) → uppercased before lookup; `SEQ=1` = max-`SHARE` in 97.78 % (dataset's `SEQ=1` designation is authoritative) |

The locked contract is recorded machine-readably in `config/hwsd_schema.yaml`.
