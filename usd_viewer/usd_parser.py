"""
OpenUSD Stage Parser for WebGL 3D Visualization.
Traverses any USD / USDA / USDC stage using pxr and serializes the complete
scene graph, PBR materials, lights, cameras, and UsdPhysics schemas to clean JSON.
"""

import math
import os
from typing import Any, Dict, List, Optional
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade


def matrix4d_to_list(mat: Gf.Matrix4d) -> List[float]:
    """Convert Gf.Matrix4d (row-major) to a flat 16-element list in column-major order for Three.js."""
    # Three.js uses column-major matrices (elements[col * 4 + row])
    # Gf.Matrix4d indexing is mat[row][col]
    elements = []
    for col in range(4):
        for row in range(4):
            elements.append(float(mat[row][col]))
    return elements


def parse_materials(stage: Usd.Stage) -> Dict[str, Dict[str, Any]]:
    """Extracts all UsdShade Material and UsdPreviewSurface shader definitions."""
    materials = {}

    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material):
            mat_path = str(prim.GetPath())
            mat = UsdShade.Material(prim)
            surface_output = mat.GetSurfaceOutput()
            
            # Default material props
            diffuse_color = [0.7, 0.7, 0.7]
            emissive_color = [0.0, 0.0, 0.0]
            roughness = 0.5
            metallic = 0.0
            opacity = 1.0
            ior = 1.5

            # Find connected shader
            shader_prim = None
            if surface_output and surface_output.HasConnectedSource():
                source = surface_output.GetConnectedSource()
                if source:
                    shader_prim = source[0].GetPrim()

            # If no direct connection found, look for child Shader
            if not shader_prim:
                for child in prim.GetChildren():
                    if child.IsA(UsdShade.Shader):
                        shader_prim = child
                        break

            if shader_prim:
                shader = UsdShade.Shader(shader_prim)
                
                # Extract inputs
                diffuse_input = shader.GetInput("diffuseColor")
                if diffuse_input and diffuse_input.Get():
                    val = diffuse_input.Get()
                    diffuse_color = [float(val[0]), float(val[1]), float(val[2])]

                emissive_input = shader.GetInput("emissiveColor")
                if emissive_input and emissive_input.Get():
                    val = emissive_input.Get()
                    emissive_color = [float(val[0]), float(val[1]), float(val[2])]

                roughness_input = shader.GetInput("roughness")
                if roughness_input and roughness_input.Get() is not None:
                    roughness = float(roughness_input.Get())

                metallic_input = shader.GetInput("metallic")
                if metallic_input and metallic_input.Get() is not None:
                    metallic = float(metallic_input.Get())

                opacity_input = shader.GetInput("opacity")
                if opacity_input and opacity_input.Get() is not None:
                    opacity = float(opacity_input.Get())

                ior_input = shader.GetInput("ior")
                if ior_input and ior_input.Get() is not None:
                    ior = float(ior_input.Get())

            materials[mat_path] = {
                "path": mat_path,
                "name": prim.GetName(),
                "diffuseColor": diffuse_color,
                "emissiveColor": emissive_color,
                "roughness": roughness,
                "metallic": metallic,
                "opacity": opacity,
                "ior": ior,
            }

    return materials


