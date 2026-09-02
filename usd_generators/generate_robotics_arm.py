#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Articulated Robotic Arm Generator.
Generates an interactive USD stage (.usda) with a 2-DOF robotic manipulator,
base pedestal, revolute joints, and UsdPhysics.DriveAPI joint controllers.
"""

import os
import sys

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    """Generates the full robotic arm stage."""
    print(f"[*] Creating Articulated Robotics Stage at: {output_path}")

    if os.path.exists(output_path):
        os.remove(output_path)

    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # Hierarchies
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Materials")

    # Environment & Lighting
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=500.0, color=(0.9, 0.95, 1.0))
    add_distant_light(stage, "/World/Environment/KeyLight", intensity=3000.0, rotation_xyz=(-45.0, 45.0, 0.0))

    ground = add_ground_plane(stage, "/World/Environment/GroundPlane", size=2000.0)
    mat_ground = create_pbr_material(stage, "/World/Materials/M_Ground", diffuse_color=(0.12, 0.14, 0.16), roughness=0.6)
    bind_material(ground.GetPrim(), "/World/Materials/M_Ground")

    # Robot Materials
    mat_base = create_pbr_material(stage, "/World/Materials/M_RobotBase", diffuse_color=(0.1, 0.1, 0.12), metallic=0.9, roughness=0.3)
    mat_arm = create_pbr_material(stage, "/World/Materials/M_RobotArm", diffuse_color=(1.0, 0.5, 0.0), metallic=0.2, roughness=0.2)
    mat_forearm = create_pbr_material(stage, "/World/Materials/M_RobotForearm", diffuse_color=(0.1, 0.6, 0.9), metallic=0.4, roughness=0.25)

    # Build Robot Arm
    build_articulated_robot_stage(stage)

    # Bind materials
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Base"), "/World/Materials/M_RobotBase")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/UpperArm"), "/World/Materials/M_RobotArm")
    bind_material(stage.GetPrimAtPath("/World/RobotArm/Forearm"), "/World/Materials/M_RobotForearm")

    # Setup Camera
    cam = UsdGeom.Camera.Define(stage, "/World/Cameras/MainCamera")
    cam.CreateFocalLengthAttr().Set(40.0)
    cam_xform = UsdGeom.Xformable(cam.GetPrim())
    cam_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 100.0, 220.0))
    cam_xform.AddRotateXYZOp().Set(Gf.Vec3d(-15.0, 0.0, 0.0))

    stage.GetRootLayer().Save()
    print(f"[OK] Successfully generated Articulated Robot Arm Stage: {output_path}")
    return output_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(current_dir, "output_robotics_arm.usda")
    build_robotics_stage(out_file)
