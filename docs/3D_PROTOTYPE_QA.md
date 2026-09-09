# 3D cartographic prototype — QA record

Gate: `3D_CARTOGRAPHY_PROTOTYPE` (base `72435f5`, checkpoint `data-gate-v1`; substrate `1dd9962`).
Status: **render substrate built, Blender scene built and rendered — prototype produced.**

The previous pass produced the deterministic **render substrate**; it was blocked on the
renderer itself. This pass installs Blender, builds the scene **by script**, and runs the
three controlled comparisons the gate requires (vertical exaggeration, camera, lighting).

## Toolchain (added this gate)

| Item | Value |
| --- | --- |
| Renderer | **Blender 4.5.13 LTS**, portable build, `tools/blender-4.5.13-windows-x64/` |
| Provenance | `download.blender.org/release/Blender4.5/` |
| Integrity | SHA256 `b5fdf800ce65fa2f209e8f68d02667e4d720fa1c42f247c72d1882ab04decba6`, **verified against the publisher's `blender-4.5.13.sha256` manifest** |
| Install type | Portable ZIP extracted in-repo (no system install, no admin, reversible by deleting `tools/`); gitignored |
| Engine | **Cycles**, GPU via CUDA on the NVIDIA MX130 |
| Storage at gate | ~18.4 GB free at start (**passes the 10 GB hard floor and the 15–20 GB preferred band**) |

EEVEE was rejected: it renders headless here only through a software-GL fallback
(105 s for a 64×64 test frame versus 2.1 s for Cycles on the GPU). Cycles is also the
physically-based choice, so shading is a light-transport result rather than a stylised effect.

## Frozen input integrity (re-verified this gate)

`sha256sum -c` — all five products **OK, unchanged**:
`iran_hwsd_mapping_units.tif`, `iran_dominant_soil_group.tif`, `soil_groups_iran.csv`,
`iran_boundary.gpkg` (soil_truth_frozen_2026-09-08.txt) and `iran_dem_90m.tif`
(dem_frozen_2026-09-09.txt). **No soil geography was touched by any render step.**

## Scene architecture (scripted, never hand-authored)

`scripts/rendering/blender_build_scene.py` builds the whole scene from
`config/render_3d.yaml` + the frozen substrate. The `.blend` is an *output*, not a source:
delete it and re-run to get it back identically.

| Layer | Source | Implementation |
| --- | --- | --- |
| A. Terrain geometry | `iran_heightmap_prototype.tif` → `elev_mesh.npy` | grid mesh, **one vertex per heightmap sample** (1536 × 1393 = 2,139,648 verts, ~1.17 km posting), z = real metres / 1000 |
| B. Soil surface | `iran_soil_texture.png` → `iran_render_basecolor.png` | image texture, **`Closest` interpolation** |
| C. Land mask | soil-texture alpha | baked into the basecolor: outside Iran is neutral grey, never a soil colour |
| D. Water | `iran_water_mask.png` (Natural Earth) | drives water colour + roughness only; **never merged into HWSD** (D-012) |

Units: 1 Blender unit = 1 km, so the map is modelled at true horizontal scale
(1796 × 1629 km) and exaggeration is a single explicit multiplier.

### Decisions that protect the science

- **`Closest` texture sampling.** Bilinear sampling would interpolate *between class
  colours* and invent soil colours that correspond to no class. Locked by test.
- **`Standard` view transform (not AgX/Filmic).** Blender's default view transform
  re-grades colour; the documented palette must reach the image as authored. Locked by test.
- **Orthographic cameras.** A perspective camera varies map scale across the frame.
- **Exaggeration as object z-scale.** The geometry holds real metres; no exaggeration is
  ever baked into the heightmap or the DEM.
- **Neutral context outside Iran.** Terrain beyond the border is rendered grey rather than
  extrapolating soil, and that grey is tested not to collide with any palette colour.

## Reproduction

```bash
python scripts/rendering/prepare_blender_inputs.py
python scripts/rendering/run_3d_prototype.py --set exaggeration
python scripts/rendering/run_3d_prototype.py --set lighting --selected-exaggeration <k>
python scripts/rendering/build_prototype_sheets.py --selected-exaggeration <k>
```

## Vertical exaggeration test — measured, not eyeballed

Terrain shading multiplies the soil palette, so for every pixel inside Iran the shading
multiplier is recoverable as `luminance(render) / luminance(flat palette colour)`. That
turns the choice into two competing measurements over identical pixels
(`scripts/validation/qa_3d_prototype.py` → `provenance/metadata/prototype_3d_qa.json`):

- **Relief contrast** = `std(shading)` — how much landform information the render carries.
- **Shadow burden** = share of pixels with `shading < 0.5` — how much soil colour is crushed.

Thresholds were fixed **before** measuring (relief ≥ 0.060, shadow ≤ 0.020) so the choice
could not be reverse-engineered, and the rule is *the lowest exaggeration meeting both*.

| Exaggeration | Relief contrast | Shadow burden | Verdict |
| --- | --- | --- | --- |
| 1× | 0.0334 | 0.0000 | relief too low |
| 2× | 0.0590 | 0.0001 | relief too low (misses by 0.001) |
| **3×** | **0.0838** | **0.0016** | **PASS — selected** |
| 4× | 0.1076 | 0.0066 | passes, but 4× the terrain distortion for no legibility need |

**A measurement error was found and fixed during this test.** The first run measured every
Iran pixel and selected 1×, contradicting what the images plainly showed. The cause was
class-boundary pixels: where the palette changes, a one-pixel disagreement between the
resampled palette and the render produces a huge luminance ratio unrelated to terrain.
That contamination is identical at every exaggeration, so it put a floor under the
statistic — it inflated 1× from 0.0334 to 0.0821 and made a nearly flat render look like
it carried relief. Restricting the measurement to pixels whose palette colour is locally
constant (7.9% of pixels excluded) removed it. **The thresholds were not touched**; fixing
the metric, not the threshold, changed the answer.

