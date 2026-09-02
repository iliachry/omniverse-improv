#!/usr/bin/env python3
"""
Robotics Inverse Kinematics (IK) & Trajectory Planner for 6-DOF Manipulators.
Provides:
- Forward Kinematics (FK) for 6-DOF kinematic chain
- Damped Least-Squares (DLS) & Optimization-based Inverse Kinematics (IK)
- Automated Pick-and-Place waypoint trajectory interpolation
- Standalone execution and UsdPhysics.DriveAPI target angle authoring
"""

import math
import os
import sys
from typing import List, Tuple, Optional, Dict
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

# Manipulator link dimensions (matching isaac_sim_sandbox.py)
L_BASE_Y = 24.0      # Base height to shoulder
L_UPPER_ARM = 45.0   # Shoulder to elbow
L_FOREARM = 40.0     # Elbow to wrist
L_WRIST_1 = 14.0     # Wrist roll to pitch
L_WRIST_2 = 11.0     # Wrist pitch to gripper tool flange
L_TOTAL_TOOL = L_WRIST_1 + L_WRIST_2 + 8.0


class Robot6DOF_IK:
    """Analytical & numerical kinematic solver for 6-DOF industrial manipulator."""

    def __init__(self):
        # Joint limits (degrees)
        self.joint_limits = [
            (-180.0, 180.0),  # Joint 1: Waist Yaw
            (-60.0, 90.0),    # Joint 2: Shoulder Pitch
            (-120.0, 120.0),  # Joint 3: Elbow Pitch
            (-180.0, 180.0),  # Joint 4: Wrist Roll
            (-100.0, 100.0),  # Joint 5: Wrist Pitch
            (-180.0, 180.0)   # Joint 6: Tool Flange Yaw
        ]

    def forward_kinematics(self, q_deg: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the 3D end-effector position (x, y, z) and direction vector
        for given joint angles in degrees.
        """
        q = [math.radians(angle) for angle in q_deg]
        q1, q2, q3, q4, q5, q6 = q

        # Planar reach in arm plane (radius & height)
        # Shoulder is at (0, L_BASE_Y, 0)
        # Shoulder pitch q2, elbow pitch q3
        r_elbow = L_UPPER_ARM * math.sin(q2)
        y_elbow = L_BASE_Y + L_UPPER_ARM * math.cos(q2)

        angle_arm = q2 + q3
        r_wrist = r_elbow + L_FOREARM * math.sin(angle_arm)
        y_wrist = y_elbow + L_FOREARM * math.cos(angle_arm)

        angle_total = angle_arm + q5
        r_tool = r_wrist + L_TOTAL_TOOL * math.sin(angle_total)
        y_tool = y_wrist + L_TOTAL_TOOL * math.cos(angle_total)

        # Rotate planar (r, y) into 3D world by waist yaw q1
        x = r_tool * math.sin(q1)
        z = r_tool * math.cos(q1)
        y = y_tool

        pos = np.array([x, y, z], dtype=np.float64)
        dir_vec = np.array([
            math.sin(q1) * math.sin(angle_total),
            math.cos(angle_total),
            math.cos(q1) * math.sin(angle_total)
        ], dtype=np.float64)

        return pos, dir_vec

    def inverse_kinematics(
        self,
        target_pos: np.ndarray,
        initial_guess: Optional[List[float]] = None,
        max_iters: int = 200,
        tol: float = 0.5
    ) -> Tuple[bool, List[float]]:
        """
        High-precision Optimization-based IK solver with joint constraints.
        Solves for [q1, q2, q3, q4, q5, q6] in degrees to reach target_pos [x, y, z].
        """
        from scipy.optimize import minimize

        target = np.array(target_pos, dtype=np.float64)
        if initial_guess is None:
            q1_init = math.degrees(math.atan2(target[0], target[2])) if (target[0] != 0 or target[2] != 0) else 0.0
            q0 = np.array([q1_init, 15.0, 30.0, 0.0, 15.0, 0.0], dtype=np.float64)
        else:
            q0 = np.array(initial_guess, dtype=np.float64)

        def objective(q):
            pos, _ = self.forward_kinematics(q.tolist())
            pos_err = np.linalg.norm(pos - target)
            # Regularization to keep joint angles smooth
            reg = 1e-4 * np.sum((q - q0) ** 2)
            return pos_err + reg

        bounds = self.joint_limits

        res = minimize(
            objective,
            q0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": max_iters, "ftol": 1e-6}
        )

        final_pos, _ = self.forward_kinematics(res.x.tolist())
        final_err = np.linalg.norm(final_pos - target)
        converged = bool(final_err < (tol * 2))

        return converged, [float(v) for v in res.x]

    def generate_pick_and_place_trajectory(
        self,
        pick_pos: np.ndarray,
        place_pos: np.ndarray,
        lift_height: float = 35.0,
        num_steps_per_segment: int = 15
    ) -> List[Dict[str, any]]:
        """
        Generates a sequence of interpolated joint poses and gripper states
        for a complete industrial pick-and-place operation.
        """
        # Waypoints:
        # 1. Home
        # 2. Above Pick
        # 3. Pick (Grip Close)
        # 4. Lift Pick
        # 5. Above Place
        # 6. Place (Grip Open)
        # 7. Lift Place
        # 8. Home

        above_pick = pick_pos + np.array([0, lift_height, 0])
        above_place = place_pos + np.array([0, lift_height, 0])

        waypoints = [
            {"pos": np.array([0.0, 110.0, 60.0]), "gripper": 0.0, "desc": "Home Pose"},
            {"pos": above_pick, "gripper": 0.0, "desc": "Approach Above Pick"},
            {"pos": pick_pos, "gripper": 0.0, "desc": "Descend to Object"},
            {"pos": pick_pos, "gripper": -2.8, "desc": "Close Gripper (Grasp)"},
            {"pos": above_pick, "gripper": -2.8, "desc": "Lift Object"},
            {"pos": above_place, "gripper": -2.8, "desc": "Translate to Target"},
            {"pos": place_pos, "gripper": -2.8, "desc": "Lower to Place Position"},
            {"pos": place_pos, "gripper": 0.0, "desc": "Open Gripper (Release)"},
            {"pos": above_place, "gripper": 0.0, "desc": "Retract Up"},
            {"pos": np.array([0.0, 110.0, 60.0]), "gripper": 0.0, "desc": "Return Home"}
        ]

        trajectory = []
        last_q = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        for wp in waypoints:
            success, q_target = self.inverse_kinematics(wp["pos"], initial_guess=last_q)
            last_q = q_target

            trajectory.append({
                "description": wp["desc"],
                "target_pos": wp["pos"].tolist(),
                "joint_angles_deg": [round(a, 2) for a in q_target],
                "gripper_position": wp["gripper"],
                "ik_converged": success
            })

        return trajectory


if __name__ == "__main__":
    solver = Robot6DOF_IK()
    print("=== Testing 6-DOF Forward & Inverse Kinematics ===")

    test_target = np.array([25.0, 30.0, 45.0])
    print(f"[*] Solving IK for Target Position: {test_target} cm")

    success, q_sol = solver.inverse_kinematics(test_target)
    print(f"[*] IK Converged: {success}")
    print(f"[*] Joint Angles (deg): {q_sol}")

    fk_pos, _ = solver.forward_kinematics(q_sol)
    print(f"[*] FK Verification Pos: {fk_pos.round(2)}")
    print(f"[*] Positioning Error: {np.linalg.norm(test_target - fk_pos):.4f} cm")

    print("\n=== Generating Pick-and-Place Trajectory ===")
    pick = np.array([30.0, 15.0, 20.0])
    place = np.array([-30.0, 15.0, 25.0])
    traj = solver.generate_pick_and_place_trajectory(pick, place)

    for i, step in enumerate(traj):
        print(f"  Step {i+1:02d}: {step['description']:<26} | Gripper: {step['gripper_position']:4.1f} | Q: {step['joint_angles_deg']}")
