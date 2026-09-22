"""Unit tests for the centralized core OpenUSD and BIM libraries.
Tests core.openusd.stage_utils, core.bim.spatial_clash,
core.bim.phasing_schedule, and core.bim.facility_builder.
"""

from __future__ import annotations

import json
import os
import pytest
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from core.openusd.stage_utils import (
    create_stage,
    setup_physics_scene,
    create_pbr_material,
    bind_material,
    add_dome_light,
    add_distant_light,
    add_ground_plane,
)
from core.bim.spatial_clash import (
    AABB,
    compute_prim_aabb,
    detect_bim_clashes,
    export_bcf_report,
)
from core.bim.phasing_schedule import (
    DEFAULT_MILESTONES,
    aggregate_construction_phasing,
)
from core.bim.facility_builder import (
    tag_bim_element,
    add_cube_element,
    add_cylinder_element,
)


def test_stage_utils_lifecycle(tmp_path):
    """Verifies OpenUSD stage initialization, physics scene, lights, and materials."""
    stage_path = str(tmp_path / "test_stage.usda")
    stage = create_stage(stage_path, up_axis="Y", meters_per_unit=0.01)

    assert stage is not None
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.y
    assert UsdGeom.GetStageMetersPerUnit(stage) == 0.01

    # Physics scene
    setup_physics_scene(stage, gravity_magnitude=981.0)
    physics_prim = stage.GetPrimAtPath("/World/PhysicsScene")
    assert physics_prim.IsValid()
    scene_api = UsdPhysics.Scene(physics_prim)
    assert scene_api.GetGravityMagnitudeAttr().Get() == 981.0

    # PBR Material
    mat = create_pbr_material(
        stage,
        "/World/Looks/TestConcrete",
        diffuse_color=(0.5, 0.5, 0.5),
        roughness=0.7,
        metallic=0.1,
    )
    assert mat.GetPrim().IsValid()

    # Lights
    dome = add_dome_light(stage, intensity=1200.0)
    assert dome.GetPrim().IsValid()
    distant = add_distant_light(stage, intensity=3000.0, rotation_xyz=(-45.0, 45.0, 0.0))
    assert distant.GetPrim().IsValid()

    # Ground Plane
    plane = add_ground_plane(stage, size=2000.0, material_path=mat)
    assert plane.GetPrim().IsValid()

    stage.GetRootLayer().Save()
    assert os.path.exists(stage_path)


def test_spatial_clash_aabb_and_intersections():
    """Tests AABB dataclass, prim bounding box calculation, and clash detection."""
    # AABB dataclass
    aabb = AABB(0.0, 0.0, 0.0, 10.0, 20.0, 30.0)
    t = aabb.to_tuple()
    assert t == (0.0, 0.0, 0.0, 10.0, 20.0, 30.0)
    assert AABB.from_tuple(t) == aabb

    # Prim AABB calculations
    cube_prim = {
        "name": "Beam_01",
        "type": "Cube",
        "position": [100.0, 200.0, 300.0],
        "scale": [2.0, 4.0, 1.0],
        "geomProps": {"size": 50.0},
    }
    # size=50: hx = 50*2*0.5 = 50, hy = 50*4*0.5 = 100, hz = 50*1*0.5 = 25
    box = compute_prim_aabb(cube_prim)
    assert box == (50.0, 100.0, 275.0, 150.0, 300.0, 325.0)

    # Cylinder X-axis prim
    cyl_prim_x = {
        "name": "Sprinkler_Pipe",
        "type": "Cylinder",
        "position": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "geomProps": {"radius": 10.0, "height": 100.0, "axis": "X"},
    }
    box_cyl = compute_prim_aabb(cyl_prim_x)
    assert box_cyl == (-50.0, -10.0, -10.0, 50.0, 10.0, 10.0)

    # Detect clash between MEP duct and Structural column
    mep_elem = {
        "name": "HVAC_Main_Duct",
        "path": "/World/BIM/Storey_00/HVAC_Main_Duct",
        "type": "Cube",
        "position": [50.0, 50.0, 50.0],
        "scale": [1.0, 1.0, 1.0],
        "geomProps": {"size": 40.0},  # [30, 70] in all axes
        "bim": {
            "discipline": "MEP",
            "ifcClass": "IfcFlowSegment",
            "storey": "Storey_00_Ground",
        },
    }
    struct_col = {
        "name": "Column_C1",
        "path": "/World/BIM/Storey_00/Column_C1",
        "type": "Cube",
        "position": [60.0, 50.0, 50.0],
        "scale": [1.0, 1.0, 1.0],
        "geomProps": {"size": 40.0},  # [40, 80] in all axes -> overlap [40, 70] = 30cm penetration
        "bim": {
            "discipline": "Structural",
            "ifcClass": "IfcColumn",
            "storey": "Storey_00_Ground",
        },
    }

    clashes = detect_bim_clashes([mep_elem, struct_col], tolerance_cm=2.0)
    assert len(clashes) == 1
    clash = clashes[0]
    assert clash["id"] == "CLASH-001"
    assert clash["severity"] == "CRITICAL"  # pen_depth = 30cm >= 15cm
    assert clash["penetrationDepthCm"] == 30.0
    assert clash["elementA"]["name"] == "HVAC_Main_Duct"
    assert clash["elementB"]["name"] == "Column_C1"


