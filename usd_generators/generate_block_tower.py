#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Jenga-Style Block Tower & Kinetic Ball Shower.
Generates an interactive USD stage (.usda) with an 8-floor block tower and
dynamic kinetic projectile spheres.
"""

import os
import sys
from pxr import Gf, Sdf, Usd, UsdGeom

# Add extension path for StageBuilder
exts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exts", "omni.improv.starter")
if exts_dir not in sys.path:
    sys.path.insert(0, exts_dir)

from omni.improv.starter.core.stage_builder import StageBuilder


def build_block_tower_stage(output_path: str = "output_block_tower.usda"):
    """Generates the block tower USD stage."""
    print(f"[*] Creating Destructible Block Tower Stage at: {output_path}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = Usd.Stage.CreateNew(output_path)
    StageBuilder.setup_stage_metadata(stage, meters_per_unit=0.01)

    # 1. Studio Environment
    StageBuilder.setup_studio_environment(stage, add_ground=True, add_lighting=True)

    # 2. Block Tower (8 floors, 24 rigid body blocks)
    StageBuilder.spawn_destructible_tower(stage, "/World/Props/BlockTower", floors=8, blocks_per_floor=3)

    # 3. Kinetic Projectile Spheres
    for i in range(6):
        StageBuilder.spawn_primitive(
            stage,
            prim_type="Sphere",
            prim_path=f"/World/Props/Projectiles/Ball_{i:02d}",
            position=(-30.0 + i * 12.0, 100.0 + (i % 2) * 20.0, 30.0),
            size=14.0,
            dynamic_physics=True,
            material_preset="neon_magenta" if i % 2 == 0 else "neon_cyan"
        )

    # 4. Viewport Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/MainCamera")
    cam.CreateFocalLengthAttr().Set(35.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(120.0, 160.0, 240.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-20.0, 25.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Successfully generated Destructible Block Tower Stage: {output_path}")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_block_tower.usda")
    build_block_tower_stage(out_file)
