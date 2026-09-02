#!/usr/bin/env python3
"""
AI & Natural Language Prompt-to-USD Scene Generator.
Converts text descriptions and architectural concepts into mathematically precise,
PBR-shaded OpenUSD (.usda) stages with lighting, materials, and physics schemas.
"""

import argparse
import math
import os
import re
import sys
from typing import Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from utils_usd import (
    create_stage,
    setup_physics_scene,
    create_pbr_material,
    bind_material,
    add_dome_light,
    add_distant_light,
    add_ground_plane
)

# Semantic Color Palette Dictionary
PALETTES = {
    "neon": {"diffuse": (0.05, 0.05, 0.08), "glow": (0.0, 0.9, 1.0), "accent": (1.0, 0.0, 0.6), "metal": 0.9, "rough": 0.2},
    "cyberpunk": {"diffuse": (0.08, 0.08, 0.12), "glow": (1.0, 0.85, 0.0), "accent": (0.0, 0.8, 1.0), "metal": 0.8, "rough": 0.25},
    "industrial": {"diffuse": (0.15, 0.16, 0.18), "glow": (1.0, 0.4, 0.0), "accent": (0.9, 0.5, 0.0), "metal": 0.85, "rough": 0.4},
    "scifi": {"diffuse": (0.1, 0.12, 0.15), "glow": (0.0, 0.8, 0.6), "accent": (0.2, 0.6, 1.0), "metal": 0.5, "rough": 0.3},
    "lunar": {"diffuse": (0.22, 0.22, 0.25), "glow": (0.4, 0.7, 1.0), "accent": (0.8, 0.8, 0.9), "metal": 0.1, "rough": 0.8},
    "gold": {"diffuse": (1.0, 0.84, 0.0), "glow": (0.9, 0.6, 0.0), "accent": (1.0, 0.9, 0.3), "metal": 0.95, "rough": 0.15},
    "emerald": {"diffuse": (0.05, 0.35, 0.15), "glow": (0.1, 0.9, 0.4), "accent": (0.0, 1.0, 0.5), "metal": 0.2, "rough": 0.1},
    "ruby": {"diffuse": (0.45, 0.05, 0.1), "glow": (1.0, 0.1, 0.2), "accent": (1.0, 0.3, 0.4), "metal": 0.3, "rough": 0.1}
}


def parse_prompt_keywords(prompt: str) -> Dict[str, any]:
    """Analyzes a text prompt and extracts design tokens, numbers, and themes."""
    p_lower = prompt.lower()

    # Theme selection (longer/specific themes first)
    theme = "scifi"
    for k in sorted(PALETTES.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(k) + r'\b', p_lower):
            theme = k
            break

    # Structure count
    nums = re.findall(r'\b(\d+)\b', p_lower)
    item_count = int(nums[0]) if nums else 8
    item_count = max(3, min(item_count, 32))

    # Architecture Archetype
    archetype = "colonnade"
    if "ring" in p_lower or "arena" in p_lower or "amphitheater" in p_lower:
        archetype = "arena"
    elif "tower" in p_lower or "spire" in p_lower or "city" in p_lower:
        archetype = "spires"
    elif "warehouse" in p_lower or "grid" in p_lower or "cargo" in p_lower:
        archetype = "grid"
    elif "pyramid" in p_lower or "temple" in p_lower:
        archetype = "temple"

    has_crystal = any(w in p_lower for w in ["crystal", "core", "gem", "floating", "sphere", "orb"])
    has_physics = any(w in p_lower for w in ["physics", "kinetic", "dynamic", "fall", "collapse", "domino"])

    return {
        "prompt": prompt,
        "theme": theme,
        "item_count": item_count,
        "archetype": archetype,
        "has_crystal": has_crystal,
        "has_physics": has_physics,
        "palette": PALETTES[theme]
    }


