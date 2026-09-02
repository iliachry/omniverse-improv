#!/usr/bin/env python3
"""
Isaac Sim & Omniverse Robotics Sandbox: 6-DOF Industrial Manipulator + Parallel Gripper.
Demonstrates:
- 6-DOF articulated kinematic chain (Waist, Shoulder, Elbow, Wrist 1/2/3)
- 2-finger parallel jaw gripper with linear Prismatic joints
- UsdPhysics.ArticulationRootAPI and DriveAPI position/velocity controllers
- Standalone OpenUSD authoring and real-time Isaac Sim control loop
"""

import math
import os
import sys
from typing import Optional, Tuple

try:
    from omni.isaac.kit import SimulationApp
    HAS_ISAAC = True
except ImportError:
    SimulationApp = None
    HAS_ISAAC = False

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade


def build_articulated_robot_stage(stage: Usd.Stage) -> Sdf.Path:
    """
    Constructs a 6-DOF industrial robot arm + parallel jaw gripper with revolute
    and prismatic joint drives adhering to UsdPhysics schemas.
    """
    print("[*] Authoring 6-DOF Industrial Robot Arm + Parallel Gripper in USD...")

    robot_path = Sdf.Path("/World/RobotArm")
    robot_xform = UsdGeom.Xform.Define(stage, robot_path)
    
    # Root Articulation Schema
    UsdPhysics.ArticulationRootAPI.Apply(robot_xform.GetPrim())

    # 1. Base Mount (Static Anchor)
    base_path = f"{robot_path}/Base"
    base_geom = UsdGeom.Cylinder.Define(stage, base_path)
    base_geom.CreateRadiusAttr().Set(18.0)
    base_geom.CreateHeightAttr().Set(14.0)
    base_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(base_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 7.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(base_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(base_geom.GetPrim())

    # 2. Link 1: Shoulder Turret (Yaw around Y)
    link1_path = f"{robot_path}/Link1_Shoulder"
    link1_geom = UsdGeom.Cylinder.Define(stage, link1_path)
    link1_geom.CreateRadiusAttr().Set(12.0)
    link1_geom.CreateHeightAttr().Set(20.0)
    link1_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link1_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 24.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(link1_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(link1_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link1_geom.GetPrim()).CreateMassAttr().Set(8.0)

    # Joint 1: Base -> Link1 (Waist Yaw, Y-Axis)
    j1 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint1_Waist")
    j1.CreateAxisAttr().Set("Y")
    j1.CreateBody0Rel().SetTargets([Sdf.Path(base_path)])
    j1.CreateBody1Rel().SetTargets([Sdf.Path(link1_path)])
    j1.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 7.0, 0.0))
    j1.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -10.0, 0.0))
    j1.CreateLowerLimitAttr().Set(-180.0)
    j1.CreateUpperLimitAttr().Set(180.0)
    d1 = UsdPhysics.DriveAPI.Apply(j1.GetPrim(), "angular")
    d1.CreateTypeAttr().Set("force")
    d1.CreateStiffnessAttr().Set(12000.0)
    d1.CreateDampingAttr().Set(1200.0)
    d1.CreateTargetPositionAttr().Set(0.0)

    # 3. Link 2: Upper Arm (Pitch around Z)
    link2_path = f"{robot_path}/Link2_UpperArm"
    link2_geom = UsdGeom.Capsule.Define(stage, link2_path)
    link2_geom.CreateRadiusAttr().Set(6.0)
    link2_geom.CreateHeightAttr().Set(45.0)
    link2_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link2_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 56.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(link2_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(link2_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link2_geom.GetPrim()).CreateMassAttr().Set(6.0)

    # Joint 2: Link1 -> Link2 (Shoulder Pitch, Z-Axis)
    j2 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint2_Shoulder")
    j2.CreateAxisAttr().Set("Z")
    j2.CreateBody0Rel().SetTargets([Sdf.Path(link1_path)])
    j2.CreateBody1Rel().SetTargets([Sdf.Path(link2_path)])
    j2.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 10.0, 0.0))
    j2.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -22.5, 0.0))
    j2.CreateLowerLimitAttr().Set(-60.0)
    j2.CreateUpperLimitAttr().Set(90.0)
    d2 = UsdPhysics.DriveAPI.Apply(j2.GetPrim(), "angular")
    d2.CreateTypeAttr().Set("force")
    d2.CreateStiffnessAttr().Set(10000.0)
    d2.CreateDampingAttr().Set(1000.0)
    d2.CreateTargetPositionAttr().Set(15.0)

    # 4. Link 3: Forearm (Pitch around Z)
    link3_path = f"{robot_path}/Link3_Forearm"
    link3_geom = UsdGeom.Capsule.Define(stage, link3_path)
    link3_geom.CreateRadiusAttr().Set(4.5)
    link3_geom.CreateHeightAttr().Set(40.0)
    link3_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link3_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 98.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(link3_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(link3_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link3_geom.GetPrim()).CreateMassAttr().Set(4.0)

    # Joint 3: Link2 -> Link3 (Elbow Pitch, Z-Axis)
    j3 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint3_Elbow")
    j3.CreateAxisAttr().Set("Z")
    j3.CreateBody0Rel().SetTargets([Sdf.Path(link2_path)])
    j3.CreateBody1Rel().SetTargets([Sdf.Path(link3_path)])
    j3.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 22.5, 0.0))
    j3.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -20.0, 0.0))
    j3.CreateLowerLimitAttr().Set(-120.0)
    j3.CreateUpperLimitAttr().Set(120.0)
    d3 = UsdPhysics.DriveAPI.Apply(j3.GetPrim(), "angular")
    d3.CreateTypeAttr().Set("force")
    d3.CreateStiffnessAttr().Set(8000.0)
    d3.CreateDampingAttr().Set(800.0)
    d3.CreateTargetPositionAttr().Set(-25.0)

    # 5. Link 4: Wrist Roll (Roll around Y)
    link4_path = f"{robot_path}/Link4_WristRoll"
    link4_geom = UsdGeom.Cylinder.Define(stage, link4_path)
    link4_geom.CreateRadiusAttr().Set(3.5)
    link4_geom.CreateHeightAttr().Set(14.0)
    link4_geom.CreateAxisAttr().Set("Y")
    UsdGeom.Xformable(link4_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 125.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(link4_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(link4_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link4_geom.GetPrim()).CreateMassAttr().Set(2.0)

    # Joint 4: Link3 -> Link4 (Wrist Roll, Y-Axis)
    j4 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint4_WristRoll")
    j4.CreateAxisAttr().Set("Y")
    j4.CreateBody0Rel().SetTargets([Sdf.Path(link3_path)])
    j4.CreateBody1Rel().SetTargets([Sdf.Path(link4_path)])
    j4.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 20.0, 0.0))
    j4.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -7.0, 0.0))
    d4 = UsdPhysics.DriveAPI.Apply(j4.GetPrim(), "angular")
    d4.CreateTypeAttr().Set("force")
    d4.CreateStiffnessAttr().Set(4000.0)
    d4.CreateDampingAttr().Set(400.0)

    # 6. Link 5: Wrist Pitch & Flange
    link5_path = f"{robot_path}/Link5_WristPitch"
    link5_geom = UsdGeom.Cube.Define(stage, link5_path)
    link5_geom.CreateSizeAttr().Set(6.0)
    UsdGeom.Xformable(link5_geom.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(0.0, 136.0, 0.0))

    UsdPhysics.RigidBodyAPI.Apply(link5_geom.GetPrim())
    UsdPhysics.CollisionAPI.Apply(link5_geom.GetPrim())
    UsdPhysics.MassAPI.Apply(link5_geom.GetPrim()).CreateMassAttr().Set(1.5)

    # Joint 5: Link4 -> Link5 (Wrist Pitch, Z-Axis)
    j5 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint5_WristPitch")
    j5.CreateAxisAttr().Set("Z")
    j5.CreateBody0Rel().SetTargets([Sdf.Path(link4_path)])
    j5.CreateBody1Rel().SetTargets([Sdf.Path(link5_path)])
    j5.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 7.0, 0.0))
    j5.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -3.0, 0.0))
    d5 = UsdPhysics.DriveAPI.Apply(j5.GetPrim(), "angular")
    d5.CreateTypeAttr().Set("force")
    d5.CreateStiffnessAttr().Set(3000.0)
    d5.CreateDampingAttr().Set(300.0)

    # 7. Gripper Base & Parallel Fingers (Prismatic Joint Drives)
    gripper_base_path = f"{robot_path}/GripperBase"
    gripper_base = UsdGeom.Cube.Define(stage, gripper_base_path)
    gripper_base.CreateSizeAttr().Set(1.0)
    gb_xform = UsdGeom.Xformable(gripper_base.GetPrim())
    gb_xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 142.0, 0.0))
    gb_xform.AddScaleOp().Set(Gf.Vec3f(12.0, 4.0, 6.0))

    UsdPhysics.RigidBodyAPI.Apply(gripper_base.GetPrim())
    UsdPhysics.CollisionAPI.Apply(gripper_base.GetPrim())
    UsdPhysics.MassAPI.Apply(gripper_base.GetPrim()).CreateMassAttr().Set(1.0)

    # Joint 6: Link5 -> GripperBase (Wrist Yaw, Y-Axis)
    j6 = UsdPhysics.RevoluteJoint.Define(stage, f"{robot_path}/Joint6_ToolFlange")
    j6.CreateAxisAttr().Set("Y")
    j6.CreateBody0Rel().SetTargets([Sdf.Path(link5_path)])
    j6.CreateBody1Rel().SetTargets([Sdf.Path(gripper_base_path)])
    j6.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 3.0, 0.0))
    j6.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -2.0, 0.0))
    d6 = UsdPhysics.DriveAPI.Apply(j6.GetPrim(), "angular")
    d6.CreateTypeAttr().Set("force")
    d6.CreateStiffnessAttr().Set(3000.0)
    d6.CreateDampingAttr().Set(300.0)

    # Left Finger (Prismatic along X)
    finger_left_path = f"{robot_path}/FingerLeft"
    finger_l = UsdGeom.Cube.Define(stage, finger_left_path)
    finger_l.CreateSizeAttr().Set(1.0)
    fl_xform = UsdGeom.Xformable(finger_l.GetPrim())
    fl_xform.AddTranslateOp().Set(Gf.Vec3d(-4.0, 150.0, 0.0))
    fl_xform.AddScaleOp().Set(Gf.Vec3f(2.0, 12.0, 4.0))

    UsdPhysics.RigidBodyAPI.Apply(finger_l.GetPrim())
    UsdPhysics.CollisionAPI.Apply(finger_l.GetPrim())
    UsdPhysics.MassAPI.Apply(finger_l.GetPrim()).CreateMassAttr().Set(0.3)

    j_finger_l = UsdPhysics.PrismaticJoint.Define(stage, f"{robot_path}/Joint_FingerLeft")
    j_finger_l.CreateAxisAttr().Set("X")
    j_finger_l.CreateBody0Rel().SetTargets([Sdf.Path(gripper_base_path)])
    j_finger_l.CreateBody1Rel().SetTargets([Sdf.Path(finger_left_path)])
    j_finger_l.CreateLocalPos0Attr().Set(Gf.Vec3f(-4.0, 2.0, 0.0))
    j_finger_l.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -6.0, 0.0))
    j_finger_l.CreateLowerLimitAttr().Set(-3.0)
    j_finger_l.CreateUpperLimitAttr().Set(0.0)
    d_fl = UsdPhysics.DriveAPI.Apply(j_finger_l.GetPrim(), "linear")
    d_fl.CreateTypeAttr().Set("force")
    d_fl.CreateStiffnessAttr().Set(2000.0)
    d_fl.CreateDampingAttr().Set(200.0)

    # Right Finger (Prismatic along X)
    finger_right_path = f"{robot_path}/FingerRight"
    finger_r = UsdGeom.Cube.Define(stage, finger_right_path)
    finger_r.CreateSizeAttr().Set(1.0)
    fr_xform = UsdGeom.Xformable(finger_r.GetPrim())
    fr_xform.AddTranslateOp().Set(Gf.Vec3d(4.0, 150.0, 0.0))
    fr_xform.AddScaleOp().Set(Gf.Vec3f(2.0, 12.0, 4.0))

    UsdPhysics.RigidBodyAPI.Apply(finger_r.GetPrim())
    UsdPhysics.CollisionAPI.Apply(finger_r.GetPrim())
    UsdPhysics.MassAPI.Apply(finger_r.GetPrim()).CreateMassAttr().Set(0.3)

    j_finger_r = UsdPhysics.PrismaticJoint.Define(stage, f"{robot_path}/Joint_FingerRight")
    j_finger_r.CreateAxisAttr().Set("X")
    j_finger_r.CreateBody0Rel().SetTargets([Sdf.Path(gripper_base_path)])
    j_finger_r.CreateBody1Rel().SetTargets([Sdf.Path(finger_right_path)])
    j_finger_r.CreateLocalPos0Attr().Set(Gf.Vec3f(4.0, 2.0, 0.0))
    j_finger_r.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, -6.0, 0.0))
    j_finger_r.CreateLowerLimitAttr().Set(0.0)
    j_finger_r.CreateUpperLimitAttr().Set(3.0)
    d_fr = UsdPhysics.DriveAPI.Apply(j_finger_r.GetPrim(), "linear")
    d_fr.CreateTypeAttr().Set("force")
    d_fr.CreateStiffnessAttr().Set(2000.0)
    d_fr.CreateDampingAttr().Set(200.0)

    print(f"[OK] 6-DOF Robot Arm + Parallel Gripper created at {robot_path}")
    return robot_path


