"""
Automated Test Suite for 6-DOF Robotics Articulations, Parallel Grippers, SDG and USDZ.
"""

import os
import pytest
from pxr import Usd, UsdPhysics

from robotics.isaac_sim_sandbox import build_articulated_robot_stage
from usd_generators.export_usdz import package_to_usdz


def test_6dof_robotics_articulation_setup():
    """Validates 6-DOF Robot Arm Articulation, Revolute Joints, and Parallel Gripper."""
    stage = Usd.Stage.CreateInMemory()
    robot_path = build_articulated_robot_stage(stage)

    assert stage.GetPrimAtPath(robot_path).IsValid()
    assert stage.GetPrimAtPath(robot_path).HasAPI(UsdPhysics.ArticulationRootAPI)

    # Check 6 Revolute Joints
    joints = [
        "Joint1_Waist",
        "Joint2_Shoulder",
        "Joint3_Elbow",
        "Joint4_WristRoll",
        "Joint5_WristPitch",
        "Joint6_ToolFlange"
    ]
    for j_name in joints:
        j_prim = stage.GetPrimAtPath(f"{robot_path}/{j_name}")
        assert j_prim.IsValid(), f"Joint {j_name} not found"
        assert j_prim.IsA(UsdPhysics.RevoluteJoint)
        assert j_prim.HasAPI(UsdPhysics.DriveAPI, "angular")

    # Check Prismatic Gripper Fingers
    fl_joint = stage.GetPrimAtPath(f"{robot_path}/Joint_FingerLeft")
    fr_joint = stage.GetPrimAtPath(f"{robot_path}/Joint_FingerRight")

    assert fl_joint.IsValid() and fl_joint.IsA(UsdPhysics.PrismaticJoint)
    assert fr_joint.IsValid() and fr_joint.IsA(UsdPhysics.PrismaticJoint)
    assert fl_joint.HasAPI(UsdPhysics.DriveAPI, "linear")
    assert fr_joint.HasAPI(UsdPhysics.DriveAPI, "linear")


def test_usdz_packaging(tmp_path):
    """Validates Apple USDZ packaging pipeline."""
    sample_usda = tmp_path / "sample.usda"
    stage = Usd.Stage.CreateNew(str(sample_usda))
    stage.GetRootLayer().Save()

    out_usdz = str(tmp_path / "sample.usdz")
    result = package_to_usdz(str(sample_usda), out_usdz)

    assert os.path.exists(result)
    assert os.path.getsize(result) > 0
