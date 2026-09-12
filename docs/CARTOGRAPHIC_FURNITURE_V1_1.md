# Cartographic furniture v1.1 — what changed, and what was measured before it changed

Gate: `CARTOGRAPHIC_FURNITURE_V1_1`, branch `design/cartographic-furniture-v1.1`, base
`bba283f`.

## Why this gate existed

The science was accepted and closed. What was not finished was the **sheet**: v1.0 was a
correct map sitting in a layout that had been assembled rather than designed. Three things
were wrong in ways that a reader would meet before they met the data.

1. **The map had no defined field.** It floated on the paper. The ground outside Iran
   (`#D2CFC9`) and the paper (`#F4F1EA`) are only ΔE00 7.6 apart, so the sheet had no edge.
2. **A sea label was drawn over land.** "Gulf of Oman" verified its anchor on Natural Earth
   water and was then nudged 2.8% of the frame upward to escape the bottom edge — which put
   the drawn text on the Makran coast. v1.0 verified the anchor and never looked at the text.
3. **Nothing shared a rail.** The map frame started at 0.068 of the sheet width; the title,
   legend, method and attribution all started at 0.055. A 1.3% step — 28 px at 2160 — that
   nothing justified.

Plus a factual slip in the legend: the rare-class note printed the *grouping threshold*
(0.05%) as though it described the classes, when the largest of the six is 0.015%.

## What was frozen

Everything scientific, and it is checked by hash rather than asserted.

| Frozen | Where it is checked |
| --- | --- |
| Scientific render `iran_map_2x_topdown_5400x4897.png` | `provenance/checksums/scientific_render_frozen_2026-09-12.txt`, `test_scientific_render_unchanged_by_a_composition_gate` |
| Soil truth, DEM | the existing 2026-09-08 / 2026-09-09 freeze files |
| Class IDs, class list, area statistics | `test_exact_class_statistics_are_unchanged`, `qa_final_publication.py` |
| Projection, orthographic camera, 2× exaggeration, registration | untouched inputs; ID-pass QA re-run |
| Palette | `qa_palette_residual.py` verdict, enforced by test |
| Water and boundary geometry | untouched; the boundary is read only to *measure* a keyline that was then rejected |

No Blender re-render was needed or made. The render hash is byte-identical to the one v1.0
published: `bf29af3c1c19854a…`. Every candidate sheet records that hash in its build file.

## A, B, C — three directions over one render

| | A — ACADEMIC MINIMAL | B — EDITORIAL CARTOGRAPHY | C — EXHIBITION POSTER |
| --- | --- | --- | --- |
| Title | 46 pt semibold, tracking 0.030 | **54 pt bold, tracking 0.020** | 60 pt bold, tracking 0.045 |
| Neatline | 1.6 pt @ 0.40 | **2.4 pt @ 0.55** | 3.0 pt @ 0.70, double |
| Legend lead tier | 15.0 pt | **16.5 pt** | 17.5 pt |
| Title rule | 0.9 pt | **1.4 pt** | 2.2 pt |
| Scale bar height | 0.0060 | **0.0085** | 0.0110 |
| Measured neatline contrast at 540 px | ΔL\* 17.8 | **ΔL\* 30.2** | ΔL\* 39.4 |

All three sit on the same grid, the same map frame (0.864 of sheet width), the same map
share of sheet height (0.627), and the same nine verified labels. Only furniture differs.

### Scorecard (1–5)

| | A | B | C |
| --- | --- | --- | --- |
| Soil-first hierarchy | 5 | 5 | 4 |
| Cartographic authority | 3 | 5 | 4 |
| Mobile readability | 3 | 5 | 5 |
| Legend scanability | 3 | 5 | 5 |
| Map-label readability | 4 | 4 | 4 |
| Figure / ground | 2 | 5 | 5 |
| Furniture integration | 4 | 5 | 3 |
| Scientific restraint | 5 | 5 | 3 |
| Editorial quality | 3 | 5 | 4 |
| Low visual clutter | 5 | 4 | 3 |
| **Total** | **37** | **48** | **40** |

**Selected: B — EDITORIAL CARTOGRAPHY.**

A loses on the only thing it was asked to prove: its 1.6 pt neatline is 0.60 px at 540 and
reads at ΔL\* 17.8, which is present but no longer a decision — the map still half-floats,
and the flat legend gives Leptosols' 40.7% the same weight as Fluvisols' 0.3%. C is not bad
— its numbers are fine and its type is the most readable of the three — but the double
keyline reads as a *card* rather than a neatline, which is the anti-pattern this gate was
explicitly told to avoid, and a 60 pt title at feed size starts competing with the map for
the first fixation. B is the only one where the furniture is strong enough to be noticed
and quiet enough not to be.

