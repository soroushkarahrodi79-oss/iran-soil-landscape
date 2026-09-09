"""Drive the Blender 3D prototype: resolve config -> job -> renders.

Blender's Python cannot read YAML or the geospatial stack, so this script (run in the
project conda env) resolves config/render_3d.yaml plus the substrate metadata into a
single job JSON and hands it to scripts/rendering/blender_build_scene.py.

    python scripts/rendering/run_3d_prototype.py --set smoke
    python scripts/rendering/run_3d_prototype.py --set exaggeration
    python scripts/rendering/run_3d_prototype.py --set lighting --selected-exaggeration 2

Render sets
  smoke         2 frames, --percentage/--samples overrides — proves the scene, measures cost
  exaggeration  VERTICAL_EXAGGERATION_TEST 1x/2x/3x/4x in both cameras (= CAMERA_TEST)
  lighting      LIGHTING_TEST, sun elevation 22/40/58 deg, at the SELECTED exaggeration
  full          both of the above in one Blender session

The lighting set is deliberately separate: the exaggeration is chosen by looking at the
exaggeration set, not assumed in advance.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config/render_3d.yaml"
BLENDER_DIR = ROOT / "data/processed/render/blender"
OUT_DIR = ROOT / "outputs/proof/3d"
BLEND_OUT = ROOT / "blender/iran_soil_landscapes_prototype.blend"
DEFAULT_BLENDER = ROOT / "tools/blender-4.5.13-windows-x64/blender.exe"


def blender_exe() -> Path:
    exe = Path(os.environ.get("BLENDER_EXE", DEFAULT_BLENDER))
    if not exe.exists():
        raise SystemExit(f"Blender not found at {exe}; set BLENDER_EXE")
    return exe


def render_list(cfg: dict, which: str, selected: int,
                percentage: int = 25, samples: int = 16) -> tuple[list[dict], int]:
    lig = cfg["lighting"]
    az, el = lig["sun_azimuth_deg"], lig["sun_elevation_deg"]
    if which == "smoke":
        return ([{"name": f"smoke_{cam}", "camera": cam, "exaggeration": 3,
                  "sun_azimuth_deg": az, "sun_elevation_deg": el,
                  "percentage": percentage, "samples": samples}
                 for cam in ("topdown", "oblique")], 3)

    renders = []
    if which in ("exaggeration", "full"):          # VERTICAL_EXAGGERATION_TEST + CAMERA_TEST
        for k in cfg["exaggeration_tests"]:
            for cam in ("topdown", "oblique"):
                renders.append({"name": f"iran_3d_{k}x_{cam}", "camera": cam, "exaggeration": k,
                                "sun_azimuth_deg": az, "sun_elevation_deg": el})
    if which in ("lighting", "full"):              # LIGHTING_TEST at the SELECTED exaggeration
        for v in lig["variants"]:
            renders.append({"name": f"iran_3d_light_{v['name']}_{selected}x_topdown",
                            "camera": "topdown", "exaggeration": selected,
                            "sun_azimuth_deg": v["azimuth_deg"], "sun_elevation_deg": v["elevation_deg"]})
    return renders, selected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="which",
                    choices=("smoke", "exaggeration", "lighting", "full"), default="smoke")
    ap.add_argument("--selected-exaggeration", type=int, default=2,
                    help="exaggeration used for the lighting test and saved in the .blend")
    ap.add_argument("--only", default=None,
                    help="render only frames whose name contains this substring (resume a set)")
    ap.add_argument("--percentage", type=int, default=25, help="smoke set: resolution percentage")
    ap.add_argument("--samples", type=int, default=16, help="smoke set: Cycles samples")
    args = ap.parse_args()

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    meta = json.loads((BLENDER_DIR / "blender_inputs.json").read_text(encoding="utf-8"))
    renders, selected = render_list(cfg, args.which, args.selected_exaggeration,
                                    args.percentage, args.samples)
    if args.only:
        renders = [r for r in renders if args.only in r["name"]]
        if not renders:
            raise SystemExit(f"--only {args.only!r} matched no frame in set {args.which!r}")
    max_exag = max(r["exaggeration"] for r in renders)

    job = {
        "elev_npy": str(BLENDER_DIR / "elev_mesh.npy"),
        "basecolor_png": str(BLENDER_DIR / "iran_render_basecolor.png"),
        "water_png": str(ROOT / "data/processed/render/iran_water_mask.png"),
        "inputs_meta": meta,
        "surface": cfg["surface"],
        "lighting": cfg["lighting"],
        "cameras": cfg["cameras"],
        "render": cfg["render"],
        "nodata_elev_m": cfg["mesh"]["nodata_elev_m"],
        "max_relief_km": meta["elevation_m"]["max"] / 1000.0 * max_exag,
        "renders": renders,
        "out_dir": str(OUT_DIR),
        "blend_out": str(BLEND_OUT),
        "blend_exaggeration": selected,
        "result_out": str(BLENDER_DIR / f"render_results_{args.which}.json"),
    }
    job_path = BLENDER_DIR / f"job_{args.which}.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")

    cmd = [str(blender_exe()), "--background", "--factory-startup", "--python",
           str(ROOT / "scripts/rendering/blender_build_scene.py"), "--", "--job", str(job_path)]
    print("running:", " ".join(cmd[:2]), "...", job_path.name, flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    keep = ("SCENE", "RENDER ", "BLEND", "Error", "error", "Traceback", "Warning: ")
    for line in proc.stdout.splitlines():
        if line.startswith(keep) or "Error" in line or "Traceback" in line:
            print(line)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-4000:] + "\n" + proc.stderr[-4000:] + "\n")
        raise SystemExit(f"blender exited {proc.returncode}")
    print(json.loads(Path(job["result_out"]).read_text(encoding="utf-8"))["device"])


if __name__ == "__main__":
    main()
