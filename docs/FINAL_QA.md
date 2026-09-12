# Final QA record — publication gate

Gate: `FINAL_PUBLICATION_CARTOGRAPHY` (base `74b435c`). Machine-checked results live in
`provenance/metadata/final_publication_qa.json`; re-run with
`python scripts/validation/qa_final_publication.py`.

## The registration semantics were wrong, and are now fixed

The prototype gate reported **99.876%** and, in places, let that number stand near the word
*registration*. It is not a registration figure. It was measured on a **shaded** render, so
lighting, shadow and tone all entered it; the 3,440 disagreeing pixels were mostly deeply
shaded slopes whose chromaticity had shifted, not pixels in the wrong place. Reporting it as
spatial accuracy would have hidden any real geometric fault inside a lighting statistic.

The two questions are now measured separately, and reported separately.

### A. Geometric / UV registration accuracy — `UNSHADED_CLASS_ID_PASS`

The scene is re-rendered with every optical variable removed: a **pure emission** material
carrying a class-ID texture (evenly spaced grey levels, 15 apart), **1 sample**, **box pixel
filter width 0.01**, **no denoising**, **no sun**, **no ambient**, and a camera pinned to
one render pixel per grid cell (4096 × 3714, `sensor_fit HORIZONTAL`, no margin). A rendered
pixel is then the class code itself. It is decoded back to the source categorical raster
through the camera's own geometry — render pixel → world coordinate → grid cell — rather
than through an assumed identity mapping.

| Measure | Result |
| --- | --- |
| Pixels compared | 8,432,268 |
| **Exact class agreement** | **100.0000%** |
| Interior (non-boundary) agreement | 100.0000% over 7,978,382 px |
| Offset search, ±3 px in both axes | best offset **(0, 0)** — no offset present |
| Classes recovered | **16 / 16** |
| Encoding fidelity | max level error **1**, against a ±7 decode margin |

Mesh construction, UV mapping, texture sampling and rendering introduce **no spatial error
at all** at the render grid's resolution. This is a measurement, not the earlier "exact by
construction" argument.

### B. Shaded cartographic class readability

Separately, on the finished shaded map: **99.931%** of 2,772,469 Iran land pixels still
classify to their substrate class after 2x relief shading. This answers "can a reader still
tell which class this is once it is shaded?" — a legibility figure, not a spatial one.

This figure was **recomputed for the published map**. The prototype's 99.876% was measured
under the prototype palette and would have been a stale number to quote for a map whose
colours changed.

**A metric fault was found and fixed while recomputing it.** The prototype classified pixels
by chromaticity, which discards lightness. That places Chernozems (`#2B2B2B`, pure neutral,
6.7 km2 of Iran) only 0.0088 from Leptosols (`#8B8A83`) — closer than any real neighbour.
Since Leptosols is 40.7% of the map, the chromaticity metric reassigned a slice of the
country to an invisible class and reported **95.874%**, a readability failure no reader could
ever experience. Classifying in full **CIELAB** keeps lightness, which is exactly what
separates a mid grey from a near-black, and shading at 2x is mild enough (mean 0.978) for
lightness to stay informative. The corrected figure, 99.931%, is *better* than the
prototype's, as expected from a palette with larger inter-class separation.

## Final scientific QA — 21/21 machine-checked

| # | Check | Result |
| --- | --- | --- |
| 1 | Frozen soil hashes unchanged | PASS — 4 products |
| 2 | Frozen DEM unchanged | PASS |
| 3 | Render class IDs == frozen soil table | PASS — 16, none missing, none extra |
| 4 | Unsmoothed categorical geography | PASS — nearest resample, `Closest` sampling (locked by test) |
| 5 | Water separate from HWSD | PASS — Natural Earth layer, D-012 |
| 6 | 2× exaggeration disclosed on the map | PASS |
| 7 | Orthographic camera, no perspective distortion | PASS |
| 8 | Legend matches the actual raster classes | PASS — 16 listed = 16 present |
| 9 | No class absent from Iran displayed | PASS |
| 10 | Attribution complete | PASS — FAO/IIASA, NASA/USGS, Natural Earth |
| 11 | Licence notice complete | PASS — CC BY-NC-SA 4.0 on the map |
| 12 | No AI-generated geography | PASS — no generative step anywhere in the pipeline |
| 13 | No false fine-resolution soil implication | PASS — "~1 km" stated on the map |
| 14 | No unsupported scale-bar claim | PASS — 0.274% measured, tolerance printed |
| 15 | Publication claim ceiling respected | PASS — forbidden phrasings absent |
| 16 | Master lossless, 4:5, 6000 × 7500 | PASS |
| 17 | LinkedIn asset derived from the master | PASS at the time — **superseded** by D-020: the feed sheet is now composed from the same render, checked by hash |
| 18 | Geographic name spellings | PASS — reviewed against the label list |
| 19 | Geometric registration, unlit | PASS — 100.0000%, offset (0,0) |
| 20 | Shaded class readability, published map | PASS — 99.931% (CIELAB) |
| 21 | Palette: high-contact neighbours separable | PASS — none failing |