def parse_lights(stage: Usd.Stage, xform_cache: UsdGeom.XformCache) -> List[Dict[str, Any]]:
    """Extracts DomeLight, DistantLight, SphereLight and RectLight."""
    lights = []

    for prim in stage.Traverse():
        type_name = prim.GetTypeName()
        path = str(prim.GetPath())
        world_tf = xform_cache.GetLocalToWorldTransform(prim)
        trans = world_tf.ExtractTranslation()
        rot_mat = world_tf.ExtractRotationMatrix()

        if prim.IsA(UsdLux.DomeLight) or type_name == "DomeLight":
            light = UsdLux.DomeLight(prim)
            color_attr = light.GetColorAttr().Get() if light.GetColorAttr() else Gf.Vec3f(1.0, 1.0, 1.0)
            intensity_attr = light.GetIntensityAttr().Get() if light.GetIntensityAttr() else 1000.0
            lights.append({
                "path": path,
                "name": prim.GetName(),
                "type": "DomeLight",
                "color": [float(color_attr[0]), float(color_attr[1]), float(color_attr[2])],
                "intensity": float(intensity_attr),
                "matrix": matrix4d_to_list(world_tf),
            })
        elif prim.IsA(UsdLux.DistantLight) or type_name == "DistantLight":
            light = UsdLux.DistantLight(prim)
            color_attr = light.GetColorAttr().Get() if light.GetColorAttr() else Gf.Vec3f(1.0, 1.0, 1.0)
            intensity_attr = light.GetIntensityAttr().Get() if light.GetIntensityAttr() else 1000.0
            
            # Rotation
            angles = world_tf.ExtractRotation().Decompose(Gf.Vec3d(1, 0, 0), Gf.Vec3d(0, 1, 0), Gf.Vec3d(0, 0, 1))
            lights.append({
                "path": path,
                "name": prim.GetName(),
                "type": "DistantLight",
                "color": [float(color_attr[0]), float(color_attr[1]), float(color_attr[2])],
                "intensity": float(intensity_attr),
                "position": [float(trans[0]), float(trans[1]), float(trans[2])],
                "rotation": [float(angles[0]), float(angles[1]), float(angles[2])],
                "matrix": matrix4d_to_list(world_tf),
            })
        elif prim.IsA(UsdLux.SphereLight) or type_name == "SphereLight":
            light = UsdLux.SphereLight(prim)
            color_attr = light.GetColorAttr().Get() if light.GetColorAttr() else Gf.Vec3f(1.0, 1.0, 1.0)
            intensity_attr = light.GetIntensityAttr().Get() if light.GetIntensityAttr() else 1000.0
            radius_attr = light.GetRadiusAttr().Get() if light.GetRadiusAttr() else 1.0
            lights.append({
                "path": path,
                "name": prim.GetName(),
                "type": "SphereLight",
                "color": [float(color_attr[0]), float(color_attr[1]), float(color_attr[2])],
                "intensity": float(intensity_attr),
                "radius": float(radius_attr),
                "position": [float(trans[0]), float(trans[1]), float(trans[2])],
                "matrix": matrix4d_to_list(world_tf),
            })

    return lights


def parse_cameras(stage: Usd.Stage, xform_cache: UsdGeom.XformCache) -> List[Dict[str, Any]]:
    """Extracts Camera prims."""
    cameras = []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Camera):
            cam = UsdGeom.Camera(prim)
            world_tf = xform_cache.GetLocalToWorldTransform(prim)
            trans = world_tf.ExtractTranslation()
            rot_mat = world_tf.ExtractRotation()
            angles = rot_mat.Decompose(Gf.Vec3d(1, 0, 0), Gf.Vec3d(0, 1, 0), Gf.Vec3d(0, 0, 1))

            focal_length = cam.GetFocalLengthAttr().Get() if cam.GetFocalLengthAttr() else 50.0
            h_aperture = cam.GetHorizontalApertureAttr().Get() if cam.GetHorizontalApertureAttr() else 20.955
            v_aperture = cam.GetVerticalApertureAttr().Get() if cam.GetVerticalApertureAttr() else 15.2908

            # Calculate FOV in degrees
            fov = 2.0 * math.atan((v_aperture / 2.0) / focal_length) * (180.0 / math.pi)

            cameras.append({
                "path": str(prim.GetPath()),
                "name": prim.GetName(),
                "focalLength": float(focal_length),
                "fov": float(fov),
                "position": [float(trans[0]), float(trans[1]), float(trans[2])],
                "rotation": [float(angles[0]), float(angles[1]), float(angles[2])],
                "matrix": matrix4d_to_list(world_tf),
            })
    return cameras


