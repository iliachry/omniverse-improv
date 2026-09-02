#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Procedural Futuristic Scene Generator.
Generates a sci-fi architectural platform with procedural pillars, emissive neon rings,
and a central levitating core with PBR materials.
"""

import os
import math
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

try:
    from .utils_usd import (
        create_stage,
        create_pbr_material,
        bind_material,
        add_dome_light,
        add_distant_light
    )
except (ImportError, ValueError):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from utils_usd import (
        create_stage,
        create_pbr_material,
        bind_material,
        add_dome_light,
        add_distant_light
    )


def build_procedural_scene(output_path: str = "output_procedural_scene.usda"):
    """Generates the procedural futuristic USD stage."""
    print(f"[*] Creating Procedural Sci-Fi Stage at: {output_path}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Hierarchies
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Architecture")
    UsdGeom.Xform.Define(stage, "/World/Materials")
    UsdGeom.Xform.Define(stage, "/World/Core")

    # 1. Lighting Setup (Dramatic Sci-Fi Contrasting Rim & Fill)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=200.0, color=(0.1, 0.15, 0.25))
    add_distant_light(stage, "/World/Environment/KeyLight", intensity=2500.0, color=(1.0, 0.85, 0.7), rotation_xyz=(-40.0, 45.0, 0.0))
    add_distant_light(stage, "/World/Environment/RimLight", intensity=3500.0, color=(0.0, 0.7, 1.0), rotation_xyz=(-20.0, -135.0, 0.0))

    # 2. Materials
    create_pbr_material(stage, "/World/Materials/M_FloorMetal", diffuse_color=(0.1, 0.11, 0.13), roughness=0.25, metallic=0.9)
    create_pbr_material(stage, "/World/Materials/M_DarkPanel", diffuse_color=(0.04, 0.04, 0.05), roughness=0.6, metallic=0.1)
    create_pbr_material(stage, "/World/Materials/M_GoldTrim", diffuse_color=(1.0, 0.78, 0.35), roughness=0.18, metallic=1.0)
    create_pbr_material(stage, "/World/Materials/M_NeonCyan", diffuse_color=(0.0, 0.9, 1.0), roughness=0.1, emissive_color=(0.0, 0.95, 1.0))
    create_pbr_material(stage, "/World/Materials/M_NeonOrange", diffuse_color=(1.0, 0.4, 0.0), roughness=0.1, emissive_color=(1.0, 0.45, 0.0))
    create_pbr_material(stage, "/World/Materials/M_CoreGem", diffuse_color=(0.9, 0.1, 0.3), roughness=0.05, metallic=0.1, opacity=0.85, ior=1.8)

    # 3. Central Tiered Dais / Platform
    for tier, (radius, height, y_pos) in enumerate([(180.0, 8.0, 4.0), (140.0, 8.0, 12.0), (90.0, 6.0, 18.0)]):
        dais_path = f"/World/Architecture/Dais_Tier_{tier}"
        cyl = UsdGeom.Cylinder.Define(stage, dais_path)
        cyl.CreateRadiusAttr().Set(radius)
        cyl.CreateHeightAttr().Set(height)
        cyl.CreateAxisAttr().Set("Y")
        cxform = UsdGeom.Xformable(cyl.GetPrim())
        cxform.AddTranslateOp().Set(Gf.Vec3d(0.0, y_pos, 0.0))
        bind_material(cyl.GetPrim(), "/World/Materials/M_FloorMetal" if tier == 0 else "/World/Materials/M_DarkPanel")

    # 4. Ring of Procedural Pillars
    num_pillars = 8
    ring_radius = 120.0
    pillar_height = 90.0
    pillar_radius = 7.0

    for i in range(num_pillars):
        angle = (i / float(num_pillars)) * math.pi * 2.0
        px = ring_radius * math.cos(angle)
        pz = ring_radius * math.sin(angle)

        pillar_path = f"/World/Architecture/Pillar_{i:02d}"
        pillar_xform = UsdGeom.Xform.Define(stage, pillar_path)
        xformable = UsdGeom.Xformable(pillar_xform.GetPrim())
        xformable.AddTranslateOp().Set(Gf.Vec3d(px, 12.0 + pillar_height * 0.5, pz))

        # Main pillar shaft
        shaft = UsdGeom.Cylinder.Define(stage, f"{pillar_path}/Shaft")
        shaft.CreateRadiusAttr().Set(pillar_radius)
        shaft.CreateHeightAttr().Set(pillar_height)
        shaft.CreateAxisAttr().Set("Y")
        bind_material(shaft.GetPrim(), "/World/Materials/M_DarkPanel")

        # Neon glow ring around pillar mid-section
        glow_ring = UsdGeom.Cylinder.Define(stage, f"{pillar_path}/NeonBand")
        glow_ring.CreateRadiusAttr().Set(pillar_radius * 1.08)
        glow_ring.CreateHeightAttr().Set(4.0)
        glow_ring.CreateAxisAttr().Set("Y")
        bind_material(glow_ring.GetPrim(), "/World/Materials/M_NeonCyan" if i % 2 == 0 else "/World/Materials/M_NeonOrange")

        # Gold Cap
        cap = UsdGeom.Cylinder.Define(stage, f"{pillar_path}/Cap")
        cap.CreateRadiusAttr().Set(pillar_radius * 1.2)
        cap.CreateHeightAttr().Set(4.0)
        cap.CreateAxisAttr().Set("Y")
        UsdGeom.Xformable(cap.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, pillar_height * 0.5 + 2.0, 0.0))
        bind_material(cap.GetPrim(), "/World/Materials/M_GoldTrim")

    # 5. Levitating Sci-Fi Central Core
    core_center_y = 65.0
    
    # Outer floating ring (Torus approximation or nested cylinders)
    outer_ring = UsdGeom.Cylinder.Define(stage, "/World/Core/OuterRing")
    outer_ring.CreateRadiusAttr().Set(35.0)
    outer_ring.CreateHeightAttr().Set(3.0)
    outer_ring.CreateAxisAttr().Set("Y")
    or_xform = UsdGeom.Xformable(outer_ring.GetPrim())
    or_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, core_center_y, 0.0))
    or_xform.AddRotateXYZOp().Set(Gf.Vec3d(25.0, 45.0, 15.0))
    bind_material(outer_ring.GetPrim(), "/World/Materials/M_GoldTrim")

    # Floating Inner Neon Sphere
    gem = UsdGeom.Sphere.Define(stage, "/World/Core/EnergyOrb")
    gem.CreateRadiusAttr().Set(14.0)
    gem_xform = UsdGeom.Xformable(gem.GetPrim())
    gem_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, core_center_y, 0.0))
    bind_material(gem.GetPrim(), "/World/Materials/M_CoreGem")

    # 6. Orbiting Satellites
    for s_idx in range(3):
        sat_angle = (s_idx / 3.0) * math.pi * 2.0
        sx = 50.0 * math.cos(sat_angle)
        sz = 50.0 * math.sin(sat_angle)
        sy = core_center_y + 10.0 * math.sin(s_idx * 2.0)

        sat = UsdGeom.Sphere.Define(stage, f"/World/Core/Satellite_{s_idx}")
        sat.CreateRadiusAttr().Set(4.0)
        sat_xform = UsdGeom.Xformable(sat.GetPrim())
        sat_xform.AddTranslateOp().Set(Gf.Vec3d(sx, sy, sz))
        bind_material(sat.GetPrim(), "/World/Materials/M_NeonCyan")

    # 7. Cinematic Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/CinematicCam")
    cam.CreateFocalLengthAttr().Set(45.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 110.0, 260.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-18.0, 0.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Successfully generated Procedural Sci-Fi Stage: {output_path}")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_procedural_scene.usda")
    build_procedural_scene(out_file)
