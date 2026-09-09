# 3D cartographic prototype — QA record

Gate: `3D_CARTOGRAPHY_PROTOTYPE` (base `72435f5`, checkpoint `data-gate-v1`). Status: **substrate built; Blender prototype BLOCKED (Blender not installed + tight disk).**

This gate produced the deterministic, verifiable **render substrate** (the layers Blender consumes) and a 2D **registration QA / terrain-enhanced proof**. The Blender scene, vertical-exaggeration/camera/lighting tests, and 3D renders are **not** produced — see Blocker.

## Storage hard gate

- Hard minimum 10 GB, preferred 15–20 GB. Measured **~12 GB free** at gate start (stable; an earlier 2 GB reading was transient Windows pagefile growth during DEM processing, since released). **PASS the 10 GB floor, below preferred.**
- Only drive is C: (no alternative working drive). Given the disk's demonstrated volatility under heavy compute (dropped to ~2 GB during DEM warp), installing Blender (~1.5 GB) and running renders would risk breaching the 10 GB floor at peak. See Blocker + Next gate.

## Frozen input integrity (re-verified this gate)

`sha256sum -c` before and after substrate build — all OK, unchanged:
`iran_hwsd_mapping_units.tif`, `iran_dominant_soil_group.tif`, `iran_boundary.gpkg`, `soil_groups_iran.csv` (soil_truth_frozen_2026-09-08.txt) and `iran_dem_90m.tif` (dem_frozen_2026-09-09.txt, `ae2ee5c6…`). No soil geography modified.

## Render substrate (data/processed/render/, all on ONE LAEA grid)

| Layer | File | Method |
| --- | --- | --- |
| A. Render heightmap (Int16, real elevation) | `iran_heightmap_prototype.tif` | downsample `iran_dem_90m.tif`, **bilinear** |
| A′. Displacement map (normalized) | `iran_heightmap_prototype_u16.png` | 0=elev_min … 65535=elev_max; nodata→0 |
| B. Soil ids on render grid | `iran_soil_ids_render.tif` | resample `iran_dominant_soil_group.tif`, **nearest** |
| B′. Soil texture | `iran_soil_texture.png` | palette colours, RGBA (alpha=0 outside Iran) |
| D. Cartographic water | `iran_water_mask.png` | NE `ne_10m_ocean`+`ne_10m_lakes`, clipped-then-LAEA rasterize |

- **Render grid:** LAEA (lat_0=32, lon_0=53), **4096 × 3714**, ~438 m/px. Long dim 4096 (prototype target 2048–4096).
- **Heightmap normalization:** the downsampled render heightmap spans ≈ −34 … 5470 m (the source DEM is −64 … 5588 m; bilinear downsampling averages away the extremes — expected for a render derivative, documented). Real elevation relationships preserved; **no exaggeration baked in** (exaggeration is a future Blender parameter).
- **Soil classes:** 16, exactly matching `soil_groups_iran.csv` (no class added). SOIL CLASS and DISPLAY COLOUR kept separate (`config/soil_palette.yaml`).
- **Water:** kept separate from HWSD (D-012); a local 42–66°E / 22–42°N clip before reprojection fixed an initial bug where the global ocean polygon distorted in Iran-centred LAEA and left the Persian Gulf empty.

## Registration QA — PASS

Because every layer is generated on the identical LAEA grid, registration is exact **by construction** (no manual texture nudging). Verified in `outputs/proof/3d/registration_qa_v01.png` at control regions:

| Region | Expectation | Result |
| --- | --- | --- |
| Caspian coast | Cambisols/Gleysols strip; Caspian water N of Alborz | ✓ |
| Lake Urmia | water + surrounding Solonchaks (salt lake) | ✓ |
| Khuzestan | lowland Solonchaks/Fluvisols; Gulf water SW | ✓ |
| Dasht-e Kavir | Solonchaks fill the low central basin | ✓ |
| Lut Desert | Solonchaks + playa water bodies | ✓ |
| Makran | SE ranges; Gulf of Oman water | ✓ |
| Zagros/Alborz | Leptosols trace the hillshaded ridges | ✓ |

No soil/terrain offset detected anywhere.

## Cartographic palette QA (`config/soil_palette.yaml`)

- **Perceptual separation:** the four dominants — Leptosols (grey), Regosols (tan), Solonchaks (pink), Calcisols (pale yellow) — read clearly; Solonchaks vs Calcisols separate well.
- **Terrain-shadow interaction:** soil colours survive the hillshade multiply (shading floored at 0.35 to avoid black crush). Good.
- **Class hierarchy:** the four dominants carry the map; minor classes (Cambisols brown, Gleysols teal, Fluvisols green, water blue) stay distinct.
- **Refinement candidates for the final (geography never changes):** (1) Leptosols grey vs Regosols tan can be close in deeply shaded areas — nudge lightness/hue apart; (2) CVD-test tan vs pale-yellow for deuteranopia. Recorded as future palette work, not a class change.

## NOT done this gate (require Blender)

Vertical-exaggeration test (1×/2×/3×/4×), camera test (top-down vs oblique orthographic), lighting test, the Blender scene (`blender/…prototype.blend`), and 3D prototype renders (`outputs/proof/3d/iran_3d_*.png`). All are unblocked the moment Blender is installed on a disk with adequate headroom — the substrate above is exactly their input.

## Known limitations

- Prototype heightmap ~438 m/px (national scale); a finer render heightmap is justified only if it yields visible benefit at final size.
- Downsampling narrows the elevation extremes slightly (documented).
- The 2D proof is a registration/terrain-enhanced check, not the 3D prototype.

## Rejected alternatives

- Installing Blender + rendering now: rejected this gate — disk (12 GB) is below the preferred 15–20 GB and has shown pagefile volatility under heavy compute, so a Blender install + render risks breaching the 10 GB hard floor. Deferred to the next gate after disk is increased.
- Deriving water from HWSD "Open Water": rejected (D-012) — HWSD water is non-soil accounting, not hydrography.