## Visual QA — human-scale inspection

| Scale | What was checked | Result |
| --- | --- | --- |
| 100% (master 1:1) | class edges, label legibility, terrain detail | Alborz ridges resolve cleanly; class edges are hard, showing the ~438 m raster honestly rather than smoothed; halo keeps labels readable over terrain |
| 50% (4000 px QA) | legend swatch separation, small-class visibility | all nine legend swatches distinguishable; Fluvisols (0.3%) and Technosols (0.4%) visible |
| Mobile (2160 px derivative) | title, 5-second comprehension, source text | title dominant, map reads as "soils of Iran with terrain" immediately; attribution small but legible |

Terrain does not outrank the soil classes at any scale: shading removes only 0.01% of soil
colour to deep shade at 2×, and colour, not relief, carries the map.

## Render sequence actually followed

Proof (2500 px) → QA (4000 px) → master (6000 × 7500). No render was attempted before the
smaller one had been inspected. Map renders: 2500 × 2267 (327 s), 3600 × 3264 (655 s),
5400 × 4897 (621 s), all on the GPU.

### GPU / memory safety

The MX130's 2 GB had already exhausted mid-session during the prototype gate. For this gate
the mitigations were in place from the start — CPU denoising, 512 px auto-tiles, and a
per-frame automatic CPU retry — and **no frame fell back to CPU and no batch was lost**.
Disk stayed between 13 and 15 GB free throughout, above the 10 GB floor.

## Residual limitations carried into publication

- Arenosols/Solonchaks are unmistakable in colour but close in luminance (ΔL\* 4.4): a
  greyscale reproduction would not separate them well.
- Four class pairs remain below the CVD threshold, all with ≤141 px of shared boundary
  between classes of ≤1.5% share (see `FINAL_CARTOGRAPHY.md`).
- The Gulf of Oman label sits at 98% of frame height because the DEM bounding box cuts
  through the gulf; only the text is offset, the anchor stays on verified water.
- DEM nodata (4.5% of the grid) renders at sea level beneath the water layer.
- Six classes below 0.02% of Iran are named in the legend but grouped, since each is
  individually invisible at map scale.

---

# LinkedIn visual polish gate (base `6f1319f`)

Typography, layout and mobile readability only. Soil geometry, soil IDs, DEM, water
geometry, projection, camera, 2× exaggeration, classification and statistics are untouched;
the frozen hashes re-verify unchanged in `qa_final_publication.py`.

## Mobile readability, measured then looked at

The requirement was legibility at ~540 × 675. That was tested, not assumed: the composed
2160 × 2700 sheet is reduced to 540 × 675 and every type size is converted to the pixel
height a reader actually gets there (`pt / 72 × dpi × 0.25`).

**The first attempt failed.** At the +20–25% uplift the gate specified, the title, map,
labels and the top four classes with percentages were readable, but the **methodology line
and the attribution were not** — 4.7 px and 4.5 px respectively. A 20–25% uplift is enough
for short bold labels and not enough for body copy at feed size, so those two were raised
further and the deviation is recorded here rather than hidden.

| Element | pt | px at 540 | Minimum | Verdict |
| --- | --- | --- | --- | --- |
| Title | 54 | 20.2 | 14.0 | ok |
| Map labels (land) | 15.0 | 5.6 | 5.0 | ok |
| Legend class name | 15.0 | 5.6 | 5.0 | ok |
| Legend percentage | 13.2 | 4.9 | 4.8 | ok |
| **Methodology line** | **24.0** | **9.0** | 8.5 | ok (raised beyond the 20–25% band) |
| **Attribution** | **19.0** | **7.1** | 6.5 | ok (raised beyond the 20–25% band) |

