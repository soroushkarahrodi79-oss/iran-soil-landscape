# Final cartography — locked decisions

Gate: `FINAL_PUBLICATION_CARTOGRAPHY` (base `74b435c`). Every value here is reproducible
from configuration; nothing was authored by hand in a GUI.

## Locked map parameters

| Parameter | Value | Where it lives |
| --- | --- | --- |
| Camera | Orthographic top-down | `config/render_3d.yaml` → `cameras.topdown` |
| Vertical exaggeration | **2.0×** | `--selected-exaggeration 2` |
| Lighting | Sun 40° elevation, azimuth 315° (NW), strength 3.0, 3° angular diameter | `config/render_3d.yaml` → `lighting` |
| Ambient | Neutral white world at 0.35, no HDRI, no colour cast | same |
| Engine | Cycles 4.5.13 LTS, CUDA GPU, 48 samples, CPU denoise, 512 px tiles | `config/render_3d.yaml` → `render` |
| View transform | **Standard** (never AgX/Filmic) | `blender_build_scene.py` |
| Texture sampling | **Closest** on every categorical texture | same |
| Projection | Lambert azimuthal equal-area, lat₀ 32°N, lon₀ 53°E | frozen substrate |
| Map render | 5400 × 4897 px (master), 3600 × 3264 (QA), 2500 × 2267 (proof) | `--map-size` |
| Poster | 20 × 25 in at 300/200/125 dpi → 6000 × 7500 / 4000 × 5000 / 2500 × 3125 | `build_poster.py` |
| Typeface | Segoe UI (system-licensed, not redistributed) | resolved at runtime |

Terrain sits **below** soil in the visual hierarchy: relief is a 2× shaded-relief context
layer whose measured shading burden removes 0.01% of soil colour to deep shade. The
composition is the project's own; it is not a reconstruction of any reference poster.

## Final palette (display colours only)

Class identity, class boundaries and class IDs are frozen and were **not** touched. Only
display colours changed, driven by `scripts/validation/qa_palette_final.py`.

| Class | Code | Hex | Share of Iran |
| --- | --- | --- | --- |
| Leptosols | LP | `#8B8A83` | 40.703% |
| Regosols | RG | `#C0A176` | 18.651% |
| Solonchaks | SC | `#E3B9D6` | 18.552% |
| Calcisols | CL | `#F2E8C6` | 16.759% |
| Arenosols | AR | `#E3B15A` | 2.139% |
| Cambisols | CM | `#9A6234` | 1.475% |
| Open Water (non-soil) | WR | `#4E79A7` | 0.544% |
| Gleysols | GL | `#7FA9AE` | 0.467% |
| Technosols | TC | `#6B4F63` | 0.419% |
| Fluvisols | FL | `#2E8B6B` | 0.265% |
| Kastanozems | KS | `#B5651D` | 0.015% |
| Gypsisols | GY | `#E7C9E0` | 0.006% |
| Luvisols | LV | `#8B4726` | 0.004% |
| Histosols | HS | `#5B3A29` | 0.001% |
| Chernozems | CH | `#2B2B2B` | 0.0004% |
| Acrisols | AC | `#C1440E` | 0.0004% |

Non-class display colours: cartographic water `#6E93B8`, terrain outside Iran `#D2CFC9`
(revised in the LinkedIn polish gate — see below), paper `#F4F1EA`. Both are tested not to
collide with any soil colour.

### What the palette QA changed, and why

Pairs were scored in **CIEDE2000** (implementation self-tested against the published
Sharma et al. 2005 reference pairs, 5/5 reproduced), weighted by the boundary length each
pair actually shares in Iran, and re-scored under simulated deuteranopia and protanopia.

The prototype palette had a real defect: **Arenosols, Calcisols and Regosols formed a
cluster of three near-identical beiges** (ΔE00 4.5–8.6). Calcisols/Regosols alone share
26,397 boundary pixels and together cover 35% of Iran, so the map's largest colour decision
was also its weakest.