def generate_usd_from_prompt(prompt: str, output_path: str = "output_prompt_generated.usda") -> str:
    """Generates a complete OpenUSD stage from a natural language prompt."""
    spec = parse_prompt_keywords(prompt)
    pal = spec["palette"]

    print(f"[*] Prompt-to-USD: \"{prompt}\"")
    print(f"    - Theme: {spec['theme']} | Archetype: {spec['archetype']} | Elements: {spec['item_count']}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Hierarchies
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Materials")
    UsdGeom.Xform.Define(stage, "/World/Architecture")

    # Physics & Lighting
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=600.0, color=(0.85, 0.9, 1.0))
    add_distant_light(stage, "/World/Environment/KeyLight", intensity=3500.0, rotation_xyz=(-45.0, 35.0, 0.0))

    # Materials
    create_pbr_material(stage, "/World/Materials/M_Base", diffuse_color=pal["diffuse"], metallic=pal["metal"], roughness=pal["rough"])
    create_pbr_material(stage, "/World/Materials/M_Glow", diffuse_color=pal["glow"], emissive_color=pal["glow"], roughness=0.1)
    create_pbr_material(stage, "/World/Materials/M_Accent", diffuse_color=pal["accent"], metallic=0.4, roughness=0.2)

    # Ground Platform
    ground = add_ground_plane(stage, "/World/Environment/GroundPlane", size=3000.0)
    mat_ground = create_pbr_material(stage, "/World/Materials/M_Ground", diffuse_color=(0.08, 0.09, 0.11), roughness=0.6)
    bind_material(ground.GetPrim(), "/World/Materials/M_Ground")

    # Procedural Structure Generation based on Archetype
    count = spec["item_count"]

    if spec["archetype"] in ["arena", "colonnade"]:
        radius = 160.0
        for i in range(count):
            theta = (2 * math.pi * i) / count
            px = radius * math.cos(theta)
            pz = radius * math.sin(theta)

            p_path = f"/World/Architecture/Pillar_{i:02d}"
            p_geom = UsdGeom.Cylinder.Define(stage, p_path)
            p_geom.CreateRadiusAttr().Set(8.0)
            p_geom.CreateHeightAttr().Set(80.0)
            p_geom.CreateAxisAttr().Set("Y")

            p_xform = UsdGeom.Xformable(p_geom.GetPrim())
            p_xform.AddTranslateOp().Set(Gf.Vec3d(px, 40.0, pz))

            if spec["has_physics"]:
                UsdPhysics.RigidBodyAPI.Apply(p_geom.GetPrim())
                UsdPhysics.CollisionAPI.Apply(p_geom.GetPrim())
                UsdPhysics.MassAPI.Apply(p_geom.GetPrim()).CreateMassAttr().Set(5.0)

            bind_material(p_geom.GetPrim(), "/World/Materials/M_Base")

            # Emissive Ring Top
            ring_path = f"/World/Architecture/RingCap_{i:02d}"
            ring = UsdGeom.Cylinder.Define(stage, ring_path)
            ring.CreateRadiusAttr().Set(9.0)
            ring.CreateHeightAttr().Set(4.0)
            ring.CreateAxisAttr().Set("Y")
            UsdGeom.Xformable(ring.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(px, 82.0, pz))
            bind_material(ring.GetPrim(), "/World/Materials/M_Glow")

    elif spec["archetype"] == "spires":
        radius = 180.0
        for i in range(count):
            theta = (2 * math.pi * i) / count
            h = 60.0 + (i % 4) * 35.0
            px = (radius + (i % 2) * 40.0) * math.cos(theta)
            pz = (radius + (i % 2) * 40.0) * math.sin(theta)

            spire_path = f"/World/Architecture/Spire_{i:02d}"
            spire = UsdGeom.Cube.Define(stage, spire_path)
            spire.CreateSizeAttr().Set(1.0)
            s_xform = UsdGeom.Xformable(spire.GetPrim())
            s_xform.AddTranslateOp().Set(Gf.Vec3d(px, h / 2.0, pz))
            s_xform.AddScaleOp().Set(Gf.Vec3f(14.0, h, 14.0))

            bind_material(spire.GetPrim(), "/World/Materials/M_Base")

    elif spec["archetype"] == "grid":
        grid_size = int(math.ceil(math.sqrt(count)))
        spacing = 45.0
        offset = ((grid_size - 1) * spacing) / 2.0

        for i in range(count):
            gx = (i % grid_size) * spacing - offset
            gz = (i // grid_size) * spacing - offset
            crate_path = f"/World/Architecture/Cargo_{i:02d}"
            crate = UsdGeom.Cube.Define(stage, crate_path)
            crate.CreateSizeAttr().Set(20.0)
            c_xform = UsdGeom.Xformable(crate.GetPrim())
            c_xform.AddTranslateOp().Set(Gf.Vec3d(gx, 10.0, gz))

            if spec["has_physics"]:
                UsdPhysics.RigidBodyAPI.Apply(crate.GetPrim())
                UsdPhysics.CollisionAPI.Apply(crate.GetPrim())

            bind_material(crate.GetPrim(), "/World/Materials/M_Accent")

    # Central Core / Floating Crystal
    if spec["has_crystal"]:
        core_path = "/World/Architecture/CentralCore"
        core = UsdGeom.Sphere.Define(stage, core_path)
        core.CreateRadiusAttr().Set(22.0)
        c_xform = UsdGeom.Xformable(core.GetPrim())
        c_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 75.0, 0.0))
        bind_material(core.GetPrim(), "/World/Materials/M_Glow")

    # Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/MainCamera")
    cam.CreateFocalLengthAttr().Set(35.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 160.0, 360.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-18.0, 0.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Prompt Stage successfully saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prompt-to-USD Procedural Scene Generator.")
    parser.add_argument("--prompt", "-p", type=str, default="Cyberpunk neon arena with 12 pillars and floating ruby crystal core", help="Scene text description")
    parser.add_argument("--output", "-o", type=str, default="output_prompt_generated.usda", help="Output .usda path")
    args = parser.parse_args()

    generate_usd_from_prompt(args.prompt, args.output)