def parse_physics_attributes(prim: Usd.Prim) -> Dict[str, Any]:
    """Extracts UsdPhysics attributes for rigid bodies, colliders, and mass."""
    physics = {
        "isRigidBody": False,
        "isCollisionEnabled": False,
        "mass": None,
        "density": None,
        "approximation": "none"
    }

    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
        rb = UsdPhysics.RigidBodyAPI(prim)
        enabled = rb.GetRigidBodyEnabledAttr().Get() if rb.GetRigidBodyEnabledAttr() else True
        physics["isRigidBody"] = bool(enabled)

    if prim.HasAPI(UsdPhysics.CollisionAPI):
        col = UsdPhysics.CollisionAPI(prim)
        enabled = col.GetCollisionEnabledAttr().Get() if col.GetCollisionEnabledAttr() else True
        physics["isCollisionEnabled"] = bool(enabled)

    if prim.HasAPI(UsdPhysics.MassAPI):
        mass_api = UsdPhysics.MassAPI(prim)
        if mass_api.GetMassAttr() and mass_api.GetMassAttr().Get() is not None:
            physics["mass"] = float(mass_api.GetMassAttr().Get())
        if mass_api.GetDensityAttr() and mass_api.GetDensityAttr().Get() is not None:
            physics["density"] = float(mass_api.GetDensityAttr().Get())

    if prim.HasAPI(UsdPhysics.MeshCollisionAPI):
        mcol = UsdPhysics.MeshCollisionAPI(prim)
        if mcol.GetApproximationAttr() and mcol.GetApproximationAttr().Get():
            physics["approximation"] = str(mcol.GetApproximationAttr().Get())

    return physics


