"""
BIM Automated Clash Detection Engine
====================================
Performs spatial intersection (AABB / geometric clearance) analysis between
MEP distribution elements and Structural framing systems in OpenUSD BIM stages.
Outputs BCF 3.0 (BIM Collaboration Format) compatible clash issues.
"""

from __future__ import annotations
import os
import sys
import argparse
import json
from typing import Dict, List, Any, Tuple, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)


def compute_prim_aabb(prim: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    """
    Computes axis-aligned bounding box (min_x, min_y, min_z, max_x, max_y, max_z) in stage units (cm).
    """
    pos = prim.get("position", [0.0, 0.0, 0.0])
    scale = prim.scale if hasattr(prim, "scale") else prim.get("scale", [1.0, 1.0, 1.0])
    props = prim.get("geomProps", {})
    ptype = prim.get("type", "Cube")

    px, py, pz = pos[0], pos[1], pos[2]
    sx, sy, sz = scale[0], scale[1], scale[2]

    if ptype == "Cube":
        size = props.get("size", 1.0)
        hx = (size * sx) * 0.5
        hy = (size * sy) * 0.5
        hz = (size * sz) * 0.5
    elif ptype == "Cylinder":
        radius = props.get("radius", 1.0)
        height = props.get("height", 2.0)
        axis = props.get("axis", "Y")
        rot = prim.get("rotation", [0.0, 0.0, 0.0])

        # If authored along X, or rotated ~90 deg around Z
        if axis == "X" or abs(rot[2]) > 45.0:
            hx = (height * sx) * 0.5
            hy = (radius * sy)
            hz = (radius * sz)
        # If authored along Z, or rotated ~90 deg around X
        elif axis == "Z" or abs(rot[0]) > 45.0:
            hx = (radius * sx)
            hy = (radius * sy)
            hz = (height * sz) * 0.5
        else:
            # Standard vertical along Y
            hx = (radius * sx)
            hy = (height * sy) * 0.5
            hz = (radius * sz)
    elif ptype == "Plane":
        w = props.get("width", 1000.0) * sx * 0.5
        l = props.get("length", 1000.0) * sz * 0.5
        hx, hy, hz = w, 1.0, l
    else:
        hx, hy, hz = 50.0 * sx, 50.0 * sy, 50.0 * sz

    return (px - hx, py - hy, pz - hz, px + hx, py + hy, pz + hz)


def detect_bim_clashes(
    prims: List[Dict[str, Any]],
    tolerance_cm: float = 2.0,
    check_slabs: bool = False
) -> List[Dict[str, Any]]:
    """
    Runs spatial collision detection between MEP systems and Structural frames.
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
            # Exclude solar PV arrays from internal clash checking
            if "Solar" not in p.get("name", ""):
                mep_prims.append(p)
        elif disc == "Structural":
            # Focus primarily on Columns and Beams (or Slabs if enabled)
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

                # Determine severity
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

    # Sort: CRITICAL first, then MAJOR, then WARNING
    severity_order = {"CRITICAL": 0, "MAJOR": 1, "WARNING": 2}
    clashes.sort(key=lambda c: (severity_order.get(c["severity"], 9), -c["penetrationDepthCm"]))

    # Re-index nicely
    for i, c in enumerate(clashes, 1):
        c["id"] = f"CLASH-{i:03d}"

    return clashes


def run_clash_detection_on_stage(stage_path: str) -> Dict[str, Any]:
    """Runs clash detection directly on a USDA/USD stage via usd_parser."""
    from usd_viewer.usd_parser import parse_usd_stage
    parsed = parse_usd_stage(stage_path)
    clashes = detect_bim_clashes(parsed.get("prims", []))
    return {
        "stageFile": os.path.basename(stage_path),
        "totalClashes": len(clashes),
        "criticalCount": sum(1 for c in clashes if c["severity"] == "CRITICAL"),
        "majorCount": sum(1 for c in clashes if c["severity"] == "MAJOR"),
        "warningCount": sum(1 for c in clashes if c["severity"] == "WARNING"),
        "clashes": clashes
    }


def main():
    parser = argparse.ArgumentParser(description="Automated OpenUSD / BIM Clash Detection Solver")
    parser.add_argument("--stage", default=os.path.join(CURRENT_DIR, "output_bim_cesium.usda"), help="Path to USD stage")
    parser.add_argument("--json", action="store_true", help="Output raw JSON report")
    parser.add_argument("--out", default=None, help="Save report to JSON file")
    args = parser.parse_args()

    print(f"[*] Running Automated BIM Clash Detection on: {args.stage}")
    report = run_clash_detection_on_stage(args.stage)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n========================================================")
        print(f" [*] BIM CLASH DETECTION REPORT: {report['totalClashes']} INTERFERENCE(S) FOUND")
        print(f"     Critical: {report['criticalCount']} | Major: {report['majorCount']} | Warning: {report['warningCount']}")
        print(f"========================================================")
        for c in report["clashes"]:
            sev = c["severity"]
            badge = "[CRITICAL]" if sev == "CRITICAL" else ("[MAJOR]" if sev == "MAJOR" else "[WARNING]")
            print(f"\n{badge} [{c['id']}] {c['title']} ({sev})")
            print(f"   Storey: {c['storey']} | Penetration Depth: {c['penetrationDepthCm']} cm")
            print(f"   Centroid (X,Y,Z): {c['centroid']}")
            print(f"   Element A: {c['elementA']['name']} ({c['elementA']['discipline']})")
            print(f"   Element B: {c['elementB']['name']} ({c['elementB']['discipline']})")
            print(f"   Mitigation: {c['mitigation']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n[OK] Saved BCF Clash Report to: {args.out}")


if __name__ == "__main__":
    main()
