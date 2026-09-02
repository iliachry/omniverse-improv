"""
Automated Test Suite for Standalone OpenUSD Stages and Procedural Generators.
Validates stage authoring, scene hierarchy, UsdShade materials, and UsdPhysics schemas.
"""

import os
import pytest
from pxr import Usd, UsdGeom, UsdShade, UsdLux, UsdPhysics

from usd_generators.generate_physics_playground import build_physics_playground
from usd_generators.generate_procedural_scene import build_procedural_scene
from usd_viewer.usd_parser import parse_usd_stage


@pytest.fixture(scope="session")
def generated_stages(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("stages")
    physics_stage_path = os.path.join(out_dir, "test_physics.usda")
    procedural_stage_path = os.path.join(out_dir, "test_procedural.usda")

    build_physics_playground(physics_stage_path)
    build_procedural_scene(procedural_stage_path)

    return {
        "physics": physics_stage_path,
        "procedural": procedural_stage_path,
    }


def test_physics_playground_generation(generated_stages):
    """Verifies that the Kinetic Physics Playground stage authors valid USD with PhysX schemas."""
    path = generated_stages["physics"]
    assert os.path.exists(path)

    stage = Usd.Stage.Open(path)
    assert stage is not None

    # Check Stage Metadata
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.y
    assert UsdGeom.GetStageMetersPerUnit(stage) == 0.01

    # Check Physics Scene
    phys_scene = stage.GetPrimAtPath("/World/PhysicsScene")
    assert phys_scene.IsValid()
    assert phys_scene.IsA(UsdPhysics.Scene)

    # Check Launch Ramp (Static Collider)
    ramp = stage.GetPrimAtPath("/World/Props/LaunchRamp")
    assert ramp.IsValid()
    assert ramp.HasAPI(UsdPhysics.CollisionAPI)

    # Check Trigger Sphere (Dynamic RigidBody with mass)
    ball = stage.GetPrimAtPath("/World/Props/TriggerSphere")
    assert ball.IsValid()
    assert ball.HasAPI(UsdPhysics.RigidBodyAPI)
    assert ball.HasAPI(UsdPhysics.CollisionAPI)
    assert ball.HasAPI(UsdPhysics.MassAPI)
    assert UsdPhysics.MassAPI(ball).GetMassAttr().Get() == 8.0

    # Check Domino Run
    domino_00 = stage.GetPrimAtPath("/World/Props/Dominoes/Domino_00")
    domino_31 = stage.GetPrimAtPath("/World/Props/Dominoes/Domino_31")
    assert domino_00.IsValid()
    assert domino_31.IsValid()
    assert domino_00.HasAPI(UsdPhysics.RigidBodyAPI)

    # Check Stacked Pyramid Target
    pyramid_base = stage.GetPrimAtPath("/World/Props/Pyramid/Level_0_Block_0")
    pyramid_top = stage.GetPrimAtPath("/World/Props/Pyramid/Level_4_Block_0")
    assert pyramid_base.IsValid()
    assert pyramid_top.IsValid()


def test_procedural_scene_generation(generated_stages):
    """Verifies the Procedural Sci-Fi Stage architecture, materials, and lighting."""
    path = generated_stages["procedural"]
    assert os.path.exists(path)

    stage = Usd.Stage.Open(path)
    assert stage is not None

    # Check Tiered Dais
    dais_0 = stage.GetPrimAtPath("/World/Architecture/Dais_Tier_0")
    dais_1 = stage.GetPrimAtPath("/World/Architecture/Dais_Tier_1")
    dais_2 = stage.GetPrimAtPath("/World/Architecture/Dais_Tier_2")
    assert dais_0.IsValid() and dais_1.IsValid() and dais_2.IsValid()

    # Check 8-Pillar Ring
    for i in range(8):
        pillar = stage.GetPrimAtPath(f"/World/Architecture/Pillar_{i:02d}")
        assert pillar.IsValid()
        assert stage.GetPrimAtPath(f"/World/Architecture/Pillar_{i:02d}/Shaft").IsValid()
        assert stage.GetPrimAtPath(f"/World/Architecture/Pillar_{i:02d}/NeonBand").IsValid()

    # Check Levitating Core & Satellites
    core_gem = stage.GetPrimAtPath("/World/Core/EnergyOrb")
    assert core_gem.IsValid()
    for s_idx in range(3):
        sat = stage.GetPrimAtPath(f"/World/Core/Satellite_{s_idx}")
        assert sat.IsValid()

    # Check Lighting Rig
    assert stage.GetPrimAtPath("/World/Environment/DomeLight").IsValid()
    assert stage.GetPrimAtPath("/World/Environment/KeyLight").IsValid()
    assert stage.GetPrimAtPath("/World/Environment/RimLight").IsValid()


def test_usd_parser_serialization(generated_stages):
    """Verifies that the USD WebGL parser serializes stages into valid web payloads."""
    for key, path in generated_stages.items():
        data = parse_usd_stage(path)
        assert data["stagePath"] == path
        assert data["metadata"]["primCount"] > 0
        assert data["metadata"]["materialCount"] > 0
        assert len(data["prims"]) > 0
        assert "hierarchy" in data