**Honest caveat:** 2× reaches 0.0590 against a 0.060 threshold — it misses by under 2%.
The 2×/3× distinction is effectively a tie at the threshold, and 2× is defensible if
minimum terrain distortion is preferred. 3× is reported as selected because the rule was
fixed in advance and applied as written.

## Camera test — top-down selected

Both cameras are orthographic, so neither adds perspective convergence. The oblique's
gain and cost are exactly calculable at national scale:

- **Gain:** at 3×, Iran's highest summit rises **17.4 px** in a 2500 px-wide frame. The
  entire relief silhouette the oblique buys is under 1% of the frame.
- **Cost:** north–south scale is multiplied by **cos 55° = 0.574**. The map loses its
  single scale, so areas can no longer be compared or measured — fatal for a soil map,
  where class extent is the point.

**Top-down is selected.** At 1800 km width, relief legibility comes from *shading*, not
from silhouette; the oblique pays 43% of the north–south dimension for 17 pixels of relief.
The oblique renders are retained as evidence for that conclusion, not as candidates.

## Registration verified on the finished render

"Exact by construction" is an argument, not evidence. Diffuse shading changes a pixel's
brightness but barely its chromaticity, so every rendered pixel can be classified back to
the nearest palette colour and compared with the class the substrate says belongs there —
testing mesh construction, UV mapping, texture sampling and rendering end to end.

**99.876%** of the 2,772,469 measured Iran land pixels still classify to their substrate
class (3,440 disagree, concentrated in deeply shaded slopes where chromaticity shifts).
No systematic offset. Locked by `test_render_still_shows_the_soil_class_the_substrate_says`.

## Lighting test — sun 40° NW selected

All three variants keep the NW azimuth (315°): light from the upper left is the
cartographic convention that prevents the relief-inversion illusion, so azimuth was held
fixed and only elevation varied. Judged by the same shading statistic as the exaggeration
test, at 3× top-down:

| Variant | Sun elevation | Relief contrast | Shadow burden | Verdict |
| --- | --- | --- | --- | --- |
| low | 22° | 0.1007 | **0.0395** | most relief, but crushes 4% of Iran — ~2× over budget |
| **default** | **40°** | **0.0838** | **0.0016** | **selected** |
| high | 58° | 0.0617 | 0.0000 | safest, but washes the landforms out |

The 22° variant is the trap: it looks the most dramatic and scores highest on relief, while
quietly burying soil colour over an area the size of a province. Rule applied: *most relief
contrast among the variants that stay within the shadow budget.*

## Selected prototype

**`outputs/proof/3d/selected_prototype_3x_topdown.png`** (copy of `iran_3d_3x_topdown.png`)
— orthographic top-down, 3× vertical exaggeration, sun 40° NW, 2500 × 2267 px.

This is a **prototype**, not a final or publication map: no titles, legend, scale bar,
north arrow, attribution block or projection note, none of which this gate produced. It is
not a LinkedIn asset and no 6K/8K publication render was made.

## Cartographic QA

- **No invented soil boundaries.** Classes come from the frozen `iran_dominant_soil_group.tif`
  via nearest-neighbour only; `Closest` texture sampling means no rendered pixel carries a
  colour between two classes.
- **No class lost or added:** 16 classes in, 16 out, matching `soil_groups_iran.csv`.
- **No soil implied outside Iran:** context terrain is neutral grey, tested not to collide
  with any palette colour.
- **Water from an authoritative source** (Natural Earth), never from HWSD (D-012).
- **Palette survives shading** at the selected exaggeration: 99.876% class agreement.
- **No AI-generated content** anywhere in the pipeline.
- Refinement candidates carried forward (geography never changes): Leptosols-grey versus
  Regosols-tan separation under shadow, and a CVD check of tan versus pale-yellow. At 3×
  these two remain the closest pair on shaded slopes.

## Known limitations

- Mesh posting ~1.17 km (1536 × 1393 from a 4096 × 3714, ~438 m/px grid). Landform shape at
  national scale is preserved; individual valleys are not.
- Each decimation narrows the elevation range: source DEM −64…5588 m → render grid
  −34…5470 m → mesh −31…5190 m. Documented, never rescaled.
- **DEM nodata (4.5% of the grid, SRTM water voids) is rendered at 0 m.** Those pixels lie
  under the cartographic water layer, so nothing false is shown, but the geometry there is
  a rendering convenience, not measured elevation.
- A thin dark rim is visible at the outer edge of the terrain slab, and in the oblique views
  the slab edge reads as a cliff. Both are artefacts of the finite DEM bounding box, outside
  Iran, and would be masked in a finished map.
- The 2×/3× exaggeration decision is a near-tie at the threshold (see above).
- Renders are 2500 px; a publication render was deliberately not attempted.

## Rejected alternatives

- **EEVEE**: headless here only via a software-GL fallback — 105 s for a 64×64 frame versus
  2.1 s for Cycles on the GPU. Rejected for speed and for being less physically grounded.
- **Oblique camera as the deliverable**: rejected — 17.4 px of relief silhouette for a 43%
  north–south compression that destroys single-scale area comparison.
- **AgX/Filmic view transform**: rejected — it re-grades the documented soil palette.
- **Bilinear soil texture sampling**: rejected — it interpolates between class colours and
  invents soils that exist in no class.
- **Committing the `.blend` (214 MB) or the Blender build (~1.2 GB)**: rejected — both are
  regenerable; the scripts are the source of truth.