| Change | From | To | Reason |
| --- | --- | --- | --- |
| Calcisols | `#E9DC9B` | `#F2E8C6` | pale calcic cream, highest L\*, out of the beige cluster |
| Regosols | `#D9C7A3` | `#C0A176` | mid tan, clearly darker than Calcisols |
| Arenosols | `#EDD59E` | `#E3B15A` | saturated sand-amber; was ΔE00 4.5 from Calcisols |
| Leptosols | `#A9A18C` | `#8B8A83` | darker neutral rock-grey, restoring luminance separation from the new Regosols |
| Cambisols | `#B5834A` | `#9A6234` | deeper red-brown, away from tan Regosols |
| Fluvisols | `#79A86B` | `#2E8B6B` | teal-green survives deuteranopia against Cambisols |
| Luvisols | `#C98A3B` | `#8B4726` | separates from Cambisols |
| Technosols | `#7F7F7F` | `#6B4F63` | off the grey axis, after Leptosols darkened onto it |

Two of these were corrections of problems the changes themselves introduced —
darkening Regosols collided with Leptosols, and darkening Leptosols then collided with
Technosols. Both were caught by re-measuring after each iteration rather than by eye.

**Result:** every class pair sharing ≥20,000 boundary pixels now passes ΔE00 ≥ 10 in normal
vision and under both dichromacies.

### Residuals accepted

| Pair | ΔE00 | Worst CVD | Shared border | Why accepted |
| --- | --- | --- | --- | --- |
| Cambisols / Fluvisols | 38.9 | 7.4 (prot) | 141 px | ~60 km of contact between a 1.5% and a 0.3% class |
| Cambisols / Luvisols | 9.9 | 6.5 | 112 px | Luvisols is 71 km² — invisible at map scale |
| Fluvisols / Leptosols | 22.4 | 5.6 | 69 px | ditto |
| Cambisols / Kastanozems | 7.1 | 3.5 | 16 px | Kastanozems is 248 km² |
| Arenosols / Solonchaks | 38.1 | — | 6,435 px | ΔE00 is high; only the **greyscale** separation is weak (ΔL\* 4.4) |

The last is the one honest limitation for a greyscale reproduction: amber and pink are
unmistakable in colour and close in luminance.

## Scale bar — measured, then included

The CRS is equal-**area**, which does not preserve distance, so a bar was not added by
default. Across 71 sample pairs spanning 44.5–63°E and 25.5–39.5°N, planar map distance
against WGS84 geodesic distance ranged **0.99825 – 1.00274**: a worst deviation of
**0.274%**. Over the 400 km bar drawn, that is about ±1.1 km — far below the width of the
bar's own end cap.

**Decision: include the bar, annotated on the map** with "equal-area projection; distance
scale accurate to ±0.3% across the map". Option B of the gate. Had the deviation been
material the bar would have been omitted; it was measured before it was drawn.

## North indicator — included, with its error stated

In an azimuthal projection meridians converge, so grid north is exactly up only on the
central meridian. Measured convergence at nine points spanning the extent reaches
**5.79°** at the extreme corners. A single small arrow is therefore honest for orientation
but not for bearings, and is labelled "±6°". No decorative compass rose.

## Labels

Nine physical-geography labels, no provinces, cities or roads. Each was **verified against
the project's own rasters** before being drawn (`build_map_furniture.py`), and the poster
build refuses to run if any label fails:

| Label | Test | Measured |
| --- | --- | --- |
| Caspian Sea, Persian Gulf, Gulf of Oman, Lake Urmia | on Natural Earth water | 100% water in a 9×9 window |
| Alborz | high ground | 3,223 m median |
| Zagros | high ground | 2,374 m median |
| Dasht-e Kavir | low ground | 721 m median |
| Lut Desert | low ground | 344 m median |
| Khuzestan Plain | low ground | 21 m median |

The Gulf of Oman is the one compromise: the DEM bounding box cuts through it, so the only
water anchor sits at 98% of the frame height. Moving the label to a comfortable position
would have placed it over the **Strait of Hormuz**, which is a different feature — so the
anchor stays on verified Gulf of Oman water and only the text is nudged upward.