def parse_geometry_prim(prim: Usd.Prim, xform_cache: UsdGeom.XformCache) -> Optional[Dict[str, Any]]:
    """Extracts geometry, transforms, material binding, and physics from a Gprim."""
    type_name = prim.GetTypeName()
    path = str(prim.GetPath())

    # Supported geometric primitives
    valid_types = ["Cube", "Sphere", "Cylinder", "Capsule", "Plane", "Mesh"]
    if type_name not in valid_types:
        return None

    world_tf = xform_cache.GetLocalToWorldTransform(prim)
    trans = world_tf.ExtractTranslation()
    rot = world_tf.ExtractRotation()
    angles = rot.Decompose(Gf.Vec3d(1, 0, 0), Gf.Vec3d(0, 1, 0), Gf.Vec3d(0, 0, 1))
    
    # Calculate scale by checking length of basis vectors
    scale_x = Gf.Vec3d(world_tf[0][0], world_tf[0][1], world_tf[0][2]).GetLength()
    scale_y = Gf.Vec3d(world_tf[1][0], world_tf[1][1], world_tf[1][2]).GetLength()
    scale_z = Gf.Vec3d(world_tf[2][0], world_tf[2][1], world_tf[2][2]).GetLength()

    # Material binding
    bound_material_path = None
    if prim.HasAPI(UsdShade.MaterialBindingAPI):
        binding_api = UsdShade.MaterialBindingAPI(prim)
        direct_binding = binding_api.GetDirectBinding()
        if direct_binding and direct_binding.GetMaterialPath():
            bound_material_path = str(direct_binding.GetMaterialPath())

    # Geometry-specific parameters
    geom_props: Dict[str, Any] = {}
    
    if type_name == "Cube":
        cube = UsdGeom.Cube(prim)
        size_val = cube.GetSizeAttr().Get() if cube.GetSizeAttr() else 2.0
        geom_props["size"] = float(size_val)
    elif type_name == "Sphere":
        sphere = UsdGeom.Sphere(prim)
        radius_val = sphere.GetRadiusAttr().Get() if sphere.GetRadiusAttr() else 1.0
        geom_props["radius"] = float(radius_val)
    elif type_name == "Cylinder":
        cyl = UsdGeom.Cylinder(prim)
        geom_props["radius"] = float(cyl.GetRadiusAttr().Get() if cyl.GetRadiusAttr() else 1.0)
        geom_props["height"] = float(cyl.GetHeightAttr().Get() if cyl.GetHeightAttr() else 2.0)
        geom_props["axis"] = str(cyl.GetAxisAttr().Get() if cyl.GetAxisAttr() else "Y")
    elif type_name == "Capsule":
        capsule = UsdGeom.Capsule(prim)
        geom_props["radius"] = float(capsule.GetRadiusAttr().Get() if capsule.GetRadiusAttr() else 0.5)
        geom_props["height"] = float(capsule.GetHeightAttr().Get() if capsule.GetHeightAttr() else 1.0)
        geom_props["axis"] = str(capsule.GetAxisAttr().Get() if capsule.GetAxisAttr() else "Y")
    elif type_name == "Plane":
        plane = UsdGeom.Plane(prim)
        geom_props["width"] = float(plane.GetWidthAttr().Get() if plane.GetWidthAttr() else 100.0)
        geom_props["length"] = float(plane.GetLengthAttr().Get() if plane.GetLengthAttr() else 100.0)
        geom_props["axis"] = str(plane.GetAxisAttr().Get() if plane.GetAxisAttr() else "Y")
    elif type_name == "Mesh":
        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        
        geom_props["points"] = [[float(p[0]), float(p[1]), float(p[2])] for p in pts] if pts else []
        geom_props["indices"] = [int(i) for i in indices] if indices else []
        geom_props["counts"] = [int(c) for c in counts] if counts else []

    physics = parse_physics_attributes(prim)

    # BIM Attributes extraction
    bim_info = None
    ifc_attr = prim.GetAttribute("bim:ifcClass")
    disc_attr = prim.GetAttribute("bim:discipline")
    storey_attr = prim.GetAttribute("bim:storey")
    if ifc_attr or disc_attr or storey_attr:
        psets = {}
        for attr in prim.GetAttributes():
            name = attr.GetName()
            if name.startswith("bim:pset:"):
                key = name[len("bim:pset:"):]
                val = attr.Get()
                psets[key] = val

        bim_info = {
            "ifcClass": str(ifc_attr.Get() or "") if ifc_attr else "IfcBuildingElement",
            "discipline": str(disc_attr.Get() or "") if disc_attr else "Architectural",
            "storey": str(storey_attr.Get() or "") if storey_attr else "",
            "psets": psets,
        }

    # Cesium Anchor extraction
    cesium_anchor = None
    lat_attr = prim.GetAttribute("cesium:anchor:latitude")
    if lat_attr and lat_attr.Get() is not None:
        lon_attr = prim.GetAttribute("cesium:anchor:longitude")
        h_attr = prim.GetAttribute("cesium:anchor:height")
        cesium_anchor = {
            "latitude": float(lat_attr.Get()),
            "longitude": float(lon_attr.Get()) if lon_attr and lon_attr.Get() is not None else 0.0,
            "height": float(h_attr.Get()) if h_attr and h_attr.Get() is not None else 0.0,
        }

    return {
        "path": path,
        "name": prim.GetName(),
        "type": type_name,
        "position": [float(trans[0]), float(trans[1]), float(trans[2])],
        "rotation": [float(angles[0]), float(angles[1]), float(angles[2])],
        "scale": [float(scale_x), float(scale_y), float(scale_z)],
        "matrix": matrix4d_to_list(world_tf),
        "materialPath": bound_material_path,
        "geomProps": geom_props,
        "physics": physics,
        "bim": bim_info,
        "cesiumAnchor": cesium_anchor,
    }


def build_hierarchy_tree(prim: Usd.Prim) -> Dict[str, Any]:
    """Builds a nested tree structure for the USD Outliner UI."""
    node = {
        "path": str(prim.GetPath()),
        "name": prim.GetName() if prim.GetName() else "/",
        "type": prim.GetTypeName() if prim.GetTypeName() else "Xform",
        "hasRigidBody": prim.HasAPI(UsdPhysics.RigidBodyAPI),
        "hasCollision": prim.HasAPI(UsdPhysics.CollisionAPI),
        "children": []
    }

    for child in prim.GetChildren():
        node["children"].append(build_hierarchy_tree(child))

    return node


