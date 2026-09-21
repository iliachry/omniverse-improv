"""
Automated Pytest Suite: BIM & Cesium Geospatial Integration.
Validates:
1. Standalone OpenUSD BIM generation with Cesium for Omniverse WGS84 georeferencing.
2. ISO 16739 IFC4-compliant hierarchy (IfcBuildingStorey, IfcColumn, IfcWall, IfcSlab, IfcDuctSegment, IfcSolarDevice).
3. BIM Property Sets (Psets) authoring and serialization.
4. OGC 3D Tiles 1.0 / 1.1 exporter and WGS84 bounding region calculations.
5. USD WebGL parser extraction of Cesium georeferences and BIM summaries.
"""

import json
import os
import sys
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from pxr import Usd, UsdGeom
from usd_generators.generate_bim_cesium_stage import build_bim_cesium_stage
from usd_generators.export_3dtiles import export_3dtiles, compute_bounding_region
from usd_viewer.usd_parser import parse_usd_stage


def test_bim_cesium_stage_generation(tmp_path):
    """Verifies generation of georeferenced BIM stage with IFC hierarchy, disciplines, and Psets."""
    stage_path = str(tmp_path / "test_facility.usda")
    res_path = build_bim_cesium_stage(
        output_path=stage_path,
        latitude=37.9753,
        longitude=23.7361,
        height_wgs84=120.0
    )

    assert os.path.exists(res_path), "BIM USD stage was not created"
    stage = Usd.Stage.Open(res_path)
    assert stage, "Failed to open authored BIM USD stage"

    # 1. Cesium Georeference Validation
    georef = stage.GetPrimAtPath("/World/CesiumGeoreference")
    assert georef.IsValid(), "/World/CesiumGeoreference prim missing"
    assert pytest.approx(float(georef.GetAttribute("cesium:latitude").Get()), 0.0001) == 37.9753
    assert pytest.approx(float(georef.GetAttribute("cesium:longitude").Get()), 0.0001) == 23.7361
    assert float(georef.GetAttribute("cesium:height").Get()) == 120.0
    assert str(georef.GetAttribute("cesium:georeferenceBinding").Get()) == "WGS84"

    # 2. Facility Cesium Anchor Validation
    facility = stage.GetPrimAtPath("/World/BIM_Facility")
    assert facility.IsValid(), "/World/BIM_Facility prim missing"
    api_schemas = facility.GetMetadata("apiSchemas")
    items = (api_schemas.explicitItems if api_schemas else []) or (api_schemas.prependedItems if api_schemas else [])
    assert "CesiumGlobeAnchorAPI" in items
    assert pytest.approx(float(facility.GetAttribute("cesium:anchor:latitude").Get()), 0.0001) == 37.9753

    # 3. Storeys Hierarchy Validation
    expected_storeys = ["Storey_00_Ground", "Storey_01_Lab", "Storey_02_Offices", "Storey_03_Rooftop"]
    for s in expected_storeys:
        s_prim = stage.GetPrimAtPath(f"/World/BIM_Facility/{s}")
        assert s_prim.IsValid(), f"Storey {s} missing from stage"
        assert str(s_prim.GetAttribute("bim:ifcClass").Get()) == "IfcBuildingStorey"

        # Check sub-disciplines
        assert stage.GetPrimAtPath(f"/World/BIM_Facility/{s}/Structural").IsValid()
        assert stage.GetPrimAtPath(f"/World/BIM_Facility/{s}/Architectural").IsValid()
        assert stage.GetPrimAtPath(f"/World/BIM_Facility/{s}/MEP").IsValid()

    # 4. Property Sets (Psets) Validation
    slab_prim = stage.GetPrimAtPath("/World/BIM_Facility/Storey_00_Ground/Structural/FoundationSlab")
    assert slab_prim.IsValid()
    assert str(slab_prim.GetAttribute("bim:ifcClass").Get()) == "IfcSlab"
    assert str(slab_prim.GetAttribute("bim:discipline").Get()) == "Structural"
    assert slab_prim.GetAttribute("bim:pset:Pset_SlabCommon:LoadBearing").Get() is True

    duct_prim = stage.GetPrimAtPath("/World/BIM_Facility/Storey_00_Ground/MEP/HVAC_MainSupplyDuct_G")
    assert duct_prim.IsValid()
    assert str(duct_prim.GetAttribute("bim:ifcClass").Get()) == "IfcDuctSegment"
    assert "5400" in str(duct_prim.GetAttribute("bim:pset:Pset_DuctCommon:AirFlowRate").Get())

    solar_prim = stage.GetPrimAtPath("/World/BIM_Facility/Storey_03_Rooftop/MEP/SolarArray_R1_P1")
    assert solar_prim.IsValid()
    assert str(solar_prim.GetAttribute("bim:ifcClass").Get()) == "IfcSolarDevice"


