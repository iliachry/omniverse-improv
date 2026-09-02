"""
Automated Test Suite for Advanced Features:
- 6-DOF Inverse Kinematics (IK) & Pick-and-Place Trajectories
- Prompt-to-USD Natural Language Procedural Generation
- YOLOv8 & COCO Synthetic Dataset Exporter
- Industrial Warehouse Digital Twin Generator
"""

import json
import os
import numpy as np
import pytest
from pxr import Usd

from robotics.ik_solver import Robot6DOF_IK
from usd_generators.prompt_to_usd import generate_usd_from_prompt, parse_prompt_keywords
from usd_generators.generate_warehouse_digital_twin import build_warehouse_digital_twin
from replicator.export_coco_yolo import export_yolo_format, export_coco_format


def test_inverse_kinematics_convergence():
    """Validates 6-DOF IK precision and forward kinematics consistency."""
    solver = Robot6DOF_IK()
    target_pos = np.array([20.0, 35.0, 40.0])

    converged, q_sol = solver.inverse_kinematics(target_pos, tol=0.5)
    assert converged is True

    fk_pos, _ = solver.forward_kinematics(q_sol)
    err = np.linalg.norm(target_pos - fk_pos)
    assert err < 1.0, f"IK positioning error too high: {err} cm"


def test_pick_and_place_trajectory_generation():
    """Validates pick-and-place waypoint trajectory sequence."""
    solver = Robot6DOF_IK()
    pick = np.array([25.0, 15.0, 20.0])
    place = np.array([-25.0, 15.0, 25.0])

    traj = solver.generate_pick_and_place_trajectory(pick, place)
    assert len(traj) == 10
    assert traj[0]["description"] == "Home Pose"
    assert traj[3]["gripper_position"] < 0  # Gripper closed for grasp
    assert traj[7]["gripper_position"] == 0  # Gripper open for release


def test_prompt_to_usd_generator(tmp_path):
    """Validates natural language prompt-to-USD generation."""
    out_file = str(tmp_path / "prompt_scene.usda")
    prompt = "cyberpunk neon arena with 6 glowing towers and floating emerald crystal"

    spec = parse_prompt_keywords(prompt)
    assert spec["theme"] == "cyberpunk"
    assert spec["item_count"] == 6
    assert spec["has_crystal"] is True

    result = generate_usd_from_prompt(prompt, out_file)
    assert os.path.exists(result)

    stage = Usd.Stage.Open(result)
    assert stage.GetPrimAtPath("/World/Architecture").IsValid()
    assert stage.GetPrimAtPath("/World/Architecture/CentralCore").IsValid()


def test_warehouse_digital_twin_generator(tmp_path):
    """Validates warehouse pallet racks and conveyor belt stage generation."""
    out_file = str(tmp_path / "warehouse.usda")
    result = build_warehouse_digital_twin(out_file)
    assert os.path.exists(result)

    stage = Usd.Stage.Open(result)
    assert stage.GetPrimAtPath("/World/RackingSystem").IsValid()
    assert stage.GetPrimAtPath("/World/ConveyorLine/MainBelt").IsValid()
    assert stage.GetPrimAtPath("/World/MobileFleet/AGV_Unit01").IsValid()


def test_yolo_and_coco_dataset_exporter(tmp_path):
    """Validates YOLO and COCO dataset export from synthetic frames."""
    # Create mock SDG annotations
    sdg_dir = tmp_path / "sdg_src"
    sdg_dir.mkdir()

    # Create dummy image
    img_name = "rgb_0000.png"
    (sdg_dir / img_name).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    annotations_data = {
        "totalFrames": 1,
        "frames": [{
            "frameIndex": 0,
            "rgbImage": img_name,
            "segmentationMask": img_name,
            "resolution": [640, 480],
            "objectsCount": 1,
            "annotations": [{
                "objectId": 1,
                "class": "cube",
                "box2d": [100, 100, 300, 300]
            }]
        }]
    }
    (sdg_dir / "dataset_annotations.json").write_text(json.dumps(annotations_data))

    # Test YOLO export
    yolo_dir = str(tmp_path / "yolo_out")
    export_yolo_format(str(sdg_dir), yolo_dir)
    assert os.path.exists(os.path.join(yolo_dir, "data.yaml"))
    assert os.path.exists(os.path.join(yolo_dir, "train", "labels", "rgb_0000.txt"))

    # Test COCO export
    coco_dir = str(tmp_path / "coco_out")
    export_coco_format(str(sdg_dir), coco_dir)
    coco_json = os.path.join(coco_dir, "annotations", "instances_train.json")
    assert os.path.exists(coco_json)

    with open(coco_json) as f:
        c_data = json.load(f)
    assert len(c_data["images"]) == 1
    assert len(c_data["annotations"]) == 1
    assert c_data["annotations"][0]["bbox"] == [100, 100, 200, 200]
