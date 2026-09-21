#!/usr/bin/env python3
"""
Standalone OpenUSD Script: Georeferenced Smart Tech Campus BIM Facility.
Authors a multi-storey Building Information Model (BIM) in OpenUSD with:
- Cesium for Omniverse WGS84 Georeferencing (CesiumGeoreference & CesiumGlobeAnchorAPI)
- ISO 16739 IFC4-compliant semantic hierarchy (IfcBuildingStorey, IfcColumn, IfcWall, IfcSlab, IfcDuctSegment, IfcSolarDevice)
- Multi-discipline separation: Structural (concrete/steel frame), Architectural (curtain walling, partitions, doors), MEP (HVAC chillers, ductwork, piping, solar PV arrays)
- Rich BIM Property Sets (Psets): FireRating, ThermalTransmittance, ConcreteGrade, PeakPower
- Production-grade PBR materials (architectural glass, galvanized steel, solar silicon, polished concrete)
"""

import argparse
import math
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from utils_usd import (
    create_stage,
    setup_physics_scene,
    create_pbr_material,
    bind_material,
    add_dome_light,
    add_distant_light,
    add_ground_plane
)


def tag_bim_element(
    prim: Usd.Prim,
    ifc_class: str,
    discipline: str,
    storey: str,
    psets: dict = None
) -> None:
    """Applies IFC-standard BIM classification and custom property sets to a USD prim."""
    prim.CreateAttribute("bim:ifcClass", Sdf.ValueTypeNames.String).Set(ifc_class)
    prim.CreateAttribute("bim:discipline", Sdf.ValueTypeNames.String).Set(discipline)
    prim.CreateAttribute("bim:storey", Sdf.ValueTypeNames.String).Set(storey)

    if psets:
        for key, val in psets.items():
            attr_name = f"bim:pset:{key}"
            if isinstance(val, bool):
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Bool).Set(val)
            elif isinstance(val, float):
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float).Set(val)
            elif isinstance(val, int):
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Int).Set(val)
            else:
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String).Set(str(val))


