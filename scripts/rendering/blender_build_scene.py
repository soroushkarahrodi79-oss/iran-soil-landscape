"""Build the Iran soil-landscapes Blender scene and render the prototype variants.

Runs INSIDE Blender (bundled Python: numpy yes, GDAL/yaml no):

    blender --background --factory-startup \
        --python scripts/rendering/blender_build_scene.py -- --job <job.json>

Everything comes from the job file written by run_3d_prototype.py, which resolves
config/render_3d.yaml + the substrate metadata. Nothing is authored by hand in the
GUI, so the scene is reproducible: delete the .blend and re-run.

Scene architecture (the four layers of the gate):
  A. terrain geometry <- elev_mesh.npy (real metres; vertical exaggeration = object z-scale)
  B. soil surface     <- iran_render_basecolor.png, sampled CLOSEST so class colours never blend
  C. land mask        <- baked into the basecolor: outside Iran is neutral grey, never a soil colour
  D. water            <- iran_water_mask.png (Natural Earth), drives colour + roughness only

Colour management is set to Standard (not AgX): a view transform that re-grades the
image would shift the soil palette away from the authored, documented colours.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def argv_after_dashes() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def hex_to_linear(value: str) -> tuple[float, float, float, float]:
    """sRGB hex -> linear RGBA (Blender node colours are linear)."""
    h = value.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_terrain(job: dict) -> bpy.types.Object:
    """Grid mesh displaced by the real elevation array, in kilometres."""
    meta = job["inputs_meta"]
    mw, mh = meta["mesh"]["width"], meta["mesh"]["height"]
    ext_x, ext_y = meta["extent_km"]["x"], meta["extent_km"]["y"]
    elev = np.load(job["elev_npy"]).astype(np.float64)
    elev = np.nan_to_num(elev, nan=float(job["nodata_elev_m"]))
    if elev.shape != (mh, mw):
        raise SystemExit(f"elev array {elev.shape} != mesh {(mh, mw)}")

    # x_subdivisions=N yields N+1 vertices, so ask for mw-1/mh-1 to get exactly one
    # vertex per heightmap sample — anything else silently duplicates a row/column.
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=mw - 1, y_subdivisions=mh - 1, size=2.0)
    obj = bpy.context.active_object
    obj.name = "iran_terrain"
    me = obj.data
    if len(me.vertices) != mw * mh:
        raise SystemExit(f"grid has {len(me.vertices)} verts, expected {mw * mh} ({mw}x{mh})")

    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    # Map each grid vertex to its (row, col) from its position, so we never depend on
    # Blender's internal vertex ordering.
    col = np.rint((co[:, 0] + 1.0) / 2.0 * (mw - 1)).astype(np.int64).clip(0, mw - 1)
    row = np.rint((1.0 - (co[:, 1] + 1.0) / 2.0) * (mh - 1)).astype(np.int64).clip(0, mh - 1)
    px, py = ext_x / mw, ext_y / mh          # posting in km (vertices at pixel centres)
    co[:, 0] = -ext_x / 2.0 + (col + 0.5) * px
    co[:, 1] = ext_y / 2.0 - (row + 0.5) * py
    co[:, 2] = elev[row, col] / 1000.0        # metres -> km, 1x (exaggeration is object scale)
    me.vertices.foreach_set("co", co.ravel())

    # UVs straight from geometry: exact registration onto the shared render grid.
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    loop_v = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", loop_v)
    lx, ly = co[loop_v, 0], co[loop_v, 1]
    uvs = np.empty((len(loop_v), 2), dtype=np.float64)
    uvs[:, 0] = (lx + ext_x / 2.0) / ext_x
    uvs[:, 1] = (ly + ext_y / 2.0) / ext_y
    uv.data.foreach_set("uv", uvs.ravel())

    me.update()
    obj.data.shade_smooth()
    return obj


def build_material(job: dict) -> bpy.types.Material:
    s = job["surface"]
    mat = bpy.data.materials.new("iran_soil_surface")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    base = nt.nodes.new("ShaderNodeTexImage")
    base.image = bpy.data.images.load(job["basecolor_png"])
    base.image.colorspace_settings.name = "sRGB"
    base.interpolation = "Closest"          # categorical: class colours must never blend
    base.extension = "EXTEND"
    base.location = (-700, 200)
    nt.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])

    water = nt.nodes.new("ShaderNodeTexImage")
    water.image = bpy.data.images.load(job["water_png"])
    water.image.colorspace_settings.name = "Non-Color"
    water.interpolation = "Closest"
    water.extension = "EXTEND"
    water.location = (-700, -200)

    rough = nt.nodes.new("ShaderNodeMix")   # land vs water roughness only
    rough.data_type = "FLOAT"
    rough.location = (-350, -200)
    rough.inputs[2].default_value = float(s["land_roughness"])
    rough.inputs[3].default_value = float(s["water_roughness"])
    nt.links.new(water.outputs["Color"], rough.inputs[0])
    nt.links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    return mat


def build_unlit_material(job: dict) -> bpy.types.Material:
    """Pure emission of the class-ID texture: geometry test, not a picture.

    No sun, no shadow, no ambient, no BSDF. A rendered pixel is the class code itself, so
    any disagreement with the source raster is a geometric/UV fault and cannot be excused
    as shading. This is what separates registration accuracy from cartographic readability.
    """
    mat = bpy.data.materials.new("iran_class_id_unlit")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(job["class_id_png"])
    tex.image.colorspace_settings.name = "sRGB"
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def build_lighting(job: dict) -> bpy.types.Object:
    lig = job["lighting"]
    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = float(lig["sun_strength"])
    sun_data.angle = math.radians(float(lig["sun_angular_diameter_deg"]))
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)

    world = bpy.data.worlds.new("neutral_ambient")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = float(lig["world_strength"])
    bpy.context.scene.world = world
    return sun


def aim_sun(sun: bpy.types.Object, azimuth_deg: float, elevation_deg: float, reach_km: float) -> None:
    """Azimuth measured clockwise from north (+Y), elevation above the horizon."""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    towards_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    sun.location = towards_sun * reach_km
    sun.rotation_euler = (-towards_sun).to_track_quat("-Z", "Y").to_euler()


def build_camera(job: dict) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("prototype_cam")
    cam_data.type = "ORTHO"                 # perspective would vary map scale across the frame
    cam_data.clip_start = 1.0
    cam_data.clip_end = 40000.0
    cam = bpy.data.objects.new("prototype_cam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def place_camera(cam: bpy.types.Object, spec: dict, job: dict, distance_km: float) -> None:
    ext_x, ext_y = job["inputs_meta"]["extent_km"]["x"], job["inputs_meta"]["extent_km"]["y"]
    tilt = math.radians(float(spec["tilt_deg"]))
    view_dir = Vector((0.0, math.sin(tilt), -math.cos(tilt)))
    cam.location = -view_dir * distance_km
    cam.rotation_euler = (tilt, 0.0, 0.0)
    rx, ry = spec["resolution"]
    margin = float(spec["ortho_margin"])
    fit = spec.get("sensor_fit", "AUTO")
    cam.data.sensor_fit = fit
    if fit == "HORIZONTAL":
        # Deterministic: ortho_scale is the width, so render pixels map 1:1 onto grid
        # columns. Required for the ID pass, where a half-pixel drift would be the result.
        cam.data.ortho_scale = margin * ext_x
        return
    # ortho_scale spans the LONGER sensor axis (sensor fit AUTO)
    need_x = ext_x
    need_y = ext_y * math.cos(tilt) + 2.0 * job["max_relief_km"] * math.sin(tilt)
    cam.data.ortho_scale = margin * max(need_x, need_y * rx / ry)


def configure_render(job: dict) -> None:
    scene = bpy.context.scene
    r = job["render"]
    scene.render.engine = "CYCLES"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = bool(r["film_transparent"])
    scene.cycles.samples = int(r["samples"])
    scene.cycles.adaptive_threshold = float(r["noise_threshold"])
    scene.cycles.use_denoising = bool(r["use_denoise"])
    # This machine has a 2 GB GPU. Denoising on the GPU and untiled rendering exhaust it
    # partway through a multi-frame session, so denoise on the CPU and render in tiles.
    if hasattr(scene.cycles, "denoising_use_gpu"):
        scene.cycles.denoising_use_gpu = False
    scene.cycles.use_auto_tile = True
    scene.cycles.tile_size = int(r.get("tile_size", 512))
    # Standard, not AgX: the soil palette must render as authored in config/soil_palette.yaml
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


def enable_gpu() -> str:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            usable = [d for d in prefs.devices if d.type == backend]
            if not usable:
                continue
            for d in prefs.devices:
                d.use = d.type == backend
            bpy.context.scene.cycles.device = "GPU"
            return f"{backend}: {', '.join(d.name for d in usable)}"
        except Exception as exc:
            print(f"  GPU backend {backend} unusable: {exc}")
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def main() -> None:
    args = argv_after_dashes()
    job = json.loads(Path(args[args.index("--job") + 1]).read_text(encoding="utf-8"))

    clear_scene()
    t0 = time.time()
    terrain = build_terrain(job)
    terrain.data.materials.append(build_material(job))
    sun = build_lighting(job)
    cam = build_camera(job)
    configure_render(job)
    device = enable_gpu()
    print(f"SCENE built in {time.time() - t0:.1f}s | verts {len(terrain.data.vertices):,} | device {device}")

    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    results = []
    lit_material = terrain.data.materials[0]
    unlit_material = None
    world_bg = scene.world.node_tree.nodes["Background"]
    world_strength = world_bg.inputs["Strength"].default_value

    for spec in job["renders"]:
        cam_spec = job["cameras"][spec["camera"]]
        unlit = bool(spec.get("unlit"))
        if unlit:
            if unlit_material is None:
                unlit_material = build_unlit_material(job)
            terrain.data.materials[0] = unlit_material
            sun.hide_render = True
            world_bg.inputs["Strength"].default_value = 0.0
            scene.cycles.use_denoising = False        # denoising would blend class codes
            scene.cycles.pixel_filter_type = "BOX"    # no cross-pixel antialiasing:
            scene.cycles.filter_width = 0.01          # a blended edge is not a class
        else:
            terrain.data.materials[0] = lit_material
            sun.hide_render = False
            world_bg.inputs["Strength"].default_value = world_strength
            scene.cycles.use_denoising = bool(job["render"]["use_denoise"])
            scene.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
            scene.cycles.filter_width = 1.5
        terrain.scale.z = float(spec["exaggeration"])
        aim_sun(sun, spec["sun_azimuth_deg"], spec["sun_elevation_deg"], reach_km=8000.0)
        place_camera(cam, cam_spec, job, distance_km=12000.0)
        scene.render.resolution_x, scene.render.resolution_y = cam_spec["resolution"]
        scene.render.resolution_percentage = int(spec.get("percentage", 100))
        scene.cycles.samples = int(spec.get("samples", job["render"]["samples"]))
        path = out_dir / f"{spec['name']}.png"
        scene.render.filepath = str(path)
        t = time.time()
        used = scene.cycles.device
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as exc:
            # Out of VRAM: finish this frame on the CPU rather than losing the set.
            print(f"RENDER {spec['name']}: GPU failed ({exc}); retrying on CPU", flush=True)
            scene.cycles.device = "CPU"
            used = "CPU (GPU out of memory)"
            bpy.ops.render.render(write_still=True)
            scene.cycles.device = "GPU"
        dt = time.time() - t
        results.append({"name": spec["name"], "seconds": round(dt, 1),
                        "device": used, "file": str(path)})
        print(f"RENDER {spec['name']}: {dt:.1f}s [{used}] -> {path.name}", flush=True)

    terrain.scale.z = float(job["blend_exaggeration"])
    blend = Path(job["blend_out"])
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), relative_remap=True)
    print(f"BLEND saved: {blend} (terrain z-scale {job['blend_exaggeration']}x)")
    Path(job["result_out"]).write_text(json.dumps(
        {"device": device, "blender": bpy.app.version_string, "renders": results}, indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
