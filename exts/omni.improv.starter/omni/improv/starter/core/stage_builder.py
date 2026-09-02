"""
Stage Builder and Procedural Spawner for Omniverse Kit and OpenUSD.
Provides procedural geometry, lighting rigs, PBR material creation, and kinetic physics setups.
"""

import math
from typing import Optional, Tuple, List
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdPhysics

from .physics_helper import PhysicsHelper

try:
    import omni.usd
    HAS_OMNI_USD = True
except ImportError:
    omni = None
    HAS_OMNI_USD = False


class StageBuilder:
    """Orchestrates USD stage creation, procedural structures, and material binding."""

    @staticmethod
    def get_current_stage() -> Optional[Usd.Stage]:
        """Gets active stage from omni.usd context if available."""
        if HAS_OMNI_USD:
            return omni.usd.get_context().get_stage()
        return None

    @staticmethod
    def setup_stage_metadata(stage: Usd.Stage, meters_per_unit: float = 0.01) -> None:
        """Sets standard stage metadata: Y-up (or Z-up), metersPerUnit (0.01 = cm)."""
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, meters_per_unit)

    @classmethod
    def setup_studio_environment(
        cls,
        stage: Usd.Stage,
        add_ground: bool = True,
        add_lighting: bool = True
    ) -> Sdf.Path:
        """
        Creates a clean studio environment with physics scene, ground collider, and lighting.
        """
        root_path = Sdf.Path("/World")
        if not stage.GetPrimAtPath(root_path).IsValid():
            UsdGeom.Xform.Define(stage, root_path)

        # 1. Physics Scene
        PhysicsHelper.ensure_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=981.0)

        # 2. Ground Plane Collider
        if add_ground:
            cls.spawn_ground_plane(stage, "/World/Environment/GroundPlane", size=4000.0)

        # 3. Studio Lighting Rig
        if add_lighting:
            cls.spawn_lighting_rig(stage, "/World/Environment/Lights")

        return root_path

    @classmethod
    def spawn_ground_plane(
        cls,
        stage: Usd.Stage,
        prim_path: str = "/World/Environment/GroundPlane",
        size: float = 4000.0
    ) -> UsdGeom.Plane:
        """Spawns a static ground plane with collision enabled and a subtle grid material."""
        plane_prim = stage.GetPrimAtPath(prim_path)
        if not plane_prim.IsValid():
            plane = UsdGeom.Plane.Define(stage, prim_path)
            plane.CreateAxisAttr().Set("Y")
            plane.CreateLengthAttr().Set(size)
            plane.CreateWidthAttr().Set(size)
        else:
            plane = UsdGeom.Plane(plane_prim)

        # Static collision
        PhysicsHelper.apply_collision(plane.GetPrim(), approximation="none")

        # Ground material
        mat_path = "/World/Materials/M_StudioGround"
        cls.create_pbr_material(
            stage,
            mat_path,
            diffuse_color=(0.12, 0.13, 0.15),
            roughness=0.4,
            metallic=0.1
        )
        cls.bind_material(plane.GetPrim(), mat_path)
        return plane

    @classmethod
    def spawn_lighting_rig(
        cls,
        stage: Usd.Stage,
        parent_path: str = "/World/Environment/Lights"
    ) -> None:
        """Spawns a balanced 3-point studio lighting rig with an ambient DomeLight."""
        lights_xform = UsdGeom.Xform.Define(stage, parent_path)

        # Ambient Dome Light
        dome_path = f"{parent_path}/DomeLight"
        dome = UsdLux.DomeLight.Define(stage, dome_path)
        dome.CreateIntensityAttr().Set(800.0)
        dome.CreateColorAttr().Set(Gf.Vec3f(0.9, 0.95, 1.0))

        # Key Light (Warm distant directional)
        key_path = f"{parent_path}/KeyLight"
        key = UsdLux.DistantLight.Define(stage, key_path)
        key.CreateIntensityAttr().Set(3500.0)
        key.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.95, 0.88))
        key_xform = UsdGeom.Xformable(key.GetPrim())
        key_xform.AddRotateXYZOp().Set(Gf.Vec3d(-45.0, 35.0, 0.0))

        # Fill Light (Cool subtle backlight)
        fill_path = f"{parent_path}/FillLight"
        fill = UsdLux.DistantLight.Define(stage, fill_path)
        fill.CreateIntensityAttr().Set(1200.0)
        fill.CreateColorAttr().Set(Gf.Vec3f(0.7, 0.85, 1.0))
        fill_xform = UsdGeom.Xformable(fill.GetPrim())
        fill_xform.AddRotateXYZOp().Set(Gf.Vec3d(-30.0, -145.0, 0.0))

    @classmethod
    def spawn_primitive(
        cls,
        stage: Usd.Stage,
        prim_type: str,
        prim_path: str,
        position: Tuple[float, float, float] = (0.0, 50.0, 0.0),
        size: float = 30.0,
        dynamic_physics: bool = True,
        material_preset: Optional[str] = "neon_cyan"
    ) -> Usd.Prim:
        """
        Spawns a 3D primitive with optional rigid body physics and PBR material.
        
        Args:
            stage: Active USD stage.
            prim_type: 'Cube', 'Sphere', 'Cylinder', 'Capsule', or 'Cone'.
            prim_path: Destination path in USD hierarchy.
            position: (X, Y, Z) coordinates.
            size: Dimension scale.
            dynamic_physics: If True, applies UsdPhysics.RigidBodyAPI and CollisionAPI.
            material_preset: Preset color/style to bind.
        """
        prim_type_lower = prim_type.lower()
        if prim_type_lower == "cube":
            geom = UsdGeom.Cube.Define(stage, prim_path)
            geom.CreateSizeAttr().Set(size)
        elif prim_type_lower == "sphere":
            geom = UsdGeom.Sphere.Define(stage, prim_path)
            geom.CreateRadiusAttr().Set(size * 0.5)
        elif prim_type_lower == "cylinder":
            geom = UsdGeom.Cylinder.Define(stage, prim_path)
            geom.CreateRadiusAttr().Set(size * 0.5)
            geom.CreateHeightAttr().Set(size)
            geom.CreateAxisAttr().Set("Y")
        elif prim_type_lower == "capsule":
            geom = UsdGeom.Capsule.Define(stage, prim_path)
            geom.CreateRadiusAttr().Set(size * 0.35)
            geom.CreateHeightAttr().Set(size * 0.7)
            geom.CreateAxisAttr().Set("Y")
        elif prim_type_lower == "cone":
            geom = UsdGeom.Cone.Define(stage, prim_path)
            geom.CreateRadiusAttr().Set(size * 0.5)
            geom.CreateHeightAttr().Set(size)
            geom.CreateAxisAttr().Set("Y")
        else:
            geom = UsdGeom.Cube.Define(stage, prim_path)
            geom.CreateSizeAttr().Set(size)

        # Set Position
        xformable = UsdGeom.Xformable(geom.GetPrim())
        xformable.AddTranslateOp().Set(Gf.Vec3d(*position))

        # Add Physics
        if dynamic_physics:
            PhysicsHelper.apply_rigid_body(geom.GetPrim())
            PhysicsHelper.apply_collision(geom.GetPrim(), approximation="convexHull")
            PhysicsHelper.apply_mass_and_density(geom.GetPrim(), density=1000.0)

        # Add Material
        if material_preset:
            mat_path = f"/World/Materials/M_{material_preset}"
            cls.create_preset_material(stage, mat_path, material_preset)
            cls.bind_material(geom.GetPrim(), mat_path)

        return geom.GetPrim()

    @classmethod
    def spawn_domino_run(
        cls,
        stage: Usd.Stage,
        parent_path: str = "/World/Props/DominoRun",
        count: int = 30,
        spacing: float = 18.0,
        curve_radius: float = 120.0
    ) -> None:
        """
        Generates an arced sequence of upright dominoes with a trigger ball on an elevated ramp.
        """
        parent_xform = UsdGeom.Xform.Define(stage, parent_path)
        domino_w, domino_h, domino_d = 4.0, 24.0, 12.0

        mat_domino = "/World/Materials/M_Domino"
        cls.create_pbr_material(stage, mat_domino, diffuse_color=(0.1, 0.7, 0.9), roughness=0.2, metallic=0.0)

        for i in range(count):
            angle = (i / max(1, count - 1)) * math.pi * 0.75  # 135 degree arc
            x = curve_radius * math.sin(angle)
            z = curve_radius * (1.0 - math.cos(angle))
            y = domino_h * 0.5

            d_path = f"{parent_path}/Domino_{i:02d}"
            cube = UsdGeom.Cube.Define(stage, d_path)
            cube.CreateSizeAttr().Set(1.0)

            xformable = UsdGeom.Xformable(cube.GetPrim())
            xformable.AddTranslateOp().Set(Gf.Vec3d(x, y, z))
            rot_deg = math.degrees(angle)
            xformable.AddRotateYOp().Set(rot_deg)
            xformable.AddScaleOp().Set(Gf.Vec3f(domino_w, domino_h, domino_d))

            PhysicsHelper.apply_rigid_body(cube.GetPrim())
            PhysicsHelper.apply_collision(cube.GetPrim(), approximation="boundingCube")
            PhysicsHelper.apply_mass_and_density(cube.GetPrim(), density=1200.0)
            cls.bind_material(cube.GetPrim(), mat_domino)

        # Trigger Ball above the first domino
        ball_path = f"{parent_path}/TriggerBall"
        ball = UsdGeom.Sphere.Define(stage, ball_path)
        ball.CreateRadiusAttr().Set(10.0)
        ball_xform = UsdGeom.Xformable(ball.GetPrim())
        ball_xform.AddTranslateOp().Set(Gf.Vec3d(-5.0, domino_h + 20.0, -10.0))

        PhysicsHelper.apply_rigid_body(ball.GetPrim())
        PhysicsHelper.apply_collision(ball.GetPrim(), approximation="boundingSphere")
        PhysicsHelper.apply_mass_and_density(ball.GetPrim(), mass=5.0)

        mat_ball = "/World/Materials/M_TriggerBall"
        cls.create_pbr_material(stage, mat_ball, diffuse_color=(1.0, 0.2, 0.1), roughness=0.1, metallic=0.8)
        cls.bind_material(ball.GetPrim(), mat_ball)

    @classmethod
    def spawn_destructible_tower(
        cls,
        stage: Usd.Stage,
        parent_path: str = "/World/Props/Tower",
        floors: int = 8,
        blocks_per_floor: int = 3,
        base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> None:
        """Generates a stacked Jenga-style physics block tower."""
        block_w = 12.0
        block_h = 7.0
        block_l = block_w * blocks_per_floor

        mat_tower = "/World/Materials/M_WoodBlock"
        cls.create_pbr_material(stage, mat_tower, diffuse_color=(0.85, 0.65, 0.45), roughness=0.6, metallic=0.0)

        for f in range(floors):
            y = base_pos[1] + (f + 0.5) * block_h
            is_rotated = (f % 2 == 1)

            for b in range(blocks_per_floor):
                offset = (b - (blocks_per_floor - 1) / 2.0) * block_w
                b_path = f"{parent_path}/Floor_{f:02d}_Block_{b}"
                cube = UsdGeom.Cube.Define(stage, b_path)
                cube.CreateSizeAttr().Set(1.0)

                xformable = UsdGeom.Xformable(cube.GetPrim())
                if is_rotated:
                    x = base_pos[0] + offset
                    z = base_pos[2]
                    scale = Gf.Vec3f(block_w * 0.95, block_h * 0.95, block_l * 0.95)
                else:
                    x = base_pos[0]
                    z = base_pos[2] + offset
                    scale = Gf.Vec3f(block_l * 0.95, block_h * 0.95, block_w * 0.95)

                xformable.AddTranslateOp().Set(Gf.Vec3d(x, y, z))
                xformable.AddScaleOp().Set(scale)

                PhysicsHelper.apply_rigid_body(cube.GetPrim())
                PhysicsHelper.apply_collision(cube.GetPrim(), approximation="boundingCube")
                PhysicsHelper.apply_mass_and_density(cube.GetPrim(), density=650.0)
                cls.bind_material(cube.GetPrim(), mat_tower)

    @classmethod
    def create_pbr_material(
        cls,
        stage: Usd.Stage,
        material_path: str,
        diffuse_color: Tuple[float, float, float] = (0.8, 0.8, 0.8),
        roughness: float = 0.4,
        metallic: float = 0.0,
        emissive_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        opacity: float = 1.0
    ) -> UsdShade.Material:
        """Creates a standard UsdPreviewSurface PBR shader and material."""
        mat_prim = stage.GetPrimAtPath(material_path)
        if not mat_prim.IsValid():
            material = UsdShade.Material.Define(stage, material_path)
        else:
            material = UsdShade.Material(mat_prim)

        shader_path = f"{material_path}/PBRShader"
        shader = UsdShade.Shader.Define(stage, shader_path)
        shader.CreateIdAttr("UsdPreviewSurface")

        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*diffuse_color))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive_color))
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)

        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return material

    @classmethod
    def create_preset_material(cls, stage: Usd.Stage, material_path: str, preset: str) -> UsdShade.Material:
        """Generates pre-tuned PBR materials by name."""
        presets = {
            "neon_cyan": dict(diffuse_color=(0.0, 0.8, 1.0), roughness=0.1, metallic=0.2, emissive_color=(0.0, 0.9, 1.0)),
            "neon_magenta": dict(diffuse_color=(1.0, 0.0, 0.8), roughness=0.1, metallic=0.2, emissive_color=(1.0, 0.0, 0.8)),
            "gold": dict(diffuse_color=(1.0, 0.766, 0.336), roughness=0.15, metallic=1.0),
            "chrome": dict(diffuse_color=(0.95, 0.95, 0.95), roughness=0.05, metallic=1.0),
            "matte_black": dict(diffuse_color=(0.05, 0.05, 0.05), roughness=0.8, metallic=0.0),
            "rubber_red": dict(diffuse_color=(0.85, 0.1, 0.1), roughness=0.5, metallic=0.0),
        }
        config = presets.get(preset, presets["neon_cyan"])
        return cls.create_pbr_material(stage, material_path, **config)

    @classmethod
    def bind_material(cls, prim: Usd.Prim, material_path: str) -> None:
        """Binds a UsdShade.Material to a USD Prim."""
        stage = prim.GetStage()
        mat_prim = stage.GetPrimAtPath(material_path)
        if mat_prim.IsValid():
            material = UsdShade.Material(mat_prim)
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