## Title and typography

- Title: **SOIL LANDSCAPES OF IRAN** — all caps, bold, 54 pt at 20 in width.
- Subtitle: *Terrain, climate and the geography beneath our feet* — sentence case, soft grey.
  The scientific meaning is unchanged from the brief; only capitalisation was set.
- Physical-feature labels in spaced semibold caps; water labels in italic blue, following
  the long-standing cartographic convention that hydronyms are italic.
- Text is composed **outside** Blender and exported as vector PDF and SVG alongside the
  raster, so no type is rasterised unless the raster output is used.

---

## Two sheets over one scientific render (LinkedIn polish gate)

The map itself is untouched by this gate. Projection, camera, 2× exaggeration, soil
geometry, soil IDs, DEM, water geometry, classification and statistics are all as accepted
at `6f1319f`; the frozen hashes are re-verified in `FINAL_QA.md`. What changed is furniture
and type, and the sheet count.

| | `master` sheet | `linkedin` sheet |
| --- | --- | --- |
| Purpose | archival / print | mobile feed |
| Map frame | 0.800 of sheet width | **0.864 (+8%)** |
| Top-right metadata block | present | **removed** |
| Map labels | 12.5 pt land / 13.0 water | **15.0 / 15.5 (+20% / +19%)** |
| Legend class names | 12.0 pt | **15.0 pt (+25%)** |
| Legend percentages | 11.0 pt, soft grey | **13.2 pt (+20%), full ink** |
| Method text | two paragraph columns | **one statement** |
| Attribution on face | full citations + DOI + licence sentence | **one credit line** |
| Scale note | "equal-area projection; distance scale accurate to ±0.3%…" | **"Scale variation <0.3%"** |
| Full citations, DOI, licence text | on the sheet | in the master, PDF and `LICENSES.md` |

**The LinkedIn sheet is a re-composition, not a downsample.** The previous gate required the
LinkedIn asset to be derived from the master, which was right when the two differed only in
size — but larger type at the same pixel count cannot be reached by resampling. The
invariant that actually matters is preserved and is now checked by hash: **both sheets draw
the same scientific render**, recorded in each sheet's `.build.json` as
`map_render_sha256`. `qa_final_publication.py` fails if they diverge.

Class ordering by mapped share and the grouped treatment of the six classes below 0.02% are
unchanged, as are the `SOIL REFERENCE GROUPS` / `NON-SOIL` split, the HWSD Open Water
accounting class, and the separate Natural Earth water entry.

### Background outside Iran

`context_land_srgb` moved `#BFBAB2` → **`#D2CFC9`**. No soil palette colour was touched.

The value was measured, not picked. Lightening the surround helps Iran read as figure
against ground, but pushes the surround toward Calcisols (`#F2E8C6`, 16.8% of Iran, and a
class that reaches the border) and toward the paper:

| Candidate | L\* | ΔE00 vs Leptosols | ΔE00 vs Calcisols | ΔE00 vs paper |
| --- | --- | --- | --- | --- |
| `#BFBAB2` (previous) | 75.7 | 14.9 | 14.1 | 12.8 |
| **`#D2CFC9` (chosen)** | **83.2** | **20.0** | **11.5** | **7.6** |
| `#DCD9D3` | 86.8 | 22.2 | 10.5 | 5.2 |
| `#E8E5DE` | 91.0 | 24.8 | 9.6 | 2.6 |

`#D2CFC9` raises separation from the dominant Leptosols grey by a third while keeping
Calcisols above the ΔE00 ≥ 10 threshold used throughout the project and keeping the map
frame distinguishable from the paper. Anything lighter buys Leptosols contrast by spending
Calcisols contrast — inside Iran, where it matters more.

This is the one change that is baked into the render rather than the composition, so it
required a single Blender re-run of the accepted scene with no other parameter altered.

A related defect was found and fixed while doing it: the legend's "Outside Iran" swatch had
its colour **hard-coded** in the layout script, so it would have kept showing the old grey
after the render changed. Both non-soil swatches now read from `config/render_3d.yaml`.