Visual confirmation at 540 × 675: title immediately readable; the map is clearly the
dominant element; ALBORZ, ZAGROS, DASHT-E KAVIR, LUT DESERT, KHUZESTAN PLAIN, Caspian Sea
and Persian Gulf all readable; the top four classes and their percentages readable; the
methodology line readable without zoom; the credit line recognisable.

**One honest marginal:** *Lake Urmia* and *Gulf of Oman* — the two smallest water labels,
both near a frame edge — are legible but tight at 540 px. The other seven labels are clear.
They were not enlarged further because the map-label size is already at the top of the
band the gate specified, and both sit over busy areas where a larger halo would cover data.

## Figure/ground

Outside-Iran terrain moved from `#BFBAB2` to `#D2CFC9`, raising ΔE00 against the dominant
Leptosols grey from 14.9 to 20.0 while keeping Calcisols at 11.5, above the project's
ΔE00 ≥ 10 threshold. No soil palette colour was altered. Full candidate table in
`FINAL_CARTOGRAPHY.md`.

A latent defect surfaced here: the legend's "Outside Iran" swatch had its colour
**hard-coded** in the layout script and would have kept displaying the superseded grey
after the render changed — a legend contradicting its own map. Both non-soil swatches now
read from `config/render_3d.yaml`, and `test_legend_non_soil_swatches_come_from_config`
fails if a colour literal reappears in the legend.

## Sheet architecture

The LinkedIn asset is now **composed**, not downsampled: larger type at the same pixel size
cannot be produced by resampling, so the previous gate's "derive from the master" rule no
longer expresses the right constraint. The constraint that matters is preserved and is now
machine-checked — **both sheets draw the same scientific render**, proven by
`map_render_sha256` in each sheet's `.build.json` (`bf29af3c1c19…` for both).

Map frame: 0.800 → 0.864 of sheet width (**+8.0%**, within the 8–12% asked).

## Machine-checked QA after this gate

`qa_final_publication.py` now runs **23 checks, all passing**, including three that did not
exist before: that both sheets draw the same render (by hash), that LinkedIn type clears its
feed-size minimum, and that the LinkedIn map frame is genuinely larger than the master's.
Shaded readability was recomputed against the re-rendered map: **99.931%**.

---

## CARTOGRAPHIC_FURNITURE_V1_1 — re-verification (2026-09-12)

Composition-only gate. Scientific integrity was checked before and after; nothing moved.

| Frozen artefact | Before | After |
| --- | --- | --- |
| Soil truth hashes | match | match |
| DEM hash | match | match |
| Scientific render `iran_map_2x_topdown_5400x4897.png` | `bf29af3c1c19854a…` | `bf29af3c1c19854a…` |
| Class list | 16 classes, no missing, no extra | same |
| Class shares (LP/RG/SC/CL/AR) | 40.7 / 18.7 / 18.6 / 16.8 / 2.1 | same |
| Registration (unlit ID pass) | agreement 1.000000, offset [0,0] | same |
| 2× exaggeration, orthographic camera, LAEA | unchanged | unchanged |
| Water geometry | unchanged | unchanged |
| Palette | 16 colours | unchanged (`KEEP_EXISTING_PALETTE`) |

`qa_final_publication.py`: **28/28 checks pass** (23 before this gate; five added here —
label edge clearance, the Gulf of Oman label on water, the keyline verdict, the palette
verdict, and that the published pair is the one `config/publication.yaml` declares).

`python -m pytest -q tests`: **52 passed** (35 before; 17 added in
`tests/test_furniture_v11.py`).

Shaded class readability on the published map, re-measured against the final palette:
**0.99931** over 2,772,469 px — unchanged, as expected from an unchanged render.

### Deviations recorded

* The national boundary stroke the gate permitted was **built and then rejected** on its own
  measurement rather than adopted. Reason and figures in
  `docs/CARTOGRAPHIC_FURNITURE_V1_1.md`; the decision is enforced by
  `test_national_keyline_follows_its_own_measurement`, which fails if the stroke is drawn
  while the verdict says otherwise, or vice versa.
* The palette residual the gate permitted to be adjusted was **searched and kept**. The
  search found zero acceptable candidates out of 1,368, and the verdict is enforced by
  `test_palette_is_unchanged_unless_the_residual_search_said_otherwise`.
* A graticule was not tested. The clutter standard the gate set (default: reject) and the
  fact that the sheet already carries a measured scale bar and a north indicator made it a
  cost with no stated benefit.