def test_bcf_export(tmp_path):
    """Verifies exporting clash records to BCF 2.1 JSON schema."""
    clashes = [
        {
            "id": "CLASH-001",
            "title": "Clash: HVAC vs Column",
            "severity": "CRITICAL",
            "storey": "Storey_00_Ground",
            "description": "Hard collision",
            "mitigation": "Reroute duct",
            "penetrationDepthCm": 25.0,
            "overlapVolumeCm3": 5000.0,
            "centroid": [55.0, 50.0, 50.0],
            "overlapExtents": [25.0, 20.0, 10.0],
            "elementA": {"name": "HVAC", "path": "/A", "discipline": "MEP", "ifcClass": "IfcFlowSegment"},
            "elementB": {"name": "Col", "path": "/B", "discipline": "Structural", "ifcClass": "IfcColumn"},
            "bcfMetadata": {"topicType": "Clash", "topicStatus": "Active", "priority": "High"},
        }
    ]
    out_file = str(tmp_path / "test_bcf.json")
    res = export_bcf_report(clashes, out_file)
    assert os.path.exists(res)

    with open(res, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["version"] == "BCF-API 2.1 JSON"
    assert data["topicCount"] == 1
    assert data["topics"][0]["guid"] == "CLASH-001"
    assert data["topics"][0]["viewpoint"]["cameraViewPoint"] == [55.0, 50.0, 50.0]


def test_phasing_schedule_engine():
    """Tests 4D construction phasing timeline calculation and metrics."""
    assert aggregate_construction_phasing([]) is None

    elements = [
        {"name": "Slab", "bim": {"constructionMonth": 0}},
        {"name": "Col_1", "bim": {"constructionMonth": 2}},
        {"name": "Col_2", "bim": {"constructionMonth": 2}},
        {"name": "Beam_1", "bim": {"constructionMonth": 4}},
        {"name": "Roof", "bim": {"constructionMonth": 6}},
        {"name": "Facade", "bim": {"constructionMonth": 8}},
        {"name": "HVAC", "bim": {"constructionMonth": 10}},
        {"name": "Fitout", "bim": {"constructionMonth": 12}},
    ]

    schedule = aggregate_construction_phasing(elements)
    assert schedule is not None
    assert schedule["totalElements"] == 8
    assert len(schedule["milestones"]) == len(DEFAULT_MILESTONES)

    phase_0 = schedule["milestones"][0]
    assert phase_0["id"] == "phase-0"
    assert phase_0["elementCount"] == 1
    assert phase_0["cumulativeCount"] == 1

    phase_1 = schedule["milestones"][1]
    assert phase_1["id"] == "phase-1"
    assert phase_1["elementCount"] == 2
    assert phase_1["cumulativeCount"] == 3

    final_phase = schedule["milestones"][-1]
    assert final_phase["cumulativeCount"] == 8
    assert final_phase["progressPercent"] == 100


def test_facility_builder_components(tmp_path):
    """Tests parametric BIM builder for OpenUSD elements and metadata tagging."""
    stage_path = str(tmp_path / "facility_test.usda")
    stage = create_stage(stage_path)

    mat_path = create_pbr_material(stage, "/World/Looks/Concrete", (0.6, 0.6, 0.6))

    # Cube element
    cube = add_cube_element(
        stage,
        "/World/Facility/Foundation",
        pos=(0.0, -10.0, 0.0),
        size_xyz=(1000.0, 20.0, 1000.0),
        mat_path=mat_path,
        ifc_class="IfcSlab",
        discipline="Structural",
        storey="Storey_00_Ground",
        psets={"CompressiveStrength": "C40/50", "ThicknessMm": 200.0},
    )
    prim = cube.GetPrim()
    assert prim.IsValid()
    assert prim.GetAttribute("bim:ifcClass").Get() == "IfcSlab"
    assert prim.GetAttribute("bim:discipline").Get() == "Structural"
    assert prim.GetAttribute("bim:phase").Get() == "Phase 0: Substructure & Foundations"
    assert prim.GetAttribute("bim:constructionMonth").Get() == 0
    assert prim.GetAttribute("bim:pset:CompressiveStrength").Get() == "C40/50"
    assert prim.GetAttribute("bim:pset:ThicknessMm").Get() == 200.0

    # Cylinder element
    cyl = add_cylinder_element(
        stage,
        "/World/Facility/ChilledWaterPipe",
        pos=(100.0, 250.0, 0.0),
        radius=15.0,
        height=300.0,
        axis="X",
        mat_path=mat_path,
        ifc_class="IfcPipeSegment",
        discipline="MEP",
        storey="Storey_01_Lab",
        psets={"FluidType": "ChilledWater", "OperatingPressureBar": 6.5},
    )
    cyl_prim = cyl.GetPrim()
    assert cyl_prim.IsValid()
    assert cyl_prim.GetAttribute("bim:ifcClass").Get() == "IfcPipeSegment"
    assert cyl_prim.GetAttribute("bim:discipline").Get() == "MEP"
    assert cyl_prim.GetAttribute("bim:phase").Get() == "Phase 5: MEP Rough-in & Services"
    assert cyl_prim.GetAttribute("bim:constructionMonth").Get() == 10
    assert cyl_prim.GetAttribute("bim:pset:OperatingPressureBar").Get() == 6.5