Proof sheets: `outputs/proof/furniture_v11/comparison_A_B_C_540x675.png` and
`comparison_v1_0_vs_v1_1_540x675.png`.

## Map frame / neatline

A single keyline around the map frame, **2.4 pt, ink at 55%**, no shadow, no rounding, no
second line.

The weight came from the feed test, not from print habit. At 2160 px one point is 1.5 px and
the sheet is judged at 540 px, so 1 pt is 0.375 px there — below a pixel. Three weights were
composed and then *read back out of the downsampled image* rather than assumed:

| Weight | px at 540 | measured ΔL\* against the paper at 540 |
| --- | --- | --- |
| 1.6 pt (A) | 0.60 | 17.8 — present, but not a decision |
| **2.4 pt (B)** | **0.90** | **30.2 — a defined field** |
| 3.0 pt double (C) | 1.13 | 39.4 — a box |

The archival master takes the print weight, 1.2 pt, because it is read at size.

## Figure / ground — and why there is no national boundary stroke

The brief allowed a subtle national keyline if it improved silhouette recognition. It was
built, drawn from the project's own Natural Earth geometry, simplified to one render pixel
(438 m) so it could not imply a boundary position finer than its source — and then
**rejected on measurement** (`qa_keyline_decision.py`).

**The gain that was available.** Iran's border ring — the 21,157 render pixels that actually
touch the outside — separates from the ground outside Iran at mean ΔE00 22.1, 10th
percentile 11.5, with **0.0% of the ring below the project's ΔE00 ≥ 10 threshold**. The
silhouette already reads. (Iran's *mean* soil surface against the surround is ΔE00 11.85,
ΔL\* 13.65 — also above threshold.)

**The bill.** Iran's outline is 8,374 km long at this simplification.

| Stroke | px at 540 | resolves at feed size? | ground width | inside HWSD's ~1 km support? | soil under the stroke |
| --- | --- | --- | --- | --- | --- |
| 0.6 pt | 0.23 | no | 0.86 km | yes | 7,176 km² (0.45%) |
| 0.9 pt | 0.34 | no | 1.29 km | no | 10,764 km² (0.67%) |
| 1.2 pt | 0.45 | no | 1.71 km | no | 14,352 km² (0.89%) |
| 1.6 pt | 0.60 | no | 2.29 km | no | 19,137 km² (1.19%) |
| 2.0 pt | 0.75 | no | 2.86 km | no | 23,921 km² (1.48%) |

There is no width that both survives the feed reduction (needs ≥ 2.27 pt) and stays inside
HWSD's native support (needs ≤ 0.7 pt). A visible stroke would have tinted ~1% of mapped
Iran — the outermost, most contact-sensitive band — to sharpen an edge that is already
sharp. **Rejected.** The side-by-side crops
(`keyline_proof_keyline_on_nw_corner.png` / `…_off_…`) show the two as effectively
indistinguishable, which is the same answer the numbers give.

The measured polylines stay in `map_furniture_qa.json`, so the decision can be re-run rather
than re-argued. A stroke clipped to the *outside* of the boundary would cost no soil pixels
and is the only version worth revisiting.

## Title

Unchanged words: **SOIL LANDSCAPES OF IRAN** / *Terrain, climate and the geography beneath
our feet*. 54 pt bold with **0.020 em of real tracking**, subtitle 21 pt, a 1.4 pt rule at
45% spanning the map measure, all on the map's left rail.

v1.0 reached for `fontstretch="expanded"` as a letter-spacing stand-in, which asks the font
for a wider *design* rather than wider spacing and silently does nothing when that design is
absent. v1.1 places glyphs at measured advances (`tracked()` in `build_poster.py`), so
tracking is a real number of ems and prefix kerning is preserved. The same mechanism now
spaces the physical-feature labels.

No new fonts. Segoe UI, resolved at runtime, never redistributed.

## Legend

Two tiers, chosen by the data rather than by eye: classes at or above **10% of Iran** lead.

```
Leptosols 40.7%   Regosols 18.7%   Solonchaks 18.6%   Calcisols 16.8%     16.5 pt, bold %
Arenosols 2.1%  Cambisols 1.5%  Gleysols 0.5%  Technosols 0.4%  Fluvisols 0.3%   14 pt
```

That puts 94.7% of the mapped country in the reader's first fixation and leaves Arenosols at
the head of the second tier instead of lost in a flat row of nine. Nothing is greyed out: a
smaller row is a lower information priority, not a claim that the class matters less.

