"""
Physics Helper Utilities for Omniverse Kit and OpenUSD.
Encapsulates UsdPhysics and PhysxSchema APIs for rigid body dynamics, collisions, and materials.
"""

from typing import Optional, Tuple
from pxr import Gf, Sdf, Usd, UsdPhysics

try:
    from pxr import PhysxSchema
    HAS_PHYSX = True
except ImportError:
    PhysxSchema = None
    HAS_PHYSX = False


class PhysicsHelper:
    """Helper class providing unified methods to configure physics on USD Stages."""

    @staticmethod
    def ensure_physics_scene(
        stage: Usd.Stage,
        scene_path: str = "/World/PhysicsScene",
        gravity_magnitude: float = 981.0,
        gravity_direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    ) -> UsdPhysics.Scene:
        """
        Ensures a UsdPhysics.Scene exists on the stage with the specified gravity settings.
        
        Args:
            stage: Active USD stage.
            scene_path: SdfPath where the physics scene prim should reside.
            gravity_magnitude: Magnitude in stage units / s^2 (default: 981.0 cm/s^2).
            gravity_direction: Unit vector for gravity direction.
            
        Returns:
            The UsdPhysics.Scene prim schema.
        """
        scene_prim = stage.GetPrimAtPath(scene_path)
        if not scene_prim.IsValid():
            scene = UsdPhysics.Scene.Define(stage, scene_path)
        else:
            scene = UsdPhysics.Scene(scene_prim)

        scene.CreateGravityMagnitudeAttr().Set(gravity_magnitude)
        scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(*gravity_direction))

        if HAS_PHYSX:
            physx_scene_api = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
            physx_scene_api.CreateEnableCCDAttr().Set(True)
            physx_scene_api.CreateEnableGPUDynamicsAttr().Set(False)

        return scene

    @staticmethod
    def set_gravity_preset(
        stage: Usd.Stage,
        scene_path: str = "/World/PhysicsScene",
        preset: str = "earth"
    ) -> float:
        """Sets gravity magnitude preset: 'earth' (981.0), 'moon' (162.0), 'zero_g' (0.0)."""
        presets = {
            "earth": 981.0,
            "moon": 162.0,
            "jupiter": 2479.0,
            "zero_g": 0.0
        }
        val = presets.get(preset.lower(), 981.0)
        scene_prim = stage.GetPrimAtPath(scene_path)
        if scene_prim.IsValid():
            scene = UsdPhysics.Scene(scene_prim)
            scene.GetGravityMagnitudeAttr().Set(val)
        return val

    @staticmethod
    def apply_rigid_body(
        prim: Usd.Prim,
        kinematic: bool = False,
        starts_asleep: bool = False
    ) -> UsdPhysics.RigidBodyAPI:
        """
        Applies RigidBody dynamics to a USD Prim.
        
        Args:
            prim: USD Prim to turn into a dynamic rigid body.
            kinematic: If True, body is kinematic (moved only via keyframes/transforms).
            starts_asleep: If True, body is deactivated until collision occurs.
            
        Returns:
            The applied UsdPhysics.RigidBodyAPI schema.
        """
        rb_api = UsdPhysics.RigidBodyAPI.Apply(prim)
        rb_api.CreateRigidBodyEnabledAttr().Set(True)
        rb_api.CreateKinematicEnabledAttr().Set(kinematic)
        rb_api.CreateStartsAsleepAttr().Set(starts_asleep)
        return rb_api

    @staticmethod
    def apply_collision(
        prim: Usd.Prim,
        approximation: str = "convexHull"
    ) -> UsdPhysics.CollisionAPI:
        """
        Applies collision geometry to a USD Prim.
        
        Args:
            prim: USD Prim to add collisions to.
            approximation: Approximation type ('none', 'convexHull', 'convexDecomposition', 'meshSimplification', 'boundingCube', 'boundingSphere').
            
        Returns:
            The applied UsdPhysics.CollisionAPI schema.
        """
        collision_api = UsdPhysics.CollisionAPI.Apply(prim)
        collision_api.CreateCollisionEnabledAttr().Set(True)

        # Apply mesh collision approximation if supported
        if prim.IsA(Usd.Typed) and approximation != "none":
            mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
            mesh_collision_api.CreateApproximationAttr().Set(approximation)

        return collision_api

    @staticmethod
    def apply_mass_and_density(
        prim: Usd.Prim,
        mass: Optional[float] = None,
        density: Optional[float] = 1000.0
    ) -> UsdPhysics.MassAPI:
        """
        Applies mass properties or material density to a Prim.
        
        Args:
            prim: USD Prim.
            mass: Explicit mass in kilograms (if None, density is used).
            density: Density in kg/m^3 (default: 1000.0 for water/plastic equivalent).
        """
        mass_api = UsdPhysics.MassAPI.Apply(prim)
        if mass is not None:
            mass_api.CreateMassAttr().Set(mass)
        elif density is not None:
            mass_api.CreateDensityAttr().Set(density)
        return mass_api

    @staticmethod
    def create_physics_material(
        stage: Usd.Stage,
        material_path: str,
        static_friction: float = 0.5,
        dynamic_friction: float = 0.5,
        restitution: float = 0.2
    ) -> UsdPhysics.MaterialAPI:
        """
        Creates a UsdPhysics Material with friction and bounciness (restitution).
        
        Args:
            stage: Active USD stage.
            material_path: SdfPath for the physics material.
            static_friction: Static friction coefficient (0.0 to 1.0+).
            dynamic_friction: Dynamic friction coefficient (0.0 to 1.0+).
            restitution: Restitution / bounciness (0.0 = clay, 1.0 = superball).
        """
        prim = stage.GetPrimAtPath(material_path)
        if not prim.IsValid():
            prim = stage.DefinePrim(Sdf.Path(material_path), "Material")
        
        phys_mat = UsdPhysics.MaterialAPI.Apply(prim)
        phys_mat.CreateStaticFrictionAttr().Set(static_friction)
        phys_mat.CreateDynamicFrictionAttr().Set(dynamic_friction)
        phys_mat.CreateRestitutionAttr().Set(restitution)
        return phys_mat

    @staticmethod
    def bind_physics_material(prim: Usd.Prim, material_path: str) -> None:
        """Binds a physics material to a collision prim."""
        mat_api = UsdPhysics.MaterialAPI.Apply(prim)
        mat_api.GetSurfaceRef().SetTargets([Sdf.Path(material_path)])
