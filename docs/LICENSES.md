# Licenses, attribution, and redistribution

| Dataset | Recorded terms | Required project action |
| --- | --- | --- |
| HWSD v2.01 | **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**, verified 2026-09-07 against the FAO primary catalog record `ff5c613c-75bb-46a9-a162-bc728059b465` (data.apps.fao.org). FAO terms additionally prohibit reproduction/redistribution for resale or other commercial purposes without written permission of the copyright holders. (Corrected from a prior "CC BY-NC-SA 3.0 IGO" record — see DECISIONS D-007. Note the ISRIC mirror record is internally inconsistent, listing "3.0" while linking the 4.0 licence URL; the FAO catalog is treated as authoritative.) | Cite *FAO & IIASA. Harmonized World Soil Database version 2.01. Rome and Laxenburg.* (technical report DOI 10.4060/cc3823en), retain the licence notice, honour the **NonCommercial** and **ShareAlike** terms on derived products, and obtain a separate decision (incl. contacting copyright@fao.org) before any commercial use or redistribution beyond these terms. |
| Natural Earth 1:10m Admin 0 v5.1.1 | Natural Earth states all site raster/vector data are public domain. | Preserve archive provenance. Use “Made with Natural Earth” in scholarly/cartographic credits although it is not required. |
| HWSD v2.01 technical report (cc3823en) | The **report document** is CC BY-NC-SA **3.0 IGO** (its own copyright page, p.3) — distinct from the **dataset**, which is 4.0. | Cite normally; the report's 3.0-IGO terms bind quotations of the report text, not the dataset-derived map. |
| NASA/USGS SRTMGL3 v003 (selected terrain, D-011) | U.S. Government work, public domain. | Acquire only via Earthdata/LP DAAC (authenticated), record product ID/tiles/void policy in run metadata, and cite NASA/USGS. |

This repository does not include any raw source data. Source archives are ignored by Git. No publication asset may omit the FAO/IIASA source citation or present the soil layer as independently surveyed by this project.

## Publication implications (summary)

The published map derives from HWSD v2.01, so **CC BY-NC-SA 4.0 is the binding constraint** (Natural Earth and SRTM add none). In short: **attribute** FAO & IIASA on every asset, **carry a "CC BY-NC-SA 4.0" notice on the map itself** (ShareAlike), and **keep publication non-commercial**. The NonCommercial line is the main grey zone (portfolio/LinkedIn posts are normally fine; paid promotion or client solicitation may not be). Full audit, precautions, and the "not legal advice / contact copyright@fao.org for commercial use" caveat are in [PUBLICATION_NOTES.md](PUBLICATION_NOTES.md).

## As published (publication gate)

The released assets carry, on the map face: the FAO & IIASA citation with the HWSD v2.01
DOI, the NASA/USGS SRTMGL3.003 credit, the Natural Earth credit, and the explicit line
**"This map is a derivative of HWSD v2.01 and is released under CC BY-NC-SA 4.0"** — the
ShareAlike obligation discharged on the artefact itself, not only in the post text.

Blender 4.5.13 LTS (GPL-2.0-or-later) is used as a tool; renders it produces carry no
licence obligation. The portable build is stored under `tools/` and is gitignored, so no
Blender binary is redistributed by this repository. Segoe UI is used as an installed system
font and **no font file is distributed**.