**Percentages are paired, not stranded.** v1.0 right-aligned each percentage to an
equal-column rail that had nothing to do with its class name, so "Leptosols" and "40.7%" sat
a thumb apart. v1.1 measures the block — swatch, widest name, widest percentage — and
distributes the blocks evenly across the measure, so name and value stay a fixed short gap
apart while the percentage edges still fall on an even rhythm and the last block is flush to
the right rail.

Legend swatch colours are still read from `config/` and never hard-coded; the test that
caught that defect in the previous gate now also guards the v1.1 legend.

## Rare classes

Was: `Also mapped, each below 0.02% of Iran: …` at 11 pt, soft grey — easy to lose, and in
the last build it printed **0.05%**, the grouping threshold, not a figure any of the six
classes meets.

Now: a semibold lead in full ink at 13.5 pt, with the bound **derived from the classes**
(largest minor share, 0.015%, rounded up):

> **Minor mapped RSGs (each <0.02% of Iran)**  Kastanozems, Gypsisols, Luvisols, Histosols,
> Chernozems, Acrisols · combined 0.027%

5.1 px at 540, above the 4.6 px minimum. No extra swatches: six classes that are invisible
at publication scale do not get six chips.

## Non-soil

Three entries, subordinate to the soil legend (13 pt against 16.5, smaller swatches, a
hairline rule above, heading in `INK_MID`), but in full ink and on the same rail.

Cartographic water `#6E93B8` and the HWSD Open Water swatch `#4E79A7` are ΔE00 **9.73**
apart — measurably close, and they *should* be: both depict water. What separates them is
provenance, so the separation is carried in type, in one em-dash construction so the row
reads as three statements of the same kind:

```
Open Water — HWSD accounting class    Seas and lakes — Natural Earth cartography    Outside Iran — no soil data shown
```

A display-colour change to pull them apart would require re-rendering the frozen map for no
cartographic gain, and would make two depictions of water look like different substances.

## Scale bar

Kept — it was justified by measurement in the previous gate and that measurement is
unchanged: 71 sample pairs, planar/geodesic ratio 0.99825–1.00274, worst deviation 0.274%.
The note still says **"Scale variation <0.3%"**, not "exact".

Improved in execution: labels 9.5 → **14 pt** (5.25 px at 540, previously 3.56 px and
illegible), a real tick hierarchy (full ticks and labels at 0/200/400 km, half-height ticks
at the quarters), bar height 0.006 → 0.0085 of the axes, an outline around the whole bar so
the white half reads against the light ground, and a paper halo behind every label.

## North indicator

Kept, redesigned, and moved. v1.0 placed it at x = 0.963 of the axes, so half of it hung in
the page margin; it is now inset to 0.920 and sits inside the cartographic field, balancing
the scale bar opposite. Needle and "N" at 15 pt bold with a halo, arrow weight 1.4 → 2.0 pt.

Option C (drop it) was considered and rejected: the sheet has no graticule, so the arrow is
the only orientation statement on it. The caption is the honest version of what one arrow
can claim in an azimuthal projection with measured convergence up to 5.79°:

> grid north ±6°

## Map labels

Nine labels, same nine features, same verified anchors — including Gulf of Oman at
(59.3°E, 25.3°N), which did **not** move.

What changed is that the **drawn text** is now measured too, not just the anchor. Each label
is scored on three things, and an offset is *searched for* rather than nudged — the smallest
displacement from the verified anchor that satisfies every constraint wins, and offset (0,0)
is evaluated first so a good placement is never disturbed:

* clearance from the drawn map edge, measured in the **cropped** frame the reader actually
  sees (the sheet trims 1.5% per side, which pushes every label that much closer to the edge
  than the raw frame fraction suggests) — floor 0.030
* class-edge density under the text box, from the flat base colour — ceiling 0.040
* for a sea label, whether the text still lands on the water body it names, inside a
  longitude window that keeps Gulf of Oman east of the Strait of Hormuz

Seven of the nine were already clear and did not move. Two did:

| Label | Why it moved | Result |
| --- | --- | --- |
| **Gulf of Oman** | edge clearance −0.004 (the text box was outside the drawn frame), clutter 0.060, **and the drawn text was not on water at all** | 221 km west-north-west along its own sea to 57.16°E; clearance 0.033, clutter 0.015, on verified water |
| **Lake Urmia** | edge clearance 0.027 below the 0.030 floor, clutter 0.050 over the 0.040 ceiling | 99 km south-east onto the quiet Calcisols ground beside the lake; clearance 0.060, clutter 0.012 |

