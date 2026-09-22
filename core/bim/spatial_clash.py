"""Automated BIM 3D Spatial Clash Detection Engine.
Performs 3D Axis-Aligned Bounding Box (AABB) intersection analysis,
overlap penetration depth calculation, severity classification, and
BCF (BIM Collaboration Format) issue generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AABB:
    """Axis-Aligned Bounding Box representation."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float, float, float, float]) -> AABB:
        return cls(t[0], t[1], t[2], t[3], t[4], t[5])

    def to_tuple(self) -> Tuple[float, float, float, float, float, float]:
        return (self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)


def compute_prim_aabb(prim: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    """Computes axis-aligned bounding box (min_x, min_y, min_z, max_x, max_y, max_z) in stage units (cm)."""
    pos = prim.get("position", [0.0, 0.0, 0.0])
    scale = prim.scale if hasattr(prim, "scale") else prim.get("scale", [1.0, 1.0, 1.0])
    props = prim.get("geomProps", {})
    ptype = prim.get("type", "Cube")

    px, py, pz = float(pos[0]), float(pos[1]), float(pos[2])
    sx, sy, sz = float(scale[0]), float(scale[1]), float(scale[2])

    if ptype == "Cube":
        size = float(props.get("size", 100.0))
        hx = (size * sx) * 0.5
        hy = (size * sy) * 0.5
        hz = (size * sz) * 0.5
    elif ptype == "Cylinder":
        radius = float(props.get("radius", 50.0))
        height = float(props.get("height", 200.0))
        axis = props.get("axis", "Y")
        rot = prim.get("rotation", [0.0, 0.0, 0.0])

        if axis == "X" or abs(float(rot[2])) > 45.0 or "Sprinkler" in prim.get("name", "") or "Water" in prim.get("name", ""):
            hx = (height * sx) * 0.5
            hy = (radius * sy)
            hz = (radius * sz)
        elif axis == "Z" or abs(float(rot[0])) > 45.0:
            hx = (radius * sx)
            hy = (radius * sy)
            hz = (height * sz) * 0.5
        else:
            hx = (radius * sx)
            hy = (height * sy) * 0.5
            hz = (radius * sz)
    elif ptype == "Plane":
        w = float(props.get("width", 1000.0)) * sx * 0.5
        l = float(props.get("length", 1000.0)) * sz * 0.5
        hx, hy, hz = w, 1.0, l
    else:
        hx, hy, hz = 50.0 * sx, 50.0 * sy, 50.0 * sz

    return (px - hx, py - hy, pz - hz, px + hx, py + hy, pz + hz)


def detect_bim_clashes(
    prims: List[Dict[str, Any]],
    tolerance_cm: float = 2.0,
    check_slabs: bool = False
) -> List[Dict[str, Any]]:
    """Runs spatial collision detection between MEP systems and Structural frames.
    
    Returns a sorted list of BCF-compliant clash records.
    """
    mep_prims = []
    structural_prims = []

    for p in prims:
        bim = p.get("bim")
        if not bim:
            continue
        disc = bim.get("discipline")
        ifc_cls = bim.get("ifcClass", "")
        if disc == "MEP":
            if "Solar" not in p.get("name", ""):
                mep_prims.append(p)
        elif disc == "Structural":
            if not check_slabs and "Slab" in ifc_cls:
                continue
            structural_prims.append(p)

    clashes = []
    clash_idx = 0

    for mep in mep_prims:
        box_a = compute_prim_aabb(mep)
        for struct in structural_prims:
            box_b = compute_prim_aabb(struct)

            # Intersection test
            ox = min(box_a[3], box_b[3]) - max(box_a[0], box_b[0])
            oy = min(box_a[4], box_b[4]) - max(box_a[1], box_b[1])
            oz = min(box_a[5], box_b[5]) - max(box_a[2], box_b[2])

            if ox > tolerance_cm and oy > tolerance_cm and oz > tolerance_cm:
                clash_idx += 1
                pen_depth = min(ox, oy, oz)
                vol = ox * oy * oz

                # Centroid of intersection
                cx = (max(box_a[0], box_b[0]) + min(box_a[3], box_b[3])) * 0.5
                cy = (max(box_a[1], box_b[1]) + min(box_a[4], box_b[4])) * 0.5
                cz = (max(box_a[2], box_b[2]) + min(box_a[5], box_b[5])) * 0.5

                if pen_depth >= 15.0:
                    severity = "CRITICAL"
                    desc = f"Hard collision: {mep.get('name')} penetrates load-bearing {struct.get('name')} by {pen_depth:.1f} cm."
                    mitigation = "Reroute distribution duct/pipe around structural grid or submit RFI for engineered structural sleeve."
                elif pen_depth >= 6.0:
                    severity = "MAJOR"
                    desc = f"Major spatial interference: {mep.get('name')} encroaches into structural boundary of {struct.get('name')}."
                    mitigation = "Adjust elevation or offset distribution run by minimum 350 mm."
                else:
                    severity = "WARNING"
                    desc = f"Clearance tolerance violation: insufficient isolation space between {mep.get('name')} and {struct.get('name')}."
                    mitigation = "Install firestop sleeve and vibration isolation bracket."

                storey = mep.get("bim", {}).get("storey", struct.get("bim", {}).get("storey", "Storey_00_Ground"))

                clash_record = {
                    "id": f"CLASH-{clash_idx:03d}",
                    "title": f"Clash: {mep.get('name')} vs {struct.get('name')}",
                    "severity": severity,
                    "storey": storey,
                    "description": desc,
                    "mitigation": mitigation,
                    "penetrationDepthCm": round(pen_depth, 1),
                    "overlapVolumeCm3": round(vol, 1),
                    "centroid": [round(cx, 1), round(cy, 1), round(cz, 1)],
                    "overlapExtents": [round(ox, 1), round(oy, 1), round(oz, 1)],
                    "elementA": {
                        "path": mep.get("path"),
                        "name": mep.get("name"),
                        "discipline": "MEP",
                        "ifcClass": mep.get("bim", {}).get("ifcClass", "IfcDistributionElement")
                    },
                    "elementB": {
                        "path": struct.get("path"),
                        "name": struct.get("name"),
                        "discipline": "Structural",
                        "ifcClass": struct.get("bim", {}).get("ifcClass", "IfcStructuralMember")
                    },
                    "bcfMetadata": {
                        "topicType": "Clash",
                        "topicStatus": "Active",
                        "priority": "High" if severity == "CRITICAL" else "Medium",
                        "assignedTo": "MEP / Structural Coordination Team"
                    }
                }
                clashes.append(clash_record)

    severity_order = {"CRITICAL": 0, "MAJOR": 1, "WARNING": 2}
    clashes.sort(key=lambda c: (severity_order.get(c["severity"], 9), -c["penetrationDepthCm"]))

    for i, c in enumerate(clashes, 1):
        c["id"] = f"CLASH-{i:03d}"

    return clashes


def export_bcf_report(clashes: List[Dict[str, Any]], out_path: str) -> str:
    """Exports detected clashes to standard BCF (BIM Collaboration Format) JSON report."""
    topics = []
    for c in clashes:
        topics.append({
            "guid": c["id"],
            "topicType": c.get("bcfMetadata", {}).get("topicType", "Clash"),
            "topicStatus": c.get("bcfMetadata", {}).get("topicStatus", "Active"),
            "title": c["title"],
            "priority": c["severity"],
            "creationDate": "2026-09-22T00:00:00Z",
            "creationAuthor": "Omniverse Automated Spatial Solver",
            "description": c.get("description", f"Spatial penetration of {c['penetrationDepthCm']} cm detected between {c['elementA']['name']} and {c['elementB']['name']}."),
            "viewpoint": {
                "cameraViewPoint": c["centroid"],
                "cameraDirection": [0.0, -0.707, -0.707],
                "cameraUpVector": [0.0, 1.0, 0.0]
            },
            "components": [c["elementA"]["path"], c["elementB"]["path"]],
            "comments": [
                {
                    "comment": c["mitigation"],
                    "date": "2026-09-22T00:00:00Z",
                    "author": "BIM Coordinator"
                }
            ]
        })

    report = {
        "project": {
            "name": "Smart Tech Campus Facility",
            "projectId": "PRJ-ATHENS-BIM-001"
        },
        "version": "BCF-API 2.1 JSON",
        "topicCount": len(topics),
        "topics": topics
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return out_path
