"""
Automated Test Suite for Isaac Sim Robotics Articulations and Standalone SDG.
"""

import os
import pytest
from pxr import Usd, UsdPhysics

from robotics.isaac_sim_sandbox import build_articulated_robot_stage


def test_robotics_articulation_setup():
    """Validates 2-DOF Robot Arm Articulation, Revolute Joints, and DriveAPIs."""
    stage = Usd.Stage.CreateInMemory()
    robot_path = build_articulated_robot_stage(stage)
    
    assert stage.GetPrimAtPath(robot_path).IsValid()
    assert stage.GetPrimAtPath(robot_path).HasAPI(UsdPhysics.ArticulationRootAPI)
    
    # Check Joints
    waist_joint = stage.GetPrimAtPath(f"{robot_path}/Joint_Waist")
    elbow_joint = stage.GetPrimAtPath(f"{robot_path}/Joint_Elbow")
    
    assert waist_joint.IsValid() and waist_joint.IsA(UsdPhysics.RevoluteJoint)
    assert elbow_joint.IsValid() and elbow_joint.IsA(UsdPhysics.RevoluteJoint)
    
    # Check DriveAPIs
    assert waist_joint.HasAPI(UsdPhysics.DriveAPI, "angular")
    assert elbow_joint.HasAPI(UsdPhysics.DriveAPI, "angular")