def parse_usd_stage(stage_path: str) -> Dict[str, Any]:
    """Parses a USD stage file and returns a complete WebGL scene dictionary."""
    if not os.path.exists(stage_path):
        raise FileNotFoundError(f"USD stage not found: {stage_path}")

    stage = Usd.Stage.Open(stage_path)
    if not stage:
        raise ValueError(f"Failed to open USD stage: {stage_path}")

    xform_cache = UsdGeom.XformCache()

    up_axis = UsdGeom.GetStageUpAxis(stage)
    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)

    materials = parse_materials(stage)
    lights = parse_lights(stage, xform_cache)
    cameras = parse_cameras(stage, xform_cache)

    prims = []
    for prim in stage.Traverse():
        geom_data = parse_geometry_prim(prim, xform_cache)
        if geom_data:
            prims.append(geom_data)

    hierarchy = build_hierarchy_tree(stage.GetPseudoRoot())

    # Count physics objects
    rigid_body_count = sum(1 for p in prims if p["physics"]["isRigidBody"])
    collider_count = sum(1 for p in prims if p["physics"]["isCollisionEnabled"])

    # Extract Cesium Georeference (if authored)
    cesium_georef = None
    georef_prim = stage.GetPrimAtPath("/World/CesiumGeoreference")
    if georef_prim.IsValid():
        g_lat = georef_prim.GetAttribute("cesium:latitude")
        g_lon = georef_prim.GetAttribute("cesium:longitude")
        g_h = georef_prim.GetAttribute("cesium:height")
        g_binding = georef_prim.GetAttribute("cesium:georeferenceBinding")
        cesium_georef = {
            "latitude": float(g_lat.Get()) if g_lat and g_lat.Get() is not None else 0.0,
            "longitude": float(g_lon.Get()) if g_lon and g_lon.Get() is not None else 0.0,
            "height": float(g_h.Get()) if g_h and g_h.Get() is not None else 0.0,
            "binding": str(g_binding.Get()) if g_binding and g_binding.Get() else "WGS84",
        }
    else:
        for p in stage.Traverse():
            p_lat = p.GetAttribute("cesium:anchor:latitude")
            if p_lat and p_lat.Get() is not None:
                p_lon = p.GetAttribute("cesium:anchor:longitude")
                p_h = p.GetAttribute("cesium:anchor:height")
                cesium_georef = {
                    "latitude": float(p_lat.Get()),
                    "longitude": float(p_lon.Get()) if p_lon and p_lon.Get() is not None else 0.0,
                    "height": float(p_h.Get()) if p_h and p_h.Get() is not None else 0.0,
                    "binding": "WGS84"
                }
                break

    # Extract BIM Summary
    bim_elements = [p for p in prims if p.get("bim")]
    bim_summary = None
    if bim_elements:
        bim_summary = {
            "elementCount": len(bim_elements),
            "storeys": sorted(list({p["bim"]["storey"] for p in bim_elements if p["bim"].get("storey")})),
            "disciplines": sorted(list({p["bim"]["discipline"] for p in bim_elements if p["bim"].get("discipline")})),
            "classes": sorted(list({p["bim"]["ifcClass"] for p in bim_elements if p["bim"].get("ifcClass")})),
        }

    return {
        "filename": os.path.basename(stage_path),
        "stagePath": stage_path,
        "metadata": {
            "upAxis": up_axis,
            "metersPerUnit": meters_per_unit,
            "primCount": len(prims),
            "materialCount": len(materials),
            "lightCount": len(lights),
            "cameraCount": len(cameras),
            "rigidBodyCount": rigid_body_count,
            "colliderCount": collider_count,
            "bimCount": len(bim_elements),
            "hasCesium": cesium_georef is not None,
        },
        "cesium": cesium_georef,
        "bimSummary": bim_summary,
        "hierarchy": hierarchy,
        "materials": materials,
        "lights": lights,
        "cameras": cameras,
        "prims": prims,
    }


if __name__ == "__main__":
    import json
    test_path = os.path.abspath("usd_generators/output_physics_playground.usda")
    res = parse_usd_stage(test_path)
    print(f"Parsed {res['filename']} successfully:")
    print(f"  Prims: {len(res['prims'])}, Materials: {len(res['materials'])}, Lights: {len(res['lights'])}, Cameras: {len(res['cameras'])}")
