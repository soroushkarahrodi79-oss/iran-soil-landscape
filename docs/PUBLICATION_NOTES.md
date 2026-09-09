# Publication notes (future release)

## Working title

**Iran Soil Landscapes — dominant soil groups from FAO/IIASA HWSD v2.01**

## Required explanatory language

Use: “Dominant soil group according to the FAO/IIASA Harmonized World Soil Database v2.01 component schema.” Do not use “the soil at this exact location” or imply field validation.

## Attribution draft

Soil data: FAO & IIASA, *Harmonized World Soil Database version 2.01*, Rome and Laxenburg (technical report DOI https://doi.org/10.4060/cc3823en), licensed CC BY-NC-SA 4.0. Boundary: Made with Natural Earth. Terrain (if used): NASA/USGS SRTMGL3 v003 (public domain). Processing and cartography: Iran Soil Landscapes project.

## Publication licence audit (CC BY-NC-SA 4.0 — the binding constraint)

The published map is a derivative of HWSD v2.01, which is **CC BY-NC-SA 4.0**. Natural Earth (public domain) and SRTM (U.S. public domain) impose no additional restriction, so HWSD's terms govern. *This is a practical summary, not legal advice; for anything commercial, consult FAO (copyright@fao.org) or counsel.*

**Clear from the licence:**
- **Attribution (BY):** the FAO & IIASA citation above must appear on every published asset and post; do not crop it out.
- **ShareAlike (SA):** derivatives must be released under the **same licence**, so the poster/LinkedIn image itself should carry a visible **"CC BY-NC-SA 4.0"** notice.
- **No additional restrictions:** do not add DRM or terms that further restrict recipients.

**Ambiguous / needs judgement:**
- **NonCommercial (NC):** a personal portfolio piece and an ordinary LinkedIn post are normally non-commercial. The grey zone is using the map to **promote a paid product/service, in paid advertising, in a monetised/ad-supported context, or for client solicitation** — those can read as commercial. LinkedIn being a "professional" network does not by itself make a post commercial, but intent and framing matter.

**Recommended precautions before publishing:**
1. Embed the attribution line and the "CC BY-NC-SA 4.0" notice directly in the image and the post text.
2. Keep it non-commercial: no paywall, no boosted/sponsored placement, no "hire me / buy this" framing on the asset itself.
3. State clearly it is "dominant soil group per HWSD v2.01" — not a field survey (avoids misrepresentation, separate from licensing).
4. If any commercial use is ever intended, seek written permission from FAO (copyright@fao.org) first.
5. Do not imply FAO/IIASA/NASA endorsement.

## Visual direction

Visual inspiration may acknowledge “Hemed Lungo’s terrain-enhanced geospatial cartography.” This is inspiration only: no collaboration, endorsement, copied layout, palette, typography, source data, or rendered assets is implied.

## Output contract

- Archival master: at least ~6000 × 7500 px, lossless PNG/TIFF.
- LinkedIn derivative: ~2160 × 2700 px (4:5), controlled downsampling from the master.
- Primary future 3D map: orthographic camera unless a documented departure is accepted.
- Blender contract: DEM supplies geometry/displacement; categorical soil raster supplies exact colour/texture class; boundary mask supplies geographic clipping. No procedural content may change soil classes.

## Geopolitical/label policy

Use the selected Natural Earth geometry consistently. No international boundary editing is permitted. Labels remain separate from source geometry. Use “Persian Gulf” for the relevant water label unless a future source/licensing constraint requires a documented alternative.

---

# Published asset (publication gate, base `74b435c`)

## Final title

**SOIL LANDSCAPES OF IRAN**
*Terrain, climate and the geography beneath our feet*

Supersedes the earlier working title. Meaning unchanged; only capitalisation was set.

## Assets

| Asset | File | Notes |
| --- | --- | --- |
| Archival master | `outputs/master/iran_soil_landscapes_6000x7500.png` | lossless PNG, 4:5, 22.3 MB |
| Vector composition | `…6000x7500.pdf` / `.svg` | live text, map embedded as raster |
| LinkedIn derivative | `outputs/linkedin/iran_soil_landscapes_linkedin_2160x2700.png` | Lanczos downsample of the master, 3.01 MB |

All are gitignored: they are regenerable from the scripts, and the repository stores the
method rather than the product.

**Before posting, re-check LinkedIn's current image size/format limits.** The 5 MB budget
used here is a conservative working figure, not a verified current platform limit.

## Allowed framing

> Terrain-enhanced cartographic visualization of dominant HWSD v2.01 soil groups across Iran.

Do **not** describe it as a high-resolution soil map, a 30 m soil map, a field-validated or
national soil survey, a real-time map, or as giving the precise soil at any point. The
`test_publication_claim_ceiling_is_not_breached` test guards the wording in the repository;
it cannot guard what is typed into a post.

## Suggested post copy

> **Soil Landscapes of Iran**
> Every colour is the dominant soil group of a HWSD v2.01 mapping unit — the most extensive
> soil in a unit that usually contains several, not the soil under any one field. Terrain is
> SRTMGL3 shaded relief at 2× vertical exaggeration, used as context: it never changes a
> soil class, and the finer terrain detail does not make the soil data finer than its native
> ~1 km.
>
> Leptosols cover 40.7% of the country — thin soils over rock, tracing the Zagros and Alborz.
> Solonchaks (18.6%) fill the closed central basins, where salts have nowhere to drain.
>
> Soils: FAO & IIASA, Harmonized World Soil Database v2.01 (CC BY-NC-SA 4.0).
> Terrain: NASA/USGS SRTMGL3.003. Boundary and water: Natural Earth.
> Projection: Lambert azimuthal equal-area. Map released under CC BY-NC-SA 4.0.
>
> Visual inspiration: Hemed Lungo's terrain-enhanced geospatial cartography — inspiration
> only, with no affiliation, collaboration or endorsement implied.

## Non-commercial reminder

HWSD v2.01 is CC BY-NC-SA 4.0, so the ShareAlike notice must stay on the asset and the post
must stay non-commercial: no boosted/sponsored placement, no paywall, no "hire me" framing
on the asset itself. For anything commercial, contact FAO (copyright@fao.org) first. This is
a practical summary, not legal advice.

---

## LinkedIn sheet (visual polish gate)

The feed asset is now composed with its own layout rather than downsampled from the master.
The map, projection, camera, 2× exaggeration, classification and statistics are identical —
both sheets draw the same render, checked by hash — but the furniture is sized for a phone.

| | On the sheet | Where the full version lives |
| --- | --- | --- |
| Method | one statement: dominance, ~1 km native support, 2× exaggeration, and that terrain detail is not soil detail | master sheet, PDF, `METHODS.md` |
| Credit | `Data: FAO & IIASA · NASA/USGS · Natural Earth · CC BY-NC-SA 4.0` | master sheet, PDF, `LICENSES.md` |
| Scale note | `Scale variation <0.3%` | `FINAL_CARTOGRAPHY.md` |

Every qualification the archival sheet makes is still made on the feed sheet — it is
shortened, not weakened. The licence identifier stays on the face of the image, which is
what the ShareAlike obligation requires; the full citation with DOI moves to the post text
and the master.

**Post the full attribution in the post body**, since the on-image credit is now compact:

> Soils: FAO & IIASA, Harmonized World Soil Database v2.01, Rome and Laxenburg
> (DOI 10.4060/cc3823en), licensed CC BY-NC-SA 4.0. Terrain: NASA/USGS SRTMGL3.003.
> Boundary and water: Made with Natural Earth. Projection: Lambert azimuthal equal-area.
> This map is released under CC BY-NC-SA 4.0.