No leader lines were needed. Land labels are spaced semibold caps (real tracking now, 0.085
em); water labels stay italic in `#2F5D82`, the long-standing convention for hydronyms.

## Water

Audited, unchanged. Cartographic water separates from every soil class by ΔE00 ≥ 14.75
(worst: Gleysols, a teal 0.5% class), from the ground outside Iran by 26.4, and from the
paper by 32.2. It reads as base geography. No display-colour change was made, so no
re-render was required.

## Palette residual — kept, and this time it was searched, not asserted

The one documented limitation (Arenosols / Solonchaks: ΔE00 38.1 but ΔL\* only 4.4, so a
greyscale reproduction loses the boundary) was re-tested rather than re-stated.
`qa_palette_residual.py` searches lightness-only moves — hue and chroma held in CIELCh, so
class identity survives — across ±9 L\* for both classes in 0.5 steps, 1,368 candidates:

| Outcome | Count |
| --- | --- |
| out of sRGB gamut | 0 |
| did not reach ΔL\* ≥ 8 | 855 |
| created a new high-contact ΔE00 failure | 0 |
| regressed under the deepest measured 2× shading | 0 |
| **regressed some other pair** | **513** |
| **acceptable** | **0** |

The decisive constraint is the last one, and it needed two corrections to be honest. The
first version of the search only forbade *new* low-luminance pairs, which let a candidate
"pass" by taking lightness out of a pair that was already the weakest on the sheet — so the
rule became per pair: a pair above the floor may not be pushed below it, and a pair already
below may not be pushed lower. The second version ignored the two display surfaces
altogether; cartographic water and the ground outside Iran are not soil classes and so are
absent from the ID raster's adjacency, yet every coastal and border class is drawn against
them. Their contact is now measured and they are scored like any other neighbour.

