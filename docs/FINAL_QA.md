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

Separately, on the finished shaded map: **99.934%** of 2,772,469 Iran land pixels still
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
lightness to stay informative. The corrected figure, 99.934%, is *better* than the
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
| 17 | LinkedIn asset derived from the master | PASS — 2160 × 2700 Lanczos downsample |
| 18 | Geographic name spellings | PASS — reviewed against the label list |
| 19 | Geometric registration, unlit | PASS — 100.0000%, offset (0,0) |
| 20 | Shaded class readability, published map | PASS — 99.934% (CIELAB) |
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