def test_bounding_region_math():
    """Verifies computation of WGS84 Cartographic Bounding Region in radians & meters."""
    region = compute_bounding_region(
        center_lat_deg=37.9753,
        center_lon_deg=23.7361,
        base_height_m=120.0,
        dx_meters=16.0,
        dz_meters=12.0,
        dy_meters=15.0
    )

    assert len(region) == 6
    west, south, east, north, min_h, max_h = region
    assert west < east, "West longitude must be strictly less than east"
    assert south < north, "South latitude must be strictly less than north"
    assert min_h == 120.0
    assert max_h == 135.0


def test_3dtiles_export(tmp_path):
    """Verifies OGC 3D Tileset export (tileset.json) from USD stage."""
    # First generate stage
    stage_path = str(tmp_path / "facility_for_tiles.usda")
    build_bim_cesium_stage(output_path=stage_path)

    # Export 3D Tiles
    out_dir = str(tmp_path / "3dtiles_out")
    tileset_file = export_3dtiles(stage_path=stage_path, output_dir=out_dir)

    assert os.path.exists(tileset_file)
    with open(tileset_file, "r", encoding="utf-8") as f:
        tileset = json.load(f)

    assert tileset["asset"]["version"] == "1.0"
    assert "region" in tileset["root"]["boundingVolume"]
    assert tileset["root"]["metadata"]["totalStoreys"] == 4
    assert tileset["root"]["metadata"]["totalElements"] >= 50
    assert len(tileset["root"]["children"]) == 4

    for child in tileset["root"]["children"]:
        assert "region" in child["boundingVolume"]
        assert child["metadata"]["elementCount"] > 0
        assert len(child["metadata"]["disciplines"]) > 0


def test_usd_parser_bim_cesium_extraction():
    """Verifies parser serialization of Cesium georeference and BIM metadata."""
    # Ensure default stage exists
    default_stage = os.path.join(WORKSPACE_DIR, "usd_generators", "output_bim_cesium.usda")
    if not os.path.exists(default_stage):
        build_bim_cesium_stage(output_path=default_stage)

    data = parse_usd_stage(default_stage)

    # Check Cesium metadata
    assert data["cesium"] is not None
    assert pytest.approx(data["cesium"]["latitude"], 0.001) == 37.9753
    assert pytest.approx(data["cesium"]["longitude"], 0.001) == 23.7361
    assert data["cesium"]["height"] == 120.0
    assert data["cesium"]["binding"] == "WGS84"

    # Check BIM Summary
    assert data["bimSummary"] is not None
    assert data["bimSummary"]["elementCount"] >= 50
    assert "Storey_00_Ground" in data["bimSummary"]["storeys"]
    assert "Structural" in data["bimSummary"]["disciplines"]
    assert "Architectural" in data["bimSummary"]["disciplines"]
    assert "MEP" in data["bimSummary"]["disciplines"]

    # Check Prim-level BIM attributes
    bim_prims = [p for p in data["prims"] if p.get("bim")]
    assert len(bim_prims) == data["bimSummary"]["elementCount"]

    first_col = next((p for p in bim_prims if p["bim"]["ifcClass"] == "IfcColumn"), None)
    assert first_col is not None
    assert first_col["bim"]["discipline"] == "Structural"
    assert "Pset_ColumnCommon:LoadBearing" in first_col["bim"]["psets"]
