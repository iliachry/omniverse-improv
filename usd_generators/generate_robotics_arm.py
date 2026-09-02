#!/usr/bin/env python3
"""
Standalone OpenUSD Script: 6-DOF Industrial Manipulator + Gripper Stage Generator.
Generates an interactive USD stage (.usda) with a 6-DOF robot arm, parallel gripper,
PBR industrial materials, studio lighting, and framing camera.
"""

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
from robotics.isaac_sim_sandbox import build_articulated_robot_stage


def build_robotics_stage(output_path: str = "output_robotics_arm.usda"):
    """Generates the full 6-DOF robotic arm stage."""
    print(f"[*] Creating 6-DOF Articulated Robotics Stage at: {output_path}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Hierarchies
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Materials")

    # Environment & Lighting
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=600.0, color=(0.92, 0.95, 1.0))
    add_distant_light(stage, "/World/Environment/KeyLight", intensity=3500.0, rotation_xyz=(-45.0, 40.0, 0.0))
    add_distant_light(stage, "/World/Environment/RimLight", intensity=1800.0, rotation_xyz=(-20.0, -140.0, 0.0))

    ground = add_ground_plane(stage, "/World/Environment/GroundPlane", size=2500.0)
    mat_ground = create_pbr_material(stage, "/World/Materials/M_Ground", diffuse_color=(0.11, 0.12, 0.14), roughness=0.5)
    bind_material(ground.GetPrim(), "/World/Materials/M_Ground")

    # Industrial Robot PBR Materials
    create_pbr_material(stage, "/World/Materials/M_CastMetal", diffuse_color=(0.08, 0.09, 0.10), metallic=0.9, roughness=0.35)
    create_pbr_material(stage, "/World/Materials/M_KukaOrange", diffuse_color=(1.0, 0.42, 0.0), metallic=0.15, roughness=0.25)
    create_pbr_material(stage, "/World/Materials/M_AccentCyan", diffuse_color=(0.0, 0.75, 1.0), metallic=0.3, roughness=0.2)
    create_pbr_material(stage, "/World/Materials/M_FingerRubber", diffuse_color=(0.15, 0.15, 0.15), metallic=0.0, roughness=0.7)

    # Build 6-DOF Robot Arm & Gripper
    build_articulated_robot_stage(stage)

    # Bind Materials to Links
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Base"), "/World/Materials/M_CastMetal")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Link1_Shoulder"), "/World/Materials/M_CastMetal")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Link2_UpperArm"), "/World/Materials/M_KukaOrange")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Link3_Forearm"), "/World/Materials/M_KukaOrange")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Link4_WristRoll"), "/World/Materials/M_AccentCyan")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Link5_WristPitch"), "/World/Materials/M_CastMetal")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/GripperBase"), "/World/Materials/M_CastMetal")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/FingerLeft"), "/World/Materials/M_FingerRubber")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/FingerRight"), "/World/Materials/M_FingerRubber")

    # Setup Viewport Framing Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/MainCamera")
    cam.CreateFocalLengthAttr().Set(42.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 120.0, 260.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-14.0, 0.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Successfully generated 6-DOF Robot Arm Stage: {output_path}")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_robotics_arm.usda")
    build_robotics_stage(out_file)
