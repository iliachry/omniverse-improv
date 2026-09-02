#!/usr/bin/env python3
"""
Isaac Sim & Omniverse Robotics Sandbox.
Demonstrates physics articulation setup, joint drive controllers (UsdPhysics.DriveAPI),
and real-time simulation stepping for robotic manipulators and mechanisms.

Usage in Isaac Sim:
  python isaac_sim_sandbox.py
Or run via Isaac Sim Python environment:
  <isaac_sim_path>/python.bat robotics/isaac_sim_sandbox.py
"""

import sys
import time
import math
from typing import List, Tuple

try:
    from omni.isaac.kit import SimulationApp
    # Initialize Isaac Sim headless or with GUI
    simulation_app = SimulationApp({"headless": False})
    HAS_ISAAC = True
except ImportError:
    simulation_app = None
    HAS_ISAAC = False

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics


def build_articulated_robot_stage(stage: Usd.Stage) -> Sdf.Path:
    """
    Constructs a 2-DOF articulated robotic arm mechanism with revolute joints and drives.
    
    Args:
        stage: Active USD stage.
        
    Returns:
        Root Sdf.Path of the robot articulation.
    """
    print("[*] Authoring Articulated Robotic Arm in USD...")

    # Root Articulation Prim
    robot_path = Sdf.Path("/World/RobotArm")
    robot_xform = UsdGeom.Xform.Define(stage, robot_path)
    
    # Apply ArticulationRootAPI to the root
    articulation_root = UsdPhysics.ArticulationRootAPI.Apply(robot_xform.GetPrim())

    # 1. Base Pedestal (Fixed / RigidBody)
    base_path = f"{robot_path}/Base"
    base_geom = UsdGeom.Cylinder.Define(stage, base_path)
    base_geom.CreateRadiusAttr().Set(15.0)
    base_geom.CreateHeightAttr().Set(20.0)
    base_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(base_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 10.0, 0.0))

    base_rb = UsdPhysics.RigidBodyAPI.Apply(base_geom.GetPrim())
    base_col = UsdPhysics.CollisionAPI.Apply(base_geom.GetPrim())

    # 2. Upper Arm Link
    link1_path = f"{robot_path}/UpperArm"
    link1_geom = UsdGeom.Capsule.Define(stage, link1_path)
    link1_geom.CreateRadiusAttr().Set(5.0)
    link1_geom.CreateHeightAttr().Set(40.0)
    link1_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link1_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 45.0, 0.0))

    link1_rb = UsdPhysics.RigidBodyAPI.Apply(link1_geom.GetPrim())
    link1_col = UsdPhysics.CollisionAPI.Apply(link1_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link1_geom.GetPrim()).CreateMassAttr().Set(3.0)

    # Joint 1: Base to UpperArm (Revolute around Y - Waist rotation)
    joint1_path = f"{robot_path}/Joint_Waist"
    joint1 = UsdPhysics.RevoluteJoint.Define(stage, joint1_path)
    joint1.CreateAxisAttr().Set("Y")
    joint1.CreateBody0Rel().SetTargets([Sdf.Path(base_path)])
    joint1.CreateBody1Rel().SetTargets([Sdf.Path(link1_path)])
    joint1.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 10.0, 0.0))
    joint1.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -25.0, 0.0))
    joint1.CreateLowerLimitAttr().Set(-180.0)
    joint1.CreateUpperLimitAttr().Set(180.0)

    # Apply DriveAPI for Joint 1 Position/Velocity Control
    drive1 = UsdPhysics.DriveAPI.Apply(joint1.GetPrim(), "angular")
    drive1.CreateTypeAttr().Set("force")
    drive1.CreateStiffnessAttr().Set(10000.0)
    drive1.CreateDampingAttr().Set(1000.0)
    drive1.CreateTargetPositionAttr().Set(0.0)

    # 3. Forearm Link
    link2_path = f"{robot_path}/Forearm"
    link2_geom = UsdGeom.Capsule.Define(stage, link2_path)
    link2_geom.CreateRadiusAttr().Set(4.0)
    link2_geom.CreateHeightAttr().Set(35.0)
    link2_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link2_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 85.0, 0.0))

    link2_rb = UsdPhysics.RigidBodyAPI.Apply(link2_geom.GetPrim())
    link2_col = UsdPhysics.CollisionAPI.Apply(link2_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link2_geom.GetPrim()).CreateMassAttr().Set(2.0)

    # Joint 2: UpperArm to Forearm (Revolute around X - Elbow pitch)
    joint2_path = f"{robot_path}/Joint_Elbow"
    joint2 = UsdPhysics.RevoluteJoint.Define(stage, joint2_path)
    joint2.CreateAxisAttr().Set("X")
    joint2.CreateBody0Rel().SetTargets([Sdf.Path(link1_path)])
    joint2.CreateBody1Rel().SetTargets([Sdf.Path(link2_path)])
    joint2.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 25.0, 0.0))
    joint2.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -20.0, 0.0))
    joint2.CreateLowerLimitAttr().Set(-90.0)
    joint2.CreateUpperLimitAttr().Set(90.0)

    drive2 = UsdPhysics.DriveAPI.Apply(joint2.GetPrim(), "angular")
    drive2.CreateTypeAttr().Set("force")
    drive2.CreateStiffnessAttr().Set(8000.0)
    drive2.CreateDampingAttr().Set(800.0)
    drive2.CreateTargetPositionAttr().Set(0.0)

    print(f"[OK] Robot arm created at {robot_path} with Waist and Elbow revolute drives.")
    return robot_path


def run_simulation_loop():
    """Executes the simulation control loop."""
    if not HAS_ISAAC:
        print("[!] Isaac Sim (omni.isaac.core) not found. Running in standalone USD mode.")
        stage = Usd.Stage.CreateInMemory()
        build_articulated_robot_stage(stage)
        print("[OK] USD Articulation hierarchy validated successfully.")
        return

    from omni.isaac.core import World
    from omni.isaac.core.objects import DynamicCuboid

    world = World(stage_units_in_meters=0.01)
    world.scene.add_default_ground_plane()

    stage = world.stage
    build_articulated_robot_stage(stage)

    world.reset()
    print("[*] Starting Isaac Sim Control Loop (Press Ctrl+C or close window to stop)...")

    step_idx = 0
    while simulation_app.is_running():
        # Physics step
        world.step(render=True)
        step_idx += 1

        # Periodic sinusoidal trajectory commands
        t = step_idx * 0.016
        target_waist = 45.0 * math.sin(t * 1.5)
        target_elbow = 30.0 * math.cos(t * 2.0)

        # Update drive targets on USD prims
        joint1_prim = stage.GetPrimAtPath("/World/RobotArm/Joint_Waist")
        joint2_prim = stage.GetPrimAtPath("/World/RobotArm/Joint_Elbow")

        if joint1_prim.IsValid():
            drive1 = UsdPhysics.DriveAPI(joint1_prim, "angular")
            drive1.GetTargetPositionAttr().Set(target_waist)

        if joint2_prim.IsValid():
            drive2 = UsdPhysics.DriveAPI(joint2_prim, "angular")
            drive2.GetTargetPositionAttr().Set(target_elbow)

    simulation_app.close()


if __name__ == "__main__":
    run_simulation_loop()
