"""
OpenUSD Authoring Utilities.
Common helper functions for creating, structuring, and decorating standalone USD stages.
Works with standalone pxr.Usd (from usd-core package or Omniverse Python environment).
"""

from typing import Tuple, Optional
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdPhysics


def create_stage(file_path: str, up_axis: str = "Y", meters_per_unit: float = 0.01) -> Usd.Stage:
    """
    Creates a new USD Stage with standard axis and unit metadata.
    
    Args:
        file_path: Target path (.usda, .usdc, or .usd).
        up_axis: 'Y' or 'Z' (default 'Y' for Omniverse).
        meters_per_unit: Scale factor (0.01 for centimeters, 1.0 for meters).
    """
    stage = Usd.Stage.CreateNew(file_path)
    if up_axis.upper() == "Y":
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    else:
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)
    return stage


def setup_physics_scene(
    stage: Usd.Stage,
    scene_path: str = "/World/PhysicsScene",
    gravity_magnitude: float = 981.0,
    gravity_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0)
) -> UsdPhysics.Scene:
    """Creates a UsdPhysics.Scene on the stage."""
    scene = UsdPhysics.Scene.Define(stage, scene_path)
    scene.CreateGravityMagnitudeAttr().Set(gravity_magnitude)
    scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(*gravity_dir))
    return scene


def create_pbr_material(
    stage: Usd.Stage,
    mat_path: str,
    diffuse_color: Tuple[float, float, float] = (0.8, 0.8, 0.8),
    roughness: float = 0.3,
    metallic: float = 0.0,
    emissive_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    opacity: float = 1.0,
    ior: float = 1.5
) -> UsdShade.Material:
    """Creates a UsdPreviewSurface material network."""
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/PBRShader")
    shader.CreateIdAttr("UsdPreviewSurface")

    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*diffuse_color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive_color))
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(ior)

    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def bind_material(prim: Usd.Prim, mat_path: str) -> None:
    """Binds a UsdShade.Material to a USD Prim."""
    stage = prim.GetStage()
    mat_prim = stage.GetPrimAtPath(mat_path)
    if mat_prim.IsValid():
        material = UsdShade.Material(mat_prim)
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)


def add_dome_light(
    stage: Usd.Stage,
    light_path: str = "/World/Lights/DomeLight",
    intensity: float = 1000.0,
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> UsdLux.DomeLight:
    """Adds an ambient HDRI / DomeLight to the stage."""
    dome = UsdLux.DomeLight.Define(stage, light_path)
    dome.CreateIntensityAttr().Set(intensity)
    dome.CreateColorAttr().Set(Gf.Vec3f(*color))
    return dome


def add_distant_light(
    stage: Usd.Stage,
    light_path: str = "/World/Lights/DistantLight",
    intensity: float = 3000.0,
    color: Tuple[float, float, float] = (1.0, 0.96, 0.9),
    rotation_xyz: Tuple[float, float, float] = (-45.0, 45.0, 0.0)
) -> UsdLux.DistantLight:
    """Adds a directional Sun / DistantLight to the stage."""
    light = UsdLux.DistantLight.Define(stage, light_path)
    light.CreateIntensityAttr().Set(intensity)
    light.CreateColorAttr().Set(Gf.Vec3f(*color))
    xform = UsdGeom.Xformable(light.GetPrim())
    xform.AddRotateXYZOp().Set(Gf.Vec3d(*rotation_xyz))
    return light


def add_ground_plane(
    stage: Usd.Stage,
    plane_path: str = "/World/Environment/GroundPlane",
    size: float = 2000.0
) -> UsdGeom.Plane:
    """Adds a static ground plane with collision."""
    plane = UsdGeom.Plane.Define(stage, plane_path)
    plane.CreateAxisAttr().Set("Y")
    plane.CreateLengthAttr().Set(size)
    plane.CreateWidthAttr().Set(size)

    # Static collider
    collision = UsdPhysics.CollisionAPI.Apply(plane.GetPrim())
    collision.CreateCollisionEnabledAttr().Set(True)
    return plane
