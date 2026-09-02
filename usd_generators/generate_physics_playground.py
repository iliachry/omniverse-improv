#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Kinetic Physics Playground Generator.
Generates an interactive USD stage (.usda) complete with an inclined ramp, rolling trigger ball,
curved domino chain, and a stacked pyramid target.
Can be opened directly in Omniverse USD Composer, Isaac Sim, Blender, or usdview.
"""

import os
import math
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

try:
    from .utils_usd import (
        create_stage,
        setup_physics_scene,
        create_pbr_material,
        bind_material,
        add_dome_light,
        add_distant_light,
        add_ground_plane
    )
except (ImportError, ValueError):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from utils_usd import (
        create_stage,
        setup_physics_scene,
        create_pbr_material,
        bind_material,
        add_dome_light,
        add_distant_light,
        add_ground_plane
    )


def build_physics_playground(output_path: str = "output_physics_playground.usda"):
    """Generates the full kinetic physics playground USD stage."""
    print(f"[*] Creating Kinetic Physics Playground Stage at: {output_path}")

    # Remove existing file if present
    if os.path.exists(output_path):
        os.remove(output_path)

    # 1. Initialize Stage (Centimeters, Y-Up)
    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Define root hierarchy
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Materials")
    UsdGeom.Xform.Define(stage, "/World/Props")

    # 2. Setup Physics & Lighting
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=600.0, color=(0.95, 0.98, 1.0))
    add_distant_light(stage, "/World/Environment/SunLight", intensity=3500.0, rotation_xyz=(-50.0, 35.0, 0.0))

    # 3. Create Ground Collider & Materials
    ground = add_ground_plane(stage, "/World/Environment/GroundPlane", size=3000.0)
    mat_ground = create_pbr_material(stage, "/World/Materials/M_Ground", diffuse_color=(0.15, 0.16, 0.18), roughness=0.5)
    bind_material(ground.GetPrim(), "/World/Materials/M_Ground")

    # Materials for props
    create_pbr_material(stage, "/World/Materials/M_Ramp", diffuse_color=(0.2, 0.4, 0.8), roughness=0.3, metallic=0.2)
    create_pbr_material(stage, "/World/Materials/M_TriggerBall", diffuse_color=(1.0, 0.2, 0.1), roughness=0.1, metallic=0.9)
    create_pbr_material(stage, "/World/Materials/M_Domino", diffuse_color=(0.0, 0.85, 0.7), roughness=0.2, metallic=0.1)
    create_pbr_material(stage, "/World/Materials/M_TargetBox", diffuse_color=(1.0, 0.7, 0.1), roughness=0.4, metallic=0.0)

    # 4. Inclined Launch Ramp (Static Collider)
    ramp_path = "/World/Props/LaunchRamp"
    ramp = UsdGeom.Cube.Define(stage, ramp_path)
    ramp.CreateSizeAttr().Set(1.0)
    ramp_xform = UsdGeom.Xformable(ramp.GetPrim())
    # Dimensions: 120 long, 6 thick, 24 wide, tilted at -20 deg
    ramp_xform.AddTranslateOp().Set(Gf.Vec3d(-80.0, 24.0, 0.0))
    ramp_xform.AddRotateZOp().Set(-18.0)
    ramp_xform.AddScaleOp().Set(Gf.Vec3f(120.0, 6.0, 24.0))

    ramp_col = UsdPhysics.CollisionAPI.Apply(ramp.GetPrim())
    ramp_col.CreateCollisionEnabledAttr().Set(True)
    bind_material(ramp.GetPrim(), "/World/Materials/M_Ramp")

    # 5. Heavy Trigger Sphere at top of ramp
    ball_path = "/World/Props/TriggerSphere"
    ball = UsdGeom.Sphere.Define(stage, ball_path)
    ball.CreateRadiusAttr().Set(12.0)
    ball_xform = UsdGeom.Xformable(ball.GetPrim())
    ball_xform.AddTranslateOp().Set(Gf.Vec3d(-125.0, 52.0, 0.0))

    ball_rb = UsdPhysics.RigidBodyAPI.Apply(ball.GetPrim())
    ball_rb.CreateRigidBodyEnabledAttr().Set(True)
    ball_col = UsdPhysics.CollisionAPI.Apply(ball.GetPrim())
    ball_col.CreateCollisionEnabledAttr().Set(True)
    UsdPhysics.MeshCollisionAPI.Apply(ball.GetPrim()).CreateApproximationAttr().Set("boundingSphere")
    UsdPhysics.MassAPI.Apply(ball.GetPrim()).CreateMassAttr().Set(8.0)
    bind_material(ball.GetPrim(), "/World/Materials/M_TriggerBall")

    # 6. Curved Domino Chain (30 Dominoes)
    domino_count = 32
    start_x, start_z = -20.0, 0.0
    domino_w, domino_h, domino_d = 3.5, 22.0, 11.0

    for i in range(domino_count):
        t = i / float(domino_count)
        # S-curve path
        x = start_x + (i * 12.0)
        z = math.sin(t * math.pi * 2.0) * 35.0
        angle_deg = math.degrees(math.atan2(
            math.cos(t * math.pi * 2.0) * 35.0 * (math.pi * 2.0 / domino_count),
            12.0
        ))

        d_path = f"/World/Props/Dominoes/Domino_{i:02d}"
        d_cube = UsdGeom.Cube.Define(stage, d_path)
        d_cube.CreateSizeAttr().Set(1.0)
        
        dxform = UsdGeom.Xformable(d_cube.GetPrim())
        dxform.AddTranslateOp().Set(Gf.Vec3d(x, domino_h * 0.5, z))
        dxform.AddRotateYOp().Set(-angle_deg)
        dxform.AddScaleOp().Set(Gf.Vec3f(domino_w, domino_h, domino_d))

        rb = UsdPhysics.RigidBodyAPI.Apply(d_cube.GetPrim())
        rb.CreateRigidBodyEnabledAttr().Set(True)
        col = UsdPhysics.CollisionAPI.Apply(d_cube.GetPrim())
        col.CreateCollisionEnabledAttr().Set(True)
        UsdPhysics.MeshCollisionAPI.Apply(d_cube.GetPrim()).CreateApproximationAttr().Set("boundingCube")
        UsdPhysics.MassAPI.Apply(d_cube.GetPrim()).CreateDensityAttr().Set(1100.0)
        bind_material(d_cube.GetPrim(), "/World/Materials/M_Domino")

    # 7. Stacked Pyramid of Blocks at the end of the domino run
    pyramid_base_x = start_x + (domino_count * 12.0) + 20.0
    box_size = 14.0
    pyramid_levels = 5

    for level in range(pyramid_levels):
        blocks_in_level = pyramid_levels - level
        y = (level + 0.5) * box_size
        z_start = -((blocks_in_level - 1) * (box_size * 1.05)) * 0.5

        for b in range(blocks_in_level):
            z = z_start + (b * box_size * 1.05)
            b_path = f"/World/Props/Pyramid/Level_{level}_Block_{b}"
            box = UsdGeom.Cube.Define(stage, b_path)
            box.CreateSizeAttr().Set(box_size * 0.96)

            bxform = UsdGeom.Xformable(box.GetPrim())
            bxform.AddTranslateOp().Set(Gf.Vec3d(pyramid_base_x, y, z))

            rb = UsdPhysics.RigidBodyAPI.Apply(box.GetPrim())
            rb.CreateRigidBodyEnabledAttr().Set(True)
            col = UsdPhysics.CollisionAPI.Apply(box.GetPrim())
            col.CreateCollisionEnabledAttr().Set(True)
            UsdPhysics.MeshCollisionAPI.Apply(box.GetPrim()).CreateApproximationAttr().Set("boundingCube")
            UsdPhysics.MassAPI.Apply(box.GetPrim()).CreateDensityAttr().Set(500.0)
            bind_material(box.GetPrim(), "/World/Materials/M_TargetBox")

    # 8. Setup Viewport Camera
    cam_path = "/World/Cameras/MainCamera"
    cam = UsdGeom.Camera.Define(stage, cam_path)
    cam.CreateFocalLengthAttr().Set(35.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(120.0, 180.0, 320.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-25.0, 18.0, 0.0))

    # Save to disk
    stage.GetRootLayer().Save()
    print(f"[OK] Successfully generated Kinetic Physics Playground: {output_path}")
    print(f"    - Elements: Ramp + Heavy Trigger Sphere + {domino_count} Dominoes + {pyramid_levels}-Level Pyramid")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_physics_playground.usda")
    build_physics_playground(out_file)
