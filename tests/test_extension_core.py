"""
Automated Test Suite for Omniverse Kit Extension Core Logic.
Validates StageBuilder and PhysicsHelper operations in standalone OpenUSD mode.
"""

import os
import sys
import pytest
from pxr import Usd, UsdGeom, UsdPhysics

# Add exts directory to sys.path
exts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exts", "omni.improv.starter")
if exts_dir not in sys.path:
    sys.path.insert(0, exts_dir)

from omni.improv.starter.core.stage_builder import StageBuilder
from omni.improv.starter.core.physics_helper import PhysicsHelper


@pytest.fixture
def stage_in_memory():
    stage = Usd.Stage.CreateInMemory()
    StageBuilder.setup_stage_metadata(stage, meters_per_unit=0.01)
    return stage


def test_setup_studio_environment(stage_in_memory):
    """Tests studio ground, physics scene, and lighting creation."""
    StageBuilder.setup_studio_environment(stage_in_memory, add_ground=True, add_lighting=True)
    
    assert stage_in_memory.GetPrimAtPath("/World/PhysicsScene").IsValid()
    assert stage_in_memory.GetPrimAtPath("/World/Environment/GroundPlane").IsValid()
    assert stage_in_memory.GetPrimAtPath("/World/Environment/Lights/KeyLight").IsValid()
    assert stage_in_memory.GetPrimAtPath("/World/Environment/Lights/DomeLight").IsValid()


def test_spawn_block_tower(stage_in_memory):
    """Tests procedural Jenga-style block tower spawner."""
    StageBuilder.spawn_destructible_tower(stage_in_memory, "/World/Props/BlockTower", floors=6, blocks_per_floor=3)
    
    assert stage_in_memory.GetPrimAtPath("/World/Props/BlockTower").IsValid()
    # 6 floors * 3 blocks per floor = 18 blocks
    for floor in range(6):
        for block in range(3):
            b_prim = stage_in_memory.GetPrimAtPath(f"/World/Props/BlockTower/Floor_{floor:02d}_Block_{block}")
            assert b_prim.IsValid()
            assert b_prim.HasAPI(UsdPhysics.RigidBodyAPI)


def test_spawn_primitive_and_materials(stage_in_memory):
    """Tests primitive spawner and PBR material binding."""
    prim = StageBuilder.spawn_primitive(
        stage_in_memory,
        prim_type="Sphere",
        prim_path="/World/Props/DynamicSphere",
        position=(0.0, 50.0, 0.0),
        size=20.0,
        dynamic_physics=True,
        material_preset="neon_cyan"
    )
    
    assert prim.IsValid()
    assert prim.HasAPI(UsdPhysics.RigidBodyAPI)
    assert prim.HasAPI(UsdPhysics.CollisionAPI)
    assert stage_in_memory.GetPrimAtPath("/World/Materials/M_neon_cyan").IsValid()


def test_physics_helper_gravity_tweaker(stage_in_memory):
    """Tests dynamic gravity tuning on UsdPhysics.Scene."""
    PhysicsHelper.ensure_physics_scene(stage_in_memory, "/World/PhysicsScene", gravity_magnitude=981.0)
    
    # Switch to Moon gravity
    PhysicsHelper.set_gravity_preset(stage_in_memory, "/World/PhysicsScene", "moon")
    scene = UsdPhysics.Scene(stage_in_memory.GetPrimAtPath("/World/PhysicsScene"))
    assert scene.GetGravityMagnitudeAttr().Get() == pytest.approx(162.0, 0.1)

    # Switch to Zero-G
    PhysicsHelper.set_gravity_preset(stage_in_memory, "/World/PhysicsScene", "zero_g")
    assert scene.GetGravityMagnitudeAttr().Get() == 0.0