With both corrections, every candidate that reaches the ΔL\* target pays for it somewhere
else — most often Arenosols/Regosols (358 candidates, from darkening Arenosols toward
Regosols' L\* 68.0), then Calcisols/Solonchaks and Solonchaks/Outside Iran (from lightening
Solonchaks toward the surround's L\* 83.2, which would have merged salt flats into "no soil
data shown" in greyscale).

**Verdict: KEEP_EXISTING_PALETTE.** The residual stands as documented. It is also worth
being clear about what it is: amber and pink at ΔE00 38.1 are unmistakable to anyone looking
at the map, and the limitation only bites in a greyscale reproduction of a 2.1% class
against an 18.6% one.

## Method strip

Same sentences, redesigned as a caption rather than body copy: a 1.2 pt rule at 30% across
the measure, then a **lead line in semibold full ink** carrying the claim that qualifies
every colour on the sheet, then the terrain qualification in `INK_MID` at the same size.

> **Dominant WRB-correlated soil groups from HWSD v2.01 (~1 km native support).**
> Terrain: SRTMGL3.003, vertically exaggerated 2× for visualization. Terrain detail does not
> increase soil-data resolution.

24 pt, 9.0 px at 540. Wrapping is by measured width, not by a guessed character count. No
card, no panel.

## Attribution

Unchanged text, 19 → **21 pt** (7.1 → 7.9 px at 540) and lifted from `INK_SOFT` `#5A6570` to
`INK_MID` `#3E4954` so it is read rather than recognised. Still one line, still on the rail,
still carrying the licence identifier the ShareAlike obligation requires on the face of the
image. Full citations with DOI remain on the master, in the PDF, and in `LICENSES.md`.

## Grid

One rail and one rhythm, both recorded in every build file.

| | Value |
| --- | --- |
| Left / right rail | 0.068 / 0.932 of sheet width — **the map frame's own edges** |
| Measure | 0.864 |
| Vertical rhythm | 0.0045 of sheet height (0.1125 in; 12.15 px at 2160) |
| Map share of sheet height | 0.627 |
| Legend headroom above the footer | +0.0045 |

Title, subtitle, title rule, map frame, legend heading, both legend tiers, the rare-class
note, the NON-SOIL block, the footer rule, the method caption and the attribution all start
at the same x. Every vertical stop is an exact multiple of the rhythm — `q()` snaps them and
`test_the_sheet_hangs_off_one_rail_and_one_rhythm` fails if any is off by more than 1e-6.
There are no unexplained nudges left in the layout.

The archival master keeps v1.0's 0.800 map frame, so the feed sheet's map stays 8% larger
than the archival one — a tested invariant that widening the master would have quietly spent.

## Mobile QA — 2160 × 2700 downsampled to 540 × 675, inspected, no zoom

| Requirement | v1.1 |
| --- | --- |
| Title immediately readable | yes — 20.2 px |
| Iran silhouette unmistakable | yes — neatline at ΔL\* 30.2 defines the field |
| Soils remain the visual subject | yes — map is 0.627 of sheet height |
| Top five groups readable | yes — 6.2 px lead tier, 5.2 px second |
| Top four percentages readable | yes — bold, paired with their names |
| Rare-class note readable | yes — 5.1 px semibold lead |
| All nine map labels readable | yes |
| Lake Urmia comfortably readable | yes — moved off the edge and off the busy ground |
| Gulf of Oman comfortably readable | yes — and now on water |
| Scale labels readable | yes — 5.25 px, was 3.56 px |
| NON-SOIL distinction understandable | yes — one em-dash construction, three provenances |
| Methodology readable | yes — 9.0 px |
| Attribution readable | yes — 7.9 px |

Every text element is measured against a minimum in `build_linkedin.py`; the nine furniture
elements this gate added are now measured too, and all fifteen clear.

## Desktop / master QA

Inspected at 2160 × 2700 at 100% and 50%, and the 6000 × 7500 master composed with PDF and
SVG. The furniture does not get heavy at size: the neatline drops to the print weight
(1.2 pt), the legend returns to archival proportions, and the master carries the full
two-column method paragraphs, the DOI, the licence sentence and the top-right metadata block
that the feed sheet delegates to the post text.

## Known residual limitations

1. **Arenosols / Solonchaks greyscale separation, ΔL\* 4.4.** Searched, no acceptable fix,
   documented above. Unchanged from v1.0.
2. **Cartographic water and the HWSD Open Water swatch are ΔE00 9.73 apart.** Deliberate —
   both depict water — and carried in type instead of colour.
3. **The Gulf of Oman is truncated by the DEM bounding box.** The label is now correctly on
   its own water, but at 57.16°E rather than over the centre of the feature, because the
   frame only keeps a 0.017-deep ribbon of that sea near the anchor. This is a property of
   the frozen render, not of the composition.
4. **The national keyline is rejected, not impossible.** A stroke clipped to the ground side
   of the boundary would cost no soil pixels; it was out of scope for a composition gate.
5. **The archival master is not independently proofed in print.** Weights are specified in
   points and are therefore physical, but no press proof was made.
6. **`MAP_CROP` is still 1.5% per side**, trimming the terrain slab's lit edge — a DEM-bbox
   artefact carried over from v1.0 and untouched here.

## Reproducing this gate

```
python scripts/rendering/build_map_furniture.py          # labels, scale, north, boundary
python scripts/rendering/build_furniture_variants.py     # A / B / C + both comparison sheets
python scripts/validation/qa_keyline_decision.py         # the keyline gain and bill
python scripts/validation/qa_palette_residual.py         # the greyscale residual search
python scripts/validation/qa_furniture_v11.py            # rules, figure/ground, water, grid, type
python scripts/rendering/build_poster.py --map <render> --width 2160 --layout v11_b \
    --out outputs/linkedin --name iran_soil_landscapes_v1_1_2160x2700
python scripts/rendering/build_linkedin.py --asset outputs/linkedin/iran_soil_landscapes_v1_1_2160x2700.png
python scripts/rendering/build_poster.py --map <render> --width 6000 --layout v11_master \
    --out outputs/master --name iran_soil_landscapes_v1_1_6000x7500 --vector
python scripts/validation/qa_final_publication.py
python -m pytest -q tests
```

`config/publication.yaml` declares which pair is published.

**On preserving v1.0.** Its published files stay on disk untouched, and its two layouts
(`master`, `linkedin`) still compose — including its own scale bar and north arrow, which
are kept in `_draw_furniture_v10()` rather than being silently upgraded, so a recomposition
shows what v1.0 actually looked like. `test_v1_0_layouts_still_compose` builds both, because
the first attempt at this gate broke them and only the claim in a document noticed.

A recomposition today is **not** byte-identical to the archived v1.0 files, and the
difference is worth stating rather than glossing: the shared map-drawing path now resamples
the render once in Pillow to the exact pixel width of the axes instead of handing matplotlib
a 5238 px image for an 1866 px frame (one Lanczos pass rather than two, and 677 MB less peak
memory at master size), and the label placements in `map_furniture_qa.json` are the corrected
ones — so a recomposed v1.0 draws "Gulf of Oman" where the evidence puts it rather than on
the Makran coast. The archived files remain the v1.0 of record.
