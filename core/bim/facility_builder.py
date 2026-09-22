"""Parametric OpenUSD BIM Facility Builder.
Provides a structured, object-oriented API for authoring multi-storey
IFC4-compliant digital twin stages with Cesium WGS84 georeferencing.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
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


def tag_bim_element(
    prim: Usd.Prim,
    ifc_class: str,
    discipline: str,
    storey: str,
    psets: Optional[Dict[str, Any]] = None,
    phase: Optional[str] = None,
    month: Optional[int] = None
) -> None:
    """Applies IFC-standard BIM classification, 4D phasing schedule, and custom property sets to a USD prim."""
    prim.CreateAttribute("bim:ifcClass", Sdf.ValueTypeNames.String).Set(ifc_class)
    prim.CreateAttribute("bim:discipline", Sdf.ValueTypeNames.String).Set(discipline)
    prim.CreateAttribute("bim:storey", Sdf.ValueTypeNames.String).Set(storey)

    prim_name = prim.GetName()
    if phase is None or month is None:
        if "Ground_Slab" in prim_name or "Foundation" in prim_name or "Substructure" in prim_name:
            phase = "Phase 0: Substructure & Foundations"
            month = 0
        elif storey == "Storey_00_Ground" and discipline == "Structural":
            phase = "Phase 1: Ground Framing & Transfer Beams"
            month = 2
        elif storey == "Storey_01_Lab" and discipline == "Structural":
            phase = "Phase 2: L1 Superstructure & Lab Deck"
            month = 4
        elif storey in ["Storey_02_Offices", "Storey_03_Rooftop"] and discipline == "Structural":
            phase = "Phase 3: Superstructure Topping Out"
            month = 6
        elif discipline == "Architectural":
            if any(k in prim_name for k in ["Partition", "Server", "Door", "Cleanroom"]):
                phase = "Phase 6: Interior Fit-out & Commissioning"
                month = 12
            else:
                phase = "Phase 4: Building Enclosure & Glazing"
                month = 8
        elif discipline == "MEP":
            if "Solar" in prim_name or "Chiller" in prim_name:
                phase = "Phase 6: Interior Fit-out & Commissioning"
                month = 12
            else:
                phase = "Phase 5: MEP Rough-in & Services"
                month = 10
        else:
            phase = "Phase 6: Interior Fit-out & Commissioning"
            month = 12

    prim.CreateAttribute("bim:phase", Sdf.ValueTypeNames.String).Set(str(phase))
    prim.CreateAttribute("bim:constructionMonth", Sdf.ValueTypeNames.Int).Set(int(month))

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
    pos: Tuple[float, float, float],
    size_xyz: Tuple[float, float, float],
    mat_path: str,
    ifc_class: str,
    discipline: str,
    storey: str,
    psets: Optional[Dict[str, Any]] = None,
    is_collider: bool = True,
    phase: Optional[str] = None,
    month: Optional[int] = None
) -> UsdGeom.Cube:
    """Creates a scaled box primitive with material binding, BIM tags, and collision."""
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr().Set(1.0)

    xform = UsdGeom.Xformable(cube.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    xform.AddScaleOp().Set(Gf.Vec3f(*size_xyz))

    bind_material(cube.GetPrim(), mat_path)
    tag_bim_element(cube.GetPrim(), ifc_class, discipline, storey, psets, phase=phase, month=month)

    if is_collider:
        col = UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        col.CreateCollisionEnabledAttr().Set(True)

    return cube


def add_cylinder_element(
    stage: Usd.Stage,
    path: str,
    pos: Tuple[float, float, float],
    radius: float,
    height: float,
    axis: str,
    mat_path: str,
    ifc_class: str,
    discipline: str,
    storey: str,
    rot_xyz: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    psets: Optional[Dict[str, Any]] = None,
    phase: Optional[str] = None,
    month: Optional[int] = None
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
    tag_bim_element(cyl.GetPrim(), ifc_class, discipline, storey, psets, phase=phase, month=month)
    return cyl