def add_cube_element(
    stage: Usd.Stage,
    path: str,
    pos: tuple,
    size_xyz: tuple,
    mat_path: str,
    ifc_class: str,
    discipline: str,
    storey: str,
    psets: dict = None,
    is_collider: bool = True
) -> UsdGeom.Cube:
    """Creates a scaled box primitive with material binding, BIM tags, and collision."""
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr().Set(1.0)
    
    xform = UsdGeom.Xformable(cube.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    xform.AddScaleOp().Set(Gf.Vec3f(*size_xyz))

    bind_material(cube.GetPrim(), mat_path)
    tag_bim_element(cube.GetPrim(), ifc_class, discipline, storey, psets)

    if is_collider:
        col = UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        col.CreateCollisionEnabledAttr().Set(True)

    return cube


def add_cylinder_element(
    stage: Usd.Stage,
    path: str,
    pos: tuple,
    radius: float,
    height: float,
    axis: str,
    mat_path: str,
    ifc_class: str,
    discipline: str,
    storey: str,
    rot_xyz: tuple = (0.0, 0.0, 0.0),
    psets: dict = None
) -> UsdGeom.Cylinder:
    """Creates a cylinder element (for columns or pipes) with BIM metadata."""
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateRadiusAttr().Set(radius)
    cyl.CreateHeightAttr().Set(height)
    cyl.CreateAxisAttr().Set(axis)

    xform = UsdGeom.Xformable(cyl.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    if rot_xyz != (0.0, 0.0, 0.0):
        xform.AddRotateXYZOp().Set(Gf.Vec3d(*rot_xyz))

    bind_material(cyl.GetPrim(), mat_path)
    tag_bim_element(cyl.GetPrim(), ifc_class, discipline, storey, psets)
    return cyl


def build_bim_cesium_stage(
    output_path: str = "output_bim_cesium.usda",
    latitude: float = 37.9753,
    longitude: float = 23.7361,
    height_wgs84: float = 120.0
) -> str:
    """
    Constructs the complete georeferenced BIM facility OpenUSD stage.
    """
    print(f"[*] Authoring Georeferenced BIM Facility USD Stage...")
    print(f"    Target File: {output_path}")
    print(f"    Cesium WGS84 Georeference: Lat {latitude:.4f}, Lon {longitude:.4f}, Alt {height_wgs84:.1f}m")

    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except OSError:
            pass

    # Standard Omniverse cm scale (metersPerUnit = 0.01)
    stage = create_stage(output_path, up_axis="Y", meters_per_unit=0.01)

    # 1. Cesium Georeference & Root Schemas
    # -------------------------------------------------------------
    UsdGeom.Xform.Define(stage, "/World")
    
    # Author CesiumGeoreference prim
    georef_prim = stage.DefinePrim("/World/CesiumGeoreference", "CesiumGeoreference")
    georef_prim.SetMetadata("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["CesiumGeoreferenceAPI"]))
    georef_prim.CreateAttribute("cesium:latitude", Sdf.ValueTypeNames.Double).Set(latitude)
    georef_prim.CreateAttribute("cesium:longitude", Sdf.ValueTypeNames.Double).Set(longitude)
    georef_prim.CreateAttribute("cesium:height", Sdf.ValueTypeNames.Double).Set(height_wgs84)
    georef_prim.CreateAttribute("cesium:georeferenceBinding", Sdf.ValueTypeNames.Token).Set("WGS84")

    # Author Facility with CesiumGlobeAnchorAPI
    facility_prim = UsdGeom.Xform.Define(stage, "/World/BIM_Facility").GetPrim()
    facility_prim.SetMetadata("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["CesiumGlobeAnchorAPI"]))
    facility_prim.CreateAttribute("cesium:anchor:latitude", Sdf.ValueTypeNames.Double).Set(latitude)
    facility_prim.CreateAttribute("cesium:anchor:longitude", Sdf.ValueTypeNames.Double).Set(longitude)
    facility_prim.CreateAttribute("cesium:anchor:height", Sdf.ValueTypeNames.Double).Set(height_wgs84)
    facility_prim.CreateAttribute("cesium:anchor:adjustOrientationForGlobeWhenMoving", Sdf.ValueTypeNames.Bool).Set(True)

    # 2. Materials Library
    # -------------------------------------------------------------
    UsdGeom.Xform.Define(stage, "/World/Materials")
    mats = {
        "Concrete": create_pbr_material(stage, "/World/Materials/Concrete", diffuse_color=(0.62, 0.62, 0.65), roughness=0.7, metallic=0.0),
        "StructuralSteel": create_pbr_material(stage, "/World/Materials/StructuralSteel", diffuse_color=(0.18, 0.20, 0.24), roughness=0.35, metallic=0.85),
        "CurtainGlass": create_pbr_material(stage, "/World/Materials/CurtainGlass", diffuse_color=(0.82, 0.92, 1.0), roughness=0.05, metallic=0.1, opacity=0.35, ior=1.52),
        "InteriorGlass": create_pbr_material(stage, "/World/Materials/InteriorGlass", diffuse_color=(0.90, 0.95, 1.0), roughness=0.10, metallic=0.05, opacity=0.25, ior=1.5),
        "Drywall": create_pbr_material(stage, "/World/Materials/Drywall", diffuse_color=(0.92, 0.92, 0.90), roughness=0.85, metallic=0.0),
        "TimberDoor": create_pbr_material(stage, "/World/Materials/TimberDoor", diffuse_color=(0.45, 0.28, 0.16), roughness=0.55, metallic=0.0),
        "HVACGalvanized": create_pbr_material(stage, "/World/Materials/HVACGalvanized", diffuse_color=(0.76, 0.80, 0.82), roughness=0.25, metallic=0.90),
        "FirePipeRed": create_pbr_material(stage, "/World/Materials/FirePipeRed", diffuse_color=(0.85, 0.15, 0.12), roughness=0.30, metallic=0.20),
        "SolarPV": create_pbr_material(stage, "/World/Materials/SolarPV", diffuse_color=(0.04, 0.10, 0.32), roughness=0.15, metallic=0.70, emissive_color=(0.02, 0.05, 0.12)),
        "ServerChassis": create_pbr_material(stage, "/World/Materials/ServerChassis", diffuse_color=(0.12, 0.12, 0.14), roughness=0.40, metallic=0.60, emissive_color=(0.0, 0.3, 0.8)),
        "ParapetAlum": create_pbr_material(stage, "/World/Materials/ParapetAlum", diffuse_color=(0.35, 0.37, 0.40), roughness=0.40, metallic=0.75),
    }

    # 3. Environment & Solar Light
    # -------------------------------------------------------------
    UsdGeom.Xform.Define(stage, "/World/Environment")
    setup_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)
    add_dome_light(stage, "/World/Environment/DomeLight", intensity=600.0, color=(0.90, 0.94, 1.0))
    # Sun light with initial orientation (representing midday at 38° N latitude)
    sun = add_distant_light(stage, "/World/Environment/SunLight", intensity=4500.0, color=(1.0, 0.98, 0.92), rotation_xyz=(-52.0, 35.0, 0.0))
    add_ground_plane(stage, "/World/Environment/SiteTerrain", size=6000.0)

    # 4. Building Dimensions & Storey Layout
    # -------------------------------------------------------------
    # Footprint: 32m x 24m (3200cm x 2400cm). Bay grid: 8m (800cm)
    bays_x = 4
    bays_z = 3
    bay_width = 800.0
    bay_depth = 800.0
    total_w = bays_x * bay_width   # 3200 cm
    total_d = bays_z * bay_depth   # 2400 cm

    # Storey Heights
    h_ground = 400.0
    h_lab = 380.0
    h_office = 380.0
    y_ground_top = h_ground             # 400
    y_lab_top = y_ground_top + h_lab    # 780
    y_office_top = y_lab_top + h_office # 1160

    storeys = [
        ("Storey_00_Ground", 0.0, h_ground, "Ground Level & Public Atrium"),
        ("Storey_01_Lab", y_ground_top, h_lab, "High-Tech Cleanroom & Server Cluster"),
        ("Storey_02_Offices", y_lab_top, h_office, "Executive Collaboration & Engineering Suites"),
        ("Storey_03_Rooftop", y_office_top, 140.0, "Mechanical Penthouse & Solar Energy Array"),
    ]

    for s_name, s_elev, s_h, s_desc in storeys:
        s_path = f"/World/BIM_Facility/{s_name}"
        s_prim = UsdGeom.Xform.Define(stage, s_path).GetPrim()
        s_prim.CreateAttribute("bim:ifcClass", Sdf.ValueTypeNames.String).Set("IfcBuildingStorey")
        s_prim.CreateAttribute("bim:elevation", Sdf.ValueTypeNames.Float).Set(s_elev)
        s_prim.CreateAttribute("bim:height", Sdf.ValueTypeNames.Float).Set(s_h)
        s_prim.CreateAttribute("bim:description", Sdf.ValueTypeNames.String).Set(s_desc)
        
        # Sub-disciplines
        UsdGeom.Xform.Define(stage, f"{s_path}/Structural")
        UsdGeom.Xform.Define(stage, f"{s_path}/Architectural")
        UsdGeom.Xform.Define(stage, f"{s_path}/MEP")

    # Column Grid coordinates
    col_x_coords = [-1200.0, -400.0, 400.0, 1200.0]
    col_z_coords = [-800.0, 0.0, 800.0]

    # =============================================================
    # STOREY 00: GROUND FLOOR
    # =============================================================
    s_id = "Storey_00_Ground"

    # Foundation Mat Slab
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Structural/FoundationSlab",
        pos=(0.0, -15.0, 0.0), size_xyz=(total_w + 100, 30.0, total_d + 100),
        mat_path="/World/Materials/Concrete",
        ifc_class="IfcSlab", discipline="Structural", storey=s_id,
        psets={"Pset_SlabCommon:LoadBearing": True, "Pset_Material:ConcreteGrade": "C40/50 Waterproof"}
    )

    # Ground Columns (Cast-in-place concrete 50x50 cm)
    c_idx = 0
    for x in col_x_coords:
        for z in col_z_coords:
            c_idx += 1
            add_cube_element(
                stage, f"/World/BIM_Facility/{s_id}/Structural/Column_G_{c_idx:02d}",
                pos=(x, h_ground / 2.0, z), size_xyz=(50.0, h_ground, 50.0),
                mat_path="/World/Materials/Concrete",
                ifc_class="IfcColumn", discipline="Structural", storey=s_id,
                psets={"Pset_ColumnCommon:LoadBearing": True, "Pset_Material:ConcreteGrade": "C40/50"}
            )

    # Floor 1 Intermediate Slab (ceiling of ground floor)
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Structural/FloorSlab_L1",
        pos=(0.0, y_ground_top - 12.5, 0.0), size_xyz=(total_w, 25.0, total_d),
        mat_path="/World/Materials/Concrete",
        ifc_class="IfcSlab", discipline="Structural", storey=s_id,
        psets={"Pset_SlabCommon:LoadBearing": True, "Pset_SlabCommon:FireRating": "REI 120"}
    )

    # Architectural: Curtain Wall Glazing (Perimeter)
    # North / South Facades
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_Front",
        pos=(0.0, h_ground / 2.0, total_d / 2.0), size_xyz=(total_w, h_ground - 25.0, 10.0),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_WallCommon:ThermalTransmittance": 0.85, "Pset_Glass:AcousticRating": "42 dB"}
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_Back",
        pos=(0.0, h_ground / 2.0, -total_d / 2.0), size_xyz=(total_w, h_ground - 25.0, 10.0),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_WallCommon:ThermalTransmittance": 0.85}
    )
    # East / West Facades
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_East",
        pos=(total_w / 2.0, h_ground / 2.0, 0.0), size_xyz=(10.0, h_ground - 25.0, total_d),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_WallCommon:ThermalTransmittance": 0.85}
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_West",
        pos=(-total_w / 2.0, h_ground / 2.0, 0.0), size_xyz=(10.0, h_ground - 25.0, total_d),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_WallCommon:ThermalTransmittance": 0.85}
    )

    # Interior Architectural Partitions (Reception & Security Core)
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/Partition_Core_North",
        pos=(-150.0, (h_ground - 30) / 2.0, 100.0), size_xyz=(350.0, h_ground - 30.0, 15.0),
        mat_path="/World/Materials/Drywall",
        ifc_class="IfcWallStandardCase", discipline="Architectural", storey=s_id,
        psets={"Pset_WallCommon:FireRating": "REI 60", "Pset_WallCommon:LoadBearing": False}
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/MainEntranceDoor",
        pos=(0.0, 120.0, total_d / 2.0 + 8.0), size_xyz=(220.0, 240.0, 20.0),
        mat_path="/World/Materials/TimberDoor",
        ifc_class="IfcDoor", discipline="Architectural", storey=s_id,
        psets={"Pset_DoorCommon:SecurityRating": "RC3", "Pset_DoorCommon:Automatic": True}
    )

    # Ground MEP: Main HVAC Central Distribution Duct
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/MEP/HVAC_MainSupplyDuct_G",
        pos=(0.0, h_ground - 40.0, 0.0), size_xyz=(total_w - 400.0, 35.0, 50.0),
        mat_path="/World/Materials/HVACGalvanized",
        ifc_class="IfcDuctSegment", discipline="MEP", storey=s_id,
        psets={"Pset_DuctCommon:AirFlowRate": "5400 m3/h", "Pset_DuctCommon:Insulation": "Rockwool 25mm"}
    )
    add_cylinder_element(
        stage, f"/World/BIM_Facility/{s_id}/MEP/ChilledWaterSupplyPipe_G",
        pos=(0.0, h_ground - 55.0, 45.0), radius=6.0, height=total_w - 450.0, axis="X",
        mat_path="/World/Materials/FirePipeRed",
        ifc_class="IfcPipeSegment", discipline="MEP", storey=s_id,
        rot_xyz=(0.0, 0.0, 90.0),
        psets={"Pset_PipeCommon:Fluid": "Chilled Water 6C", "Pset_PipeCommon:PressureRating": "PN16"}
    )

    # =============================================================
    # STOREY 01: HIGH-TECH LAB & DATA CLUSTER
    # =============================================================
    s_id = "Storey_01_Lab"
    y_base = y_ground_top

    # Steel & Composite Columns
    c_idx = 0
    for x in col_x_coords:
        for z in col_z_coords:
            c_idx += 1
            add_cube_element(
                stage, f"/World/BIM_Facility/{s_id}/Structural/Column_L1_{c_idx:02d}",
                pos=(x, y_base + (h_lab / 2.0), z), size_xyz=(45.0, h_lab, 45.0),
                mat_path="/World/Materials/StructuralSteel",
                ifc_class="IfcColumn", discipline="Structural", storey=s_id,
                psets={"Pset_ColumnCommon:LoadBearing": True, "Pset_Material:SteelGrade": "S355 JR"}
            )

    # Floor 2 Slab
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Structural/FloorSlab_L2",
        pos=(0.0, y_lab_top - 12.5, 0.0), size_xyz=(total_w, 25.0, total_d),
        mat_path="/World/Materials/Concrete",
        ifc_class="IfcSlab", discipline="Structural", storey=s_id,
        psets={"Pset_SlabCommon:FireRating": "REI 120"}
    )

    # Perimeter Glazing
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_Front",
        pos=(0.0, y_base + (h_lab / 2.0), total_d / 2.0), size_xyz=(total_w, h_lab - 25.0, 10.0),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_Back",
        pos=(0.0, y_base + (h_lab / 2.0), -total_d / 2.0), size_xyz=(total_w, h_lab - 25.0, 10.0),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id
    )

    # Server Cluster Enclosures (Architectural / Equipment)
    for rack_i, r_z in enumerate([-350.0, -150.0, 50.0, 250.0]):
        add_cube_element(
            stage, f"/World/BIM_Facility/{s_id}/Architectural/ServerRow_{rack_i + 1}",
            pos=(-450.0, y_base + 110.0, r_z), size_xyz=(320.0, 220.0, 80.0),
            mat_path="/World/Materials/ServerChassis",
            ifc_class="IfcDiscreteAccessory", discipline="Architectural", storey=s_id,
            psets={"Pset_Equipment:Type": "42U High-Density Compute Blade", "Pset_Equipment:ThermalLoad": "24 kW"}
        )

    # Cleanroom Glass Partition
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CleanroomGlazing",
        pos=(200.0, y_base + (h_lab / 2.0), 0.0), size_xyz=(15.0, h_lab - 30.0, total_d - 300.0),
        mat_path="/World/Materials/InteriorGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_SpaceCommon:CleanroomClass": "ISO 5"}
    )

    # Lab MEP: High-Efficiency HVAC & Fire Suppression Sprinkler
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/MEP/HVAC_SupplyDuct_L1",
        pos=(0.0, y_lab_top - 40.0, 0.0), size_xyz=(total_w - 300.0, 30.0, 45.0),
        mat_path="/World/Materials/HVACGalvanized",
        ifc_class="IfcDuctSegment", discipline="MEP", storey=s_id,
        psets={"Pset_DuctCommon:FilterGrade": "HEPA H14"}
    )
    add_cylinder_element(
        stage, f"/World/BIM_Facility/{s_id}/MEP/FireSprinklerLine_L1",
        pos=(0.0, y_lab_top - 55.0, -60.0), radius=4.5, height=total_w - 350.0, axis="X",
        mat_path="/World/Materials/FirePipeRed",
        ifc_class="IfcPipeSegment", discipline="MEP", storey=s_id,
        rot_xyz=(0.0, 0.0, 90.0),
        psets={"Pset_FireProtection:System": "Wet Chemical Pre-Action"}
    )

    # =============================================================
    # STOREY 02: EXECUTIVE OFFICES & COLLABORATION
    # =============================================================
    s_id = "Storey_02_Offices"
    y_base = y_lab_top

    # Columns
    c_idx = 0
    for x in col_x_coords:
        for z in col_z_coords:
            c_idx += 1
            add_cube_element(
                stage, f"/World/BIM_Facility/{s_id}/Structural/Column_L2_{c_idx:02d}",
                pos=(x, y_base + (h_office / 2.0), z), size_xyz=(40.0, h_office, 40.0),
                mat_path="/World/Materials/StructuralSteel",
                ifc_class="IfcColumn", discipline="Structural", storey=s_id,
                psets={"Pset_ColumnCommon:LoadBearing": True}
            )

    # Roof Slab
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Structural/RoofSlab",
        pos=(0.0, y_office_top - 12.5, 0.0), size_xyz=(total_w, 25.0, total_d),
        mat_path="/World/Materials/Concrete",
        ifc_class="IfcSlab", discipline="Structural", storey=s_id,
        psets={"Pset_SlabCommon:Waterproofing": "EPDM Membrane 2.0mm"}
    )

    # Executive Curtain Glazing & Shading Louvers
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/CurtainWall_SouthRibbon",
        pos=(0.0, y_base + (h_office / 2.0), total_d / 2.0), size_xyz=(total_w, h_office - 25.0, 10.0),
        mat_path="/World/Materials/CurtainGlass",
        ifc_class="IfcCurtainWall", discipline="Architectural", storey=s_id,
        psets={"Pset_Shading:SolarHeatGainCoeff": 0.28}
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/OfficePartition_Boardroom",
        pos=(-300.0, y_base + (h_office - 30) / 2.0, 150.0), size_xyz=(450.0, h_office - 30.0, 15.0),
        mat_path="/World/Materials/Drywall",
        ifc_class="IfcWallStandardCase", discipline="Architectural", storey=s_id,
        psets={"Pset_Acoustic:SoundTransmissionClass": 52}
    )

    # Office HVAC
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/MEP/HVAC_SupplyDuct_L2",
        pos=(0.0, y_office_top - 40.0, 0.0), size_xyz=(total_w - 300.0, 30.0, 45.0),
        mat_path="/World/Materials/HVACGalvanized",
        ifc_class="IfcDuctSegment", discipline="MEP", storey=s_id
    )

    # =============================================================
    # STOREY 03: ROOFTOP PENTHOUSE & SOLAR ARRAY
    # =============================================================
    s_id = "Storey_03_Rooftop"
    y_base = y_office_top

    # Perimeter Safety Parapet Wall
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/Parapet_North",
        pos=(0.0, y_base + 60.0, total_d / 2.0), size_xyz=(total_w, 120.0, 20.0),
        mat_path="/World/Materials/ParapetAlum",
        ifc_class="IfcWall", discipline="Architectural", storey=s_id
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/Parapet_South",
        pos=(0.0, y_base + 60.0, -total_d / 2.0), size_xyz=(total_w, 120.0, 20.0),
        mat_path="/World/Materials/ParapetAlum",
        ifc_class="IfcWall", discipline="Architectural", storey=s_id
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/Parapet_East",
        pos=(total_w / 2.0, y_base + 60.0, 0.0), size_xyz=(20.0, 120.0, total_d),
        mat_path="/World/Materials/ParapetAlum",
        ifc_class="IfcWall", discipline="Architectural", storey=s_id
    )
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/Parapet_West",
        pos=(-total_w / 2.0, y_base + 60.0, 0.0), size_xyz=(20.0, 120.0, total_d),
        mat_path="/World/Materials/ParapetAlum",
        ifc_class="IfcWall", discipline="Architectural", storey=s_id
    )

    # Rooftop Stair/Elevator Enclosure Penthouse
    add_cube_element(
        stage, f"/World/BIM_Facility/{s_id}/Architectural/StairPenthouse",
        pos=(-800.0, y_base + 125.0, 0.0), size_xyz=(350.0, 250.0, 450.0),
        mat_path="/World/Materials/ParapetAlum",
        ifc_class="IfcBuildingElementProxy", discipline="Architectural", storey=s_id,
        psets={"Pset_BuildingElement:Access": "Rooftop Maintenance Hatch"}
    )

    # Heavy MEP: Industrial Rooftop Chillers
    for ch_i, ch_x in enumerate([400.0, 950.0]):
        add_cube_element(
            stage, f"/World/BIM_Facility/{s_id}/MEP/ChillerUnit_{ch_i + 1}",
            pos=(ch_x, y_base + 110.0, -450.0), size_xyz=(320.0, 220.0, 200.0),
            mat_path="/World/Materials/HVACGalvanized",
            ifc_class="IfcChiller", discipline="MEP", storey=s_id,
            psets={"Pset_ChillerCommon:CoolingCapacity": "350 kW", "Pset_ChillerCommon:Refrigerant": "R1234ze (Low GWP)"}
        )

    # Photovoltaic (PV) Solar Panel Arrays (Angled southwards)
    # 3 rows of solar arrays
    pv_rows = [-150.0, 150.0, 450.0]
    for r_idx, r_z in enumerate(pv_rows):
        for col_idx in range(4):
            p_x = -400.0 + (col_idx * 320.0)
            panel = add_cube_element(
                stage, f"/World/BIM_Facility/{s_id}/MEP/SolarArray_R{r_idx + 1}_P{col_idx + 1}",
                pos=(p_x, y_base + 55.0, r_z), size_xyz=(280.0, 12.0, 160.0),
                mat_path="/World/Materials/SolarPV",
                ifc_class="IfcSolarDevice", discipline="MEP", storey=s_id,
                psets={
                    "Pset_SolarDevice:Type": "Monocrystalline Bifacial PV",
                    "Pset_SolarDevice:NominalPower": "580 Wp",
                    "Pset_SolarDevice:TiltAngle": 30.0,
                    "Pset_SolarDevice:Azimuth": 180.0
                }
            )
            # Tilt 25 degrees toward south (+Z)
            xform = UsdGeom.Xformable(panel.GetPrim())
            xform.AddRotateXOp().Set(-25.0)

    # Save stage
    stage.GetRootLayer().Save()
    print(f"[OK] BIM Cesium Stage generated successfully: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate Georeferenced BIM Cesium USD Stage")
    parser.add_argument("--output", "-o", default="usd_generators/output_bim_cesium.usda", help="Output .usda path")
    parser.add_argument("--lat", type=float, default=37.9753, help="WGS84 Latitude")
    parser.add_argument("--lon", type=float, default=23.7361, help="WGS84 Longitude")
    parser.add_argument("--height", type=float, default=120.0, help="WGS84 Ellipsoidal Height (meters)")
    args = parser.parse_args()

    out_file = args.output
    if not os.path.isabs(out_file):
        out_file = os.path.join(WORKSPACE_DIR, out_file)

    build_bim_cesium_stage(
        output_path=out_file,
        latitude=args.lat,
        longitude=args.lon,
        height_wgs84=args.height
    )


if __name__ == "__main__":
    main()