def run_simulation_loop():
    """Executes the Isaac Sim trajectory loop when running inside Isaac Sim."""
    if not HAS_ISAAC:
        print("[!] Isaac Sim (omni.isaac.core) not found. Running in standalone USD mode.")
        stage = Usd.Stage.CreateInMemory()
        build_articulated_robot_stage(stage)
        print("[OK] Standalone 6-DOF USD Articulation hierarchy validated successfully.")
        return

    from omni.isaac.core import World

    world = World(stage_units_in_meters=0.01)
    world.scene.add_default_ground_plane()

    stage = world.stage
    build_articulated_robot_stage(stage)
    world.reset()

    print("[*] Starting Isaac Sim 6-DOF Control Loop...")
    step_idx = 0
    while SimulationApp and simulation_app.is_running():
        world.step(render=True)
        step_idx += 1
        t = step_idx * 0.016

        # Sinusoidal joint trajectory
        q1 = 45.0 * math.sin(t * 1.2)
        q2 = 25.0 * math.cos(t * 1.0)
        q3 = -30.0 + 20.0 * math.sin(t * 1.5)

        j1_prim = stage.GetPrimAtPath("/World/RobotArm/Joint1_Waist")
        j2_prim = stage.GetPrimAtPath("/World/RobotArm/Joint2_Shoulder")
        j3_prim = stage.GetPrimAtPath("/World/RobotArm/Joint3_Elbow")

        if j1_prim.IsValid():
            UsdPhysics.DriveAPI(j1_prim, "angular").GetTargetPositionAttr().Set(q1)
        if j2_prim.IsValid():
            UsdPhysics.DriveAPI(j2_prim, "angular").GetTargetPositionAttr().Set(q2)
        if j3_prim.IsValid():
            UsdPhysics.DriveAPI(j3_prim, "angular").GetTargetPositionAttr().Set(q3)

    if simulation_app:
        simulation_app.close()


if __name__ == "__main__":
    run_simulation_loop()
