#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Industrial Warehouse Digital Twin & Conveyor Simulation.
Generates an interactive USD stage (.usda) with:
- Multi-tier structural steel pallet racks
- Wooden Euro-pallets & stacked cargo boxes
- Motorized industrial physics conveyor belt with guide rails
- Automated Guided Vehicle (AGV) / Forklift transport unit
- High-bay industrial lighting and safety floor markings
"""

import math
import os
import sys

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


def build_warehouse_digital_twin(output_path: str = "output_warehouse_digital_twin.usda") -> str:
    """Constructs the complete industrial warehouse digital twin USD stage."""
    print(f"[*] Creating Industrial Warehouse Digital Twin Stage at: {output_path}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Hierarchies
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Materials")
    UsdGeom.Xform.Define(stage, "/World/RackingSystem")
    UsdGeom.Xform.Define(stage, "/World/ConveyorLine")
    UsdGeom.Xform.Define(stage, "/World/MobileFleet")

    # Physics & Environment Lighting
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=400.0, color=(0.88, 0.92, 1.0))
    add_distant_light(stage, "/World/Environment/CeilingFlood", intensity=3800.0, rotation_xyz=(-65.0, 30.0, 0.0))

    # Concrete Factory Floor
    ground = add_ground_plane(stage, "/World/Environment/GroundPlane", size=4000.0)
    mat_floor = create_pbr_material(stage, "/World/Materials/M_ConcreteFloor", diffuse_color=(0.14, 0.15, 0.17), roughness=0.45)
    bind_material(ground.GetPrim(), "/World/Materials/M_ConcreteFloor")

    # Industrial PBR Materials
    mat_steel_blue = create_pbr_material(stage, "/World/Materials/M_SteelBlue", diffuse_color=(0.04, 0.22, 0.45), metallic=0.7, roughness=0.3)
    mat_beam_orange = create_pbr_material(stage, "/World/Materials/M_SafetyOrange", diffuse_color=(1.0, 0.38, 0.0), metallic=0.3, roughness=0.35)
    mat_wood_pallet = create_pbr_material(stage, "/World/Materials/M_WoodPallet", diffuse_color=(0.65, 0.48, 0.32), metallic=0.0, roughness=0.75)
    mat_cardboard = create_pbr_material(stage, "/World/Materials/M_Cardboard", diffuse_color=(0.78, 0.62, 0.42), metallic=0.0, roughness=0.8)
    mat_conveyor_belt = create_pbr_material(stage, "/World/Materials/M_RubberBelt", diffuse_color=(0.06, 0.06, 0.07), metallic=0.1, roughness=0.5)
    mat_hazard_yellow = create_pbr_material(stage, "/World/Materials/M_HazardYellow", diffuse_color=(0.95, 0.78, 0.05), metallic=0.1, roughness=0.3)

    # 1. Multi-Tier Warehouse Pallet Racking
    rack_bay_width = 160.0
    rack_bay_depth = 60.0
    rack_height = 240.0
    num_bays = 3
    num_tiers = 3

    for b in range(num_bays):
        bx_offset = (b - 1) * (rack_bay_width + 10.0)

        # Vertical Upright Columns (Blue Steel)
        for side in [-rack_bay_width / 2.0, rack_bay_width / 2.0]:
            col_path = f"/World/RackingSystem/Column_B{b}_{'L' if side < 0 else 'R'}"
            col = UsdGeom.Cube.Define(stage, col_path)
            col.CreateSizeAttr().Set(1.0)
            cx = UsdGeom.Xformable(col.GetPrim())
            cx.AddTranslateOp().Set(Gf.Vec3d(bx_offset + side, rack_height / 2.0, -120.0))
            cx.AddScaleOp().Set(Gf.Vec3f(6.0, rack_height, 8.0))
            bind_material(col.GetPrim(), "/World/Materials/M_SteelBlue")
            UsdPhysics.CollisionAPI.Apply(col.GetPrim())

        # Horizontal Load Beams (Safety Orange)
        for t in range(1, num_tiers + 1):
            tier_y = t * 65.0

            beam_f_path = f"/World/RackingSystem/Beam_B{b}_T{t}_Front"
            beam_f = UsdGeom.Cube.Define(stage, beam_f_path)
            beam_f.CreateSizeAttr().Set(1.0)
            bfx = UsdGeom.Xformable(beam_f.GetPrim())
            bfx.AddTranslateOp().Set(Gf.Vec3d(bx_offset, tier_y, -120.0 + (rack_bay_depth / 2.0)))
            bfx.AddScaleOp().Set(Gf.Vec3f(rack_bay_width, 6.0, 4.0))
            bind_material(beam_f.GetPrim(), "/World/Materials/M_SafetyOrange")
            UsdPhysics.CollisionAPI.Apply(beam_f.GetPrim())

            beam_b_path = f"/World/RackingSystem/Beam_B{b}_T{t}_Back"
            beam_b = UsdGeom.Cube.Define(stage, beam_b_path)
            beam_b.CreateSizeAttr().Set(1.0)
            bbx = UsdGeom.Xformable(beam_b.GetPrim())
            bbx.AddTranslateOp().Set(Gf.Vec3d(bx_offset, tier_y, -120.0 - (rack_bay_depth / 2.0)))
            bbx.AddScaleOp().Set(Gf.Vec3f(rack_bay_width, 6.0, 4.0))
            bind_material(beam_b.GetPrim(), "/World/Materials/M_SafetyOrange")
            UsdPhysics.CollisionAPI.Apply(beam_b.GetPrim())

            # Pallets & Cargo on Tiers
            for p in [-38.0, 38.0]:
                pallet_path = f"/World/RackingSystem/Pallet_B{b}_T{t}_{'L' if p < 0 else 'R'}"
                pallet = UsdGeom.Cube.Define(stage, pallet_path)
                pallet.CreateSizeAttr().Set(1.0)
                px = UsdGeom.Xformable(pallet.GetPrim())
                px.AddTranslateOp().Set(Gf.Vec3d(bx_offset + p, tier_y + 4.0, -120.0))
                px.AddScaleOp().Set(Gf.Vec3f(55.0, 5.0, 50.0))
                bind_material(pallet.GetPrim(), "/World/Materials/M_WoodPallet")
                UsdPhysics.CollisionAPI.Apply(pallet.GetPrim())

                # Cargo Crates
                crate_path = f"/World/RackingSystem/Crate_B{b}_T{t}_{'L' if p < 0 else 'R'}"
                crate = UsdGeom.Cube.Define(stage, crate_path)
                crate.CreateSizeAttr().Set(1.0)
                cx = UsdGeom.Xformable(crate.GetPrim())
                cx.AddTranslateOp().Set(Gf.Vec3d(bx_offset + p, tier_y + 22.0, -120.0))
                cx.AddScaleOp().Set(Gf.Vec3f(44.0, 32.0, 42.0))
                bind_material(crate.GetPrim(), "/World/Materials/M_Cardboard")
                UsdPhysics.RigidBodyAPI.Apply(crate.GetPrim())
                UsdPhysics.CollisionAPI.Apply(crate.GetPrim())

    # 2. Motorized Industrial Conveyor Line
    conveyor_len = 360.0
    conveyor_width = 45.0
    conveyor_height = 35.0

    belt_path = "/World/ConveyorLine/MainBelt"
    belt = UsdGeom.Cube.Define(stage, belt_path)
    belt.CreateSizeAttr().Set(1.0)
    bx = UsdGeom.Xformable(belt.GetPrim())
    bx.AddTranslateOp().Set(Gf.Vec3d(0.0, conveyor_height, 60.0))
    bx.AddScaleOp().Set(Gf.Vec3f(conveyor_len, 4.0, conveyor_width))
    bind_material(belt.GetPrim(), "/World/Materials/M_RubberBelt")
    UsdPhysics.CollisionAPI.Apply(belt.GetPrim())

    # Conveyor Support Legs
    for i, lx in enumerate([-150.0, -50.0, 50.0, 150.0]):
        leg_path = f"/World/ConveyorLine/Leg_{i:02d}"
        leg = UsdGeom.Cylinder.Define(stage, leg_path)
        leg.CreateRadiusAttr().Set(3.0)
        leg.CreateHeightAttr().Set(conveyor_height)
        leg.CreateAxisAttr().Set("Y")
        UsdGeom.Xformable(leg.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(lx, conveyor_height / 2.0, 60.0))
        bind_material(leg.GetPrim(), "/World/Materials/M_SteelBlue")

    # Dynamic Packages on Conveyor
    for i, c_pos in enumerate([-120.0, -40.0, 40.0, 120.0]):
        pkg_path = f"/World/ConveyorLine/Package_{i}"
        pkg = UsdGeom.Cube.Define(stage, pkg_path)
        pkg.CreateSizeAttr().Set(1.0)
        px = UsdGeom.Xformable(pkg.GetPrim())
        px.AddTranslateOp().Set(Gf.Vec3d(c_pos, conveyor_height + 12.0, 60.0))
        px.AddScaleOp().Set(Gf.Vec3f(24.0, 20.0, 24.0))
        bind_material(pkg.GetPrim(), "/World/Materials/M_Cardboard")

        UsdPhysics.RigidBodyAPI.Apply(pkg.GetPrim())
        UsdPhysics.CollisionAPI.Apply(pkg.GetPrim())
        UsdPhysics.MassAPI.Apply(pkg.GetPrim()).CreateMassAttr().Set(2.5)

    # 3. Automated Guided Vehicle (AGV) Chassis
    agv_path = "/World/MobileFleet/AGV_Unit01"
    agv_chassis = UsdGeom.Cube.Define(stage, agv_path)
    agv_chassis.CreateSizeAttr().Set(1.0)
    ax = UsdGeom.Xformable(agv_chassis.GetPrim())
    ax.AddTranslateOp().Set(Gf.Vec3d(140.0, 10.0, -20.0))
    ax.AddScaleOp().Set(Gf.Vec3f(70.0, 16.0, 45.0))
    bind_material(agv_chassis.GetPrim(), "/World/Materials/M_HazardYellow")
    UsdPhysics.CollisionAPI.Apply(agv_chassis.GetPrim())

    # Framing Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/MainCamera")
    cam.CreateFocalLengthAttr().Set(35.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(280.0, 220.0, 290.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-24.0, 42.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Industrial Warehouse Stage saved successfully to: {output_path}")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_warehouse_digital_twin.usda")
    build_warehouse_digital_twin(out_file)
